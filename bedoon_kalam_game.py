# bedoon_kalam_game.py
import flet as ft
import random
import threading
import time
from bedoon_kalam_words import WORD_BANK

# --- Sizing Constants (Copied from taboo_game.py for consistency) ---
FONT_SIZE_NORMAL = 14
FONT_SIZE_MEDIUM = 16
FONT_SIZE_LARGE = 18
FONT_SIZE_XLARGE = 20
FONT_SIZE_TITLE = 22
FONT_SIZE_SECTION_TITLE = 20
FONT_SIZE_SECRET_WORD = 30 # For Bedoon Kalam, this is the word to act
FONT_SIZE_FORBIDDEN = 16 # Not used in Bedoon Kalam, but kept for constant set
BUTTON_HEIGHT_NORMAL = 40
BUTTON_HEIGHT_LARGE = 50
BUTTON_HEIGHT_SMALL = 30
CONTAINER_PADDING_NORMAL = ft.padding.symmetric(horizontal=5, vertical=3)
INPUT_HEIGHT = 45
STANDARD_BORDER_RADIUS = 8
STANDARD_ICON_SIZE = 22
TITLE_ICON_SIZE = 26


# --- OFFLINE MODE LOGIC --- (Apply sizing constants)
def bedoon_kalam_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {}
    team_name_fields_offline = []

    word_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=5 # Use constants or reduced values
    )
    score_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=3
    )
    timer_text_control_offline = ft.Text("الوقت: 90 ثانية", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700)

    offline_title_bar_bedoonkalam = ft.Row(
        [
            ft.Text("🤫 بدون كلام (أوفلاين)", size=FONT_SIZE_TITLE, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=lambda e: safe_go_home_offline(),
                icon_size=TITLE_ICON_SIZE
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    offline_main_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8
    )

    def destroy_offline_game_state():
        event = offline_state.get("stop_timer_event")
        if isinstance(event, threading.Event):
            event.set()
            time.sleep(0.1)
        offline_state.clear()
        team_name_fields_offline.clear()

    def reset_offline_state_and_ui():
        destroy_offline_game_state()
        offline_state.update({
            "teams": [], "scores": {}, "current_team_index": 0, "used_words": set(),
            "word_log": [], "current_word": None, "game_started": False,
            "round": 1, "step": "input_teams",
            "stop_timer_event": threading.Event(),
            "max_rounds": 3, "round_duration": 90, # Bedoon Kalam specific
            "current_round_summary_team": None,
            "current_round_summary_words": []
        })
        update_offline_ui()

    def get_new_word_offline():
        remaining = [w for w in WORD_BANK if w not in offline_state.get("used_words", set())]
        if not remaining:
            offline_state["used_words"] = set()
            remaining = list(WORD_BANK) # Ensure it's a new list
            if not remaining:
                if page.client_storage:
                    page.snack_bar = ft.SnackBar(ft.Text("لا توجد كلمات في القائمة!"), open=True)
                    page.update()
                return "انتهت الكلمات!"
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("تم إعادة تعيين الكلمات المستخدمة."), open=True)
                page.update()
        word = random.choice(remaining)
        offline_state.setdefault("used_words", set()).add(word)
        return word

    def _get_word_display_content_offline():
        controls = []
        word = offline_state.get("current_word")
        if word and word != "انتهت الكلمات!":
            controls.append(ft.Text(f"الكلمة: {word}", size=FONT_SIZE_SECRET_WORD, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER))
        elif word: # "انتهت الكلمات!"
            controls.append(ft.Text(word, size=FONT_SIZE_XLARGE, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER))
        return controls

    def _get_score_display_content_offline():
        controls = []
        if offline_state.get("scores"):
            controls.append(ft.Text("📊 النقاط:", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            for team, score in offline_state.get("scores",{}).items():
                controls.append(ft.Text(f"فريق {team}: {float(score):.1f} نقطة", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))
        return controls

    def handle_end_round_offline(e=None): # Can be called by timer or button
        if "stop_timer_event" in offline_state:
            offline_state["stop_timer_event"].set()

        if not offline_state.get("teams") or offline_state.get("current_team_index", -1) < 0:
            set_offline_step("input_teams") # Graceful fallback
            return

        current_team_name = offline_state["teams"][offline_state["current_team_index"]]
        round_words_summary = [
            log for log in offline_state.get("word_log", [])
            if log.get("team") == current_team_name and log.get("round") == offline_state.get("round")
        ]
        # offline_state["step"] = "round_summary" # set_offline_step will call update_offline_ui
        offline_state["current_round_summary_team"] = current_team_name
        offline_state["current_round_summary_words"] = round_words_summary
        set_offline_step("round_summary") # This calls update_offline_ui


    def start_timer_offline():
        if "stop_timer_event" not in offline_state: return
        stop_event = offline_state["stop_timer_event"]
        stop_event.clear()
        round_duration = offline_state.get("round_duration", 90)
        timer_text_control_offline.value = f"⏳ الوقت المتبقي: {round_duration} ثانية"
        if page.client_storage: timer_text_control_offline.update()

        def run_timer():
            current_time = round_duration
            while current_time >= 0:
                if not page.client_storage or stop_event.is_set():
                    return
                timer_text_control_offline.value = f"⏳ الوقت المتبقي: {current_time} ثانية"
                if page.client_storage: timer_text_control_offline.update()
                if current_time == 0:
                    if not stop_event.is_set() and page.client_storage:
                        # Ensure UI updates from timer thread are handled safely by Flet
                        page.run_thread(lambda: handle_end_round_offline(None))
                    return
                time.sleep(1)
                if stop_event.is_set(): return # Check again after sleep
                current_time -=1
        threading.Thread(target=run_timer, daemon=True).start()


    def show_team_intro_offline():
        set_offline_step("team_intro") # Use set_offline_step for consistency

    def start_round_logic_offline():
        offline_state["current_word"] = get_new_word_offline()
        set_offline_step("playing_round") # This will call update_offline_ui
        if offline_state["current_word"] != "انتهت الكلمات!":
            start_timer_offline()
        # else: message already shown by _get_word_display_content_offline

    def handle_correct_offline(e):
        s = offline_state
        if not s.get("teams") or not s.get("current_word") or s.get("current_word") == "انتهت الكلمات!": return
        team = s["teams"][s["current_team_index"]]
        s["scores"][team] = s["scores"].get(team, 0.0) + 2.0
        s.setdefault("word_log",[]).append({"team": team, "word": s["current_word"], "correct": True, "round": s["round"]})
        new_word = get_new_word_offline()
        s["current_word"] = new_word
        if s["step"] == "playing_round": update_offline_ui() # Just update, don't change step
        if new_word == "انتهت الكلمات!" and page.client_storage and not s.get("stop_timer_event", threading.Event()).is_set():
            handle_end_round_offline()


    def handle_skip_offline(e):
        s = offline_state
        if not s.get("teams") or not s.get("current_word") or s.get("current_word") == "انتهت الكلمات!": return
        team = s["teams"][s["current_team_index"]]
        s["scores"][team] = s["scores"].get(team, 0.0) - 0.5
        s.setdefault("word_log",[]).append({"team": team, "word": s["current_word"], "correct": False, "round": s["round"]})
        new_word = get_new_word_offline()
        s["current_word"] = new_word
        if s["step"] == "playing_round": update_offline_ui()
        if new_word == "انتهت الكلمات!" and page.client_storage and not s.get("stop_timer_event", threading.Event()).is_set():
            handle_end_round_offline()

    def start_game_setup_offline(e):
        team_names = [tf.value.strip() for tf in team_name_fields_offline if tf.value.strip()]
        if len(team_names) != 2:
            if page.client_storage: page.snack_bar = ft.SnackBar(ft.Text("❗ تحتاج لفريقين بالضبط لهذه اللعبة."), open=True); page.update()
            return
        if any(not name for name in team_names):
            if page.client_storage: page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء الفرق يجب ألا تكون فارغة."), open=True); page.update()
            return
        if len(set(team_names)) != len(team_names):
            if page.client_storage: page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء الفرق يجب أن تكون فريدة."), open=True); page.update()
            return

        offline_state["teams"] = team_names
        offline_state["scores"] = {team: 0.0 for team in team_names}
        offline_state["game_started"] = True
        offline_state["round"] = 1
        offline_state["current_team_index"] = 0
        offline_state["used_words"] = set()
        offline_state["word_log"] = []
        show_team_intro_offline()

    def update_offline_ui():
        if not page.client_storage: return
        offline_main_column.controls.clear()
        offline_main_column.controls.append(offline_title_bar_bedoonkalam)
        offline_main_column.controls.append(ft.Divider(height=1, thickness=0.5))
        s = offline_state

        if s["step"] == "input_teams":
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء الفرق (فريقان):", size=FONT_SIZE_TITLE, text_align=ft.TextAlign.CENTER))
            team_name_fields_offline.clear()
            for i in range(2):
                tf = ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER, border_radius=STANDARD_BORDER_RADIUS, height=INPUT_HEIGHT)
                team_name_fields_offline.append(tf)
                offline_main_column.controls.append(
                     ft.Container(content=tf, width=page.width * 0.85 if page.width else 280, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3))
                )
            offline_main_column.controls.append(ft.ElevatedButton("🚀 بدء اللعبة", on_click=start_game_setup_offline, width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))

        elif s["step"] == "team_intro":
            if not s.get("teams") or s.get("current_team_index", -1) >= len(s["teams"]) or s.get("current_team_index", -1) < 0:
                set_offline_step("input_teams")
                return
            current_team = s["teams"][s["current_team_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"استعد يا فريق", size=FONT_SIZE_XLARGE, text_align=ft.TextAlign.CENTER),
                ft.Text(f"{current_team}", size=FONT_SIZE_XLARGE + 4, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_ACCENT_700),
                ft.Text(f"أحدكم سيمثل الكلمات.", size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(f"🚀 ابدأ الجولة {s['round']} لفريق {current_team}",
                                 on_click=lambda e: start_round_logic_offline(), width=300, height=BUTTON_HEIGHT_LARGE,
                                 style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS)))
            ])

        elif s["step"] == "playing_round":
            current_team = s["teams"][s["current_team_index"]]
            word_display_offline_container.controls = _get_word_display_content_offline()
            word_display_offline_container.visible = True
            score_display_offline_container.controls = _get_score_display_content_offline()
            score_display_offline_container.visible = True
            is_last_round = (s["round"] == s["max_rounds"]) # Check if it's the absolute last round
            # More precise: last round and last team playing in that round
            is_truly_last_turn = is_last_round and (s["current_team_index"] == len(s.get("teams",[]))-1)

            last_round_text_ui = ft.Text("⚠️ هذا هو الدور الأخير في اللعبة!", size=FONT_SIZE_MEDIUM, color=ft.Colors.RED_700, visible=is_truly_last_turn, weight=ft.FontWeight.BOLD)

            button_row_offline = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("✅ صح", on_click=handle_correct_offline, col={"xs": 6}, height=BUTTON_HEIGHT_LARGE, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
                    ft.ElevatedButton("⏭ تخطي", on_click=handle_skip_offline, col={"xs": 6}, height=BUTTON_HEIGHT_LARGE, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS)))
                ],
                alignment=ft.MainAxisAlignment.CENTER, spacing=10
            )
            offline_main_column.controls.extend([
                ft.Text(f"🎮 الجولة {s['round']} - فريق: {current_team}", size=FONT_SIZE_XLARGE, color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD),
                last_round_text_ui,
                timer_text_control_offline,
                ft.Divider(height=5, thickness=1),
                word_display_offline_container,
                ft.Divider(height=5, thickness=1),
                button_row_offline,
                ft.Container(height=5),
                ft.ElevatedButton("⏹ إنهاء الدور مبكراً", on_click=handle_end_round_offline, width=260, height=BUTTON_HEIGHT_SMALL, bgcolor=ft.Colors.AMBER_300, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
                ft.Divider(height=8, thickness=1),
                score_display_offline_container
            ])

        elif s["step"] == "round_summary":
            summary_team = s.get("current_round_summary_team", "فريق")
            summary_words = s.get("current_round_summary_words", [])
            word_list_display_column = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=3, height=130, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            if not summary_words:
                word_list_display_column.controls.append(ft.Text("لم يتم لعب كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=FONT_SIZE_NORMAL))
            else:
                for log_item in summary_words:
                    word_list_display_column.controls.append(
                        ft.Text(f"- {log_item['word']} ({'✔ صح' if log_item['correct'] else '✘ تخطي'})",
                                  color=ft.Colors.GREEN_800 if log_item["correct"] else ft.Colors.RED_800,
                                  size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER)
                    )
            summary_container = ft.Container(
                content=word_list_display_column,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=STANDARD_BORDER_RADIUS,
                padding=8,
                width=page.width * 0.9 if page.width else 310,
                alignment=ft.alignment.top_center
            )

            def proceed_to_next_team_or_end_offline(e):
                s["current_team_index"] += 1
                if s["current_team_index"] >= len(s["teams"]):
                    s["current_team_index"] = 0
                    s["round"] += 1
                if s["round"] > s["max_rounds"]:
                    set_offline_step("game_over")
                else:
                    show_team_intro_offline()

            offline_main_column.controls.extend([
                ft.Text(f"⏰ انتهى وقت فريق: {summary_team}", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER),
                ft.Text("🔤 كلمات الدور:", size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER),
                summary_container,
                ft.Container(height=8),
                ft.ElevatedButton("▶ الفريق/الجولة التالية", on_click=proceed_to_next_team_or_end_offline, width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
            ])

        elif s["step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة!", size=FONT_SIZE_XLARGE + 2, weight="bold", text_align=ft.TextAlign.CENTER))
            final_scores_data = []
            for team, score in sorted(s.get("scores",{}).items(), key=lambda item: item[1], reverse=True):
                final_scores_data.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(team, weight=ft.FontWeight.BOLD, size=FONT_SIZE_MEDIUM)),
                    ft.DataCell(ft.Text(f"{float(score):.1f}", size=FONT_SIZE_MEDIUM)),
                ]))
            
            if final_scores_data:
                offline_main_column.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL)),
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL), numeric=True),
                            ],
                            rows=final_scores_data,
                            column_spacing=25,
                            data_row_max_height=40,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.85 if page.width else 300,
                        alignment=ft.alignment.center
                    )
                )
            else:
                offline_main_column.controls.append(ft.Text("لا توجد نتائج.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))

            offline_main_column.controls.extend([
                ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: reset_offline_state_and_ui(), width=260, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
            ])
        else:
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'", size=FONT_SIZE_LARGE, color=ft.Colors.RED_700))

        if page.client_storage: page.update()

    def set_offline_step(step_name):
        offline_state["step"] = step_name
        update_offline_ui()

    def safe_go_home_offline(e=None):
        destroy_offline_game_state()
        go_home_fn()

    reset_offline_state_and_ui()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=5, vertical=5)
        )
    ]

# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def bedoon_kalam_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    status_text = ft.Text("...", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    player_list_display_online = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    team_score_display_online = ft.Column(spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    action_area_online = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6, scroll=ft.ScrollMode.ADAPTIVE)
    word_to_act_display_online = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6)
    online_timer_display = ft.Text("الوقت: --", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700)

    # --- Controls for Host LOBBY UI (New Approach, similar to Taboo) ---
    bk_team_name_input_fields_online = [
        ft.TextField(label="اسم الفريق 1", text_align=ft.TextAlign.CENTER, border_radius=STANDARD_BORDER_RADIUS, height=INPUT_HEIGHT),
        ft.TextField(label="اسم الفريق 2", text_align=ft.TextAlign.CENTER, border_radius=STANDARD_BORDER_RADIUS, height=INPUT_HEIGHT)
    ]
    bk_player_assignment_dropdowns_online = {}
    bk_player_assignment_column_container_online = ft.Container(
        content=ft.Column(visible=False, spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.ADAPTIVE),
        padding=ft.padding.only(top=5, bottom=5)
    )
    bk_confirm_manual_assignment_button_online = ft.ElevatedButton(
        "✔️ تأكيد التخصيص والبدء", visible=False,
        on_click=lambda e: _handle_start_game_online_bk(manual_assignment=True), # Defined in update_ui
        width=280, height=BUTTON_HEIGHT_LARGE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))
    )
    # --- End Controls for Host LOBBY UI ---

    _initial_ui_build_done_bk = False # Specific flag for this game mode

    online_main_content_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6
    )

    def log_debug_online_bk(msg): # Renamed log function
        print(f"[BedoonKalam_Online_Client:{current_player_name} session:{page.session_id}] {msg}")


    def _handle_start_game_online_bk(manual_assignment=False): # Renamed handler
        if not page.client_storage: return

        team_names = [tf.value.strip() for tf in bk_team_name_input_fields_online if tf.value.strip()]
        if len(team_names) != 2: # Bedoon Kalam needs exactly 2 teams for this setup
            page.snack_bar = ft.SnackBar(ft.Text("تحتاج لإدخال اسمي الفريقين بالضبط."), open=True); page.update()
            return
        if any(not name for name in team_names):
            page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب ألا تكون فارغة."), open=True); page.update()
            return
        if len(set(team_names)) != len(team_names):
            page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب أن تكون فريدة."), open=True); page.update()
            return

        payload_to_send = {"team_names": team_names}
        # Get fresh player list directly from game_rooms_ref before sending
        current_room_data = game_rooms_ref.get(room_code, {})
        current_players_in_room = current_room_data.get("players", {})
        current_players_in_room_keys = list(current_players_in_room.keys())


        if manual_assignment:
            payload_to_send["assignment_mode"] = "manual"
            assignments = {}
            team1_player_count = 0
            team2_player_count = 0

            for p_name_key in current_players_in_room_keys:
                dd_widget = bk_player_assignment_dropdowns_online.get(p_name_key)
                if not dd_widget or not dd_widget.value:
                    page.snack_bar = ft.SnackBar(ft.Text(f"الرجاء تخصيص فريق للاعب {p_name_key}."), open=True); page.update()
                    return
                assignments[p_name_key] = dd_widget.value
                if dd_widget.value == team_names[0]: team1_player_count +=1
                elif dd_widget.value == team_names[1]: team2_player_count +=1
            
            min_players_per_team = 1 # Each team needs at least one player
            if len(current_players_in_room_keys) < 2 : # Need at least 2 players total for 2 teams
                 page.snack_bar = ft.SnackBar(ft.Text("تحتاج للاعبين اثنين على الأقل للعب في فريقين."), open=True); page.update()
                 return
            if team1_player_count < min_players_per_team or team2_player_count < min_players_per_team:
                page.snack_bar = ft.SnackBar(ft.Text("كل فريق يجب أن يحتوي على لاعب واحد على الأقل."), open=True); page.update()
                return
            payload_to_send["assignments"] = assignments
        else: # Random assignment
            payload_to_send["assignment_mode"] = "random"
            if len(current_players_in_room_keys) < 2: # Minimum 2 players for 2 teams
                page.snack_bar = ft.SnackBar(ft.Text("تحتاج للاعبين اثنين على الأقل للتوزيع العشوائي على فريقين."), open=True); page.update()
                return
        
        send_action_fn("SETUP_TEAMS_AND_START_GAME", payload_to_send) # Action name from bedoon_kalam_actions.py


    def update_ui_from_server_state_online_bk(room_state_from_server): # Renamed
        nonlocal _initial_ui_build_done_bk # Use the correct flag
        if not page.client_storage:
            log_debug_online_bk("Page detached, skipping UI update.")
            return

        gs = room_state_from_server.get("game_state",{})
        players_in_room = room_state_from_server.get("players",{})
        teams_data = gs.get("teams", {}) # 'teams' is used in bedoon_kalam_actions.py
        current_player_data = players_in_room.get(current_player_name, {})
        is_host = current_player_data.get("is_host", False)
        my_team = current_player_data.get("team_name")
        current_phase = gs.get("phase", "LOBBY")

        status_text.value = gs.get("status_message", "...")

        player_list_display_online.controls.clear()
        player_list_display_online.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
        for p_name_iter, p_data_iter in players_in_room.items():
            team_tag = f" (فريق {p_data_iter.get('team_name', '؟')})" if p_data_iter.get('team_name') else ""
            player_list_display_online.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}{team_tag}", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_NORMAL)
            )

        team_score_display_online.controls.clear()
        team_score_display_online.controls.append(ft.Text("📊 النقاط:", weight=ft.FontWeight.BOLD, size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER))
        if teams_data:
            for team_name_iter, team_info in teams_data.items():
                team_score_display_online.controls.append(ft.Text(f"فريق {team_name_iter}: {float(team_info.get('score',0.0)):.1f}", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))
        else:
            team_score_display_online.controls.append(ft.Text("لم يتم تحديد الفرق.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_NORMAL))

        action_area_online.controls.clear()
        word_to_act_display_online.visible = False
        word_to_act_display_online.controls.clear()

        timer_val = gs.get('timer_value', '--')
        online_timer_display.value = f"⏳ الوقت: {timer_val}" if gs.get("round_active") else "الوقت: --"
        online_timer_display.visible = gs.get("round_active", False)

        if current_phase == "LOBBY":
            action_area_online.controls.append(ft.Text("الهوست يحدد الفرق ويبدأ اللعبة.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            if is_host:
                for tf_host_lobby in bk_team_name_input_fields_online: # Use BK specific fields
                    action_area_online.controls.append(
                        ft.Container(content=tf_host_lobby, width=page.width * 0.75 if page.width and page.width > 400 else 290, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3))
                    )
                
                start_random_button_bk = ft.ElevatedButton(
                    "🎲 بدء بتوزيع عشوائي",
                    on_click=lambda e: _handle_start_game_online_bk(manual_assignment=False),
                    width=280, height=BUTTON_HEIGHT_LARGE,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))
                )
                
                def _show_manual_assignment_ui_bk(e): # Renamed
                    if not page.client_storage: return
                    t1_name = bk_team_name_input_fields_online[0].value.strip()
                    t2_name = bk_team_name_input_fields_online[1].value.strip()

                    if not t1_name or not t2_name:
                        page.snack_bar = ft.SnackBar(ft.Text("الرجاء إدخال اسمي الفريقين أولاً."), open=True); page.update()
                        return
                    if t1_name == t2_name:
                        page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب أن تكون مختلفة."), open=True); page.update()
                        return

                    inner_column = bk_player_assignment_column_container_online.content
                    inner_column.controls.clear()
                    bk_player_assignment_dropdowns_online.clear()
                    team_options = [ft.dropdown.Option(t1_name), ft.dropdown.Option(t2_name)]
                    
                    # Get fresh player list for dropdowns
                    current_room_data_local = game_rooms_ref.get(room_code, {}) 
                    current_players_in_room_local = current_room_data_local.get("players", {})

                    for p_name_iter in current_players_in_room_local.keys():
                        dd = ft.Dropdown(
                            hint_text=f"فريق لـ {p_name_iter}",
                            options=list(team_options), 
                            data=p_name_iter, 
                            border_radius=STANDARD_BORDER_RADIUS,
                            content_padding=ft.padding.symmetric(horizontal=8, vertical=5),
                            text_size=FONT_SIZE_NORMAL -1,
                            dense=True
                        )
                        bk_player_assignment_dropdowns_online[p_name_iter] = dd # Use BK specific dict
                        inner_column.controls.append(
                            ft.Container(
                                content=ft.Row(
                                    [ft.Text(f"{p_name_iter}:", expand=1, text_align=ft.TextAlign.START, weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL-1),
                                     ft.Container(content=dd, expand=2)],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
                                ),
                                width=page.width * 0.75 if page.width and page.width > 400 else 290,
                                alignment=ft.alignment.center, padding=ft.padding.only(bottom=2)
                            )
                        )
                    inner_column.visible = True
                    bk_confirm_manual_assignment_button_online.visible = True # Use BK specific button
                    if page.client_storage:
                        bk_player_assignment_column_container_online.update()
                        bk_confirm_manual_assignment_button_online.update()
                        start_random_button_bk.visible = False; start_random_button_bk.update()
                        e.control.visible = False; e.control.update() # Hide the "start manual" button

                start_manual_button_bk = ft.ElevatedButton(
                    "✍️ بدء بتخصيص يدوي",
                    on_click=_show_manual_assignment_ui_bk,
                    width=280, height=BUTTON_HEIGHT_LARGE,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))
                )
                
                action_area_online.controls.append(start_random_button_bk)
                action_area_online.controls.append(start_manual_button_bk)
                action_area_online.controls.append(bk_player_assignment_column_container_online)
                action_area_online.controls.append(bk_confirm_manual_assignment_button_online)
                
                bk_confirm_manual_assignment_button_online.on_click=lambda e_confirm: _handle_start_game_online_bk(manual_assignment=True)


        elif current_phase == "TEAMS_SET": # Matches action file
            action_area_online.controls.append(ft.Text("تم تحديد الفرق!", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            if teams_data:
                for team_name_iter, team_info in teams_data.items():
                    player_names_in_team = ", ".join(team_info.get("players", []))
                    action_area_online.controls.append(ft.Text(f"فريق {team_name_iter}: {player_names_in_team}", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("▶️ بدء الدور الأول", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN"), width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))
            else:
                action_area_online.controls.append(ft.Text("انتظار الهوست لبدء الدور...", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))


        elif current_phase == "TEAM_INTRO":
            acting_team = gs.get("current_acting_team")
            current_actor = gs.get("current_actor_name")
            my_team = current_player_data.get("team_name") # Ensure fresh
            if my_team == acting_team:
                action_area_online.controls.append(ft.Text(f"استعد يا فريق {acting_team}!", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
                if current_player_name == current_actor:
                    action_area_online.controls.append(ft.Text("أنت ستمثل هذه الجولة!", size=FONT_SIZE_LARGE, color=ft.Colors.GREEN_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
                    action_area_online.controls.append(ft.ElevatedButton("👀 عرض الكلمة والبدء", on_click=lambda e: send_action_fn("ACTOR_READY_START_ROUND"), width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))
                else:
                    action_area_online.controls.append(ft.Text(f"{current_actor} سيمثل. استعدوا!", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))
            else:
                action_area_online.controls.append(ft.Text(f"جولة فريق {acting_team}. {current_actor} سيمثل.", size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ACTING_ROUND":
            word_to_act_display_online.visible = True
            acting_team = gs.get("current_acting_team")
            current_actor = gs.get("current_actor_name")
            current_word = gs.get("current_word_to_act", "---")
            my_team = current_player_data.get("team_name") # Ensure fresh
            
            # Check for last turn of the game
            is_last_round_of_game = (gs.get("current_game_round") == gs.get("max_game_rounds", 3))
            is_last_team_in_current_round = (gs.get("current_team_turn_idx") == len(teams_data.keys()) -1) if teams_data else False
            is_truly_last_turn_online = is_last_round_of_game and is_last_team_in_current_round


            if current_player_name == current_actor:
                word_to_act_display_online.controls.append(ft.Text("مثل الكلمة:", size=FONT_SIZE_SECTION_TITLE, text_align=ft.TextAlign.CENTER))
                word_to_act_display_online.controls.append(ft.Text(current_word, size=FONT_SIZE_SECRET_WORD, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT_700, text_align=ft.TextAlign.CENTER))
                action_area_online.controls.append(
                     ft.Text(f"ج {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=FONT_SIZE_MEDIUM, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER)
                )
                if is_truly_last_turn_online:
                     action_area_online.controls.append(ft.Text("⚠️ الدور الأخير في اللعبة!", size=FONT_SIZE_MEDIUM, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))

                actor_button_row = ft.ResponsiveRow(
                    [
                        ft.ElevatedButton("✅ صح", on_click=lambda e: send_action_fn("WORD_GUESSED_CORRECT"), col={"xs": 6}, height=BUTTON_HEIGHT_LARGE, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
                        ft.ElevatedButton("⏭ تخطي", on_click=lambda e: send_action_fn("SKIP_WORD"), col={"xs": 6}, height=BUTTON_HEIGHT_LARGE, bgcolor=ft.Colors.ORANGE_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=10
                )
                action_area_online.controls.append(actor_button_row)
            elif my_team == acting_team:
                word_to_act_display_online.controls.append(ft.Text(f"فريقك يمثل! خمن ما يمثله {current_actor}.", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))
                word_to_act_display_online.controls.append(ft.Text("الكلمة: ؟؟؟؟؟", size=FONT_SIZE_SECRET_WORD -2, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_300, text_align=ft.TextAlign.CENTER))
                action_area_online.controls.append(
                     ft.Text(f"ج {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=FONT_SIZE_MEDIUM, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER)
                )
                if is_truly_last_turn_online:
                     action_area_online.controls.append(ft.Text("⚠️ الدور الأخير في اللعبة!", size=FONT_SIZE_MEDIUM, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))

            else: # Spectator
                word_to_act_display_online.controls.append(ft.Text(f"فريق {acting_team} يمثل. ({current_actor})", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))
                word_to_act_display_online.controls.append(ft.Text(f"الكلمة: {current_word}", size=FONT_SIZE_XLARGE, weight="bold", color=ft.Colors.DEEP_ORANGE_ACCENT_400, text_align=ft.TextAlign.CENTER))
                action_area_online.controls.append(
                     ft.Text(f"ج {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=FONT_SIZE_MEDIUM, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER)
                )
                if is_truly_last_turn_online:
                     action_area_online.controls.append(ft.Text("⚠️ الدور الأخير في اللعبة!", size=FONT_SIZE_MEDIUM, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
                action_area_online.controls.append(ft.Text("لا يمكنك التخمين.", size=FONT_SIZE_NORMAL, italic=True, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ROUND_SUMMARY":
            summary_data = gs.get("summary_for_ui", {})
            summary_team = summary_data.get("team_name", "فريق")
            summary_round_num = summary_data.get("round_number", gs.get("current_game_round","?"))
            summary_words = summary_data.get("words", [])

            word_list_display_column_online = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=3, height=130, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            if not summary_words:
                word_list_display_column_online.controls.append(ft.Text("لم يتم لعب كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=FONT_SIZE_NORMAL))
            else:
                for log_item_online in summary_words:
                    word_list_display_column_online.controls.append(
                        ft.Text(f"- {log_item_online['word']} ({'✔ تم' if log_item_online['correct'] else '✘ تخطي'})",
                                  color=ft.Colors.GREEN_800 if log_item_online["correct"] else ft.Colors.RED_800,
                                  size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER)
                    )
            summary_container_online = ft.Container(
                content=word_list_display_column_online,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=STANDARD_BORDER_RADIUS,
                padding=8,
                width=page.width * 0.9 if page.width else 310,
                alignment=ft.alignment.top_center
            )
            action_area_online.controls.extend([
                ft.Text(f"⏰ ملخص دور فريق: {summary_team} (ج {summary_round_num})", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER),
                ft.Text("🔤 الكلمات:", size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER),
                summary_container_online,
                ft.Container(height=8)
            ])
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("▶ الدور التالي", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN"), width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))
            else:
                action_area_online.controls.append(ft.Text("انتظار الهوست...", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))

        elif current_phase == "GAME_OVER":
            action_area_online.controls.append(ft.Text("🏁 انتهت اللعبة!", size=FONT_SIZE_XLARGE + 2, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            if teams_data:
                sorted_teams = sorted(teams_data.items(), key=lambda item: item[1].get('score',0.0), reverse=True)
                final_scores_table_rows = []
                for team_name_iter, team_info_iter_go in sorted_teams:
                    final_scores_table_rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(team_name_iter, weight=ft.FontWeight.BOLD, size=FONT_SIZE_MEDIUM)),
                        ft.DataCell(ft.Text(f"{float(team_info_iter_go.get('score',0.0)):.1f}", size=FONT_SIZE_MEDIUM)),
                    ]))
                if final_scores_table_rows:
                    action_area_online.controls.append(
                        ft.Container(
                            content=ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL)),
                                    ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL), numeric=True),
                                ],
                                rows=final_scores_table_rows,
                                column_spacing=25,
                                data_row_max_height=40,
                                horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                            ),
                            width=page.width * 0.85 if page.width else 300,
                            alignment=ft.alignment.center
                        )
                    )
                else:
                    action_area_online.controls.append(ft.Text("لا توجد نتائج.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: send_action_fn("RESTART_GAME_SAME_TEAMS"), width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))

        if page.client_storage:
            page.update()
        _initial_ui_build_done_bk = True


    def on_server_message_online_bk(*args_received): # Renamed
        if not page.client_storage: return
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online_bk(room_state) # Call correct update function
        elif msg_type == "ACTION_ERROR":
            error_msg = msg_data.get("message", "حدث خطأ ما.")
            if page.client_storage:
                 page.snack_bar = ft.SnackBar(ft.Text(error_msg, text_align=ft.TextAlign.CENTER), open=True)
                 page.update()

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online_bk) # Use renamed handler

    online_main_content_column.controls.extend([
        ft.Row(
            [
                ft.Text(f"🤫 بدون كلام - غرفة: {room_code}", size=FONT_SIZE_TITLE, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
                ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=TITLE_ICON_SIZE)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=1, thickness=0.5),
        status_text,
        online_timer_display,
        ft.Divider(height=3, thickness=1),
        word_to_act_display_online,
        ft.ResponsiveRow(
            [
                ft.Container(
                    content=ft.Column([
                        player_list_display_online,
                        ft.Divider(height=8),
                        team_score_display_online
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=8,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.OUTLINE)),
                    border_radius=STANDARD_BORDER_RADIUS,
                    col={"xs": 12, "md": 4},
                    margin=ft.margin.only(bottom=8 if page.width and page.width < 768 else 0, top=5)
                ),
                ft.Container(
                    content=action_area_online,
                    padding=CONTAINER_PADDING_NORMAL,
                    col={"xs": 12, "md": 8},
                    alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            spacing=3, run_spacing=3
        )
    ])
    
    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        update_ui_from_server_state_online_bk(initial_room_data) # Call correct update function
    else:
        status_text.value = "خطأ في الاتصال بالغرفة."
        if page.client_storage: status_text.update()


    return [
        ft.Container(
            content=online_main_content_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=5, vertical=5)
        )
    ]

# --- GAME ENTRY POINT ---
def bedoon_kalam_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return bedoon_kalam_offline_logic(page, go_home_fn)
    else:
        if not room_code or not player_name or game_rooms_ref is None:
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة للعب أونلاين."), alignment=ft.alignment.center, expand=True)]

        def send_bedoon_kalam_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "bedoon_kalam", action_type, payload or {})

        return bedoon_kalam_online_logic(page, go_home_fn, send_bedoon_kalam_action_to_server_wrapper, room_code, player_name, game_rooms_ref)