import struct

# Protocol Constants 
MAGIC_COOKIE = 0xabcddcba
MSG_TYPE_OFFER = 0x2
MSG_TYPE_REQUEST = 0x3
MSG_TYPE_PAYLOAD = 0x4

# UDP Port for offer discovery (defined by assignment)
UDP_PORT = 13122

# Game Result Codes
RESULT_WIN = 0x3
RESULT_LOSS = 0x2
RESULT_TIE = 0x1
RESULT_ACTIVE = 0x0

# Card suits for display purposes
SUITS = {0: '♥', 1: '♦', 2: '♣', 3: '♠'}

# Offer Messages  pack_offer

def build_offer_packet(server_port, server_name):
    """
    Build a UDP offer packet sent by the server.
    Packet Structure:
    - Magic Cookie (4 bytes)
    - Message Type: OFFER (1 byte)
    - Server TCP Port (2 bytes)
    - Server Name (32 bytes, null-padded)
    """
    name_bytes = server_name.encode('utf-8')[:32].ljust(32, b'\0')
    return struct.pack('!IBH32s', MAGIC_COOKIE, MSG_TYPE_OFFER, server_port, name_bytes)

def parse_offer_packet(data):
    """
    Parse a received UDP offer packet.

    Returns:
    - (server_port, server_name) on success
    - None if packet is invalid
    """
    try:
        if len(data) != 39: return None
        magic, m_type, port, name = struct.unpack('!IBH32s', data)
        if magic != MAGIC_COOKIE or m_type != MSG_TYPE_OFFER: return None
        return port, name.decode('utf-8').rstrip('\0')
    except:
        return None

def build_request_packet(num_rounds, team_name):
    """
    Build a TCP request packet sent by the client.
    Packet Structure:
    - Magic Cookie (4 bytes)
    - Message Type: REQUEST (1 byte)
    - Number of Rounds (1 byte)
    - Team Name (32 bytes, null-padded)
    """
    name_bytes = team_name.encode('utf-8')[:32].ljust(32, b'\0')
    return struct.pack('!IBB32s', MAGIC_COOKIE, MSG_TYPE_REQUEST, num_rounds, name_bytes)

def parse_request_packet(data):
    """
    Parse a TCP request packet from a client.

    Returns:
    - (rounds_requested, team_name) on success
    - None if packet is invalid
    """
    try:
        if len(data) != 38: return None
        magic, m_type, rounds, name = struct.unpack('!IBB32s', data)
        if magic != MAGIC_COOKIE or m_type != MSG_TYPE_REQUEST: return None
        return rounds, name.decode('utf-8').rstrip('\0')
    except:
        return None

def build_server_payload(result, rank, suit):
    """
    Server Payload: Magic(4), Type(1), Result(1), Rank(2), Suit(1)
    Total: 9 bytes
    """
    return struct.pack('!IBBHB', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, result, rank, suit)

def parse_server_payload(data):
    """
    Build a payload packet sent by the server during the game.
    """
    try:
        if len(data) != 9: return None
        magic, m_type, result, rank, suit = struct.unpack('!IBBHB', data)
        if magic != MAGIC_COOKIE or m_type != MSG_TYPE_PAYLOAD: return None
        return result, rank, suit
    except:
        return None

def build_client_payload(decision):
    """
    Parse a server payload packet.
    Returns:
    - (result_code, rank, suit) on success
    - None if packet is invalid
    """
    decision_bytes = decision.encode('utf-8')[:5] 
    return struct.pack('!IB5s', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, decision_bytes)

def parse_client_payload(data):
    """
    Build a payload packet sent by the client.
    """
    try:
        if len(data) != 10: return None 
        magic, m_type, decision = struct.unpack('!IB5s', data)
        if magic != MAGIC_COOKIE or m_type != MSG_TYPE_PAYLOAD: return None
        return decision.decode('utf-8')
    except:
        return None