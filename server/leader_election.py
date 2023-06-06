import socket
import struct


def elect_leader(servers):
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 5000))

    # Send messages to neighbors in the ring
    for i in range(len(servers)):
        neighbor = (servers[i-1] if i > 0 else servers[-1], 5000)
        message = struct.pack('!I', servers[i])
        sock.sendto(message, neighbor)

    # Receive messages from neighbors in the ring
    leader = None
    for i in range(len(servers)):
        message, address = sock.recvfrom(1024)
        neighbor = struct.unpack('!I', message)[0]
        if neighbor > servers[i]:
            leader = neighbor
        elif neighbor == servers[i]:
            leader = neighbor
            break

    # If no leader was found, start a new election
    if leader is None:
        leader = elect_leader(servers)

    return leader
