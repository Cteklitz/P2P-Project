import getopt
import sys
import socket
import threading
from datetime import datetime
import time
import random
import math

peers = []
peer_id = 0
shutdown_flag = threading.Event()


def log(message):
    now = datetime.now()
    formatted = now.strftime("%Y-%m-%d %H:%M:%S")
    file.write(f"{formatted}: {message}\n")
    print(f"{formatted}: {message}")


class Peer:
    def __init__ (self, id, ip, port, has_file, bitfield):
        self.id = id
        self.ip = ip
        self.port = port
        self.has_file = has_file
        self.connection = None
        self.bitfield = bitfield # this peers bitfield
        self.preferred = False # whether this peer is a preferred neightbor
        self.interestedin = False  # whether the local peer is interested in this peer
        self.interestedfrom = False  # whether this peer is interested in the local peer
        self.optimistic = False # whether this peer is the optimistically unchoked neighbor
        self.unchoked = False # whether this peer has unchoked self (is this peer sending us data)
        self.outstanding_request = False # whether there is a current request that has not been replied to
        self.requested = -1 # the currently requested piece, -1 if none
        self.numconnections = 0
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
            temp_bitfield = [True] * int(math.ceil(file_size/piece_size))
            has = True
        else:
            temp_bitfield = [False] * int(math.ceil(file_size/piece_size))
            
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


def unchokingScheduler():
    """
    Periodically selects preferred and optimistic unchoked neighbors.
    Runs for all peers (even those with the full file).
    Enforces the num_pref_neighbors limit strictly.
    """
    global peers

    while True:
        # --- Step 1: Get interested peers ---
        interested_peers = [p for p in peers if p.connection and p.interestedfrom]

        # --- Step 2: Reset preferred & optimistic flags before re-selection ---
        for p in peers:
            if p.preferred or p.optimistic:
                was_opt = p.optimistic
                p.preferred = False
                p.optimistic = False
                if p.unchoked:
                    # send choke message
                    try:
                        p.connection.send("00010".encode())
                    except Exception as e:
                        print(f"Error sending choke to {p.id}: {e}")
                    p.unchoked = False
                    reason = "optimistic" if was_opt else "preferred"
                    log(f"Peer {peer_id} choked Peer {p.id} ({reason}).")

        # --- Step 3: Select new preferred neighbors ---
        preferred = []
        newpref = []
        if interested_peers:
            random.shuffle(interested_peers)
            preferred = interested_peers[:num_pref_neighbors]
            for p in preferred:
                if len(newpref) < num_pref_neighbors:
                    p.preferred = True
                    p.unchoked = True
                    try:
                        p.connection.send("00011".encode())  # unchoke
                    except Exception as e:
                        print(f"Error sending unchoke to {p.id}: {e}")
                    log(f"Peer {peer_id} unchoked Peer {p.id} as preferred neighbor.")
                    newpref.append(p.id)

        if preferred:
            log(f"Peer {peer_id} has the preferred neighbors {getPrefNeighborsString()}.")
        else:
            log(f"Peer {peer_id} currently has no preferred neighbors.")

        # --- Step 4: Select one optimistic unchoke neighbor (not already preferred) ---
        optimistic_peer = None
        candidates = [p for p in interested_peers if p not in preferred]
        if candidates:
            optimistic_peer = random.choice(candidates)
            optimistic_peer.optimistic = True
            optimistic_peer.unchoked = True
            try:
                optimistic_peer.connection.send("00011".encode())
            except Exception as e:
                print(f"Error sending optimistic unchoke to {optimistic_peer.id}: {e}")
            log(f"Peer {peer_id} unchoked Peer {optimistic_peer.id} as optimistic neighbor.")

        # --- Step 5: Check for global completion ---
        if allPeersComplete():
            log(f"All peers now have the complete file. Shutting down peer {peer_id}.")
            shutdown_flag.set()
            break

        # --- Step 6: Sleep until the next interval ---
        time.sleep(unchoking_interval)



def allPeersComplete():
    """Return True if all peers have finished downloading the file."""
    for p in peers:
        if not p.has_file:
            return False
    return True


def listen(_port):
    # create socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Socket created on port: ", _port)
    except socket.error as err:
        print("socket creation failed with error %s" % (err))
        return 0

    s.settimeout(1.0)
    timeouts = 0

    s.bind(('', _port))
    s.listen(5)
    print(f"Listening on port {_port}...")
    while local_peer.numconnections < len(peers) - 1:
        print("connections: ", local_peer.numconnections, " peers - 1: ", len(peers) - 1)
        try:
            c, addr = s.accept()
            handshake(c, False)
            timeouts = 0
        except socket.timeout:
            timeouts += 1 # No new connection, check condition again
        except:
            print(f"connection from {local_peer.id} to {_port} failed")
            pass


def connect(_peer_id):
    # create socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as err:
        print("socket creation failed with error %s" % (err))

    peer = getPeer(_peer_id)
    s.connect((peer.ip, peer.port))
    handshake(s, True)


