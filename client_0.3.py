import socket
import time
import pickle
import core

# Localhost (pc local) en el puerto 12345
server_addr = ('127.0.0.1', 12345)
# Crea un socket TCP
client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
# Establece una conexión con el servidor
client_sock.connect(server_addr)
# Envia un mensaje al servidor
# while True:
#     client_sock.send(bytes(f"Hello Server {server_addr}!",'UTF-8')) 
#     # Espera por un mensaje del servidor
#     message = client_sock.recv(1024).decode()
#     print('Server:\t',message)
#     time.sleep(10)

# Cierra la conexión
# client_sock.close()
data = core.receive_data_from(client_sock)
# header = pickle.loads(data[0])
# d = data[1]
# for i in range(2,len(data)):
#     d += data [i]
d = pickle.loads(data)
print(d)
h_d_t_list = tuple(["ACK","OK","!END!"])
pickled_data = pickle.dumps(h_d_t_list)
result = core.sender_3th(pickled_data,client_sock)
print(result)
    
