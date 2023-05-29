import socket
import multiprocessing
import time
import pickle

TAIL = '!END!'
DNS_addr = ('127.0.0.1',5383)
LEADER_PORT = 8989

def send_bytes_to(payload:bytes,connection:socket.socket,wait_for_response:bool=True,attempts:int=3,time_to_retry_ms:int=1000,bytes_flow:int=1500, timeout=10):
    # number of sending attempts while a disconnection error pops up
    if attempts < 0: attempts = 3
    ok = False
    i = 0
    while i < attempts:
        try:
            total_sent = 0
            start = 0
            while start < len(payload):
                
                # Calculate remaining length based on payload size and current chunk size
                end = min( len(payload), start + bytes_flow ) 
                    
                # Send chunk and keep track of how much was actually sent
                sent = connection.send(payload[start : end])
                total_sent += sent
                start += sent
                print("\nSent %d/%d bytes" % (total_sent, len(payload)))
            ok = True
            break
        except socket.error as error:
            i +=1
            print(error, "Error while sending data. Starting over for ",i," time after resting for ",time_to_retry_ms/1000,"sec.") # remove
            time.sleep(time_to_retry_ms/1000) # find a better way
    
    # If data was sended correctly and waiting for an ACk, receive it and return the proper label and data
    if ok:
        if wait_for_response:
            response = receive_data_from(connection,bytes_flow,5000,3)
            return "OK", response
        else:   
            "OK", None
    else:
        return "Connection Lost Error!", None

def receive_data_from(connection:socket.socket,bytes_flow:int=1024,waiting_time_ms:int=2500,iter_n:int=5):
    def _receive_handler(queue:multiprocessing.Queue,connection:socket.socket,bytes_flow:int=1024):
        # rd = queue.get() # return dictionary
        # rd['forced'] = 'AHHHHHHHH!!!!!!!!!!!!!!!'
        # queue.put(rd)
        rd = queue.get() 
        msg = connection.recv(bytes_flow)
        rd['return'] = msg
        queue.put(rd)
    
    data = bytes()
    i = 0
    msg = None
    while i < iter_n:
        
        queue = multiprocessing.Queue()
        queue.put(dict())
        p = multiprocessing.Process(target=_receive_handler,args=(queue,connection,bytes_flow))
        p.start()
        p.join(waiting_time_ms/1000)
        if p.is_alive():
            print("Waiting for response timed-out.")
            p.terminate()
            p.join()
        if not queue.empty():
            rd = queue.get()
            msg = rd.get('return')
           
        if msg != None:
            data = data + msg
            try:
                decode = pickle.loads(data)
                if TAIL in decode:
                    print('tail reached')
                    break
                else: print(decode)
            except:
                pass
        else: i+=1
        
    print('Failed iter: ', i, '. Received data = ', len(data))
    return data
