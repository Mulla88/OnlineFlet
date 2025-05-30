import flet as ft  # For type hinting Page
import random
from min_fina_questions import min_fina_questions  # Assuming this is accessible

def process_min_fina_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "min_fina":
        print(f"Error: Room {room_code} not for Min Fina or not found.")
        return

    room = game_rooms_ref[room_code]
    gs = room["game_state"]
    players_data = room["players"]

    action_processed = True
    original_status_message = gs.get("status_message")

    min_players_required = gs.get("min_players_for_game", 3)

    def _choose_new_minfina_question_server():
        gs.setdefault("used_questions", [])
        available = [q for q in min_fina_questions if q not in gs["used_questions"]]
        if not available:
            gs["used_questions"] = []
            available = list(min_fina_questions)
        if not available:
            return "لا توجد أسئلة متبقية في القائمة!"
        new_q = random.choice(available)
        gs["used_questions"].append(new_q)
        return new_q

    if action_type == "START_NEW_QUESTION_HOST":
        if players_data.get(player_name, {}).get("is_host"):
            if len(players_data) < min_players_required:
                gs["status_message"] = f"تحتاج لـ {max(0, min_players_required - len(players_data))} لاعبين إضافيين على الأقل لبدء اللعبة."
            else:
                gs["current_question"] = _choose_new_minfina_question_server()
                gs["skip_chances_left"] = gs.get("initial_skip_chances", 2)
                gs["phase"] = "QUESTION_DISPLAY"
                gs["status_message"] = "سؤال جديد! الهوست يمكنه بدء التصويت أو تغيير السؤال."
                gs["players_voted_this_round"] = []
                gs["current_round_votes"] = {}
                gs.pop("last_vote_counts", None)
                gs.pop("last_question_answered", None)
                print(f"MinFina Room {room_code}: New question '{gs['current_question']}' by host {player_name}")
        else:
            action_processed = False

    elif action_type == "SKIP_QUESTION_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "QUESTION_DISPLAY":
            if gs.get("skip_chances_left", 0) > 0:
                gs["skip_chances_left"] -= 1
                gs["current_question"] = _choose_new_minfina_question_server()
                gs["status_message"] = "تم تغيير السؤال. الهوست يبدأ التصويت أو يغير السؤال."
            else:
                gs["status_message"] = "لا يمكن تغيير السؤال، انتهت الفرص."
        else:
            action_processed = False

    elif action_type == "INITIATE_VOTING_HOST":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "QUESTION_DISPLAY" and gs.get("current_question"):
            if gs["current_question"].startswith("لا توجد أسئلة"):
                gs["status_message"] = "لا يمكن بدء التصويت، لا يوجد سؤال حالي."
            else:
                gs["phase"] = "VOTING"
                gs["players_voted_this_round"] = []
                gs["current_round_votes"] = {}
                gs["status_message"] = "بدأ التصويت للسؤال."
        else:
            action_processed = False

    elif action_type == "CAST_PLAYER_VOTE":
        if gs["phase"] == "VOTING" and player_name not in gs.get("players_voted_this_round", []):
            voted_for_player = payload.get("voted_for")
            if voted_for_player in players_data:
                gs.setdefault("current_round_votes", {})[player_name] = voted_for_player
                gs.setdefault("players_voted_this_round", []).append(player_name)
                gs["status_message"] = f"{player_name} قام بالتصويت. في انتظار البقية..."

                if len(gs["players_voted_this_round"]) == len(players_data):
                    gs["phase"] = "RESULTS"
                    vote_counts = {p_name_iter: 0 for p_name_iter in players_data.keys()}
                    for voted_player_name in gs["current_round_votes"].values():
                        if voted_player_name in vote_counts:
                            vote_counts[voted_player_name] += 1

                    gs["last_vote_counts"] = vote_counts
                    gs["last_question_answered"] = gs["current_question"]
                    gs["status_message"] = "اكتمل التصويت! عرض النتائج."
                    print(f"MinFina Room {room_code}: All voted. Results: {vote_counts}")
            else:
                gs["status_message"] = f"لاعب غير صالح تم التصويت له: {voted_for_player}"
        else:
            action_processed = False

    game_rooms_ref[room_code]["game_state"] = gs
    if action_processed or gs.get("status_message") != original_status_message:
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )
