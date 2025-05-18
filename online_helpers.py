# online_helpers.py
import threading
import time
import random
import string

def generate_room_code(length=5): # Alphabetical only
    return ''.join(random.choices(string.ascii_uppercase, k=length))

# online_helpers.py
# ... (imports) ...
def start_server_timer(page_ref, room_code, duration_seconds, game_rooms_ref, timer_tick_action, round_end_action):
    def timer_logic():
        for i in range(duration_seconds, -1, -1):
            time.sleep(1) 
            
            # ... (room exists, round_active checks) ...
            if not (room_code in game_rooms_ref and \
                    game_rooms_ref[room_code].get("game_state", {}).get("round_active", False)):
                print(f"Timer for room {room_code} stopping early: room/gs missing or round inactive.")
                return

            room_data = game_rooms_ref[room_code] 
            game_state = room_data["game_state"]
            timer_tick_action(game_state, i) # Update server-side state

            # Adjusted PubSub send frequency
            # Send update at start, every 5 seconds, and for the last 10 seconds, and at 0
            should_send_update = (
                i == duration_seconds or  # Initial send
                i % 4 == 0 or             # Every 4 seconds
                i <= 10                   # Every second for the last 10 seconds
            )

            if should_send_update:
                if page_ref.client_storage: 
                    page_ref.pubsub.send_all_on_topic(
                        f"room_{room_code}",
                        {"type": "GAME_STATE_UPDATE", "room_state": room_data} 
                    )
                else:
                    print(f"Timer for room {room_code}: Page disconnected, stopping broadcast.")
                    return
            
            if i == 0: 
                break
        
        # ... (rest of timer end logic) ...
        if room_code in game_rooms_ref:
            room_data_final_check = game_rooms_ref[room_code]
            gs_final_check = room_data_final_check.get("game_state", {})
            if gs_final_check.get("round_active", False) and gs_final_check.get("timer_value", -1) == 0:
                print(f"Timer for room {room_code} reached 0. Processing round end.")
                round_end_action(gs_final_check) 
                if page_ref.client_storage:
                    page_ref.pubsub.send_all_on_topic(
                        f"room_{room_code}",
                        {"type": "GAME_STATE_UPDATE", "room_state": room_data_final_check}
                    )
                    print(f"Timer for room {room_code} finished naturally. Final state broadcasted.")
                else:
                    print(f"Timer for room {room_code}: Page disconnected before final broadcast on timer end.")
            # else:
            #     print(f"Timer for room {room_code} loop ended, but conditions for natural end not met or already handled.")
        # else:
        #     print(f"Timer for room {room_code} loop ended, but room no longer exists.")

    thread = threading.Thread(target=timer_logic, daemon=True)
    thread.start()
    print(f"Server timer started for room {room_code} for {duration_seconds}s with adjusted update frequency.")