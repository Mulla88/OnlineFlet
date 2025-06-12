# server_actions/sudoku_actions.py
import flet as ft
from sudoku_utils import get_sudoku_puzzle, check_solution_correctness, copy_board

def process_sudoku_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "sudoku":
        print(f"Server Error: Room {room_code} not found or not a Sudoku game for action {action_type}.")
        return

    room = game_rooms_ref[room_code]
    gs = room["game_state"]
    players_data = room["players"]

    action_processed = True
    send_full_update = False 
    send_targeted_feedback = False
    feedback_player_target = None
    feedback_message_content = ""

    # print(f"Server: Processing Sudoku action: {action_type} for room {room_code}, player {player_name}. Current phase: {gs.get('phase')}")


    if action_type == "SETUP_SUDOKU_GAME":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            difficulty = payload.get("difficulty", "normal")
            puzzle, solution = get_sudoku_puzzle(difficulty)
            
            print(f"Server: [DEBUG] SETUP_SUDOKU_GAME processed for room {room_code} by host {player_name}")
            print(f"Server: [DEBUG] Difficulty: {difficulty}")
            # print("[DEBUG] Solution board:", solution) # Keep this for debugging if needed

            gs["puzzle_board"] = puzzle
            gs["solution_board"] = solution
            gs["difficulty"] = difficulty
            gs["winner"] = None
            gs["phase"] = "PLAYING" # Phase changes HERE
            gs["status_message"] = f"أول من يحل السودوكو يفوز. بالتوفيق!"
            send_full_update = True # This will trigger GAME_STATE_UPDATE later
            
            # It's good practice to send critical individual updates if needed,
            # but GAME_STATE_UPDATE should carry all necessary info.
            # The SUDOKU_SOLUTION_UPDATE is fine as it provides the solution early for local validation.
            if page_ref.client_storage:
                page_ref.pubsub.send_all_on_topic(
                    f"room_{room_code}",
                    {
                        "type": "SUDOKU_SOLUTION_UPDATE",
                        "solution_board": solution
                    }
                )
                print(f"Server: [DEBUG] Sent SUDOKU_SOLUTION_UPDATE to room {room_code}")
        else:
            print(f"Server: SETUP_SUDOKU_GAME rejected. Player {player_name} is_host: {players_data.get(player_name, {}).get('is_host')}, phase: {gs['phase']}")
            gs["status_message"] = "لا يمكن بدء لعبة سودوكو الآن (إما أنك لست الهوست أو اللعبة ليست في اللوبي)."
            send_full_update = True # Send update with error status
            action_processed = False

    elif action_type == "SUBMIT_SUDOKU_SOLUTION":
        if gs["phase"] == "PLAYING" and player_name in players_data:
            submitted_board = payload.get("board")
            if not submitted_board or len(submitted_board) != 9 or not all(len(row) == 9 for row in submitted_board):
                feedback_player_target = player_name
                feedback_message_content = "تنسيق اللوحة المرسلة غير صالح."
                send_targeted_feedback = True
                action_processed = False
            else:
                is_correct, _ = check_solution_correctness(submitted_board, gs.get("solution_board"))
                if is_correct:
                    if gs.get("winner") is None: 
                        gs["winner"] = player_name
                        gs["phase"] = "GAME_OVER"
                        gs["status_message"] = f"🎉 اللاعب {player_name} حل لغز السودوكو بشكل صحيح وفاز باللعبة!"
                        send_full_update = True 
                    else:
                        feedback_player_target = player_name
                        feedback_message_content = f"أحسنت! لقد حللتها، لكن {gs['winner']} كان الأسرع."
                        send_targeted_feedback = True
                else:
                    feedback_player_target = player_name
                    feedback_message_content = "الحل الذي أرسلته غير صحيح. حاول مرة أخرى!"
                    send_targeted_feedback = True
            action_processed = True 
        else:
            action_processed = False 
            if player_name in players_data and gs["phase"] != "PLAYING":
                feedback_player_target = player_name
                feedback_message_content = "لا يمكنك إرسال الحل الآن (اللعبة لم تبدأ أو انتهت)."
                send_targeted_feedback = True

    elif action_type == "RESTART_SUDOKU_GAME": 
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "GAME_OVER":
            gs["phase"] = "LOBBY"
            gs["puzzle_board"] = None
            gs["solution_board"] = None 
            gs["winner"] = None
            gs["difficulty"] = "normal" 
            gs["status_message"] = "الهوست أعاد اللعبة. في انتظار بدء لعبة سودوكو جديدة."
            send_full_update = True
        else:
            action_processed = False 

    else:
        action_processed = False 
        print(f"Server: Room {room_code}: Unknown Sudoku action type '{action_type}' or not processed.")

    game_rooms_ref[room_code]["game_state"] = gs

    if send_full_update:
        if page_ref.client_storage: 
            print(f"Server: Sending GAME_STATE_UPDATE for room {room_code}. New phase: {gs.get('phase')}, Status: {gs.get('status_message')}")
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )
        else:
            print(f"Server: Sudoku Room {room_code}: Server page detached, cannot send pubsub for full update on {action_type}.")
    elif send_targeted_feedback and feedback_player_target and feedback_message_content:
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {
                    "type": "SUDOKU_SUBMISSION_FEEDBACK", 
                    "room_code": room_code, 
                    "feedback_for_player": feedback_player_target,
                    "feedback_message": feedback_message_content,
                }
            )
        else:
            print(f"Server: Sudoku Room {room_code}: Server page detached, cannot send pubsub for targeted feedback on {action_type}.")
    # Removed the 'elif gs.get("status_message") != original_status_message' block as GAME_STATE_UPDATE covers it.