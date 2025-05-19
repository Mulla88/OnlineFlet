# heads_up_game.py
import flet as ft
import random
import threading
import time
from heads_up_words import HEADS_UP_WORDS

_game_state_heads_up = {}

def heads_up_game_offline_logic(page: ft.Page, go_home_fn):
    # --- UI Controls (defined once, values updated) ---
    word_text_control = ft.Text(
        "",
        size=55,  # Increased size
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
        height=120, # Increased height for potentially longer words / better centering
        expand=True # Allow it to take available width in its container
    )
    timer_text_control = ft.Text(
        "الوقت: 60",
        size=34, # Increased size
        color=ft.Colors.RED_ACCENT_700,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER
    )
    score_text_control = ft.Text(
        "النقاط: 0",
        size=28, # Increased size
        color=ft.Colors.GREEN_700,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER
    )

    # Main content area - padding will be applied by the ft.Container it's placed in
    main_content_area = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20, # Increased default spacing
    )
    # --- End UI Controls ---

    def initialize_game_state():
        _game_state_heads_up.clear()
        _game_state_heads_up.update({
            "num_players": 2,
            "players_names_list": [],
            "current_player_index": 0,
            "is_playing_round": False,
            "words_shown_this_round_unique": set(),
            "current_round_word_log": [],
            "current_round_score": 0.0, # Use float for scores
            "all_player_scores": {},
            "current_active_word": "",
            "current_page_step": "select_num_players",
            "stop_timer_event": threading.Event(),
            "round_duration": 60,
        })
        update_main_ui()

    def cleanup_and_go_home_offline(e=None):
        if "stop_timer_event" in _game_state_heads_up:
            _game_state_heads_up["stop_timer_event"].set()
            time.sleep(0.1)
        _game_state_heads_up.clear()
        go_home_fn()

    def get_new_word_for_round():
        shown_this_round = _game_state_heads_up.get("words_shown_this_round_unique", set())
        # Ensure HEADS_UP_WORDS is not empty before proceeding
        if not HEADS_UP_WORDS:
            return "لا توجد كلمات في القائمة!"

        available_words = [w for w in HEADS_UP_WORDS if w not in shown_this_round]

        if not available_words:
            # Optionally reset if all words in the bank have been shown in this session (across all rounds for all players)
            # For now, just indicating round-specific completion.
            # If you want a global reset, that logic would be more complex.
            return "انتهت الكلمات الفريدة لهذه الجولة!" # Or reset used_words and pick again

        word = random.choice(available_words)
        _game_state_heads_up.setdefault("words_shown_this_round_unique", set()).add(word)
        return word

    def _log_word_action(word, status):
        if word and not word.startswith("انتهت الكلمات"):
            _game_state_heads_up.setdefault("current_round_word_log", []).append({"word": word, "status": status})

    def _display_new_active_word():
        if not _game_state_heads_up.get("is_playing_round"): return

        new_word = get_new_word_for_round()
        _game_state_heads_up["current_active_word"] = new_word
        word_text_control.value = new_word
        word_text_control.weight = ft.FontWeight.BOLD # Ensure it's bold

        if new_word.startswith("انتهت الكلمات"):
             word_text_control.color = ft.Colors.RED_700
             word_text_control.size = 30 # Smaller if it's a message
        else:
             word_text_control.color = ft.Colors.BLACK # Default color
             word_text_control.size = 55 # Back to game word size

        if page.client_storage:
            word_text_control.update()

    def handle_correct_guess(e=None):
        if not _game_state_heads_up.get("is_playing_round"): return

        current_word = _game_state_heads_up.get("current_active_word", "")
        if current_word.startswith("انتهت الكلمات"): return

        _log_word_action(current_word, "correct")
        _game_state_heads_up["current_round_score"] += 1.0
        score_text_control.value = f"النقاط: {float(_game_state_heads_up['current_round_score']):.1f}" # Format to one decimal
        if page.client_storage: score_text_control.update()

        _display_new_active_word()

    def handle_skip_action(e=None):
        if not _game_state_heads_up.get("is_playing_round"): return

        current_word = _game_state_heads_up.get("current_active_word", "")
        if current_word and not current_word.startswith("انتهت الكلمات"):
            _log_word_action(current_word, "skipped")
            _game_state_heads_up["current_round_score"] -= 0.5
            score_text_control.value = f"النقاط: {float(_game_state_heads_up['current_round_score']):.1f}" # Format to one decimal
            if page.client_storage: score_text_control.update()

        _display_new_active_word()

    def handle_round_end(e=None):
        if _game_state_heads_up.get("is_playing_round"):
            _game_state_heads_up["stop_timer_event"].set()
            _game_state_heads_up["is_playing_round"] = False

            current_word_at_end = _game_state_heads_up.get("current_active_word", "")
            last_logged_entry = _game_state_heads_up.get("current_round_word_log", [])[-1] if _game_state_heads_up.get("current_round_word_log") else None
            if current_word_at_end and not current_word_at_end.startswith("انتهت الكلمات"):
                if not last_logged_entry or last_logged_entry["word"] != current_word_at_end:
                     _log_word_action(current_word_at_end, "skipped_at_timeout") # Differentiate if needed

            player_name = _game_state_heads_up["players_names_list"][_game_state_heads_up["current_player_index"]]
            current_total_score = _game_state_heads_up.get("all_player_scores", {}).get(player_name, 0.0)
            _game_state_heads_up["all_player_scores"][player_name] = current_total_score + _game_state_heads_up["current_round_score"]

            set_current_page_step("round_summary")

    def start_timer_for_round():
        _game_state_heads_up["stop_timer_event"].clear()
        duration = _game_state_heads_up.get("round_duration", 60)
        timer_text_control.value = f"الوقت: {duration}" # Initial display
        if page.client_storage: timer_text_control.update()

        def timer_thread_run():
            for i in range(duration, -1, -1):
                if not page.client_storage or _game_state_heads_up.get("stop_timer_event", threading.Event()).is_set():
                    return

                timer_text_control.value = f"⏳الوقت: {i}" # Add emoji
                if page.client_storage: timer_text_control.update()

                if i == 0:
                    if not _game_state_heads_up.get("stop_timer_event", threading.Event()).is_set():
                        if page.client_storage: page.run_thread_safe(lambda: handle_round_end(None))
                    return
                time.sleep(1)

        threading.Thread(target=timer_thread_run, daemon=True).start()

    def start_player_round():
        _game_state_heads_up["is_playing_round"] = True
        _game_state_heads_up["current_page_step"] = "playing_round_active"
        _game_state_heads_up["current_round_score"] = 0.0
        _game_state_heads_up["words_shown_this_round_unique"] = set()
        _game_state_heads_up["current_round_word_log"] = []

        score_text_control.value = "النقاط: 0.0"
        word_text_control.color = ft.Colors.BLACK

        update_main_ui()
        _display_new_active_word()
        start_timer_for_round()

    def proceed_from_summary():
        _game_state_heads_up["current_player_index"] += 1
        if _game_state_heads_up["current_player_index"] >= len(_game_state_heads_up["players_names_list"]):
            set_current_page_step("final_results")
        else:
            set_current_page_step("handoff_to_next_player")

    def restart_full_game():
        initialize_game_state()

    def set_current_page_step(step_name):
        _game_state_heads_up["current_page_step"] = step_name
        update_main_ui()

    name_inputs_offline_list = [] # To store TextField instances

    def update_main_ui():
        if not page.client_storage or not _game_state_heads_up: return

        main_content_area.controls.clear()
        current_step = _game_state_heads_up.get("current_page_step", "select_num_players")

        main_content_area.vertical_alignment = ft.MainAxisAlignment.CENTER
        main_content_area.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        main_content_area.spacing = 25 # Increased general spacing

        if current_step == "select_num_players":
            main_content_area.controls.extend([
                ft.Text("📱 الجوال على الرأس", size=36, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Larger title
                ft.Text("عدد اللاعبين (2-10):", size=22, text_align=ft.TextAlign.CENTER), # Clarify range
                ft.ResponsiveRow(
                    [
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e: update_num_players_offline(-1), col={"xs": 4}, icon_size=30),
                        ft.Text(str(_game_state_heads_up["num_players"]), size=32, weight=ft.FontWeight.BOLD, col={"xs": 4}, text_align=ft.TextAlign.CENTER),
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e: update_num_players_offline(1), col={"xs": 4}, icon_size=30),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.ElevatedButton("التالي", on_click=lambda e: set_current_page_step("input_player_names"), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                ft.ElevatedButton("🏠 العودة للقائمة", on_click=cleanup_and_go_home_offline, width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])
        elif current_step == "input_player_names":
            main_content_area.controls.append(ft.Text("✏️ أدخل أسماء اللاعبين:", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            name_inputs_offline_list.clear()
            for i in range(_game_state_heads_up["num_players"]):
                tf = ft.TextField(label=f"اسم اللاعب {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8)
                name_inputs_offline_list.append(tf)
                main_content_area.controls.append(
                    ft.Container(content=tf, width=page.width * 0.85 if page.width else 300, alignment=ft.alignment.center)
                )

            def save_player_names_and_proceed(e):
                names = [tf.value.strip() for tf in name_inputs_offline_list if tf.value.strip()]
                if len(names) != _game_state_heads_up["num_players"] or len(set(names)) != len(names) or any(not n for n in names):
                    page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء اللاعبين يجب أن تكون فريدة وغير فارغة ومكتملة."), open=True)
                    if page.client_storage: page.update()
                    return
                _game_state_heads_up["players_names_list"] = names
                _game_state_heads_up["all_player_scores"] = {name: 0.0 for name in names}
                _game_state_heads_up["current_player_index"] = 0
                set_current_page_step("handoff_to_next_player")
            main_content_area.controls.append(ft.ElevatedButton("تأكيد وبدء اللعبة", on_click=save_player_names_and_proceed, width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            main_content_area.controls.append(ft.ElevatedButton("🔙 رجوع لاختيار العدد", on_click=lambda e: set_current_page_step("select_num_players"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        elif current_step == "handoff_to_next_player":
            player_name = _game_state_heads_up["players_names_list"][_game_state_heads_up["current_player_index"]]
            main_content_area.controls.extend([
                ft.Text(f"📱 أعطِ الجوال إلى:", size=28, text_align=ft.TextAlign.CENTER),
                ft.Text(player_name, size=34, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_700),
                ft.Text("تأكد من وضع الجوال بشكل أفقي على الرأس قبل البدء!", size=20, color=ft.Colors.ORANGE_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500),
                ft.Text("عندما تكون جاهزاً، اضغط 'ابدأ الجولة'", size=18, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("🚀 ابدأ الجولة", on_click=lambda e: start_player_round(), width=300, height=65, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif current_step == "playing_round_active":
            main_content_area.alignment = ft.MainAxisAlignment.SPACE_AROUND # More space
            main_content_area.controls.extend([
                timer_text_control,
                ft.Container( # Container for word for better control if needed
                    content=word_text_control,
                    padding=ft.padding.symmetric(horizontal=10),
                    alignment=ft.alignment.center
                ),
                score_text_control,
                ft.ResponsiveRow(
                    [
                        ft.ElevatedButton("✅ صحيح", on_click=handle_correct_guess, col={"xs": 6}, height=80, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                        ft.ElevatedButton("⏭️ تخطي", on_click=handle_skip_action, col={"xs": 6}, height=80, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, # Center the row of buttons
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20
                ),
                ft.ElevatedButton("⏹️ إنهاء الجولة مبكراً", on_click=lambda e: handle_round_end(None), width=300, height=50, bgcolor=ft.Colors.AMBER_400, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif current_step == "round_summary":
            player_name_idx = _game_state_heads_up.get("current_player_index", 0)
            if player_name_idx >= len(_game_state_heads_up.get("players_names_list",[])): # Safety check
                print("Error: Invalid player index in round_summary.")
                set_current_page_step("final_results") # Or go home
                return

            player_name = _game_state_heads_up["players_names_list"][player_name_idx]
            round_score = _game_state_heads_up.get("current_round_score", 0.0)
            total_score = _game_state_heads_up.get("all_player_scores", {}).get(player_name, 0.0)

            word_log_column = ft.Column( # Changed name for clarity
                scroll=ft.ScrollMode.AUTO,
                spacing=5,
                height=200, # Increased height for scroll
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            word_log_column.controls.append(ft.Text("الكلمات في هذه الجولة:", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=18))

            round_words = _game_state_heads_up.get("current_round_word_log", [])
            if not round_words:
                word_log_column.controls.append(ft.Text("لم يتم لعب كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=16))
            else:
                for item in round_words:
                    status_symbol = "✅" if item["status"] == "correct" else ("⏭️" if item["status"] == "skipped" else "⏳")
                    color = ft.Colors.GREEN_800 if item["status"] == "correct" else (ft.Colors.RED_800 if item["status"] == "skipped" else ft.Colors.ORANGE_800)
                    word_log_column.controls.append(ft.Text(f"{status_symbol} {item['word']}", color=color, text_align=ft.TextAlign.CENTER, size=16))

            main_content_area.controls.extend([
                ft.Text(f"⏰ انتهى دور اللاعب: {player_name}", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text(f"النقاط في هذه الجولة: {float(round_score):.1f}", size=24, text_align=ft.TextAlign.CENTER),
                ft.Text(f"إجمالي نقاط {player_name}: {float(total_score):.1f}", size=20, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_GREY_700),
                ft.Divider(height=15, thickness=1),
                ft.Container( # Container for scrollable word log
                    content=word_log_column,
                    border=ft.border.all(1, ft.Colors.BLACK26),
                    border_radius=8,
                    padding=10,
                    width=page.width * 0.9 if page.width else 320,
                    alignment=ft.alignment.top_center
                ),
                ft.Divider(height=15, thickness=1),
                ft.ElevatedButton("▶ اللاعب التالي / عرض النتائج", on_click=lambda e: proceed_from_summary(), width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif current_step == "final_results":
            main_content_area.controls.append(ft.Text("🏁 انتهت اللعبة!", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            main_content_area.controls.append(ft.Text("📊 النتائج النهائية:", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))

            sorted_scores = sorted(_game_state_heads_up.get("all_player_scores", {}).items(), key=lambda x: x[1], reverse=True)
            
            score_table_rows = []
            for name, final_score in sorted_scores:
                score_table_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(name, weight=ft.FontWeight.BOLD, size=20)),
                        ft.DataCell(ft.Text(f"{float(final_score):.1f} نقطة", size=20)),
                    ])
                )
            if score_table_rows:
                main_content_area.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("اللاعب", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD), numeric=True),
                            ],
                            rows=score_table_rows,
                            column_spacing=30,
                            data_row_max_height=45,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.9 if page.width else 350,
                        alignment=ft.alignment.center
                    )
                )
            else:
                main_content_area.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER))

            main_content_area.controls.append(
                ft.ResponsiveRow(
                    [
                        ft.ElevatedButton("🔁 العب مرة أخرى", on_click=lambda e: restart_full_game(), col={"xs": 12, "sm": 6}, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                        ft.ElevatedButton("🏠 القائمة الرئيسية", on_click=cleanup_and_go_home_offline, col={"xs": 12, "sm": 6}, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    run_spacing=10, # Spacing if they wrap
                    spacing=10
                )
            )

        if page.client_storage: page.update()

    def update_num_players_offline(delta):
        current_num = _game_state_heads_up.get("num_players", 2)
        _game_state_heads_up["num_players"] = max(2, min(10, current_num + delta))
        update_main_ui()

    initialize_game_state()

    return [
        ft.Container(
            content=main_content_area,
            expand=True,
            alignment=ft.alignment.center, # Center the main column in the view
            padding=ft.padding.symmetric(horizontal=10, vertical=20) # Add overall padding
        )
    ]


# --- GAME ENTRY POINT (Called by app.py) ---
def heads_up_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    # Heads Up is offline only
    if is_online:
        return [
            ft.Container(
                content=ft.Column([
                    ft.Text("لعبة 'الجوال على الرأس' متاحة فقط في وضع الأوفلاين حالياً.", size=20, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD),
                    ft.Container(height=20), # Spacer
                    ft.ElevatedButton("🔙 العودة للقائمة", on_click=lambda e: go_home_fn(), width=250, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
                spacing=20
                ),
                expand=True,
                alignment=ft.alignment.center,
                padding=20
            )
        ]
    else:
        return heads_up_game_offline_logic(page, go_home_fn)