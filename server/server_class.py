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

    def __init__(self, serverNumber, serverIpAddr, role:nd.Role_node, args:tuple=()):

        self.serverHeaders = {'ReqJRing':self.__requested_join,     # Request Join Ring
                            #   'JRingAt':self.__new_neighbors,     # Join Ring At
                            #   'ReqInit':0, # Request Initialization Info
                            #   'SolInit':0, # Solved Initialization Info
                              'ReportNext':self.back_reporting,     # Report to your next in ring
                              'FixRing':self.fix_ring,
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
        self.role_instance = manager.list()
        self.role_instance.append(None)
        self.init_role = [role, args]
        


    def run_server(self):
        if self.accept_process.is_alive():
            self.accept_process.terminate()
            self.accept_process.join()
        multiprocessing.set_start_method('fork', force=True)
        self.accept_process = multiprocessing.Process(target=self.init_socket)
        self.accept_process.start()
        # self.accept_process.join()
        # assign role
        if self.init_role[0] != None:
            # print(self.init_role[0],self.init_role[1])
            # print(self.role_instance)
            self.role_instance[0] = self.init_role[0](*self.init_role[1])
        else:
            self.__get_role()

        return self.accept_process

    def init_socket(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        address = (self.serverIpAddr, nd.ports_by_role[self.init_role[0].str_rep])
        self.serverSocket.bind(address)
        print(address)
        self.serverSocket.listen(5)
        # self.liveStatus = "Alive"
        if not isinstance(self.role_instance[0],nd.DNS_node):
            # if not DNS: join ring and subscribe to DNS
            while True:
                try:                    
                    result = core.send_addr_to_dns(nd.domains_by_role[self.init_role[0].str_rep],address)
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

    def attend_connection(self,connection:socket,address):

        received = core.receive_data_from(connection,waiting_time_ms=3000,iter_n=5,verbose=False)
        while self.role_instance[0] == None:
            continue
        # try:
        decoded = pickle.loads(received)
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

        # except Exception as err:
        #     print(err, "FAILED REQ") 
        #     response = core.FAILED_REQ
        #     encoded = pickle.dumps(response)
        #     core.send_bytes_to(encoded,connection,False)
                 
        # finally:
        #     connection.close()

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
        # print(data_nodes, router_nodes)

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
                            # 'JRingAt',(back_neighbor, next_neighbor, second_neighbor)
                            links = decoded[1]
                            self.updatelinks(links[0],links[1],links[2])
                            # if links[0] == None:
                            #     # the ring is open
                            #     self.ring_links[1] = (node[0],core.RING_PORT)
                            #     self.ring_links[2] = None
                            #     self.ring_links[0] = (node[0],core.RING_PORT)
                            #     print('the ring is open. ', self.ring_links)
                            # elif links[1] == None: 
                            #     # also the ring is open
                            #     self.ring_links[1] = (links[0][0],core.RING_PORT)
                            #     self.ring_links[2] = (node[0],core.RING_PORT)
                            #     self.ring_links[0] = (node[0],core.RING_PORT)
                            #     print('the ring is open. ', self.ring_links)
                            # else:
                            #     self.ring_links[1] = (links[0][0],core.RING_PORT)
                            #     self.ring_links[2]= (links[1][0],core.RING_PORT)
                            #     self.ring_links[0] = (node[0],core.RING_PORT)
                            #     print(self.ring_links)

                            self.ring_process = multiprocessing.Process(target=self.ring_handler)
                            self.ring_process.start()
                            return

                except Exception as er:
                    print(er)
                    sock.close()
                    continue

        # self.ring_process = multiprocessing.Process(target=self.ring_handler)
        # self.ring_process.start()
        print("Couldn't join ring. I'm alone")

    def __requested_join(self,address:tuple,connection:socket,conn_address:str):
        if address[0] == self.serverIpAddr:
            raise Exception('Why am I asking to myself???')
        alone = were_two = regular = False
        if self.ring_links[0] == None and self.ring_links[1] == None and self.ring_links[2] == None:
            # I'm alone so, it's back and it's next are myself, it's second is None
            alone = True
            its_next = self.serverIpAddr        # myself
            its_back = self.serverIpAddr        # myself
            its_second = None                   # my_next
        elif self.ring_links[2] == None:
            # We're two in the ring, so it's next is me, it's back is my back, and it's second is m next
            were_two = True
            its_next = self.serverIpAddr        # myself
            its_back = self.ring_links[0][0]    # my_back
            its_second = self.ring_links[1][0]  # my_next
        else:
            regular = True
            its_next = self.serverIpAddr        # myself
            its_back = self.ring_links[0][0]    # my_back
            its_second = self.ring_links[1][0]  # my_next
        
        response = tuple(['JRingAt',(its_back,its_next,its_second),core.TAIL])
        encoded = pickle.dumps(response)
        state = core.send_bytes_to(encoded,connection,False)

        if state [0] == "OK":
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            if 'ACK' in decoded:
                # change my references only if the new back_neighbor received OK
                if alone: 
                    # my new back and my new next are address
                    self.updatelinks(address[0],address[0],None)
                    # start ring process
                    self.ring_process = multiprocessing.Process(target=self.ring_handler)
                    self.ring_process.start()
                    print('\n new links: ', self.ring_links)
                    return True
                if were_two:
                    # send FixRing to my current back with it's new next = address
                    # my new second and my new back is address
                    message = pickle.dumps(tuple(['FixRing',('?',address[0],self.serverIpAddr),core.TAIL]))
                    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                    sock.connect(self.ring_links[0])
                    sended, _ = core.send_bytes_to(message, sock, False)
                    if sended == 'OK':
                        result = core.receive_data_from(sock)
                        decoded = pickle.loads(result)
                        sock.close()
                        print(decoded)
                        if 'ACK' in decoded:
                            self.updatelinks(address[0],self.ring_links[1][0],address[0])
                            print('\n new links: ', self.ring_links)   
                            return True
                    return False
                if regular:
                    # send FixRing to my current back with it's new next = address
                    # my new back is address
                    message = pickle.dumps(tuple(['FixRing',('?',address[0], self.serverIpAddr),core.TAIL]))
                    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                    sock.connect(self.ring_links[0])
                    sended, _ = core.send_bytes_to(message, sock, False)
                    if sended == 'OK':
                        result = core.receive_data_from(sock)
                        decoded = pickle.loads(result)
                        sock.close()
                        print(decoded)
                        if 'ACK' in decoded:
                            self.updatelinks(address[0],self.ring_links[1][0],self.ring_links[2][0])
                            print('\n new links: ', self.ring_links)   
                            return True            
        return False
    
    def ring_handler(self):
        try: 
            self.ringSocket.close()
        except: pass
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
            self.ringSocket.close()

    def ping_next(self):
        while True:
            time.sleep(15)
            print('---- trying to ping next ----')
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
                    if 'ACK' in decoded:
                        if 'OK' in decoded:
                            # ring is stable here
                            print('--- ring stable ---')
                            continue
                        else:
                            print("I'm not his previous. So there was a desconnection")
                            # I'm not his previous. So there was a desconnection
                            self.updatelinks(None,None,None)
                            print('\n Out of Ring\n')
                            self.__join_ring((self.serverIpAddr, core.RING_PORT))
                            return
                            
            except Exception as er:
                print(er)
                print("next_neighbor has fallen, or I've fallen")
                sock.close() #??? 

                try:
                    self.__report_second()
                except Exception as er:
                    print(er)
                    # It must be me the disconnected one
                    sock.close() 
                    self.__join_ring((self.serverIpAddr, core.RING_PORT))
                    return
                
                # Send Fallen node message
                try:
                    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                    sock.connect(self.ring_links[1])

                    # next_neighbor has fallen 'FallenNode'
                    request = tuple(['FallenNode',[[(self.serverIpAddr,core.RING_PORT),self.role_instance[0].__str__()]],core.TAIL])
                    encoded = pickle.dumps(request)
                    sended, _ = core.send_bytes_to(encoded, sock, False)
                except Exception as er:
                    print(er)
                    # It must be me the disconnected one
                    sock.close() 
                    self.__join_ring((self.serverIpAddr, core.RING_PORT))
                    return
                
    def __report_second(self):
        request = tuple(['ReportNext','Fallen Next',core.TAIL])
        encoded = pickle.dumps(request)
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        sock.connect(self.ring_links[2])
        sended, _ = core.send_bytes_to(encoded, sock, False)
        if sended == 'OK':
            result = core.receive_data_from(sock)
            decoded = pickle.loads(result)
            if 'ACK' in decoded:
                if 'OK' in decoded:
                    sock.close()
                    raise Exception(" I was not his back. How can it be OK?")
                else:
                    result = core.receive_data_from(sock)
                    decoded = pickle.loads(result)
                    if 'FixRing' in decoded:
                        self.fix_ring(decoded[1],sock,self.ring_links[2])
        sock.close()

    def back_reporting(self, request_data, connection, address):
        if address[0] == self.ring_links[0][0]:
            reply = core.ACK_OK_tuple
            encoded = pickle.dumps(reply)
            state, _ = core.send_bytes_to(encoded,connection,False)
            return True
        else: 
            # the ping is not from my back neighbor
            reply = tuple(["ACK","Discontinuity in Ring",core.TAIL])
            encoded = pickle.dumps(reply)
            state, _ = core.send_bytes_to(encoded,connection,False)
            if state == 'OK':
                if request_data != 'Fallen Next':
                    return True
                
                if self.ring_links[2] == self.ring_links[0]:
                    # set second as None
                    self.updatelinks(address[0],self.ring_links[1][0],None)
                else:
                    # update back neighbor
                    self.updatelinks(address[0],self.ring_links[1][0],self.ring_links[2][0])

                print('\n new links: ', self.ring_links)                  
                if address[0] == self.ring_links[1][0]:
                    # my back and my next at the same time
                    message = pickle.dumps(tuple(['FixRing',(self.serverIpAddr, self.serverIpAddr, None),core.TAIL]))
                else:
                    message = pickle.dumps(tuple(['FixRing',('?', self.serverIpAddr, self.ring_links[2][0]),core.TAIL]))
                # send new second to this new neighbor
                sended, _ = core.send_bytes_to(message, connection, False)
                if sended == 'OK':
                    result = core.receive_data_from(connection)
                    decoded = pickle.loads(result)
                    print(decoded)
                    if 'ACK' in decoded:         
                        return True
        return False
               
    # def update_back(self, request_data, connection, address):
    #     if self.ring_links[0] == None:
    #         self.ring_links[0] = (address[0],core.RING_PORT)
    #         print('Updated back_neighbor',self.ring_links[0])
    #     reply = core.ACK_OK_tuple
    #     encoded = pickle.dumps(reply)
    #     state, _ = core.send_bytes_to(encoded,connection,False)
    #     return True


    def updatelinks(self, back_ip:str, next_ip:str, second_ip:str):
        # Next
        if next_ip != None:
            self.ring_links[1] = (next_ip, core.RING_PORT)
        else: self.ring_links[1] = None
        # Second
        if second_ip != None:
            self.ring_links[2] = (second_ip, core.RING_PORT)
        else: self.ring_links[2] = None
        # Back
        if back_ip != None:
            self.ring_links[0] = (back_ip, core.RING_PORT)
        else: self.ring_links[0] = None

    def fix_ring(self, request_data, connection, address):
        new = [request_data[i] != '?' for i in range(len(request_data))]
        args = []
        if new[0]: args.append(request_data[0])
        else: args.append(self.ring_links[0][0])
        if new[1]: args.append(request_data[1])
        else: args.append(self.ring_links[1][0])
        if new[2]: args.append(request_data[2])
        else: args.append(self.ring_links[2][0])
        args = tuple(args)
        self.updatelinks(*args)
        print('\n new links: ', self.ring_links)   
        reply = core.ACK_OK_tuple
        encoded = pickle.dumps(reply)
        state, _ = core.send_bytes_to(encoded,connection,False)
        return state == "OK"

    def fallen_node(self, request_data, connection, address):
        unbalanced = False
        add_self = True
        for node in request_data:
            print(node[0][0]) # TODO erase
            if node[0][0] == self.serverIpAddr:
                # it's back to me. Check balance
                unbalanced = True
                add_self = False
        if add_self:
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            try:
                sock.connect(self.ring_links[1])
            except:
                print("next_neighbor has fallen, or I've fallen")
                sock.close() #??? 
                try:
                    self.__report_second()
                    # updated my second as my next
                    sock.connect(self.ring_links[1])
                except Exception as er:
                    print(er)
                    # It must be me the disconnected one
                    sock.close() 
                    self.__join_ring((self.serverIpAddr, core.RING_PORT))
                    return False
                
            request_data.append([(self.serverIpAddr,core.RING_PORT),self.role_instance[0].__str__()])
            request = tuple(['FallenNode',request_data,core.TAIL])
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
            else:
                # nothing to do
                return True
            if self.role_instance[0].__str__() != request[1]:
                print('I can solve the unbalance')
                self.__get_role()
                return True
            
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            try:
                sock.connect(self.ring_links[1])
            except:
                print("next_neighbor has fallen, or I've fallen")
                sock.close() #??? 
                try:
                    self.__report_second()
                    # updated my second as my next
                    sock.connect(self.ring_links[1])
                except Exception as er:
                    print(er)
                    # It must be me the disconnected one
                    sock.close() 
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
            print("next_neighbor has fallen, or I've fallen")
            sock.close() #??? 
            try:
                self.__report_second()
                # updated my second as my next
                sock.connect(self.ring_links[1])
            except Exception as er:
                print(er)
                # It must be me the disconnected one
                sock.close() 
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
        argList = [None,'0','0.0.0.0']

    # if a == 1:
    #     argList = [None,'1','localhost']
    #     core.DNS_addr = ('0.0.0.0',core.DNS_PORT)
    # if a == 2:
    #     argList = [None,'2','0.0.0.0']
    # if a == 3:
    #     argList = [None,'3','localhost']
    #     core.DNS_addr = ('0.0.0.0',core.DNS_PORT)

    # Creating instances of Servers 
    if argList[1] == '0':
        Server0 = Server(0, argList[2])
        p0 = Server0.run_server()
    elif argList[1] == '1':
        Server1 = Server(1, argList[2],nd.Data_node,(argList[2],'data_nodes', 'songs'))
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
