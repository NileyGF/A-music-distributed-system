import socket
import threading

MAX_CLIENTS = 2
current_clients = 0
lock = threading.Lock()

client_dict = {}


def handle_client(client_socket):
    global current_clients

    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        print("Mensaje recibido del cliente:", data.decode())
        client_socket.send(bytes(f"OK", 'UTF-8'))
        client_socket.send(bytes(f"Testing", 'UTF-8'))
        client_socket.send(bytes(f"!END!", 'UTF-8'))
        # Realiza cualquier procesamiento adicional necesario

    with lock:
        current_clients -= 1

    client_socket.close()


def start_server(host, port):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(host)
    server_socket.bind((host, int(port)))
    server_socket.listen(2)  # Permite hasta 10 conexiones simultáneas
    current_clients = 0
    print("Servidor en espera de conexiones...")

    while True:
        client_socket, addr = server_socket.accept()

        with lock:
            if current_clients >= MAX_CLIENTS:
                print(
                    "Se ha alcanzado el límite máximo de clientes. Rechazando conexión del cliente:", addr)
                client_socket.close()
                continue
            else:
                current_clients += 1

        print("Cliente conectado:", addr)
        client_thread = threading.Thread(
            target=handle_client, args=(client_socket,))
        client_dict[addr] = client_thread
        client_thread.start()
