import socket
import sys
from protocol import GameProtocol

# --- Config ---
TEAM = "Tussi's Team"  # Team name sent to the server
BUF_SIZE = 2048  # UDP receive buffer size


class BlackjackPlayer:
    """
    Blackjack client that discovers servers via UDP
    and plays the game over TCP.
    """
    def __init__(self):
        #Initialize client state and round tracking variables.
        self.running = True
        self.curr_hand_count = 0
        self.dealer_visible_shown = False
        self.my_turn = True

    def launch(self):
        #Main client loop: find server, connect, and play rounds.
        while self.running:
            try:
                rounds_input = input("How many rounds do you want to play? ")
                if not rounds_input.isdigit():
                    rounds = 1
                else:
                    rounds = int(rounds_input)

                print("Client started, listening for offer requests...")

                srv = self._find_server()
                if not srv: continue

                ip, port, name = srv
                print(f"Received offer from {ip}")

                self._run_session(ip, port, rounds)

            except KeyboardInterrupt:
                self.running = False

    def _find_server(self):
        #Listen for UDP broadcast offers and return server details.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            s.bind(("", GameProtocol.PORT_DISCOVERY))
            data, addr = s.recvfrom(BUF_SIZE)

            parsed = GameProtocol.parse_offer(data)
            if parsed: return addr[0], parsed[0], parsed[1]
            return None

    def _run_session(self, ip, port, rounds):
        #Connect to the server via TCP and start the game session.
        print(f"Connecting to {ip}:{port}...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(GameProtocol.create_request(rounds, TEAM))
                self._game_loop(s, rounds)
        except Exception as e:
            print(f"Connection Error: {e}")

    def _game_loop(self, sock, total_rounds):
        #Main game loop handling incoming server messages.
        rounds_done = 0
        wins = 0
        self._reset_round()

        while rounds_done < total_rounds:
            raw = self._recv_safe(sock, 9)
            if not raw: break

            parsed = GameProtocol.parse_server_payload(raw)
            if not parsed: continue

            res, rank, suit = parsed

            # --- Event Handling ---

            if res != GameProtocol.RES_ACTIVE:
                # Round Ended
                if rank != 0:
                    # If server sent the busting card with the result
                    print(f"Your card: {self._fmt(rank, suit)}")

                if res == GameProtocol.RES_WIN:
                    print("Round Result: WIN")
                    wins += 1
                elif res == GameProtocol.RES_TIE:
                    print("Round Result: TIE")
                    wins += 1  # Counting tie as win for rate calculation per some requirements
                else:
                    print("Round Result: LOSS")

                rounds_done += 1
                self._reset_round()

                if rounds_done == total_rounds:
                    rate = (wins / total_rounds) if total_rounds else 0
                    print(f"Finished playing {total_rounds} rounds, win rate: {rate:.2f}")

            else:
                # Active Game (Card Received)
                card_str = self._fmt(rank, suit)

                if self.curr_hand_count < 2:
                    # First two cards always mine
                    print(f"Your card: {card_str}")
                    self.curr_hand_count += 1
                    self.current_score = self._update_score(rank)

                elif not self.dealer_visible_shown:
                    # 3rd card total -> Dealer's first visible
                    print(f"Dealer's card: {card_str}")
                    self.dealer_visible_shown = True
                    self._make_move(sock)

                elif self.my_turn:
                    # If it's my turn, any card I get is mine (Hit result)
                    print(f"Your card: {card_str}")
                    self.current_score = self._update_score(rank)
                    if self.current_score > 21:
                        # Will receive LOSS packet next loop
                        pass
                    else:
                        self._make_move(sock)
                else:
                    print(f"Dealer draws: {card_str}")

    def _make_move(self, sock):
        #Ask the player for Hit or Stand and send the command.
        if self.current_score == 21:
            sock.sendall(GameProtocol.create_client_payload("Stand"))
            self.my_turn = False
            return

        while True:
            c = input(f"Sum: {self.current_score}. Hit or Stand? ").lower()
            if c in ['h', 'hit']:
                sock.sendall(GameProtocol.create_client_payload("Hittt"))
                return
            if c in ['s', 'stand']:
                sock.sendall(GameProtocol.create_client_payload("Stand"))
                self.my_turn = False
                return

    def _recv_safe(self, sock, n):
        #Receive exactly n bytes from the TCP socket
        buf = b''
        while len(buf) < n:
            try:
                chunk = sock.recv(n - len(buf))
                if not chunk: return None
                buf += chunk
            except:
                return None
        return buf

    def _reset_round(self):
        #Reset all round-related state variables.
        self.curr_hand_count = 0
        self.dealer_visible_shown = False
        self.my_turn = True
        self.current_score = 0
        self.aces = 0

    def _update_score(self, rank):
        #Update and return the current hand score with Ace handling.
        val = 11 if rank == 1 else (10 if rank >= 10 else rank)
        if rank == 1: self.aces += 1

        score = self.current_score + val
        temp_aces = self.aces

        while score > 21 and temp_aces > 0:
            score -= 10
            temp_aces -= 1
        return score

    def _fmt(self, r, s):
        r_n = GameProtocol.RANKS_MAP.get(r, str(r))
        s_n = GameProtocol.SUITS_MAP.get(s, '?')
        return f"{r_n}{s_n}"


if __name__ == "__main__":
    BlackjackPlayer().launch()