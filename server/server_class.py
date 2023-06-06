import socket
import sys
import multiprocessing
import os
from os import path
import pickle
import core
import nodes_definition as nd


class Server:
    'Common base class for all servers.'

    # Global Variables
    # Constructor updates this.
    serverIpAddr = ""
    # Will be re-assigned by constructor.
    serverNumber = 1
    # Status toggled on/off
    liveStatus = "Alive"
    # shutdown list is shared between instances, i.e. if one object changes it,
    # the change is reflected to all objects. It starts with all False because
    # all servers are up initially. (Maybe this is not necessary)
    shutdown = [False, False, False, False]

    # Constructor

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
        print(address)
        self.serverSocket.bind(address)
        self.serverSocket.listen(5)
        self.liveStatus = "Alive"
        if not isinstance(self.role_instance,nd.DNS_node):
            # while True:
            try:                    
                # self.serverSocket.connect(core.DNS_addr)
                result = core.send_addr_to_dns(nd.domains_by_role[str(self.role_instance)],address)
                # if result: break
            except Exception as err:
                print(err)    

        # TODO find out if the connection to DNS must/can be closed
        # self.serverSocket.detach()

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
            if not self.role_instance.headers.get(decoded[0]):
                response = core.FAILED_REQ
                encoded = pickle.dumps(response)
                sended, _ = core.send_bytes_to(encoded,connection,False)
            else:
                handler = self.role_instance.headers.get(decoded[0])
                response = handler(decoded[1],connection,address)
                # encoded = pickle.dumps(response)
                # sended, _ = core.send_bytes_to(encoded,connection,False)
        except Exception as err:
            print(err) 
            response = core.FAILED_REQ
            encoded = pickle.dumps(response)
            sended, _ = core.send_bytes_to(encoded,connection,False)
                 
        finally:
            connection.close()

    # Socket Programming for Server 1 to 4 (it can be more)
    def serverProgram(self, chosenPort):
        print("Im ", chosenPort)
        serverPort = chosenPort
        serverIP = self.serverIpAddr
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serverSocket.bind((serverIP, serverPort))
        serverSocket.listen(5)
        liveStatus = "Alive"
        conn, address = serverSocket.accept()
        print(conn)
        while True:
            try:
                # print("Connection from: " + str(address))
                data = core.receive_data_from(conn)
                # Decode received data into UTF-8
                data = pickle.loads(data)
                # Convert decoded data into list
                print(data)
                data = eval(data)
                if (self.liveStatus == "Dead"):
                    # print("Im here")
                    continue
                # print(data)
                file1 = open("segment"+str(data[0])+".mp4", "rb")
                fileData = file1.read(100000000)
                conn.send(fileData)
                # print("Segment "+str(data[0]) +
                #       " sent by " + str(self.serverNumber))
                continue
            except Exception as e:
                # Block runs when all segments asked by client have been sent.
                # Do last minute programming here
                # print("Server "+str(self.serverNumber)+" list over")
                print(e)
                continue
        # print("Server not listening")
        # serverSocket.close()

    # Socket Programming for Server 5
    def closingServer(self, chosenPort):
        serverPort = chosenPort
        serverIP = self.serverIpAddr
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serverSocket.bind((serverIP, serverPort))
        serverSocket.listen(5)
        conn, address = serverSocket.accept()
        tempArray = []
        while True:
            try:
                # print("Connection from: " + str(address))
                # x1 is a boolean list that tells which servers are down.
                x1 = []
                for x in range(len(self.shutdown)):  # Loop to populate x1
                    if (self.shutdown[x] == True):
                        x1.append(0)
                        # self.shutdown[x] = False
                    else:
                        x1.append(1)
                if (tempArray == x1):  # If list is same as before, continue
                    continue
                else:  # If list different, send its contents.
                    x1 = str(x1)
                    x1 = x1.encode()
                    conn.send(x1)
            except Exception as e:
                # print("Server 5 connection over.")
                raise e  # Throws exception to try/except in runServer5 block
                break

