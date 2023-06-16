"""Here goes the definions of the types of nodes and their role, according to the orientation.
An unique host can have more than one node, allowing it to have more than one role.
For instance, we must define a "data_base node", "order router"(presumibly the one waiting for orders to redirect them), 
and others.
"""
import database_controller as dbc
import core as core
import errors as errors
import socket
import pickle
import os
import math
import random
import time
import multiprocessing

headers = { 'SSList':0,     # Send Songs List 
            'RSList':0,     # Request Songs List
            'Rsong': 0,     # Request song
            'SPList':0,     # Send Providers List
            'Rchunk':0,     # Request chunk
            'Schunk':0,     # Send chunk
            'RHSong':0,     # Request Have Song
            'SHSong':0,     # Send Have Song
            'ACK':0,
            'RNSolve':0,    # Request Name Solve 
            'SNSolve':0,    # Send Name Solve
            'AddRec' :0,    # Add Record | data: (labels, addr, ttl) 
            'NRServer':0,   # New Router Server
            'NDServer':0,   # New Data Server
            'ping'    :0,   # ping -_-  
            'echoreply':0,  # ping reply
            'FailedReq':0,  # Failed Request
            'ReqInit':0,    # Request Initialization Info
            'SolInit':0,    # Solved Initialization Info
            'ReqJRing':0,   # Request Join Ring
            'JRingAt':0,    # Join Ring At
            'FallenNode':0, # Fallen Node
            'Unbalance':0,  # Unbalanced Roles


            # 'ReqELECTION':0,# Request ELECTION
            # 'RecELECTION':0,# Received ELECTION
            # 'ELECTED':0,    # ELECTED (Election result)
            }


class Role_node():
    """base class for all roles"""
    def __init__(self,server_id=None):
        self.headers = {'ping':core.send_echo_replay}
    def __str__(self) -> str:
        return self.__class__.__name__

