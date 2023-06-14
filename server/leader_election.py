import socket
import pickle
import random
import core


def elect_new_leader(temporal_leader_addrs, group_domain:str):
    group_servers = core.get_addr_from_dns(group_domain)
    candidates = [temporal_leader_addrs]
    print(temporal_leader_addrs, ' begins election for ', group_domain)
    for i in range(len(group_servers)):
        if group_servers[i] == temporal_leader_addrs:
            continue

        try:
            messag = tuple(['ReqELECTION',None,core.TAIL])
            encoded = pickle.dumps(messag)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(group_servers[i])

            # Send elecction message to neighbor
            core.send_bytes_to(encoded,sock,False)
            result = core.receive_data_from(sock,waiting_time_ms=2000,iter_n=3)
            decoded = pickle.loads(result)
            # Receive message from neighbor
            if 'RecELECTION' in decoded:
                candidates.append(group_servers[i])
                print('new candidate: ',group_servers[i])
                ack = pickle.dumps(core.ACK_OK_tuple)
                core.send_bytes_to(ack,sock,False)

        except Exception as err:
            print(err) 
        finally:
            sock.close()


    # Elect a leader randomly
    leader = None
    leader = random.sample(candidates,1)[0]
    print('elected leader: ',leader)

    for i in range(len(candidates)):
        if candidates[i] == temporal_leader_addrs:
            continue

        try:
            messag = tuple(['ELECTED',leader,core.TAIL])
            encoded = pickle.dumps(messag)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(candidates[i])

            # Send new leader message to neighbor
            core.send_bytes_to(encoded,sock,False)
            # receive ACK
            result = core.receive_data_from(sock,waiting_time_ms=2000,iter_n=3)

        except Exception as err:
            print(err) 
        finally:
            sock.close()

    return leader

def ongoing_election(server_instance, _, connection,address):
    """ 'ReqELECTION' received, send 'RecELECTION' """
    encoded = pickle.dumps(tuple(['RecELECTION',False,core.TAIL]))
    state, _ = core.send_bytes_to(encoded,connection,False)
    if state == 'OK': 
        result = core.receive_data_from(connection)
        try: 
            decoded = pickle.loads(result)
        
            if 'ACK' in decoded:
                return True
        except:
            pass
    return False

def ended_election(server_instance, new_leader, connection,address):
    """ 'ELECTED' new leader received, update group leader """
    ack = pickle.dumps(core.ACK_OK_tuple)
    core.send_bytes_to(ack,connection,False)

    server_instance.role_instance.group_leader = new_leader
    return True