# Function to carry out the finsihing tasks(updating shutdown array etc..) before a server is forecfully shutdown.

    def kill(self):
        self.liveStatus = "Dead"
        self.shutdown[self.serverNumber-1] = True

# Function to carry out the starting tasks(updating shutdown array etc..) before a server is forecfully woken up.
    def alive(self):
        self.liveStatus = "Alive"
        self.shutdown[self.serverNumber-1] = False


def main():
    # --------- Retrieve info from the terminal command ---------
    argSize = len(sys.argv)
    argList = sys.argv
    

    # Creating instances of Servers 
    if argList[1] == '0':
        Server0 = Server(0, argList[2])
        p0 = Server0.assign_role(nd.DNS_node,())
    elif argList[1] == '1':
        Server1 = Server(1, argList[2])
        p1 = Server1.assign_role(nd.Data_node,('data_nodes', None, False, 'songs'))
    elif argList[1] == '2':
        Server2 = Server(2, argList[2])
        p2 = Server2.assign_role(nd.Data_node,('data_nodes', None, True, 'songs'))
    elif argList[1] == '3':
        Server3 = Server(3, argList[2])
        p3 = Server3.assign_role(nd.Router_node,())
    elif argList[1] == '4':
        Server4 = Server(4, argList[2])
        p4 = Server4.assign_role(nd.Router_node,())

    if argList[1] == '0':
        p0.join()
    elif argList[1] == '1':
        p1.join()
    elif argList[1] == '2':
        p2.join()
    elif argList[1] == '3':
        p3.join()
    elif argList[1] == '4':
        p4.join()


    # Function to safely exit program.
    # def exitProgram():
    #     p1.terminate()
    #     p2.terminate()
    #     p3.terminate()
    #     p4.terminate()
    #     os._exit(os.EX_OK)

    # def output():
    #     while True:
    #         print("MultiServers")
    #         print("Server 1 at Port: " +
    #               str(PORT_NUMBERS[0]) + " Status: " + Server1.liveStatus + " To shutdown/wakeup enter 1")
    #         print("Server 2 at Port: " +
    #               str(PORT_NUMBERS[1]) + " Status: " + Server2.liveStatus + " To shutdown/wakeup enter 2")
    #         print("Server 3 at Port: " +
    #               str(PORT_NUMBERS[2]) + " Status: " + Server3.liveStatus + " To shutdown/wakeup enter 3")
    #         print("Server 4 at Port: " +
    #               str(PORT_NUMBERS[3]) + " Status: " + Server4.liveStatus + " To shutdown/wakeup enter 4")
    #         print("To quit, enter -1: ")
    #         val = int(input("\nEnter your Choice: "))
    #         if val == 1:
    #             if (Server1.liveStatus == "Alive"):
    #                 Server1.kill()
    #             else:
    #                 Server1.alive()
    #         elif val == 2:
    #             if (Server2.liveStatus == "Alive"):
    #                 Server2.kill()
    #             else:
    #                 Server2.alive()
    #         elif val == 3:
    #             if (Server3.liveStatus == "Alive"):
    #                 Server3.kill()
    #             else:
    #                 Server3.alive()
    #         elif val == 4:
    #             if (Server4.liveStatus == "Alive"):
    #                 Server4.kill()
    #             else:
    #                 Server4.alive()
    #         elif val == -1:
    #             exitProgram()
    #         else:
    #             print("Wrong input, try again..")
    #         os.system("clear")

    if argList[2] == '0':
        p0.join()
    elif argList[2] == '1':
        p1.join()
    elif argList[2] == '2':
        p2.join()
    elif argList[2] == '3':
        p3.join()
    elif argList[2] == '4':
        p4.join()



if __name__ == "__main__":
    main()
    # python3 server_class.py --status-interval 10 --num-of-servers 5 --file-name data.txt -server-ip 127.0.0.1 8888 8887 8886 8885 8884
