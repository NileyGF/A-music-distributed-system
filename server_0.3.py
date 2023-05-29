import socket
from threading import *
import nodes_definition as nd

def client_handler(connection,client_addr):
    sended, received = router.send_songs_tags_list(connection)
    print('sended: ',sended, ' received by client',received)
    # conn.send(bytes(f"Hello client {client_addr}", 'UTF-8')) # Envia un mensaje
    
    # exchanges = 1
    # while True:
    #     client_message = conn.recv(1024).decode()
    #     print('Client:\t', client_message, client_addr)
    #     conn.send(bytes(f"Exchange {exchanges}", 'UTF-8')) # Envia un mensaje
    #     exchanges+=1
    connection.close()


server_addr = ('192.168.43.147', 8888) # Dirección IP
server_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
# server_sock.getifaddrs()
server_sock.bind(server_addr) # Enlaza el puerto
server_sock.listen(3) # Espera por un clientex  
client_n = 1
# router = nd.Router_node(None, None)
dns = nd.DNS_node()
# record = nd.DNS_node._add_record('distpotify.router',300,'127.0.0.1')
try:
    while True:
        
        conn, client_addr = server_sock.accept()
        
        print('CONNECTION: ',client_n)
        client_n += 1
        client_thread = Thread(target=client_handler, args=(conn,client_addr))
        client_thread.start()
finally:
    server_sock.close()