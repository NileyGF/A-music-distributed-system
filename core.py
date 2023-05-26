import socket
import multiprocessing
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

def sender_3th(payload:bytes,connection:socket.socket,bytes_flow:int=1500, timeout=10):
    # Loop through chunks of data to send
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
        # rd = multiprocessing.Value('return_dict',dict())
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
                if '!END!' in decode:
                    print('tail reached')
                    break
                else: print(decode)
            except:
                pass
        else: i+=1
        
    print('failed iter: ', i, '. data = ', len(data))
    return data