class Data_node(Role_node):
    def __init__(self,server_id=0, path='data_nodes', database_bin:bytes = None, begin_new_data_base:bool = False, raw_songs_path=None):
        self.id = server_id
        
        self.headers = {'ping'  :core.send_echo_replay,         # ping -_-  
                        'ReqInit':self.replicate_data,          # Request Initialization Info
                        'SolInit':0,    # Solved Initialization Info
                        'RSList':self.request_songs_list,       # Request Songs List
                        'Rsong' :self.request_song,             # Request song
                        'Rchunk':self.request_chunk,            # Request chunk
                        'RHSong':self.have_song,                # Request Have Song
                        'NSong' :self.add_song,                 # New Song
                        'DSong' :self.remove_song,              # Delete Song
                        'SynData':self.sync_data_center,        # Synchronize Data Center
                        }
        
        # path to read and save data from (must be on os format)
        self.path = path 
        # full path of the sqlite database file
        self.db_path = 'spotify_'+str(self.id)+'.db'
        self.db_path = os.path.join(self.path,self.db_path)

        if begin_new_data_base:
            # start new database and fill it with data from the songs in 'raw_songs_path' 
            # or leave it empty if 'raw_songs_path' is invalid
            dbc.create_db(self.db_path)
            dbc.Create_Songs_Chunks_tables(self.db_path)

            try:
                songs_list = dbc.songs_list_from_directory(raw_songs_path)
                dbc.Insert_songs(songs_list,self.db_path)
            except Exception as er:
                print(er)

        elif database_bin != None:
            # save the database from 'database_bin' into a file if it's a valid value
            with open(self.db_path,'wb') as f:
                f.write(database_bin)
        else: 
            raise Exception("The data server didn't receive any database. Initialize with a binary database or with the songs' path")

    def have_song(self,song_id:int,connection,address):
        query = "SELECT * from songs where id_S = "+str(song_id)
        # row = [id_S, title, artists, genre, duration_ms, chunk_slice]
        row = dbc.read_data(self.db_path, query)
        print(row)
        if row != None and len(row) > 0:
            encoded = pickle.dumps(tuple(['SHSong',True,core.TAIL]))
        else:
            encoded = pickle.dumps(tuple(['SHSong',False,core.TAIL]))

        state, _ = core.send_bytes_to(encoded,connection,False)
        if state == 'OK': 
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            try: 
                if 'ACK' in decoded:
                    return True
            except:
                pass
        return False

    def replicate_data(self,request_data,connection,address):
        # args = ( path='', database_bin:bytes = None, begin_new_data_base:bool = False, raw_songs_path=None )
        with open(self.db_path,'rb') as f:
            database_bin = f.read()

        args = (self.path, database_bin, False, None)
        encoded = pickle.dumps(tuple(['SolInit',args,core.TAIL]))

        state, _ = core.send_bytes_to(encoded,connection,False)
        if state == 'OK': 
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            try: 
                if 'ACK' in decoded:
                    return True
            except:
                pass
        return False

    def add_song(self,song_bin:bytes,connection,address):
        pass

    def remove_song(self,song_id:int,connection,address):
        pass

    def sync_data_center(self,request_data,connection,address):
        pass

    def request_songs_list(self,request_data,connection,address):
        if not self.have_data:
            return []
        self.songs_tags_list = dbc.get_aviable_songs(self.db_path)
        encoded = pickle.dumps(tuple(['SSList',self.songs_tags_list,core.TAIL]))
        state, _ = core.send_bytes_to(encoded,connection,False)
        if state == 'OK': 
            result = core.receive_data_from(connection,waiting_time_ms=3000,iter_n=30)
            decoded = pickle.loads(result)
            try: 
                if 'ACK' in decoded:
                    return True
            except:
                pass
        return False
        
    def request_song(self,song_id:int,connection,address):
        if not self.have_data:
            return None
        query = "SELECT * from songs where id_S = "+str(song_id)
        # row = [id_S, title, artists, genre, duration_ms, chunk_slice]
        row = dbc.read_data(self.db_path, query)
        row = row[0]
        print('song row: ',row)
        # duration_sec = duration_ms / 1000
        duration_sec = row[4] / 1000 
        number_of_chunks:float = duration_sec / row[5]
        number_of_chunks = math.ceil(number_of_chunks)

        chunks = dbc.get_n_chunks(0,song_id,number_of_chunks,self.db_path)
        print('chunks gotten')
        for ch in chunks:
            try:
                encoded = pickle.dumps(tuple(['Schunk',ch,core.TAIL]))
                state, _ = core.send_bytes_to(encoded,connection,False)
                if state == 'OK': 
                    result = core.receive_data_from(connection)
                    decoded = pickle.loads(result)
                    if 'ACK' in decoded:
                        continue
                return False
            except Exception as er:
                print(er)
                return False
        return True
    
    def request_chunk(self,request_data,connection,address):
        if not self.have_data:
            return False
        id_Song = int(request_data[0])
        ms = int(request_data[1])
        chunk = dbc.get_a_chunk(ms,id_Song,self.db_path) 
        try:
            encoded = pickle.dumps(tuple(['Schunk',chunk,core.TAIL]))
            state, _ = core.send_bytes_to(encoded,connection,False)
            if state == 'OK': 
                result = core.receive_data_from(connection)
                decoded = pickle.loads(result)
                if 'ACK' in decoded:
                    return True
            return False
        except Exception as er:
            print(er)
            return False

