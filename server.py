import socket
import threading
import time
import random
import traceback
from protocol import GameProtocol

# --- Config ---
SERVER_ALIAS = "Cohen's Casino" # Name broadcasted to clients
IFACE = "0.0.0.0" # Listen on all network interfaces
BCAST_ADDR = "255.255.255.255" # UDP broadcast address
DELAY = 0.6   # Delay between card sends 


class DeckManager:
    def __init__(self):
        """Manages a shuffled deck of 52 playing cards."""
        self._cards = []
        self._refill()

    def _refill(self):
        """Create and shuffle a full 52-card deck."""
        self._cards = [(rank, suit) for suit in range(4) for rank in range(1, 14)]
        random.shuffle(self._cards)

    def pop_card(self):
        if not self._cards: self._refill()
        return self._cards.pop()


class CasinoServer:
    # Blackjack casino server handling TCP gameplay and UDP discovery.

    def __init__(self):
        self.active = True
        self.tcp_port = self._init_sockets()
        print(f"Server started on port {self.tcp_port}")

    def _init_sockets(self):
        # Create TCP socket for gameplay and UDP socket for broadcast

        self.sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock_tcp.bind((IFACE, 0))
        self.sock_tcp.listen(10)

        self.sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        return self.sock_tcp.getsockname()[1]

    def start_service(self):
        #Start UDP advertising and accept incoming TCP clients.
        threading.Thread(target=self._advertise, daemon=True).start()
        print("Waiting for players...")
        try:
            while self.active:
                conn, addr = self.sock_tcp.accept()
                t = threading.Thread(target=self._handle_player, args=(conn,))
                t.daemon = True
                t.start()
        except Exception as e:
            print(f"Main loop error: {e}")

    def _advertise(self):
        #Broadcast server offer packets periodically via UDP.
        packet = GameProtocol.create_offer(self.tcp_port, SERVER_ALIAS)
        while self.active:
            try:
                self.sock_udp.sendto(packet, (BCAST_ADDR, GameProtocol.PORT_DISCOVERY))
                time.sleep(1)
            except:
                pass

    def _handle_player(self, conn):
        #Handle a single connected client and play requested rounds.
        try:
            conn.settimeout(60)

            raw_req = self._recv_exact(conn, 38)
            if not raw_req: return

            parsed = GameProtocol.parse_request(raw_req)
            if not parsed: return

            rounds_num, team_name = parsed
            print(f"Team '{team_name}' connected for {rounds_num} rounds.")

            for i in range(rounds_num):
                self._play_round(conn)
                print(f"Round {i + 1} finished for {team_name}")

            # Wait a bit before closing to ensure client got everything
            time.sleep(1)

        except Exception as e:
            print(f"Error with client: {e}")
            traceback.print_exc()
        finally:
            conn.close()

    def _play_round(self, conn):
        #Execute a single Blackjack round.
        try:
            deck = DeckManager()

            # Initial Hands
            p_cards = [deck.pop_card(), deck.pop_card()]
            d_cards = [deck.pop_card(), deck.pop_card()]

            # Deal Initial Cards
            self._send_status(conn, GameProtocol.RES_ACTIVE, p_cards[0])
            time.sleep(DELAY)
            self._send_status(conn, GameProtocol.RES_ACTIVE, p_cards[1])
            time.sleep(DELAY)
            self._send_status(conn, GameProtocol.RES_ACTIVE, d_cards[0])
            time.sleep(DELAY)

            # --- Player Turn ---
            p_val = self._calc_value(p_cards)
            player_busted = False

            while p_val < 21:
                raw_cmd = self._recv_exact(conn, 10)
                if not raw_cmd: raise ConnectionResetError("Client disconnected during turn")

                cmd = GameProtocol.parse_client_payload(raw_cmd)

                if cmd == "Hittt":
                    new_card = deck.pop_card()
                    p_cards.append(new_card)
                    p_val = self._calc_value(p_cards)

                    status = GameProtocol.RES_LOSS if p_val > 21 else GameProtocol.RES_ACTIVE
                    self._send_status(conn, status, new_card)

                    if p_val > 21:
                        player_busted = True
                        return  # Round over (Player lost)
                else:
                    break  # Stand

            # --- Dealer Turn ---
            if not player_busted:
                # Reveal hidden card
                self._send_status(conn, GameProtocol.RES_ACTIVE, d_cards[1])
                time.sleep(DELAY)

                d_val = self._calc_value(d_cards)

                # Hit until 17
                while d_val < 17:
                    new_card = deck.pop_card()
                    d_cards.append(new_card)
                    d_val = self._calc_value(d_cards)

                    self._send_status(conn, GameProtocol.RES_ACTIVE, new_card)
                    time.sleep(DELAY)

                # Determine Winner
                res = self._get_winner(p_val, d_val)
                self._send_status(conn, res, (0, 0))

        except Exception as e:
            print(f"Round Logic Error: {e}")
            raise e  # Rethrow so connection closes

    def _recv_exact(self, conn, n):
        #Receive exactly n bytes from a TCP socket.
        buf = b''
        while len(buf) < n:
            try:
                chunk = conn.recv(n - len(buf))
                if not chunk: return None
                buf += chunk
            except:
                return None
        return buf

    def _send_status(self, conn, res, card):
        #Send a server payload message to the client.
        pkt = GameProtocol.create_server_payload(res, card[0], card[1])
        conn.sendall(pkt)

    def _calc_value(self, hand):
        #Calculate Blackjack hand value with Ace handling.
        val = sum([10 if c[0] >= 10 else c[0] for c in hand])
        aces = sum([1 for c in hand if c[0] == 1])
        for _ in range(aces):
            if val + 10 <= 21: val += 10
        return val

    def _get_winner(self, p, d):
        #Determine round outcome based on player and dealer values.
        if p > 21: return GameProtocol.RES_LOSS
        if d > 21: return GameProtocol.RES_WIN
        if p > d: return GameProtocol.RES_WIN
        if d > p: return GameProtocol.RES_LOSS
        return GameProtocol.RES_TIE


if __name__ == "__main__":
    CasinoServer().start_service()