import socket
import sys
import multiprocessing
import os
from os import path
import pickle
import core
import nodes_definition as nd
import leader_election as elect


class Server:
    'Common base class for all servers.'

    # Global Variables
    # Constructor updates this.
    serverIpAddr = ""
    # Will be re-assigned by constructor.
    # serverNumber = 1
    neighbor = None
    next_neighbor = None

    


    def __init__(self, serverNumber, serverIpAddr, role:nd.Role_node=None,args:tuple=()):

        self.serverHeaders = {'ReqJRing':self.__requested_join,   # Request Join Ring
                              'JRingAt':self.__new_neighbors,    # Join Ring At
                            #   'ReqInit':0, # Request Initialization Info
                            #   'SolInit':0, # Solved Initialization Info
                              'FallenNode':0, # Fallen Node
                              'Unbalance':0,  # Unbalanced Roles
                             }
        
        multiprocessing.set_start_method('fork', force=True)
        self.accept_proccess = multiprocessing.Process(target=self.init_socket)

        # self.serverNumber = serverNumber
        self.serverIpAddr = serverIpAddr
        # self.role_instance = nd.Role_node(self.serverNumber)
        if role != None:
            self.role_instance = role(*args)
            # group_members = core.get_addr_from_dns(nd.domains_by_role[str(self.role_instance)])
        else:
            self.__get_role()

        # self.run_server()


        # print("Constructing server...")

    def run_server(self):
        if self.accept_proccess.is_alive():
            self.accept_proccess.terminate()
            self.accept_proccess.join()
        multiprocessing.set_start_method('fork', force=True)
        self.accept_proccess = multiprocessing.Process(target=self.init_socket)
        self.accept_proccess.start()
        # self.accept_proccess.join()
        return self.accept_proccess

    def init_socket(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        address = (self.serverIpAddr, nd.ports_by_role[str(self.role_instance)])
        self.serverSocket.bind(address)
        print(address)
        self.serverSocket.listen(5)
        self.liveStatus = "Alive"
        if not isinstance(self.role_instance,nd.DNS_node):
            # if not DNS: join ring and subscribe to DNS
            while True:
                try:                    
                    result = core.send_addr_to_dns(nd.domains_by_role[str(self.role_instance)],address)
                    if result: 
                        self.__join_ring(address)
                        break
                except Exception as err:
                    print(err)    

        proccesses = []
        try:
            while True:                
                conn, address = self.serverSocket.accept()
                print('CONNECTED: ',address)
                multiprocessing.set_start_method('fork', force=True)
                p = multiprocessing.Process(
                    target=self.attend_connection, args=(conn, address))
                proccesses.append(p)
                p.start()
                # p.join()
        finally:
            self.serverSocket.close()
            for p in proccesses:
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
                handler = self.serverHeaders.get(decoded[0])
                response = handler(decoded[1],connection,address)
            # else, if it isn't a role action, send FAILED REQUEST
            elif not self.role_instance.headers.get(decoded[0]):
                response = core.FAILED_REQ
                encoded = pickle.dumps(response)
                core.send_bytes_to(encoded,connection,False)
            else:
                handler = self.role_instance.headers.get(decoded[0])
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
            self.role_instance = nd.Router_node()
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
                        self.role_instance = nd.Data_node(*args)
                        return

            except:
                sock.close()
                continue

    def __join_ring(self,address:tuple):
        group_members = core.get_addr_from_dns(nd.domains_by_role[str(self.role_instance)])
        for node in group_members:
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
                        # 'JRingAt',(self.neighbor,self.next_neighbor)
                        links = decoded[1]
                        self.neighbor = links[0]
                        self.next_neighbor = links[1]
                        return

            except:
                sock.close()
                continue
        raise Exception("Couldn't join ring!!!")

    def __requested_join(self,address:tuple,connection:socket,conn_address:str):
        response = tuple(['JRingAt',(self.neighbor,self.next_neighbor),core.TAIL])
        encoded = pickle.dumps(response)

        state = core.send_bytes_to(encoded,connection,False)
        
        if state [0] == "OK":
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)

            if 'ACK' in decoded:
                # change my references only if the new neighbor received OK
                self.next_neighbor = self.neighbor
                self.neighbor = address
                print('new links: ', self.neighbor, ' --> ', self.next_neighbor)
                return True
            
        return False

    # def __new_neighbors(self,links:tuple,connection:socket,address:str):
    #     self.neighbor = links[0]
    #     self.next_neighbor = links[1]

    #     ack = pickle.dumps(core.ACK_OK_tuple)
    #     core.send_bytes_to(ack,connection,False)
            
    #     return True


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
        Server1 = Server(1, argList[2],nd.Data_node,('data_nodes', None, False, 'songs'))
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