def handshake(socket, source):  # source is a boolean, True if the connection was started from this peer, False if it came from another peer
    # send handshake msg
    handshake_msg_out = ("P2PFILESHARINGPROJ0000000000" + (str(peer_id)))
    socket.send(handshake_msg_out.encode())
    # listen for handshake msg
    handshake_msg_in = socket.recv(32).decode()

    handshake_header = handshake_msg_in[0:28]
    if handshake_header != "P2PFILESHARINGPROJ0000000000":
        print("Error: Handshake header invalid")
        return

    connected_peer_id = int(handshake_msg_in[28:32])  # get the peer id from the handshake msg
    connected_peer = getPeer(connected_peer_id)
    connected_peer.connection = socket  # add the socket to the peer array
    local_peer.numconnections += 1

    if source:
        log(f"Peer {peer_id} makes a connection to Peer {connected_peer_id}.")
    else:
        log(f"Peer {peer_id} is connected from Peer {connected_peer_id}.")

    # start main thread
    thread = threading.Thread(target=connection, args=(connected_peer_id,))
    thread.start()

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
    last_interest_state = None

    while not shutdown_flag.is_set(): # change to be while this peer does not have full file
        #print(f"{connected_peer.id}: {connected_peer.unchoked}")       
        #print(f"Sending from: {local_peer.id}, to: {connected_peer.id}, bitfield len: {len(connected_peer.bitfield)}, check: {checkBitField(connected_peer.bitfield)}, unchoked: {connected_peer.unchoked}")
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
            # send not intersetd msg
            # TODO: Make it so this only sends once
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

    while not shutdown_flag.is_set(): # change to end loop once all peers are connected eventually, based on timeout for testing
        try:
            t, payload = reciveMessage(connected_peer.connection)
            #print(f"{t}: {payload}")

            if t == 0:  # choke
                connected_peer.unchoked = False
                log(f"Peer {peer_id} is choked by {connected_peer.id}.")
            elif t == 1:  # unchoke
                if not connected_peer.unchoked:
                    connected_peer.unchoked = True
                    log(f"Peer {peer_id} is unchoked by {connected_peer.id}.")
            elif t == 2:  # interested
                log(f"Peer {peer_id} received the 'interested' message from {connected_peer.id}.")
                if getPrefCount() < num_pref_neighbors:
                    if not connected_peer.preferred:
                        connected_peer.preferred = True
                        connected_peer.unchoked = True
                        msg = "00011"
                        s.send(msg.encode())
                        log(f"Peer {peer_id} has the preferred neighbors {getPrefNeighborsString()}.")
                else:  # peer is interested but preferred neighbors is full
                    connected_peer.interestedfrom = True
            elif t == 3:  # not interested
                log(f"Peer {peer_id} received the 'not interested' message from {connected_peer.id}.")
                connected_peer.interestedfrom = False
            elif t == 4:  # have, recieves 4-byte piece index field
                index = int(payload, 16)
                connected_peer.bitfield[index] = True
                log(f"Peer {peer_id} received the 'have' message from {connected_peer.id} for the piece {index}")
                if not local_peer.bitfield[index]:
                    connected_peer.interestedin = True
                else:
                    connected_peer.interestedin = False
            elif t == 5:  # bitfield
                print(f"Local: {local_peer.id}, From: {connected_peer.id}; bitfield message, should not receive if not initial connection; {payload}")
                connected_peer.bitfield = decodeBitfield(payload)
            elif t == 6:  # request
                connected_peer.requested = int(payload, 16)
                print(f"recived request: {connected_peer.requested}")
            elif t == 7:  # piece
                index = int(payload[0:4], 16)
                local_peer.bitfield[index] = True
                log(f"Peer {peer_id} has downloaded the piece {index} from {connected_peer.id}. Now the number of pieces it has is {bitfieldHasCount(local_peer.bitfield)}.")
                connected_peer.outstanding_request = False

                #broadcast 'have' to all peers
                for peer in peers:
                    if peer.id != peer_id and peer.connection is not None:
                        try:
                            msg = "00054" + intToHex(index, 4)
                            peer.connection.send(msg.encode())
                        except Exception as e:
                            print(f"Error broadcasting 'have': {e}")

                if bitfieldHasCount(local_peer.bitfield) == int(math.ceil(file_size/piece_size)):
                    local_peer.has_file = True
                    log(f"Peer {peer_id} has completed the file.")
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
    global peers, peer_id, file, num_pref_neighbors, unchoking_interval, optimistic_unchoking_interval, file_name, file_size, piece_size, local_peer
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
    print(f"{len(local_peer.bitfield)}")

    # start listening for connections
    print(f"Starting peer {peer_id} on port {local_peer.port}")

    # Connect to peers that appear before this one in PeerInfo.cfg
    for peer in peers:
        if peer.id == peer_id:
            break  # Stop once we reach ourself
        connect(peer.id)

    # Start listening for incoming connections
    listening_thread = threading.Thread(target=listen, args=(local_peer.port,))
    listening_thread.start()

    # Wait until all connections are done
    #listening_thread.join()

    scheduler_thread = threading.Thread(target=unchokingScheduler)
    scheduler_thread.start()
    print("scheduler starting")

    # Wait for shutdown signal
    while not shutdown_flag.is_set():
        time.sleep(1)

    # Cleanup
    log(f"Peer {peer_id} shutting down all connections.")
    for p in peers:
        if p.connection:
            try:
                p.connection.close()
            except:
                pass
    file.close()
    print(f"Peer {peer_id} exited cleanly.")



if __name__ == "__main__":
    main()