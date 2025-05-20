# server_actions/taboo_actions.py
import flet as ft # For type hinting Page
import random
import threading # Required for type hinting the timer event
from taboo_words import WORD_BANK as TABOO_WORD_BANK 
from online_helpers import start_server_timer # Ensure this can handle/store timer events

def process_taboo_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "taboo":
        print(f"Error: Room {room_code} not found or not a Taboo game.")
        # Optionally send error back to client via pubsub if this action originated from a client
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}", # Or a specific client if possible and desired
                {"type": "ACTION_ERROR", "message": f"خطأ في الغرفة {room_code}."}
            )
        return

    room = game_rooms_ref[room_code]
    gs = room["game_state"]
    players_data = room["players"]
    teams_data = gs.get("teams_online", {}) 

    action_processed = True
    original_status_message = gs.get("status_message")
    send_update = False # Flag to control sending pubsub update

    def get_new_taboo_word_server():
        gs.setdefault("used_words_secrets", []) 
        available = [w for w in TABOO_WORD_BANK if isinstance(w, dict) and w.get("secret") and w["secret"] not in gs["used_words_secrets"]]
        if not available:
            gs["used_words_secrets"] = [] 
            available = [w for w in TABOO_WORD_BANK if isinstance(w, dict) and w.get("secret")]
            if not available:
                gs["status_message"] = "لا توجد كلمات متبقية في قائمة الكلمات!"
                print(f"Room {room_code}: No words left in TABOO_WORD_BANK.")
                return None 
            else:
                 gs["status_message"] = "تم إعادة تعيين قائمة الكلمات المستخدمة." # Inform players if words reset
        
        word_obj = random.choice(available)
        gs["used_words_secrets"].append(word_obj["secret"])
        return word_obj

    def taboo_timer_tick_action(game_state, remaining_time):
        game_state["timer_value"] = remaining_time
        # No direct pubsub here; will be sent after action processing or by timer itself in online_helpers

    def taboo_finalize_round_server(game_state, early_end=False):
        game_state["round_active"] = False
        
        # Stop any active timer for this room if not already stopped
        timer_event = room.get("active_timer_event")
        if timer_event and isinstance(timer_event, threading.Event) and not timer_event.is_set():
            timer_event.set()
            print(f"Room {room_code}: Timer event set during finalize_round_server.")
        # room.pop("active_timer_event", None) # Clean up event, or let timer thread do it.

        current_word_obj = game_state.get("current_word_obj_online")
        if current_word_obj and current_word_obj.get("secret"):
            # If round ends (timer or early) and a word is active, it's considered skipped/not guessed
            team_name_finalize = game_state.get("current_acting_team_online")
            if team_name_finalize:
                 game_state.setdefault("word_log_online", []).append({
                    "team": team_name_finalize,
                    "word": current_word_obj["secret"],
                    "correct": False, 
                    "round": game_state.get("current_game_round_online", 1)
                })
        
        game_state["phase"] = "ROUND_SUMMARY_TABOO"
        summary_team = game_state.get("current_acting_team_online", "فريق")
        summary_round_num = game_state.get("current_game_round_online", 1)
        game_state["summary_for_ui_taboo"] = {
            "team_name": summary_team,
            "round_number": summary_round_num,
            "words": [log for log in game_state.get("word_log_online", [])
                      if log.get("team") == summary_team and log.get("round") == summary_round_num]
        }
        if early_end:
            game_state["status_message"] = f"انتهى دور فريق {summary_team} مبكراً في الجولة {summary_round_num}!"
        else:
            game_state["status_message"] = f"انتهى الوقت لدور فريق {summary_team} في الجولة {summary_round_num}!"
        
        game_state["current_word_obj_online"] = None
        game_state["timer_value"] = gs.get("round_duration", 60) # Reset for display, though round is inactive


    def taboo_round_end_action_timeout(game_state): # Called by timer when it naturally finishes
        print(f"Room {room_code}: Timer ended naturally for Taboo.")
        if game_state.get("round_active"): # Ensure round is still considered active before finalizing due to timeout
             taboo_finalize_round_server(game_state, early_end=False)
             # The timer in online_helpers should also send a pubsub update after calling this
        else:
            print(f"Room {room_code}: Timer timeout callback, but round already inactive.")


    if action_type == "SETUP_TABOO_GAME_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            team_names_payload = payload.get("team_names", [])
            assignment_mode = payload.get("assignment_mode", "random")
            manual_assignments = payload.get("assignments", {})

            if len(team_names_payload) != 2: 
                gs["status_message"] = "لعبة تابو تتطلب فريقين بالضبط."
                action_processed = False
            elif len(players_data) < 2 : # Minimum for two teams
                gs["status_message"] = f"تحتاج للاعبين اثنين على الأقل (لاعب لكل فريق). حالياً: {len(players_data)}."
                action_processed = False
            else:
                gs["teams_online"] = {name: {"score": 0.0, "players": [], "current_actor_idx": -1} for name in team_names_payload}
                
                if assignment_mode == "manual" and manual_assignments:
                    # Validate manual assignments
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
                            if p_team_name not in gs["teams_online"]:
                                gs["status_message"] = f"خطأ: اسم الفريق '{p_team_name}' غير صالح."
                                valid_manual = False; break
                            temp_team_players[p_team_name].append(p_assigned_name)
                    
                    if valid_manual:
                         # Check if each team has at least one player
                        if len(players_data) >= 2 and (not temp_team_players[team_names_payload[0]] or not temp_team_players[team_names_payload[1]]):
                            gs["status_message"] = "خطأ: يجب أن يكون هناك لاعب واحد على الأقل في كل فريق عند التخصيص اليدوي."
                            valid_manual = False

                    if valid_manual:
                        for team_n, p_list in temp_team_players.items():
                            gs["teams_online"][team_n]["players"] = p_list
                            for p_in_list in p_list:
                                players_data[p_in_list]["team_name"] = team_n
                        gs["status_message"] = "تم تحديد فرق تابو يدوياً! الهوست يمكنه بدء أول دور."
                        print(f"Room {room_code}: Taboo teams set up manually by host {player_name}.")
                    else: # Fallback or error
                        action_processed = False # Error in manual assignment
                        # Keep teams_online empty or reset to prevent partial setup
                        gs["teams_online"] = {}


                elif assignment_mode == "random":
                    player_names_list = list(players_data.keys())
                    random.shuffle(player_names_list)
                    for i, p_n_rand in enumerate(player_names_list):
                        team_idx = i % len(team_names_payload) 
                        assigned_team_name = team_names_payload[team_idx]
                        players_data[p_n_rand]["team_name"] = assigned_team_name 
                        gs["teams_online"][assigned_team_name]["players"].append(p_n_rand)
                    gs["status_message"] = "تم تحديد فرق تابو عشوائياً! الهوست يمكنه بدء أول دور."
                    print(f"Room {room_code}: Taboo teams set up randomly by host {player_name}.")
                else: # Should not happen if client sends correctly
                    gs["status_message"] = "خطأ في وضع تخصيص الفرق."
                    action_processed = False
                
                if action_processed: # Only proceed if teams were successfully assigned
                    gs["current_game_round_online"] = 1
                    gs["current_team_turn_idx_online"] = -1 
                    gs["round_active"] = False
                    gs["used_words_secrets"] = []
                    gs["word_log_online"] = []
                    gs["timer_value"] = gs.get("round_duration", 60) 
                    gs["phase"] = "TEAMS_SET_TABOO"
                    send_update = True
        else:
            gs["status_message"] = "لا يمكن إعداد الفرق الآن."
            action_processed = False

    elif action_type == "PROCEED_TO_NEXT_TURN_TABOO":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] in ["TEAMS_SET_TABOO", "ROUND_SUMMARY_TABOO"]:
            team_names_list = list(teams_data.keys())
            if not team_names_list or not all(teams_data[tn].get("players") for tn in team_names_list): # Ensure teams exist and have players
                gs["status_message"] = "خطأ: لم يتم تحديد فرق تابو بشكل صحيح أو الفرق فارغة."
                action_processed = False
            else:
                if gs["phase"] == "ROUND_SUMMARY_TABOO":
                    last_acting_team_name = gs.get("summary_for_ui_taboo", {}).get("team_name")
                    if last_acting_team_name and last_acting_team_name in teams_data:
                        team_info = teams_data[last_acting_team_name]
                        if team_info.get("players"): # Ensure players list exists
                            team_info["current_actor_idx"] = (team_info.get("current_actor_idx", -1) + 1) % len(team_info["players"])

                gs["current_team_turn_idx_online"] = (gs.get("current_team_turn_idx_online", -1) + 1)
                if gs["current_team_turn_idx_online"] >= len(team_names_list):
                    gs["current_team_turn_idx_online"] = 0
                    gs["current_game_round_online"] = gs.get("current_game_round_online", 1) + 1

                if gs["current_game_round_online"] > gs.get("max_rounds", 3):
                    gs["phase"] = "GAME_OVER_TABOO"
                    gs["status_message"] = "انتهت لعبة تابو!"
                else:
                    next_team_name = team_names_list[gs["current_team_turn_idx_online"]]
                    next_team_info = teams_data[next_team_name]

                    if not next_team_info.get("players"): # Should be caught earlier, but good check
                        gs["status_message"] = f"فريق {next_team_name} (تابو) لا يوجد به لاعبون. تخطي الدور..."
                        # This could loop infinitely if a team is empty. Logic should ensure teams are valid.
                        # For now, we assume setup validates this. If it gets here, it's an issue.
                        action_processed = False # Prevent bad state
                    else:
                        # Ensure current_actor_idx is initialized or valid
                        if next_team_info.get("current_actor_idx", -1) < 0 or \
                           next_team_info.get("current_actor_idx", 0) >= len(next_team_info["players"]):
                           next_team_info["current_actor_idx"] = 0 

                        next_actor_idx = next_team_info["current_actor_idx"]
                        next_actor = next_team_info["players"][next_actor_idx]
                        
                        gs["current_acting_team_online"] = next_team_name
                        gs["current_actor_name_online"] = next_actor 
                        gs["phase"] = "TEAM_INTRO_TABOO"
                        gs["status_message"] = f"جولة {gs['current_game_round_online']} لتابو. فريق {next_team_name} يستعد، {next_actor} سيصف الكلمات."
                send_update = True
        else:
            action_processed = False

    elif action_type == "ACTOR_READY_START_ROUND_TABOO":
        if gs["phase"] == "TEAM_INTRO_TABOO" and player_name == gs.get("current_actor_name_online"):
            gs["current_word_obj_online"] = get_new_taboo_word_server()
            if gs["current_word_obj_online"] is None:
                gs["status_message"] = "عذراً، انتهت كل كلمات تابو!" # get_new_taboo_word_server might set its own status
                taboo_finalize_round_server(gs, early_end=True) # End round as no words
            else:
                gs["phase"] = "ACTING_ROUND_TABOO"
                gs["round_active"] = True
                gs["timer_value"] = gs.get("round_duration", 60)
                gs["status_message"] = f"فريق {gs['current_acting_team_online']} يصف الكلمات. الواصف: {player_name}"
                start_server_timer(page_ref, room_code, gs["round_duration"], game_rooms_ref, taboo_timer_tick_action, taboo_round_end_action_timeout)
            send_update = True
        else:
            action_processed = False
            
    elif action_type == "WORD_GUESSED_CORRECT_TABOO":
        if gs["phase"] == "ACTING_ROUND_TABOO" and player_name == gs.get("current_actor_name_online") and gs.get("round_active"):
            acting_team_name = gs["current_acting_team_online"]
            if acting_team_name and acting_team_name in teams_data and gs.get("current_word_obj_online"):
                teams_data[acting_team_name]["score"] = teams_data[acting_team_name].get("score", 0.0) + 1.0
                gs.setdefault("word_log_online",[]).append({
                    "team": acting_team_name, "word": gs["current_word_obj_online"]["secret"], 
                    "correct": True, "round": gs.get("current_game_round_online",1)
                }) 
                gs["current_word_obj_online"] = get_new_taboo_word_server()
                if gs["current_word_obj_online"] is None:
                    # gs["status_message"] already set by get_new_taboo_word_server if no words
                    taboo_finalize_round_server(gs, early_end=True) 
                # else: gs["status_message"] = "صحيح! الكلمة التالية..." # Optional status update
                send_update = True
            else: action_processed = False # E.g. no current word
        else:
            action_processed = False

    elif action_type == "SKIP_WORD_TABOO": 
        if gs["phase"] == "ACTING_ROUND_TABOO" and player_name == gs.get("current_actor_name_online") and gs.get("round_active"):
            acting_team_name = gs["current_acting_team_online"]
            if acting_team_name and acting_team_name in teams_data and gs.get("current_word_obj_online"):
                 teams_data[acting_team_name]["score"] = teams_data[acting_team_name].get("score", 0.0) - 0.5
                 gs.setdefault("word_log_online",[]).append({
                    "team": acting_team_name, "word": gs["current_word_obj_online"]["secret"], 
                    "correct": False, "round": gs.get("current_game_round_online",1)
                }) 
                 gs["current_word_obj_online"] = get_new_taboo_word_server()
                 if gs["current_word_obj_online"] is None:
                    taboo_finalize_round_server(gs, early_end=True)
                 # else: gs["status_message"] = "تخطي! الكلمة التالية..." # Optional
                 send_update = True
            else: action_processed = False
        else:
            action_processed = False

    elif action_type == "END_ROUND_EARLY_TABOO":
        if gs["phase"] == "ACTING_ROUND_TABOO" and player_name == gs.get("current_actor_name_online") and gs.get("round_active"):
            print(f"Room {room_code}: Player {player_name} requested to end round early.")
            # Timer event stopping and other finalization is handled by taboo_finalize_round_server
            taboo_finalize_round_server(gs, early_end=True)
            send_update = True
        else:
            gs["status_message"] = "لا يمكن إنهاء الدور مبكراً الآن."
            action_processed = False


    elif action_type == "RESTART_GAME_SAME_TEAMS_TABOO":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "GAME_OVER_TABOO":
            if not teams_data: # Should not happen if game reached game over
                gs["status_message"] = "لا يمكن إعادة اللعبة، لم يتم تحديد فرق."
                action_processed = False
            else:
                for team_name_iter in teams_data:
                    if team_name_iter in teams_data: # Should always be true
                        teams_data[team_name_iter]["score"] = 0.0
                        teams_data[team_name_iter]["current_actor_idx"] = -1 # Reset actor index for fresh start
                
                gs["current_game_round_online"] = 0 # Will be incremented to 1 by PROCEED_TO_NEXT_TURN
                gs["current_team_turn_idx_online"] = -1 # Will be incremented to 0
                gs["round_active"] = False
                gs["used_words_secrets"] = []
                gs["word_log_online"] = []
                gs["timer_value"] = gs.get("round_duration", 60)
                # Go back to TEAMS_SET_TABOO, host will click "Proceed to Next Turn" to start round 1
                gs["phase"] = "TEAMS_SET_TABOO" 
                gs["status_message"] = "تمت إعادة لعبة تابو بنفس الفرق. الهوست يبدأ الدور الأول."
                gs.pop("summary_for_ui_taboo", None) # Clear previous summary
                gs.pop("current_word_obj_online", None)
                gs.pop("current_actor_name_online", None)
                gs.pop("current_acting_team_online", None)
                send_update = True
        else:
            action_processed = False
    
    # Fallback for unhandled actions or if no specific action was processed but status might need update
    else: 
        action_processed = False 
        print(f"Room {room_code}: Unknown Taboo action type '{action_type}' or not processed.")


    if not action_processed and gs.get("status_message") == original_status_message:
        # If action was not processed and status message didn't change,
        # potentially send an error message back to the originating client.
        # This depends on how you want to handle unpermitted actions.
        # For now, we rely on status_message changes or send_update flag.
        pass


    # Update game_rooms_ref with potentially modified gs (even if action_processed is False, gs might have changed status)
    game_rooms_ref[room_code]["game_state"] = gs
    game_rooms_ref[room_code]["players"] = players_data # if player data like team_name was changed

    if send_update or (gs.get("status_message") != original_status_message and action_processed):
        if page_ref.client_storage: # Ensure server context (page) is still valid
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )
        else:
            print(f"Room {room_code}: Server page detached, cannot send pubsub update for action {action_type}.")