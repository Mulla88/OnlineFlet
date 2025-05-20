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
        size=48,  # Adjusted size for compactness
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
        height=100, # Adjusted height
        expand=True
    )
    timer_text_control = ft.Text(
        "الوقت: 60",
        size=28, # Adjusted size
        color=ft.Colors.RED_ACCENT_700,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER
    )
    score_text_control = ft.Text(
        "النقاط: 0",
        size=24, # Adjusted size
        color=ft.Colors.GREEN_700,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER
    )

    # --- OFFLINE UI ENHANCEMENT: Persistent Home Button ---
    offline_title_bar_headsup = ft.Row(
        [
            ft.Text("📱 الجوال على الرأس", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=lambda e: cleanup_and_go_home_offline(), # Use existing cleanup
                icon_size=28
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    # --- END OFFLINE UI ENHANCEMENT ---

    main_content_area = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15, # Adjusted default spacing
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
            "current_round_score": 0.0,
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
        if not HEADS_UP_WORDS:
            return "لا توجد كلمات!" # Simpler message

        available_words = [w for w in HEADS_UP_WORDS if w not in shown_this_round]
        if not available_words:
            return "انتهت كلمات الجولة!" # Simpler message

        word = random.choice(available_words)
        _game_state_heads_up.setdefault("words_shown_this_round_unique", set()).add(word)
        return word

    def _log_word_action(word, status):
        if word and not (word.startswith("انتهت كلمات") or word.startswith("لا توجد كلمات")):
            _game_state_heads_up.setdefault("current_round_word_log", []).append({"word": word, "status": status})

    def _display_new_active_word():
        if not _game_state_heads_up.get("is_playing_round"): return

        new_word = get_new_word_for_round()
        _game_state_heads_up["current_active_word"] = new_word
        word_text_control.value = new_word
        word_text_control.weight = ft.FontWeight.BOLD

        if new_word.startswith("انتهت كلمات") or new_word.startswith("لا توجد كلمات"):
             word_text_control.color = ft.Colors.RED_700
             word_text_control.size = 28 # Adjusted
        else:
             word_text_control.color = ft.Colors.BLACK
             word_text_control.size = 48 # Back to game word size, was 55

        if page.client_storage:
            word_text_control.update()

    def handle_correct_guess(e=None):
        if not _game_state_heads_up.get("is_playing_round"): return
        current_word = _game_state_heads_up.get("current_active_word", "")
        if current_word.startswith("انتهت كلمات") or current_word.startswith("لا توجد كلمات"): return

        _log_word_action(current_word, "correct")
        _game_state_heads_up["current_round_score"] += 1.0
        score_text_control.value = f"النقاط: {float(_game_state_heads_up['current_round_score']):.1f}"
        if page.client_storage: score_text_control.update()
        _display_new_active_word()

    def handle_skip_action(e=None):
        if not _game_state_heads_up.get("is_playing_round"): return
        current_word = _game_state_heads_up.get("current_active_word", "")
        if current_word and not (current_word.startswith("انتهت كلمات") or current_word.startswith("لا توجد كلمات")):
            _log_word_action(current_word, "skipped")
            _game_state_heads_up["current_round_score"] -= 0.5
            score_text_control.value = f"النقاط: {float(_game_state_heads_up['current_round_score']):.1f}"
            if page.client_storage: score_text_control.update()
        _display_new_active_word()

    def handle_round_end(e=None):
        if _game_state_heads_up.get("is_playing_round"):
            _game_state_heads_up["stop_timer_event"].set()
            _game_state_heads_up["is_playing_round"] = False

            current_word_at_end = _game_state_heads_up.get("current_active_word", "")
            last_logged_entry = _game_state_heads_up.get("current_round_word_log", [])[-1] if _game_state_heads_up.get("current_round_word_log") else None
            if current_word_at_end and not (current_word_at_end.startswith("انتهت كلمات") or current_word_at_end.startswith("لا توجد كلمات")):
                if not last_logged_entry or last_logged_entry["word"] != current_word_at_end:
                     _log_word_action(current_word_at_end, "skipped_at_timeout")

            player_name = _game_state_heads_up["players_names_list"][_game_state_heads_up["current_player_index"]]
            current_total_score = _game_state_heads_up.get("all_player_scores", {}).get(player_name, 0.0)
            _game_state_heads_up["all_player_scores"][player_name] = current_total_score + _game_state_heads_up["current_round_score"]
            set_current_page_step("round_summary")

    def start_timer_for_round():
        _game_state_heads_up["stop_timer_event"].clear()
        duration = _game_state_heads_up.get("round_duration", 60)
        timer_text_control.value = f"الوقت: {duration}"
        if page.client_storage: timer_text_control.update()

        def timer_thread_run():
            for i in range(duration, -1, -1):
                if not page.client_storage or _game_state_heads_up.get("stop_timer_event", threading.Event()).is_set():
                    return
                timer_text_control.value = f"⏳الوقت: {i}"
                if page.client_storage: timer_text_control.update()
                if i == 0:
                    if not _game_state_heads_up.get("stop_timer_event", threading.Event()).is_set():
                        if page.client_storage: page.run_thread_safe(lambda: handle_round_end(None)) # run_thread_safe is good here
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

    name_inputs_offline_list = []

    def update_main_ui():
        if not page.client_storage or not _game_state_heads_up: return

        main_content_area.controls.clear()
        main_content_area.controls.append(offline_title_bar_headsup)
        main_content_area.controls.append(ft.Divider(height=1, thickness=0.5))
        current_step = _game_state_heads_up.get("current_page_step", "select_num_players")

        main_content_area.vertical_alignment = ft.MainAxisAlignment.CENTER
        main_content_area.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        main_content_area.spacing = 20 # Adjusted general spacing

        if current_step == "select_num_players":
            # Title is in offline_title_bar_headsup
            main_content_area.controls.extend([
                ft.Text("عدد اللاعبين (2-10):", size=20, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.ResponsiveRow(
                    [
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e: update_num_players_offline(-1), col={"xs": 4}, icon_size=28), # Adjusted
                        ft.Text(str(_game_state_heads_up["num_players"]), size=30, weight=ft.FontWeight.BOLD, col={"xs": 4}, text_align=ft.TextAlign.CENTER), # Adjusted
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e: update_num_players_offline(1), col={"xs": 4}, icon_size=28), # Adjusted
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5 # Adjusted
                ),
                ft.ElevatedButton("التالي", on_click=lambda e: set_current_page_step("input_player_names"), width=260, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                # Redundant home button removed
            ])
        elif current_step == "input_player_names":
            main_content_area.controls.append(ft.Text("✏️ أدخل أسماء اللاعبين:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            name_inputs_offline_list.clear()
            for i in range(_game_state_heads_up["num_players"]):
                tf = ft.TextField(label=f"اسم اللاعب {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8, height=45, text_size=14) # Adjusted
                name_inputs_offline_list.append(tf)
                main_content_area.controls.append(
                    ft.Container(content=tf, width=page.width * 0.85 if page.width else 280, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3)) # Adjusted
                )

            def save_player_names_and_proceed(e):
                names = [tf.value.strip() for tf in name_inputs_offline_list if tf.value.strip()]
                if len(names) != _game_state_heads_up["num_players"] or len(set(names)) != len(names) or any(not n for n in names):
                    if page.client_storage:
                        page.snack_bar = ft.SnackBar(ft.Text("❗ الأسماء فريدة، غير فارغة، ومكتملة."), open=True) # Compacted
                        page.update()
                    return
                _game_state_heads_up["players_names_list"] = names
                _game_state_heads_up["all_player_scores"] = {name: 0.0 for name in names}
                _game_state_heads_up["current_player_index"] = 0
                set_current_page_step("handoff_to_next_player")
            main_content_area.controls.append(ft.ElevatedButton("تأكيد وبدء", on_click=save_player_names_and_proceed, width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            main_content_area.controls.append(ft.ElevatedButton("🔙 رجوع للعدد", on_click=lambda e: set_current_page_step("select_num_players"), width=260, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif current_step == "handoff_to_next_player":
            player_name = _game_state_heads_up["players_names_list"][_game_state_heads_up["current_player_index"]]
            main_content_area.controls.extend([
                ft.Text(f"📱 أعطِ الجوال إلى:", size=26, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text(player_name, size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_700), # Adjusted
                ft.Text("ضع الجوال أفقياً على الرأس!", size=18, color=ft.Colors.ORANGE_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500), # Adjusted
                ft.Text("عند الجاهزية، اضغط 'ابدأ'", size=16, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.ElevatedButton("🚀 ابدأ الجولة", on_click=lambda e: start_player_round(), width=280, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))) # Adjusted
            ])

        elif current_step == "playing_round_active":
            main_content_area.vertical_alignment = ft.MainAxisAlignment.SPACE_EVENLY # Changed for better vertical spread
            main_content_area.spacing = 10 # Reduced spacing for this specific screen
            main_content_area.controls.extend([
                timer_text_control,
                ft.Container(
                    content=word_text_control,
                    padding=ft.padding.symmetric(horizontal=5), # Reduced padding
                    alignment=ft.alignment.center,
                    # Ink for swipe detection - this assumes the container takes up significant screen space
                    ink=True, 
                    on_click=handle_correct_guess, # Tap for correct
                    # For swipe, you might need a GestureDetector in more complex Flet versions or alternative input.
                    # Flet's direct swipe on Container might be limited.
                    # This is a conceptual placeholder for swipe.
                    # If page.on_swipe is available and works for your Flet version, that's better.
                    # Otherwise, buttons are the reliable input.
                    # For now, relying on buttons.
                ),
                score_text_control,
                ft.ResponsiveRow(
                    [
                        ft.ElevatedButton("✅ صحيح", on_click=handle_correct_guess, col={"xs": 6}, height=70, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                        ft.ElevatedButton("⏭️ تخطي", on_click=handle_skip_action, col={"xs": 6}, height=70, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))) # Adjusted
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15 # Adjusted
                ),
                ft.ElevatedButton("⏹️ إنهاء الجولة", on_click=lambda e: handle_round_end(None), width=280, height=45, bgcolor=ft.Colors.AMBER_300, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))) # Adjusted
            ])

        elif current_step == "round_summary":
            player_name_idx = _game_state_heads_up.get("current_player_index", 0)
            if player_name_idx >= len(_game_state_heads_up.get("players_names_list",[])):
                set_current_page_step("final_results")
                return

            player_name = _game_state_heads_up["players_names_list"][player_name_idx]
            round_score = _game_state_heads_up.get("current_round_score", 0.0)
            total_score = _game_state_heads_up.get("all_player_scores", {}).get(player_name, 0.0)

            word_log_column = ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=3, # Adjusted
                height=180, # Adjusted
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            word_log_column.controls.append(ft.Text("كلمات الجولة:", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=16)) # Adjusted

            round_words = _game_state_heads_up.get("current_round_word_log", [])
            if not round_words:
                word_log_column.controls.append(ft.Text("لم يتم لعب كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=14)) # Adjusted
            else:
                for item in round_words:
                    status_symbol = "✅" if item["status"] == "correct" else ("⏭️" if item["status"] == "skipped" else "⏳")
                    color = ft.Colors.GREEN_800 if item["status"] == "correct" else (ft.Colors.RED_800 if item["status"] == "skipped" else ft.Colors.ORANGE_800)
                    word_log_column.controls.append(ft.Text(f"{status_symbol} {item['word']}", color=color, text_align=ft.TextAlign.CENTER, size=14)) # Adjusted

            main_content_area.controls.extend([
                ft.Text(f"⏰ انتهى دور: {player_name}", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text(f"نقاط الجولة: {float(round_score):.1f}", size=22, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text(f"إجمالي نقاط {player_name}: {float(total_score):.1f}", size=18, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_GREY_700), # Adjusted
                ft.Divider(height=10, thickness=1), # Adjusted
                ft.Container(
                    content=word_log_column,
                    border=ft.border.all(1, ft.Colors.BLACK26),
                    border_radius=8,
                    padding=8, # Adjusted
                    width=page.width * 0.9 if page.width else 300, # Adjusted
                    alignment=ft.alignment.top_center
                ),
                ft.Divider(height=10, thickness=1), # Adjusted
                ft.ElevatedButton("▶ التالي", on_click=lambda e: proceed_from_summary(), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))) # Adjusted
            ])

        elif current_step == "final_results":
            main_content_area.controls.append(ft.Text("🏁 انتهت اللعبة!", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            main_content_area.controls.append(ft.Text("📊 النتائج النهائية:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted

            sorted_scores = sorted(_game_state_heads_up.get("all_player_scores", {}).items(), key=lambda x: x[1], reverse=True)
            
            score_table_rows = []
            for name, final_score in sorted_scores:
                score_table_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(name, weight=ft.FontWeight.BOLD, size=18)), # Adjusted
                        ft.DataCell(ft.Text(f"{float(final_score):.1f} نقطة", size=18)), # Adjusted
                    ])
                )
            if score_table_rows:
                main_content_area.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("اللاعب", weight=ft.FontWeight.BOLD, size=16)), # Adjusted
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=16), numeric=True), # Adjusted
                            ],
                            rows=score_table_rows,
                            column_spacing=25, # Adjusted
                            data_row_max_height=40, # Adjusted
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.9 if page.width else 330, # Adjusted
                        alignment=ft.alignment.center
                    )
                )
            else:
                main_content_area.controls.append(ft.Text("لا توجد نتائج.", text_align=ft.TextAlign.CENTER, size=16)) # Adjusted

            main_content_area.controls.append(
                ft.ResponsiveRow(
                    [
                        ft.ElevatedButton("🔁 العب مرة أخرى", on_click=lambda e: restart_full_game(), col={"xs": 12}, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Single full-width button
                        # Redundant home button removed
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    run_spacing=8, # Adjusted
                    spacing=8 # Adjusted
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
            alignment=ft.alignment.top_center, # Changed to top_center
            padding=ft.padding.symmetric(horizontal=8, vertical=10) # Adjusted padding
        )
    ]


# --- GAME ENTRY POINT (Called by app.py) ---
def heads_up_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    # Heads Up is offline only
    if is_online:
        # --- ONLINE UI ENHANCEMENT: Consistent Top Bar for "Not Available" screen ---
        online_not_available_title_bar = ft.Row(
            [
                ft.Text("📱 الجوال على الرأس", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
                ft.IconButton(
                    ft.Icons.HOME_ROUNDED,
                    tooltip="العودة للقائمة الرئيسية",
                    on_click=lambda e: go_home_fn(),
                    icon_size=28
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return [
            ft.Container(
                content=ft.Column([
                    online_not_available_title_bar,
                    ft.Divider(height=1, thickness=0.5),
                    ft.Container(height=20), # Spacer
                    ft.Text("لعبة 'الجوال على الرأس' متاحة فقط في وضع الأوفلاين حالياً.", size=18, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD), # Adjusted
                    ft.Container(height=20),
                    # Redundant "Back to Menu" button removed as persistent home button exists
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                # vertical_alignment=ft.MainAxisAlignment.CENTER, # Removed to allow top bar
                expand=True,
                spacing=15 # Adjusted
                ),
                expand=True,
                alignment=ft.alignment.top_center, # Align to top
                padding=10 # Adjusted
            )
        ]
    else:
        return heads_up_game_offline_logic(page, go_home_fn)