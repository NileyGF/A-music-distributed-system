import socket
import time
import pickle
import core

# Localhost (pc local) en el puerto 12345
server_addr = ('127.0.0.1', 12345)
dns_addr = ('127.0.0.1', 5383)
# Crea un socket TCP
client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
# Establece una conexión con el servidor
client_sock.connect(server_addr)
# client_sock.connect(dns_addr)


data = core.receive_data_from(client_sock)

d = pickle.loads(data)
print(d)
h_d_t_list = tuple(["ACK", "OK", "!END!"])
pickled_data = pickle.dumps(h_d_t_list)
result = core.sender_3th(pickled_data, client_sock)
print(result)

# h_d_t_list = tuple(["RNSolve","distpotify.router","!END!"])
# pickled_data = pickle.dumps(h_d_t_list)
# result = core.send_bytes_to(pickled_data,client_sock,False)
# result = core.receive_data_from(client_sock,1500,5000,99)
# print(result)

# h_d_t_list = tuple(["ACK","OK","!END!"])
# pickled_data = pickle.dumps(h_d_t_list)
# result = core.send_bytes_to(pickled_data,client_sock,False)
# print(result)
