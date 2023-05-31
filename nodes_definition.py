"""Here goes the definions of the types of nodes and their role, according to the orientation.
An unique host can have more than one node, allowing it to have more than one role.
For instance, we must define a "data_base node", "order router"(presumibly the one waiting for orders to redirect them), 
and others.
"""
import database_controller as dbc
import core
import server_class as serv
import errors
import socket
import pickle
import os
import math
import time
import multiprocessing

headers = { 'SSList':0,     # Send Songs List 
            'RSList':0,     # Request Songs List
            'Rsong': 0,     # Request song
            'SPList':0,     # Send Providers List
            'Rchunk':0,     # Request chunk
            'Schunk':0,     # Send chunk
            'ACK':0,
            'RNSolve':0,    # Request Name Solve 
            'SNSolve':0,    # Send Name Solve
            'AddRec' :0,    # Add Record | data: (labels, addr, ttl) 
            'NRServer':0,   # New Router Server
            'NDServer':0,   # New Data Server
            'ping'    :0,   # ping -_-  
            'echoreply':0,  # ping reply
            'FailReq':0,    # Failed Request
            # ''
            }


class Data_node(serv.Server):
    def __init__(self, id, ipAddr, path, database_bin:bytes = None, begin_new_data_base:bool = False, raw_songs_path=None, state:int=0):
        super().__init__(id, ipAddr)
        self.headers = {'ping':core.send_echo_replay,       # ping -_-  
                        'RSList':self.request_songs_list,   # Request Songs List
                        'Rsong': self.request_song,         # Request song
                        'Rchunk':self.request_chunk,        # Request chunk
                        'NSong':self.add_song,              # New Song
                        'DSong':self.remove_song,           # Delete Song
                        'SynData':self.sync_data_center,    # Synchronize Data Center
                        }
        # path to read and save data from (must be on os format)
        self.path = path 
        # full path of the sqlite database file
        self.db_path = 'spotify_'+str(self.id)+'.db'
        self.db_path = os.path.join(self.path,self.db_path)
        
        self.state = state
        self.have_data = False

        if begin_new_data_base:
            # start new database and fill it with data from the songs in 'raw_songs_path' 
            # or leave it empty if 'raw_songs_path' is invalid
            dbc.create_db(self.db_path)
            dbc.Create_Songs_Chunks_tables(self.db_path)

            try:
                songs_list = dbc.songs_list_from_directory(raw_songs_path)
                dbc.Insert_songs(songs_list,self.db_path)
                self.have_data = True
            except Exception as er:
                print(er)
        else:
            # save the database from 'database_bin' into a file if it's a valid value
            if database_bin != None:
                with open(self.db_path,'wb') as f:
                    f.write(database_bin)
                    self.have_data = True
    
    def add_song(self,song_bin:bytes):
        pass

    def remove_song(self,song_id:int):
        pass

    def sync_data_center(self,request):
        pass

    def request_songs_list(self,request):
        if not self.have_data:
            return []
        self.songs_tags_list = dbc.get_aviable_songs(self.db_path)
        return self.songs_tags_list
        
    def request_song(self,request):
        if not self.have_data:
            return None
        id_Song = int(request[1])
        query = "SELECT * from songs where id_S = "+str(id_Song)
        # row = [id_S, title, artists, genre, duration_ms, chunk_slice]
        row = dbc.read_data(self.db_path, query)
        # duration_sec = duration_ms / 1000
        duration_sec = row[4] / 1000 
        number_of_chunks:float = duration_sec / row[5]
        number_of_chunks = math.ceil(number_of_chunks)
        chunks = dbc.get_n_chunks(0,id_Song,number_of_chunks)
        return chunks
    
    def request_chunk(self,request):
        if not self.have_data:
            return None
        id_Song = int(request[1][0])
        ms = int(request[1][1])
        return dbc.get_a_chunk(ms,id_Song) 

