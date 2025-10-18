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

def listen(_port):
    # create socket
    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
        print ("socket creation failed with error %s" %(err))

    port = _port

    s.bind(('', port))
    s.listen(5) 
    if True:
        c, addr = s.accept()
        handshake_thread = threading.Thread(target=handshake, args=(c, False))
        handshake_thread.start()
        handshake_thread.join()

        # handle handshake to get peer_id of other peer
        #connection_peer_id = 1002

        #for peer in peers:
            #if peer.id == connection_peer_id:
                #peer.connection = c
        # start main sharing thread  

def connect(_peer_id):
    # create socket
    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
        print ("socket creation failed with error %s" %(err))

    index = -1
    for i in range(len(peers)):
        if peers[i].id == _peer_id:
            index = i     

    s.connect((peers[index].ip, peers[index].port))
    handshake_thread = threading.Thread(target=handshake, args=(s, True))
    handshake_thread.start()
    handshake_thread.join()
    #peers[index].connection = s 

    # handle handshake

# TODO: Handle handshake function
# TODO: Main sharing function (for thread)

def handshake(socket, source): # source is a boolean, True if the connection was started from this peer, False if it came from another peer
    # send handshake msg
    handshake_msg_out = ("P2PFILESHARINGPROJ0000000000" + (str(peer_id)))
    socket.send(handshake_msg_out.encode())
    # listen for handshake msg
    handshake_msg_in = socket.recv(32).decode()

    connected_peer_id = int(handshake_msg_in[28:32])


    if (source):
        log(f"Peer {peer_id} makes a connection to Peer {connected_peer_id}.")
    else:
        log(f"Peer {peer_id} is connected from Peer {connected_peer_id}.")

    socket.close()

    # start main thread

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

    if peer_id == peers[0].id:
        listening_thread = threading.Thread(target=listen, args=(peers[0].port,))
        listening_thread.start()
        listening_thread.join()

    else:
        connect_thread = threading.Thread(target=connect, args=(peers[0].id,))
        connect_thread.start()
        connect_thread.join()

        

if __name__ == "__main__":
    main()