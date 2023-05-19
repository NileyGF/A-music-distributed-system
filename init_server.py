import socket
import threading
import Pyro5.api
import argparse
import subprocess
import time
import zmq
from _server import *


# def start(self):
#     # Registrar servidor en el sistema de nombres Pyro5
#     daemon = Pyro5.api.Daemon(host=self.ip, port=int(self.port)-2)
#     uri = daemon.register(self)
#     print(uri)
#     nameserver.register(f'chatroom.{args.room_name}', uri)

#     # Inicia servidor
#     self.subscribe_clients()
#     self.start_broadcasting()

#     # Inicia el servidor de nombres en otro hilo
#     threading.Thread(target=daemon.requestLoop).start()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("ip", help="IP del servidor")
    parser.add_argument("-p", "--port", help="Puerto", default="5555")
    # parser.add_argument("-pwd", "--password", help="Contraseña de acceso", default="12345678")
    args = parser.parse_args()

    # # Inicializar el contexto ZeroMQ y el socket PUB (publicación) y SUB (suscripción)
    # context = zmq.Context()
    # publisher = context.socket(zmq.PUB)
    # puller = context.socket(zmq.PULL)

    # Inicializar sistema de nombres Pyro5
    # Definir el comando para ejecutar el servidor de nombres Pyro5
    broadcast = args.ip.split(".")
    broadcast[-1] = "255"
    broadcast = "".join([i for i in broadcast])
    command = [
        "pyro5-ns",
        "-n", f"{args.ip}",
        '-p', f"{int(args.port)-1}",
        #   "--bchost",f"{ broadcast}",
        #   "--bcport",f"{int(args.port)-3}"
    ]

# # # Ejecutar el comando en un proceso aparte
#     subprocess.Popen(command)

#  # Esperar 1 segundo para que el servidor de nombres se inicie
#     time.sleep(1)
# #     # Definir la dirección IP del broker y el puerto del servidor

#     nameserver = Pyro5.api.locate_ns()

#     # if args.password:
#     #     print(f"Contraseña de acceso: {args.password}")
    print(f"Dirección IP: {args.ip}")
    print(f"Puerto: {args.port}")

    start_server(args.ip, args.port)
