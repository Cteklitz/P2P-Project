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
    def __init__ (self, id, ip, port, has_file):
        self.id = id
        self.ip = ip
        self.port = port
        self.has_file = has_file
        self.connection = socket.socket()

def parsePeerInfo(): # returns an array of Peer object containing the data from PeerInfo.cfg
    cfg = open("PeerInfo.cfg", "r")
    lines = cfg.readlines()

    peers = []

    for line in lines:
        temp_peer = line.split(' ')
        peers.append(Peer(int(temp_peer[0]),
                          str(temp_peer[1]),
                          int(temp_peer[2]),
                          bool(temp_peer[3])))
        
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
            handshake_thread = threading.Thread(target=handshake, args=(c, False))
            handshake_thread.start()
            handshake_thread.join()
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
    handshake_thread = threading.Thread(target=handshake, args=(s, True))
    handshake_thread.start()
    handshake_thread.join()

# TODO: Main sharing function (for thread)

def handshake(socket, source): # source is a boolean, True if the connection was started from this peer, False if it came from another peer
    # send handshake msg
    handshake_msg_out = ("P2PFILESHARINGPROJ0000000000" + (str(peer_id)))
    socket.send(handshake_msg_out.encode())
    # listen for handshake msg
    handshake_msg_in = socket.recv(32).decode()

    connected_peer_id = int(handshake_msg_in[28:32]) # get the peer id from the handshake msg
    connected_peer = getPeer(connected_peer_id)
    connected_peer.connection = socket # add the socket to the peer array

    if (source):
        log(f"Peer {peer_id} makes a connection to Peer {connected_peer_id}.")
    else:
        log(f"Peer {peer_id} is connected from Peer {connected_peer_id}.")

    # start main thread
    socket.close() # temporary

def main():    
    global peers, peer_id, file
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

    listening_thread = threading.Thread(target=listen, args=(getPeer(peer_id).port,))
    listening_thread.start()

    for peer in peers:
        if peer.id == peer_id: # leave loop once self is reached in list (only connect to peers prior to self)
            break
        connect_thread = threading.Thread(target=connect, args=(peer.id,))
        connect_thread.start()
    
if __name__ == "__main__":
    main()