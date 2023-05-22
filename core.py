import socket
import threading
import time
import pickle

def send_data_to(Info:tuple,connection:socket.socket,wait_for_response:bool=True,attempts:int=3,time_to_retry_ms:int=1000,bytes_flow:int=1024):
    i = 0
    if attempts < 0: attempts = 3
    send = []
    for item in Info:
        item:bytes
        if len(item) <= bytes_flow:
            send.append(item)
        else:
            for i in range(0,len(item),bytes_flow):
                send.append(item[i:min(i+bytes_flow+1,len(item))])
    n_s = len(send)
    ok = False
    while i < attempts:
        try:
            for i in range(n_s):
                connection.send(send[i])
            ok = True
            break
        except socket.error as error:
            print(error) # remove
            i +=1
            time.sleep(time_to_retry_ms/1000) # find a better way
    if ok:
        if wait_for_response:
            response = receive_data_from(connection,bytes_flow)
            return "OK", response
        else:   # Acknowledgement
            "OK", None
    else:
        return "Connection Lost Error!"
    
def receive_data_from(connection:socket.socket,bytes_flow:int=1024):
    data = []
    while True:
        msg = connection.recv(bytes_flow)
        try:
            decode = pickle.loads(msg)
            if decode == '!END!':
                break
        except:
            pass

        data.append(msg)
    return data