class Router_node(serv.Server):
    def __init__(self, id, ipAddr):
        super().__init__(id, ipAddr)
        self.headers = {'ping':core.send_echo_replay,           # ping -_-  
                        'RSList':self.send_songs_tags_list,    # Request Songs List
                        'Rsong': self.send_providers_list,      # Request song
                        'Rchunk':self.send_providers_list,      # Request chunk
                        }
        addrs = core.get_addr_from_dns("distpotify.router.leader" )

        # now connect to "distpotify.router.leader" 
        # leader_addr = (result[1],core.LEADER_PORT)
        # sock.connect(leader_addr)


        self.providers_by_song = dict()     # update by time or by event
        self.songs_tags_list = list()       # update by time or by event

        self.__get_songs_tags_list()

    
    def __get_songs_tags_list(self):
        # connect to a data node and ask for it
        addrs = core.get_addr_from_dns("distpotify.data" )
        data_servers = []
        if addrs != None:
            for addr in addrs:
                ip = addr.split(':')[0]
                port = int(addr[1].split(':')[1])
                data_servers.append((ip,port,addr))
        data_servers = set(data_servers)
        req = tuple(['RSList',None,core.TAIL])
        pickled_data = pickle.dumps(req)

        for ds in data_servers:
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            sock.connect((ds[0],ds[1]))

            core.send_bytes_to(pickled_data,sock,False)
            result = core.receive_data_from(sock,waiting_time_ms=3000,iter_n=3)
            decoded = pickle.loads(result) 
            if 'SSList' in decoded:
                break
        if 'SSList' in decoded:
            self.songs_tags_list = decoded[1]
        else:
            self.songs_tags_list = None

        return self.songs_tags_list
    
    def send_songs_tags_list(self,connection:socket.socket):
        data = self.__get_songs_tags_list()
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

class DNS_node(serv.Server):
    """DNS server node, with A records. An A record fields are:
        Label : Identifies the owner name of the resource being referenced by the record. It consists of the original parent name plus any additional labels separated by periods (.), ending with a period. For example, "example."
        Type  : Specifies the kind of information contained in the RDATA section of the record. Common values include A (for an IPv4 address), CNAME (for an alias), MX (for mail exchange servers), etc.
        Class : Indicates the type of database in which the RRset resides. There is only one current class, IN, and therefore the Class field is omitted from many RRs.
        TTL   : Time to live (how long the RR can be cached).Represents the number of seconds that a resolver cache can store the record before discarding it.
        Data  : The actual content of the record, typically consisting of an IP address, domain name, or other relevant identifier."""
    
    def __init__(self,id,dns_ip=core.DNS_addr[0],dns_port=core.DNS_addr[1]):
        super().__init__(id, dns_ip)

        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((dns_ip,dns_port)) 
        self.socket.listen(3)
        self.headers = {'ping':core.send_echo_replay,   # ping -_-  
                        'RNSolve':self._name_solve,     # Request Name Solve | data: domain_to_solve
                        # 'SNSolve':0,                    # Send Name Solve
                        'AddRec' :0,                    # Add Record | data: (labels, addr, ttl) 
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
                p = multiprocessing.Process(target=self._client_handler,args=(conn,client_addr))
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

    # @staticmethod
    def _get_records(self):
        path = "dns_records"
        try:
            files = os.listdir(path)
            with open(os.path.join(path,files[0]),'rb') as f:
                data = pickle.load(f)
        except FileNotFoundError:
            print("DNS error. Records not found")
        return data
    
    # @staticmethod
    def _add_record(self,request:tuple):
        labels, addr, ttl = request
        record = dict()
    
        record['labels'] = labels
        record['type'] = 'A'
        record['class'] = 'IN'
        record['ttl'] = ttl
        record['data'] = addr
        record['start_time'] = int(time.time())

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
    
    # @staticmethod
    def _name_solve(self,request:str):
        # domain_parts = self.domain.split('.')
        domain = request
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
    
    # @staticmethod
    def _client_handler(self,connection:socket.socket,client_addr):
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

    def update_using_ttl():
        pass
