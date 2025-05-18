# trivia_battle_game.py
import flet as ft
import random
import importlib 
import os 

# --- OFFLINE MODE LOGIC ---
def trivia_battle_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {}

    trivia_categories_offline = {
        "The Office": "trivia_data.trivia_the_office", 
        "رياضة": "trivia_data.trivia_sports",
        "جغرافيا": "trivia_data.trivia_geography",
        "ثقافة عامة": "trivia_data.trivia_general_knowledge",
        "موسيقى": "trivia_data.trivia_music"
    }
    if not os.path.isdir("trivia_data"): 
        print("CRITICAL WARNING: 'trivia_data' directory not found. Trivia questions will likely fail to load.")
        trivia_categories_offline = {"خطأ في تحميل الفئات": None}

    def load_questions_offline(module_name_str): 
        if not module_name_str: return []
        try:
            module_to_import = module_name_str 
            mod = importlib.import_module(module_to_import)
            loaded_qs = getattr(mod, "trivia_questions", [])
            valid_qs = [
                q for q in loaded_qs 
                if isinstance(q, dict) and 
                   all(k in q for k in ["question", "options", "answer"]) and
                   isinstance(q["options"], list) and len(q["options"]) > 1 
            ]
            if len(valid_qs) != len(loaded_qs):
                print(f"Offline Warning: Some invalid question formats in {module_name_str}. Loaded {len(valid_qs)} valid questions.")
            return valid_qs
        except ModuleNotFoundError:
            print(f"Offline - Module not found: {module_name_str}. Make sure it's in trivia_data/ and __init__.py exists if needed.")
            return []
        except AttributeError:
            print(f"Offline - Variable 'trivia_questions' not found in module: {module_name_str}.")
            return []
        except Exception as e:
            print(f"Offline - Error loading questions from {module_name_str}: {e}")
            return []

    player_name_inputs_offline = [] # Changed from team_name_inputs_offline
    offline_main_column = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, 
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)

    def reset_offline_trivia_state():
        offline_state.clear()
        offline_state.update({
            "step": "choose_player_count", # CHANGED from choose_team_count
            "player_count": 2,          # CHANGED from team_count
            "players": [],              # CHANGED from teams
            "scores": {},               # Will store player scores {player_name: score}
            "selected_category_name": None, 
            "question_pool": [], 
            "current_question_idx_in_pool": 0,
            "questions_per_player": 10, # New state for offline
            "current_player_turn_idx": 0,# CHANGED from current_team_turn_idx
            "player_question_counts": {},# Tracks questions answered by each player
            "current_question_data": None, 
            "answer_submitted_this_q": False,
            "last_q_correct_bool": None, 
            "last_q_correct_answer_text": "",
            "total_questions_answered_this_game": 0, # Overall count
            "max_total_questions": 0 
        })
        update_offline_trivia_ui()

    def set_offline_trivia_step(step_name):
        offline_state["step"] = step_name
        update_offline_trivia_ui()

    def update_offline_trivia_ui():
        offline_main_column.controls.clear()
        s = offline_state

        if s["step"] == "choose_player_count": # CHANGED
            offline_main_column.controls.append(ft.Text("👥 كم عدد اللاعبين؟ (2-6)", size=24))
            player_count_display = ft.Text(str(s["player_count"]), size=26)
            def change_player_count_offline(delta):
                s["player_count"] = max(2, min(6, s["player_count"] + delta))
                player_count_display.value = str(s["player_count"])
                if page.client_storage: page.update(player_count_display)
            offline_main_column.controls.extend([
                player_count_display,
                ft.Row([
                    ft.IconButton(icon=ft.icons.REMOVE, on_click=lambda e: change_player_count_offline(-1)),
                    ft.IconButton(icon=ft.icons.ADD, on_click=lambda e: change_player_count_offline(1)),
                ], alignment="center"),
                ft.ElevatedButton("التالي: أسماء اللاعبين", on_click=lambda e: prepare_player_name_inputs_offline(), width=200), # CHANGED
                ft.ElevatedButton("🏠 العودة للقائمة", on_click=lambda e: safe_go_home_offline_trivia(), width=200)
            ])
        elif s["step"] == "enter_player_names": # CHANGED
            offline_main_column.controls.append(ft.Text("✏️ أدخل أسماء اللاعبين:", size=24))
            offline_main_column.controls.extend(player_name_inputs_offline) 
            offline_main_column.controls.append(ft.ElevatedButton("التالي: اختيار الفئة", on_click=lambda e: save_players_offline(), width=200)) # CHANGED
        
        elif s["step"] == "choose_category":
            offline_main_column.controls.append(ft.Text("🧠 اختر فئة الأسئلة", size=24))
            cat_options = [ft.dropdown.Option(key=cat_key, text=cat_key) for cat_key in trivia_categories_offline.keys()]
            category_dd_offline = ft.Dropdown(options=cat_options, label="الفئة", width=300)
            offline_main_column.controls.append(category_dd_offline)
            offline_main_column.controls.append(ft.ElevatedButton("بدء اللعبة بالفئة المختارة", on_click=lambda e: confirm_category_offline(category_dd_offline.value), width=250))

        elif s["step"] == "question_display":
            current_player_name = s["players"][s["current_player_turn_idx"]] # CHANGED
            q_data = s.get("current_question_data")
            if not q_data:
                # ... (error handling same)
                offline_main_column.controls.append(ft.Text("خطأ: لا يوجد سؤال حالي أو انتهت الأسئلة.", color=ft.colors.RED))
                offline_main_column.controls.append(ft.ElevatedButton("النتائج النهائية", on_click=lambda e: set_offline_trivia_step("results")))
                if page.client_storage: page.update(); return

            # Calculate overall question number for display
            # This is a bit tricky with individual player quotas.
            # Let's show current player's question number out of their quota.
            player_q_count = s["player_question_counts"].get(current_player_name, 0)
            total_qs_for_player = s["questions_per_player"]

            offline_main_column.controls.append(ft.Text(f"❓ سؤال للاعب: {current_player_name} (سؤاله رقم {player_q_count + 1}/{total_qs_for_player})", size=20, weight="bold", color=ft.colors.BLUE_700)) # CHANGED
            offline_main_column.controls.append(ft.Text(q_data.get("question",""), size=22, text_align=ft.TextAlign.CENTER, weight="bold", selectable=True))
            
            options_column = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER, width=350) 
            shuffled_options = list(q_data.get("options",[])) 
            random.shuffle(shuffled_options)
            for opt_text in shuffled_options:
                options_column.controls.append(
                    ft.ElevatedButton(text=opt_text, width=300, height=50, on_click=lambda e, chosen_opt=opt_text: handle_answer_offline(chosen_opt))
                )
            offline_main_column.controls.append(options_column)

        elif s["step"] == "answer_feedback":
            current_player_name = s["players"][s["current_player_turn_idx"]] # CHANGED
            q_data = s.get("current_question_data",{})
            offline_main_column.controls.append(ft.Text(f"سؤال اللاعب: {current_player_name}", size=18)) # CHANGED
            offline_main_column.controls.append(ft.Text(q_data.get("question",""), size=20, text_align=ft.TextAlign.CENTER))
            
            if s.get("last_q_correct_bool"):
                offline_main_column.controls.append(ft.Text("✅ إجابة صحيحة!", color=ft.colors.GREEN_700, size=22, weight="bold"))
            else:
                offline_main_column.controls.append(ft.Text(f"❌ إجابة خاطئة! الجواب الصحيح: {s.get('last_q_correct_answer_text','')}", color=ft.colors.RED_700, size=20, weight="bold"))

            offline_main_column.controls.append(ft.Text("📊 النقاط الحالية:", size=20, weight="bold"))
            for p_name, p_score in s.get("scores",{}).items(): # Iterate player scores
                offline_main_column.controls.append(ft.Text(f"- اللاعب {p_name}: {p_score} نقطة"))
            
            offline_main_column.controls.append(ft.ElevatedButton("السؤال التالي / اللاعب التالي", on_click=lambda e: proceed_to_next_question_or_player_offline(), width=250)) # CHANGED
        
        elif s["step"] == "results":
            offline_main_column.controls.append(ft.Text("🎉 انتهت اللعبة!", size=24, weight="bold"))
            offline_main_column.controls.append(ft.Text("🏆 النتائج النهائية:", size=22))
            sorted_scores = sorted(s.get("scores",{}).items(), key=lambda x: x[1], reverse=True)
            for p_name, score_val in sorted_scores: # Iterate player scores
                offline_main_column.controls.append(ft.Text(f"- اللاعب {p_name}: {score_val} نقطة"))
            offline_main_column.controls.extend([
                ft.ElevatedButton("🔁 العب مرة أخرى", on_click=lambda e: reset_offline_trivia_state()),
                ft.ElevatedButton("🏠 العودة للقائمة", on_click=lambda e: safe_go_home_offline_trivia())
            ])
        else: 
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'"))
            offline_main_column.controls.append(ft.ElevatedButton("العودة للرئيسية", on_click=safe_go_home_offline_trivia))
        
        if page.client_storage: page.update()

    def prepare_player_name_inputs_offline(): # CHANGED
        player_name_inputs_offline.clear() 
        for i in range(offline_state["player_count"]): # CHANGED
            player_name_inputs_offline.append(ft.TextField(label=f"اسم اللاعب {i+1}", width=300)) # CHANGED
        set_offline_trivia_step("enter_player_names") # CHANGED

    def save_players_offline(): # CHANGED
        s = offline_state
        names = [tf.value.strip() for tf in player_name_inputs_offline if tf.value.strip()] # CHANGED
        if len(names) != s["player_count"] or len(set(names)) != len(names) or any(not n for n in names):
            page.snack_bar = ft.SnackBar(ft.Text("أسماء اللاعبين يجب أن تكون فريدة ومكتملة!"), open=True)
            if page.client_storage: page.update()
            return
        s["players"] = names # CHANGED
        s["scores"] = {name: 0 for name in names}
        s["player_question_counts"] = {name: 0 for name in names}
        s["max_total_questions"] = len(s["players"]) * s["questions_per_player"]
        set_offline_trivia_step("choose_category")

    def confirm_category_offline(cat_name):
        s = offline_state
        if not cat_name:
            page.snack_bar = ft.SnackBar(ft.Text("الرجاء اختيار فئة."), open=True)
            if page.client_storage: page.update()
            return
        s["selected_category_name"] = cat_name
        module_path_str = trivia_categories_offline.get(cat_name)
        
        all_questions = load_questions_offline(module_path_str)

        if not all_questions:
            page.snack_bar = ft.SnackBar(ft.Text(f"لا توجد أسئلة في فئة '{cat_name}'. اختر فئة أخرى."), open=True)
            if page.client_storage: page.update()
            return
        
        # Max total questions needed for the game based on players and questions_per_player
        s["max_total_questions"] = len(s["players"]) * s["questions_per_player"]
        
        if len(all_questions) < s["max_total_questions"]:
            print(f"Offline Warning: Category '{cat_name}' has {len(all_questions)} questions, need {s['max_total_questions']}. Using all available. Game might be shorter.")
            s["question_pool"] = random.sample(all_questions, len(all_questions))
            s["max_total_questions"] = len(s["question_pool"]) # Adjust max if not enough questions
        else:
            s["question_pool"] = random.sample(all_questions, s["max_total_questions"])
        
        if not s["question_pool"]:
            page.snack_bar = ft.SnackBar(ft.Text(f"خطأ: لا توجد أسئلة متاحة في '{cat_name}'."), open=True)
            if page.client_storage: page.update()
            set_offline_trivia_step("choose_category")
            return

        s["current_question_idx_in_pool"] = 0
        s["total_questions_answered_this_game"] = 0 # Overall counter for pool
        s["current_player_turn_idx"] = 0 
        s["player_question_counts"] = {player_name: 0 for player_name in s["players"]} # Reset counts
        load_next_question_offline() 

    def load_next_question_offline():
        s = offline_state
        current_player_name = s["players"][s["current_player_turn_idx"]]

        # Check if current player has answered enough questions
        if s["player_question_counts"].get(current_player_name, 0) >= s["questions_per_player"]:
            # This player is done, try to move to next or end game (handled by proceed_to_next_...)
            proceed_to_next_question_or_player_offline() 
            return

        if s["current_question_idx_in_pool"] < len(s["question_pool"]):
            s["current_question_data"] = s["question_pool"][s["current_question_idx_in_pool"]]
            s["answer_submitted_this_q"] = False
            s["last_q_correct_bool"] = None
            s["last_q_correct_answer_text"] = ""
            set_offline_trivia_step("question_display")
        else: 
            # Pool exhausted, but some players might not have hit their quota if pool was small
            set_offline_trivia_step("results")


    def handle_answer_offline(chosen_option):
        s = offline_state
        q_data = s["current_question_data"]
        if not q_data: return
        correct_ans = q_data.get("answer")
        s["answer_submitted_this_q"] = True
        s["last_q_correct_answer_text"] = correct_ans

        current_player_name = s["players"][s["current_player_turn_idx"]] # CHANGED
        if chosen_option == correct_ans:
            s["last_q_correct_bool"] = True
            s["scores"][current_player_name] = s["scores"].get(current_player_name, 0) + 1
        else:
            s["last_q_correct_bool"] = False
        
        s["player_question_counts"][current_player_name] = s["player_question_counts"].get(current_player_name, 0) + 1
        s["total_questions_answered_this_game"] +=1 # This is the index into the shared pool
        set_offline_trivia_step("answer_feedback")
    
    def proceed_to_next_question_or_player_offline(): # CHANGED
        s = offline_state

        # Check if all players have completed their quota
        all_done = True
        for p_name in s["players"]:
            if s["player_question_counts"].get(p_name, 0) < s["questions_per_player"]:
                all_done = False
                break
        
        if all_done or s["total_questions_answered_this_game"] >= s["max_total_questions"]:
            set_offline_trivia_step("results")
            return

        # Cycle to next player
        s["current_player_turn_idx"] = (s["current_player_turn_idx"] + 1) % len(s["players"])
        
        # Find the next player who still needs to answer questions
        # This loop ensures we skip players who have already answered 10 questions
        start_idx_loop_check = s["current_player_turn_idx"]
        while s["player_question_counts"].get(s["players"][s["current_player_turn_idx"]], 0) >= s["questions_per_player"]:
            s["current_player_turn_idx"] = (s["current_player_turn_idx"] + 1) % len(s["players"])
            if s["current_player_turn_idx"] == start_idx_loop_check:
                # This means all remaining players have finished their quota, should go to results
                set_offline_trivia_step("results")
                return
        
        s["current_question_idx_in_pool"] +=1 # Advance the main pool index
        load_next_question_offline()

    def safe_go_home_offline_trivia(e=None):
        offline_state.clear() 
        go_home_fn()

    reset_offline_trivia_state()
    return [ft.Container(content=offline_main_column, expand=True, alignment=ft.alignment.top_center, padding=10)]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def trivia_battle_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    page_title = ft.Text(f"تريفيا باتل - غرفة: {room_code}", size=20, weight="bold")
    status_text = ft.Text("قيد التحميل...", size=18, weight="bold", text_align=ft.TextAlign.CENTER)
    player_list_display = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=5, height=120, alignment=ft.MainAxisAlignment.START)
    player_score_display_online = ft.Column(spacing=5, alignment=ft.MainAxisAlignment.START) # CHANGED
    action_area = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, scroll=ft.ScrollMode.ADAPTIVE) 
    question_display_online = ft.Column(visible=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5) 
    
    online_main_container = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    def log_debug_online(msg):
        print(f"[Trivia_Online_Client:{current_player_name} session:{page.session_id}] {msg}")

    def update_ui_from_server_state_online_trivia(room_state_from_server):
        if not page.client_storage: 
            log_debug_online("Page detached, skipping UI update.")
            return

        gs = room_state_from_server.get("game_state",{}) 
        players_in_room = room_state_from_server.get("players",{}) # This is {name: {details}}
        # Scores are now per player
        player_scores = gs.get("players_scores_online", {}) # CHANGED

        my_player_data = players_in_room.get(current_player_name,{})
        is_host = my_player_data.get("is_host", False)
        current_phase = gs.get("phase", "LOBBY")

        log_debug_online(f"Trivia online UI update, phase: {current_phase}")
        status_text.value = gs.get("status_message", "...")
        
        player_list_display.controls.clear()
        player_list_display.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)} / {gs.get('max_players_for_game', 6)}):", weight="bold"))
        for p_name, p_data in players_in_room.items():
            player_list_display.controls.append(
                ft.Text(f"• {p_data.get('name','Unknown')} {'👑' if p_data.get('is_host') else ''}")
            )
        
        player_score_display_online.controls.clear()
        player_score_display_online.controls.append(ft.Text("النقاط:", weight="bold"))
        if player_scores:
            for p_name, score in player_scores.items():
                player_score_display_online.controls.append(ft.Text(f"{p_name}: {score}"))
        else:
            player_score_display_online.controls.append(ft.Text("لم تبدأ اللعبة بعد."))

        action_area.controls.clear()
        question_display_online.controls.clear()
        question_display_online.visible = False


        if current_phase == "LOBBY":
            min_players = gs.get("min_players_for_game", 2)
            action_area.controls.append(ft.Text(f"في انتظار انضمام اللاعبين ({min_players}-{gs.get('max_players_for_game', 6)}).", text_align=ft.TextAlign.CENTER))
            if is_host:
                # Category selection for host
                # This map should match TRIVIA_CATEGORIES_SERVER_MAP in server_actions
                online_trivia_cats_client = { 
                    "The Office": "trivia_data.trivia_the_office", 
                    "رياضة": "trivia_data.trivia_sports",
                    "جغرافيا": "trivia_data.trivia_geography",
                    "ثقافة عامة": "trivia_data.trivia_general_knowledge",
                    "موسيقى": "trivia_data.trivia_music"
                }
                cat_dd_online = ft.Dropdown(label="اختر فئة الأسئلة", options=[ft.dropdown.Option(k) for k in online_trivia_cats_client.keys()], width=300)
                action_area.controls.append(cat_dd_online)

                def host_start_trivia_game(e):
                    selected_cat = cat_dd_online.value
                    if not selected_cat:
                        page.snack_bar = ft.SnackBar(ft.Text("الرجاء اختيار فئة للأسئلة."),open=True)
                        if page.client_storage: page.update()
                        return
                    # No team names needed, just category
                    send_action_fn("SETUP_TRIVIA_GAME_HOST", {"category": selected_cat})

                can_start = len(players_in_room) >= min_players
                start_button = ft.ElevatedButton("🚀 بدء اللعبة", on_click=host_start_trivia_game, disabled=not can_start)
                action_area.controls.append(start_button)
                if not can_start:
                    action_area.controls.append(ft.Text(f"تحتاج إلى {min_players - len(players_in_room)} لاعبين إضافيين على الأقل.", color=ft.colors.ORANGE_600))


        elif current_phase == "QUESTION_DISPLAY_ONLINE":
            question_display_online.visible = True
            current_q_online = gs.get("current_question_online_data", {})
            current_acting_player = gs.get("current_acting_player_online") # CHANGED key
            is_my_turn = (current_player_name == current_acting_player)

            player_q_count = gs.get("player_question_counts", {}).get(current_acting_player, 0)
            total_qs_for_player = gs.get("questions_per_player", 10)

            question_display_online.controls.append(ft.Text(f"سؤال للاعب: {current_acting_player} (سؤاله {player_q_count + 1}/{total_qs_for_player})", size=18, weight="bold", color=ft.colors.BLUE_700))
            question_display_online.controls.append(ft.Text(current_q_online.get("question", "تحميل السؤال..."), size=22, weight="bold", text_align=ft.TextAlign.CENTER))
            
            options_area_online = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            q_options = current_q_online.get("options", [])
            for opt in q_options:
                btn = ft.ElevatedButton(
                    text=opt, width=300, height=50,
                    on_click= (lambda e, chosen_opt=opt: send_action_fn("SUBMIT_TRIVIA_ANSWER", {"answer": chosen_opt})) if is_my_turn else None, 
                    disabled=not is_my_turn
                )
                options_area_online.controls.append(btn)
            action_area.controls.append(options_area_online) 
            if not is_my_turn:
                action_area.controls.append(ft.Text(f"انتظر دورك. الآن دور {current_acting_player}.", italic=True))

        elif current_phase == "ANSWER_FEEDBACK_ONLINE":
            question_display_online.visible = True 
            q_data_online = gs.get("last_answered_question_data", {})
            last_actor = gs.get("current_acting_player_online") # The player who just answered
            question_display_online.controls.append(ft.Text(f"السؤال كان لـ {last_actor}: {q_data_online.get('question','')}", size=18, text_align=ft.TextAlign.CENTER))
            
            if gs.get("last_answer_was_correct"):
                action_area.controls.append(ft.Text("✅ إجابة صحيحة!", color=ft.colors.GREEN_700, size=22, weight="bold"))
            else:
                action_area.controls.append(ft.Text(f"❌ إجابة خاطئة! الجواب: {gs.get('correct_answer_text_for_last_q','')}", color=ft.colors.RED_700, size=20, weight="bold"))
            
            if is_host:
                action_area.controls.append(ft.ElevatedButton("السؤال/اللاعب التالي", on_click=lambda e: send_action_fn("NEXT_TRIVIA_QUESTION_HOST")))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست للسؤال التالي..."))


        elif current_phase == "GAME_OVER_TRIVIA":
            action_area.controls.append(ft.Text("🏁 انتهت لعبة التريفيا!", size=24, weight="bold", text_align=ft.TextAlign.CENTER))
            if player_scores:
                sorted_players = sorted(player_scores.items(), key=lambda item: item[1], reverse=True)
                for p_name_iter, score_val in sorted_players:
                    action_area.controls.append(ft.Text(f"اللاعب {p_name_iter}: {score_val} نقطة", size=20, text_align=ft.TextAlign.CENTER))
            if is_host:
                action_area.controls.append(ft.ElevatedButton("🔄 جولة جديدة بنفس اللاعبين والفئة", on_click=lambda e: send_action_fn("RESTART_TRIVIA_HOST")))
        
        if page.client_storage:
            log_debug_online(f"EXECUTING page.update() for Trivia phase {current_phase}")
            page.update()


    def on_server_message_online_trivia(*args_received):
        # ... (same as before)
        if not page.client_storage: return
        log_debug_online(f"TRIVIA_PUBSUB_RAW_ARGS_RECEIVED: {args_received}")
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]   
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
        log_debug_online(f"Processing Trivia PubSub: Type: {msg_type}")
        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online_trivia(room_state)
        elif msg_type == "ACTION_ERROR":
            error_msg = msg_data.get("message", "حدث خطأ في تريفيا باتل.")
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text(error_msg), open=True); page.update()


    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online_trivia)
    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data: update_ui_from_server_state_online_trivia(initial_room_data)

    online_main_container.controls.extend([
        ft.Row([page_title, ft.IconButton(ft.icons.HOME, tooltip="العودة للرئيسية", on_click=go_home_fn)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(), status_text, ft.Divider(),
        question_display_online, 
        ft.Row([
            ft.Container(content=ft.Column([player_list_display, ft.Divider(), player_score_display_online]), # CHANGED to player_score_display_online
                         padding=10, border=ft.border.all(1, "outline"), border_radius=5, width=280, margin=ft.margin.only(right=10)),
            ft.VerticalDivider(),
            ft.Container(content=action_area, padding=10, expand=True, alignment=ft.alignment.top_center)
        ], vertical_alignment=ft.CrossAxisAlignment.START, expand=True),
    ])
    return [online_main_container]


# --- GAME ENTRY POINT ---
def trivia_battle_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return trivia_battle_offline_logic(page, go_home_fn)
    else:
        if not all([room_code, player_name, game_rooms_ref]):
             return [ft.Container(content=ft.Text("خطأ في تحميل لعبة تريفيا باتل أونلاين."), alignment=ft.alignment.center, expand=True)]
        
        def send_trivia_action_to_server_wrapper(action_type: str, payload: dict = None): # Renamed for clarity
            process_action_fn(page, room_code, player_name, "trivia_battle", action_type, payload or {})
            
        return trivia_battle_online_logic(page, go_home_fn, send_trivia_action_to_server_wrapper, room_code, player_name, game_rooms_ref)