# server_actions/bara_alsalfa_actions.py
import flet as ft # For type hinting Page, ft.colors might be used by client but not server actions
import random
from categories import categories # Assuming categories.py is in the parent directory or accessible in PYTHONPATH

# Note: page_ref is ft.Page, but its main use here is page_ref.pubsub
def process_bara_alsalfa_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "bara_alsalfa":
        print(f"Error: Room {room_code} not found or not a Bara Alsalfa game for action by {player_name}.")
        return

    room = game_rooms_ref[room_code] # Use passed game_rooms_ref
    gs = room["game_state"]
    players_data = room["players"]

    action_processed = True 
    original_status_message = gs.get("status_message") 

    if action_type == "SELECT_CATEGORY_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            selected_cat = payload.get("category")
            if selected_cat and selected_cat in categories: # categories is imported
                gs["selected_category"] = selected_cat
                gs["status_message"] = f"الهوست اختار القائمة: {selected_cat}. يمكن الآن بدء اللعبة."
                gs["phase"] = "CATEGORY_SELECTED"
                print(f"Room {room_code}: Category '{selected_cat}' selected by host {player_name}.")
            else:
                gs["status_message"] = f"فئة غير صالحة أو غير موجودة: '{selected_cat}'."
                print(f"Room {room_code}: Invalid category '{selected_cat}' by host {player_name}. Valid keys: {list(categories.keys())}")
                action_processed = False
        else:
            print(f"Room {room_code}: SELECT_CATEGORY_HOST denied. Host: {players_data.get(player_name, {}).get('is_host')}, Phase: {gs['phase']}")
            action_processed = False

    elif action_type == "START_GAME_HOST": 
        if not players_data.get(player_name, {}).get("is_host"):
            print(f"Player {player_name} (not host) tried to start game in room {room_code}.")
            action_processed = False
        elif gs["phase"] not in ["LOBBY", "CATEGORY_SELECTED"]:
            gs["status_message"] = "لا يمكن بدء اللعبة في هذه المرحلة."
            action_processed = False
        elif len(players_data) < gs.get("min_players_for_game", 3): 
            gs["status_message"] = f"تحتاج لـ {max(0, gs.get('min_players_for_game', 3)-len(players_data))} لاعبين إضافيين على الأقل لبدء اللعبة."
            action_processed = False
        elif not gs.get("selected_category"):
            gs["status_message"] = "الرجاء اختيار قائمة أولاً قبل بدء اللعبة."
            action_processed = False
        else: 
            all_player_names = list(players_data.keys())
            gs["bara_player"] = random.choice(all_player_names)
            
            current_category_words = categories.get(gs["selected_category"], [])
            available_words = [w for w in current_category_words if w not in gs.get("used_words", [])]
            if not available_words and current_category_words:
                gs["used_words"] = [] 
                available_words = list(current_category_words)
            
            if not available_words:
                gs["status_message"] = f"لا توجد كلمات جديدة في قائمة '{gs['selected_category']}'! لا يمكن بدء اللعبة."
                action_processed = False
            else:
                gs["game_word"] = random.choice(available_words)
                gs.setdefault("used_words", []).append(gs["game_word"])

                for p_name_iter, p_info_iter in players_data.items():
                    p_info_iter["role"] = "برة السالفة" if p_name_iter == gs["bara_player"] else "داخل السالفة"
                
                gs["roles_assigned"] = True
                gs["phase"] = "ROLES_REVEAL" 
                gs["current_role_reveal_index"] = 0 
                gs["player_reveal_order"] = list(players_data.keys())
                random.shuffle(gs["player_reveal_order"]) 
                if gs["player_reveal_order"]: 
                    next_player_to_see_role = gs["player_reveal_order"][0]
                    gs["status_message"] = f"بدأت اللعبة! دور {next_player_to_see_role} لتفقد دوره."
                else: 
                    gs["status_message"] = "خطأ في بدء اللعبة، لا يوجد لاعبون."
                    action_processed = False

                print(f"Room {room_code}: Game started by host {player_name}. Bara player: {gs.get('bara_player')}, Word: {gs.get('game_word')}")

    elif action_type == "PLAYER_ACK_ROLE": 
        if gs["phase"] == "ROLES_REVEAL":
            player_reveal_order = gs.get("player_reveal_order", [])
            current_reveal_idx = gs.get("current_role_reveal_index", 0)
            
            if player_reveal_order and current_reveal_idx < len(player_reveal_order):
                expected_player_for_ack = player_reveal_order[current_reveal_idx]
                if player_name == expected_player_for_ack:
                    gs["current_role_reveal_index"] += 1
                    if gs["current_role_reveal_index"] >= len(players_data):
                        gs["phase"] = "DISCUSSION" 
                        gs["status_message"] = "الجميع عرف دوره. تبدأ مرحلة النقاش أو الأسئلة."
                        gs["votes"] = {}
                        gs["question_pairs"] = []
                        gs["current_question_pair_index"] = 0
                    else:
                        next_player_to_see_role = gs["player_reveal_order"][gs["current_role_reveal_index"]]
                        gs["status_message"] = f"دور {next_player_to_see_role} لتفقد دوره."
                else:
                    print(f"Warning: Player {player_name} in room {room_code} (Bara Alsalfa) acknowledged role, but expected {expected_player_for_ack}.")
                    action_processed = False 
            else: 
                action_processed = False
        else:
            action_processed = False
            
    elif action_type == "START_QUESTION_ROUND_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "DISCUSSION":
            player_list = list(players_data.keys())
            random.shuffle(player_list)
            gs["question_pairs"] = [(player_list[i], player_list[(i + 1) % len(player_list)]) for i in range(len(player_list))]
            gs["current_question_pair_index"] = 0
            gs["phase"] = "QUESTION_TIME"
            if gs["question_pairs"]:
                 pair = gs["question_pairs"][0]
                 gs["status_message"] = f"جولة الأسئلة: {pair[0]} يسأل {pair[1]}"
            else:
                 gs["status_message"] = "لا يوجد لاعبون كافون للأسئلة."
                 gs["phase"] = "DISCUSSION" 
        else:
            action_processed = False

    elif action_type == "NEXT_QUESTION_PAIR_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "QUESTION_TIME":
            gs["current_question_pair_index"] += 1
            if gs["current_question_pair_index"] < len(gs.get("question_pairs",[])):
                pair = gs["question_pairs"][gs["current_question_pair_index"]]
                gs["status_message"] = f"جولة الأسئلة: {pair[0]} يسأل {pair[1]}"
            else:
                gs["phase"] = "DISCUSSION" 
                gs["status_message"] = "انتهت جولة الأسئلة. يمكنكم الآن التصويت."
        else:
            action_processed = False

    elif action_type == "INITIATE_VOTE_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] in ["DISCUSSION", "QUESTION_TIME"]:
            gs["phase"] = "VOTING"
            gs["votes"] = {p_name_iter: None for p_name_iter in players_data} 
            gs["players_who_voted"] = []
            gs["status_message"] = "بدأ التصويت! كل لاعب يصوت على من يعتقد أنه 'برة السالفة'."
        else:
            action_processed = False
            
    elif action_type == "CAST_VOTE":
        if gs["phase"] == "VOTING" and player_name not in gs.get("players_who_voted", []):
            voted_for = payload.get("voted_for")
            if voted_for in players_data and voted_for != player_name:
                gs["votes"][player_name] = voted_for
                gs.setdefault("players_who_voted", []).append(player_name)
                gs["status_message"] = f"{player_name} قام بالتصويت."
                if len(gs["players_who_voted"]) == len(players_data):
                    gs["phase"] = "VOTE_RESULTS"
                    gs["status_message"] = "اكتمل التصويت. عرض النتائج..."
                    
                    gs.setdefault("round_scores", {p: 0.0 for p in players_data.keys()})
                    for p_key in gs["round_scores"]: gs["round_scores"][p_key] = 0.0 # Reset for this round

                    correct_voters_count = 0
                    for voter, voted_target in gs["votes"].items():
                        if voted_target == gs.get("bara_player"):
                            gs["round_scores"][voter] = gs["round_scores"].get(voter, 0.0) + 5.0
                            correct_voters_count +=1
                    
                    if correct_voters_count == 0 and len(players_data) > 1 and gs.get("bara_player"): 
                         gs["round_scores"][gs["bara_player"]] = gs["round_scores"].get(gs["bara_player"],0.0) + (len(players_data)-1) * 2.0
                    
                    current_category_words = categories.get(gs.get("selected_category", ""), [])
                    words_for_options = [w for w in current_category_words if w != gs.get("game_word")]
                    # Ensure enough options for sample, or take all available if fewer than 7
                    num_options_to_sample = min(7, len(words_for_options))
                    options = random.sample(words_for_options, num_options_to_sample) 
                    if gs.get("game_word") and gs.get("game_word") not in options : # Add game word if not already picked by chance in sample
                        options.append(gs["game_word"])
                    random.shuffle(options)
                    gs["bara_guess_options"] = options
            else:
                action_processed = False 
        else:
            action_processed = False 

    elif action_type == "BARA_GUESS_WORD":
        if gs["phase"] == "VOTE_RESULTS" and player_name == gs.get("bara_player"):
            guessed_word = payload.get("word")
            if guessed_word == gs.get("game_word"):
                gs["bara_guess_result"] = f"صحيح! {gs.get('bara_player','')} خمن الكلمة ({gs.get('game_word', '')}) وحصل على 10 نقاط."
                gs["round_scores"][gs["bara_player"]] = gs["round_scores"].get(gs["bara_player"], 0.0) + 10.0
            else:
                gs["bara_guess_result"] = f"خطأ! الكلمة الصحيحة كانت {gs.get('game_word', 'غير محددة')}."
            gs["phase"] = "ROUND_OVER"
            gs["status_message"] = "انتهت الجولة. عرض النتائج النهائية للجولة."
            
            gs.setdefault("global_scores", {p: 0.0 for p in players_data.keys()}) 
            for p_name_iter, score in gs.get("round_scores", {}).items():
                gs["global_scores"][p_name_iter] = gs["global_scores"].get(p_name_iter,0.0) + score
        else:
            action_processed = False
            
    elif action_type == "NEXT_ROUND_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "ROUND_OVER":
            gs["phase"] = "LOBBY" 
            gs["status_message"] = "جولة جديدة! الهوست يختار قائمة الكلمات."
            gs["selected_category"] = None 
            gs["roles_assigned"] = False
            gs["bara_player"] = None
            gs["game_word"] = None
            gs["votes"] = {} 
            gs["players_who_voted"] = [] 
            gs["current_role_reveal_index"] = 0 
            gs["player_reveal_order"] = [] 
            gs["question_pairs"] = [] 
            gs["current_question_pair_index"] = 0 
            gs["bara_guess_options"] = []
            gs["bara_guess_result"] = ""
            gs["round_scores"] = {p_name_iter: 0.0 for p_name_iter in players_data.keys()} # Reset round scores
            print(f"Room {room_code}: Host {player_name} initiated next round for Bara Alsalfa. State reset to LOBBY.")
        else:
            action_processed = False
            print(f"Room {room_code}: NEXT_ROUND_HOST for Bara Alsalfa denied. Host: {players_data.get(player_name, {}).get('is_host')}, Phase: {gs['phase']}")
            
    # Update the game_state in the passed game_rooms_ref
    game_rooms_ref[room_code]["game_state"] = gs 
    
    # Send update to clients if action was processed or status message changed
    if action_processed or gs.get("status_message") != original_status_message:
        if page_ref.client_storage: # Check if page is still connected
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]} # Send updated room state
            )
        if not action_processed:
            print(f"Bara Alsalfa action {action_type} by {player_name} in room {room_code} was not fully processed but status may have changed, sent update.")
    elif not action_processed:
         print(f"Bara Alsalfa action {action_type} by {player_name} in room {room_code} was not processed and status message did not change.")