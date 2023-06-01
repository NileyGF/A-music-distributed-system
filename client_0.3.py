import socket
import time
import pickle
import core

server_addr = ('192.168.43.147',8888)

# # Localhost (pc local) en el puerto 12345
# server_addr = ('127.0.0.1', 12345)
dns_addr = ('192.168.43.161',5353)
# # Crea un socket TCP
# Localhost (pc local) en el puerto 12345
# server_addr = ('127.0.0.1', 12345)
# dns_addr = ('0.0.0.0', 5353)
# Crea un socket TCP
client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
# # Establece una conexión con el servidor
client_sock.connect(dns_addr)
print(client_sock)
# client_sock.connect(dns_addr)



# data = core.receive_data_from(client_sock)

# d = pickle.loads(data)
# print(d)
# h_d_t_list = tuple(["ACK", "OK", "!END!"])
# pickled_data = pickle.dumps(h_d_t_list)
# result = core.sender_3th(pickled_data, client_sock)
# print(result)

# h_d_t_list = tuple(["RNSolve","distpotify.router","!END!"])
# pickled_data = pickle.dumps(h_d_t_list)
# result = core.send_bytes_to(pickled_data,client_sock,False)
# result = core.receive_data_from(client_sock,1500,5000,99)
# print(result)

# d = pickle.loads(data)
# print(d)
# h_d_t_list = tuple(["ACK","OK","!END!"])
# pickled_data = pickle.dumps(h_d_t_list)
# result = core.sender_3th(pickled_data,client_sock)
# print(result)
    
h_d_t_list = tuple(["RNSolve","distpotify.router","!END!"])
pickled_data = pickle.dumps(h_d_t_list)
core.send_bytes_to(pickled_data,client_sock,False)
result = core.receive_data_from(client_sock,1500,5000,99)
result = pickle.loads(result)
print(result)
rout_addr = result[1][0]

h_d_t_list = tuple(["ACK","OK","!END!"])
pickled_data = pickle.dumps(h_d_t_list)
core.send_bytes_to(pickled_data,client_sock,False)

client_sock.close()
client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
client_sock.connect(rout_addr)

h_d_t_list = tuple(["RSList",None,"!END!"])
pickled_data = pickle.dumps(h_d_t_list)
core.send_bytes_to(pickled_data,client_sock,False)
result = core.receive_data_from(client_sock,1500,10000,99)
result = pickle.loads(result)
print(result)

h_d_t_list = tuple(["ACK","OK","!END!"])
pickled_data = pickle.dumps(h_d_t_list)
core.send_bytes_to(pickled_data,client_sock,False)

client_sock.close()
client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
client_sock.connect(rout_addr)

h_d_t_list = tuple(["Rsong",11,"!END!"])
pickled_data = pickle.dumps(h_d_t_list)
core.send_bytes_to(pickled_data,client_sock,False)
result = core.receive_data_from(client_sock,1500,10000,99)
result = pickle.loads(result)
print(result)
prov_addr = result[1][0]

h_d_t_list = tuple(["ACK","OK","!END!"])
pickled_data = pickle.dumps(h_d_t_list)
core.send_bytes_to(pickled_data,client_sock,False)

client_sock.close()
client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
client_sock.connect(prov_addr)

h_d_t_list = tuple(["Rsong",11,"!END!"])
pickled_data = pickle.dumps(h_d_t_list)
core.send_bytes_to(pickled_data,client_sock,False)
result = core.receive_data_from(client_sock,1500,5000,99)
result = pickle.loads(result)
print(result)


h_d_t_list = tuple(["ACK","OK","!END!"])
pickled_data = pickle.dumps(h_d_t_list)
core.send_bytes_to(pickled_data,client_sock,False)

result[1].export("11_dice.mp3", format='mp3')
