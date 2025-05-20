# server_actions/bedoon_kalam_actions.py
import flet as ft
import random
from bedoon_kalam_words import WORD_BANK as BK_WORD_BANK
from online_helpers import start_server_timer
import threading

def process_bedoon_kalam_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "bedoon_kalam":
        print(f"Error: Room {room_code} not found or not a Bedoon Kalam game.")
        return

    room = game_rooms_ref[room_code]
    gs = room["game_state"]
    players_data = room["players"]
    teams_data = gs.get("teams", {})

    action_processed = True
    original_status_message = gs.get("status_message")
    send_update = False # Flag to control sending pubsub update

    def get_new_bk_word_server():
        gs.setdefault("used_words", [])
        remaining = [w for w in BK_WORD_BANK if w not in gs["used_words"]]
        if not remaining:
            gs["used_words"] = []
            remaining = list(BK_WORD_BANK)
            if not remaining:
                gs["status_message"] = "لا توجد كلمات متبقية في قائمة الكلمات!"
                return "انتهت الكلمات!"
            else:
                 gs["status_message"] = "تم إعادة تعيين قائمة الكلمات المستخدمة."
        word = random.choice(remaining)
        gs["used_words"].append(word)
        return word

    def bk_timer_tick_action(game_state, remaining_time):
        game_state["timer_value"] = remaining_time

    def bk_finalize_round_and_prepare_summary(game_state):
        game_state["round_active"] = False
        
        timer_event = room.get("active_timer_event") # Check for active timer event
        if timer_event and isinstance(timer_event, threading.Event) and not timer_event.is_set():
            timer_event.set()
            print(f"Bedoon Kalam Room {room_code}: Timer event set during finalize_round.")

        game_state["phase"] = "ROUND_SUMMARY"
        if game_state.get("current_word_to_act") and game_state.get("current_word_to_act") != "انتهت الكلمات!":
            team_name_finalize = game_state.get("current_acting_team")
            if team_name_finalize:
                game_state.setdefault("word_log", []).append({
                    "team": team_name_finalize,
                    "word": game_state["current_word_to_act"],
                    "correct": False,
                    "round": game_state.get("current_game_round", 1)
                })
        summary_team = game_state.get("current_acting_team", "فريق")
        summary_round_num = game_state.get("current_game_round", 1)
        game_state["summary_for_ui"] = {
            "team_name": summary_team,
            "round_number": summary_round_num,
            "words": [log for log in game_state.get("word_log", [])
                      if log.get("team") == summary_team and log.get("round") == summary_round_num]
        }
        game_state["status_message"] = f"انتهى دور فريق {summary_team} في الجولة {summary_round_num}!"
        game_state["current_word_to_act"] = None
        game_state["timer_value"] = gs.get("round_duration_seconds", 90) # Reset timer display value


    def bk_round_end_action_timeout(game_state):
        if game_state.get("round_active"): # Only finalize if still active
            bk_finalize_round_and_prepare_summary(game_state)
            # The timer in online_helpers should also send a pubsub update.
        else:
            print(f"Bedoon Kalam Room {room_code}: Timer timeout, but round already inactive.")


    if action_type == "SETUP_TEAMS_AND_START_GAME":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            team_names_payload = payload.get("team_names", [])
            assignment_mode = payload.get("assignment_mode", "random") # New
            manual_assignments = payload.get("assignments", {})       # New

            min_players_per_team = 1
            # For Bedoon Kalam with 2 teams, this is 2 players total.
            # If you allow more teams, this calculation needs to be len(team_names_payload) * min_players_per_team
            total_players_needed = 2 # Hardcoded for 2 teams for now.

            if len(team_names_payload) != 2: # Bedoon kalam is usually 2 teams
                 gs["status_message"] = "لعبة بدون كلام تتطلب فريقين بالضبط."
                 action_processed = False
            elif len(players_data) < total_players_needed :
                 gs["status_message"] = f"تحتاج لـ {max(0, total_players_needed - len(players_data))} لاعبين إضافيين على الأقل."
                 action_processed = False
            else:
                gs["teams"] = {name: {"score": 0.0, "players": [], "current_actor_idx": -1} for name in team_names_payload}
                
                # --- Start Team Assignment Logic (similar to Taboo) ---
                if assignment_mode == "manual" and manual_assignments:
                    valid_manual = True
                    temp_team_players = {team_names_payload[0]: [], team_names_payload[1]: []}
                    
                    if len(manual_assignments) != len(players_data):
                        gs["status_message"] = "خطأ: لم يتم تخصيص جميع اللاعبين لفرق في الوضع اليدوي."
                        valid_manual = False
                    else:
                        for p_assigned_name, p_team_name in manual_assignments.items():
                            if p_assigned_name not in players_data:
                                gs["status_message"] = f"خطأ: اللاعب {p_assigned_name} غير موجود في الغرفة."
                                valid_manual = False; break
                            if p_team_name not in gs["teams"]:
                                gs["status_message"] = f"خطأ: اسم الفريق '{p_team_name}' غير صالح."
                                valid_manual = False; break
                            temp_team_players[p_team_name].append(p_assigned_name)
                    
                    if valid_manual:
                        if len(players_data) >= 2 and (not temp_team_players[team_names_payload[0]] or not temp_team_players[team_names_payload[1]]):
                            gs["status_message"] = "خطأ: يجب أن يكون هناك لاعب واحد على الأقل في كل فريق عند التخصيص اليدوي."
                            valid_manual = False

                    if valid_manual:
                        for team_n, p_list in temp_team_players.items():
                            gs["teams"][team_n]["players"] = p_list
                            for p_in_list in p_list:
                                players_data[p_in_list]["team_name"] = team_n
                        gs["status_message"] = "تم تحديد فرق بدون كلام يدوياً! الهوست يمكنه بدء أول دور."
                        print(f"Room {room_code}: Bedoon Kalam teams set up manually by host {player_name}.")
                    else:
                        action_processed = False
                        gs["teams"] = {} # Reset teams if manual assignment failed
                
                elif assignment_mode == "random":
                    player_names_list = list(players_data.keys())
                    random.shuffle(player_names_list)
                    for i, p_n_rand in enumerate(player_names_list):
                        team_idx = i % len(team_names_payload) # Should be 0 or 1 for 2 teams
                        assigned_team_name = team_names_payload[team_idx]
                        players_data[p_n_rand]["team_name"] = assigned_team_name
                        gs["teams"][assigned_team_name]["players"].append(p_n_rand)
                    gs["status_message"] = "تم تحديد فرق بدون كلام عشوائياً! الهوست يمكنه بدء أول دور."
                    print(f"Room {room_code}: Bedoon Kalam teams set up randomly by host {player_name}.")
                else:
                    gs["status_message"] = "خطأ في وضع تخصيص الفرق."
                    action_processed = False
                # --- End Team Assignment Logic ---

                if action_processed: # Only if teams were successfully assigned
                    gs["current_game_round"] = 1
                    gs["current_team_turn_idx"] = -1 # Will be incremented to 0 for first team
                    gs["round_active"] = False
                    gs["used_words"] = []
                    gs["word_log"] = []
                    gs["timer_value"] = gs.get("round_duration_seconds", 90) # Bedoon Kalam specific
                    gs["phase"] = "TEAMS_SET"
                    send_update = True # Flag for pubsub
        else:
            gs["status_message"] = "لا يمكن إعداد الفرق الآن."
            action_processed = False

    # ... (rest of your Bedoon Kalam actions: PROCEED_TO_NEXT_TURN, ACTOR_READY_START_ROUND, etc.)
    # Ensure they use the correct gs keys like "round_duration_seconds", "max_game_rounds" etc.

    elif action_type == "PROCEED_TO_NEXT_TURN":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] in ["TEAMS_SET", "ROUND_SUMMARY"]:
            team_names_list = list(teams_data.keys())
            if not team_names_list or not all(teams_data[tn].get("players") for tn in team_names_list):
                gs["status_message"] = "خطأ: لم يتم تحديد فرق بشكل صحيح أو الفرق فارغة."
                action_processed = False
            else:
                last_acting_team_name = None
                if gs["phase"] == "ROUND_SUMMARY":
                    last_acting_team_name = gs.get("summary_for_ui", {}).get("team_name")

                if last_acting_team_name and last_acting_team_name in teams_data:
                    team_info = teams_data[last_acting_team_name]
                    if team_info.get("players"):
                        team_info["current_actor_idx"] = (team_info.get("current_actor_idx", -1) + 1) % len(team_info["players"])

                gs["current_team_turn_idx"] = (gs.get("current_team_turn_idx", -1) + 1)
                if gs["current_team_turn_idx"] >= len(team_names_list):
                    gs["current_team_turn_idx"] = 0
                    gs["current_game_round"] = gs.get("current_game_round", 1) + 1
                
                gs["is_last_team_in_round"] = (gs["current_team_turn_idx"] == len(team_names_list) -1)


                if gs["current_game_round"] > gs.get("max_game_rounds",3): # Use BK specific max_game_rounds
                    gs["phase"] = "GAME_OVER"
                    gs["status_message"] = "انتهت اللعبة!"
                else:
                    next_team_name = team_names_list[gs["current_team_turn_idx"]]
                    next_team_info = teams_data[next_team_name]

                    if not next_team_info.get("players"):
                        gs["status_message"] = f"فريق {next_team_name} لا يوجد به لاعبون. تخطي الدور..."
                        action_processed = False # To prevent issues, or could try to auto-skip more gracefully
                    else:
                        if next_team_info.get("current_actor_idx", -1) < 0 or \
                           next_team_info.get("current_actor_idx", 0) >= len(next_team_info["players"]):
                           next_team_info["current_actor_idx"] = 0

                        next_actor_idx = next_team_info["current_actor_idx"]
                        next_actor = next_team_info["players"][next_actor_idx]

                        gs["current_acting_team"] = next_team_name
                        gs["current_actor_name"] = next_actor
                        gs["phase"] = "TEAM_INTRO"
                        gs["status_message"] = f"الجولة {gs['current_game_round']}. فريق {next_team_name} يستعد، {next_actor} سيمثل."
                send_update = True
        else:
            action_processed = False

    elif action_type == "ACTOR_READY_START_ROUND":
        if gs["phase"] == "TEAM_INTRO" and player_name == gs.get("current_actor_name"):
            gs["current_word_to_act"] = get_new_bk_word_server()
            if gs["current_word_to_act"] == "انتهت الكلمات!":
                # gs["status_message"] is already set by get_new_bk_word_server
                bk_finalize_round_and_prepare_summary(gs)
            else:
                gs["phase"] = "ACTING_ROUND"
                gs["round_active"] = True
                gs["timer_value"] = gs["round_duration_seconds"] # BK specific
                gs["status_message"] = f"فريق {gs['current_acting_team']} يمثل الآن. الممثل: {player_name}"
                start_server_timer(page_ref, room_code, gs["round_duration_seconds"], game_rooms_ref, bk_timer_tick_action, bk_round_end_action_timeout)
            send_update = True
        else:
            action_processed = False

    elif action_type == "WORD_GUESSED_CORRECT":
        if gs["phase"] == "ACTING_ROUND" and player_name == gs.get("current_actor_name") and gs.get("round_active"):
            acting_team_name = gs["current_acting_team"]
            if acting_team_name and acting_team_name in teams_data and gs.get("current_word_to_act"):
                teams_data[acting_team_name]["score"] = teams_data[acting_team_name].get("score",0.0) + 2.0 # BK specific score
                gs.setdefault("word_log",[]).append({
                    "team": acting_team_name, "word": gs["current_word_to_act"],
                    "correct": True, "round": gs.get("current_game_round",1)
                })
                gs["current_word_to_act"] = get_new_bk_word_server()
                if gs["current_word_to_act"] == "انتهت الكلمات!":
                    bk_finalize_round_and_prepare_summary(gs)
                send_update = True
            else: action_processed = False
        else:
            action_processed = False

    elif action_type == "SKIP_WORD":
        if gs["phase"] == "ACTING_ROUND" and player_name == gs.get("current_actor_name") and gs.get("round_active"):
            acting_team_name = gs["current_acting_team"]
            if acting_team_name and acting_team_name in teams_data and gs.get("current_word_to_act"):
                 teams_data[acting_team_name]["score"] = teams_data[acting_team_name].get("score",0.0) - 0.5 # BK specific penalty
                 gs.setdefault("word_log",[]).append({
                    "team": acting_team_name, "word": gs["current_word_to_act"],
                    "correct": False, "round": gs.get("current_game_round",1)
                })
                 gs["current_word_to_act"] = get_new_bk_word_server()
                 if gs["current_word_to_act"] == "انتهت الكلمات!":
                    bk_finalize_round_and_prepare_summary(gs)
                 send_update = True
            else: action_processed = False
        else:
            action_processed = False

    elif action_type == "RESTART_GAME_SAME_TEAMS":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "GAME_OVER":
            if not teams_data:
                gs["status_message"] = "لا يمكن إعادة اللعبة، لم يتم تحديد فرق."
                action_processed = False
            else:
                for team_name_iter in teams_data:
                    if team_name_iter in teams_data:
                        teams_data[team_name_iter]["score"] = 0.0
                        teams_data[team_name_iter]["current_actor_idx"] = -1
                gs["current_game_round"] = 0
                gs["current_team_turn_idx"] = -1
                gs["round_active"] = False
                gs["used_words"] = []
                gs["word_log"] = []
                gs["timer_value"] = gs.get("round_duration_seconds",90)
                gs["phase"] = "TEAMS_SET"
                gs["status_message"] = "تمت إعادة اللعبة بنفس الفرق. الهوست يبدأ الدور الأول."
                gs.pop("summary_for_ui", None)
                gs.pop("current_word_to_act", None)
                gs.pop("current_actor_name", None)
                gs.pop("current_acting_team", None)
                send_update = True
        else:
            action_processed = False
    else:
        action_processed = False # Default for unhandled actions
        print(f"Room {room_code}: Unknown Bedoon Kalam action type '{action_type}' or not processed.")


    # Update game_rooms_ref with potentially modified gs and players_data
    game_rooms_ref[room_code]["game_state"] = gs
    game_rooms_ref[room_code]["players"] = players_data # If player team_name was changed

    if send_update or (gs.get("status_message") != original_status_message and action_processed):
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )
        else:
             print(f"Bedoon Kalam Room {room_code}: Server page detached, cannot send pubsub for {action_type}.")