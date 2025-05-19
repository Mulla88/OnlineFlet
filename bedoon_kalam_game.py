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
    word_display_offline_container = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10) # Added spacing
    score_display_offline_container = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5) # Added spacing

    # Buttons will be part of the main column now, no need to define them globally here if rebuilt each time.
    # timer_text_offline will also be created within update_offline_ui

    offline_main_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15
    )

    def destroy_offline_game_state():
        event = offline_state.get("stop_timer_event")
        if isinstance(event, threading.Event):
            event.set()
            time.sleep(0.1)
        offline_state.clear()

    def reset_offline_state_and_ui():
        destroy_offline_game_state()
        offline_state.update({
            "teams": [], "scores": {}, "current_team_index": 0, "used_words": set(), # Changed to set for efficiency
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
            offline_state["used_words"] = set() # Reset used words
            remaining = list(WORD_BANK)
            if not remaining: # Should not happen if WORD_BANK is not empty
                page.snack_bar = ft.SnackBar(ft.Text("لا توجد كلمات في القائمة!"), open=True)
                return "انتهت الكلمات!"
            page.snack_bar = ft.SnackBar(ft.Text("تم إعادة تعيين الكلمات المستخدمة."), open=True)

        word = random.choice(remaining)
        offline_state.setdefault("used_words", set()).add(word)
        return word

    def _get_word_display_content_offline(): # Renamed for clarity
        controls = []
        word = offline_state.get("current_word")
        if word and word != "انتهت الكلمات!":
            controls.append(ft.Text(f"الكلمة: {word}", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER)) # Larger
        elif word:
            controls.append(ft.Text(word, size=26, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER)) # Larger
        return controls

    def _get_score_display_content_offline(): # Renamed for clarity
        controls = []
        if offline_state.get("scores"):
            controls.append(ft.Text("📊 النقاط:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Title
            for team, score in offline_state.get("scores",{}).items():
                controls.append(ft.Text(f"فريق {team}: {score} نقطة", size=20, text_align=ft.TextAlign.CENTER)) # Larger
        return controls


    def handle_end_round_offline(e=None):
        if "stop_timer_event" in offline_state:
            offline_state["stop_timer_event"].set()

        if not offline_state.get("teams") or offline_state.get("current_team_index", -1) < 0:
            print("Error: Cannot end round, team data missing in offline state.")
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

    timer_text_control_offline = ft.Text("الوقت: 90 ثانية", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700) # Define once

    def start_timer_offline():
        if "stop_timer_event" not in offline_state: return
        stop_event = offline_state["stop_timer_event"]
        stop_event.clear()

        round_duration = offline_state.get("round_duration", 90)
        timer_text_control_offline.value = f"⏳ الوقت المتبقي: {round_duration} ثانية"
        if page.client_storage: timer_text_control_offline.update()

        def run_timer():
            for i in range(round_duration, -1, -1):
                if page.client_storage is None: break
                if stop_event.is_set(): return

                timer_text_control_offline.value = f"⏳ الوقت المتبقي: {i} ثانية"
                if page.client_storage: timer_text_control_offline.update()

                if i == 0:
                    if not stop_event.is_set():
                        if page.client_storage:
                            page.run_thread_safe(lambda: handle_end_round_offline(None))
                        else:
                            return
                    return
                time.sleep(1)

        threading.Thread(target=run_timer, daemon=True).start()


    def show_team_intro_offline():
        offline_state["step"] = "team_intro"
        update_offline_ui()

    def start_round_logic_offline():
        offline_state["step"] = "playing_round"
        offline_state["current_word"] = get_new_word_offline()
        update_offline_ui()
        start_timer_offline()


    def handle_correct_offline(e):
        if not offline_state.get("teams") or offline_state.get("current_word", "").startswith("انتهت الكلمات"): return
        team = offline_state["teams"][offline_state["current_team_index"]]
        offline_state["scores"][team] = offline_state["scores"].get(team, 0) + 2 # Corrected score increment
        offline_state.setdefault("word_log",[]).append({"team": team, "word": offline_state["current_word"], "correct": True, "round": offline_state["round"]})

        new_word = get_new_word_offline()
        offline_state["current_word"] = new_word
        if offline_state["step"] == "playing_round":
            update_offline_ui()

        if new_word == "انتهت الكلمات!":
            if page.client_storage: # Ensure it's safe to call
                handle_end_round_offline()


    def handle_skip_offline(e):
        if not offline_state.get("teams") or offline_state.get("current_word", "").startswith("انتهت الكلمات"): return
        team = offline_state["teams"][offline_state["current_team_index"]]
        offline_state["scores"][team] = offline_state["scores"].get(team, 0) - 0.5
        offline_state.setdefault("word_log",[]).append({"team": team, "word": offline_state["current_word"], "correct": False, "round": offline_state["round"]})

        new_word = get_new_word_offline()
        offline_state["current_word"] = new_word
        if offline_state["step"] == "playing_round":
            update_offline_ui()

        if new_word == "انتهت الكلمات!":
            if page.client_storage: # Ensure it's safe to call
                handle_end_round_offline()


    def start_game_setup_offline(e):
        team_names = [tf.value.strip() for tf in team_name_fields_offline if tf.value.strip()]
        if len(team_names) < 2 or any(not name for name in team_names): # Check for empty names too
            page.snack_bar = ft.SnackBar(ft.Text("❗ تحتاج لفريقين على الأقل وبأسماء غير فارغة."), open=True)
            if page.client_storage: page.update()
            return
        if len(set(team_names)) != len(team_names): # Check for unique team names
            page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء الفرق يجب أن تكون فريدة."), open=True)
            if page.client_storage: page.update()
            return

        offline_state["teams"] = team_names
        offline_state["scores"] = {team: 0 for team in team_names}
        offline_state["game_started"] = True
        offline_state["round"] = 1
        offline_state["current_team_index"] = 0
        offline_state["used_words"] = set() # Initialize as set
        offline_state["word_log"] = []
        show_team_intro_offline()


    def update_offline_ui():
        offline_main_column.controls.clear()
        s = offline_state

        if s["step"] == "input_teams":
            offline_main_column.controls.append(ft.Text("🎯 لعبة بدون كلام", size=30, weight=ft.FontWeight.BOLD)) # Larger
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء الفرق (فريقان):", size=22)) # Clarified 2 teams
            team_name_fields_offline.clear()
            for i in range(2): # Fixed to 2 teams for now as per typical setup
                tf_container = ft.Container(
                    content=ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER),
                    width=page.width * 0.85 if page.width else 300,
                    alignment=ft.alignment.center
                )
                team_name_fields_offline.append(tf_container.content) # Store the TextField itself
                offline_main_column.controls.append(tf_container)
            offline_main_column.controls.append(ft.ElevatedButton("🚀 بدء اللعبة بالفرق المدخلة", on_click=start_game_setup_offline, width=300, height=55)) # Wider
            offline_main_column.controls.append(ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=safe_go_home_offline, width=250, height=50))

        elif s["step"] == "team_intro":
            if not s.get("teams") or s.get("current_team_index", -1) >= len(s["teams"]):
                 # Safety check if teams/index are invalid, go back to setup
                print("Error in team_intro: Invalid teams or current_team_index.")
                set_offline_step("input_teams")
                return

            current_team = s["teams"][s["current_team_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"استعد يا فريق", size=26, text_align=ft.TextAlign.CENTER),
                ft.Text(f"{current_team}", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_ACCENT_700),
                ft.Text(f"سيقوم أحد أعضاء فريقكم بالتمثيل.", size=20, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(f"🚀 ابدأ الجولة {s['round']} لفريق {current_team}",
                                 on_click=lambda e: start_round_logic_offline(), width=300, height=60,
                                 style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif s["step"] == "playing_round":
            current_team = s["teams"][s["current_team_index"]]

            word_display_offline_container.controls = _get_word_display_content_offline()
            word_display_offline_container.visible = True

            score_display_offline_container.controls = _get_score_display_content_offline()
            score_display_offline_container.visible = True

            is_last_round = (s["round"] == s["max_rounds"])
            last_round_text = ft.Text("⚠️ هذا هو الدور الأخير!", size=20, color=ft.Colors.RED_700, visible=is_last_round, weight=ft.FontWeight.BOLD)

            # Button row for Correct and Skip
            button_row_offline = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("✅ إجابة صحيحة", on_click=handle_correct_offline, col={"xs": 6}, height=60, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                    ft.ElevatedButton("⏭ تخطي", on_click=handle_skip_offline, col={"xs": 6}, height=60, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15
            )

            offline_main_column.controls.extend([
                ft.Text(f"🎮 الجولة {s['round']} - فريق: {current_team}", size=24, color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD), # Larger
                last_round_text,
                timer_text_control_offline, # Use the single instance
                ft.Divider(height=10, thickness=1),
                word_display_offline_container,
                ft.Divider(height=10, thickness=1),
                button_row_offline,
                ft.Container(height=10), # Spacer
                ft.ElevatedButton("⏹ إنهاء الجولة مبكراً", on_click=handle_end_round_offline, width=280, height=45, bgcolor=ft.Colors.AMBER_300, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Slightly different color
                ft.Divider(height=15, thickness=1),
                score_display_offline_container
            ])

        elif s["step"] == "round_summary":
            summary_team = s.get("current_round_summary_team", "فريق")
            summary_words = s.get("current_round_summary_words", [])

            word_list_display_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=5, height=150) # Max height for scroll
            if not summary_words:
                word_list_display_column.controls.append(ft.Text("لم يتم لعب كلمات.", italic=True, text_align=ft.TextAlign.CENTER))
            else:
                for log_item in summary_words: # Renamed log to log_item
                    word_list_display_column.controls.append(
                        ft.Text(f"- {log_item['word']} ({'✔ إجابة صحيحة' if log_item['correct'] else '✘ تخطي'})",
                                  color=ft.Colors.GREEN_800 if log_item["correct"] else ft.Colors.RED_800,
                                  size=16, text_align=ft.TextAlign.CENTER) # Centered and slightly larger
                    )
            summary_container = ft.Container( # Container for word list
                content=word_list_display_column,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=5,
                padding=10,
                width=page.width * 0.9 if page.width else 320,
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
                ft.Text(f"⏰ انتهى وقت فريق: {summary_team}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER), # Changed color
                ft.Text("🔤 الكلمات التي ظهرت في هذا الدور:", size=20, text_align=ft.TextAlign.CENTER),
                summary_container,
                ft.Container(height=10), # Spacer
                ft.ElevatedButton("▶ الفريق التالي / الجولة التالية", on_click=proceed_to_next_team_or_end_offline, width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=safe_go_home_offline, width=250, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif s["step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة! النتائج النهائية:", size=28, weight="bold", text_align=ft.TextAlign.CENTER)) # Larger
            
            final_scores_data = []
            for team, score in sorted(s.get("scores",{}).items(), key=lambda item: item[1], reverse=True):
                final_scores_data.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(team, weight=ft.FontWeight.BOLD, size=18)),
                    ft.DataCell(ft.Text(str(score), size=18)),
                ]))
            
            if final_scores_data:
                offline_main_column.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD), numeric=True),
                            ],
                            rows=final_scores_data,
                            column_spacing=30,
                            data_row_max_height=45, # Increased height
                            horizontal_lines=ft.border.BorderSide(1, "black12"),
                        ),
                        width=page.width * 0.8 if page.width else 300,
                        alignment=ft.alignment.center
                    )
                )
            else:
                offline_main_column.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER))


            offline_main_column.controls.extend([
                ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: reset_offline_state_and_ui(), width=250, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=safe_go_home_offline, width=250, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])
        else:
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'"))
            offline_main_column.controls.append(ft.ElevatedButton("العودة للرئيسية", on_click=safe_go_home_offline))


        if page.client_storage: page.update()

    def set_offline_step(step_name):
        offline_state["step"] = step_name
        update_offline_ui()

    def safe_go_home_offline(e=None):
        destroy_offline_game_state()
        go_home_fn()

    # Correct and Skip buttons are now created within update_offline_ui when step is "playing_round"

    reset_offline_state_and_ui()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center, # Keep top alignment
            padding=ft.padding.symmetric(horizontal=10, vertical=15) # Overall padding
        )
    ]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def bedoon_kalam_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):

    page_title = ft.Text(f"لعبة بدون كلام - غرفة: {room_code}", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Larger
    status_text = ft.Text("...", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Larger
    
    player_list_display_online = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Centered text
    team_score_display_online = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Centered text
    action_area_online = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    word_to_act_display_online = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    online_timer_display = ft.Text("الوقت: --", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700) # Larger and colored

    online_main_content_column = ft.Column( # This will be the content of the padded container
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
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

        log_debug_online(f"Updating UI. Phase: {current_phase}, My Team: {my_team}")
        status_text.value = gs.get("status_message", "...")
        status_text.text_align = ft.TextAlign.CENTER

        player_list_display_online.controls.clear()
        player_list_display_online.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
        for p_name_iter, p_data_iter in players_in_room.items():
            team_tag = f" (فريق {p_data_iter.get('team_name', '؟')})" if p_data_iter.get('team_name') else ""
            player_list_display_online.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}{team_tag}", text_align=ft.TextAlign.CENTER, size=16) # Slightly larger
            )

        team_score_display_online.controls.clear()
        team_score_display_online.controls.append(ft.Text("📊 النقاط:", weight=ft.FontWeight.BOLD, size=20, text_align=ft.TextAlign.CENTER)) # Title
        if teams_data:
            for team_name_iter, team_info in teams_data.items():
                team_score_display_online.controls.append(ft.Text(f"فريق {team_name_iter}: {team_info.get('score',0)}", size=18, text_align=ft.TextAlign.CENTER)) # Larger
        else:
            team_score_display_online.controls.append(ft.Text("لم يتم تحديد الفرق بعد.", text_align=ft.TextAlign.CENTER))


        action_area_online.controls.clear()
        word_to_act_display_online.visible = False
        timer_val = gs.get('timer_value', '--')
        online_timer_display.value = f"⏳ الوقت: {timer_val}" if gs.get("round_active") else "الوقت: --"
        online_timer_display.visible = gs.get("round_active", False) # Show timer only when round is active


        if current_phase == "LOBBY":
            action_area_online.controls.append(ft.Text("في انتظار الهوست لتحديد الفرق وبدء اللعبة.", text_align=ft.TextAlign.CENTER, size=18)) # Larger
            if is_host:
                team_inputs_online_host = [] # Changed variable name
                for i in range(2):
                    tf_container = ft.Container(
                        content=ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER),
                        width=page.width * 0.8 if page.width else 280, # Responsive width
                        alignment=ft.alignment.center
                    )
                    team_inputs_online_host.append(tf_container.content) # Store TextField
                    action_area_online.controls.append(tf_container)

                def setup_teams_and_start_online(e):
                    team_names_host = [tf.value.strip() for tf in team_inputs_online_host if tf.value.strip()]
                    if len(team_names_host) < 2 or any(not name for name in team_names_host):
                        page.snack_bar = ft.SnackBar(ft.Text("تحتاج لإدخال اسمي الفريقين بشكل صحيح."),open=True)
                        if page.client_storage: page.update()
                        return
                    if len(set(team_names_host)) != len(team_names_host):
                        page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب أن تكون فريدة."),open=True)
                        if page.client_storage: page.update()
                        return
                    send_action_fn("SETUP_TEAMS_AND_START_GAME", {"team_names": team_names_host})

                action_area_online.controls.append(ft.ElevatedButton("🏆 إعداد الفرق وبدء اللعبة", on_click=setup_teams_and_start_online, width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Wider

        elif current_phase == "TEAMS_SET":
            action_area_online.controls.append(ft.Text("تم تحديد الفرق!", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            if teams_data:
                for team_name_iter, team_info in teams_data.items():
                    player_names_in_team = ", ".join(team_info.get("players", []))
                    action_area_online.controls.append(ft.Text(f"فريق {team_name_iter}: {player_names_in_team}", text_align=ft.TextAlign.CENTER, size=16)) # Larger
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("▶️ بدء الدور الأول", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                action_area_online.controls.append(ft.Text("في انتظار الهوست لبدء الدور الأول...", text_align=ft.TextAlign.CENTER, size=16))


        elif current_phase == "TEAM_INTRO":
            acting_team = gs.get("current_acting_team")
            current_actor = gs.get("current_actor_name")
            if my_team == acting_team:
                action_area_online.controls.append(ft.Text(f"استعد يا فريق {acting_team}!", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
                if current_player_name == current_actor:
                    action_area_online.controls.append(ft.Text("أنت من سيمثل هذه الجولة!", size=20, color=ft.Colors.GREEN_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Bolder
                    action_area_online.controls.append(ft.ElevatedButton("👀 عرض الكلمة والبدء", on_click=lambda e: send_action_fn("ACTOR_READY_START_ROUND"), width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Larger
                else:
                    action_area_online.controls.append(ft.Text(f"{current_actor} من فريقكم سيمثل. استعدوا للتخمين!", size=18, text_align=ft.TextAlign.CENTER))
            else:
                action_area_online.controls.append(ft.Text(f"جولة فريق {acting_team}. {current_actor} سيمثل.", size=20, text_align=ft.TextAlign.CENTER)) # Larger

        elif current_phase == "ACTING_ROUND":
            word_to_act_display_online.visible = True
            word_to_act_display_online.controls.clear()

            acting_team = gs.get("current_acting_team")
            current_actor = gs.get("current_actor_name")
            current_word = gs.get("current_word_to_act", "---")
            is_last_round_online = (gs.get("current_game_round") == gs.get("max_game_rounds", 3) and gs.get("is_last_team_in_round", False))


            if current_player_name == current_actor:
                word_to_act_display_online.controls.append(ft.Text("مثل الكلمة التالية:", size=22, text_align=ft.TextAlign.CENTER)) # Larger
                word_to_act_display_online.controls.append(ft.Text(current_word, size=36, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT_700, text_align=ft.TextAlign.CENTER)) # Larger
                action_area_online.controls.append(
                     ft.Text(f"الجولة {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=18, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER)
                )
                if is_last_round_online:
                     action_area_online.controls.append(ft.Text("⚠️ هذا هو الدور الأخير في اللعبة!", size=16, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))

                # Buttons for actor
                actor_button_row = ft.ResponsiveRow(
                    [
                        ft.ElevatedButton("✅ خمنوها صح!", on_click=lambda e: send_action_fn("WORD_GUESSED_CORRECT"), col={"xs": 6}, height=60, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                        ft.ElevatedButton("⏭ تخطي الكلمة", on_click=lambda e: send_action_fn("SKIP_WORD"), col={"xs": 6}, height=60, bgcolor=ft.Colors.ORANGE_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=15
                )
                action_area_online.controls.append(actor_button_row)
            elif my_team == acting_team:
                word_to_act_display_online.controls.append(ft.Text(f"فريقك يمثل! حاول تخمين الكلمة التي يمثلها {current_actor}.", size=18, text_align=ft.TextAlign.CENTER))
                word_to_act_display_online.controls.append(ft.Text("الكلمة: ؟؟؟؟؟", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_300, text_align=ft.TextAlign.CENTER)) # Lighter color for guessers
                action_area_online.controls.append(
                     ft.Text(f"الجولة {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=18, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER)
                )
                if is_last_round_online:
                     action_area_online.controls.append(ft.Text("⚠️ هذا هو الدور الأخير في اللعبة!", size=16, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))

            else: # Spectator from other team
                word_to_act_display_online.controls.append(ft.Text(f"فريق {acting_team} يمثل الآن. {current_actor} هو الممثل.", size=18, text_align=ft.TextAlign.CENTER))
                word_to_act_display_online.controls.append(ft.Text(f"الكلمة التي يمثلونها: {current_word}", size=26, weight="bold", color=ft.Colors.DEEP_ORANGE_ACCENT_400, text_align=ft.TextAlign.CENTER)) # Bolder
                action_area_online.controls.append(
                     ft.Text(f"الجولة {gs.get('current_game_round', '?')} - دور فريق: {acting_team}", size=18, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER)
                )
                if is_last_round_online:
                     action_area_online.controls.append(ft.Text("⚠️ هذا هو الدور الأخير في اللعبة!", size=16, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
                action_area_online.controls.append(ft.Text("لا يمكنك التخمين الآن.", size=16, italic=True, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ROUND_SUMMARY":
            summary_data = gs.get("summary_for_ui", {})
            summary_team = summary_data.get("team_name", "فريق")
            summary_round_num = summary_data.get("round_number", gs.get("current_game_round","?"))
            summary_words = summary_data.get("words", [])

            word_list_display_column_online = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=5, height=150) # Max height
            if not summary_words:
                word_list_display_column_online.controls.append(ft.Text("لم يتم لعب أي كلمات في هذا الدور.", italic=True, text_align=ft.TextAlign.CENTER))
            else:
                for log_item_online in summary_words: # Renamed
                    word_list_display_column_online.controls.append(
                        ft.Text(f"- {log_item_online['word']} ({'✔ تم التخمين' if log_item_online['correct'] else '✘ تخطي'})",
                                  color=ft.Colors.GREEN_800 if log_item_online["correct"] else ft.Colors.RED_800,
                                  size=16, text_align=ft.TextAlign.CENTER)
                    )
            summary_container_online = ft.Container( # Container for word list
                content=word_list_display_column_online,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=5,
                padding=10,
                width=page.width * 0.9 if page.width else 320,
                alignment=ft.alignment.top_center
            )

            action_area_online.controls.extend([
                ft.Text(f"⏰ ملخص دور فريق: {summary_team} (الجولة {summary_round_num})", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER), # Larger
                ft.Text("🔤 الكلمات:", size=20, text_align=ft.TextAlign.CENTER),
                summary_container_online,
                ft.Container(height=10) # Spacer
            ])

            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("▶ الدور التالي / الجولة التالية", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                action_area_online.controls.append(ft.Text("في انتظار الهوست للمتابعة...", text_align=ft.TextAlign.CENTER, size=16))

        elif current_phase == "GAME_OVER":
            action_area_online.controls.append(ft.Text("🏁 انتهت اللعبة! النتائج النهائية:", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            if teams_data:
                sorted_teams = sorted(teams_data.items(), key=lambda item: item[1].get('score',0), reverse=True)
                
                final_scores_table_rows = []
                for team_name_iter, team_info_iter in sorted_teams:
                    final_scores_table_rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(team_name_iter, weight=ft.FontWeight.BOLD, size=18)),
                        ft.DataCell(ft.Text(str(team_info_iter.get('score',0)), size=18)),
                    ]))
                
                if final_scores_table_rows:
                    action_area_online.controls.append(
                        ft.Container(
                            content=ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD), numeric=True),
                                ],
                                rows=final_scores_table_rows,
                                column_spacing=30,
                                data_row_max_height=45,
                                horizontal_lines=ft.border.BorderSide(1, "black12"),
                            ),
                            width=page.width * 0.8 if page.width else 300,
                            alignment=ft.alignment.center
                        )
                    )
                else: # Should not happen if teams_data exists
                    action_area_online.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER))

            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى بنفس الفرق", on_click=lambda e: send_action_fn("RESTART_GAME_SAME_TEAMS"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Wider

        if page.client_storage:
            log_debug_online(f"EXECUTING page.update() for phase {current_phase}")
            page.update()
        else:
            log_debug_online(f"SKIPPING page.update() for phase {current_phase} because page.client_storage is None")


    def on_server_message_online(*args_received):
        if not page.client_storage:
            log_debug_online("Page disposed, skipping on_server_message.")
            return
        # log_debug_online(f"PUBSUB_RAW_ARGS_RECEIVED: {args_received}")
        if not args_received or len(args_received) < 2:
            log_debug_online(f"Not enough arguments received in on_server_message: {len(args_received)}")
            return

        msg_data = args_received[1]
        if not isinstance(msg_data, dict):
            log_debug_online(f"Error: Extracted msg_data is not a dictionary: type={type(msg_data)}, value={msg_data}")
            return

        msg_type = msg_data.get("type")
        # log_debug_online(f"Processing PubSub: Type: {msg_type}")

        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online(room_state)
            else:
                log_debug_online(f"Error: No valid room_state in message for {msg_type}. room_state: {room_state}")
        elif msg_type == "ACTION_ERROR":
            error_msg = msg_data.get("message", "حدث خطأ ما.")
            log_debug_online(f"Action Error from server: {error_msg}")
            if page.client_storage:
                 page.snack_bar = ft.SnackBar(ft.Text(error_msg, text_align=ft.TextAlign.CENTER), open=True)
                 page.update()
        # else:
            # log_debug_online(f"Unknown message type received: {msg_type}")

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online)
    log_debug_online(f"Subscribed to topic: room_{room_code}")

    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        log_debug_online("Found initial room data on client load. Updating UI.")
        update_ui_from_server_state_online(initial_room_data)
    else:
        log_debug_online(f"Room {room_code} not found in game_rooms_ref on client load.")
        status_text.value = "خطأ في الاتصال بالغرفة."


    # Main layout construction for online mode
    online_main_content_column.controls.extend([
        ft.Row(
            [page_title, ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=30)], # Larger icon
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=5, thickness=1.5), # Slightly thicker
        status_text,
        online_timer_display,
        ft.Divider(height=5, thickness=1.5),
        word_to_act_display_online,
        # ResponsiveRow for player list/scores and action area
        ft.ResponsiveRow(
            [
                ft.Container( # Container for Player List & Team Scores
                    content=ft.Column([
                        player_list_display_online,
                        ft.Divider(height=10),
                        team_score_display_online
                    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER), # Center content within this column
                    padding=10,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.6, ft.Colors.OUTLINE)), # Slightly more visible border
                    border_radius=10, # More rounded
                    col={"xs": 12, "md": 4}, # Takes full width on small, less on medium+
                    margin=ft.margin.only(bottom=15 if page.width and page.width < 768 else 0) # Margin when stacked
                ),
                ft.Container( # Container for Main Action Area
                    content=action_area_online,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5), # Adjust padding as needed
                    col={"xs": 12, "md": 8}, # Takes full width on small, more on medium+
                    alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            alignment=ft.MainAxisAlignment.SPACE_AROUND # Space around for better distribution
        )
    ])
    return [
        ft.Container(
            content=online_main_content_column, # This is the main Column
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=10, vertical=10) # Overall padding for the view
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