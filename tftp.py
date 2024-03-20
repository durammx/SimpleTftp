"""

This module handles all TFTP related "stuff": data structures, packet
definitions, methods and protocol operations.

"""
import sys
import os
import socket
import string
import struct
from tqdm import tqdm

###############################################################
##                                                           ##
##              PROTOCOL CONSTANTS AND TYPES                 ##
##                                                           ##     
###############################################################

MAX_DATA_LEN = 512           # bytes    
MAX_BLOCK_NUMBER = 2**16 - 1 # 0..65535
INACTIVITY_TIMEOUT = 60.0    # segs
DEFAULT_MODE = 'octet'
DEFAULT_BUFFER_SIZE = 1024   # bytes

# TFTP message opcodes

RRQ = 1 # Read Request
WRQ = 2 # Write Request
DAT = 3 # Data Transfer
ACK = 4 # Acknowledge
ERR = 5 # Error packet: what the server responds if a read/write 
        # can't be processed, read and write errors during file 
        # transmission also cause this message to be sent, and 
        # transmission is then terminated. The error number gives a
        # numeric error code, followed by and ASCII error message that
        # might contain additional, operating system specific 
        # information.


ERR_NOT_DEFINED = 0
ERR_FILE_NOT_FOUND = 1 
ERR_ACCESS_VIOLATION = 2
DISK_FULL_OR_ALLOC_EXC = 3
ILLEGAL_TFTP_OP = 4
UNKOWN_TRANSF_ID = 5
FILE_ALREADY_EXISTS = 6
NO_SUCH_USER = 7

ERROR_MESSAGES = {
    ERR_NOT_DEFINED: 'Not defined, see error message(if any).',
    ERR_FILE_NOT_FOUND: 'File not found',
    ERR_ACCESS_VIOLATION: 'Access violation',
    DISK_FULL_OR_ALLOC_EXC: 'Disk full or allocation exceeded.',
    ILLEGAL_TFTP_OP: 'Illegal TFTP operation',
    UNKOWN_TRANSF_ID: 'Unkown Transfer ID',
    FILE_ALREADY_EXISTS: 'File already exists',
    NO_SUCH_USER: 'No such user'

}

#### Função de verificão de ficheiro no servidor ##############

def check_remote_file(server: str, port: int, remote_filename: str) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(INACTIVITY_TIMEOUT)
        rrq = pack_rrq(remote_filename)
        sock.sendto(rrq, (server, port))

        try:
            while True:
                packet, _ = sock.recvfrom(DEFAULT_BUFFER_SIZE)
                opcode = unpack_opcode(packet)

                if opcode == DAT:
                    # File exists, as the server responded with data
                    return True

                elif opcode == ERR:
                    error_code, _ = unpack_err(packet)

                    if error_code == ERR_FILE_NOT_FOUND:
                        # File not found, as the server responded with an error
                        return False
                    else:
                        # Other error, raise an exception
                        raise Err(error_code, "File existence check error")

                else:
                    # Unexpected packet, raise a protocol error
                    raise ProtocolError(f"Unexpected opcode {opcode}. Expected {DAT=} or {ERR=}")

        except socket.timeout:
            # Timeout occurred, assume the file does not exist
            return False

#:

###############################################################
##                                                           ##
##                 SEND AND RECEIVE FILES                    ##
##                                                           ##
###############################################################

################## Função GET #################################

def get_file(server: str, port: int, remote_filename: str, local_filename: str = None):
    """
    Obtém o arquivo remoto dado por 'remote_filename' do servidor
    através de uma conexão TFTP RRQ.
    """
 
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(INACTIVITY_TIMEOUT)
        rrq = pack_rrq(remote_filename)
        sock.sendto(rrq, (server, port))
        with open(local_filename, 'wb') as out_file:
            block_number = 1
            file_size = 0
            print(f"Downloading '{remote_filename}' from server {server}...")                
            with tqdm(desc="Downloading", unit="B", unit_scale=False, colour="red") as pbar:
                while True:
                    try:
                        # Receive data from the server
                        dat_packet, server_addr = sock.recvfrom(DEFAULT_BUFFER_SIZE)
 
                        dat_opcode = unpack_opcode(dat_packet)
 
                        if dat_opcode == DAT:
                            dat_block_number, data = unpack_dat(dat_packet)
 
                            if dat_block_number == block_number:
                                out_file.write(data)
                                ack_packet = pack_ack(block_number)
                                sock.sendto(ack_packet, server_addr)
 
                                pbar.update(len(data))
                                block_number += 1
                                file_size += len(data)
 
                                if len(data) < MAX_DATA_LEN:
                                    return True
                            else:
                                error_msg = (
                                    f"Unexpected DAT block number: {dat_block_number}."
                                    f"Expecting: {block_number}."
                                )
                                raise ProtocolError(error_msg)
 
                        elif dat_opcode == ERR:
                            error_code, error_msg = unpack_err(dat_packet)
                            raise Err(error_code, error_msg)
 
                        else:
                            error_msg = (
                                f"Invalid packet opcode: {dat_opcode}."
                                f"Expecting {DAT=} or {ERR=}."
                            )
 
                            raise ProtocolError(error_msg)
 
                    except Exception as e:
                        print(f"Error: {e}")
                        sys.exit(1)


