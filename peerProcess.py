import getopt
import sys
import socket
import threading

peers = []
peer_id = 0

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
        print ("Socket successfully created")
    except socket.error as err: 
        print ("socket creation failed with error %s" %(err))

    port = _port

    s.bind(('', port))
    s.listen(5) 
    if True:
        c, addr = s.accept()
        print ('Got connection from', addr )

        # handle handshake to get peer_id of other peer
        connection_peer_id = 1002

        for peer in peers:
            if peer.id == connection_peer_id:
                peer.connection = c
        # start main sharing thread  

def connect(_peer_id):
    # create socket
    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        print ("Socket successfully created")
    except socket.error as err: 
        print ("socket creation failed with error %s" %(err))

    index = -1
    for i in range(len(peers)):
        if peers[i].id == _peer_id:
            index = i     

    s.connect((peers[index].ip, peers[index].port))
    peers[index].connection = s 

    # handle handshake

# TODO: Handle handshake function
# TODO: Main sharing function (for thread)

def main():    
    global peers
    # parse peers.cfg
    peers = parsePeerInfo()
    print(peers[1].has_file)
    # get port from cli arg
    if len(sys.argv) < 2:
        print("Error: No peer id provided")
        sys.exit()
    if not sys.argv[1].isnumeric():
        print("Error: Invalid peer id provided")
        sys.exit()    

    peer_id = int(sys.argv[1])

    if peer_id == peers[0].id:
        listening_thread = threading.Thread(target=listen, args=(peers[0].port,))
        listening_thread.start()
        listening_thread.join()
        peers[1].connection.send('Thank you for connecting'.encode()) 

        # Close the connection with the client 
        peers[1].connection.close()
    else:
        connect_thread = threading.Thread(target=connect, args=(peers[0].id,))
        connect_thread.start()
        connect_thread.join()

        # receive data from the server and decoding to get the string.
        print (peers[0].connection.recv(1024).decode())
        # close the connection 
        peers[0].connection.close() 
        

if __name__ == "__main__":
    main()