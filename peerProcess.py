import getopt
import sys
import socket
import threading
import time
import random

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
        self.unchoked = False # whether this peer has unchoked self (is this peer sending us data)
        self.outstanding_request = False # whether there is a current request that has not been replied to
        self.requested = -1 # the currently requested piece, -1 if none
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

def getPrefNeighborsString():
    out = ""
    pref = getPrefNeighbors()
    for peer in pref:
        out += str(peer.id)
        out += ","
    out = out[0:len(out) - 1] # remove trailing comma
    return out

def getOptimistic(): # returns the current optimistic unchoked peer, None if there is not one currently
    for peer in peers:
        if peer.optimistic:
            return peer
    return None

def encodeBitfield(bitfield): # retuns a hex string represnting the input bitfield
    binary = ""
    for bit in bitfield:
        if bit:
            binary += "1"
        else:
            binary += "0"
    while len(binary) % 8 != 0: # add 0's to fill last byte
        binary += "0"

    hex_value = hex(int(binary, 2))[2:]
    required_hex_digits = len(binary) // 4
    hex_string = hex_value.zfill(required_hex_digits)
    return hex_string

def decodeBitfield(string): # returns a bitfield array for input bitfield hex string
    binary = bin(int(string, 16))[2:]
    required_binary_digits = len(string) * 4
    binary = binary.zfill(required_binary_digits)

    bitfield = []
    for i in range(len(self.bitfield)):
        if binary[i] == '1':
            bitfield.append(True)
        else:
            bitfield.append(False)
    return bitfield

def bitfieldHasCount(bitfield): # returns the amount of pieces present in a bitfield
    count = 0
    for bit in bitfield:
        if bit:
            count += 1
    return count

def getRandomNeededIndex(): # returns the index of a random bit self needs
    needed = []
    for i in range(len(self.bitfield)):
        if not self.bitfield[i]:
            needed.append(i)
    rand = random.randint(0, len(needed) - 1)
    return needed[rand]
    

def checkBitField(bitfield): # returns True if the input bitfield has any pieces that self does not have, False otherwise
    for i in range(len(bitfield)):
        if not self.bitfield[i] and bitfield[i]:
            return True
    return False

def intToHex(num, len):
    hex_num = hex(num)[2:]
    hex_num = hex_num.zfill(len) # pad msg with 0s 
    return hex_num

def parsePeerInfo(): # returns an array of Peer object containing the data from PeerInfo.cfg
    cfg = open("PeerInfo.cfg", "r")
    lines = cfg.readlines()

    peers = []

    for line in lines:
        temp_peer = line.split(' ')
        temp_bitfield = []
        has = False
        # initalize bitfield based on if peer has file or not
        if temp_peer[3] == "1":
            temp_bitfield = [True] * int(file_size / piece_size)
            has = True
        else:
            temp_bitfield = [False] * int(file_size / piece_size)
            
        peers.append(Peer(int(temp_peer[0]),
                          str(temp_peer[1]),
                          int(temp_peer[2]),
                          has,
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
        #print(timeouts)
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
    bitfield_string = encodeBitfield(self.bitfield)
    bitfield_msg_len = intToHex(len(bitfield_string) + 1, 4)
    bitfield_msg = str(bitfield_msg_len)

    bitfield_msg += "5"
    bitfield_msg += bitfield_string

    connected_peer.connection.send(bitfield_msg.encode())

    # receive bit field msg
    t, bitfield_string = reciveMessage(connected_peer.connection)
    if t != 5:
        print(f"Error: expected msg type 5, received: {t}")
        return
    connected_peer.bitfield = decodeBitfield(bitfield_string)

    sending_thread = threading.Thread(target=sending, args=(_peer_id,))
    receiving_thread = threading.Thread(target=receiving, args=(_peer_id,))
    sending_thread.start()
    receiving_thread.start()
    sending_thread.join()
    receiving_thread.join()
    
    connected_peer.connection.close() # temporary

def sending(_peer_id): # loop to send msgs to a peer
    connected_peer = getPeer(_peer_id)
    s = connected_peer.connection
    s.settimeout(10.0)
    while True: # change to be while this peer does not have full file
        #print(f"{connected_peer.id}: {connected_peer.unchoked}")       
        if connected_peer.unchoked and not connected_peer.outstanding_request and not self.has_file:
            # send request msg
            connected_peer.outstanding_request = True
            index = getRandomNeededIndex()
            msg = "00056" + intToHex(index, 4)
            print(f"requesting: {index}")
            s.send(msg.encode())           
        elif checkBitField(connected_peer.bitfield) and not connected_peer.unchoked and not self.has_file:
            # send interested msg
            msg = "00012"
            s.send(msg.encode())
            time.sleep(1)
        elif not checkBitField(connected_peer.bitfield) and connected_peer.unchoked:
            msg = "00013"
            s.send(msg.encode())
            time.sleep(1)

        if connected_peer.preferred or connected_peer.optimistic:
            if connected_peer.requested != -1:
                # send piece
                print(f"sending: {connected_peer.requested}")
                msg = "0005" + "7" + intToHex(connected_peer.requested, 4) # TODO: Add data to msg
                s.send(msg.encode())
                connected_peer.requested = -1


def receiving(_peer_id): # loop to receive msgs from a peer
    connected_peer = getPeer(_peer_id)
    s = connected_peer.connection

    s.settimeout(2.5)
    timeouts = 0

    while timeouts < 15: # change to end loop once all peers are connected eventually, based on timeout for testing
        try:
            t, payload = reciveMessage(connected_peer.connection)
            #print(f"{t}: {payload}")

            if t == 0: # choke
                connected_peer.unchoked = False
                log(f"Peer {peer_id} is choked by {connected_peer.id}.")
            elif t == 1: # unchoke
                if not connected_peer.unchoked:
                    connected_peer.unchoked = True
                    log(f"Peer {peer_id} is unchoked by {connected_peer.id}.")
            elif t == 2: # interested
                log(f"Peer {peer_id} received the 'interested' message from {connected_peer.id}.")
                if getPrefCount() < num_pref_neighbors: # TODO: propper choking/unchoking
                    if not connected_peer.preferred:
                        connected_peer.preferred = True
                        msg = "00011"
                        s.send(msg.encode())
                        log(f"Peer {peer_id} has the preferred neighbors {getPrefNeighborsString()}.")
            elif t == 6: # request
                connected_peer.requested = int(payload, 16)
                print(f"recived request: {connected_peer.requested}")
            elif t == 7: # piece
                index = int(payload[0:4], 16)
                self.bitfield[index] = True
                log(f"Peer {peer_id} has downloaded the piece {index} from {connected_peer.id}. Now the number of pieces it has is {bitfieldHasCount(self.bitfield)}.")
                connected_peer.outstanding_request = False
                if bitfieldHasCount(self.bitfield) == int(file_size/piece_size):
                    self.has_file = True
                    return
                    # TODO: handle stuff for self having full file
                # TODO: process data, write to file
        except socket.timeout:
            timeouts += 1


def reciveMessage(socket): # recives a msg, returns a tuple of the type and payload
    msg_len = socket.recv(4).decode() # get msg len
    length = int(msg_len, 16)
    msg = socket.recv(length).decode() # get msg
    #print(msg)
    type = int(msg[0])
    payload = msg[1:]
    return (type,payload)


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