# server_actions/bedoon_kalam_actions.py
import flet as ft # For type hinting Page
import random
from bedoon_kalam_words import WORD_BANK as BK_WORD_BANK # Assuming this is accessible
from online_helpers import start_server_timer # For the online timer

def process_bedoon_kalam_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "bedoon_kalam":
        print(f"Error: Room {room_code} not found or not a Bedoon Kalam game.")
        return

    room = game_rooms_ref[room_code] # Use passed game_rooms_ref
    gs = room["game_state"]
    players_data = room["players"] 
    teams_data = gs.get("teams", {}) 

    action_processed = True
    original_status_message = gs.get("status_message")

    def get_new_bk_word_server(): 
        gs.setdefault("used_words", [])
        remaining = [w for w in BK_WORD_BANK if w not in gs["used_words"]]
        if not remaining:
            gs["used_words"] = [] 
            remaining = list(BK_WORD_BANK)
            if not remaining: return "انتهت الكلمات!" 
        word = random.choice(remaining)
        gs["used_words"].append(word)
        return word

    def bk_timer_tick_action(game_state, remaining_time): 
        game_state["timer_value"] = remaining_time
        # No pubsub send here, start_server_timer handles periodic updates

    def bk_finalize_round_and_prepare_summary(game_state): 
        game_state["round_active"] = False
        game_state["phase"] = "ROUND_SUMMARY"
        
        if game_state.get("current_word_to_act") and game_state.get("current_word_to_act") != "انتهت الكلمات!":
            team_name = game_state.get("current_acting_team")
            if team_name: 
                game_state.setdefault("word_log", []).append({
                    "team": team_name, 
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
        # Pubsub send will be handled by start_server_timer or the main logic after this call

    def bk_round_end_action_timeout(game_state): 
        bk_finalize_round_and_prepare_summary(game_state)


    if action_type == "SETUP_TEAMS_AND_START_GAME":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            team_names_payload = payload.get("team_names", [])
            min_players_per_team = 1 
            total_players_needed = len(team_names_payload) * min_players_per_team
            
            if len(team_names_payload) < 2:
                 gs["status_message"] = "تحتاج لفريقين على الأقل."
                 action_processed = False
            elif len(players_data) < total_players_needed : 
                 gs["status_message"] = f"تحتاج لـ {max(0, total_players_needed - len(players_data))} لاعبين إضافيين على الأقل للفرق المحددة."
                 action_processed = False
            else:
                gs["teams"] = {name: {"score": 0.0, "players": [], "current_actor_idx": -1} for name in team_names_payload}
                
                player_names_list = list(players_data.keys())
                random.shuffle(player_names_list) 
                for i, p_n in enumerate(player_names_list):
                    team_idx = i % len(team_names_payload)
                    assigned_team_name = team_names_payload[team_idx]
                    players_data[p_n]["team_name"] = assigned_team_name
                    gs["teams"][assigned_team_name]["players"].append(p_n)
                
                gs["current_game_round"] = 1 
                gs["current_team_turn_idx"] = -1 
                gs["round_active"] = False
                gs["used_words"] = []
                gs["word_log"] = []
                gs["timer_value"] = gs.get("round_duration_seconds", 90) 

                gs["phase"] = "TEAMS_SET" 
                gs["status_message"] = "تم تحديد الفرق! الهوست يمكنه بدء أول دور."
                print(f"Room {room_code}: Bedoon Kalam teams set up by host {player_name}.")
        else:
            action_processed = False

    elif action_type == "PROCEED_TO_NEXT_TURN": 
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] in ["TEAMS_SET", "ROUND_SUMMARY"]:
            team_names_list = list(teams_data.keys()) 
            if not team_names_list:
                gs["status_message"] = "خطأ: لم يتم تحديد فرق."
                action_processed = False
            else:
                last_acting_team_name = None
                if gs["phase"] == "ROUND_SUMMARY": 
                    last_acting_team_name = gs.get("summary_for_ui", {}).get("team_name")
                
                # Advance actor for the team that just played
                if last_acting_team_name and last_acting_team_name in teams_data:
                    team_info = teams_data[last_acting_team_name]
                    if team_info.get("players"): 
                        team_info["current_actor_idx"] = (team_info.get("current_actor_idx", -1) + 1) % len(team_info["players"])

                # Determine next team for the turn
                gs["current_team_turn_idx"] = (gs.get("current_team_turn_idx", -1) + 1)
                if gs["current_team_turn_idx"] >= len(team_names_list): 
                    gs["current_team_turn_idx"] = 0
                    gs["current_game_round"] = gs.get("current_game_round", 1) + 1

                if gs["current_game_round"] > gs.get("max_game_rounds",3):
                    gs["phase"] = "GAME_OVER"
                    gs["status_message"] = "انتهت اللعبة!"
                else:
                    next_team_name = team_names_list[gs["current_team_turn_idx"]]
                    next_team_info = teams_data[next_team_name]
                    
                    if not next_team_info.get("players"): 
                        gs["status_message"] = f"فريق {next_team_name} لا يوجد به لاعبون. تخطي الدور..."
                        # This might need a loop or recursive call if multiple empty teams, or host intervention
                        action_processed = True # Send update to reflect skip
                    else:
                        # Ensure actor index is valid for the new team
                        if next_team_info.get("current_actor_idx", -1) < 0 or \
                           next_team_info.get("current_actor_idx", 0) >= len(next_team_info["players"]):
                            next_team_info["current_actor_idx"] = 0 # Default to first player
                        
                        next_actor_idx = next_team_info["current_actor_idx"]
                        next_actor = next_team_info["players"][next_actor_idx]
                        
                        gs["current_acting_team"] = next_team_name
                        gs["current_actor_name"] = next_actor
                        gs["phase"] = "TEAM_INTRO"
                        gs["status_message"] = f"الجولة {gs['current_game_round']}. فريق {next_team_name} يستعد، {next_actor} سيمثل."
        else:
            action_processed = False

    elif action_type == "ACTOR_READY_START_ROUND":
        if gs["phase"] == "TEAM_INTRO" and player_name == gs.get("current_actor_name"):
            gs["current_word_to_act"] = get_new_bk_word_server()
            if gs["current_word_to_act"] == "انتهت الكلمات!":
                gs["status_message"] = "عذراً، انتهت كل الكلمات!"
                bk_finalize_round_and_prepare_summary(gs) 
            else:
                gs["phase"] = "ACTING_ROUND"
                gs["round_active"] = True
                gs["timer_value"] = gs["round_duration_seconds"]
                gs["status_message"] = f"فريق {gs['current_acting_team']} يمثل الآن. الممثل: {player_name}"
                # Pass game_rooms_ref to start_server_timer
                start_server_timer(page_ref, room_code, gs["round_duration_seconds"], game_rooms_ref, bk_timer_tick_action, bk_round_end_action_timeout)
        else:
            action_processed = False
            
    elif action_type == "WORD_GUESSED_CORRECT":
        if gs["phase"] == "ACTING_ROUND" and player_name == gs.get("current_actor_name") and gs.get("round_active"):
            acting_team_name = gs["current_acting_team"]
            if acting_team_name and acting_team_name in teams_data:
                teams_data[acting_team_name]["score"] = teams_data[acting_team_name].get("score",0.0) + 2.0
            
            gs.setdefault("word_log",[]).append({
                "team": acting_team_name, "word": gs["current_word_to_act"], 
                "correct": True, "round": gs.get("current_game_round",1)
            }) 
            gs["current_word_to_act"] = get_new_bk_word_server()
            if gs["current_word_to_act"] == "انتهت الكلمات!":
                gs["status_message"] = "رائع! انتهت كل الكلمات في هذه الجولة!"
                bk_finalize_round_and_prepare_summary(gs) # Timer will stop as round_active becomes false
        else:
            action_processed = False

    elif action_type == "SKIP_WORD":
        if gs["phase"] == "ACTING_ROUND" and player_name == gs.get("current_actor_name") and gs.get("round_active"):
            acting_team_name = gs["current_acting_team"]
            if acting_team_name and acting_team_name in teams_data:
                 teams_data[acting_team_name]["score"] = teams_data[acting_team_name].get("score",0.0) - 0.5
            
            gs.setdefault("word_log",[]).append({
                "team": acting_team_name, "word": gs["current_word_to_act"], 
                "correct": False, "round": gs.get("current_game_round",1)
            }) 
            gs["current_word_to_act"] = get_new_bk_word_server()
            if gs["current_word_to_act"] == "انتهت الكلمات!":
                gs["status_message"] = "تخطي! انتهت كل الكلمات في هذه الجولة!"
                bk_finalize_round_and_prepare_summary(gs) # Timer will stop as round_active becomes false
        else:
            action_processed = False

    elif action_type == "RESTART_GAME_SAME_TEAMS": 
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "GAME_OVER":
            for team_name_iter in teams_data: 
                if team_name_iter in teams_data: 
                    teams_data[team_name_iter]["score"] = 0.0
                    teams_data[team_name_iter]["current_actor_idx"] = -1 
            
            gs["current_game_round"] = 0 # Will become 1 on next PROCEED_TO_NEXT_TURN
            gs["current_team_turn_idx"] = -1
            gs["round_active"] = False
            gs["used_words"] = []
            gs["word_log"] = []
            gs["timer_value"] = gs.get("round_duration_seconds",90)
            gs["phase"] = "TEAMS_SET" 
            gs["status_message"] = "تمت إعادة اللعبة بنفس الفرق. الهوست يبدأ الدور الأول."
            gs.pop("summary_for_ui", None) 
        else:
            action_processed = False

    game_rooms_ref[room_code]["game_state"] = gs # Update the game_state in the passed dictionary
    if action_processed or gs.get("status_message") != original_status_message:
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )