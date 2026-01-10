import socket
import protocol
import sys

# Configuration Part
TEAM_NAME = "Tussi's Team"
BUFFER_SIZE = 1024
RANK_NAMES = {1: 'Ace', 11: 'Jack', 12: 'Queen', 13: 'King'}


class BlackjackClient:
    """
    Blackjack client.
    - Listens for server offers via UDP
    - Connects to server via TCP
    - Manages user interaction and game state
    """

    def run(self):
        """
        Main client loop.
        Allows the user to repeatedly connect and play.
        """
        while True:
            rounds_input = input("How many rounds do you want to play? ")
            rounds = int(rounds_input) if rounds_input.isdigit() else 1

            print("Client started, listening for offer requests...")

            server_ip, server_port, server_name = self.wait_for_server_offer()
            print(f"Received offer from {server_ip}")

            self.connect_to_server(server_ip, server_port, rounds)

    def wait_for_server_offer(self):
        """
        Listen for UDP offer messages from servers.
        Returns server IP, port and name upon success.
        """
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except Exception:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        udp_socket.bind(("", protocol.UDP_PORT))

        while True:
            data, address = udp_socket.recvfrom(BUFFER_SIZE)
            offer = protocol.unpack_offer(data)

            if offer:
                server_port, server_name = offer
                udp_socket.close()
                return address[0], server_port, server_name

    def connect_to_server(self, server_ip, server_port, rounds):
        """
        Establish a TCP connection to the server and start the game.
        """
        print(f"Connecting to {server_ip}:{server_port}...")
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            tcp_socket.connect((server_ip, server_port))
            tcp_socket.sendall(protocol.pack_request(rounds, TEAM_NAME))
            self.run_game_loop(tcp_socket, rounds)

        except ConnectionResetError:
            print("Server disconnected (Connection Reset).")
        except Exception as error:
            print(f"Connection error: {error}")
        finally:
            tcp_socket.close()

    def run_game_loop(self, connection, total_rounds):
        """
        Handle all game rounds and maintain game state.
        """
        wins_count = 0
        rounds_completed = 0

        # State Variables 
        player_sum = 0
        ace_counter = 0
        cards_counter = 0
        is_player_turn = True

        while rounds_completed < total_rounds:
            try:
                data = connection.recv(BUFFER_SIZE)
                if not data:
                    break

                offset = 0
                while offset + 9 <= len(data):
                    packet = data[offset:offset + 9]
                    offset += 9

                    parsed_payload = protocol.unpack_payload_server(packet)
                    if not parsed_payload:
                        continue

                    result_code, rank, suit = parsed_payload
                    card_display = self.format_card(rank, suit)

                    # End of Round 
                    if result_code != protocol.RESULT_ACTIVE:
                        if rank != 0:
                            print(f"Drawn card: {card_display}")

                        if result_code == protocol.RESULT_WIN:
                            print("Round Result: WIN")
                            wins_count += 1
                        elif result_code == protocol.RESULT_TIE:
                            print("Round Result: TIE")
                            wins_count += 1
                        else:
                            print("Round Result: LOSS")

                        rounds_completed += 1

                        if rounds_completed < total_rounds:
                            print("\n--- New Round ---\n")

                        # Reset state for next round
                        player_sum = 0
                        ace_counter = 0
                        cards_counter = 0
                        is_player_turn = True

                        if rounds_completed == total_rounds:
                            win_rate = wins_count / total_rounds if total_rounds > 0 else 0
                            print(
                                f"Finished playing {total_rounds} rounds, "
                                f"win rate: {win_rate:.2f}"
                            )
                            return

                    # Active Round 
                    else:
                        cards_counter += 1

                        card_value = 0
                        if rank == 1:  # Ace
                            card_value = 11
                            if cards_counter <= 2 or (cards_counter > 3 and is_player_turn):
                                ace_counter += 1
                        elif rank >= 10:
                            card_value = 10
                        else:
                            card_value = rank

                        if cards_counter <= 2 or (cards_counter > 3 and is_player_turn):
                            player_sum += card_value
                            while player_sum > 21 and ace_counter > 0:
                                player_sum -= 10
                                ace_counter -= 1

                        if cards_counter <= 2:
                            print(f"Your card: {card_display}")

                        elif cards_counter == 3:
                            print(f"Dealer's card: {card_display}")
                            action = self.get_player_action(connection, player_sum)
                            if action == 'stand':
                                is_player_turn = False

                        else:
                            if is_player_turn:
                                print(f"Your card: {card_display}")

                                if player_sum <= 21:
                                    action = self.get_player_action(connection, player_sum)
                                    if action == 'stand':
                                        is_player_turn = False
                            else:
                                print(f"Dealer draws: {card_display}")

            except OSError:
                break

    def get_player_action(self, connection, current_sum):
        """
        Prompt the user for Hit or Stand and send the decision to the server.
        """
        if current_sum == 21:
            connection.sendall(protocol.pack_payload_client("Stand"))
            return 'stand'

        while True:
            move = input(f"Sum: {current_sum}. Hit or Stand? ").lower()
            if move in ['h', 'hit']:
                connection.sendall(protocol.pack_payload_client("Hittt"))
                return 'hit'
            elif move in ['s', 'stand']:
                connection.sendall(protocol.pack_payload_client("Stand"))
                return 'stand'

    def format_card(self, rank, suit):
        """
        Convert rank and suit to a human-readable string.
        """
        rank_str = RANK_NAMES.get(rank, str(rank))
        suit_str = protocol.SUITS.get(suit, '?')
        return f"{rank_str}{suit_str}"


if __name__ == "__main__":
    BlackjackClient().run()
