# server_actions/sudoku_actions.py
import flet as ft
from sudoku_utils import get_sudoku_puzzle, check_solution_correctness, copy_board

def validate_sudoku_solution(board: list[list[int]]) -> dict:
    """
    Validate Sudoku solution
    Returns {"valid": True} if valid, {"valid": False} otherwise
    """
    # We need to check if the board is valid according to Sudoku rules
    # Since we don't have the solution here, we'll check the board rules
    # This is similar to the offline validation logic
    if not board or len(board) != 9 or not all(len(row) == 9 for row in board):
        return {"valid": False}
    
    # Check rows, columns, and 3x3 boxes
    for i in range(9):
        row_set = set()
        col_set = set()
        for j in range(9):
            # Check row
            if board[i][j] != 0:
                if board[i][j] in row_set:
                    return {"valid": False}
                row_set.add(board[i][j])
            
            # Check column
            if board[j][i] != 0:
                if board[j][i] in col_set:
                    return {"valid": False}
                col_set.add(board[j][i])
    
    # Check 3x3 boxes
    for box_i in range(0, 9, 3):
        for box_j in range(0, 9, 3):
            box_set = set()
            for i in range(box_i, box_i+3):
                for j in range(box_j, box_j+3):
                    if board[i][j] != 0:
                        if board[i][j] in box_set:
                            return {"valid": False}
                        box_set.add(board[i][j])
    
    return {"valid": True}