class Router_node(Role_node):
    class _providers:
        def __init__(self,address,type):
            self.address = address
            self.type = type
            self.used = 0
        def use(self):
            self.used +=1

    def __init__(self,server_id=None):
        self.headers = {'ping':core.send_echo_replay,           # ping -_-  
                        'RSList':self.send_songs_tags_list,    # Request Songs List
                        'Rsong': self.send_providers_list,      # Request song
                        'Rchunk':self.send_providers_list,      # Request chunk
                        }

        self.providers_by_song = dict()     # update by time or by event
        self.existing_providers = list()
        self.songs_tags_list = list()       # update by time or by event

    def __get_songs_tags_list(self):
        # connect to a data node and ask for it
        addrs = core.get_addr_from_dns("distpotify.data" )
        data_servers = []
        if addrs != None:
            for addr in addrs:
                # ip = addr.split(':')[0]
                # port = int(addr[1].split(':')[1])
                data_servers.append(addr)

        data_servers = set(data_servers)
        req = tuple(['RSList',None,core.TAIL])
        pickled_data = pickle.dumps(req)

        for ds in data_servers:
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            sock.connect(ds)

            core.send_bytes_to(pickled_data,sock,False)
            result = core.receive_data_from(sock,waiting_time_ms=3000,iter_n=33)
            decoded = pickle.loads(result) 
            if 'SSList' in decoded:
                break
        encoded = pickle.dumps(core.ACK_OK_tuple)
        state, _ = core.send_bytes_to(encoded,sock,False)
        # if state == 'OK': return True
        # return False
        if 'SSList' in decoded:
            self.songs_tags_list = decoded[1]
        else:
            self.songs_tags_list = None

        return self.songs_tags_list
    
    def __get_best_providers(self,song_id):
        # TODO self.__update_alive_providers()
        old_prov = self.providers_by_song.get(song_id)
        self.providers_by_song[song_id] = []
        if not old_prov:
            # no one have the song, go and ask DNS for the data servers
            addresses = core.get_addr_from_dns('distpotify.data')
            for data_server in addresses:
                try:
                    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                    sock.connect(data_server)
                    encoded = pickle.dumps(tuple(['RHSong',song_id,core.TAIL]))
                    state, _ = core.send_bytes_to(encoded,sock,False)
                    if state != 'OK':
                        continue
                    result = core.receive_data_from(sock)
                    decoded = pickle.loads(result)

                    pickled_data = pickle.dumps(core.ACK_OK_tuple)
                    state, _ = core.send_bytes_to(pickled_data,sock,False)
                    sock.close()

                    if state == 'OK' and decoded[1]:
                        #  data_server is a provider of the song
                        existed = False
                        for prov in self.existing_providers:
                            if prov.address == data_server:
                                # already knew that server
                                existed = True
                                self.providers_by_song[song_id] += [prov]
                        if not existed:
                            # did'n knew that server
                            new_prov = Router_node._providers(data_server,'data server')
                            self.existing_providers.append(new_prov)
                            self.providers_by_song[song_id] += [new_prov]
                except Exception as er:
                    print(er)
                    continue
            
        else:
            for prov in old_prov:
                # for every provider, if still exists (is connected) keep it
                if prov in self.existing_providers:
                    self.providers_by_song[song_id] += [prov]
        sampl = random.sample(self.providers_by_song[song_id],min(3,len(self.providers_by_song[song_id])))
        to_send =[]
        for prov in sampl:
            to_send.append(prov.address)
        return to_send
    
    def __update_alive_providers(self):
        pass

    def send_songs_tags_list(self,request_data,connection,address):
        data = self.__get_songs_tags_list()
        response = tuple(["SSList",data,core.TAIL])
        encoded = pickle.dumps(response)

        state = core.send_bytes_to(encoded,connection,False)
        
        if state [0] == "OK":
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            print("Songs Tags Sended ")
            if 'ACK' in decoded:
                return True
            
        return False
    
    def send_providers_list(self,song_id:int,connection,address):
        providers = self.__get_best_providers(song_id)

        response = tuple(['SPList',providers,core.TAIL])
        encoded = pickle.dumps(response)

        state = core.send_bytes_to(encoded,connection,False)
        if state [0] == "OK":
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            print("Songs Tags Sended ")
            if 'ACK' in decoded:
                return True
            
        return False

