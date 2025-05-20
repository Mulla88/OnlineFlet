# bedoon_kalam_game.py
import flet as ft
import random
import threading
import time
from bedoon_kalam_words import WORD_BANK

# --- OFFLINE MODE LOGIC ---
def bedoon_kalam_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {}
    team_name_fields_offline = []

    word_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8 # Adjusted spacing
    )
    score_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4 # Adjusted spacing
    )
    timer_text_control_offline = ft.Text("الوقت: 90 ثانية", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700) # Adjusted

    # --- OFFLINE UI ENHANCEMENT: Persistent Home Button ---
    offline_title_bar_bedoonkalam = ft.Row(
        [
            ft.Text("🤫 بدون كلام (أوفلاين)", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=lambda e: safe_go_home_offline(),
                icon_size=28
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
        spacing=12 # Adjusted spacing
    )

    def destroy_offline_game_state():
        event = offline_state.get("stop_timer_event")
        if isinstance(event, threading.Event):
            event.set()
            time.sleep(0.1)
        offline_state.clear()
        team_name_fields_offline.clear() # Clear the textfield list as well

    def reset_offline_state_and_ui():
        destroy_offline_game_state()
        offline_state.update({
            "teams": [], "scores": {}, "current_team_index": 0, "used_words": set(),
            "word_log": [], "current_word": None, "game_started": False,
            "round": 1, "step": "input_teams",
            "stop_timer_event": threading.Event(),
            "max_rounds": 3, "round_duration": 90,
            "current_round_summary_team": None,
            "current_round_summary_words": []
        })
        update_offline_ui()

    def get_new_word_offline():
        remaining = [w for w in WORD_BANK if w not in offline_state.get("used_words", set())]
        if not remaining:
            offline_state["used_words"] = set()
            remaining = list(WORD_BANK)
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
            controls.append(ft.Text(f"الكلمة: {word}", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER)) # Adjusted
        elif word:
            controls.append(ft.Text(word, size=24, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER)) # Adjusted
        return controls

    def _get_score_display_content_offline():
        controls = []
        if offline_state.get("scores"):
            controls.append(ft.Text("📊 النقاط:", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            for team, score in offline_state.get("scores",{}).items():
                controls.append(ft.Text(f"فريق {team}: {float(score):.1f} نقطة", size=18, text_align=ft.TextAlign.CENTER)) # Adjusted, added float formatting
        return controls

    def handle_end_round_offline(e=None):
        if "stop_timer_event" in offline_state:
            offline_state["stop_timer_event"].set()

        if not offline_state.get("teams") or offline_state.get("current_team_index", -1) < 0:
            set_offline_step("input_teams")
            return

        current_team_name = offline_state["teams"][offline_state["current_team_index"]]
        round_words_summary = [
            log for log in offline_state.get("word_log", [])
            if log.get("team") == current_team_name and log.get("round") == offline_state.get("round")
        ]
        offline_state["step"] = "round_summary"
        offline_state["current_round_summary_team"] = current_team_name
        offline_state["current_round_summary_words"] = round_words_summary
        update_offline_ui()

    def start_timer_offline():
        if "stop_timer_event" not in offline_state: return
        stop_event = offline_state["stop_timer_event"]
        stop_event.clear()
        round_duration = offline_state.get("round_duration", 90)
        timer_text_control_offline.value = f"⏳ الوقت المتبقي: {round_duration} ثانية"
        if page.client_storage: timer_text_control_offline.update()

        def run_timer():
            for i in range(round_duration, -1, -1):
                if not page.client_storage or stop_event.is_set(): # Check page.client_storage directly
                    return
                timer_text_control_offline.value = f"⏳ الوقت المتبقي: {i} ثانية"
                if page.client_storage: timer_text_control_offline.update()
                if i == 0:
                    if not stop_event.is_set() and page.client_storage:
                        # Use page.run_thread_safe if available and needed,
                        # otherwise direct call if Flet handles it (newer versions might)
                        page.run_thread_safe(lambda: handle_end_round_offline(None))
                    return
                time.sleep(1)
        threading.Thread(target=run_timer, daemon=True).start()

    def show_team_intro_offline():
        offline_state["step"] = "team_intro"
        update_offline_ui()

    def start_round_logic_offline():
        offline_state["step"] = "playing_round"
        offline_state["current_word"] = get_new_word_offline()
        update_offline_ui() # Update UI before starting timer to show word
        if offline_state["current_word"] != "انتهت الكلمات!":
            start_timer_offline()


    def handle_correct_offline(e):
        s = offline_state
        if not s.get("teams") or s.get("current_word", "").startswith("انتهت الكلمات"): return
        team = s["teams"][s["current_team_index"]]
        s["scores"][team] = s["scores"].get(team, 0.0) + 2.0 # Ensure float
        s.setdefault("word_log",[]).append({"team": team, "word": s["current_word"], "correct": True, "round": s["round"]})
        new_word = get_new_word_offline()
        s["current_word"] = new_word
        if s["step"] == "playing_round": update_offline_ui()
        if new_word == "انتهت الكلمات!" and page.client_storage and not s["stop_timer_event"].is_set():
            handle_end_round_offline()

    def handle_skip_offline(e):
        s = offline_state
        if not s.get("teams") or s.get("current_word", "").startswith("انتهت الكلمات"): return
        team = s["teams"][s["current_team_index"]]
        s["scores"][team] = s["scores"].get(team, 0.0) - 0.5 # Ensure float
        s.setdefault("word_log",[]).append({"team": team, "word": s["current_word"], "correct": False, "round": s["round"]})
        new_word = get_new_word_offline()
        s["current_word"] = new_word
        if s["step"] == "playing_round": update_offline_ui()
        if new_word == "انتهت الكلمات!" and page.client_storage and not s["stop_timer_event"].is_set():
            handle_end_round_offline()

    def start_game_setup_offline(e):
        team_names = [tf.value.strip() for tf in team_name_fields_offline if tf.value.strip()]
        if len(team_names) != 2: # Bedoon Kalam is strictly 2 teams for this offline version
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("❗ تحتاج لفريقين بالضبط لهذه اللعبة."), open=True)
                page.update()
            return
        if any(not name for name in team_names):
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء الفرق يجب ألا تكون فارغة."), open=True)
                page.update()
            return
        if len(set(team_names)) != len(team_names):
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء الفرق يجب أن تكون فريدة."), open=True)
                page.update()
            return

        offline_state["teams"] = team_names
        offline_state["scores"] = {team: 0.0 for team in team_names} # Initialize scores as float
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
            # Title is in offline_title_bar_bedoonkalam
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء الفرق (فريقان):", size=20, text_align=ft.TextAlign.CENTER)) # Adjusted
            team_name_fields_offline.clear()
            for i in range(2):
                tf = ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8, height=45, text_size=14) # Adjusted
                team_name_fields_offline.append(tf)
                offline_main_column.controls.append(
                     ft.Container(content=tf, width=page.width * 0.85 if page.width else 280, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3)) # Adjusted
                )
            offline_main_column.controls.append(ft.ElevatedButton("🚀 بدء اللعبة", on_click=start_game_setup_offline, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            # Redundant home button removed

        elif s["step"] == "team_intro":
            if not s.get("teams") or s.get("current_team_index", -1) >= len(s["teams"]):
                set_offline_step("input_teams")
                return
            current_team = s["teams"][s["current_team_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"استعد يا فريق", size=24, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text(f"{current_team}", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_ACCENT_700), # Adjusted
                ft.Text(f"أحدكم سيمثل الكلمات.", size=18, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.ElevatedButton(f"🚀 ابدأ الجولة {s['round']} لفريق {current_team}",
                                 on_click=lambda e: start_round_logic_offline(), width=300, height=55, # Adjusted
                                 style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif s["step"] == "playing_round":
            current_team = s["teams"][s["current_team_index"]]
            word_display_offline_container.controls = _get_word_display_content_offline()
            word_display_offline_container.visible = True
            score_display_offline_container.controls = _get_score_display_content_offline()
            score_display_offline_container.visible = True
            is_last_round = (s["round"] == s["max_rounds"])
            last_round_text_ui = ft.Text("⚠️ هذا هو الدور الأخير!", size=18, color=ft.Colors.RED_700, visible=is_last_round, weight=ft.FontWeight.BOLD) # Adjusted

            button_row_offline = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("✅ صح", on_click=handle_correct_offline, col={"xs": 6}, height=55, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                    ft.ElevatedButton("⏭ تخطي", on_click=handle_skip_offline, col={"xs": 6}, height=55, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))) # Adjusted
                ],
                alignment=ft.MainAxisAlignment.CENTER, spacing=10 # Adjusted
            )
            offline_main_column.controls.extend([
                ft.Text(f"🎮 الجولة {s['round']} - فريق: {current_team}", size=22, color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD), # Adjusted
                last_round_text_ui,
                timer_text_control_offline,
                ft.Divider(height=8, thickness=1), # Adjusted
                word_display_offline_container,
                ft.Divider(height=8, thickness=1), # Adjusted
                button_row_offline,
                ft.Container(height=8), # Adjusted
                ft.ElevatedButton("⏹ إنهاء الدور مبكراً", on_click=handle_end_round_offline, width=260, height=40, bgcolor=ft.Colors.AMBER_300, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))), # Adjusted
                ft.Divider(height=10, thickness=1), # Adjusted
                score_display_offline_container
            ])

        elif s["step"] == "round_summary":
            summary_team = s.get("current_round_summary_team", "فريق")
            summary_words = s.get("current_round_summary_words", [])
            word_list_display_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=3, height=130, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Adjusted
            if not summary_words:
                word_list_display_column.controls.append(ft.Text("لم يتم لعب كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=14)) # Adjusted
            else:
                for log_item in summary_words:
                    word_list_display_column.controls.append(
                        ft.Text(f"- {log_item['word']} ({'✔ صح' if log_item['correct'] else '✘ تخطي'})", # Compacted
                                  color=ft.Colors.GREEN_800 if log_item["correct"] else ft.Colors.RED_800,
                                  size=15, text_align=ft.TextAlign.CENTER) # Adjusted
                    )
            summary_container = ft.Container(
                content=word_list_display_column,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=8, # Adjusted
                padding=8, # Adjusted
                width=page.width * 0.9 if page.width else 310, # Adjusted
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
                ft.Text(f"⏰ انتهى وقت فريق: {summary_team}", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text("🔤 كلمات الدور:", size=18, text_align=ft.TextAlign.CENTER), # Adjusted
                summary_container,
                ft.Container(height=8), # Adjusted
                ft.ElevatedButton("▶ الفريق/الجولة التالية", on_click=proceed_to_next_team_or_end_offline, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                # Redundant home button removed
            ])

        elif s["step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة!", size=26, weight="bold", text_align=ft.TextAlign.CENTER)) # Adjusted
            
            final_scores_data = []
            for team, score in sorted(s.get("scores",{}).items(), key=lambda item: item[1], reverse=True):
                final_scores_data.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(team, weight=ft.FontWeight.BOLD, size=16)), # Adjusted
                    ft.DataCell(ft.Text(f"{float(score):.1f}", size=16)), # Adjusted, ensure float
                ]))
            
            if final_scores_data:
                offline_main_column.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD, size=15)), # Adjusted
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=15), numeric=True), # Adjusted
                            ],
                            rows=final_scores_data,
                            column_spacing=25, # Adjusted
                            data_row_max_height=40, # Adjusted
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12), # Corrected color
                        ),
                        width=page.width * 0.85 if page.width else 300, # Adjusted
                        alignment=ft.alignment.center
                    )
                )
            else:
                offline_main_column.controls.append(ft.Text("لا توجد نتائج.", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted

            offline_main_column.controls.extend([
                ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: reset_offline_state_and_ui(), width=260, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                # Redundant home button removed
            ])
        else: # Fallback
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'", size=18, color=ft.Colors.RED_700))
            # Redundant home button removed

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
            padding=ft.padding.symmetric(horizontal=8, vertical=10) # Adjusted overall padding
        )
    ]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def bedoon_kalam_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    # page_title moved to the main content column
    status_text = ft.Text("...", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Adjusted
    
    player_list_display_online = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Adjusted
    team_score_display_online = ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Adjusted
    action_area_online = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8, scroll=ft.ScrollMode.ADAPTIVE) # Adjusted
    word_to_act_display_online = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8) # Adjusted
    online_timer_display = ft.Text("الوقت: --", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700) # Adjusted

    online_main_content_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8 # Adjusted
    )

    def log_debug_online(msg):
        print(f"[BedoonKalam_Online_Client:{current_player_name} session:{page.session_id}] {msg}")

    def update_ui_from_server_state_online(room_state_from_server):
        if not page.client_storage:
            log_debug_online("Page detached, skipping UI update.")
            return

        gs = room_state_from_server.get("game_state",{})
        players_in_room = room_state_from_server.get("players",{})
        teams_data = gs.get("teams", {})
        current_player_data = players_in_room.get(current_player_name, {})
        is_host = current_player_data.get("is_host", False)
        my_team = current_player_data.get("team_name")
        current_phase = gs.get("phase", "LOBBY")

        # log_debug_online(f"Updating UI. Phase: {current_phase}, My Team: {my_team}") # Less verbose
        status_text.value = gs.get("status_message", "...")
        status_text.text_align = ft.TextAlign.CENTER

        player_list_display_online.controls.clear()
        player_list_display_online.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=15)) # Adjusted
        for p_name_iter, p_data_iter in players_in_room.items():
            team_tag = f" (فريق {p_data_iter.get('team_name', '؟')})" if p_data_iter.get('team_name') else ""
            player_list_display_online.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}{team_tag}", text_align=ft.TextAlign.CENTER, size=13) # Adjusted
            )

        team_score_display_online.controls.clear()
        team_score_display_online.controls.append(ft.Text("📊 النقاط:", weight=ft.FontWeight.BOLD, size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
        if teams_data:
            for team_name_iter, team_info in teams_data.items():
                team_score_display_online.controls.append(ft.Text(f"فريق {team_name_iter}: {float(team_info.get('score',0.0)):.1f}", size=14, text_align=ft.TextAlign.CENTER)) # Adjusted, ensure float
        else:
            team_score_display_online.controls.append(ft.Text("لم يتم تحديد الفرق.", text_align=ft.TextAlign.CENTER, size=13)) # Adjusted


        action_area_online.controls.clear()
        word_to_act_display_online.visible = False # Hide by default
        word_to_act_display_online.controls.clear() # Clear previous content

        timer_val = gs.get('timer_value', '--')
        online_timer_display.value = f"⏳ الوقت: {timer_val}" if gs.get("round_active") else "الوقت: --"
        online_timer_display.visible = gs.get("round_active", False)


        if current_phase == "LOBBY":
            action_area_online.controls.append(ft.Text("الهوست يحدد الفرق ويبدأ اللعبة.", text_align=ft.TextAlign.CENTER, size=16)) # Adjusted
            if is_host:
                team_inputs_online_host = []
                for i in range(2): # Bedoon Kalam usually has 2 teams
                    tf = ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8, height=45, text_size=14) # Adjusted
                    team_inputs_online_host.append(tf)
                    action_area_online.controls.append(
                        ft.Container(content=tf, width=page.width * 0.8 if page.width else 260, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3)) # Adjusted
                    )

                def setup_teams_and_start_online(e):
                    team_names_host = [tf.value.strip() for tf in team_inputs_online_host if tf.value.strip()]
                    if len(team_names_host) != 2: # Strictly 2 teams
                        if page.client_storage:
                            page.snack_bar = ft.SnackBar(ft.Text("تحتاج لإدخال اسمي الفريقين بالضبط."),open=True)
                            page.update()
                        return
                    if any(not name for name in team_names_host):
                        if page.client_storage:
                            page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب ألا تكون فارغة."),open=True)
                            page.update()
                        return
                    if len(set(team_names_host)) != len(team_names_host):
                        if page.client_storage:
                            page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب أن تكون فريدة."),open=True)
                            page.update()
                        return
                    send_action_fn("SETUP_TEAMS_AND_START_GAME", {"team_names": team_names_host})

                action_area_online.controls.append(ft.ElevatedButton("🏆 إعداد الفرق والبدء", on_click=setup_teams_and_start_online, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif current_phase == "TEAMS_SET":
            action_area_online.controls.append(ft.Text("تم تحديد الفرق!", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            if teams_data:
                for team_name_iter, team_info in teams_data.items():
                    player_names_in_team = ", ".join(team_info.get("players", []))
                    action_area_online.controls.append(ft.Text(f"فريق {team_name_iter}: {player_names_in_team}", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("▶️ بدء الدور الأول", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            else:
                action_area_online.controls.append(ft.Text("انتظار الهوست لبدء الدور...", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted


        elif current_phase == "TEAM_INTRO":
            acting_team = gs.get("current_acting_team")
            current_actor = gs.get("current_actor_name")
            if my_team == acting_team:
                action_area_online.controls.append(ft.Text(f"استعد يا فريق {acting_team}!", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
                if current_player_name == current_actor:
                    action_area_online.controls.append(ft.Text("أنت ستمثل هذه الجولة!", size=18, color=ft.Colors.GREEN_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Adjusted
                    action_area_online.controls.append(ft.ElevatedButton("👀 عرض الكلمة والبدء", on_click=lambda e: send_action_fn("ACTOR_READY_START_ROUND"), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
                else:
                    action_area_online.controls.append(ft.Text(f"{current_actor} سيمثل. استعدوا!", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
            else:
                action_area_online.controls.append(ft.Text(f"جولة فريق {acting_team}. {current_actor} سيمثل.", size=18, text_align=ft.TextAlign.CENTER)) # Adjusted

        elif current_phase == "ACTING_ROUND":
            word_to_act_display_online.visible = True
            acting_team = gs.get("current_acting_team")
            current_actor = gs.get("current_actor_name")
            current_word = gs.get("current_word_to_act", "---")
            is_last_round_online = (gs.get("current_game_round") == gs.get("max_game_rounds", 3) and gs.get("is_last_team_in_round", False))

            if current_player_name == current_actor:
                word_to_act_display_online.controls.append(ft.Text("مثل الكلمة:", size=20, text_align=ft.TextAlign.CENTER)) # Adjusted
                word_to_act_display_online.controls.append(ft.Text(current_word, size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT_700, text_align=ft.TextAlign.CENTER)) # Adjusted
                action_area_online.controls.append(
                     ft.Text(f"ج {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=16, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER) # Adjusted
                )
                if is_last_round_online:
                     action_area_online.controls.append(ft.Text("⚠️ الدور الأخير في اللعبة!", size=15, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted

                actor_button_row = ft.ResponsiveRow(
                    [
                        ft.ElevatedButton("✅ صح", on_click=lambda e: send_action_fn("WORD_GUESSED_CORRECT"), col={"xs": 6}, height=55, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                        ft.ElevatedButton("⏭ تخطي", on_click=lambda e: send_action_fn("SKIP_WORD"), col={"xs": 6}, height=55, bgcolor=ft.Colors.ORANGE_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=10 # Adjusted
                )
                action_area_online.controls.append(actor_button_row)
            elif my_team == acting_team:
                word_to_act_display_online.controls.append(ft.Text(f"فريقك يمثل! خمن ما يمثله {current_actor}.", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
                word_to_act_display_online.controls.append(ft.Text("الكلمة: ؟؟؟؟؟", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_300, text_align=ft.TextAlign.CENTER)) # Adjusted
                action_area_online.controls.append(
                     ft.Text(f"ج {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=16, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER) # Adjusted
                )
                if is_last_round_online:
                     action_area_online.controls.append(ft.Text("⚠️ الدور الأخير في اللعبة!", size=15, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted

            else: # Spectator
                word_to_act_display_online.controls.append(ft.Text(f"فريق {acting_team} يمثل. ({current_actor})", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
                word_to_act_display_online.controls.append(ft.Text(f"الكلمة: {current_word}", size=24, weight="bold", color=ft.Colors.DEEP_ORANGE_ACCENT_400, text_align=ft.TextAlign.CENTER)) # Adjusted
                action_area_online.controls.append(
                     ft.Text(f"ج {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=16, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER) # Adjusted
                )
                if is_last_round_online:
                     action_area_online.controls.append(ft.Text("⚠️ الدور الأخير في اللعبة!", size=15, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
                action_area_online.controls.append(ft.Text("لا يمكنك التخمين.", size=14, italic=True, text_align=ft.TextAlign.CENTER)) # Adjusted

        elif current_phase == "ROUND_SUMMARY":
            summary_data = gs.get("summary_for_ui", {})
            summary_team = summary_data.get("team_name", "فريق")
            summary_round_num = summary_data.get("round_number", gs.get("current_game_round","?"))
            summary_words = summary_data.get("words", [])

            word_list_display_column_online = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=3, height=130, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Adjusted
            if not summary_words:
                word_list_display_column_online.controls.append(ft.Text("لم يتم لعب كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=14)) # Adjusted
            else:
                for log_item_online in summary_words:
                    word_list_display_column_online.controls.append(
                        ft.Text(f"- {log_item_online['word']} ({'✔ تم' if log_item_online['correct'] else '✘ تخطي'})", # Compacted
                                  color=ft.Colors.GREEN_800 if log_item_online["correct"] else ft.Colors.RED_800,
                                  size=15, text_align=ft.TextAlign.CENTER) # Adjusted
                    )
            summary_container_online = ft.Container(
                content=word_list_display_column_online,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=8, # Adjusted
                padding=8, # Adjusted
                width=page.width * 0.9 if page.width else 310, # Adjusted
                alignment=ft.alignment.top_center
            )
            action_area_online.controls.extend([
                ft.Text(f"⏰ ملخص دور فريق: {summary_team} (ج {summary_round_num})", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text("🔤 الكلمات:", size=18, text_align=ft.TextAlign.CENTER), # Adjusted
                summary_container_online,
                ft.Container(height=8) # Adjusted
            ])
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("▶ الدور التالي", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            else:
                action_area_online.controls.append(ft.Text("انتظار الهوست...", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted

        elif current_phase == "GAME_OVER":
            action_area_online.controls.append(ft.Text("🏁 انتهت اللعبة!", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            if teams_data:
                sorted_teams = sorted(teams_data.items(), key=lambda item: item[1].get('score',0.0), reverse=True) # Ensure float comparison
                final_scores_table_rows = []
                for team_name_iter, team_info_iter in sorted_teams:
                    final_scores_table_rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(team_name_iter, weight=ft.FontWeight.BOLD, size=16)), # Adjusted
                        ft.DataCell(ft.Text(f"{float(team_info_iter.get('score',0.0)):.1f}", size=16)), # Adjusted, ensure float
                    ]))
                if final_scores_table_rows:
                    action_area_online.controls.append(
                        ft.Container(
                            content=ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD, size=15)), # Adjusted
                                    ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=15), numeric=True), # Adjusted
                                ],
                                rows=final_scores_table_rows,
                                column_spacing=25, # Adjusted
                                data_row_max_height=40, # Adjusted
                                horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12), # Corrected color
                            ),
                            width=page.width * 0.85 if page.width else 300, # Adjusted
                            alignment=ft.alignment.center
                        )
                    )
                else:
                    action_area_online.controls.append(ft.Text("لا توجد نتائج.", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: send_action_fn("RESTART_GAME_SAME_TEAMS"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        if page.client_storage:
            # log_debug_online(f"EXECUTING page.update() for phase {current_phase}") # Less verbose
            page.update()
        # else:
            # log_debug_online(f"SKIPPING page.update() for phase {current_phase} because page.client_storage is None") # Less verbose

    def on_server_message_online(*args_received):
        if not page.client_storage: return
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online(room_state)
        elif msg_type == "ACTION_ERROR":
            error_msg = msg_data.get("message", "حدث خطأ ما.")
            if page.client_storage:
                 page.snack_bar = ft.SnackBar(ft.Text(error_msg, text_align=ft.TextAlign.CENTER), open=True)
                 page.update()

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online)
    # log_debug_online(f"Subscribed to topic: room_{room_code}") # Less verbose

    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        # log_debug_online("Found initial room data on client load. Updating UI.") # Less verbose
        update_ui_from_server_state_online(initial_room_data)
    else:
        # log_debug_online(f"Room {room_code} not found on client load.") # Less verbose
        status_text.value = "خطأ في الاتصال بالغرفة."

    online_main_content_column.controls.extend([
        ft.Row( # Consistent Top Bar
            [
                ft.Text(f"🤫 بدون كلام - غرفة: {room_code}", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
                ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=28)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=1, thickness=0.5),
        status_text,
        online_timer_display,
        ft.Divider(height=3, thickness=1), # Adjusted
        word_to_act_display_online, # Content built in update_ui
        ft.ResponsiveRow(
            [
                ft.Container(
                    content=ft.Column([
                        player_list_display_online,
                        ft.Divider(height=8), # Adjusted
                        team_score_display_online
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER), # Adjusted
                    padding=8, # Adjusted
                    border=ft.border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.OUTLINE)), # Adjusted
                    border_radius=8, # Adjusted
                    col={"xs": 12, "md": 4},
                    margin=ft.margin.only(bottom=8 if page.width and page.width < 768 else 0, top=5), # Adjusted
                    min_height=120 # Ensure some height
                ),
                ft.Container(
                    content=action_area_online, # Content built in update_ui
                    padding=ft.padding.symmetric(horizontal=8, vertical=3), # Adjusted
                    col={"xs": 12, "md": 8},
                    alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            spacing=3, run_spacing=3 # Adjusted
        )
    ])
    return [
        ft.Container(
            content=online_main_content_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=6, vertical=6) # Adjusted overall padding
        )
    ]

# --- GAME ENTRY POINT (Called by app.py) ---
def bedoon_kalam_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return bedoon_kalam_offline_logic(page, go_home_fn)
    else:
        if not room_code or not player_name or game_rooms_ref is None:
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة للعب أونلاين."), alignment=ft.alignment.center, expand=True)]

        def send_bedoon_kalam_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "bedoon_kalam", action_type, payload or {})

        return bedoon_kalam_online_logic(page, go_home_fn, send_bedoon_kalam_action_to_server_wrapper, room_code, player_name, game_rooms_ref)