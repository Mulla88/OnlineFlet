# trivia_battle_game.py
import flet as ft
import random
import importlib
import os

# --- OFFLINE MODE LOGIC ---
def trivia_battle_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {}

    trivia_categories_offline_map = {
        "The Office": "trivia_data.trivia_the_office",
        "رياضة": "trivia_data.trivia_sports",
        "جغرافيا": "trivia_data.trivia_geography",
        "ثقافة عامة": "trivia_data.trivia_general_knowledge",
        "موسيقى": "trivia_data.trivia_music"
    }
    if not os.path.isdir("trivia_data"):
        print("CRITICAL WARNING: 'trivia_data' directory not found. Trivia questions will likely fail to load.")
        trivia_categories_offline_map = {"خطأ في تحميل الفئات": None}

    def load_questions_offline(module_name_str):
        if not module_name_str: return []
        try:
            module_to_import = module_name_str
            mod = importlib.import_module(module_to_import)
            importlib.reload(mod)
            loaded_qs = getattr(mod, "trivia_questions", [])
            valid_qs = [
                q for q in loaded_qs
                if isinstance(q, dict) and
                   all(k in q for k in ["question", "options", "answer"]) and
                   isinstance(q["options"], list) and len(q["options"]) > 1
            ]
            if len(valid_qs) != len(loaded_qs):
                print(f"Offline Warning: Some invalid question formats in {module_name_str}. Loaded {len(valid_qs)} valid questions out of {len(loaded_qs)}.")
            return valid_qs
        except ModuleNotFoundError:
            print(f"Offline - Module not found: {module_name_str}.")
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text(f"خطأ: ملف الفئة '{module_name_str.split('.')[-1]}' غير موجود."), open=True)
                page.update()
            return []
        except AttributeError:
            print(f"Offline - Variable 'trivia_questions' not found in module: {module_name_str}.")
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text(f"خطأ: لا يوجد متغير 'trivia_questions' في ملف الفئة."), open=True)
                page.update()
            return []
        except Exception as e:
            print(f"Offline - Error loading questions from {module_name_str}: {e}")
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text(f"خطأ عام في تحميل الأسئلة."), open=True)
                page.update()
            return []

    player_name_inputs_offline_controls = []

    # --- OFFLINE UI ENHANCEMENT: Persistent Home Button ---
    offline_title_bar = ft.Row(
        [
            ft.Text("🧠 معركة التريفيا (أوفلاين)", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=lambda e: safe_go_home_offline_trivia(),
                icon_size=28 # Slightly smaller for consistency
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    # --- END OFFLINE UI ENHANCEMENT ---

    offline_main_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15 # Adjusted spacing
    )

    def reset_offline_trivia_state():
        nonlocal player_name_inputs_offline_controls
        offline_state.clear()
        offline_state.update({
            "step": "choose_player_count",
            "player_count": 2,
            "players": [],
            "scores": {},
            "selected_category_name": None,
            "question_pool": [],
            "current_question_idx_in_pool": 0,
            "questions_per_player": 10,
            "current_player_turn_idx": 0,
            "player_question_counts": {},
            "current_question_data": None,
            "answer_submitted_this_q": False,
            "last_q_correct_bool": None,
            "last_q_correct_answer_text": "",
            "total_questions_answered_this_game": 0,
            "max_total_questions": 0
        })
        player_name_inputs_offline_controls = []
        update_offline_trivia_ui()

    def set_offline_trivia_step(step_name):
        offline_state["step"] = step_name
        update_offline_trivia_ui()

    def update_offline_trivia_ui():
        nonlocal player_name_inputs_offline_controls
        if not page.client_storage: return

        offline_main_column.controls.clear()
        # --- OFFLINE UI ENHANCEMENT: Add title bar ---
        offline_main_column.controls.append(offline_title_bar)
        offline_main_column.controls.append(ft.Divider(height=1, thickness=0.5))
        # --- END OFFLINE UI ENHANCEMENT ---

        s = offline_state

        if s["step"] == "choose_player_count":
            # Title is now in offline_title_bar
            # offline_main_column.controls.append(ft.Text("🧠 معركة التريفيا", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            offline_main_column.controls.append(ft.Text("👥 كم عدد اللاعبين؟ (2-6)", size=24, text_align=ft.TextAlign.CENTER)) # Adjusted size
            player_count_display = ft.Text(str(s["player_count"]), size=28, weight=ft.FontWeight.BOLD) # Adjusted size
            def change_player_count_offline(delta):
                s["player_count"] = max(2, min(6, s["player_count"] + delta))
                player_count_display.value = str(s["player_count"])
                if page.client_storage: player_count_display.update()
            offline_main_column.controls.extend([
                ft.ResponsiveRow(
                    [
                        ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e: change_player_count_offline(-1), col={"xs":4}, icon_size=28),
                        ft.Container(content=player_count_display, col={"xs":4}, alignment=ft.alignment.center),
                        ft.IconButton(icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e: change_player_count_offline(1), col={"xs":4}, icon_size=28),
                    ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=5
                ),
                ft.ElevatedButton("التالي: أسماء اللاعبين", on_click=lambda e: prepare_player_name_inputs_offline(), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                # Removed redundant "Back to Menu" button as persistent home button exists
                # ft.ElevatedButton("🏠 العودة للقائمة", on_click=lambda e: safe_go_home_offline_trivia(), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])
        elif s["step"] == "enter_player_names":
            offline_main_column.controls.append(ft.Text("✏️ أدخل أسماء اللاعبين:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            for input_container in player_name_inputs_offline_controls:
                 offline_main_column.controls.append(input_container)
            offline_main_column.controls.append(ft.ElevatedButton("التالي: اختيار الفئة", on_click=lambda e: save_players_offline(), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            offline_main_column.controls.append(ft.ElevatedButton("🔙 رجوع للعدد", on_click=lambda e: set_offline_trivia_step("choose_player_count"), width=260, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        elif s["step"] == "choose_category":
            offline_main_column.controls.append(ft.Text("📜 اختر فئة الأسئلة", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Changed icon and size
            cat_options = [ft.dropdown.Option(key=cat_key, text=cat_key) for cat_key in trivia_categories_offline_map.keys()]
            category_dd_offline = ft.Dropdown(options=cat_options, label="الفئة", hint_text="اختر فئة", border_radius=8)
            category_dd_container = ft.Container(
                content=category_dd_offline,
                width=page.width * 0.85 if page.width else 310, # Adjusted width
                alignment=ft.alignment.center
            )
            offline_main_column.controls.append(category_dd_container)
            offline_main_column.controls.append(ft.ElevatedButton("بدء اللعبة بالفئة المختارة", on_click=lambda e: confirm_category_offline(category_dd_offline.value), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted width/height

        elif s["step"] == "question_display":
            current_player_name = s["players"][s["current_player_turn_idx"]]
            q_data = s.get("current_question_data")
            if not q_data:
                offline_main_column.controls.append(ft.Text("خطأ: لا يوجد سؤال حالي أو انتهت الأسئلة.", color=ft.Colors.RED_700, size=18, text_align=ft.TextAlign.CENTER))
                offline_main_column.controls.append(ft.ElevatedButton("النتائج النهائية", on_click=lambda e: set_offline_trivia_step("results"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
                if page.client_storage: page.update(); return

            player_q_count = s["player_question_counts"].get(current_player_name, 0)
            total_qs_for_player = s["questions_per_player"]

            offline_main_column.controls.append(ft.Text(f"❓ سؤال للاعب: {current_player_name}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER)) # Adjusted
            offline_main_column.controls.append(ft.Text(f"(سؤاله رقم {player_q_count + 1} من {total_qs_for_player})", size=15, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_GREY_700)) # Adjusted
            
            offline_main_column.controls.append(
                ft.Container(
                    content=ft.Text(q_data.get("question",""), size=22, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, selectable=True), # Adjusted
                    padding=ft.padding.symmetric(horizontal=8, vertical=5), # Adjusted
                    margin=ft.margin.symmetric(vertical=8) # Adjusted
                )
            )

            options_responsive_row = ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8, run_spacing=8 # Adjusted
            )
            shuffled_options = list(q_data.get("options",[]))
            random.shuffle(shuffled_options)
            for opt_text in shuffled_options:
                opt_button = ft.ElevatedButton(
                    text=opt_text,
                    on_click=lambda e, chosen_opt=opt_text: handle_answer_offline(chosen_opt),
                    col={"xs": 12, "sm": 6},
                    height=50, # Adjusted
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                )
                options_responsive_row.controls.append(ft.Container(content=opt_button, alignment=ft.alignment.center)) # No need for another container here, ResponsiveRow handles it.
            offline_main_column.controls.append(options_responsive_row)

        elif s["step"] == "answer_feedback":
            current_player_name = s["players"][s["current_player_turn_idx"]]
            q_data = s.get("current_question_data",{})
            offline_main_column.controls.append(ft.Text(f"سؤال اللاعب: {current_player_name}", size=18, text_align=ft.TextAlign.CENTER)) # Adjusted
            offline_main_column.controls.append(
                ft.Container(
                    content=ft.Text(q_data.get("question",""), size=20, text_align=ft.TextAlign.CENTER, selectable=True), #Adjusted
                    padding=5
                )
            )

            feedback_icon = "✅" if s.get("last_q_correct_bool") else "❌"
            feedback_color = ft.Colors.GREEN_800 if s.get("last_q_correct_bool") else ft.Colors.RED_800
            #feedback_text_val = "إجابة صحيحة!" if s.get("last_q_correct_bool") else f"إجابة خاطئة! الجواب: {s.get('last_q_correct_answer_text','')}"
            # Replace the feedback_text_val line with:
            correct_answer = s.get('last_q_correct_answer_text', '')
            if s.get("last_q_correct_bool"):
                feedback_text_val = f"إجابة صحيحة! الجواب: {correct_answer}"
            else:
                feedback_text_val = f"إجابة خاطئة! الجواب: {correct_answer}"
            offline_main_column.controls.append(ft.Text(f"{feedback_icon} {feedback_text_val}", color=feedback_color, size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted

            offline_main_column.controls.append(ft.Divider(height=8)) # Adjusted
            offline_main_column.controls.append(ft.Text("📊 النقاط الحالية:", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            scores_col = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            for p_name, p_score in s.get("scores",{}).items():
                scores_col.controls.append(ft.Text(f"• اللاعب {p_name}: {p_score} نقطة", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
            offline_main_column.controls.append(scores_col)
            offline_main_column.controls.append(ft.Container(height=8)) # Adjusted

            offline_main_column.controls.append(ft.ElevatedButton("السؤال التالي / اللاعب التالي", on_click=lambda e: proceed_to_next_question_or_player_offline(), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif s["step"] == "results":
            offline_main_column.controls.append(ft.Text("🎉 انتهت اللعبة!", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            offline_main_column.controls.append(ft.Text("🏆 النتائج النهائية:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            
            final_scores_data_trivia = []
            sorted_scores = sorted(s.get("scores",{}).items(), key=lambda x: x[1], reverse=True)
            for p_name, score_val in sorted_scores:
                final_scores_data_trivia.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(p_name, weight=ft.FontWeight.BOLD, size=16)), # Adjusted
                    ft.DataCell(ft.Text(f"{score_val} نقطة", size=16)), # Adjusted
                ]))
            
            if final_scores_data_trivia:
                offline_main_column.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("اللاعب", weight=ft.FontWeight.BOLD, size=15)), # Adjusted
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=15), numeric=True), # Adjusted
                            ],
                            rows=final_scores_data_trivia,
                            column_spacing=25, # Adjusted
                            data_row_max_height=40, # Adjusted
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.9 if page.width else 310, # Adjusted
                        alignment=ft.alignment.center
                    )
                )
            else:
                offline_main_column.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER, size=16)) # Adjusted

            buttons_results_row_trivia = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("🔁 العب مرة أخرى", on_click=lambda e: reset_offline_trivia_state(), col={"xs":12, "sm":6}, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                    # Removed "Back to Menu" as persistent home button exists. If you want it, it should call safe_go_home_offline_trivia
                    # ft.ElevatedButton("🏠 العودة للقائمة", on_click=lambda e: safe_go_home_offline_trivia(), col={"xs":12, "sm":6}, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                ],
                alignment=ft.MainAxisAlignment.CENTER, run_spacing=8, spacing=8 # Adjusted
            )
            offline_main_column.controls.append(buttons_results_row_trivia)
        else: # Fallback for unknown step
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'", size=18, color=ft.Colors.RED_700))
            # Redundant "Back to Home" button is removed as persistent one exists.

        if page.client_storage: page.update()

    def prepare_player_name_inputs_offline():
        nonlocal player_name_inputs_offline_controls
        player_name_inputs_offline_controls.clear()
        for i in range(offline_state["player_count"]):
            tf = ft.TextField(label=f"اسم اللاعب {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8)
            container = ft.Container(
                content=tf,
                width=page.width * 0.85 if page.width else 300,
                alignment=ft.alignment.center,
                padding=ft.padding.only(bottom=5) # Add a little space between textfields
            )
            player_name_inputs_offline_controls.append(container)
        set_offline_trivia_step("enter_player_names")

    def save_players_offline():
        s = offline_state
        actual_textfields = [container.content for container in player_name_inputs_offline_controls]
        names = [tf.value.strip() for tf in actual_textfields if tf.value.strip()]
        if len(names) != s["player_count"] or len(set(names)) != len(names) or any(not n for n in names):
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("أسماء اللاعبين يجب أن تكون فريدة وغير فارغة ومكتملة!"), open=True)
                page.update()
            return
        s["players"] = names
        s["scores"] = {name: 0 for name in names}
        s["player_question_counts"] = {name: 0 for name in names}
        s["max_total_questions"] = len(s["players"]) * s["questions_per_player"]
        set_offline_trivia_step("choose_category")

    def confirm_category_offline(cat_name):
        s = offline_state
        if not cat_name:
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("الرجاء اختيار فئة."), open=True)
                page.update()
            return
        s["selected_category_name"] = cat_name
        module_path_str = trivia_categories_offline_map.get(cat_name)
        all_questions = load_questions_offline(module_path_str)

        if not all_questions:
            set_offline_trivia_step("choose_category")
            return

        s["max_total_questions"] = len(s["players"]) * s["questions_per_player"]

        if len(all_questions) < s["max_total_questions"]:
            print(f"Offline Warning: Category '{cat_name}' has {len(all_questions)} questions, need {s['max_total_questions']}. Using all available. Game might be shorter.")
            s["question_pool"] = random.sample(all_questions, len(all_questions))
            s["max_total_questions"] = len(s["question_pool"])
            if s["max_total_questions"] < len(s["players"]) * s["questions_per_player"]:
                s["questions_per_player"] = s["max_total_questions"] // len(s["players"]) if len(s["players"]) > 0 else 0
                if s["questions_per_player"] == 0 and s["max_total_questions"] > 0 :
                    s["questions_per_player"] = 1
                s["max_total_questions"] = len(s["players"]) * s["questions_per_player"]
        else:
            s["question_pool"] = random.sample(all_questions, s["max_total_questions"])

        if not s["question_pool"]:
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text(f"خطأ فادح: لا توجد أسئلة متاحة بعد الفرز في '{cat_name}'. الرجاء اختيار فئة أخرى."), open=True)
                page.update()
            set_offline_trivia_step("choose_category")
            return

        s["current_question_idx_in_pool"] = 0
        s["total_questions_answered_this_game"] = 0
        s["current_player_turn_idx"] = 0
        s["player_question_counts"] = {player_name: 0 for player_name in s["players"]}
        load_next_question_offline()

    def load_next_question_offline():
        s = offline_state
        if s["total_questions_answered_this_game"] >= s["max_total_questions"]:
            set_offline_trivia_step("results")
            return

        current_player_name = s["players"][s["current_player_turn_idx"]]
        if s["player_question_counts"].get(current_player_name, 0) >= s["questions_per_player"]:
            proceed_to_next_question_or_player_offline()
            return

        if s["total_questions_answered_this_game"] < len(s["question_pool"]):
            s["current_question_data"] = s["question_pool"][s["total_questions_answered_this_game"]]
            s["answer_submitted_this_q"] = False
            s["last_q_correct_bool"] = None
            s["last_q_correct_answer_text"] = ""
            set_offline_trivia_step("question_display")
        else:
            set_offline_trivia_step("results")

    def handle_answer_offline(chosen_option):
        s = offline_state
        q_data = s["current_question_data"]
        if not q_data or s["answer_submitted_this_q"]: return
        correct_ans = q_data.get("answer")
        s["answer_submitted_this_q"] = True
        s["last_q_correct_answer_text"] = correct_ans

        current_player_name = s["players"][s["current_player_turn_idx"]]
        if chosen_option == correct_ans:
            s["last_q_correct_bool"] = True
            s["scores"][current_player_name] = s["scores"].get(current_player_name, 0) + 1
        else:
            s["last_q_correct_bool"] = False

        s["player_question_counts"][current_player_name] = s["player_question_counts"].get(current_player_name, 0) + 1
        s["total_questions_answered_this_game"] +=1
        set_offline_trivia_step("answer_feedback")

    def proceed_to_next_question_or_player_offline():
        s = offline_state
        if s["total_questions_answered_this_game"] >= s["max_total_questions"]:
            set_offline_trivia_step("results")
            return

        s["current_player_turn_idx"] = (s["current_player_turn_idx"] + 1) % len(s["players"])
        current_player_name = s["players"][s["current_player_turn_idx"]]
        start_cycle_idx = s["current_player_turn_idx"]

        while s["player_question_counts"].get(current_player_name, 0) >= s["questions_per_player"]:
            s["current_player_turn_idx"] = (s["current_player_turn_idx"] + 1) % len(s["players"])
            current_player_name = s["players"][s["current_player_turn_idx"]]
            if s["current_player_turn_idx"] == start_cycle_idx:
                set_offline_trivia_step("results")
                return
        load_next_question_offline()

    def safe_go_home_offline_trivia(e=None):
        offline_state.clear()
        player_name_inputs_offline_controls.clear()
        go_home_fn()

    reset_offline_trivia_state()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=8, vertical=10) # Adjusted padding
        )
    ]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def trivia_battle_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    # --- ONLINE UI ENHANCEMENT: page_title moved into the main content for consistency ---
    # page_title = ft.Text(f"تريفيا باتل - غرفة: {room_code}", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    status_text = ft.Text("قيد التحميل...", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Adjusted
    
    player_list_display_online_trivia = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Adjusted
    player_score_display_online_trivia = ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Adjusted
    action_area_online_trivia = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12, scroll=ft.ScrollMode.ADAPTIVE) # Adjusted
    question_display_online_trivia = ft.Column(visible=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6) # Adjusted

    online_main_content_column_trivia = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12 # Adjusted
    )

    def log_debug_online_trivia(msg):
        print(f"[Trivia_Online_Client:{current_player_name} session:{page.session_id}] {msg}")

    def update_ui_from_server_state_online_trivia(room_state_from_server):
        if not page.client_storage:
            log_debug_online_trivia("Page detached, skipping UI update.")
            return

        gs = room_state_from_server.get("game_state",{})
        players_in_room = room_state_from_server.get("players",{})
        player_scores_online = gs.get("players_scores_online", {})

        my_player_data = players_in_room.get(current_player_name,{})
        is_host = my_player_data.get("is_host", False)
        current_phase = gs.get("phase", "LOBBY")

        # log_debug_online_trivia(f"Trivia online UI update, phase: {current_phase}") # Less verbose logging
        status_text.value = gs.get("status_message", "...")
        status_text.text_align = ft.TextAlign.CENTER

        player_list_display_online_trivia.controls.clear()
        player_list_display_online_trivia.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)} / {gs.get('max_players_for_game', 6)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=16)) # Adjusted
        for p_name, p_data in players_in_room.items():
            player_list_display_online_trivia.controls.append(
                ft.Text(f"• {p_data.get('name','Unknown')} {'👑' if p_data.get('is_host') else ''}", text_align=ft.TextAlign.CENTER, size=14) # Adjusted
            )

        player_score_display_online_trivia.controls.clear()
        player_score_display_online_trivia.controls.append(ft.Text("📊 النقاط:", weight=ft.FontWeight.BOLD, size=18, text_align=ft.TextAlign.CENTER)) # Adjusted
        if player_scores_online:
            for p_name, score in player_scores_online.items():
                player_score_display_online_trivia.controls.append(ft.Text(f"{p_name}: {score}", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
        else:
            player_score_display_online_trivia.controls.append(ft.Text("لم تبدأ اللعبة بعد.", text_align=ft.TextAlign.CENTER, size=14)) # Adjusted

        action_area_online_trivia.controls.clear()
        question_display_online_trivia.controls.clear()
        question_display_online_trivia.visible = False


        if current_phase == "LOBBY":
            min_players_online = gs.get("min_players_for_game", 2)
            action_area_online_trivia.controls.append(ft.Text(f"في انتظار انضمام اللاعبين ({min_players_online}-{gs.get('max_players_for_game', 6)}).", text_align=ft.TextAlign.CENTER, size=16)) # Adjusted
            if is_host:
                online_trivia_cats_client_map = {
                    "The Office": "trivia_data.trivia_the_office",
                    "رياضة": "trivia_data.trivia_sports",
                    "جغرافيا": "trivia_data.trivia_geography",
                    "ثقافة عامة": "trivia_data.trivia_general_knowledge",
                    "موسيقى": "trivia_data.trivia_music"
                }
                cat_dd_online_trivia = ft.Dropdown(label="اختر فئة الأسئلة", options=[ft.dropdown.Option(k) for k in online_trivia_cats_client_map.keys()], border_radius=8, hint_text="اختر فئة")
                cat_dd_container_online = ft.Container(
                    content=cat_dd_online_trivia,
                    width=page.width * 0.85 if page.width else 300,
                    alignment=ft.alignment.center
                )
                action_area_online_trivia.controls.append(cat_dd_container_online)

                def host_start_trivia_game_online(e):
                    selected_cat_online = cat_dd_online_trivia.value
                    if not selected_cat_online:
                        if page.client_storage:
                            page.snack_bar = ft.SnackBar(ft.Text("الرجاء اختيار فئة للأسئلة."),open=True)
                            page.update()
                        return
                    send_action_fn("SETUP_TRIVIA_GAME_HOST", {"category": selected_cat_online})

                can_start_online = len(players_in_room) >= min_players_online
                start_button_online = ft.ElevatedButton("🚀 بدء اللعبة", on_click=host_start_trivia_game_online, disabled=not can_start_online, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))) # Adjusted
                action_area_online_trivia.controls.append(start_button_online)
                if not can_start_online:
                    action_area_online_trivia.controls.append(ft.Text(f"تحتاج إلى {min_players_online - len(players_in_room)} لاعبين إضافيين على الأقل.", color=ft.Colors.ORANGE_ACCENT_700, size=14, text_align=ft.TextAlign.CENTER)) # Adjusted color


        elif current_phase == "QUESTION_DISPLAY_ONLINE":
            question_display_online_trivia.visible = True
            current_q_online_data = gs.get("current_question_online_data", {})
            current_acting_player_online = gs.get("current_acting_player_online")
            is_my_turn_online = (current_player_name == current_acting_player_online)

            player_q_count_online = gs.get("player_question_counts_online", {}).get(current_acting_player_online, 0)
            total_qs_for_player_online = gs.get("questions_per_player", 10)

            question_display_online_trivia.controls.append(ft.Text(f"سؤال للاعب: {current_acting_player_online}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER)) # Adjusted
            question_display_online_trivia.controls.append(ft.Text(f"(سؤاله {player_q_count_online + 1} من {total_qs_for_player_online})", size=15, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_GREY_700)) # Adjusted
            
            question_display_online_trivia.controls.append(
                ft.Container(
                    content=ft.Text(current_q_online_data.get("question", "تحميل السؤال..."), size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, selectable=True), # Adjusted
                    padding=ft.padding.symmetric(horizontal=5,vertical=5), margin=ft.margin.symmetric(vertical=8) # Adjusted
                )
            )

            options_responsive_row_online = ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8, run_spacing=8 # Adjusted
            )
            q_options_online = current_q_online_data.get("options", [])
            for opt_online in q_options_online:
                btn_online = ft.ElevatedButton(
                    text=opt_online,
                    on_click= (lambda e, chosen_opt=opt_online: send_action_fn("SUBMIT_TRIVIA_ANSWER", {"answer": chosen_opt})) if is_my_turn_online else None,
                    disabled=not is_my_turn_online,
                    col={"xs": 12, "sm": 6},
                    height=50, # Adjusted
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                )
                options_responsive_row_online.controls.append(btn_online) # No need for ft.Container wrapper
            action_area_online_trivia.controls.append(options_responsive_row_online) # Add options to action_area
            if not is_my_turn_online:
                action_area_online_trivia.controls.append(ft.Text(f"انتظر دورك. الآن دور {current_acting_player_online}.", italic=True, size=15, text_align=ft.TextAlign.CENTER)) # Adjusted

        elif current_phase == "ANSWER_FEEDBACK_ONLINE":
            question_display_online_trivia.visible = True # Keep question visible during feedback
            q_data_online_feedback = gs.get("last_answered_question_data", {})
            last_actor_online = gs.get("current_acting_player_online")
            question_display_online_trivia.controls.append(ft.Text(f"السؤال كان لـ {last_actor_online}:", size=18, text_align=ft.TextAlign.CENTER)) # Adjusted
            question_display_online_trivia.controls.append(
                ft.Container(
                    content=ft.Text(q_data_online_feedback.get('question',''), size=20, text_align=ft.TextAlign.CENTER, selectable=True), #Adjusted
                    padding=5
                )
            )

            feedback_icon_online = "✅" if gs.get("last_answer_was_correct") else "❌"
            feedback_color_online = ft.Colors.GREEN_800 if gs.get("last_answer_was_correct") else ft.Colors.RED_800
            #feedback_text_val_online = "إجابة صحيحة!" if gs.get("last_answer_was_correct") else f"إجابة خاطئة! الجواب: {gs.get('correct_answer_text_for_last_q','')}"
            correct_answer_online = gs.get('correct_answer_text_for_last_q', '')
            if gs.get("last_answer_was_correct"):
                feedback_text_val_online = f"إجابة صحيحة! الجواب: {correct_answer_online}"
            else:
                feedback_text_val_online = f"إجابة خاطئة! الجواب: {correct_answer_online}"
            
            action_area_online_trivia.controls.append(ft.Text(f"{feedback_icon_online} {feedback_text_val_online}", color=feedback_color_online, size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted

            if is_host:
                action_area_online_trivia.controls.append(ft.ElevatedButton("السؤال/اللاعب التالي", on_click=lambda e: send_action_fn("NEXT_TRIVIA_QUESTION_HOST"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            else:
                action_area_online_trivia.controls.append(ft.Text("في انتظار الهوست للسؤال التالي...", size=15, text_align=ft.TextAlign.CENTER)) # Adjusted


        elif current_phase == "GAME_OVER_TRIVIA":
            action_area_online_trivia.controls.append(ft.Text("🏁 انتهت لعبة التريفيا!", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            
            final_scores_data_trivia_online = []
            if player_scores_online:
                sorted_players_online = sorted(player_scores_online.items(), key=lambda item: item[1], reverse=True)
                for p_name_iter, score_val in sorted_players_online:
                    final_scores_data_trivia_online.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(p_name_iter, weight=ft.FontWeight.BOLD, size=16)), # Adjusted
                        ft.DataCell(ft.Text(f"{score_val} نقطة", size=16)), # Adjusted
                    ]))
            
            if final_scores_data_trivia_online:
                 action_area_online_trivia.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("اللاعب", weight=ft.FontWeight.BOLD, size=15)), # Adjusted
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=15), numeric=True), # Adjusted
                            ],
                            rows=final_scores_data_trivia_online,
                            column_spacing=25, # Adjusted
                            data_row_max_height=40, # Adjusted
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.9 if page.width else 310, # Adjusted
                        alignment=ft.alignment.center
                    )
                )
            else:
                action_area_online_trivia.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted

            if is_host:
                action_area_online_trivia.controls.append(ft.ElevatedButton("🔄 جولة جديدة بنفس اللاعبين والفئة", on_click=lambda e: send_action_fn("RESTART_TRIVIA_HOST"), width=300, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            else:
                action_area_online_trivia.controls.append(ft.Text("في انتظار الهوست لبدء جولة جديدة...", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted

        if page.client_storage:
            # log_debug_online_trivia(f"EXECUTING page.update() for Trivia phase {current_phase}")
            page.update()


# trivia_battle_game.py

# ... (other parts of trivia_battle_online_logic) ...

    def on_server_message_online_trivia(*args_received):
        # current_player_name IS IN SCOPE HERE from the trivia_battle_online_logic parameters
        if not page.client_storage: return
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        
        msg_type = msg_data.get("type")

        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online_trivia(room_state)
        elif msg_type == "ACTION_ERROR":
            error_msg = msg_data.get("message", "حدث خطأ في تريفيا باتل.")
            recipient = msg_data.get("recipient") # Get the recipient from the message

            # Only show snackbar if the error is general (no recipient) 
            # OR if this client is the intended recipient of the error message.
            if not recipient or recipient == current_player_name:
                if page.client_storage:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(error_msg, text_align=ft.TextAlign.CENTER), 
                        open=True
                    )
                    page.update()
            # else:
                # Optionally log if an error message was for someone else, for debugging
                # print(f"Client: Received error for {recipient}, I am {current_player_name}. Ignoring SnackBar.")

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online_trivia)
    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        update_ui_from_server_state_online_trivia(initial_room_data)
    else:
        status_text.value = "خطأ في تحميل بيانات الغرفة."

    # Construct main online layout
    online_main_content_column_trivia.controls.extend([
        # --- ONLINE UI ENHANCEMENT: Top Bar with Title and Home Button ---
        ft.Row(
            [
                ft.Text(f"تريفيا باتل - غرفة: {room_code}", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER), # Game title
                ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=28) # Home button
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=1, thickness=0.5), # Separator
        # --- END ONLINE UI ENHANCEMENT ---
        status_text,
        ft.Divider(height=3, thickness=1), # Adjusted
        question_display_online_trivia, # This will be visible/hidden by update_ui
        ft.ResponsiveRow(
            [
                ft.Container(
                    content=ft.Column([
                        player_list_display_online_trivia,
                        ft.Divider(height=8), # Adjusted
                        player_score_display_online_trivia
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER), # Adjusted
                    padding=8, # Adjusted
                    border=ft.border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.OUTLINE)), # Adjusted
                    border_radius=8, # Adjusted
                    col={"xs": 12, "md": 4},
                    margin=ft.margin.only(bottom=10 if page.width and page.width < 768 else 0) # Adjusted
                ),
                ft.Container(
                    content=action_area_online_trivia,
                    padding=ft.padding.symmetric(horizontal=8, vertical=5), # Adjusted
                    col={"xs": 12, "md": 8},
                    alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            spacing=5, run_spacing=5
        )
    ])
    return [
        ft.Container(
            content=online_main_content_column_trivia,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=8, vertical=8) # Adjusted overall padding
        )
    ]


# --- GAME ENTRY POINT ---
def trivia_battle_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return trivia_battle_offline_logic(page, go_home_fn)
    else:
        if not all([room_code, player_name, game_rooms_ref is not None]):
             return [ft.Container(content=ft.Text("خطأ في تحميل لعبة تريفيا باتل أونلاين."), alignment=ft.alignment.center, expand=True)]

        def send_trivia_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "trivia_battle", action_type, payload or {})

        return trivia_battle_online_logic(page, go_home_fn, send_trivia_action_to_server_wrapper, room_code, player_name, game_rooms_ref)