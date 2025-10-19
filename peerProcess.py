import getopt
import sys
import socket
import threading
import time

peers = []
peer_id = 0

def log(message):
    file.write(f"{time.ctime()}: {message}\n")

class Peer:
    def __init__ (self, id, ip, port, has_file, bitfield):
        self.id = id
        self.ip = ip
        self.port = port
        self.has_file = has_file
        self.connection = socket.socket()
        self.bitfield = bitfield # this peers bitfield
        self.preferred = False # whether this peer is a preferred neightbor
        self.optimistic = False # whether this peer is the optimistically unchoked neighbor
        # TODO: add fields for data rate from peer

def getPrefCount(): # returns the amount of neighbors currently prefered
    count = 0
    for peer in peers:
        if peer.preferred:
            count += 1
    return count

def getPrefNeighbors(): # returns an array of the current prefered neighbors
    out = []
    for peer in peers:
        if peer.preferred:
            out.append(peer)
    return out

def getOptimistic(): # returns the current optimistic unchoked peer, None if there is not one currently
    for peer in peers:
        if peer.optimistic:
            return peer
    return None

def encodeBitfield(bitfield): # retuns a string represnting the input bitfield
    binary = ""
    for bit in bitfield:
        if bit:
            binary += "1"
        else:
            binary += "0"
    while len(binary) % 8 != 0: # add 0's to fill last byte
        binary += "0"

    string = ''.join(chr(int(binary[i:i+8], 2)) for i in range(0, len(binary), 8)) # convert binary to string, from: https://www.geeksforgeeks.org/python/convert-binary-to-string-using-python/      
    return string

def decodeBitfield(string): # returns a bitfield array for input bitfield string
    binary = ''.join(format(ord(char), '08b') for char in string) # convert string to binary, from: https://www.geeksforgeeks.org/python/python-convert-string-to-binary/
    bitfield = []
    for i in range(len(self.bitfield)):
        if binary[i] == '1':
            bitfield.append(True)
        else:
            bitfield.append(False)
    return bitfield
    

def parsePeerInfo(): # returns an array of Peer object containing the data from PeerInfo.cfg
    cfg = open("PeerInfo.cfg", "r")
    lines = cfg.readlines()

    peers = []

    for line in lines:
        temp_peer = line.split(' ')
        temp_bitfield = []
        # initalize bitfield based on if peer has file or not
        if temp_peer[3] == "1":
            temp_bitfield = [True] * int(file_size / piece_size)
        else:
            temp_bitfield = [False] * int(file_size / piece_size)
            
        peers.append(Peer(int(temp_peer[0]),
                          str(temp_peer[1]),
                          int(temp_peer[2]),
                          bool(temp_peer[3]),
                          temp_bitfield))
        
    return peers

def getPeer(_id): # gets Peer from array based on id
    for peer in peers:
            if peer.id == _id:
                return peer

def listen(_port):
    # create socket
    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
        print ("socket creation failed with error %s" %(err))

    s.settimeout(1.0)
    timeouts = 0

    port = _port

    s.bind(('', port))
    s.listen(5) 
    while timeouts < 15: # change to end loop once all peers are connected eventually, based on timeout for testing
        try:
            c, addr = s.accept()
            #handshake_thread = threading.Thread(target=handshake, args=(c, False))
            #handshake_thread.start()
            #handshake_thread.join()
            handshake(c, False)
        except socket.timeout:
            timeouts += 1

def connect(_peer_id):
    # create socket
    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
        print ("socket creation failed with error %s" %(err))

    peer = getPeer(_peer_id)   

    s.connect((peer.ip, peer.port))
    #handshake_thread = threading.Thread(target=handshake, args=(s, True))
    #handshake_thread.start()
    #handshake_thread.join()
    handshake(s, True)

# TODO: Main sharing function (for thread)

def handshake(socket, source): # source is a boolean, True if the connection was started from this peer, False if it came from another peer
    # send handshake msg
    handshake_msg_out = ("P2PFILESHARINGPROJ0000000000" + (str(peer_id)))
    socket.send(handshake_msg_out.encode())
    # listen for handshake msg
    handshake_msg_in = socket.recv(32).decode()

    handshake_header = handshake_msg_in[0:28]
    if handshake_header != "P2PFILESHARINGPROJ0000000000":
        print("Error: Handshake header invalid")
        return
    
    connected_peer_id = int(handshake_msg_in[28:32]) # get the peer id from the handshake msg
    connected_peer = getPeer(connected_peer_id)
    connected_peer.connection = socket # add the socket to the peer array

    if (source):
        log(f"Peer {peer_id} makes a connection to Peer {connected_peer_id}.")
    else:
        log(f"Peer {peer_id} is connected from Peer {connected_peer_id}.")

    # start main thread
    thread = threading.Thread(target=connection, args=(connected_peer_id,))
    thread.start()
   
def connection(_peer_id):
    connected_peer = getPeer(_peer_id)

    # send bitfield msg
    bitfield_string = bitfieldToString(self.bitfield)

    # receive bit field msg
    
    connected_peer.connection.close() # temporary


def main():    
    global peers, peer_id, file, num_pref_neighbors, unchoking_interval, optimistic_unchoking_interval, file_name, file_size, piece_size, self

    # parse config.cfg
    cfg = open("Common.cfg", "r")
    lines = cfg.readlines()
    num_pref_neighbors = int(lines[0].split(' ')[1])
    unchoking_interval = int(lines[1].split(' ')[1])
    optimistic_unchoking_interval = int(lines[2].split(' ')[1])
    file_name = lines[3].split(' ')[1]
    file_size = int(lines[4].split(' ')[1])
    piece_size = int(lines[5].split(' ')[1])
    cfg.close()

    # parse peers.cfg
    peers = parsePeerInfo()
    # get port from cli arg
    if len(sys.argv) < 2:
        print("Error: No peer id provided")
        sys.exit()
    if not sys.argv[1].isnumeric():
        print("Error: Invalid peer id provided")
        sys.exit()    

    peer_id = int(sys.argv[1])
    file = open(f"log_peer_{peer_id}.log", "w")

    self = getPeer(peer_id)

    # start listening for connections
    listening_thread = threading.Thread(target=listen, args=(getPeer(peer_id).port,))
    listening_thread.start()

    connect_threads = []
    # attempt to connect to all peers lower in the list
    for peer in peers:
        if peer.id == peer_id: # leave loop once self is reached in list (only connect to peers prior to self)
            break
        connect_threads.append(threading.Thread(target=connect, args=(peer.id,)))
        connect_threads[len(connect_threads) - 1].start()
    
    
if __name__ == "__main__":
    main()