# server_actions/taboo_actions.py
import flet as ft # For type hinting Page
import random
from taboo_words import WORD_BANK as TABOO_WORD_BANK # Assuming this is accessible
from online_helpers import start_server_timer

def process_taboo_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "taboo":
        print(f"Error: Room {room_code} not found or not a Taboo game.")
        return

    room = game_rooms_ref[room_code]
    gs = room["game_state"]
    players_data = room["players"]
    # Use "teams_online" to differentiate if offline has a different team structure
    teams_data = gs.get("teams_online", {}) 

    action_processed = True
    original_status_message = gs.get("status_message")

    def get_new_taboo_word_server():
        gs.setdefault("used_words_secrets", []) 
        available = [w for w in TABOO_WORD_BANK if isinstance(w, dict) and w.get("secret") and w["secret"] not in gs["used_words_secrets"]]
        if not available:
            gs["used_words_secrets"] = [] # Reset if exhausted in a game session
            available = [w for w in TABOO_WORD_BANK if isinstance(w, dict) and w.get("secret")]
            if not available:
                return None 
        
        word_obj = random.choice(available)
        gs["used_words_secrets"].append(word_obj["secret"])
        return word_obj

    def taboo_timer_tick_action(game_state, remaining_time):
        game_state["timer_value"] = remaining_time

    def taboo_finalize_round_server(game_state): # Renamed to avoid conflict if other games use similar names
        game_state["round_active"] = False
        game_state["phase"] = "ROUND_SUMMARY_TABOO"
        
        current_word_obj = game_state.get("current_word_obj_online")
        if current_word_obj and current_word_obj.get("secret"):
            team_name = game_state.get("current_acting_team_online")
            if team_name:
                 game_state.setdefault("word_log_online", []).append({
                    "team": team_name,
                    "word": current_word_obj["secret"],
                    "correct": False, # Considered skipped if timer runs out
                    "round": game_state.get("current_game_round_online", 1)
                })
        
        summary_team = game_state.get("current_acting_team_online", "فريق")
        summary_round_num = game_state.get("current_game_round_online", 1)
        game_state["summary_for_ui_taboo"] = {
            "team_name": summary_team,
            "round_number": summary_round_num,
            "words": [log for log in game_state.get("word_log_online", [])
                      if log.get("team") == summary_team and log.get("round") == summary_round_num]
        }
        game_state["status_message"] = f"انتهى دور فريق {summary_team} في الجولة {summary_round_num} للعبة تابو!"
        game_state["current_word_obj_online"] = None


    def taboo_round_end_action_timeout(game_state):
        taboo_finalize_round_server(game_state)


    if action_type == "SETUP_TABOO_GAME_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            team_names_payload = payload.get("team_names", [])
            if len(team_names_payload) != 2: 
                gs["status_message"] = "لعبة تابو تتطلب فريقين بالضبط."
                action_processed = False
            elif len(players_data) < 2 : 
                gs["status_message"] = f"تحتاج للاعب واحد على الأقل لكل فريق (إجمالي {len(players_data)} حالياً)."
                action_processed = False
            else:
                gs["teams_online"] = {name: {"score": 0.0, "players": [], "current_actor_idx": -1} for name in team_names_payload}
                
                player_names_list = list(players_data.keys())
                random.shuffle(player_names_list)
                for i, p_n in enumerate(player_names_list):
                    team_idx = i % len(team_names_payload) # Should be 0 or 1
                    assigned_team_name = team_names_payload[team_idx]
                    players_data[p_n]["team_name"] = assigned_team_name 
                    gs["teams_online"][assigned_team_name]["players"].append(p_n)
                
                gs["current_game_round_online"] = 1
                gs["current_team_turn_idx_online"] = -1 
                gs["round_active"] = False
                gs["used_words_secrets"] = []
                gs["word_log_online"] = []
                gs["timer_value"] = gs.get("round_duration", 60) 
                gs["phase"] = "TEAMS_SET_TABOO"
                gs["status_message"] = "تم تحديد فرق تابو! الهوست يمكنه بدء أول دور."
                print(f"Room {room_code}: Taboo teams set up by host {player_name}.")
        else:
            action_processed = False

    elif action_type == "PROCEED_TO_NEXT_TURN_TABOO":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] in ["TEAMS_SET_TABOO", "ROUND_SUMMARY_TABOO"]:
            team_names_list = list(teams_data.keys())
            if not team_names_list:
                gs["status_message"] = "خطأ: لم يتم تحديد فرق لتابو."
                action_processed = False
            else:
                if gs["phase"] == "ROUND_SUMMARY_TABOO":
                    last_acting_team_name = gs.get("summary_for_ui_taboo", {}).get("team_name")
                    if last_acting_team_name and last_acting_team_name in teams_data:
                        team_info = teams_data[last_acting_team_name]
                        if team_info.get("players"):
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

                    if not next_team_info.get("players"):
                        gs["status_message"] = f"فريق {next_team_name} (تابو) لا يوجد به لاعبون. تخطي الدور..."
                    else:
                        if next_team_info.get("current_actor_idx", -1) < 0 or \
                           next_team_info.get("current_actor_idx",0) >= len(next_team_info["players"]):
                           next_team_info["current_actor_idx"] = 0 

                        next_actor_idx = next_team_info["current_actor_idx"]
                        next_actor = next_team_info["players"][next_actor_idx]
                        
                        gs["current_acting_team_online"] = next_team_name
                        gs["current_actor_name_online"] = next_actor # Store current actor name
                        gs["phase"] = "TEAM_INTRO_TABOO"
                        gs["status_message"] = f"جولة {gs['current_game_round_online']} لتابو. فريق {next_team_name} يستعد، {next_actor} سيصف الكلمات."
        else:
            action_processed = False

    elif action_type == "ACTOR_READY_START_ROUND_TABOO":
        if gs["phase"] == "TEAM_INTRO_TABOO" and player_name == gs.get("current_actor_name_online"):
            gs["current_word_obj_online"] = get_new_taboo_word_server()
            if gs["current_word_obj_online"] is None:
                gs["status_message"] = "عذراً، انتهت كل كلمات تابو!"
                taboo_finalize_round_server(gs) 
            else:
                gs["phase"] = "ACTING_ROUND_TABOO"
                gs["round_active"] = True
                gs["timer_value"] = gs["round_duration"]
                gs["status_message"] = f"فريق {gs['current_acting_team_online']} يصف الكلمات. الواصف: {player_name}"
                start_server_timer(page_ref, room_code, gs["round_duration"], game_rooms_ref, taboo_timer_tick_action, taboo_round_end_action_timeout)
        else:
            action_processed = False
            
    elif action_type == "WORD_GUESSED_CORRECT_TABOO":
        if gs["phase"] == "ACTING_ROUND_TABOO" and player_name == gs.get("current_actor_name_online") and gs.get("round_active"):
            acting_team_name = gs["current_acting_team_online"]
            if acting_team_name and acting_team_name in teams_data:
                teams_data[acting_team_name]["score"] = teams_data[acting_team_name].get("score", 0.0) + 1.0
            
            gs.setdefault("word_log_online",[]).append({
                "team": acting_team_name, "word": gs["current_word_obj_online"]["secret"], 
                "correct": True, "round": gs.get("current_game_round_online",1)
            }) 
            gs["current_word_obj_online"] = get_new_taboo_word_server()
            if gs["current_word_obj_online"] is None:
                gs["status_message"] = "رائع! انتهت كل كلمات تابو في هذه الجولة!"
                taboo_finalize_round_server(gs)
        else:
            action_processed = False

    elif action_type == "SKIP_WORD_TABOO": 
        if gs["phase"] == "ACTING_ROUND_TABOO" and player_name == gs.get("current_actor_name_online") and gs.get("round_active"):
            acting_team_name = gs["current_acting_team_online"]
            if acting_team_name and acting_team_name in teams_data:
                 teams_data[acting_team_name]["score"] = teams_data[acting_team_name].get("score", 0.0) - 0.5
            
            gs.setdefault("word_log_online",[]).append({
                "team": acting_team_name, "word": gs["current_word_obj_online"]["secret"], 
                "correct": False, "round": gs.get("current_game_round_online",1)
            }) 
            gs["current_word_obj_online"] = get_new_taboo_word_server()
            if gs["current_word_obj_online"] is None:
                gs["status_message"] = "تخطي! انتهت كل كلمات تابو في هذه الجولة!"
                taboo_finalize_round_server(gs)
        else:
            action_processed = False

    elif action_type == "RESTART_GAME_SAME_TEAMS_TABOO":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "GAME_OVER_TABOO":
            for team_name_iter in teams_data:
                if team_name_iter in teams_data:
                    teams_data[team_name_iter]["score"] = 0.0
                    teams_data[team_name_iter]["current_actor_idx"] = -1 
            
            gs["current_game_round_online"] = 0 
            gs["current_team_turn_idx_online"] = -1
            gs["round_active"] = False
            gs["used_words_secrets"] = []
            gs["word_log_online"] = []
            gs["timer_value"] = gs.get("round_duration", 60)
            gs["phase"] = "TEAMS_SET_TABOO" 
            gs["status_message"] = "تمت إعادة لعبة تابو بنفس الفرق. الهوست يبدأ الدور الأول."
            gs.pop("summary_for_ui_taboo", None)
        else:
            action_processed = False

    game_rooms_ref[room_code]["game_state"] = gs
    if action_processed or gs.get("status_message") != original_status_message:
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )