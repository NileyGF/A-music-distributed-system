import socket
from threading import *
import nodes_definition as nd

def client_handler(connection,client_addr):
    router.send_songs_tags_list(connection)
    # conn.send(bytes(f"Hello client {client_addr}", 'UTF-8')) # Envia un mensaje
    
    # exchanges = 1
    # while True:
    #     client_message = conn.recv(1024).decode()
    #     print('Client:\t', client_message, client_addr)
    #     conn.send(bytes(f"Exchange {exchanges}", 'UTF-8')) # Envia un mensaje
    #     exchanges+=1
    connection.close()


server_addr = ('127.0.0.1', 12345) # Dirección IP
server_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
server_sock.bind(server_addr) # Enlaza el puerto
server_sock.listen(3) # Espera por un clientex  
client_n = 1
router = nd.Router_node(None, None)
while True:
    # Establece la conexión y lee un mensaje
    conn, client_addr = server_sock.accept()
    print('CONNECTION: ',client_n)
    client_n += 1
    client_thread = Thread(target=client_handler, args=(conn,client_addr))
    client_thread.start()