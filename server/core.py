import socket
import multiprocessing
import time
import pickle
import errors

# Addresses
DNS_addr = ('172.20.0.2', 5353)
bytes_mult = 2

DATA_PORT = 7777
ROUTER_PORT = 8888
DNS_PORT = 5353
RING_PORT = 8000
CHORD_PORT = 7000
NONE_PORT = 6789
# Messages
TAIL = '!END!'
ACK_OK_tuple = tuple(["ACK","OK",TAIL])
PING_tuple = tuple(['ping',None,TAIL])
ECHO_REPLAY = tuple(['echoreplay',None,TAIL])
FAILED_REQ = tuple(['FailedReq',None,TAIL])
ANSI_colors = {'blue': '\033[94m',
               'violet': '\033[95m',
               'cyan': '\033[96m',
               'green': '\033[92m',
               'yellow': '\033[93m',
               'red': '\033[91m',
               'gray': '\033[90',
               'default': '\033[0m',
               }


def send_bytes_to(payload: bytes, connection: socket.socket, wait_for_response: bool = True, attempts: int = 3, time_to_retry_ms: int = 3000, bytes_flow: int = bytes_mult*1024, verbose=1):
    # number of sending attempts while a disconnection error pops up
    if attempts < 0:
        attempts = 3
    ok = False
    i = 0
    while i < attempts:
        try:
            total_sent = 0
            start = 0
            while start < len(payload):

                # Calculate remaining length based on payload size and current chunk size
                end = min(len(payload), start + bytes_flow)

                # Send chunk and keep track of how much was actually sent
                sent = connection.send(payload[start: end])
                total_sent += sent
                start += sent
                if verbose > 0:
                    print("\nSent %d/%d bytes" % (total_sent, len(payload)), connection)
            if verbose == 0:
                print("\nFinished. Sent %d/%d bytes" % (total_sent, len(payload)), connection)
            ok = True
            if verbose > 1:
                print("Sent : ",pickle.loads(payload))
            break
        except socket.error as error:
            i += 1
            print(error, "Error while sending data. Starting over for ", i,
                  " time after resting for ", time_to_retry_ms/1000, "sec.")  # remove
            time.sleep(time_to_retry_ms/1000)  # find a better way

    # If data was sended correctly and waiting for an ACK, receive it and return the proper label and data
    if ok:
        if wait_for_response:
            response = receive_data_from(connection, bytes_flow, 5000, 3,verbose=verbose)
            return "OK", response
        else:
            return "OK", None
    else:
        return "Connection Lost Error!", None

def receive_data_from(connection: socket.socket, bytes_flow: int = bytes_mult*1024, waiting_time_ms: int = 5000, iter_n: int = 5, verbose=0):
    def _receive_handler(queue: multiprocessing.Queue, connection: socket.socket, bytes_flow: int = bytes_mult*1024):
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
        multiprocessing.set_start_method('fork', force=True)
        p = multiprocessing.Process(
            target=_receive_handler, args=(queue, connection, bytes_flow))
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
                    break
                else:
                    if verbose:
                        print(decode)
            except:
                pass
        else:
            i += 1

    print('Failed iter: ', i, '. Received data = ', len(data))
    if verbose > 0:
        print( ' \tFrom: ',connection)
    if len(data) > 0:
        if verbose > 1:
            try: print(pickle.loads(data))
            except: pass

    return data

def get_addr_from_dns(domain:str):
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    sock.connect(DNS_addr)
    h_d_t_list = tuple(["RNSolve",domain,TAIL])
    pickled_data = pickle.dumps(h_d_t_list)
    send_bytes_to(pickled_data,sock,False,verbose=2)
    result = receive_data_from(sock,waiting_time_ms=5000,iter_n=8,verbose=2)
    if not result or len(result) == 0:
        raise errors.ConnectionError("DNS unresponsive.")
    result = pickle.loads(result)
    
    pickled_data = pickle.dumps(ACK_OK_tuple)
    send_bytes_to(pickled_data,sock,False)
    sock.close()
    
    if result[0] == 'SNSolve':
        return result[1]

def send_addr_to_dns(domain:str, address:tuple, ttl:int=60):

    # address = ip + ':'+str(port)
    data = tuple([domain, address, ttl])
    messag = tuple(['AddRec',data,TAIL])
    encoded = pickle.dumps(messag) 

    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    sock.connect(DNS_addr)

    state, _ = send_bytes_to(encoded,sock,False)
    result = receive_data_from(sock,verbose=2)
    decoded = pickle.loads(result)
    try: 
        if decoded[0] == 'ACK' and decoded[1] == 'OK':
            print('DNS added record success')
            return True
    except:
        pass
    return False
    
def send_ping_to(address:tuple,data=None):
    """Send a ping message to address (ip, port)"""
    try: 
        messag = tuple([PING_tuple[0],data,PING_tuple[2]])
        pickled_data = pickle.dumps(messag)
        # ip = address.split(':')[0]
        # port = int(address[1].split(':')[1])
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        sock.connect(address)
    
        send_bytes_to(pickled_data,sock,False)
        result = receive_data_from(sock,waiting_time_ms=3000,iter_n=3)
        decoded = pickle.loads(result)
        if 'echoreplay' in decoded:
            sock.close()
            return True
    except Exception as err :
        print('ping error: ',err)
    sock.close()
    return False

def send_echo_replay(ping_data,connection:socket.socket,address):
    """answer a ping message"""
    pickled_data = pickle.dumps(ECHO_REPLAY)
    state, _ = send_bytes_to(pickled_data,connection,False)
    if state == 'OK': 
        return True
    return False