class DNS_node(Role_node):
    """DNS server node, with A records. An A record fields are:
        Label : Identifies the owner name of the resource being referenced by the record. It consists of the original parent name plus any additional labels separated by periods (.), ending with a period. For example, "example."
        Type  : Specifies the kind of information contained in the RDATA section of the record. Common values include A (for an IPv4 address), CNAME (for an alias), MX (for mail exchange servers), etc.
        Class : Indicates the type of database in which the RRset resides. There is only one current class, IN, and therefore the Class field is omitted from many RRs.
        TTL   : Time to live (how long the RR can be cached).Represents the number of seconds that a resolver cache can store the record before discarding it.
        Data  : The actual content of the record, typically consisting of an IP address, domain name, or other relevant identifier."""
    
    def __init__(self,server_id=None): 
        self.headers = {'ping':core.send_echo_replay,   # ping -_-  
                        'RNSolve':self.name_solve,      # Request Name Solve | data: domain_to_solve
                        'AddRec' :self.add_record,      # Add Record | data: (labels, addr, ttl) 
            }
        multiprocessing.set_start_method('fork', force=True)
        p = multiprocessing.Process(target=self.update_using_ttl)
        p.start()

    def _get_records(self):
        path = "dns_records"
        try:
            files = os.listdir(path)
            with open(os.path.join(path,files[0]),'rb') as f:
                data = pickle.load(f)
        except FileNotFoundError:
            print("DNS error. Records not found")
        return data

    def add_record(self,request:tuple,connection,address):
        labels, addr, ttl = request
        record = dict()
    
        record['labels'] = labels
        record['type'] = 'A'
        record['class'] = 'IN'
        record['ttl'] = ttl
        record['data'] = addr
        record['start_time'] = int(time.time())

        try:
            rds = self._get_records()
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
                with open(os.path.join(path,'rcrds.bin'),'wb') as f:
                    pickle.dump(rds,f)
            else: # TODO change files[0]
                with open(os.path.join(path,files[0]),'wb') as f:
                    pickle.dump(rds,f)
        except FileNotFoundError:
            print("DNS error. Records not found")
            return False

        encoded = pickle.dumps(core.ACK_OK_tuple)
        state, _ = core.send_bytes_to(encoded,connection,False)
        if state == 'OK': return True
        return False

    def name_solve(self,domain:str,connection,address):
        all_records = self._get_records()
        if not all_records:
            return False
        try:
            records = all_records[domain]
            datas = [r['data'] for r in records]
        except:
            # problems in the records for self.domain
            error_msg = "DNS error. Problems with record of "+domain+"."
            raise errors.Error(error_msg)
        datas = self.__alive_from(datas)
        response = tuple(['SNSolve', datas, core.TAIL])
        encoded = pickle.dumps(response)
        state, _ = core.send_bytes_to(encoded,connection,False)
        if state == 'OK': 
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            if 'ACK' in decoded:
                return True
        return False
    
    def update_using_ttl(self):
        while True:
            time.sleep(15)
            try:
                data = self._get_records()
            except:
                continue
            for label in data:
                for rec in data[label]:
                    ping = core.send_ping_to(rec['data'])
                    if ping:
                        print('ping to ',rec['data'],'success')
                        if time.time() - rec['start_time'] >= rec['ttl']:
                            rec['start_time'] = time.time()
                            print('Updated TTL for ', rec['data'])
                    else: 
                        print('ping to ',rec['data'],'failed')
                        data[label].remove(rec) # TODO: test remove() method

            path = "dns_records"        
            try:
                files = os.listdir(path)
                if not files or len(files) == 0:
                    with open(os.path.join(path,'rcrds.bin'),'wb') as f:
                        pickle.dump(data,f)
                else: # TODO change files[0]
                    with open(os.path.join(path,files[0]),'wb') as f:
                        pickle.dump(data,f)
            except FileNotFoundError:
                print("DNS error. Records not found")
                return False
        
    def __alive_from(self,addrss):
        result = []
        for addr in addrss:
            if core.send_ping_to(addr):
                result.append(addr)
        return result


ports_by_role = { 'Role_node'  : core.NONE_PORT,
                  'Data_node'  : core.DATA_PORT,
                  'Router_node': core.ROUTER_PORT,
                  'DNS_node'   : core.DNS_PORT}

domains_by_role = {'Role_node'  : 'distpotify.no_role',
                   'Data_node'  : 'distpotify.data',
                   'Router_node': 'distpotify.router',
                   'DNS_node'   : ''}