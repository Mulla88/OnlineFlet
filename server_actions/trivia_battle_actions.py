# server_actions/trivia_battle_actions.py
import flet as ft
import random
import importlib

TRIVIA_CATEGORIES_SERVER_MAP = {
    "The Office": "trivia_data.trivia_the_office",
    "رياضة": "trivia_data.trivia_sports",
    "جغرافيا": "trivia_data.trivia_geography",
    "ثقافة عامة": "trivia_data.trivia_general_knowledge",
    "موسيقى": "trivia_data.trivia_music" # Make sure you have this trivia_data file
}

def process_trivia_battle_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "trivia_battle":
        print(f"Error: Room {room_code} not found or not a Trivia Battle game.")
        return

    room = game_rooms_ref[room_code]
    gs = room["game_state"]
    players_data_dict = room["players"] 
    player_names_list = list(players_data_dict.keys()) 

    action_processed = True
    original_status_message = gs.get("status_message")

    def load_questions_server(category_key_from_client):
        module_path_str = TRIVIA_CATEGORIES_SERVER_MAP.get(category_key_from_client)
        if not module_path_str:
            print(f"Server - Unknown trivia category key: {category_key_from_client}")
            return []
        try:
            mod = importlib.import_module(module_path_str)
            loaded_qs = getattr(mod, "trivia_questions", [])
            valid_qs = [
                q for q in loaded_qs
                if isinstance(q, dict) and
                   all(k in q for k in ["question", "options", "answer"]) and
                   isinstance(q["options"], list) and len(q["options"]) > 1
            ]
            if len(valid_qs) != len(loaded_qs):
                print(f"Warning: Some invalid question formats in {module_path_str}. Loaded {len(valid_qs)} valid questions.")
            return valid_qs
        except Exception as e:
            print(f"Server - Error loading questions from {module_path_str} for category '{category_key_from_client}': {e}")
            return []

    if action_type == "SETUP_TRIVIA_GAME_HOST": 
        if players_data_dict.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            category_key = payload.get("category")
            min_players = gs.get("min_players_for_game", 2)
            max_players = gs.get("max_players_for_game", 6)


            if not (min_players <= len(player_names_list) <= max_players):
                gs["status_message"] = f"اللعبة تتطلب من {min_players} إلى {max_players} لاعبين. العدد الحالي: {len(player_names_list)}"
                action_processed = False
            elif not category_key or category_key not in TRIVIA_CATEGORIES_SERVER_MAP:
                gs["status_message"] = "الرجاء اختيار فئة أسئلة صالحة."
                action_processed = False
            else:
                all_qs_for_cat = load_questions_server(category_key)
                if not all_qs_for_cat:
                    gs["status_message"] = f"لا توجد أسئلة في فئة '{category_key}'. لا يمكن بدء اللعبة."
                    action_processed = False
                else:
                    questions_per_player = gs.get("questions_per_player", 10)
                    total_questions_needed = len(player_names_list) * questions_per_player
                    
                    if len(all_qs_for_cat) < total_questions_needed:
                        print(f"Warning: Trivia category '{category_key}' has {len(all_qs_for_cat)} questions, need {total_questions_needed}. Using all available, game might be shorter per player.")
                        gs["question_pool_online"] = random.sample(all_qs_for_cat, len(all_qs_for_cat))
                    else:
                        gs["question_pool_online"] = random.sample(all_qs_for_cat, total_questions_needed)
                    
                    if not gs["question_pool_online"]:
                        gs["status_message"] = "خطأ فادح: لا توجد أسئلة متاحة بعد اختيار الفئة."
                        action_processed = False
                    else:
                        gs["players_scores_online"] = {p_name_init: 0 for p_name_init in player_names_list}
                        gs["player_question_counts"] = {p_name_init: 0 for p_name_init in player_names_list} 
                        gs["current_question_pool_idx"] = 0 
                        gs["current_player_turn_idx_online"] = 0 
                        gs["phase"] = "QUESTION_DISPLAY_ONLINE"
                        gs["selected_category_online"] = category_key
                        
                        current_player_for_turn = player_names_list[gs["current_player_turn_idx_online"]]
                        gs["status_message"] = f"بدأت لعبة تريفيا! فئة: {category_key}. دور اللاعب {current_player_for_turn}."
                        gs["current_acting_player_online"] = current_player_for_turn 
                        gs["current_question_online_data"] = gs["question_pool_online"][gs["current_question_pool_idx"]]
                        gs["last_answered_question_data"] = None
                        gs["last_answer_was_correct"] = None
                        gs["correct_answer_text_for_last_q"] = ""
                        print(f"Trivia game started. Players: {player_names_list}. Pool size: {len(gs['question_pool_online'])}")
        else:
            action_processed = False

    elif action_type == "SUBMIT_TRIVIA_ANSWER":
        current_acting_player = gs.get("current_acting_player_online")

        if gs["phase"] == "QUESTION_DISPLAY_ONLINE" and player_name == current_acting_player:
            submitted_answer = payload.get("answer")
            current_q_data = gs.get("current_question_online_data", {})
            correct_answer = current_q_data.get("answer")

            gs["last_answered_question_data"] = current_q_data
            gs["correct_answer_text_for_last_q"] = correct_answer

            if submitted_answer == correct_answer:
                gs["players_scores_online"][current_acting_player] = gs["players_scores_online"].get(current_acting_player, 0) + 1
                gs["last_answer_was_correct"] = True
                gs["status_message"] = f"اللاعب {current_acting_player} أجاب بشكل صحيح!"
            else:
                gs["last_answer_was_correct"] = False
                gs["status_message"] = f"اللاعب {current_acting_player} أجاب بشكل خاطئ. الجواب الصحيح: {correct_answer}"
            
            gs["player_question_counts"][current_acting_player] = gs["player_question_counts"].get(current_acting_player, 0) + 1
            gs["phase"] = "ANSWER_FEEDBACK_ONLINE"
        else:
            gs["status_message"] = "ليس دورك للإجابة أو أن اللعبة ليست في مرحلة استقبال الإجابات."
            action_processed = False

    elif action_type == "NEXT_TRIVIA_QUESTION_HOST":
        if players_data_dict.get(player_name, {}).get("is_host") and gs["phase"] == "ANSWER_FEEDBACK_ONLINE":
            
            all_players_finished_quota = True
            for p_name_check in player_names_list:
                if gs["player_question_counts"].get(p_name_check, 0) < gs.get("questions_per_player", 10):
                    all_players_finished_quota = False
                    break
            
            # Also check if we've simply run out of pooled questions
            pool_exhausted = gs["current_question_pool_idx"] + 1 >= len(gs.get("question_pool_online",[]))

            if all_players_finished_quota or pool_exhausted:
                gs["phase"] = "GAME_OVER_TRIVIA"
                gs["status_message"] = "انتهت جميع الأسئلة أو أكمل جميع اللاعبين حصتهم! عرض النتائج النهائية."
            else:
                # Determine next player who hasn't finished their quota
                next_player_found = False
                original_turn_idx = gs.get("current_player_turn_idx_online", 0)
                temp_turn_idx = original_turn_idx

                for _ in range(len(player_names_list)): # Iterate at most once through all players
                    temp_turn_idx = (temp_turn_idx + 1) % len(player_names_list)
                    potential_next_player = player_names_list[temp_turn_idx]
                    if gs["player_question_counts"].get(potential_next_player, 0) < gs.get("questions_per_player", 10):
                        gs["current_player_turn_idx_online"] = temp_turn_idx
                        next_player_found = True
                        break
                
                if not next_player_found: # Should be caught by all_players_finished_quota
                    gs["phase"] = "GAME_OVER_TRIVIA"
                    gs["status_message"] = "خطأ: لم يتم العثور على لاعب تالٍ. عرض النتائج."
                else:
                    gs["current_question_pool_idx"] += 1 
                    # Double check pool exhaustion after incrementing (although outer check should catch it)
                    if gs["current_question_pool_idx"] >= len(gs.get("question_pool_online",[])):
                         gs["phase"] = "GAME_OVER_TRIVIA"
                         gs["status_message"] = "انتهت جميع الأسئلة المجمعة! عرض النتائج النهائية."
                    else:
                        next_player_for_turn = player_names_list[gs["current_player_turn_idx_online"]]
                        gs["current_acting_player_online"] = next_player_for_turn
                        gs["current_question_online_data"] = gs["question_pool_online"][gs["current_question_pool_idx"]]
                        gs["phase"] = "QUESTION_DISPLAY_ONLINE"
                        gs["status_message"] = f"دور اللاعب {next_player_for_turn} للإجابة."
                        gs["last_answered_question_data"] = None
                        gs["last_answer_was_correct"] = None
                        gs["correct_answer_text_for_last_q"] = ""
        else:
            action_processed = False
            
    elif action_type == "RESTART_TRIVIA_HOST": 
        if players_data_dict.get(player_name, {}).get("is_host") and gs["phase"] == "GAME_OVER_TRIVIA":
            gs["players_scores_online"] = {p_name_reset: 0 for p_name_reset in player_names_list}
            gs["player_question_counts"] = {p_name_reset: 0 for p_name_reset in player_names_list}
            
            category_key = gs.get("selected_category_online")
            if category_key:
                all_qs_for_cat = load_questions_server(category_key)
                if all_qs_for_cat:
                    questions_per_player = gs.get("questions_per_player", 10)
                    total_questions_needed = len(player_names_list) * questions_per_player
                    if len(all_qs_for_cat) < total_questions_needed:
                        gs["question_pool_online"] = random.sample(all_qs_for_cat, len(all_qs_for_cat))
                    else:
                        gs["question_pool_online"] = random.sample(all_qs_for_cat, total_questions_needed)
                else:
                    gs["question_pool_online"] = [] 
            else:
                 gs["question_pool_online"] = []

            if not gs["question_pool_online"]:
                gs["phase"] = "LOBBY" 
                gs["status_message"] = "خطأ في إعادة تحميل الأسئلة. الرجاء إعادة إعداد اللعبة من البداية."
            else:
                gs["current_question_pool_idx"] = 0
                gs["current_player_turn_idx_online"] = 0
                first_player_restart = player_names_list[0]
                gs["current_acting_player_online"] = first_player_restart
                gs["current_question_online_data"] = gs["question_pool_online"][0]
                gs["phase"] = "QUESTION_DISPLAY_ONLINE"
                gs["status_message"] = f"بدأت لعبة تريفيا جديدة بنفس اللاعبين والفئة ({category_key}). دور اللاعب {first_player_restart}."
        else:
            action_processed = False

    game_rooms_ref[room_code]["game_state"] = gs
    if action_processed or gs.get("status_message") != original_status_message:
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )