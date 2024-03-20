#!/usr/bin/python3

"""
TFTPy - This module implements an interactive and command line TFTP client.
It also takes command line options to get/send files.

This client accepts the following options:
    $ python3 client.py [-p serv_port] server
    $ python3 client.py get [-p serv_port] server remote_file [local_file]
    $ python3 client.py put [-p serv_port] server local_file [remote_file]
    $ python3 client.py dir [-p serv_port] server

"""

import os
import sys
import textwrap
from docopt import docopt
from tftp import get_file, put_file, dir_file, check_remote_file
from utils import check_server, resolve_server_address

def main():
    doc = """\
    TFTPy: A TFTP client written in Python.

    Usage:
        cliente.py [-p SERV_PORT] <server>
        cliente.py get [-p SERV_PORT] <server> <remote_file> [<local_file>]
        cliente.py put [-p SERV_PORT] <server> <local_file> [<remote_file>]
        cliente.py dir [-p SERV_PORT] <server>

    Options:
        -h, --help                      Show this help message
        -p SERV_PORT, --port=SERV_PORT  Port number [default: 69]
    """
    args = docopt(doc)
    
    server = args["<server>"]
    server_port = int(args["--port"])
    check_server(server, server_port)

    server_name, server_ip = resolve_server_address(server, server_port)

    if args["get"]:
        remote_file = args["<remote_file>"]
        local_file = args["<local_file>"]
        if args["<local_file>"] == None:
            local_file = args["<remote_file>"]
        if not check_remote_file(server, server_port, remote_file):
            print(f"Error: The remote file '{remote_file}' does not exist on the server.")
            sys.exit(1)
        if get_file(server, server_port, remote_file, local_file) == True:
            print(f"File '{remote_file}' downloaded as '{local_file}'")

    elif args["put"]:
        local_file = args["<local_file>"]
        remote_file = args["<remote_file>"]
        if args["<remote_file>"] == None:
            remote_file = args["<local_file>"]
        if not os.path.exists(local_file):
            print(f"Error: The local file '{local_file}' does not exist.")
            sys.exit(1)
        if put_file(server, server_port, local_file, remote_file) == True:
            print(f"File '{local_file}' uploaded as '{remote_file}'")

    else:
        exec_tftp_shell(server_name, server_port, server_ip)

def exec_tftp_shell(server_name, server_port, server_ip):
    print(f"""
    *********************************************
    *                                           *
    *    \033[1;4;33mWelcome to TFTP Transfer v1.0!\033[0m         *
    *                                           *
    *                                           *
    *    Este programa permite que transfira    *
    *    facilmente arquivos usando o TFTP      *
    *    (Trivial File Transfer Protocol)       *
    *    sobre UDP                              *
    *                                           *
    *    Siga as instruções para iniciar        *
    *    as transferências de arquivos.         *
    *                                           *
    *  Copyright© Duarte Rita / Ana Figueiredo  *
    *                                           *
    *********************************************

  \033[1mServer Name:\033[0m {server_name}
  \033[1mServer IP:\033[0m {server_ip}
  \033[1mPort:\033[0m {server_port}
""")

    while True:
        try:
            cmd = input("\033[1mTftp client>\033[0m ")

            if cmd.startswith("get"):
                _, *args = cmd.split()
                if len(args) == 0:
                    print("\033[1mUsage:\033[0m get remote_file [local_file]")
                    continue

                remote_file = args[0]
                local_file = args[1] if len(args) > 1 else remote_file
                if check_server(server_name, server_port) == True:
                    continue

                if not check_remote_file(server_name, server_port, remote_file):
                    print(f"\033[41mError:\033[0m The remote file '{remote_file}' does not exist on the server.")
                    continue

                if get_file(server_ip, server_port, remote_file, local_file) == True:
                    print(f"File '{remote_file}' downloaded as '{local_file}'")

            elif cmd.startswith("put"):
                _, *args = cmd.split()
                if len(args) == 0:
                    print("\033[1mUsage:\033[0m put local_file [remote_file]")
                    continue

                local_file = args[0]
                remote_file = args[1] if len(args) > 1 else local_file
                if not os.path.exists(local_file):
                    print(f"\033[41mError:\033[0m The local file '{local_file}' does not exist.")
                    continue
                if check_server(server_name, server_port) == True:
                    continue

                if put_file(server_name, server_port, local_file, remote_file) == True:
                    print(f"File '{local_file}' uploaded as '{remote_file}'")

            elif cmd == "dir":
                dir_file(server_name, server_port)
                 # Add functionality to show file content
                with open('list.txt', 'rb') as f:
                    print(f.read().decode('utf-8'))       
                    # Delete the file afterwards
                    os.remove('list.txt')

            elif cmd == "help":
                print(
                    textwrap.dedent(
                        """
                        \033[1mCommands:\033[0m
                            get remote_file [local_file] - get a file from the server and save on your drive
                            put local_file [remote_file] - send and store a file into the server
                            dir                          - list Tftp directory files on the server
                            quit                         - exit the Tftp client
                        """
                    )
                )

            elif cmd == "quit":
                print("Exiting the Tftp client.")
                print(f"\033[1;33mGoodbye!\033[0m")
                sys.exit(0)

            else:
                print(f"\033[1mInvalid command:\033[0m '{cmd}'")

        except Exception as e:
            print(f"\033[41mError:\033[0m {e}")

if __name__ == "__main__":
    main()