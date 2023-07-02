"""Here goes the definions of the types of nodes and their role, according to the orientation.
An unique host can have more than one node, allowing it to have more than one role.
For instance, we must define a "data_base node", "order router"(presumibly the one waiting for orders to redirect them), 
and others.
"""
import database_controller as dbc
import core as core
import errors as errors
import hash_table
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
            'ReportNext':0, # Report to your next in ring
            'FixRing':0,    # Fix Ring
            }


class Role_node():
    """base class for all roles"""
    str_rep = 'Role_node'
    def __init__(self,server_id=None):
        self.headers = {'ping':core.send_echo_replay}
    def __str__(self) -> str:
        return self.__class__.__name__

class Data_node(Role_node):
    """Data base manager"""
    str_rep = 'Data_node'
    def __init__(self, server_ip:str, path='data_nodes', raw_songs_path=None):
        self.chord = hash_table.Node(server_ip,core.CHORD_PORT)
        
        self.headers = {'ping'  :core.send_echo_replay,         # ping -_-  
                        # 'ReqInit':self.replicate_data,          # Request Initialization Info
                        # 'SolInit':0,    # Solved Initialization Info
                        'RSList':self.request_songs_list,       # Request Songs List
                        'Rsong' :self.request_song,             # Request song
                        'Rchunk':self.request_chunk,            # Request chunk
                        'RHSong':self.have_song,                # Request Have Song
                        # 'NSong' :self.add_song,                 # New Song
                        # 'DSong' :self.remove_song,              # Delete Song
                        # 'SynData':self.sync_data_center,        # Synchronize Data Center
                        }
        self.headers = dict(list(self.headers.items()) + list(self.chord.headers.items()))
        # print(self.headers)
        
        # path to read and save data from (must be on os format)
        self.path = path 
        # full path of the sqlite database file
        self.db_path = 'spotify_'+str(self.chord.id)+'.db'
        self.db_path = os.path.join(self.path,self.db_path)

        
        # start new database 
        dbc.create_db(self.db_path)
        dbc.Create_Songs_Chunks_tables(self.db_path)

        try:
            # attemp to fill it with data from the songs in 'raw_songs_path' 
            # or leave it empty if 'raw_songs_path' is invalid
            songs_list = dbc.songs_list_from_directory(raw_songs_path)
            dbc.Insert_songs(songs_list,self.db_path)
        except Exception as er:
            print(er)
        
        self.chord.data_base = self.db_path
        multiprocessing.set_start_method('fork', force=True)
        chord_process = multiprocessing.Process(target=self.chord_handler)
        chord_process.start()
        try:
            dbs = core.get_addr_from_dns("distpotify.data")
            if dbs != None:
                if len(dbs) > 0:
                    self.chord.join((dbs[0][0],core.CHORD_PORT))
                else:
                    print("CREATING CHORD RING")
                    self.chord.predecessor[0] = (self.chord.id, (self.chord.ip,self.chord.port))
                    self.chord.successor[0] = (self.chord.id, (self.chord.ip,self.chord.port))
                    self.chord.finger_table[0][1] = (self.chord.id, (self.chord.ip,self.chord.port))

        except:
            raise Exception("Can't join hash table")
            # raise Exception("The data server didn't receive any database. Initialize with a binary database or with the songs' path")

    def chord_handler(self):
        print(core.ANSI_colors['cyan'])
        self.chordSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chordSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        address = (self.chord.ip, core.CHORD_PORT)
        self.chordSocket.bind(address)
        print(address)
        self.chordSocket.listen(5)
        print(core.ANSI_colors['default'])

        processes = []
        try:
            while True:                
                conn, address = self.chordSocket.accept()
                print('CONNECTED: ',address)
                multiprocessing.set_start_method('fork', force=True)
                p = multiprocessing.Process(target=self.chord_connection, args=(conn, address))
                processes.append(p)
                p.start()
        finally:
            self.chordSocket.close()
            for p in processes:
                if p.is_alive():
                    p.terminate()
                    p.join()
    
    def chord_connection(self,connection:socket,address):
        print(core.ANSI_colors['green'])
        received = core.receive_data_from(connection,waiting_time_ms=3000,iter_n=5,verbose=False)

        try:
            decoded = pickle.loads(received)
            # check if it is a server action
            if self.chord.headers.get(decoded[0]):
                handler = self.chord.headers.get(decoded[0])
                response = handler(decoded[1],connection,address)
            # else, send FAILED REQUEST
            else:
                response = core.FAILED_REQ
                encoded = pickle.dumps(response)
                core.send_bytes_to(encoded,connection,False)


        except Exception as err:
            print(err, "FAILED REQ") 
            response = core.FAILED_REQ
            encoded = pickle.dumps(response)
            core.send_bytes_to(encoded,connection,False)
                 
        finally:
            print(core.ANSI_colors['default'])
            connection.close()
        
    def have_song(self,song_id:int,connection,address):
        query = "SELECT * from songs where id_S = "+str(song_id)
        # row = [id_S, title, artists, genre, duration_ms, chunk_slice]
        row = dbc.read_data(self.db_path, query)
        row = row[0]
        # print(row)
        have_all_chunks = False

        if row != None and len(row) > 0:
            have_tags = True
            duration_sec = row[4] / 1000 
            number_of_chunks:float = duration_sec / row[5]
            number_of_chunks = math.ceil(number_of_chunks)
            query = "SELECT * from chunks where id_S = "+str(song_id)
            chunks = dbc.read_data(self.db_path, query)
            have_all_chunks = len(chunks) == number_of_chunks
        else: have_tags = False

        #     encoded = pickle.dumps(tuple(['SHSong',True,core.TAIL]))
        # else:
        #     encoded = pickle.dumps(tuple(['SHSong',False,core.TAIL]))
        encoded = pickle.dumps(tuple(['SHSong',have_tags and have_all_chunks,core.TAIL]))
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
                state, _ = core.send_bytes_to(encoded,connection,False,verbose=False)
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
        id_Song = int(request_data[0])
        ms = int(request_data[1])
        chunk = dbc.get_a_chunk(ms,id_Song,self.db_path) 
        try:
            encoded = pickle.dumps(tuple(['Schunk',chunk,core.TAIL]))
            state, _ = core.send_bytes_to(encoded,connection,False,verbose=False)
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
    """ Client manager node"""
    str_rep = 'Router_node'
    class _providers:
        def __init__(self,address,type):
            self.address = address
            self.type = type
            self.used = 0
        def use(self):
            self.used +=1

    def __init__(self,server_ip=None):
        self.headers = {'ping':core.send_echo_replay,           # ping -_-  
                        'RSList':self.send_songs_tags_list,     # Request Songs List
                        'Rsong' :self.send_providers_list,      # Request song
                        'Rchunk':self.send_providers_list,      # Request chunk
                        }

        self.providers_by_song = dict()    
        self.existing_providers = list()
        self.songs_tags_list = list()       

    def __already_in_song_list(self,row,rows_list) -> bool:
        for r in rows_list:
            if len(row) != len(r):
                continue
            if row == r:
                # print("row == r: ", row, r)
                return True
            # eq = True
            # for i in range(len(row)):
            #     if row[i] != r[i]:
            #         eq = False
            #         break
            # if eq: return True
        return False

    def __already_in_prov_list(self,prov:_providers,prov_list) -> bool:
        for pr in prov_list:
            if prov.address[0] == pr.address[0] and prov.address[1] == pr.address[1]:
                return True
        return False
    
    def __song_by_id(self,id):
        a = 0
        b = len(self.songs_tags_list) - 1
        m = 0
        while a <= b:
            m = (a+b) // 2
            if self.songs_tags_list[m][0] < id:
                a = m + 1
            elif self.songs_tags_list[m][0] > id:
                b = m - 1
            else:
                return self.songs_tags_list[m]
        return None
    
    def __get_songs_tags_list(self):
        """ Connect to a data nodes and ask for the songs tags. 
        Unite the songs of every data node"""
        addrs = core.get_addr_from_dns("distpotify.data" )
        data_servers = []
        if addrs != None:
            for addr in addrs:
                data_servers.append(addr)

        data_servers = set(data_servers)
        request = tuple(['RSList',None,core.TAIL])
        encoded = pickle.dumps(request)

        new_song_list = list()
        for ds in data_servers:
            prov = Router_node._providers(ds,'data server')
            # if not self.__already_in_prov_list(prov,self.existing_providers):
            #     self.existing_providers.append(prov)

            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            sock.connect(ds)

            core.send_bytes_to(encoded,sock,False)
            result = core.receive_data_from(sock,waiting_time_ms=3000,iter_n=33,verbose=False)
            decoded = pickle.loads(result) 
            if 'SSList' in decoded:
                ack = pickle.dumps(core.ACK_OK_tuple)
                state, _ = core.send_bytes_to(ack,sock,False)
                
                for s in decoded[1]:
                    if not self.providers_by_song.get(s[0]):
                        self.providers_by_song[s[0]] = []
                    if not self.__already_in_prov_list(prov, self.providers_by_song[s[0]]):
                        self.providers_by_song[s[0]].append(prov)

                    if not self.__already_in_song_list(s,new_song_list):
                        new_song_list.append(s)
        
        self.songs_tags_list = new_song_list
        print(self.songs_tags_list)

        self.songs_tags_list.sort(key=lambda x: x[0])
        # if 'SSList' in decoded:
        #     self.songs_tags_list = decoded[1]
        # else:
        #     print(decoded)
        #     self.songs_tags_list = None

        return self.songs_tags_list
    
    def __get_best_providers(self,song_id, max_prov):
        old_prov = self.providers_by_song.get(song_id)
        self.providers_by_song[song_id] = []
        responsible = None
        song = self.__song_by_id(song_id)
        # if not old_prov or len(old_prov) == 0:
            # no one have the song, go and ask DNS for the data servers
        addresses = core.get_addr_from_dns('distpotify.data')
        for data_server in addresses:
            if not responsible and (song != None):
                sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                sock.connect(data_server)
                encoded = pickle.dumps(tuple(['RSResp',song,core.TAIL]))
                state, _ = core.send_bytes_to(encoded,sock,False)
                if state == 'OK':
                    result = core.receive_data_from(sock)
                    decoded = pickle.loads(result)
                    ack = pickle.dumps(core.ACK_OK_tuple)
                    state, _ = core.send_bytes_to(ack,sock,False)
                    if 'SSResp' in decoded:
                        responsible = Router_node._providers(decoded[1], 'data server') 
                sock.close()

            try:
                sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                sock.connect(data_server)
                encoded = pickle.dumps(tuple(['RHSong',song_id,core.TAIL]))
                state, _ = core.send_bytes_to(encoded,sock,False)
                if state != 'OK':
                    continue
                result = core.receive_data_from(sock)
                decoded = pickle.loads(result)

                ack = pickle.dumps(core.ACK_OK_tuple)
                state, _ = core.send_bytes_to(ack,sock,False)
                sock.close()

                if decoded[1]:
                    #  data_server is a provider of the song
                    new_prov = Router_node._providers(data_server,'data server')
                    # self.existing_providers.append(new_prov)
                    if not self.__already_in_prov_list(new_prov, self.providers_by_song[song_id]):
                        self.providers_by_song[song_id] += [new_prov]
            except Exception as er:
                print(er)
                continue
            
        # else:
        #     if len(old_prov) >= max_prov:

        #     for prov in old_prov:
        #         # for every provider, if still exists (is connected) keep it
        #         if prov in self.existing_providers:
        #             self.providers_by_song[song_id] += [prov]
        sampl = random.sample(self.providers_by_song[song_id], min(max_prov,len(self.providers_by_song[song_id])))
        if (responsible != None) and not self.__already_in_prov_list(responsible, sampl):
            sampl.insert(0,responsible)
        to_send = []
        for prov in sampl:
            to_send.append(prov.address)
        return to_send

    def send_songs_tags_list(self,request_data,connection,address):
        """ update the list of songs tags and send it to the client """
        self.__get_songs_tags_list()
        response = tuple(["SSList",self.songs_tags_list,core.TAIL])
        encoded = pickle.dumps(response)

        state = core.send_bytes_to(encoded,connection,False)
        
        if state [0] == "OK":
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            print("Songs Tags Sended ")
            if 'ACK' in decoded:
                return True
            
        return False
    
    def send_providers_list(self,request_data,connection,address):
        if isinstance(request_data,(list,tuple)):
            song_id = request_data[0]
        else: song_id = request_data
        providers = self.__get_best_providers(song_id,3)

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
    
    str_rep = 'DNS_node'
    def __init__(self,server_id=None): 
        self.headers = {'ping':core.send_echo_replay,   # ping -_-  
                        'RNSolve':self.name_solve,      # Request Name Solve | data: domain_to_solve
                        'AddRec' :self.add_record,      # Add Record | data: (labels, addr, ttl) 
            }
        server_directory = os.path.dirname(os.path.abspath(__file__))
        self.records_path = os.path.join(server_directory,'dns_records')
        # files = os.listdir(self.records_path)
        # f = open(os.path.join(self.records_path,files[0]),'rb')
        # f.close()
        multiprocessing.set_start_method('fork', force=True)
        p = multiprocessing.Process(target=self.update_using_ttl)
        p.start()

    def _get_records(self):
        try:
            files = os.listdir(self.records_path)
            with open(os.path.join(self.records_path,files[0]),'rb') as f:
                data = pickle.load(f)
        except FileNotFoundError as err:
            print("DNS error. Records not found. ", err)
        return data

    def _new_record(self,record:dict,rcrdss:list):
        for rc in rcrdss:
            if rc['labels'] == record['labels'] and rc['data'] == record['data']:
                return False
        return True

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
        elif self._new_record(record,rds[labels]): 
            rds[labels].append(record)
 
        try:
            files = os.listdir(self.records_path)
            if not files or len(files) == 0:
                with open(os.path.join(self.records_path,'rcrds.bin'),'wb') as f:
                    pickle.dump(rds,f)
            else: # TODO change files[0]
                with open(os.path.join(self.records_path,files[0]),'wb') as f:
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
        # datas = self.__alive_from(datas)
        datas = set(datas)
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
            time.sleep(30)
            try:
                data = self._get_records()
            except Exception as er:
                print(er)
            data_new = dict(data)
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
                        data_new[label].remove(rec) # TODO: test remove() method

            try:
                files = os.listdir(self.records_path)
                if not files or len(files) == 0:
                    with open(os.path.join(self.records_path,'rcrds.bin'),'wb') as f:
                        pickle.dump(data_new,f)
                else: # TODO change files[0]
                    with open(os.path.join(self.records_path,files[0]),'wb') as f:
                        pickle.dump(data_new,f)
            except FileNotFoundError:
                print("DNS error. Records not found")
                return False
            finally: 
                if f: f.close()
        
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
