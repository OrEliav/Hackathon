import socket
import struct
import threading
import time
import random
import os



MAGIC_COOKIE = 0xabcddcba
UDP_PORT = 13122
TEAM_NAME = "TheAceArchitects".ljust(32, '\x00')




def get_card():
    # Rank 1-13, Suit 0-3
    return random.randint(1, 13), random.randint(0, 3)

def card_val(rank):
    if rank == 1: return 11 # Ace
    return min(rank, 10) # Face cards 10, 11, 12, 13 -> 10

def handle_game(conn, addr):
    try:
        data = conn.recv(1024)
        if not data: return
        cookie, m_type, num_rounds, team = struct.unpack('!IbB32s', data[:38])
        if cookie != MAGIC_COOKIE: return

        print(f"Starting game with {team.decode().strip()} for {num_rounds} rounds")

        for _ in range(num_rounds):
            p_hand = [get_card(), get_card()]
            d_hand = [get_card(), get_card()]
            
            # [cite_start]Initial Deal: 2 Player, 1 Dealer [cite: 37-39]
            for r, s in [p_hand[0], p_hand[1], d_hand[0]]:
                conn.sendall(struct.pack('!IbB3s', MAGIC_COOKIE, 0x4, 0x0, bytes([r, s, 0])))
                time.sleep(0.05) # Prevent packet merging

            p_sum = sum(card_val(c[0]) for c in p_hand)
            
            # Player Turn
# ... inside the loop ...
            # Player Turn
            while p_sum <= 21:
                action_data = conn.recv(1024)
                if not action_data: break
                

                _, _, _, action = struct.unpack('!IbB5s', action_data[:11])

                
                if b"Hittt" in action:
                    r, s = get_card()
                    p_hand.append((r, s))
                    p_sum += card_val(r)
                    
                    # Check bust inside the loop
                    if p_sum > 21:
                        # Send the card causing the bust with LOSS result [cite: 46, 101]
                        conn.sendall(struct.pack('!IbB3s', MAGIC_COOKIE, 0x4, 0x2, bytes([r, s, 0])))
                        break # Break while loop
                    else:
                        # Send new card with Continue (0x0) result
                        conn.sendall(struct.pack('!IbB3s', MAGIC_COOKIE, 0x4, 0x0, bytes([r, s, 0])))
                else: 
                    break # Stand

            # Dealer Turn (Only if player didn't bust)
            if p_sum <= 21:
                # Reveal hidden card
                conn.sendall(struct.pack('!IbB3s', MAGIC_COOKIE, 0x4, 0x0, bytes([d_hand[1][0], d_hand[1][1], 0]))) # [cite: 49]
                
                d_sum = sum(card_val(c[0]) for c in d_hand)
                
                while d_sum < 17: # [cite: 54]
                    r, s = get_card()
                    d_hand.append((r, s))
                    d_sum += card_val(r)
                    conn.sendall(struct.pack('!IbB3s', MAGIC_COOKIE, 0x4, 0x0, bytes([r, s, 0])))
                    time.sleep(0.05)

                # Determine Winner
                res = 0x1 # Tie default
                if d_sum > 21: res = 0x3 # Dealer Bust -> Win
                elif p_sum > d_sum: res = 0x3 
                elif d_sum > p_sum: res = 0x2 
                
                # Send Final Result
                conn.sendall(struct.pack('!IbB3s', MAGIC_COOKIE, 0x4, res, b'\x00\x00\x00'))

    except Exception as e: print(f"Err: {e}")
    finally: conn.close()

def broadcast(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    packet = struct.pack('!IbH32s', MAGIC_COOKIE, 0x2, port, TEAM_NAME.encode())
    while True:
        sock.sendto(packet, ('<broadcast>', UDP_PORT))
        time.sleep(1)

if __name__ == "__main__":
    # Get Local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except: ip = "127.0.0.1"

    t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    t.bind(('', 0)); t.listen(5)
    port = t.getsockname()[1]
    
    print(f"Server started, listening on IP address {ip}")
    threading.Thread(target=broadcast, args=(port,), daemon=True).start()
    
    while True:
        c, a = t.accept(); threading.Thread(target=handle_game, args=(c, a)).start()










