import time
import hashlib
import socket
import multiprocessing
import random
import pickle
import core
import database_controller as dbc

RING_SIZE = 6

""" A distributed hash table stores key-value pairs by assigning keys to different computers (known as "nodes"); a node will store the values for all the keys for which it is responsible.
    Nodes and keys are assigned an 64-bit identifier using consistent hashing. Nodes and keys are arranged in an identifier circle that has at most 2^m nodes, ranging from 0 to 2^m - 1.
    Each node has a successor and a predecessor. The successor to a node is the next node in the identifier circle in a clockwise direction. The predecessor is counter-clockwise.

    The successor node of a key k is the first node whose ID >= k in the identifier circle, denoted by successor(k). Every key is assigned to (stored at) its successor node, so looking up a key 
    k is to query successor(k).

    Since the successor (or predecessor) of a node may disappear from the network, each node records an arc of 2r+1 nodes in the middle of which it stands, i.e., the list of r nodes preceding it and 
    r nodes following it. This list results in a high probability that a node is able to correctly locate its successor or predecessor, even if the network in question suffers from a high failure rate.
        (r = 2)
    
    The core usage of the Chord protocol is to query a key from a client, i.e. to find successor(k). The basic approach is to pass the query to a node's successor, if it cannot find the key locally. 

    Finger Table:
        Contains up to m entries, the i-th entry of node n will contain successor( ( n + 2^{i-1} ) mod 2^m).
        The first entry of finger table is actually the node's immediate successor 

        Every time a node wants to look up a key k, it will pass the query to the closest successor or predecessor of k in its finger table (the "largest" one on the circle whose ID is smaller than k), until a node finds out the key is stored in its immediate successor.
    
    Node Join:
        Must ensure:
        * Each node's successor points to its immediate successor correctly.
        * Each key is stored in successor(k).
        * Each node's finger table should be correct.
        
        A new node must:
        * Initialize node n (the predecessor and the finger table).
        * Notify other nodes to update their predecessors and finger tables.
        * Takes over its responsible keys from its successor.

        The predecessor of n can be easily obtained from the predecessor of successor(n)
    
    Stabilization: 
    Therefore, a stabilization protocol is running periodically in the background which updates finger tables and successor pointers.
    The stabilization protocol works as follows:
        Stabilize(): n asks its successor for its predecessor p and decides whether p should be n's successor instead (this is the case if p recently joined the system).
        Notify(): notifies n's successor of its existence, so it can change its predecessor to n
        Fix_fingers(): updates finger tables

"""