#:

################## Função PUT #################################


def put_file(server: str, port: int, local_filename: str, remote_filename: str = None):
    """
    Coloque o arquivo local dado por 'local_filename' no servidor remoto
    através de uma conexão TFTP WRQ.
    """
    server_addr = (server, port)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(INACTIVITY_TIMEOUT)
            with open(local_filename, 'rb') as in_file:
                wrq = pack_wrq(remote_filename)
                sock.sendto(wrq, server_addr)
                block_number = 0

                file_size = os.path.getsize(local_filename)
                print(f"Uploading '{local_filename}' ({file_size} bytes) to server at {server}...")
                with tqdm(total=file_size, desc="Uploading", unit="B", unit_scale=False, colour="green") as pbar:
                    while True:
                        ack_packet, server_addr = sock.recvfrom(DEFAULT_BUFFER_SIZE)
                        ack_opcode = unpack_opcode(ack_packet)

                        if ack_opcode == ACK:
                            ack_block_number = unpack_ack(ack_packet)
                            if ack_block_number == block_number:
                                block_number += 1
                            else:
                                error_msg = (
                                    f"Unexpected ACK block number: {ack_block_number}. "
                                    f"Expecting: {block_number}."
                                )
                                raise ProtocolError(error_msg)

                            data = in_file.read(MAX_DATA_LEN)
                            dat_packet = pack_dat(block_number, data)
                            sock.sendto(dat_packet, server_addr)

                            pbar.update(len(data))

                            if len(data) < MAX_DATA_LEN:
                                return True

                        elif ack_opcode == ERR:
                            error_code, error_msg = unpack_err(ack_packet)
                            raise Err(error_code, error_msg)

                        else:
                            error_msg = (
                                f"Invalid packet opcode: {ack_opcode}. "
                                f"Expecting {ACK=} or {ERR=}."
                            )
                            raise ProtocolError(error_msg)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
 
#:

################## Função DIR #################################

