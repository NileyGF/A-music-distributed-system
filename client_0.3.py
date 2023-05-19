import socket
import time
import pickle

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
header = client_sock.recv(1024)
header = pickle.loads(header)
print(header)
data = None
while True:
    msg = client_sock.recv(1024)
    try:
        decode = pickle.loads(msg)
        if decode == '!END!':
            break
    except:
        pass

    if data: data+=msg
    else: data = msg
data_d = pickle.loads(data)
print(data_d)
    