class Node:
    def __init__(self, ip:str, port:int):
        self.ip = ip
        self.port = int(port)
        self.id = self.hash() # 0 <= self.id < 2^RING_SIZE
        manager = multiprocessing.Manager()
        
        """ Since the successor (or predecessor) of a node may disappear from the network, 
            record an arc of 2r+1 nodes in the middle of which it stands.
            A list of r nodes preceding it and r nodes following it. 
            This list results in a high probability that a node is able to correctly 
            locate its successor or predecessor, even if the network in question suffers from a high failure rate.
            (r = 2)
        """
        self.predecessor = manager.list([(self.id, (self.ip,self.port)),None])
        self.successor = manager.list([(self.id, (self.ip,self.port)),None])

        self.finger_table = manager.list()
        for i in range(RING_SIZE):
            entry = (self.id + pow(2, i)) % pow(2,RING_SIZE)
            node = manager.list([None])
            # node.values
            self.finger_table.append( manager.list([entry, node]) )
        self.print_finger()

        self.data_base = None

        self.headers = {'ping'  :core.send_echo_replay,         # ping -_-  
                        'ReqInit':self.send_keys_init,          # Request Initialization Info
                        'SolInit_tags':self.add_rows_to_songs,  # Solved Initialization Info for 'song' table
                        'SChunkRow':self.add_row_to_chunks,     # Send chunk row
                        'ReqJChord':self.join_request,          # Request Joing Chord Ring
                        'JChordAt':0,        # Join Chord Ring At
                        'RSccssN':self.solve_successor,         # Request Successor of N
                        'RPcssN':self.solve_predecessor,        # Request Predecessor of N
                        'SSccssN':0,          # Request Successor of N
                        'SPcssN':0,           # Request Predecessor of N
                        'Notify':self.notify,                   # Notify successor
                        'NotifyP':self.notify_pred,             # Notify predecessor
                        'RSResp':self.lookup,                   # Request Song Responsible
                        'SSResp':0,           # Solve Song Responsible
                        }
        multiprocessing.set_start_method('fork', force=True)
        p = multiprocessing.Process(target=self.stabilize)
        p.start()
        p = multiprocessing.Process(target=self.check_predecessor)
        p.start()
        p = multiprocessing.Process(target=self.fix_fingers)
        p.start()
        # t = threading.Thread(target = self.stabilize)
        # t.start()
        # t = threading.Thread(target = self.fix_fingers)
        # t.start()
        # t = threading.Thread(target = self.check_predecessor)
        # t.start()

    def __str__(self) -> str:
        return self.ip + ":" + str(self.port)  
    
    def hash_song(self, song_labels:list):
        """ This function is used to find the id of any string 
            and hence find it's correct position in the ring
        """
        song_all:str = song_labels[1] + song_labels[2]
        
        hashx = hashlib.sha256(song_all.encode('utf-8')).hexdigest()
        hashx = int(hashx, 16) % pow(2, RING_SIZE)
        return hashx

    def hash(self):
        hashx = hashlib.sha256(self.__str__().encode('utf-8')).hexdigest()
        hashx = int(hashx, 16) % pow(2, RING_SIZE)
        return hashx

    def init_finger_table(self):
        """ Contains up to RING_SIZE entries, the i-th entry 
            will contain successor((id + 2^{i-1} ) % 2^RING_SIZE).
            The first entry of finger table is actually the node's immediate successor. 
        """
        
        table = []
        for i in range(RING_SIZE):
            entry = (self.id + pow(2, i)) % pow(2,RING_SIZE)
            node = None
            table.append( [entry, node] )
        return table

    def join(self,node_addr):
        """
        Function responsible to join any new nodes to the chord ring 
        it finds out the successor and the predecessor of the new 
        incoming node in the ring and then it sends a send_keys request to 
        its successor to recieve all the keys smaller than its id from its successor.
        """
        print(core.ANSI_colors['cyan'])
        if node_addr[0] == self.ip and node_addr[1] == self.port:
            self.successor[0] = (self.id, (self.ip, self.port))
            self.finger_table[0][1] [0] = self.successor[0]
            # self.predecessor = [None, None]
            print(core.ANSI_colors['default'])
            return
        request = tuple(['ReqJChord',self.id,core.TAIL])
        encoded = pickle.dumps(request)
        try:
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            sock.connect(node_addr)
            sended, _ = core.send_bytes_to(encoded, sock, False)
            if sended == 'OK':
                result = core.receive_data_from(sock)
                decoded = pickle.loads(result)
                # Send ACK
                ack = pickle.dumps(core.ACK_OK_tuple)
                core.send_bytes_to(ack,sock,False)
                sock.close()
                if 'JChordAt' in decoded:
                    self.successor[0] = decoded[1] # (id, address)
                    self.finger_table[0][1] [0] = self.successor[0]
                    print(self.successor)
                    # ask for the keys <= self.id, from successor
                    if self.successor[0][0] != self.id:
                        self.get_keys_init()
        except Exception as er:
            print(er)
        print(core.ANSI_colors['default'])
                
    def get_keys_init(self):
        """ sends a send_keys request to its successor to recieve 
            all the keys smaller than its id from its successor """
        try:
            request = tuple(['RPcssN',self.id,core.TAIL])
            encoded = pickle.dumps(request)
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            sock.connect(self.successor[0][1])
            sended, _ = core.send_bytes_to(encoded, sock, False)
            if sended == 'OK':
                result = core.receive_data_from(sock)
                decoded = pickle.loads(result)
                # Send ACK
                ack = pickle.dumps(core.ACK_OK_tuple)
                core.send_bytes_to(ack,sock,False)
                sock.close()
                if 'SPcssN' in decoded:
                    self.predecessor[0] = decoded[1]

                    request = tuple(['ReqInit',[self.id,self.predecessor[0][0]],core.TAIL])
                    encoded = pickle.dumps(request)
                    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                    sock.connect(self.successor[0][1])
                    sended, _ = core.send_bytes_to(encoded, sock, False)
                    if sended == 'OK': 
                        result = core.receive_data_from(sock)
                        decoded = pickle.loads(result)
                        if 'ACK' in decoded:
                            return True
        except Exception as er:
            print(er)
        return False

    def join_request(self, node_id, connection, address):
        """ will return successor for the node who is requesting to join """
        print(core.ANSI_colors['green'])
        try:
            node_successor =  self.find_successor(node_id)
            response = tuple(['JChordAt',node_successor,core.TAIL])
            encoded = pickle.dumps(response)
            state = core.send_bytes_to(encoded,connection,False)

            if state [0] == "OK":
                result = core.receive_data_from(connection)
                decoded = pickle.loads(result)
                if 'ACK' in decoded:
                    print(core.ANSI_colors['default'])
                    return True     
        except Exception as er:
            print(er)
        print(core.ANSI_colors['default'])
        return False
    
    def send_keys_init(self,request_data,connection,address):
        """ send all the keys less than equal to the node_id to the new node that has joined the chord ring """
        print(core.ANSI_colors['green'])
        try:
            node_id = request_data[0]
            node_pred_id = request_data[1]
            encoded = pickle.dumps(core.ACK_OK_tuple)
            state, _ = core.send_bytes_to(encoded,connection,False)

            self.songs_tags_list = dbc.get_aviable_songs(self.data_base)
            to_send = []
            for s in self.songs_tags_list:
                id_in_ring = self.hash_song(s)
                # print(f"song: {s}. hash: {id_in_ring}")
                if self.get_forward_distance(id_in_ring, node_id) < self.get_forward_distance(id_in_ring, self.id):
                    if self.get_forward_distance(id_in_ring, node_pred_id) > self.get_forward_distance(id_in_ring, node_id):
                        to_send.append(s)
                    # theorically remove from me that data
        except Exception as er:
            print(er)
        
        try:
            # first send all the song tags
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            # print(f"send keys to : {(address[0],core.CHORD_PORT)}")
            sock.connect((address[0],core.CHORD_PORT))
            encoded = pickle.dumps(tuple(['SolInit_tags',to_send,core.TAIL]))
            # print('sending his songs', to_send)
            state, _ = core.send_bytes_to(encoded,sock,False,verbose=False)
            if state == 'OK': 
                result = core.receive_data_from(sock)
                sock.close()
                decoded = pickle.loads(result)
                if not 'ACK' in decoded:
                    print(core.ANSI_colors['default'])
                    return False
                    
                # then send the corresponding chunks
                for s in to_send:
                    chunks_rows = dbc.get_chunks_rows_for_song(s[0],self.data_base)
                    # print('len(chunks_row): ',len(chunks_row))
                    for chunk in chunks_rows:
                        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                        sock.connect((address[0],core.CHORD_PORT))
                        encoded = pickle.dumps(tuple(['SChunkRow',chunk,core.TAIL]))
                        state, _ = core.send_bytes_to(encoded,sock,False,verbose=False)
                        if state == 'OK': 
                            result = core.receive_data_from(sock)
                            sock.close()
                            decoded = pickle.loads(result)
                            if not 'ACK' in decoded:
                                print(core.ANSI_colors['default'])
                                return False
                            continue
                        sock.close()
                    # return False
                print(core.ANSI_colors['default'])
                return True
            sock.close()    
        except Exception as er:
            print(er)
        if sock:
            sock.close()
        print(core.ANSI_colors['default'])
        return False
    
    def lookup(self, key, connection, address):
        """ Return the node responsible for storing the key """
        print(core.ANSI_colors['green'])
        try:
            key = self.hash(key)
            resp = self.find_successor(key)
            response = tuple(['SSResp',resp,core.TAIL])
            encoded = pickle.dumps(response)
            state = core.send_bytes_to(encoded,connection,False)

            if state [0] == "OK":
                result = core.receive_data_from(connection)
                decoded = pickle.loads(result)
                if 'ACK' in decoded:
                    print(core.ANSI_colors['default'])
                return True     
        except Exception as er:
            print(er)
        print(core.ANSI_colors['default'])
        return False

    def add_rows_to_songs(self,rows,connection,address):
        try:
            encoded = pickle.dumps(core.ACK_OK_tuple)
            state, _ = core.send_bytes_to(encoded,connection,False)

            dbc.insert_rows_into_songs(rows,self.data_base)
            return True
        except Exception as er:
            print(er)
            return False
    
    
    def add_row_to_chunks(self,row,connection,address):
        try:
            encoded = pickle.dumps(core.ACK_OK_tuple)
            state, _ = core.send_bytes_to(encoded,connection,False)

            s_id = row[2]
            query = "SELECT * from songs where id_S = "+str(s_id)
            s_row = dbc.read_data(self.data_base, query)
            if s_row != None and len(s_row) > 0:
                # I have the tags of that song
                # print(f"trying to insert chunk {row[0]}, with length: {len(row[0])}")
                dbc.insert_rows_into_chunks([row],self.data_base)
                return True
            return False
        except Exception as er:
            print(er)
            return False

    def solve_successor(self, search_id, connection, address):
        print(core.ANSI_colors['green'])
        node_successor = self.find_successor(search_id)
        response = tuple(['SSccssN',node_successor,core.TAIL])
        encoded = pickle.dumps(response)
        state = core.send_bytes_to(encoded,connection,False)

        if state [0] == "OK":
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            if 'ACK' in decoded:
                print(core.ANSI_colors['default'])
                return True     
        print(core.ANSI_colors['default'])
        return False

    def solve_predecessor(self, search_id, connection, address):
        print(core.ANSI_colors['green'])
        node_predecessor = self.find_predecessor(search_id)
        response = tuple(['SPcssN',node_predecessor,core.TAIL])
        encoded = pickle.dumps(response)
        state = core.send_bytes_to(encoded,connection,False)

        if state [0] == "OK":
            result = core.receive_data_from(connection)
            decoded = pickle.loads(result)
            if 'ACK' in decoded:
                print(core.ANSI_colors['default'])
                return True     
        print(core.ANSI_colors['default'])
        return False

    def find_predecessor(self, search_id):
        """ Provides the predecessor of any value in the ring given its id."""
        if search_id == self.id:
            print(f" Predecessor of {search_id} is {(self.id, (self.ip, self.port))}")
            return (self.id, (self.ip, self.port))
        
        if self.predecessor[0] is not None and  self.successor[0][0] == self.id:
            print(f" ---- Predecessor of {search_id} is {(self.id, (self.ip, self.port))}")
            return (self.id, (self.ip, self.port))
        
        print(core.ANSI_colors['cyan'])
        if self.predecessor[0] is not None and self.get_forward_distance(self.id, self.successor[0][0]) > self.get_forward_distance(self.id, search_id):
            print(core.ANSI_colors['default'])
            print(f" Predecessor of {search_id} is {(self.id, (self.ip, self.port))}")
            return (self.id, (self.ip, self.port))
        
        else:
            # forward the query around the circle
            # n0 := closest_preceding_node(search_id)
            # return n0.find_successor(search_id)
            new_node_hop = self.closest_preceding_node(search_id)
            # print(f"new_node_hop {new_node_hop}")
            if new_node_hop is None:
                print(core.ANSI_colors['default'])
                print(f" Predecessor of {search_id} is {None}")
                return None
            ip, port = new_node_hop [1]
            if ip == self.ip and port == self.port:
                print(core.ANSI_colors['default'])
                # print(f" I'm predecessor")
                print(f" Predecessor of {search_id} is {(self.id, (self.ip, self.port))}")
                return (self.id, (self.ip, self.port))
            
            try:
                request = tuple(['RPcssN',search_id,core.TAIL])
                encoded = pickle.dumps(request)
                sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                sock.connect(new_node_hop[1])
                sended, _ = core.send_bytes_to(encoded, sock, False)
                if sended == 'OK':
                    result = core.receive_data_from(sock)
                    decoded = pickle.loads(result)
                    # Send ACK
                    ack = pickle.dumps(core.ACK_OK_tuple)
                    core.send_bytes_to(ack,sock,False)
                    sock.close()
                    if 'SPcssN' in decoded:
                        print(core.ANSI_colors['default'])
                        print(f" Predecessor of {search_id} is {decoded[1]}")
                        return decoded[1]
            except Exception as er:
                print(er)
                print(core.ANSI_colors['default'])
                return None
        print(core.ANSI_colors['default'])

    def find_successor(self, search_id):
        """ Provides the successor of any value in the ring given its id."""
        if(search_id == self.id):
            print(f" Successor of {search_id} is {(self.id, (self.ip, self.port))}")
            return (self.id, (self.ip, self.port))
        
        print(core.ANSI_colors['cyan'])
        predecessor = self.find_predecessor(search_id)
   
        if predecessor == None:
            print(core.ANSI_colors['default'])
            print(f" Successor of {search_id} is {None}")
            return None
        if predecessor[0] == self.id:
            print(core.ANSI_colors['default'])
            if self.successor[0]:
                print(f" Successor of {search_id} is {self.successor[0]}")
                return self.successor[0]
            print(f" Successor of {search_id} is {(self.id, (self.ip, self.port))}")
            return (self.id, (self.ip, self.port))
        try:
            request = tuple(['RSccssN',search_id,core.TAIL])
            encoded = pickle.dumps(request)
            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            sock.connect(predecessor[1])
            sended, _ = core.send_bytes_to(encoded, sock, False)
            if sended == 'OK':
                result = core.receive_data_from(sock)
                decoded = pickle.loads(result)
                # Send ACK
                ack = pickle.dumps(core.ACK_OK_tuple)
                core.send_bytes_to(ack,sock,False)
                sock.close()
                if 'SSccssN' in decoded:
                    print(core.ANSI_colors['default'])
                    print(f" Successor of {search_id} is {decoded[1]}")
                    return decoded[1]
        except Exception as er:
            print(er)
            print(core.ANSI_colors['default'])
            return None
        print(core.ANSI_colors['default'])
    
    def closest_preceding_node(self, search_id):
        """search the finger table for the highest predecessor of search_id"""
        closest_node = (self.id, (self.ip,self.port))
        min_distance = pow(2,RING_SIZE) + 1
        for i in list(reversed(range(RING_SIZE))):
            
            if self.finger_table[i][1][0] is not None and self.get_forward_distance(self.finger_table[i][0], search_id) < min_distance  :
                closest_node = self.finger_table[i][1][0]
                min_distance = self.get_forward_distance(self.finger_table[i][0],search_id)
                # print("Min distance",min_distance)
        print(f" Closest preceding node of {search_id} is {(self.id, (self.ip, self.port))}")
        return closest_node

    def stabilize(self):
        """
        The stabilize function is called in repetitively in regular intervals as it is responsible to make sure that each 
        node is pointing to its correct successor and predecessor nodes. By the help of the stabilize function each node
        is able to gather information of new nodes joining the ring.
        """
        while True:
            if self.successor[0] is None:
                time.sleep(20)
                print(core.ANSI_colors['red'], " No successor" , core.ANSI_colors['default'])
                continue

            if self.successor[0][1][0] == self.ip  and self.successor[0][1][1] == self.port:
                time.sleep(20)
                print(core.ANSI_colors['red'], " I'm my successor", core.ANSI_colors['default'])
                continue
            
            # get successor.predecesor
            try:
                print(core.ANSI_colors['red'])
                request = tuple(['RPcssN',self.successor[0][0],core.TAIL])
                encoded = pickle.dumps(request)
                sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                sock.connect(self.successor[0][1])
                sended, _ = core.send_bytes_to(encoded, sock, False)
                if sended == 'OK':
                    result = core.receive_data_from(sock)
                    decoded = pickle.loads(result)
                    # Send ACK
                    ack = pickle.dumps(core.ACK_OK_tuple)
                    core.send_bytes_to(ack,sock,False)
                    sock.close()
                    if 'SPcssN' in decoded:
                        if decoded[1] == None or len(decoded[1]) != 2:
                            # notify successor that we are his predecessor
                            request = tuple(['Notify',(self.id, (self.ip, self.port)),core.TAIL])
                            encoded = pickle.dumps(request)
                            sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                            sock.connect(self.successor[0][1])
                            sended, _ = core.send_bytes_to(encoded, sock, False)
                            if sended == 'OK':
                                result = core.receive_data_from(sock)
                                decoded_ack = pickle.loads(result)
                                sock.close()
                                if 'ACK' in decoded_ack:
                                    print(core.ANSI_colors['default'])  
                                    continue
                        else:
                            succ_pred = decoded[1]
                
                # found predecessor of my successor
                if self.get_backward_distance(self.id,succ_pred[0]) > self.get_backward_distance(self.id,self.successor[0][0]):
                    # if ... changing my successor in stabilize
                    self.successor[0] = succ_pred # (id, (ip, port))
                    self.finger_table[0][1] [0] = self.successor[0]

                # notify successor
                request = tuple(['Notify',(self.id, (self.ip, self.port)),core.TAIL])
                encoded = pickle.dumps(request)
                sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                sock.connect(self.successor[0][1])
                sended, _ = core.send_bytes_to(encoded, sock, False)
                if sended == 'OK':
                    result = core.receive_data_from(sock)
                    decoded_ack = pickle.loads(result)
                    sock.close()
            except Exception as er:
                print(er)

            print("===============================================")
            print("STABILIZING")
            print("===============================================")
            print("ID: ", self.id)
            if self.successor[0] is not None:
                print("Successor ID: " , self.successor[0][0])
            if self.predecessor[0] is not None:
                print("predecessor ID: " , self.predecessor[0][0])
            print("===============================================")
            print("=============== FINGER TABLE ==================")
            self.print_finger()
            # print("===============================================")
            # print("DATA STORE")
            # print("===============================================")
            # print(str(self.data_store.data))
            print("===============================================")
            print("++++++++++++++++++++ END ++++++++++++++++++++++",core.ANSI_colors['default'])
            time.sleep(20)

    def notify(self, node_info, connection, address):
        """
        Recevies notification from stabilized function when there is change in successor,
        node thinks it might be our predecessor.
        """
        print(core.ANSI_colors['red'])
        encoded = pickle.dumps(core.ACK_OK_tuple)
        state, _ = core.send_bytes_to(encoded,connection,False)

        node_id = node_info[0]
        
        if self.predecessor[0] is not None:
            if self.get_backward_distance(self.id,node_id) < self.get_backward_distance(self.id,self.predecessor[0][0]):
                print("changing my predecessor", node_id)
                self.predecessor[0] = node_info
                print(core.ANSI_colors['default'])
                return
        
        if self.predecessor[0] is None \
        or ( node_id > self.predecessor[0][0] and node_id < self.id ) \
        or ( self.id == self.predecessor[0][0] and node_id != self.id) :
            print("changing my predecessor", node_id)
            self.predecessor[0] = node_info

            # special case???
            if self.id == self.successor[0][0]:
                # print("changing my succ", node_id)
                self.successor[0] = node_info
                self.finger_table[0][1] [0] = self.successor[0]
        print(core.ANSI_colors['default'])
    
    def notify_pred(self, node_info, connection, address):
        """
        Recevies notification from stabilized function when there is change in successor,
        node thinks it might be our predecessor.
        """
        print(core.ANSI_colors['red'])
        encoded = pickle.dumps(core.ACK_OK_tuple)
        state, _ = core.send_bytes_to(encoded,connection,False)

        node_id = node_info[0]
        
        if self.successor[0] is not None:
            if self.get_forward_distance(self.id,node_id) < self.get_forward_distance(self.id,self.successor[0][0]):
                print("changing my successor", node_id)
                self.successor[0] = node_info
                self.finger_table[0][1] [0] = self.successor[0]
                print(core.ANSI_colors['default'])
                return
        
        if self.successor[0] is None \
        or ( node_id < self.successor[0][0] and node_id > self.id ) \
        or ( self.id == self.successor[0][0] and node_id != self.id) :
            print("changing my successor", node_id)
            self.successor[0] = node_info
            self.finger_table[0][1] [0] = self.successor[0]

            # special case???
            if self.id == self.successor[0][0]:
                # print("changing my succ", node_id)
                self.predecessor[0] = node_info
        print(core.ANSI_colors['default'])
    
    def fix_fingers(self):
        """
        The fix_fingers function is used to correct the finger table at regular interval of time this function waits for
        10 seconds and then picks one random index of the table and corrects it so that if any new node has joined the 
        ring it can properly mark that node in its finger table.
        """
        i = 0
        while True:
            try:
                # random_index = random.randint(0,RING_SIZE-1)
                # finger = self.finger_table[random_index][0]
                finger = self.finger_table[i][0]
                
                data = self.find_successor(finger)
                if data == None:
                    time.sleep(20)
                    continue
                print(f"fix_fingers\t{finger} successor : {data}")
                self.finger_table[i][1] [0] = data
                self.print_finger()
                i = i+1 
                i = i % RING_SIZE
                time.sleep(20)
            except:
                time.sleep(20)
            continue

    def check_predecessor(self):
        """periodically checks whether predecessor has failed."""
        while True:
            if self.predecessor[0] is not None:
                if self.predecessor[0][0] != self.id:
                    request = tuple(['NotifyP',(self.id, (self.ip, self.port)),core.TAIL])
                    encoded = pickle.dumps(request)
                    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                    sock.connect(self.predecessor[0][1])
                    sended, _ = core.send_bytes_to(encoded, sock, False,verbose=False)
                    if sended == 'OK':
                        result = core.receive_data_from(sock,verbose=False)
                        decoded_ack = pickle.loads(result)
                        sock.close()
                        if 'ACK' in decoded_ack:
                            print(core.ANSI_colors['cyan'] + "Chord predecessor OK!" + core.ANSI_colors['default'])
                            time.sleep(20)
                            continue
                    self.predecessor[0] = None
                print(core.ANSI_colors['cyan'] + "Chord predecessor OK!" + core.ANSI_colors['default'])
            time.sleep(20)

    def get_backward_distance(self, node2, node1):
        
        distance = 0
        if(node2 > node1):
            distance =  node2 - node1
        elif node2 == node1:
            distance = 0
        else:
            distance = pow(2,RING_SIZE) - abs(node2 - node1)
     
        return distance

    def get_forward_distance(self, node2, node1):
        return pow(2,RING_SIZE) - self.get_backward_distance(node2,node1)

    def print_finger(self):
        for finger in self.finger_table:
            print(f"{finger[0]} , {finger[1][0]}")

# d1 = Node('172.20.0.5',7777)
# d2 = Node('172.20.0.7',7777)
# d3 = Node('172.20.0.6',7777)

# print(d1.hash())
# print(d2.hash())
# print(d3.hash())
# chunks_row = dbc.get_chunks_rows_for_song(11,'server/data_nodes/spotify_1.db')
# print(len(chunks_row))
# print(chunks_row[0])