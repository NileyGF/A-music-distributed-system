import socket
import sys
import multiprocessing
import os
from os import path
import pickle
import core
import nodes_definition as nd
import time


class Server:
    'Common base class for all servers.'

    # Global Variables
    # Constructor updates this.
    serverIpAddr = ""
    # Will be re-assigned by constructor.
    serverNumber = 1
    # next_neighbor = None
    # second_neighbor = None
    # back_neighbor = None   

    def __init__(self, serverNumber, serverIpAddr, role:nd.Role_node=None, args:tuple=()):

        self.serverHeaders = {'ReqJRing':self.__requested_join,     # Request Join Ring
                            #   'JRingAt':self.__new_neighbors,     # Join Ring At
                            #   'ReqInit':0, # Request Initialization Info
                            #   'SolInit':0, # Solved Initialization Info
                              'ReportNext':self.back_reporting,     # Fallen Node
                              'FallenNode':self.fallen_node,        # Fallen Node
                              'Unbalance':self.unbalanced_ring,     # Unbalanced Roles
                             }
        manager = multiprocessing.Manager()
        self.ring_links = manager.list()
        self.ring_links.append(None)
        self.ring_links.append(None)
        self.ring_links.append(None)
        
        multiprocessing.set_start_method('fork', force=True)
        self.accept_process = multiprocessing.Process(target=self.init_socket)
        self.ring_process = multiprocessing.Process(target=self.ring_handler)
        self.ping_next_process= multiprocessing.Process(target=self.ping_next)

        self.serverNumber = serverNumber
        self.serverIpAddr = serverIpAddr
        # self.role_instance = nd.Role_node(self.serverNumber)
        self.role_instance = manager.list()
        self.role_instance.append(None)
        if role != None:
            self.role_instance[0] = role(serverNumber,*args)
        else:
            self.__get_role()


    def run_server(self):
        if self.accept_process.is_alive():
            self.accept_process.terminate()
            self.accept_process.join()
        multiprocessing.set_start_method('fork', force=True)
        self.accept_process = multiprocessing.Process(target=self.init_socket)
        self.accept_process.start()
        # self.accept_process.join()
        return self.accept_process

    def init_socket(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        address = (self.serverIpAddr, nd.ports_by_role[str(self.role_instance[0])])
        self.serverSocket.bind(address)
        print(address)
        self.serverSocket.listen(5)
        # self.liveStatus = "Alive"
        if not isinstance(self.role_instance[0],nd.DNS_node):
            # if not DNS: join ring and subscribe to DNS
            while True:
                try:                    
                    result = core.send_addr_to_dns(nd.domains_by_role[str(self.role_instance[0])],address)
                    if result: 
                        break
                except Exception as err:
                    print(err)    
            
            self.__join_ring((self.serverIpAddr, core.RING_PORT))

        processes = []
        try:
            while True:                
                conn, address = self.serverSocket.accept()
                print('CONNECTED: ',address)
                multiprocessing.set_start_method('fork', force=True)
                p = multiprocessing.Process(
                    target=self.attend_connection, args=(conn, address))
                processes.append(p)
                p.start()
        finally:
            self.serverSocket.close()
            for p in processes:
                if p.is_alive():
                    p.terminate()
                    p.join()
        
    # def assign_role(self,role:nd.Role_node,args:tuple):
    #     self.role_instance = role(self.serverNumber,*args)
    #     return self.run_server()

    def attend_connection(self,connection:socket,address:str):
        received = core.receive_data_from(connection,waiting_time_ms=3000,iter_n=5)
        try:
            decoded = pickle.loads(received)
            print('received: ', decoded)
            # check if it is a server action
            if self.serverHeaders.get(decoded[0]):
                print('Ring Handler')
                handler = self.serverHeaders.get(decoded[0])
                response = handler(decoded[1],connection,address)
            # else, if it isn't a role action, send FAILED REQUEST
            elif not self.role_instance[0].headers.get(decoded[0]):
                response = core.FAILED_REQ
                encoded = pickle.dumps(response)
                core.send_bytes_to(encoded,connection,False)
            else:
                print('Role Handler')
                handler = self.role_instance[0].headers.get(decoded[0])
                response = handler(decoded[1],connection,address)

        except Exception as err:
            print(err, "FAILED REQ") 
            response = core.FAILED_REQ
            encoded = pickle.dumps(response)
            core.send_bytes_to(encoded,connection,False)
                 
        finally:
            connection.close()

    def __get_role(self):
        role = 0
        try:
            data_nodes = core.get_addr_from_dns('distpotify.data')
            router_nodes = core.get_addr_from_dns('distpotify.router')
            n_data = len(data_nodes)
            n_router = len(router_nodes)
            if n_data * 1.5 <= n_router:
                role = 0
            else: role = 1
        except:
            pass
        # router role
        if role == 1:
            self.role_instance[0] = nd.Router_node()
            return
        # data role
        for dn in data_nodes:
            try:
                request = tuple(['ReqInit',None,core.TAIL])
                encoded = pickle.dumps(request)
                sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                sock.connect(dn)

                sended, _ = core.send_bytes_to(encoded, sock, False)
                if sended == 'OK':
                    result = core.receive_data_from(sock)
                    decoded = pickle.loads(result)
                    # Send ACK
                    ack = pickle.dumps(core.ACK_OK_tuple)
                    core.send_bytes_to(ack,sock,False)
                    sock.close()

                    if 'SolInit' in decoded:
                        args = decoded[1]
                        self.role_instance[0] = nd.Data_node(n_data+1,*args)
                        return

            except:
                sock.close()
                continue

    def __join_ring(self,address:tuple):
        data_nodes = core.get_addr_from_dns('distpotify.data')
        router_nodes = core.get_addr_from_dns('distpotify.router')
        print(data_nodes, router_nodes)

        for nodes_list in [data_nodes, router_nodes]:
            if nodes_list == None:  continue
            for node in nodes_list:
                if node[0] == self.serverIpAddr: continue
                try:
                    request = tuple(['ReqJRing',address,core.TAIL])
                    encoded = pickle.dumps(request)
                    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                    sock.connect(node)

                    sended, _ = core.send_bytes_to(encoded, sock, False)
                    if sended == 'OK':
                        result = core.receive_data_from(sock)
                        decoded = pickle.loads(result)
                        # Send ACK
                        ack = pickle.dumps(core.ACK_OK_tuple)
                        core.send_bytes_to(ack,sock,False)
                        sock.close()

                        if 'JRingAt' in decoded:
                            # 'JRingAt',(self.next_neighbor,self.second_neighbor)
                            links = decoded[1]
                            if links[0] == None:
                                # the ring is open
                                self.ring_links[1] = (node[0],core.RING_PORT)
                                self.ring_links[2] = None
                                self.ring_links[0] = (node[0],core.RING_PORT)
                                print('the ring is open. ', self.ring_links)
                            else:
                                self.ring_links[1] = (links[0][0],core.RING_PORT)
                                self.ring_links[2]= (links[1][0],core.RING_PORT)
                                self.ring_links[0] = (node[0],core.RING_PORT)
                                print(self.ring_links)

                            self.ring_process = multiprocessing.Process(target=self.ring_handler)
                            self.ring_process.start()
                            return

                except Exception as er:
                    print(er)
                    sock.close()
                    continue

        # self.ring_process = multiprocessing.Process(target=self.ring_handler)
        # self.ring_process.start()
        print("Couldn't join ring!!!")

    def __requested_join(self,address:tuple,connection:socket,conn_address:str):
        if address[0] == self.serverIpAddr:
            raise Exception('Why am I asking to myself???')
        response = tuple(['JRingAt',(self.ring_links[1],self.ring_links[2]),core.TAIL])
        encoded = pickle.dumps(response)

        state = core.send_bytes_to(encoded,connection,False)

        if state [0] == "OK":
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)

            if 'ACK' in decoded:
                # change my references only if the new next_neighbor received OK
                if self.ring_links[1] == None:
                    # I'm not in ring
                    self.ring_process = multiprocessing.Process(target=self.ring_handler)
                    self.ring_process.start()
                self.ring_links[2] = self.ring_links[1]
                self.ring_links[1] = address
                print('new links: ', self.ring_links)
                
                return True
            
        return False
    

    def ring_handler(self):

        self.ringSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ringSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        address = (self.serverIpAddr, core.RING_PORT)
        self.ringSocket.bind(address)
        print(address)
        self.ringSocket.listen(5)

        self.ping_next_process= multiprocessing.Process(target=self.ping_next)
        self.ping_next_process.start()

        processes = []
        try:
            while True:                
                conn, address = self.ringSocket.accept()
                print('Ring conn: ',address)
                multiprocessing.set_start_method('fork', force=True)
                p = multiprocessing.Process(
                    target=self.attend_connection, args=(conn, address))
                processes.append(p)
                p.start()
        finally:
            self.serverSocket.close()
            for p in processes:
                if p.is_alive():
                    p.terminate()
                    p.join()
            if self.ping_next_process.is_alive():
                    self.ping_next_process.terminate()
                    self.ping_next_process.join()


    def ping_next(self):
        while True:
            time.sleep(7)
            print('trying to ping next')
            request = tuple(['ReportNext',None,core.TAIL])
            encoded = pickle.dumps(request)
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            try:
                sock.connect(self.ring_links[1])
                sended, _ = core.send_bytes_to(encoded, sock, False)
                if sended == 'OK':
                    result = core.receive_data_from(sock)
                    decoded = pickle.loads(result)
                    sock.close()
                    print(decoded)
                    if 'ACK' in decoded:
                        if 'OK' in decoded:
                            # ring is stable here
                            print('ring stable')
                            continue
                        else:
                            print("I'm not his previous. So there was a desconnection")
                            # I'm not his previous. So there was a desconnection
                            self.__join_ring((self.serverIpAddr, core.RING_PORT))
                            return
                            
            except Exception as er:
                print(er)
                # next_neighbor is fallen, or I'm fallen
                sock.close() #??? 
                try:
                    sock.connect(self.ring_links[2])
                    # next_neighbor is fallen 'FallenNode'
                    request = tuple(['FallenNode',[[(self.serverIpAddr,core.RING_PORT),self.role_instance[0].__str__()]],core.TAIL])
                    encoded = pickle.dumps(request)
                    sended, _ = core.send_bytes_to(encoded, sock, False)
                except Exception as er:
                    print(er)
                    # It must be me the disconnected one
                    sock.close() #??? 
                    self.__join_ring((self.serverIpAddr, core.RING_PORT))
                    return
                    
    def back_reporting(self, request_data, connection, address):
        if self.ring_links[0] == None:
            self.ring_links[0] = (address[0],core.RING_PORT)
            print('update back_neighbor',self.ring_links[0])
        if address[0] != self.ring_links[0][0]:
            # the ping is not from my back neighbor
            reply = tuple(["ACK","Discontinuity in Ring",core.TAIL])
        else: 
            reply = core.ACK_OK_tuple
        encoded = pickle.dumps(reply)
        state, _ = core.send_bytes_to(encoded,connection,False)
        return True

    def fallen_node(self, request_data, connection, address):
        unbalanced = False
        add_self = True
        for node in request_data:
            print(node[0][0]) # TODO erase
            if node[0][0] == self.serverIpAddr:
                # it's back to me. Check balance
                unbalanced = True
                add_self =False
        if add_self:
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            try:
                sock.connect(self.ring_links[1])
            except:
                # next_neighbor is fallen, or I'm fallen
                sock.close() #??? 
                try:
                    sock.connect(self.ring_links[2])
                except:
                    # It must be me the disconnected one
                    sock.close() #??? 
                    self.__join_ring((self.serverIpAddr, core.RING_PORT))
                    return False
                
            alives = request_data.append([(self.serverIpAddr,core.RING_PORT),self.role_instance[0].__str__()])
            request = tuple(['FallenNode',alives,core.TAIL])
            encoded = pickle.dumps(request)
            sended, _ = core.send_bytes_to(encoded, sock, False)
            return True
        
        if unbalanced:
            n_data = 0
            n_router = 0
            for node in request_data:
                if node[1] == 'Data_node':
                    n_data += 1
                if node[1] == 'Router_node':
                    n_router += 1
            print('datas: ',n_data,'routers: ',n_router)
            if n_data < 2 and n_router > 1:
                request = tuple(["Unbalance","Data_node",core.TAIL])
            elif n_router < 2 and n_data > 2: 
                request = tuple(["Unbalance","Router_node",core.TAIL])
            
            if self.role_instance[0].__str__() != request[1]:
                # I can solve the unbalance
                self.__get_role()
                return True
            
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            try:
                sock.connect(self.ring_links[1])
            except:
                # next_neighbor is fallen, or I'm fallen
                sock.close() #??? 
                try:
                    sock.connect(self.ring_links[2])
                except:
                    # It must be me the disconnected one
                    sock.close() #??? 
                    self.__join_ring((self.serverIpAddr, core.RING_PORT))
                    return False
                
            encoded = pickle.dumps(request)
            sended, _ = core.send_bytes_to(encoded, sock, False)
            return sended == 'OK'
         
    def unbalanced_ring(self, request_data, connection, address):
        request = tuple(["Unbalance",request_data ,core.TAIL])
        encoded = pickle.dumps(request)
            
        if self.role_instance[0].__str__() != request_data:
            # I can solve the unbalance
            self.__get_role()
            return True
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        try:
            sock.connect(self.ring_links[1])
        except:
            # next_neighbor is fallen, or I'm fallen
            sock.close() #??? 
            try:
                sock.connect(self.ring_links[2])
            except:
                # It must be me the disconnected one
                sock.close() #??? 
                self.__join_ring((self.serverIpAddr, core.RING_PORT))
                return False
            
        sended, _ = core.send_bytes_to(encoded, sock, False)
        return True


def main():
    # --------- Retrieve info from the terminal command ---------
    argSize = len(sys.argv)
    argList = sys.argv
    if argSize == 4:
        core.DNS_addr = (argList[3],core.DNS_PORT)
    if argSize < 2:
        argList = [None,'0','172.20.0.200']

    # Creating instances of Servers 
    if argList[1] == '0':
        Server0 = Server(0, argList[2])
        p0 = Server0.run_server()
    elif argList[1] == '1':
        Server1 = Server(1, argList[2],nd.Data_node,('data_nodes', None, True, 'songs'))
        p1 = Server1.run_server()
    elif argList[1] == '2':
        Server2 = Server(2, argList[2],nd.DNS_node,())
        p2 = Server2.run_server()
    elif argList[1] == '3':
        Server3 = Server(3, argList[2],nd.Router_node,())
        p3 = Server3.run_server()

    if argList[1] == '0':
        p0.join()
    elif argList[1] == '1':
        p1.join()
    elif argList[1] == '2':
        p2.join()
    elif argList[1] == '3':
        p3.join()


if __name__ == "__main__":
    main()
    # python3 server_class.py <server_number> <server_ip> <DNS_ip>
