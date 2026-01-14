import socket
import struct
import pygame

MAGIC_COOKIE = 0xabcddcba
UDP_PORT = 13122
TEAM_NAME = "PythonPlayer".ljust(32, '\x00')

class SoundManager:
    def __init__(self):
        self.enabled = True
        try:
            import pygame
            pygame.mixer.init()
            self.sounds = {
                'connect': pygame.mixer.Sound('sounds/connect.wav'),
                'hit': pygame.mixer.Sound('sounds/hit.wav'),
                'stand': pygame.mixer.Sound('sounds/stand.wav'),
                'win': pygame.mixer.Sound('sounds/win.wav'),
                'lose': pygame.mixer.Sound('sounds/lose.wav')
            }
        except Exception as e:
            print(f"Audio disabled (error: {e})")
            self.enabled = False

    def play(self, name):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].play()
            except: pass

def start_client():

    sound_player = SoundManager()

    # 1. User Input
    while True:
        try:
            num_rounds = int(input("How many rounds would you like to play? "))
            break
        except ValueError: pass

    while True:
        # 2. Discovery (UDP)
        print("Client started, listening for offer requests...")
        u_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        u_sock.bind(('', UDP_PORT))
        
        server_addr = None
        server_port = None
        
        while True:
            data, addr = u_sock.recvfrom(1024)
            if len(data) >= 39:
                cookie, m_type, port, srv = struct.unpack('!IbH32s', data[:39])
                if cookie == MAGIC_COOKIE and m_type == 0x2:
                    print(f"Received offer from {addr[0]} ({srv.decode().strip()})")
                    server_addr = addr[0]
                    server_port = port
                    break
        u_sock.close()

        # 3. Game Connection (TCP)
        try:
            t_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            t_sock.connect((server_addr, server_port))
            t_sock.sendall(struct.pack('!IbB32s', MAGIC_COOKIE, 0x3, num_rounds, TEAM_NAME.encode())) 

            wins = 0
            recv_buffer = b""

            for r in range(num_rounds):
                print(f"\n--- Round {r+1} ---")
                
                # State Variables for the Round
                cards_received = 0
                player_done = False
                round_active = True

                while round_active:
                    # Only recv if buffer is empty or incomplete (optional optimization, 
                    # but strictly, just recv if you need more data)
                    try:
                        data = t_sock.recv(1024)
                        if not data: 
                            round_active = False # Server closed connection
                            break 
                        recv_buffer += data
                    except OSError:
                        break

                    # Process full 9-byte chunks from buffer
                    while len(recv_buffer) >= 9:
                        chunk = recv_buffer[:9]
                        recv_buffer = recv_buffer[9:] # Remove processed bytes
                        
                        # Parse Packet
                        cookie, m_type, res, card = struct.unpack('!IbB3s', chunk)
                        if cookie != MAGIC_COOKIE: continue

                        cards_received += 1
                        rank, suit = card[0], card[1]

                        # --- LOGIC TO PRINT CORRECT LABELS ---
                        if rank != 0:
                            if cards_received <= 2:
                                print(f"Your Card: Rank {rank}, Suit {suit}")
                            elif cards_received == 3:
                                print(f"Dealer's Visible Card: Rank {rank}, Suit {suit}")
                            elif not player_done:
                                print(f"Your New Card: Rank {rank}, Suit {suit}")
                            else:
                                print(f"Dealer's Card: Rank {rank}, Suit {suit}")

                        # --- CHECK RESULT ---
                        if res != 0x0: 
                            status = {0x3:'WIN', 0x2:'LOSS', 0x1:'TIE'}.get(res, "UNKNOWN")
                            print(f"Result: {status}")
                            if res == 0x3: wins += 1
                            round_active = False
                            break # Exit chunk loop, move to next round

                        # --- USER INPUT ---
                        # Only ask if we have seen initial 3 cards and haven't stood yet
                        if cards_received >= 3 and not player_done:
                            move = input("Hit or Stand? (h/s): ").lower()
                            decision = b"Hittt" if move == 'h' else b"Stand"
                            t_sock.sendall(struct.pack('!IbB5s', MAGIC_COOKIE, 0x4, 0, decision))
                            
                            if move == 's':
                                player_done = True 
                
            # End of Game Stats
            win_rate = (wins / num_rounds) * 100 if num_rounds > 0 else 0
            print(f"\nFinished playing {num_rounds} rounds, win rate: {win_rate:.1f}%")
            t_sock.close()

        except Exception as e:
            print(f"Game error: {e}")

if __name__ == "__main__":
    start_client()