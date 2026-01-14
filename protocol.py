import struct


class GameProtocol:
    """
    Protocol handler for Blackjack.
    Ensures consistent binary messaging between client and server.
    """

    # --- Constants ---
    MAGIC = 0xabcddcba
    MSG_OFFER = 0x2
    MSG_REQUEST = 0x3
    MSG_PAYLOAD = 0x4

    PORT_DISCOVERY = 13122

    # Results
    RES_WIN = 0x3
    RES_LOSS = 0x2
    RES_TIE = 0x1
    RES_ACTIVE = 0x0

    # Mappings
    SUITS_MAP = {0: '♥', 1: '♦', 2: '♣', 3: '♠'}
    RANKS_MAP = {1: 'Ace', 11: 'Jack', 12: 'Queen', 13: 'King'}

    @staticmethod
    def create_offer(port, name):
        # Create a UDP offer packet broadcasted by the server.
        name_clean = name.encode('utf-8')[:32].ljust(32, b'\0')
        return struct.pack('!IBH32s', GameProtocol.MAGIC, GameProtocol.MSG_OFFER, port, name_clean)

    @staticmethod
    def parse_offer(buffer):
        #Parse a received UDP offer packet.
        if len(buffer) != 39: return None
        try:
            magic, mtype, port, name_bytes = struct.unpack('!IBH32s', buffer)
            if magic != GameProtocol.MAGIC or mtype != GameProtocol.MSG_OFFER: return None
            return port, name_bytes.decode('utf-8').rstrip('\0')
        except:
            return None

    @staticmethod
    def create_request(rounds, team_name):
        #Create a TCP request packet sent by the client.
        name_clean = team_name.encode('utf-8')[:32].ljust(32, b'\0')
        return struct.pack('!IBB32s', GameProtocol.MAGIC, GameProtocol.MSG_REQUEST, rounds, name_clean)

    @staticmethod
    def parse_request(buffer):
        #Parse a TCP request packet received by the server.
        if len(buffer) != 38: return None
        try:
            magic, mtype, rounds, name_bytes = struct.unpack('!IBB32s', buffer)
            if magic != GameProtocol.MAGIC or mtype != GameProtocol.MSG_REQUEST: return None
            return rounds, name_bytes.decode('utf-8').rstrip('\0')
        except:
            return None

    @staticmethod
    def create_server_payload(result, rank, suit):
        #Create a server gameplay payload (card or round result)
        return struct.pack('!IBBHB', GameProtocol.MAGIC, GameProtocol.MSG_PAYLOAD, result, rank, suit)

    @staticmethod
    def parse_server_payload(buffer):
        #Parse a gameplay payload sent from the server.
        if len(buffer) != 9: return None
        try:
            magic, mtype, res, rank, suit = struct.unpack('!IBBHB', buffer)
            if magic != GameProtocol.MAGIC or mtype != GameProtocol.MSG_PAYLOAD: return None
            return res, rank, suit
        except:
            return None

    @staticmethod
    def create_client_payload(cmd_str):
        #Create a gameplay command payload sent by the client.
        cmd_bytes = cmd_str.encode('utf-8')[:5]
        return struct.pack('!IB5s', GameProtocol.MAGIC, GameProtocol.MSG_PAYLOAD, cmd_bytes)

    @staticmethod
    def parse_client_payload(buffer):
        #Parse a gameplay command received from the client.
        if len(buffer) != 10: return None
        try:
            magic, mtype, cmd_bytes = struct.unpack('!IB5s', buffer)
            if magic != GameProtocol.MAGIC or mtype != GameProtocol.MSG_PAYLOAD: return None
            # Important: Strip null bytes to prevent string comparison errors
            return cmd_bytes.decode('utf-8').rstrip('\x00')
        except:
            return None