def process_sudoku_action(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    if room_code not in game_rooms_ref or game_rooms_ref[room_code]["game_type"] != "sudoku":
        print(f"Error: Room {room_code} not found or not a Sudoku game.")
        # Optionally, send an error back to the specific client if possible,
        # though this action processor is generic.
        # For now, the client might just not see an update or the game might not progress.
        return

    room = game_rooms_ref[room_code]
    gs = room["game_state"]
    players_data = room["players"] # Used to check if player is host

    action_processed = True
    original_status_message = gs.get("status_message")
    send_full_update = False 
    send_targeted_feedback = False
    feedback_player_target = None
    feedback_message_content = ""


    if action_type == "SETUP_SUDOKU_GAME":
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "LOBBY":
            difficulty = payload.get("difficulty", "normal")
            puzzle, solution = get_sudoku_puzzle(difficulty) # Assumes this returns (puzzle_matrix, solution_matrix)

            gs["puzzle_board"] = puzzle
            gs["solution_board"] = solution # Crucial: Server sends the solution to clients
            gs["difficulty"] = difficulty
            gs["winner"] = None
            gs["phase"] = "PLAYING"
            gs["status_message"] = f"بدأت لعبة سودوكو"
            send_full_update = True
        else:
            # Conditions not met for starting the game (not host or not in LOBBY)
            # Set a status message that clients can see if they attempt this action invalidly.
            # This might not be the best place for this message if only host sees start button,
            # but good for robustness.
            gs["status_message"] = "لا يمكن بدء لعبة سودوكو الآن." 
            send_full_update = True 
            action_processed = False 

    elif action_type == "VALIDATE_SUDOKU_SOLUTION":
        if gs["phase"] == "PLAYING" and player_name in players_data:
            submitted_board = payload.get("board")
            if not submitted_board or len(submitted_board) != 9 or not all(len(row) == 9 for row in submitted_board):
                feedback_message_content = "تنسيق اللوحة المرسلة غير صالح."
                is_correct = False
            else:
                is_correct, _ = check_solution_correctness(submitted_board, gs.get("solution_board"))
                feedback_message_content = "✅ الحل صحيح! يمكنك الآن إرساله للخادم." if is_correct else "⚠️ الحل الذي أدخلته غير صحيح. راجعه."
            
            if page_ref.client_storage:
                page_ref.pubsub.send_all_on_topic(
                    f"room_{room_code}",
                    {
                        "type": "SUDOKU_VALIDATION_RESULT",
                        "player": player_name,
                        "valid": is_correct,
                        "message": feedback_message_content
                    }
                )
            action_processed = True

    elif action_type == "SUBMIT_SUDOKU_SOLUTION":
        if gs["phase"] == "PLAYING" and player_name in players_data: # Ensure player is part of the game
            submitted_board = payload.get("board")
            if not submitted_board or len(submitted_board) != 9 or not all(len(row) == 9 for row in submitted_board):
                feedback_player_target = player_name
                feedback_message_content = "تنسيق اللوحة المرسلة غير صالح."
                send_targeted_feedback = True
                action_processed = False # Invalid payload, action didn't fully succeed
            else:
                is_correct, _ = check_solution_correctness(submitted_board, gs.get("solution_board"))

                if is_correct:
                    if gs.get("winner") is None: # First correct submission
                        gs["winner"] = player_name
                        gs["phase"] = "GAME_OVER"
                        gs["status_message"] = f"🎉 اللاعب {player_name} حل لغز السودوكو بشكل صحيح وفاز باللعبة!"
                        send_full_update = True # Send full update to announce winner and game over
                    else:
                        # Player solved it, but someone was faster
                        feedback_player_target = player_name
                        feedback_message_content = f"أحسنت! لقد حللتها، لكن {gs['winner']} كان الأسرع."
                        send_targeted_feedback = True
                        # Game state (winner, phase) doesn't change here, already determined
                else:
                    # Incorrect submission
                    feedback_player_target = player_name
                    feedback_message_content = "الحل الذي أرسلته غير صحيح. حاول مرة أخرى!"
                    send_targeted_feedback = True
                    # Game state doesn't change for an incorrect submission by one player
            action_processed = True # The submission attempt was processed
        else:
            # Player not in game, or game not in playing phase, or player unknown
            action_processed = False
            # Optionally send targeted feedback if player_name is known but conditions not met
            if player_name in players_data and gs["phase"] != "PLAYING":
                feedback_player_target = player_name
                feedback_message_content = "لا يمكنك إرسال الحل الآن (اللعبة لم تبدأ أو انتهت)."
                send_targeted_feedback = True


    elif action_type == "RESTART_SUDOKU_GAME": # Host action
        if players_data.get(player_name, {}).get("is_host") and gs["phase"] == "GAME_OVER":
            gs["phase"] = "LOBBY"
            gs["puzzle_board"] = None
            gs["solution_board"] = None # Clear previous solution
            gs["winner"] = None
            gs["difficulty"] = "normal" # Reset to default or last used
            gs["status_message"] = "الهوست أعاد اللعبة. في انتظار بدء لعبة سودوكو جديدة."
            send_full_update = True
        else:
            action_processed = False # Not host or game not over
            # Could send targeted feedback if needed

    else:
        action_processed = False # Unknown action
        print(f"Room {room_code}: Unknown Sudoku action type '{action_type}' or not processed.")

    # Persist changes to the game room's state
    game_rooms_ref[room_code]["game_state"] = gs
    # game_rooms_ref[room_code]["players"] = players_data # players_data itself is rarely modified here

    # Determine if a pubsub update needs to be sent
    if send_full_update:
        if page_ref.client_storage: # Check if the server's page object is still valid (client connected)
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]}
            )
        else:
            print(f"Sudoku Room {room_code}: Server page detached, cannot send pubsub for full update on {action_type}.")
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
            print(f"Sudoku Room {room_code}: Server page detached, cannot send pubsub for targeted feedback on {action_type}.")
    elif gs.get("status_message") != original_status_message and action_processed:
        # This handles cases where only status_message changed due to an invalid action by host
        # but not requiring a full state refresh for all game elements,
        # and it wasn't a targeted feedback scenario.
        if page_ref.client_storage:
            page_ref.pubsub.send_all_on_topic(
                f"room_{room_code}",
                {"type": "GAME_STATE_UPDATE", "room_state": game_rooms_ref[room_code]} # Send full state for simplicity
            )
        else:
            print(f"Sudoku Room {room_code}: Server page detached, cannot send pubsub for status message update on {action_type}.")