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

HOST = "127.0.0.1"  # server address (localhost)
PORT = 8080         # port to which connect

s = socket(AF_INET, SOCK_STREAM)
s.connect((HOST, PORT)) # connect to server (block until accepted)
msg = "Hello World"
# compose a message
s.send(msg.encode())
# send the message
data = s.recv(1024)
# receive the response
print(data.decode())
# print the result
s.close()
# close the connection


# --------- theoretically similar --------- 

# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#     s.connect((HOST, PORT))
#     s.sendall(b"Hello, world")
#     data = s.recv(1024)

# print(f"Received {data!r}")