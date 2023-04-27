""" this simple server makes use of a connection-oriented
service as offered by the socket library available in Python. This service allows
two communicating parties to reliably send and receive data over a connection.
• socket(): to create an object representing the connection
• accept(): a blocking call to wait for incoming connection requests; if
successful, the call returns a new socket for a separate connection
• connect(): to set up a connection to a specified party
• close(): to tear down a connection
• send(), recv(): to send and receive data over a connection, respectively
The combination of constants AF_INET and SOCK_STREAM is used to specify that
the TCP protocol should be used in the communication between the two parties.
These two constants can be seen as part of the interface, whereas making use of
TCP is part of the offered service. How TCP is implemented, or for that matter, any
part of the communication service, is hidden completely from the applications.
"""
from socket import *
HOST = "0.0.0.0"  # to be associated with all the red interfaces
PORT = 8080 # the ports <= 1023 require privileges

s = socket(AF_INET, SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()
(conn, addr) = s.accept() # returns new socket and addr. client
while True:
    # forever
    data = conn.recv(1024) # receive data from client
    if not data: 
        break
    # stop if client stopped
    msg = data.decode()+"*" # process the incoming data into a response
    conn.send(msg.encode()) # return the response
    conn.close()
    # close the connection

# --------- theoretically similar --------- 

# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#     s.bind((HOST, PORT))
#     s.listen()
#     conn, addr = s.accept()
#     with conn:
#         print(f"Connected by {addr}")
#         while True:
#             data = conn.recv(1024)
#             if not data:
#                 break
#             conn.sendall(data)
