import socket
import pickle
import sys
import math
import core
from os import path

class Client:
    def __init__(self) -> None:
        self.song_list = []

    def __get_router_addr(self):
        router_addrsss = None
        ack = tuple(["ACK","OK",core.TAIL])
        ack_encoded = pickle.dumps(ack)

        client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        client_sock.connect(core.DNS_addr)
        ns_request = tuple(["RNSolve","distpotify.router",core.TAIL])
        ns_encoded = pickle.dumps(ns_request)
        ns_sended, _ = core.send_bytes_to(ns_encoded, client_sock, False)
        if ns_sended == 'OK':
            ns_result = core.receive_data_from(client_sock,1500,3000,10)
            try:
                ns_decoded = pickle.loads(ns_result)
                # Send ACK
                core.send_bytes_to(ack_encoded,client_sock,False)

                if 'SNSolve' in ns_decoded:
                    client_sock.close()
                    # ensure that there are not repeated addresses and some load balancing because set() randomize the iter 
                    router_addrsss = set(ns_decoded[1])
                    return router_addrsss
            except Exception as err:
                client_sock.close()
                print(err)
                return False
        
        client_sock.close()
        return False

    def refresh_song_list(self):
        router_addrsss = None
        ack = tuple(["ACK","OK",core.TAIL])
        ack_encoded = pickle.dumps(ack)

        router_addrsss = self.__get_router_addr()
        print('routers: ',router_addrsss)
        if not router_addrsss:
            return False
                    
        for rout in router_addrsss:
            try:
                client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                client_sock.connect(rout)
                sl_request = tuple(["RSList",None,core.TAIL])
                sl_encoded = pickle.dumps(sl_request)
                sl_sended, _ = core.send_bytes_to(sl_encoded, client_sock, False)
                if sl_sended == 'OK':
                    sl_result = core.receive_data_from(client_sock,1500,3000,10)
                    
                    sl_decoded = pickle.loads(sl_result)
                    # Send ACK
                    core.send_bytes_to(ack_encoded,client_sock,False)
                    
                    if 'SSList' in sl_decoded:
                        client_sock.close()
                        self.song_list = sl_decoded[1]
                        return True    
                else: 
                    client_sock.close()
                    return False
                
            except Exception as err:
                client_sock.close()
                print(err)
                return False  

    def __request_song_known_addr(self, song_id, n_chunks, provider_addr):
        ack = tuple(["ACK","OK",core.TAIL])
        ack_encoded = pickle.dumps(ack)

        client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        client_sock.connect(provider_addr)
        rs_request  = tuple(["Rsong",song_id,core.TAIL])
        rs_encoded = pickle.dumps(rs_request)
        rs_sended, _ = core.send_bytes_to(rs_encoded, client_sock, False)
        if rs_sended != 'OK':
            client_sock.close()
            return False
        
        try:
            # receive every chunk
            for i in range(n_chunks):
                rs_result = core.receive_data_from(client_sock,1500,3000,10)
                rs_decoded = pickle.loads(rs_result)
                # Send ACK
                core.send_bytes_to(ack_encoded,client_sock,False)

                if 'Schunk' in rs_decoded:
                    # rs_decoded[1].export(f"{song_id}_dice{i}.mp3", format='mp3')
                    with open(f'{song_id}_dice_{i}.mp3','wb') as f:
                        f.write(rs_decoded[1])

            client_sock.close()
            return True
        except Exception as err:
            client_sock.close()
            print(err)
            return False

    def __request_chunk_known_addr(self, song_id, start_from_ms, provider_addr):
        ack = tuple(["ACK","OK",core.TAIL])
        ack_encoded = pickle.dumps(ack)

        client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        client_sock.connect(provider_addr)
        rc_request  = tuple(["Rchunk",[song_id,start_from_ms],core.TAIL])
        rc_encoded = pickle.dumps(rc_request)
        rc_sended, _ = core.send_bytes_to(rc_encoded, client_sock, False)
        if rc_sended != 'OK':
            client_sock.close()
            return False
        
        try:            
            rs_result = core.receive_data_from(client_sock,1500,3000,10)
            rs_decoded = pickle.loads(rs_result)
            # Send ACK
            core.send_bytes_to(ack_encoded,client_sock,False)

            if 'Schunk' in rs_decoded:
                rs_decoded[1].export(f"{song_id}_dice{start_from_ms}.mp3", format='mp3')
                client_sock.close()
                return True
        except Exception as err:
            client_sock.close()
            print(err)
            return False

    def request_song(self, song_id, n_chunks):
        ack = tuple(["ACK","OK",core.TAIL])
        ack_encoded = pickle.dumps(ack)
        providers = []

        router_addrsss = self.__get_router_addr()
        if not router_addrsss:
            return False
        
        for rout in router_addrsss:
            client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            client_sock.connect(rout)

            rs_request  = tuple(["Rsong",song_id,core.TAIL])
            rs_encoded = pickle.dumps(rs_request)
            rs_sended, _ = core.send_bytes_to(rs_encoded, client_sock, False)
            if rs_sended != 'OK':
                client_sock.close()
                continue

            rs_result = core.receive_data_from(client_sock,1500,3000,10)
            
            rs_decoded = pickle.loads(rs_result)
            # Send ACK
            core.send_bytes_to(ack_encoded,client_sock,False)
            client_sock.close()
            if 'SPList' in rs_decoded:    
                providers = rs_decoded[1]
                break

        if len(providers) == 0:
            return False 
        for prov in providers:
            ch_saved = self.__request_song_known_addr(song_id,n_chunks,prov) 
            if ch_saved:
                return True
        return False
    
    def request_song_from(self, song_id, start_from_ms, n_chunks):
        ack = tuple(["ACK","OK",core.TAIL])
        ack_encoded = pickle.dumps(ack)
        providers = []

        router_addrsss = self.__get_router_addr()
        if not router_addrsss:
            return False

        for rout in router_addrsss:
            client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            client_sock.connect(rout)

            rc_request = tuple(["Rchunk",[song_id,start_from_ms],core.TAIL])
            rc_encoded = pickle.dumps(rc_request)
            rc_sended, _ = core.send_bytes_to(rc_encoded, client_sock, False)
            if rc_sended != 'OK':
                client_sock.close()
                continue

            rs_result = core.receive_data_from(client_sock,1500,3000,10)
            
            rs_decoded = pickle.loads(rs_result)
            # Send ACK
            core.send_bytes_to(ack_encoded,client_sock,False)
            client_sock.close()
            if 'SPList' in rs_decoded:    
                providers = rs_decoded[1]
                break

        if len(providers) == 0:
            return False 
        for prov in providers:
            ch_saved = self.__request_chunk_known_addr(song_id,start_from_ms,prov) 
            if ch_saved:
                return True
        return False

if __name__ == "__main__":
    argList = sys.argv
    if len(argList) > 1:
        core.DNS_addr = (argList[1],core.DNS_PORT)
    core.DNS_addr = ('172.20.0.2',core.DNS_PORT)

    cl = Client()
    while True:
        order:str = input()
        if order == 'song list':
            cl.refresh_song_list()
            print(cl.song_list)
        elif 'song' == order.split()[0]:
            id = int(order.split()[1])
            row = None
            for ind in cl.song_list:
                if id == ind[0]:
                    row = ind
                    break
            # duration_sec = duration_ms / 1000
            duration_sec = row[4] / 1000 
            number_of_chunks:float = duration_sec / row[5]
            number_of_chunks = math.ceil(number_of_chunks)

            cl.request_song(id,number_of_chunks)
        else: 
            print('wrong request')
