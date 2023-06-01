import subprocess

# # Define the targets to scan (replace with appropriate IP ranges)
# targets = ['192.168.0.0/24'] # List of CIDR blocks or individual IP addresses

# # Execute the command to discover hosts on specified subnets
# outcomes = subprocess.run([
#     'nmap', '-v', '-A', '--max-retries=3', *targets,
# ], shell=True, text=True, universal_newlines=True, capture_output=True)
# print(outcomes.stdout)

# # Parse the captured output to extract IP addresses
# ips = []
# last_prefix = ""
# for line in outcomes.stdout.split('\n'):
#     prefix = line.split(' ')[0]
#     if prefix == "Nmap:" or not line.strip():
#         continue
#     elif len(prefix) > len(last_prefix):
#         last_prefix = prefix
#     elif prefix[:len(last_prefix)] != last_prefix:
#         break
#     else:
#         current_ip = f"{prefix} ({last_prefix})"
#         if current_ip not in ips:
#             ips.append(current_ip)

# # Print discovered IP addresses
# print("Discovered IP Addresses:")
# print("\n".join(ips))

# import socket
# hostname=socket.gethostname()
# IPAddr=socket.gethostbyname(hostname)
# # print(hostname, IPAddr)
# ad = socket.ge
# print(ad)

# s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# s.connect(('1.1.1.1', 1))  # connect() for UDP doesn't send packets
# local_ip_address = s.getsockname()[0]
# print(local_ip_address)

# import socket, struct, fcntl
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sockfd = sock.fileno()
# SIOCGIFADDR = 0x8915

# def get_ip(iface = 'eth0'):
#     ifreq = struct.pack('16sH14s', iface.encode('utf-8'), socket.AF_INET, b'\x00'*14)
#     try:
#         res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
#     except:
#         return None
#     ip = struct.unpack('16sH2x4s8x', res)[2]
#     return socket.inet_ntoa(ip)

# print(get_ip('wlo1'))


import nodes_definition as nd
print(nd.ports_by_role)
