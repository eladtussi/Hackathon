import socket
import threading
import time
import random
import protocol

# Configuration Part
SERVER_NAME = "Nadav's Casino"
SERVER_BIND_IP = "0.0.0.0"          # Bind to all interfaces
BROADCAST_IP = "255.255.255.255"    # UDP broadcast address


class BlackjackServer:
    """
    Blackjack game server.
    Handles:
    - UDP broadcast offers
    - TCP client connections
    - Blackjack game logic per client
    """

    def __init__(self):
        """Initialize TCP and UDP sockets."""
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((SERVER_BIND_IP, 0))  # Ephemeral port
        self.tcp_port = self.tcp_socket.getsockname()[1]
        self.tcp_socket.listen(5)

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        print("=== Server Started ===")
        print(f"IP: {socket.gethostbyname(socket.gethostname())}")
        print(f"Listening on TCP Port: {self.tcp_port}")

    def run(self):
        """
        Start the server:
        - Launch UDP broadcast thread
        - Accept and handle TCP client connections
        """
        threading.Thread(
            target=self.broadcast_offers_loop,
            daemon=True
        ).start()

        try:
            while True:
                client_socket, client_address = self.tcp_socket.accept()
                print(f"[+] Connection accepted from: {client_address}")

                threading.Thread(
                    target=self.handle_client_session,
                    args=(client_socket,),
                    daemon=True
                ).start()

        except Exception as error:
            print(f"Server Error: {error}")

    def broadcast_offers_loop(self):
        """
        Continuously broadcast UDP offer messages
        so clients can discover the server.
        """
        offer_packet = protocol.build_offer_packet(self.tcp_port, SERVER_NAME)

        while True:
            try:
                self.udp_socket.sendto(
                    offer_packet,
                    (BROADCAST_IP, protocol.UDP_PORT)
                )
                time.sleep(1)
            except Exception:
                pass

    def handle_client_session(self, connection):
        """
        Handle a single client connection:
        - Receive game request
        - Run requested number of rounds
        """
        client_address = connection.getpeername()

        try:
            connection.settimeout(60)

            request_data = connection.recv(1024)
            request = protocol.parse_request_packet(request_data)

            if not request:
                print(f"[-] Invalid request from {client_address}")
                return

            rounds_requested, team_name = request
            print(f"[!] Team '{team_name}' started {rounds_requested} rounds.")

            for _ in range(rounds_requested):
                self.run_single_round(connection)

            print(f"[V] Finished serving {team_name}.")

        except socket.timeout:
            print(f"[-] Timeout: {client_address} inactive.")
        except Exception as error:
            print(f"[-] Error with {client_address}: {error}")
        finally:
            connection.close()

    def run_single_round(self, connection):
        """
        Execute a single round of simplified Blackjack.
        """
        deck = [(rank, suit) for rank in range(1, 14) for suit in range(4)]
        random.shuffle(deck)

        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        # ---- Initial deal ----
        self.send_card_payload(connection, protocol.RESULT_ACTIVE, player_hand[0])
        time.sleep(0.05)
        self.send_card_payload(connection, protocol.RESULT_ACTIVE, player_hand[1])
        time.sleep(0.05)

        # Dealer visible card
        self.send_card_payload(connection, protocol.RESULT_ACTIVE, dealer_hand[0])

        player_score = self.compute_hand_score(player_hand)

        # -------- Player Turn --------
        while player_score < 21:
            try:
                decision = protocol.parse_client_payload(connection.recv(1024))

                if decision == "Hittt":
                    drawn_card = deck.pop()
                    player_hand.append(drawn_card)
                    player_score = self.compute_hand_score(player_hand)

                    if player_score > 21:
                        self.send_card_payload(
                            connection,
                            protocol.RESULT_LOSS,
                            drawn_card
                        )
                        return
                    else:
                        self.send_card_payload(
                            connection,
                            protocol.RESULT_ACTIVE,
                            drawn_card
                        )
                else:
                    break
            except Exception:
                return

        # -------- Dealer Turn --------
        self.send_card_payload(connection, protocol.RESULT_ACTIVE, dealer_hand[1])
        time.sleep(0.5)

        dealer_score = self.compute_hand_score(dealer_hand)

        while dealer_score < 17:
            drawn_card = deck.pop()
            dealer_hand.append(drawn_card)
            dealer_score = self.compute_hand_score(dealer_hand)

            self.send_card_payload(
                connection,
                protocol.RESULT_ACTIVE,
                drawn_card
            )
            time.sleep(0.5)

        # -------- Determine Result --------
        if player_score > 21:
            round_result = protocol.RESULT_LOSS
        elif dealer_score > 21:
            round_result = protocol.RESULT_WIN
        elif player_score > dealer_score:
            round_result = protocol.RESULT_WIN
        elif dealer_score > player_score:
            round_result = protocol.RESULT_LOSS
        else:
            round_result = protocol.RESULT_TIE

        self.send_card_payload(connection, round_result, (0, 0))

    def send_card_payload(self, connection, result_code, card):
        """
        Send a card payload to the client using the protocol layer.
        """
        connection.sendall(
            protocol.build_server_payload(
                result_code,
                card[0],
                card[1]
            )
        )

    def compute_hand_score(self, cards):
        """
        Compute blackjack hand score with Ace adjustment.
        """
        total_value = 0
        ace_count = 0

        for rank, _ in cards:
            if rank == 1:
                ace_count += 1
                total_value += 11
            elif rank >= 10:
                total_value += 10
            else:
                total_value += rank

        while total_value > 21 and ace_count > 0:
            total_value -= 10
            ace_count -= 1

        return total_value


if __name__ == "__main__":
    BlackjackServer().run()
