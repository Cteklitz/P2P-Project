import getopt
import sys
import socket
import threading
from datetime import datetime
import time
import random

peers = []
peer_id = 0


def log(peer, message):
    now = datetime.now()
    formatted = now.strftime("%Y-%m-%d %H:%M:%S")
    peer.log_file.write(f"{formatted}: {message}\n")
    peer.log_file.flush()


class Peer:
    def __init__ (self, id, ip, port, has_file, bitfield):
        self.id = id
        self.ip = ip
        self.port = port
        self.has_file = has_file
        self.connections = []
        self.bitfield = bitfield # this peers bitfield
        self.preferred = False # whether this peer is a preferred neightbor
        self.optimistic = False # whether this peer is the optimistically unchoked neighbor
        self.unchoked = False # whether this peer has unchoked self (is this peer sending us data)
        self.outstanding_request = False # whether there is a current request that has not been replied to
        self.requested = -1 # the currently requested piece, -1 if none
        self.log_file = open(f"log_peer_{id}.log", "w")
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
    for i in range(len(local_peer.bitfield)):
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
    for i in range(len(local_peer.bitfield)):
        if not local_peer.bitfield[i]:
            needed.append(i)
    rand = random.randint(0, len(needed) - 1)
    return needed[rand]
    

def checkBitField(bitfield): # returns True if the input bitfield has any pieces that self does not have, False otherwise
    for i in range(len(bitfield)):
        if not local_peer.bitfield[i] and bitfield[i]:
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


def getPeerByPort(_port):
    for peer in peers:
        if peer.port == _port:
            return peer


def listen(_port):
    # create socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Socket created on port: ", _port)
    except socket.error as err:
        print("socket creation failed with error %s" % (err))
        return 0
    s.bind(('', _port))
    s.listen(5)
    print(f"Listening on port {_port}...")
    recievepeer = getPeerByPort(_port)
    while listenforpeers:
        c, addr = s.accept()
        print(f"Incoming connection from {addr}")
        #recievepeer.connections.append(c)
        threading.Thread(target=handshake, args=(c, False, recievepeer.id)).start()

    print("stopping listen for peer ", peer_id)


def connect(_topeer_id, _frompeer_id):
    # create socket
    topeer = getPeer(_topeer_id)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as err:
        print("socket creation failed with error %s" % (err))
    s.connect((topeer.ip, topeer.port))
    print(f"Connected to peer {_topeer_id} at {topeer.ip}:{topeer.port}")
    handshake(s, True, _frompeer_id)


def handshake(socket, source, peerid): # source is a boolean, True if the connection was started from this peer, False if it came from another peer
    # send handshake msg

    if source:  # Active peer
        # Send handshake first
        #local_ip, local_port = socket.getsockname()
        #peerfrom = getPeerByPort(local_port) # peer initiating connection
        handshake_msg_out = "P2PFILESHARINGPROJ0000000000" + str(peerid)
        socket.send(handshake_msg_out.encode())
        print(f"active Sent handshake: {handshake_msg_out}")

        # Receive handshake reply
        handshake_msg_in = socket.recv(32).decode()
        handshake_header = handshake_msg_in[0:28]
        if handshake_header != "P2PFILESHARINGPROJ0000000000":
            print("Error: Handshake header invalid")
            return
        connected_peer_id = int(handshake_msg_in[28:32])
        print(f"active Received handshake from peer {connected_peer_id}")
        log(getPeer(peerid), f"Peer {peerid} is connected to Peer {connected_peer_id}.")


    else:  # Passive peer
        # Receive handshake first
        handshake_msg_in = socket.recv(32).decode()
        handshake_header = handshake_msg_in[0:28]
        if handshake_header != "P2PFILESHARINGPROJ0000000000":
            print("Error: Handshake header invalid")
            return
        connected_peer_id = int(handshake_msg_in[28:32])
        print(f"passive Received handshake from peer {connected_peer_id}")

        # Send handshake reply
        handshake_msg_out = "P2PFILESHARINGPROJ0000000000" + str(peerid)
        socket.send(handshake_msg_out.encode())
        print(f"passive Sent handshake reply: {handshake_msg_out}")
        log(getPeer(peerid), f"Peer {peerid} is connected from Peer {connected_peer_id}")

        # Set connection
    connected_peer = getPeer(peerid)
    connected_peer.connections.append(socket)

def connection(_peer_id):
    connected_peer = getPeer(_peer_id)

    # send bitfield msg
    bitfield_string = encodeBitfield(local_peer.bitfield)
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
        if connected_peer.unchoked and not connected_peer.outstanding_request and not local_peer.has_file:
            # send request msg
            connected_peer.outstanding_request = True
            index = getRandomNeededIndex()
            msg = "00056" + intToHex(index, 4)
            print(f"requesting: {index}")
            s.send(msg.encode())           
        elif checkBitField(connected_peer.bitfield) and not connected_peer.unchoked and not local_peer.has_file:
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
                local_peer.bitfield[index] = True
                log(f"Peer {peer_id} has downloaded the piece {index} from {connected_peer.id}. Now the number of pieces it has is {bitfieldHasCount(local_peer.bitfield)}.")
                connected_peer.outstanding_request = False
                if bitfieldHasCount(local_peer.bitfield) == int(file_size/piece_size):
                    local_peer.has_file = True
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
    global peers, peer_id, file, num_pref_neighbors, unchoking_interval, optimistic_unchoking_interval, file_name, file_size, piece_size, local_peer, listenforpeers
    listenforpeers = True
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

    local_peer = getPeer(peer_id)

    # start listening for connections
    listening_thread = threading.Thread(target=listen, args=(getPeer(peer_id).port,))
    listening_thread.start()

    listening_threads = []

    for peer in peers:
        if not peers[0] == peer:
            for peer2 in peers:
                if peer != peer2:
                    connect_thread = threading.Thread(target=connect, args=(peer2.id, peer.id))
                    connect_thread.start()
                    connect_thread.join()
                else:
                    break
            listen_thread = threading.Thread(target=listen, args=(peer.port,))
            listen_thread.start()
            listening_threads.append(listen_thread)

    #listenforpeers = False
    #for thread in listening_threads:
    #    print("Joining listening thread")
    #    thread.join()

    for connecti in peers[6].connections:
        print("Connection: ", connecti)
    print("connections printed")


if __name__ == "__main__":
    main()