def dir_file(server: str, port: int, remote_filename: str ='list.txt', local_filename: str ='list.txt'):
    """
    List directory on the server
    """
    server_addr = (server, port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(INACTIVITY_TIMEOUT)
        rrq = pack_rrq(remote_filename)
        sock.sendto(rrq, server_addr)


        with open(local_filename, 'wb') as out_file:
            block_number = 1

            while True:
                try:
                    dat_packet, server_addr = sock.recvfrom(DEFAULT_BUFFER_SIZE)
                    dat_opcode = unpack_opcode(dat_packet)

                    if dat_opcode == DAT:
                        dat_block_number, data = unpack_dat(dat_packet)

                        if dat_block_number == block_number:
                            out_file.write(data)
                            ack_packet = pack_ack(block_number)
                            sock.sendto(ack_packet, server_addr)

                            block_number += 1

                            if len(data) < MAX_DATA_LEN:
                                
                                break

                        else:
                            error_msg = (
                                f"Unexpected DAT block number: {dat_block_number}."
                                f"Expecting: {block_number}."
                            )
                            raise ProtocolError(error_msg)

                    elif dat_opcode == ERR:
                        error_code, error_msg = unpack_err(dat_packet)
                        raise Err(error_code, error_msg)

                    else:
                        error_msg = (
                            f"Invalid packet opcode: {dat_opcode}."
                            f"Expecting {DAT=} or {ERR=}."
                        )

                        raise ProtocolError(error_msg)

                except socket.timeout:
                    print("\nServer not responding. Exiting.")
                    sys.exit(1)

                except Exception as e:
                    print(f"Error: {e}")
                    sys.exit(1)

#:

##############################################################
##                                                          ## 
##              PACKET PACKING AND UNPACKING                ##
##                                                          ##
############################################################## 

def pack_rrq(filename: str, mode: str = DEFAULT_MODE) -> bytes:
    return _pack_rrq_wrq(RRQ, filename, mode)
#:


def _pack_rrq_wrq(opcode: int, filename: str, mode: str = DEFAULT_MODE) -> bytes:
    if not is_ascii_printable(filename):
        raise TFTPValueError(f"Invalid filename: {filename}. Not ASCII printable")
    filename_bytes = filename.encode() + b'\x00'
    mode_bytes = mode.encode() + b'\x00'
    fmt = f'!H{len(filename_bytes)}s{len(mode_bytes)}s'
    return struct.pack(fmt, opcode, filename_bytes, mode_bytes)
#:

def unpack_rrq(packet: bytes) -> tuple[str, str]:
    return _unpack_rrq_wrq(RRQ, packet)
#:

def _unpack_rrq_wrq(opcode: int, packet: bytes) -> tuple[str, str]:
    received_opcode = unpack_opcode(packet)
    if opcode != received_opcode:
        raise TFTPValueError(f'Invalid opcode: {received_opcode}. Expected opcode: {opcode}')
    delim_pos = packet.index(b'\x00', 2)
    filename = packet[2: delim_pos].decode()
    mode = packet[delim_pos + 1:-1].decode()
    return filename, mode
#:

def pack_dat(block_number:int, data: bytes) -> bytes:
    if not 0 <= block_number <= MAX_BLOCK_NUMBER:
        err_msg = f'Block number {block_number} larger than allowed ({MAX_BLOCK_NUMBER})'
        raise TFTPValueError(err_msg)
    if len(data) > MAX_DATA_LEN:
        err_msg = f'Data size {block_number} larger than allowed ({MAX_DATA_LEN})'
        raise TFTPValueError(err_msg)
    
    fmt = f'!HH{len(data)}s'
    return struct.pack(fmt, DAT, block_number, data)
#:

def unpack_dat(packet: bytes) -> tuple[int, bytes]:
    opcode, block_number = struct.unpack('!HH', packet[:4])
    if opcode != DAT:
        raise TFTPValueError(f'Invalid opcode {opcode}. Expecting {DAT=}.')
    return block_number, packet[4:]
#:

def pack_ack(block_number: int) -> bytes:
    if not 0 <= block_number <= MAX_BLOCK_NUMBER:
        err_msg = f'Block number {block_number} larger than allowed ({MAX_BLOCK_NUMBER})'
        raise TFTPValueError(err_msg)
    
    return struct.pack(f'!HH', ACK, block_number)
#:

def unpack_ack(packet: bytes) -> int:
    opcode, block_number = struct.unpack('!HH', packet)
    if opcode != ACK:
        raise TFTPValueError(f'Invalid opcode {opcode}. Expecting {DAT=}.')
    return block_number
#:

def pack_err(error_code: int, error_msg: str | None = None) -> bytes:
    if error_code not in ERROR_MESSAGES:
        raise TFTPValueError(f'Invalid error code {error_code}')
    if error_msg is None:
        error_msg = ERROR_MESSAGES[error_code]
    error_msg_bytes = error_msg.encode() + b'\x00'
    fmt = f'!HH{len(error_msg_bytes)}s'
    return struct.pack(fmt, ERR, error_code, error_msg_bytes)
#:

def unpack_err(packet: bytes) -> tuple[int, str]:
    opcode, error_code = struct.unpack('!HH', packet[:4])
    if opcode != ERR:
        raise TFTPValueError(f'Invalid opcode: {opcode}. Expected opcode: {ERR=}')
    return error_code, packet[4:-1].decode()
#:

def unpack_opcode(packet: bytes) -> int:
    opcode, *_ = struct.unpack('!H', packet[:2])
    if opcode not in (RRQ, WRQ, DAT, ACK, ERR):
        raise TFTPValueError(f'Invalid opcode {opcode}')
    return opcode
#:
def pack_wrq(filename: str, mode: str = DEFAULT_MODE) -> bytes:
    return _pack_rrq_wrq(WRQ, filename, mode)

def unpack_wrq(packet: bytes) -> tuple[str, str]:
    return _unpack_rrq_wrq(WRQ, packet)


###############################################################
##                                                           ##
##                  ERRORS AND EXCEPTIONS                    ##
##                                                           ##     
###############################################################

class TFTPValueError(ValueError):
    pass
#:

class NetworkError(Exception):
    """
    Any network error, like "host not found", timeouts, etc.
    """
#:
    
class ProtocolError(NetworkError):
    """
    A protocol error like unexpected or invalid opcode, wrong block 
    number, or any other invalid protocol parameter.
    """
#:
    
class Err(Exception):
    """
    An error sent by the server. It may be caused because a read/write
    can't be processed. Read and write errors during file transmission
    also cause this message to be sent, and transmission is then 
    terminated. The error number gives a numeric error code, followed
    by an ASCII error message that might contain additional, operating
    system specific information.
    """
    def __init__(self, error_code: int, error_msg: str):
        super().__init__(f'TFTP Error {error_code}')
        self.error_code = error_code
        self.error_msg = error_msg
#:

def is_ascii_printable(txt: str) -> bool:
    return set(txt).issubset(string.printable)
    # ALTERNATIVA: return not set(txt) - set(string.printable)

#: