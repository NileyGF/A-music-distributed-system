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
    serverNumber = 1

    serverHeaders = {'ReqELECTION':elect.ongoing_election,   # Request ELECTION
                     'RecELECTION':0,                        # Received ELECTION
                     'ELECTED':elect.ended_election          # ELECTED (Election result)
                    }


    def __init__(self, serverNumber, serverIpAddr):
        self.serverNumber = serverNumber
        self.serverIpAddr = serverIpAddr
        self.role_instance = nd.Role_node(self.serverNumber)
        queue = multiprocessing.Queue()
        queue.put(dict())
        multiprocessing.set_start_method('fork', force=True)
        self.accept_proccess = multiprocessing.Process(target=self.init_socket)
        # self.accept_proccess.start()
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
            # while True:
            try:                    
                result = core.send_addr_to_dns(nd.domains_by_role[str(self.role_instance)],address)
                # if result: break
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
        
    def assign_role(self,role:nd.Role_node,args:tuple):
        self.role_instance = role(self.serverNumber,*args)
        return self.run_server()

    def attend_connection(self,connection:socket,address:str):
        received = core.receive_data_from(connection,waiting_time_ms=3000,iter_n=5)
        try:
            decoded = pickle.loads(received)
            print('received: ', decoded)
            # check if it is a server action
            if self.serverHeaders.get(decoded[0]):
                handler = self.serverHeaders.get(decoded[0])
                response = handler(self,decoded[1],connection,address)
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



def main():
    # --------- Retrieve info from the terminal command ---------
    argSize = len(sys.argv)
    argList = sys.argv
    if argSize == 4:
        core.DNS_addr = (argList[3],core.DNS_PORT)
    if argSize < 2:
        argList = [None,'0','172.20.0.0']

    # Creating instances of Servers 
    if argList[1] == '0':
        Server0 = Server(0, argList[2])
        p0 = Server0.run_server()
    elif argList[1] == '1':
        Server1 = Server(1, argList[2])
        p1 = Server1.assign_role(nd.Data_node,('data_nodes', None, False, 'songs'))
    elif argList[1] == '2':
        Server2 = Server(2, argList[2])
        p2 = Server2.assign_role(nd.DNS_node,())
    elif argList[1] == '3':
        Server3 = Server(3, argList[2])
        p3 = Server3.assign_role(nd.Router_node,())

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
