from socket import *
import sys
import time
import multiprocessing
import subprocess
import math
import os
from os import path
from stat import *  # ST_SIZE etc
import threading
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
        self.role_instance = nd.Role_node()
        queue = multiprocessing.Queue()
        queue.put(dict())
        self.accept_proccess = multiprocessing.Process(target=self.init_socket, args=(queue))
        self.accept_proccess.start()
        # print("Constructing server...")

    def init_socket(self,queue):
        self.serverSocket = socket(AF_INET, SOCK_STREAM)
        self.serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.serverSocket.bind((self.serverIpAddr, nd.ports_by_role[str(self.role_instance)]))
        self.serverSocket.listen(5)
        self.liveStatus = "Alive"
        proccesses = []
        try:
            while True:
                
                conn, address = self.serverSocket.accept()
                print('CONNECTED: ',conn)
                multiprocessing.set_start_method('fork', force=True)
                p = multiprocessing.Process(
                    target=self.attend_connection, args=(conn, address))
                proccesses.append(p)
                p.start()
        finally:
            self.serverSocket.close()
            for p in proccesses:
                if p.is_alive():
                    p.terminate()
                    p.join()
        
    def assign_role(self, role:nd.Role_node,args:list):
        self.role_instance = role(*args)
        # TODO update to DNS
        if self.accept_proccess.is_alive():
            self.accept_proccess.terminate()
            self.accept_proccess.join()
        self.accept_proccess.start()

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
        except:
            pass        
        
        connection.close()
        
    # Socket Programming for Server 1 to 4 (it can be more)
    def serverProgram(self, chosenPort):
        print("Im ", chosenPort)
        serverPort = chosenPort
        serverIP = self.serverIpAddr
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
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
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
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
    # argSize = len(sys.argv)
    # argList = sys.argv
    # print(argSize, argList)
    argList = ['server_class.py', '--status-interval', '10', '--num-of-servers', '5',
               '--file-name', 'data.txt', '-server-ip', '0.0.0.0', '8888', '8887', '8886', '8885', '8884']
    argSize = 14
    # --------- Constants ---------
    STATUS_INTERVAL = int(argList[2])
    NUM_OF_SERVERS = int(argList[4])
    PORT_NUMBERS = []
    FILE_NAME = argList[6]
    SERVER_IP = argList[8]
    # PORT_NUMBERS = [8888, 8883, 8884, 8885, 8886]

    # --------- Populating PORT_NUMBERS with 'n' number of ports ---------
    for n in range(9, argSize):
        port = int(argList[n])
        PORT_NUMBERS.append(port)

    # Creating 5 instances of Servers with args as splitSize and serverNumber and common IP Address
    Server1 = Server(1, SERVER_IP)
    Server2 = Server(2, SERVER_IP)
    Server3 = Server(3, SERVER_IP)
    Server4 = Server(4, SERVER_IP)
    Server5 = Server(5, SERVER_IP)

    # Server 1 and 2 are responsible of DB updates. (Ask to Niley)

    # Function to safely exit program.
    def exitProgram():
        p1.terminate()
        p2.terminate()
        p3.terminate()
        p4.terminate()
        os._exit(os.EX_OK)

    def output():
        while True:
            print("MultiServers")
            print("Server 1 at Port: " +
                  str(PORT_NUMBERS[0]) + " Status: " + Server1.liveStatus + " To shutdown/wakeup enter 1")
            print("Server 2 at Port: " +
                  str(PORT_NUMBERS[1]) + " Status: " + Server2.liveStatus + " To shutdown/wakeup enter 2")
            print("Server 3 at Port: " +
                  str(PORT_NUMBERS[2]) + " Status: " + Server3.liveStatus + " To shutdown/wakeup enter 3")
            print("Server 4 at Port: " +
                  str(PORT_NUMBERS[3]) + " Status: " + Server4.liveStatus + " To shutdown/wakeup enter 4")
            print("To quit, enter -1: ")
            val = int(input("\nEnter your Choice: "))
            if val == 1:
                if (Server1.liveStatus == "Alive"):
                    Server1.kill()
                else:
                    Server1.alive()
            elif val == 2:
                if (Server2.liveStatus == "Alive"):
                    Server2.kill()
                else:
                    Server2.alive()
            elif val == 3:
                if (Server3.liveStatus == "Alive"):
                    Server3.kill()
                else:
                    Server3.alive()
            elif val == 4:
                if (Server4.liveStatus == "Alive"):
                    Server4.kill()
                else:
                    Server4.alive()
            elif val == -1:
                exitProgram()
            else:
                print("Wrong input, try again..")
            os.system("clear")

    # 4 processes and 2 thread created.
    p1 = multiprocessing.Process(target=runServer, args=(Server1, PORT_NUMBERS[0]))
    p2 = multiprocessing.Process(target=runServer, args=(Server2, PORT_NUMBERS[1]))
    p3 = multiprocessing.Process(target=runServer, args=(Server3, PORT_NUMBERS[2]))
    p4 = multiprocessing.Process(target=runServer, args=(Server4, PORT_NUMBERS[3]))
    t1 = threading.Thread(target=runServer5)
    t2 = threading.Thread(target=output)

    p1.start()
    time.sleep(0.04)
    p2.start()
    time.sleep(0.04)
    p3.start()
    time.sleep(0.04)
    p4.start()
    time.sleep(0.04)
    t1.start()
    time.sleep(0.04)
    t2.start()

    p1.join()
    p2.join()
    p3.join()
    p4.join()
    t1.join()
    t2.join()

    # Function to create Server 1


def runServer(server, port):
    server.serverProgram(port)

    # Function to create Server 2 only.
    # def runServer2():
    #     main.Server2.serverProgram(PORT_NUMBERS[1])

    # # Function to create Server 3 only.
    # def runServer3():
    #     Server3.serverProgram(PORT_NUMBERS[2])

    # # Function to create Server 4 only.
    # def runServer4():
    #     Server4.serverProgram(PORT_NUMBERS[3])


def runServer5(Server5, PORT_NUMBERS):
    try:
        Server5.closingServer(PORT_NUMBERS[4])
    except Exception as e:
        main.exitProgram()


# Driver code
if __name__ == "__main__":
    main()
    # python3 server_class.py --status-interval 10 --num-of-servers 5 --file-name data.txt -server-ip 127.0.0.1 8888 8887 8886 8885 8884
