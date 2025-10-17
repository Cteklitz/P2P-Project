import getopt
import sys
import socket
import configparser

class Peer:
    def __init__ (self, id, ip, port, has_file):
        self.id = id
        self.ip = ip
        self.port = port
        self.has_file = has_file


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


def main():    
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

    port = 6001 # TODO: get from PeerInfo.cfg

    # create socket
    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        print ("Socket successfully created")
    except socket.error as err: 
        print ("socket creation failed with error %s" %(err))

    if peer_id == 1001:
        s.bind(('', port))
        s.listen(10)
        c, addr = s.accept()
        print ('Got connection from', addr )

        # send a thank you message to the client. encoding to send byte type. 
        c.send('Thank you for connecting'.encode()) 

        # Close the connection with the client 
        c.close()
    else:
        s.connect(('127.0.0.1', port))

        # receive data from the server and decoding to get the string.
        print (s.recv(1024).decode())
        # close the connection 
        s.close() 
        

if __name__ == "__main__":
    main()