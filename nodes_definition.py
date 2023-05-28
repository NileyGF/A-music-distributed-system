"""Here goes the definions of the types of nodes and their role, according to the orientation.
An unique host can have more than one node, allowing it to have more than one role.
For instance, we must define a "data_base node", "order router"(presumibly the one waiting for orders to redirect them), 
and others.
"""
import database_controller
import core
import errors
import socket
import pickle
import os
import multiprocessing
# import threading
# TAIL = '!END!'

headers = { 'SSList':0, # Send Songs List 
            'RSList':0,#send_songs_tags_list, # Request Songs List
            'Rsong': 0, # Request song
            'SPList':0, # Send Providers List
            'Rchunk':0, # Request chunk
            'Schunk':0, # Send chunk
            'ACK':0,
            'RNSolve':0,# Request Name Solve 
            'SNSolve':0 # Send Name Solve
            }

class Router_node:
    def __init__(self, router_group_addr:str, reading_group_addr:str) -> None:
        self.providers_by_song = dict()  # update by time or by event
        self.songs_tags_list = list()     # update by time or by event

        self.__get_songs_tags_list()

    
    def __get_songs_tags_list(self):
        # fix to connect to a reader node and ask for it

        # change to conect to a reading node and ask for the list 
        self.songs_tags_list = database_controller.get_aviable_songs()
        return self.songs_tags_list
    
    def send_songs_tags_list(self,connection:socket.socket):
        data = database_controller.get_aviable_songs()
        h_d_t_list = tuple(["SSList",data,core.TAIL])
        pickled_data = pickle.dumps(h_d_t_list)

        result = core.send_bytes_to(pickled_data,connection,True)
        if result [0] == "OK":
            print("Songs Tags Sended: ",pickle.loads(result[1]))
            if result[0] == 'ACK' and result[1] == 'OK':
                return True, True
            return True, False
        return False, False
    
    def send_providers_list(self,connection:socket.socket,song_id:int):
        if self.providers_by_song.get(song_id):
            providers = self.providers_by_song[song_id]

class DNS_node:
    """DNS server node, with A records. An A record fields are:
        Label : Identifies the owner name of the resource being referenced by the record. It consists of the original parent name plus any additional labels separated by periods (.), ending with a period. For example, "example."
        Type  : Specifies the kind of information contained in the RDATA section of the record. Common values include A (for an IPv4 address), CNAME (for an alias), MX (for mail exchange servers), etc.
        Class : Indicates the type of database in which the RRset resides. There is only one current class, IN, and therefore the Class field is omitted from many RRs.
        TTL   : Time to live (how long the RR can be cached).Represents the number of seconds that a resolver cache can store the record before discarding it.
        Data  : The actual content of the record, typically consisting of an IP address, domain name, or other relevant identifier."""
    
    def __init__(self,dns_ip='127.0.0.1',dns_port=5383):
        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((dns_ip,dns_port)) 
        self.socket.listen(3)
        self.headers = { 'ACK': 0,
                         'RNSolve':0,# Request Name Solve 
                         'SNSolve':0 # Send Name Solve
            }
        p = multiprocessing.Process(target=self.run,args=())
        p.start()

        
    def run(self):
        client_n = 1
        try:
            while True:                
                conn, client_addr = self.socket.accept()                
                print('DNS CONNECTION: ',client_n, '. Client: ',client_addr)
                client_n += 1
                # queue = multiprocessing.Queue()
                # queue.put(dict())
                p = multiprocessing.Process(target=DNS_node._client_handler,args=(conn,client_addr))
                p.start()
                # p.join(waiting_time_ms/1000)
                # if p.is_alive():
                #     print("Waiting for response timed-out.")
                #     p.terminate()
                #     p.join()
                # if not queue.empty():
                #     rd = queue.get() 
                #     msg = rd.get('return')
        finally:
            self.socket.close()

    @staticmethod
    def _get_records():
        path = "dns_records"
        try:
            files = os.listdir(path)
            with open(os.path.join(path,files[0]),'rb') as f:
                data = pickle.load(f)
        except FileNotFoundError:
            print("DNS error. Records not found")
        return data
    
    @staticmethod
    def _add_record(labels:str,ttl:int,data):
        record = dict()
    
        record['labels'] = labels
        record['type'] = 'A'
        record['class'] = 'IN'
        record['ttl'] = ttl
        record['data'] = data

        try:
            rds = DNS_node._get_records()
            if not isinstance(rds,dict):
                rds = dict()
        except:
            rds = dict()

        rl = rds.get(labels)
        if rl is None:
            rds[labels] = [record]
        else: 
            rds[labels].append(record)

        path = "dns_records"        
        try:
            files = os.listdir(path)
            if not files or len(files) == 0:
                with open(os.path.join(path,labels),'wb') as f:
                    pickle.dump(rds,f)
            else:
                with open(os.path.join(path,files[0]),'wb') as f:
                    pickle.dump(rds,f)
        except FileNotFoundError:
            print("DNS error. Records not found")

        return record
    
    @staticmethod
    def _name_solve(domain):
        # domain_parts = self.domain.split('.')
        all_records = DNS_node._get_records()
        if not all_records:
            return None
        try:
            records = all_records[domain]
            datas = [r['data'] for r in records]
        except:
            # problems in the records for self.domain
            error_msg = "DNS error. Problems with record of "+domain+"."
            raise errors.Error(error_msg)

        to_encode = tuple(['SNSolve', datas, core.TAIL])
        return to_encode
    
    
    @staticmethod
    def _client_handler(connection:socket.socket,client_addr):
        try:
            while True:
                request = core.receive_data_from(connection)
                data = pickle.loads(request)
                if 'RNSolve' in data:
                    to_encode = DNS_node._name_solve(data[1])
                    response = core.send_bytes_to(pickle.dumps(to_encode),connection,False)

                elif 'ACK' in data:
                    print('successfully')
                    return 
                else:
                    error_msg = "Invalid DNS request: "+data[0]
                    raise errors.Error(error_msg)
                
        except Exception as err:
            print(err)
        finally:

            print('client handled.')
            connection.close()
