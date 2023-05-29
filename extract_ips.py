import subprocess

# Define the targets to scan (replace with appropriate IP ranges)
targets = ['192.168.0.0/24'] # List of CIDR blocks or individual IP addresses

# Execute the command to discover hosts on specified subnets
outcomes = subprocess.run([
    'nmap', '-v', '-A', '--max-retries=3', *targets,
], shell=True, text=True, universal_newlines=True, capture_output=True)
print(outcomes.stdout)

# Parse the captured output to extract IP addresses
ips = []
last_prefix = ""
for line in outcomes.stdout.split('\n'):
    prefix = line.split(' ')[0]
    if prefix == "Nmap:" or not line.strip():
        continue
    elif len(prefix) > len(last_prefix):
        last_prefix = prefix
    elif prefix[:len(last_prefix)] != last_prefix:
        break
    else:
        current_ip = f"{prefix} ({last_prefix})"
        if current_ip not in ips:
            ips.append(current_ip)

# Print discovered IP addresses
print("Discovered IP Addresses:")
print("\n".join(ips))
