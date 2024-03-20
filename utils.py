###############################################################
##                                                           ##
##                     COMMON UTILITIES                      ##
##              Mostly related to network tasks              ##
##                                                           ##
###############################################################

import subprocess
import socket
import sys


def check_server(server, server_port):
    try:
        subprocess.run(["ping", "-c", "1", server], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except subprocess.CalledProcessError:
        print(f"\033[41mError:\033[0m {server} is unreachable.")
        sys.exit(1)

#:

def resolve_server_address(server, server_port):
    try:
        # Attempt to resolve the hostname
        server_name = socket.gethostbyaddr(server)[0]
        server_ip_list = socket.gethostbyaddr(server)[2]
        server_ip = server_ip_list[0]
        return server_name, server_ip
    except socket.herror:
        server_name = server
        server_ip = server
        return server_name, server_ip
    except socket.error:
        print(f"\033[41mError:\033[0m Unable to resolve the server address for {server}")
        sys.exit(1)

#: