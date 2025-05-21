# server_actions/trivia_battle_actions.py
import flet as ft
import random
import importlib
import sys # For potentially modifying sys.path if trivia_data is not a package

TRIVIA_CATEGORIES_SERVER_MAP = {
    "The Office": "trivia_data.trivia_the_office",
    "رياضة": "trivia_data.trivia_sports",
    "جغرافيا": "trivia_data.trivia_geography",
    "ثقافة عامة": "trivia_data.trivia_general_knowledge",
    "موسيقى": "trivia_data.trivia_music"
}

def process_trivia_battle_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "trivia_battle":
        print(f"Error: Room {room_code} not found or not a Trivia Battle game.")
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic( # Send to all, client can filter
                f"room_{room_code}",
                {"type": "ACTION_ERROR", "message": "خطأ في الغرفة أو نوع اللعبة.", "recipient": player_name}
            )
        return

    room = game_rooms_ref[room_code]
    gs = room["game_state"]
    players_data_dict = room["players"]
    player_names_list = list(players_data_dict.keys())

    action_processed = True
    original_status_message = gs.get("status_message")
    error_to_client = None

    def load_questions_server(category_key_from_client):
        module_path_str = TRIVIA_CATEGORIES_SERVER_MAP.get(category_key_from_client)
        if not module_path_str:
            print(f"Server - Unknown trivia category key: {category_key_from_client}")
            return []
        try:
            # Example: if trivia_data is a directory at the same level as your main script's directory
            # import os
            # current_dir = os.path.dirname(os.path.abspath(__file__)) # Gets dir of this file
            # trivia_data_path = os.path.join(os.path.dirname(current_dir), "trivia_data") # Assumes trivia_data is one level up from server_actions
            # if trivia_data_path not in sys.path:
            #     sys.path.append(os.path.dirname(trivia_data_path)) # Add parent of trivia_data to import it as a package

            mod = importlib.import_module(module_path_str)
            importlib.reload(mod)
            loaded_qs = getattr(mod, "trivia_questions", [])
            valid_qs = [
                q for q in loaded_qs
                if isinstance(q, dict) and
                   all(k in q for k in ["question", "options", "answer"]) and
                   isinstance(q["options"], list) and len(q["options"]) > 1
            ]
            if len(valid_qs) != len(loaded_qs):
                print(f"Server Warning: Some invalid question formats in {module_path_str}. Loaded {len(valid_qs)} valid questions out of {len(loaded_qs)}.")
            return valid_qs
        except ModuleNotFoundError:
            print(f"Server - Module not found: {module_path_str} for category '{category_key_from_client}'. Ensure 'trivia_data' is structured as a package or its parent directory is in sys.path.")
            return []
        except AttributeError:
            print(f"Server - Variable 'trivia_questions' not found in module: {module_path_str}.")
            return []
        except Exception as e:
            print(f"Server - Error loading questions from {module_path_str} for category '{category_key_from_client}': {e}")
            return []

    if action_type == "SETUP_TRIVIA_GAME_HOST":
        if players_data_dict.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            category_key = payload.get("category")
            min_players = gs.get("min_players_for_game", 2)
            max_players = gs.get("max_players_for_game", 6)
            num_actual_players = len(player_names_list)

            if not (min_players <= num_actual_players <= max_players):
                error_to_client = f"اللعبة تتطلب من {min_players} إلى {max_players} لاعبين. العدد الحالي: {num_actual_players}"
                action_processed = False
            elif not category_key or category_key not in TRIVIA_CATEGORIES_SERVER_MAP:
                error_to_client = "الرجاء اختيار فئة أسئلة صالحة."
                action_processed = False
            else:
                all_qs_for_cat = load_questions_server(category_key)
                if not all_qs_for_cat:
                    error_to_client = f"لا توجد أسئلة في فئة '{category_key}'. لا يمكن بدء اللعبة."
                    action_processed = False
                else:
                    initial_questions_per_player = gs.get("questions_per_player_setting", 10)
                    gs["questions_per_player_setting"] = initial_questions_per_player

                    target_total_questions_needed = num_actual_players * initial_questions_per_player

                    if len(all_qs_for_cat) < target_total_questions_needed:
                        print(f"Server Info: Category '{category_key}' has {len(all_qs_for_cat)} questions, target was {target_total_questions_needed}. Using all available.")
                        gs["question_pool_online"] = random.sample(all_qs_for_cat, len(all_qs_for_cat))
                    else:
                        gs["question_pool_online"] = random.sample(all_qs_for_cat, target_total_questions_needed)

                    game_total_available_questions_in_pool = len(gs["question_pool_online"])

                    if game_total_available_questions_in_pool == 0:
                        error_to_client = f"خطأ فادح: لا توجد أسئلة متاحة في '{category_key}' لبدء اللعبة."
                        action_processed = False
                    else:
                        if num_actual_players > 0:
                            calculated_questions_per_player = game_total_available_questions_in_pool // num_actual_players
                            if calculated_questions_per_player == 0 and game_total_available_questions_in_pool > 0:
                                gs["questions_per_player"] = 1
                            else:
                                gs["questions_per_player"] = calculated_questions_per_player
                        else:
                            gs["questions_per_player"] = 0
                        
                        gs["max_total_questions_for_game"] = num_actual_players * gs["questions_per_player"]

                        if len(gs["question_pool_online"]) > gs["max_total_questions_for_game"]:
                            gs["question_pool_online"] = gs["question_pool_online"][:gs["max_total_questions_for_game"]]
                        elif len(gs["question_pool_online"]) < gs["max_total_questions_for_game"]:
                            gs["max_total_questions_for_game"] = len(gs["question_pool_online"])
                            if num_actual_players > 0:
                                new_q_per_p = gs["max_total_questions_for_game"] // num_actual_players
                                if new_q_per_p == 0 and gs["max_total_questions_for_game"] > 0:
                                     gs["questions_per_player"] = 1
                                else:
                                     gs["questions_per_player"] = new_q_per_p
                                gs["max_total_questions_for_game"] = num_actual_players * gs["questions_per_player"]
                            
                        if gs["max_total_questions_for_game"] == 0 :
                            error_to_client = "خطأ: لا توجد أسئلة كافية لبدء اللعبة بعد التوزيع."
                            action_processed = False
                        else:
                            gs["players_scores_online"] = {p_name_init: 0 for p_name_init in player_names_list}
                            gs["player_question_counts_online"] = {p_name_init: 0 for p_name_init in player_names_list}
                            gs["current_question_pool_idx"] = 0
                            gs["current_player_turn_idx_online"] = 0
                            gs["phase"] = "QUESTION_DISPLAY_ONLINE"
                            gs["selected_category_online"] = category_key
                            
                            current_player_for_turn = player_names_list[gs["current_player_turn_idx_online"]] if player_names_list else "Unknown"
                            gs["status_message"] = f"بدأت لعبة تريفيا! فئة: {category_key}. دور اللاعب {current_player_for_turn}."
                            gs["current_acting_player_online"] = current_player_for_turn
                            gs["current_question_online_data"] = gs["question_pool_online"][gs["current_question_pool_idx"]]
                            gs["last_answered_question_data"] = None
                            gs["last_answer_was_correct"] = None
                            gs["correct_answer_text_for_last_q"] = ""
                            print(f"Server: Trivia game started. Players: {player_names_list}. Qs/Player: {gs['questions_per_player']}. Total Qs in Game: {gs['max_total_questions_for_game']}. Pool Size: {len(gs['question_pool_online'])}")
        else:
            error_to_client = "لا يمكنك بدء اللعبة. إما أنك لست الهوست أو أن اللعبة ليست في مرحلة الانتظار."
            action_processed = False

    elif action_type == "SUBMIT_TRIVIA_ANSWER":
        current_acting_player_server = gs.get("current_acting_player_online")

        if gs["phase"] == "QUESTION_DISPLAY_ONLINE" and player_name == current_acting_player_server:
            submitted_answer = payload.get("answer")
            current_q_data_server = gs.get("current_question_online_data", {})
            correct_answer_server = current_q_data_server.get("answer")

            gs["last_answered_question_data"] = current_q_data_server
            gs["correct_answer_text_for_last_q"] = correct_answer_server

            if submitted_answer == correct_answer_server:
                gs["players_scores_online"][current_acting_player_server] = gs["players_scores_online"].get(current_acting_player_server, 0) + 1
                gs["last_answer_was_correct"] = True
                gs["status_message"] = f"اللاعب {current_acting_player_server} أجاب بشكل صحيح!"
            else:
                gs["last_answer_was_correct"] = False
                gs["status_message"] = f"اللاعب {current_acting_player_server} أجاب بشكل خاطئ. الجواب الصحيح: {correct_answer_server}"
            
            gs["player_question_counts_online"][current_acting_player_server] = gs["player_question_counts_online"].get(current_acting_player_server, 0) + 1
            gs["phase"] = "ANSWER_FEEDBACK_ONLINE"
        else:
            error_to_client = "ليس دورك للإجابة أو أن اللعبة ليست في مرحلة استقبال الإجابات."
            action_processed = False

    elif action_type == "NEXT_TRIVIA_QUESTION_HOST":
        if players_data_dict.get(player_name, {}).get("is_host") and gs["phase"] == "ANSWER_FEEDBACK_ONLINE":
            max_questions_for_this_game = gs.get("max_total_questions_for_game", 0)
            
            if gs.get("current_question_pool_idx", -1) + 1 >= max_questions_for_this_game:
                gs["phase"] = "GAME_OVER_TRIVIA"
                gs["status_message"] = "انتهت جميع الأسئلة المخطط لها! عرض النتائج النهائية."
            else:
                next_player_found = False
                last_player_acted = gs.get("current_acting_player_online")
                try:
                    last_player_idx = player_names_list.index(last_player_acted) if last_player_acted and player_names_list else gs.get("current_player_turn_idx_online", -1)
                except ValueError:
                    last_player_idx = gs.get("current_player_turn_idx_online", -1) # Fallback
                
                temp_turn_idx = last_player_idx

                if not player_names_list: # Should not happen if game started
                    action_processed = False
                    error_to_client = "لا يوجد لاعبون في القائمة."
                else:
                    for _ in range(len(player_names_list)):
                        temp_turn_idx = (temp_turn_idx + 1) % len(player_names_list)
                        potential_next_player = player_names_list[temp_turn_idx]
                        
                        if gs["player_question_counts_online"].get(potential_next_player, 0) < gs.get("questions_per_player", 10):
                            gs["current_player_turn_idx_online"] = temp_turn_idx
                            next_player_found = True
                            break
                    
                    if not next_player_found:
                        gs["phase"] = "GAME_OVER_TRIVIA"
                        gs["status_message"] = "لم يتم العثور على لاعب تالٍ مؤهل أو تم الوصول لحد الأسئلة. عرض النتائج."
                        print(f"Server: No next player found. Qs asked: {gs.get('current_question_pool_idx', -1) + 1}, Max for game: {max_questions_for_this_game}")
                    else:
                        gs["current_question_pool_idx"] += 1
                        
                        if gs["current_question_pool_idx"] >= len(gs.get("question_pool_online",[])) or \
                           gs["current_question_pool_idx"] >= max_questions_for_this_game :
                             gs["phase"] = "GAME_OVER_TRIVIA"
                             gs["status_message"] = "تم الوصول لنهاية مجمع الأسئلة أو الحد الأقصى للأسئلة. عرض النتائج النهائية."
                        else:
                            next_player_for_turn_server = player_names_list[gs["current_player_turn_idx_online"]]
                            gs["current_acting_player_online"] = next_player_for_turn_server
                            gs["current_question_online_data"] = gs["question_pool_online"][gs["current_question_pool_idx"]]
                            gs["phase"] = "QUESTION_DISPLAY_ONLINE"
                            gs["status_message"] = f"دور اللاعب {next_player_for_turn_server} للإجابة."
                            gs["last_answered_question_data"] = None
                            gs["last_answer_was_correct"] = None
                            gs["correct_answer_text_for_last_q"] = ""
        else:
            error_to_client = "لا يمكنك الانتقال للسؤال التالي. إما أنك لست الهوست أو أن اللعبة ليست في مرحلة التقييم."
            action_processed = False
            
    elif action_type == "RESTART_TRIVIA_HOST":
        if players_data_dict.get(player_name, {}).get("is_host") and gs["phase"] == "GAME_OVER_TRIVIA":
            gs["players_scores_online"] = {p_name_reset: 0 for p_name_reset in player_names_list}
            gs["player_question_counts_online"] = {p_name_reset: 0 for p_name_reset in player_names_list}
            
            category_key = gs.get("selected_category_online")
            num_actual_players = len(player_names_list)

            if not player_names_list:
                action_processed = False
                error_to_client = "لا يمكن إعادة تشغيل اللعبة بدون لاعبين."
                gs["phase"] = "LOBBY"
                gs["status_message"] = "خطأ: لا يوجد لاعبون لإعادة تشغيل اللعبة."
            elif category_key:
                all_qs_for_cat = load_questions_server(category_key)
                if all_qs_for_cat:
                    initial_questions_per_player = gs.get("questions_per_player_setting", 10)
                    target_total_questions_needed = num_actual_players * initial_questions_per_player

                    if len(all_qs_for_cat) < target_total_questions_needed:
                        gs["question_pool_online"] = random.sample(all_qs_for_cat, len(all_qs_for_cat))
                    else:
                        gs["question_pool_online"] = random.sample(all_qs_for_cat, target_total_questions_needed)

                    game_total_available_questions_in_pool = len(gs["question_pool_online"])

                    if game_total_available_questions_in_pool > 0:
                        if num_actual_players > 0:
                            calculated_questions_per_player = game_total_available_questions_in_pool // num_actual_players
                            if calculated_questions_per_player == 0:
                                gs["questions_per_player"] = 1
                            else:
                                gs["questions_per_player"] = calculated_questions_per_player
                        else:
                             gs["questions_per_player"] = 0
                        
                        gs["max_total_questions_for_game"] = num_actual_players * gs["questions_per_player"]

                        if len(gs["question_pool_online"]) > gs["max_total_questions_for_game"]:
                            gs["question_pool_online"] = gs["question_pool_online"][:gs["max_total_questions_for_game"]]
                        elif len(gs["question_pool_online"]) < gs["max_total_questions_for_game"]:
                            gs["max_total_questions_for_game"] = len(gs["question_pool_online"])
                            if num_actual_players > 0:
                                new_q_per_p = gs["max_total_questions_for_game"] // num_actual_players
                                if new_q_per_p == 0 and gs["max_total_questions_for_game"] > 0:
                                     gs["questions_per_player"] = 1
                                else:
                                     gs["questions_per_player"] = new_q_per_p
                                gs["max_total_questions_for_game"] = num_actual_players * gs["questions_per_player"]
                    else:
                        gs["question_pool_online"] = []
                        gs["max_total_questions_for_game"] = 0
                else:
                    gs["question_pool_online"] = []
                    gs["max_total_questions_for_game"] = 0
            else:
                 gs["question_pool_online"] = []
                 gs["max_total_questions_for_game"] = 0

            if not gs["question_pool_online"] or gs.get("max_total_questions_for_game", 0) == 0:
                gs["phase"] = "LOBBY"
                gs["status_message"] = "خطأ في إعادة تحميل الأسئلة أو لا توجد أسئلة كافية. الرجاء إعادة إعداد اللعبة من البداية."
                gs.pop("selected_category_online", None)
                gs.pop("questions_per_player", None)
                gs.pop("max_total_questions_for_game", None)
                gs.pop("question_pool_online", None)
                gs.pop("current_question_pool_idx", None)
            else:
                gs["current_question_pool_idx"] = 0
                gs["current_player_turn_idx_online"] = 0
                first_player_restart = player_names_list[0]
                gs["current_acting_player_online"] = first_player_restart
                gs["current_question_online_data"] = gs["question_pool_online"][0]
                gs["phase"] = "QUESTION_DISPLAY_ONLINE"
                gs["status_message"] = f"بدأت لعبة تريفيا جديدة بنفس اللاعبين والفئة ({category_key}). دور اللاعب {first_player_restart}."
                gs["last_answered_question_data"] = None
                gs["last_answer_was_correct"] = None
                gs["correct_answer_text_for_last_q"] = ""
                print(f"Server: Trivia game RESTARTED. Players: {player_names_list}. Qs/Player: {gs['questions_per_player']}. Total Qs in Game: {gs['max_total_questions_for_game']}. Pool Size: {len(gs['question_pool_online'])}")
        else:
            error_to_client = "لا يمكنك إعادة بدء اللعبة. إما أنك لست الهوست أو أن اللعبة لم تنتهِ بعد."
            action_processed = False
    else:
        print(f"Server: Unknown trivia action type: {action_type}")
        error_to_client = f"أمر غير معروف: {action_type}"
        action_processed = False

    game_rooms_ref[room_code]["game_state"] = gs

    if page_ref.client_storage:
        if error_to_client:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "ACTION_ERROR", "message": error_to_client, "recipient": player_name}
            )
            # Always send a state update after an error so clients reflect any status message change
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )
        elif action_processed: # No error, action was processed
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )
        elif gs.get("status_message") != original_status_message: # No error, action not processed, but status changed
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )
    else:
        print(f"Server: page_ref.client_storage is False for room {room_code}. Cannot send pubsub message.")