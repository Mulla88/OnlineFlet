# taboo_game.py
import flet as ft
import random
import threading
import time
from taboo_words import WORD_BANK

# --- OFFLINE MODE LOGIC ---
_taboo_offline_state = {}

def taboo_offline_logic(page: ft.Page, go_home_fn):
    team_name_fields_offline_controls = [] # To store TextField controls
    # UI elements that update frequently
    word_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8 # Adjusted spacing
    )
    score_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=5 # Adjusted spacing
    )
    timer_text_offline_control = ft.Text("الوقت: 60", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700) # Defined once, larger
    last_round_warning_offline_text = ft.Text("", size=20, color=ft.Colors.RED_700, visible=False, weight=ft.FontWeight.BOLD) # Defined once

    offline_main_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20 # Increased spacing
    )

    def destroy_taboo_offline_state():
        event = _taboo_offline_state.get("stop_timer_event")
        if isinstance(event, threading.Event):
            event.set()
            time.sleep(0.1)
        _taboo_offline_state.clear()

    def reset_taboo_offline_game():
        destroy_taboo_offline_state()
        _taboo_offline_state.update({
            "teams": [], "scores": {}, "current_team_index": 0, "used_words_secrets": set(), # Use set
            "word_log": [], "current_word_obj": None, "game_started": False,
            "round": 1, "step": "input_teams",
            "stop_timer_event": threading.Event(),
            "max_rounds": 3, "round_duration": 60,
            "current_round_summary_data": {} # Initialize
        })
        update_taboo_offline_ui()

    def get_new_taboo_word_offline():
        remaining = [w for w in WORD_BANK if isinstance(w, dict) and w.get("secret") and w["secret"] not in _taboo_offline_state.get("used_words_secrets", set())]
        if not remaining:
            if not WORD_BANK: # If WORD_BANK is empty from the start
                page.snack_bar = ft.SnackBar(ft.Text("قائمة الكلمات فارغة!"), open=True)
                if page.client_storage: page.update()
                return None
            _taboo_offline_state["used_words_secrets"] = set()
            remaining = [w for w in WORD_BANK if isinstance(w, dict) and w.get("secret")]
            page.snack_bar = ft.SnackBar(ft.Text("تم إعادة تعيين الكلمات المستخدمة."), open=True)
            if page.client_storage: page.update()
            if not remaining: # Should not happen if WORD_BANK was not empty
                return None
        word_obj = random.choice(remaining)
        _taboo_offline_state.setdefault("used_words_secrets", set()).add(word_obj["secret"])
        return word_obj

    def _get_taboo_word_display_content_offline(): # Renamed
        controls = []
        word_obj = _taboo_offline_state.get("current_word_obj")
        if word_obj:
            controls.append(ft.Text(f"الكلمة السرية:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            controls.append(ft.Text(f"{word_obj['secret']}", size=34, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER, selectable=True)) # Larger
            controls.append(ft.Container(height=10)) # Spacer
            controls.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.BLOCK_ROUNDED, color=ft.Colors.RED_ACCENT_700, size=28), # Changed icon
                        ft.Text("كلمات ممنوعة:", size=22, color=ft.Colors.RED_ACCENT_700, weight=ft.FontWeight.BOLD) # Larger
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=8
                )
            )
            forbidden_list_col = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            for w_forbidden in word_obj.get("forbidden", []):
                forbidden_list_col.controls.append(ft.Text(f"• {w_forbidden}", color=ft.Colors.RED_700, size=18, text_align=ft.TextAlign.CENTER)) # Larger, centered
            controls.append(forbidden_list_col)
        elif _taboo_offline_state.get("current_word_obj") is None and _taboo_offline_state.get("step") == "playing_round":
             controls.append(ft.Text("انتهت الكلمات!", size=28, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Larger
        return controls

    def _get_taboo_score_display_content_offline(): # Renamed
        controls = []
        if _taboo_offline_state.get("scores"):
            controls.append(ft.Text("📊 النقاط الحالية:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Title
            for team, score in _taboo_offline_state.get("scores",{}).items():
                controls.append(ft.Text(f"فريق {team}: {float(score):.1f} نقطة", size=20, text_align=ft.TextAlign.CENTER)) # Larger, formatted
        return controls

    def end_taboo_round_offline(e=None):
        if "stop_timer_event" in _taboo_offline_state:
            _taboo_offline_state["stop_timer_event"].set()

        if not _taboo_offline_state.get("teams") or _taboo_offline_state.get("current_team_index", -1) < 0 :
             set_taboo_offline_step("input_teams")
             return

        team_name = _taboo_offline_state["teams"][_taboo_offline_state["current_team_index"]]
        current_round_num = _taboo_offline_state["round"]
        round_words = [
            log for log in _taboo_offline_state.get("word_log", [])
            if log.get("team") == team_name and log.get("round") == current_round_num
        ]
        _taboo_offline_state["current_round_summary_data"] = {"team": team_name, "words": round_words}
        set_taboo_offline_step("round_summary")

    def start_taboo_timer_offline():
        if "stop_timer_event" not in _taboo_offline_state: return
        stop_event = _taboo_offline_state["stop_timer_event"]
        stop_event.clear()
        duration = _taboo_offline_state.get("round_duration", 60)
        timer_text_offline_control.value = f"⏳ الوقت المتبقي: {duration} ثانية"
        if page.client_storage: timer_text_offline_control.update()

        def run_timer():
            for i in range(duration, -1, -1):
                if not page.client_storage or stop_event.is_set(): return
                timer_text_offline_control.value = f"⏳ الوقت المتبقي: {i} ثانية"
                if page.client_storage: timer_text_offline_control.update()
                if i == 0:
                    if not stop_event.is_set() and page.client_storage:
                        page.run_thread_safe(lambda: end_taboo_round_offline(None))
                    return
                time.sleep(1)
        threading.Thread(target=run_timer, daemon=True).start()

    def start_taboo_round_offline():
        s = _taboo_offline_state
        # Check if game should end before starting a new round
        if s["round"] > s.get("max_rounds", 3):
            set_taboo_offline_step("game_over")
            return

        s["step"] = "playing_round"
        s["current_word_obj"] = get_new_taboo_word_offline()

        update_taboo_offline_ui() # This will now build the buttons
        if s["current_word_obj"]:
            start_taboo_timer_offline()
        else: # No more words
            timer_text_offline_control.value = "لا توجد كلمات لبدء الجولة!"
            # Maybe automatically end round or go to game over if no words AT ALL for any team.
            # For now, the UI will show "انتهت الكلمات!" and buttons will be disabled effectively.
            # Consider adding a button to proceed if this happens.
            if page.client_storage: timer_text_offline_control.update()


    def handle_correct_taboo_offline(e):
        s = _taboo_offline_state
        if not s.get("current_word_obj"): return
        team_name = s["teams"][s["current_team_index"]]
        s["scores"][team_name] = s["scores"].get(team_name,0.0) + 1.0
        s.setdefault("word_log",[]).append({
            "team": team_name, "word": s["current_word_obj"]["secret"],
            "correct": True, "round": s["round"]
        })
        s["current_word_obj"] = get_new_taboo_word_offline()
        if s["step"] == "playing_round":
            update_taboo_offline_ui()
        if not s["current_word_obj"] and page.client_storage: end_taboo_round_offline()


    def handle_skip_taboo_offline(e):
        s = _taboo_offline_state
        if not s.get("current_word_obj"): return
        team_name = s["teams"][s["current_team_index"]]
        s["scores"][team_name] = s["scores"].get(team_name,0.0) - 0.5
        s.setdefault("word_log",[]).append({
            "team": team_name, "word": s["current_word_obj"]["secret"],
            "correct": False, "round": s["round"]
        })
        s["current_word_obj"] = get_new_taboo_word_offline()
        if s["step"] == "playing_round":
            update_taboo_offline_ui()
        if not s["current_word_obj"] and page.client_storage: end_taboo_round_offline()

    def start_taboo_game_from_inputs_offline(e):
        s = _taboo_offline_state
        team_names = [tf.value.strip() for tf in team_name_fields_offline_controls if tf.value.strip()] # Use new list
        if len(team_names) != 2 or any(not name for name in team_names): # Ensure exactly 2 non-empty names
            page.snack_bar = ft.SnackBar(ft.Text("❗ تحتاج لإدخال اسمي الفريقين بشكل صحيح."), open=True)
            if page.client_storage: page.update()
            return
        if len(set(team_names)) != len(team_names): # Check for unique team names
            page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء الفرق يجب أن تكون فريدة."), open=True)
            if page.client_storage: page.update()
            return

        s["teams"] = team_names
        s["scores"] = {team: 0.0 for team in team_names}
        s["game_started"] = True
        s["round"] = 1
        s["current_team_index"] = 0
        s["used_words_secrets"] = set() # Initialize as set
        s["word_log"] = []
        # Instead of calling start_taboo_round_offline directly, go to team intro
        # This ensures the first team sees the "Ready?" screen
        set_taboo_offline_step("team_intro_offline")


    def set_taboo_offline_step(step_name):
        _taboo_offline_state["step"] = step_name
        update_taboo_offline_ui()

    def safe_go_home_taboo_offline(e=None):
        destroy_taboo_offline_state()
        go_home_fn()

    def update_taboo_offline_ui():
        nonlocal team_name_fields_offline_controls # To modify it
        offline_main_column.controls.clear()
        s = _taboo_offline_state

        if s["step"] == "input_teams":
            offline_main_column.controls.append(ft.Text("🚫 لعبة تابو", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Game Title
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء الفرق (فريقان):", size=24, text_align=ft.TextAlign.CENTER)) # Larger
            team_name_fields_offline_controls.clear() # Clear old TextFields
            for i in range(2): # Fixed to 2 teams
                tf = ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8)
                team_name_fields_offline_controls.append(tf)
                offline_main_column.controls.append(
                    ft.Container(content=tf, width=page.width * 0.85 if page.width else 300, alignment=ft.alignment.center)
                )
            offline_main_column.controls.append(ft.ElevatedButton("🚀 ابدأ اللعبة", on_click=start_taboo_game_from_inputs_offline, width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Larger
            offline_main_column.controls.append(ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=safe_go_home_taboo_offline, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        elif s["step"] == "team_intro_offline": # New step for offline
            if not s.get("teams") or s.get("current_team_index", -1) >= len(s["teams"]):
                set_taboo_offline_step("input_teams")
                return
            current_team = s["teams"][s["current_team_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"استعد يا فريق", size=28, text_align=ft.TextAlign.CENTER),
                ft.Text(f"{current_team}", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_ACCENT_700),
                ft.Text(f"سيقوم أحد أعضاء فريقكم بوصف الكلمات.", size=20, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(f"🚀 ابدأ الدور {s['round']} لفريق {current_team}",
                                 on_click=lambda e: start_taboo_round_offline(), width=300, height=60,
                                 style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif s["step"] == "playing_round":
            current_team = s["teams"][s["current_team_index"]]
            last_round_warning_offline_text.visible = (s["round"] == s.get("max_rounds",3))
            last_round_warning_offline_text.value = "⚠️ هذا هو الدور الأخير!" if last_round_warning_offline_text.visible else ""

            word_display_offline_container.controls = _get_taboo_word_display_content_offline()
            score_display_offline_container.controls = _get_taboo_score_display_content_offline()
            word_display_offline_container.visible = True
            score_display_offline_container.visible = True

            buttons_playing_row = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("✅ إجابة صحيحة", on_click=handle_correct_taboo_offline, col={"xs": 6}, height=70, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                    ft.ElevatedButton("⏭ تخطي/ممنوعة", on_click=handle_skip_taboo_offline, col={"xs": 6}, height=70, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))
                ],
                alignment=ft.MainAxisAlignment.CENTER, spacing=15
            )

            offline_main_column.controls.extend([
                ft.Text(f"🎮 الجولة {s['round']} - فريق: {current_team}", size=24, color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD), # Larger
                last_round_warning_offline_text,
                timer_text_offline_control, # Use the single instance
                ft.Divider(height=10, thickness=1),
                word_display_offline_container,
                ft.Divider(height=10, thickness=1),
                buttons_playing_row,
                ft.Container(height=10), # Spacer
                ft.ElevatedButton("⏹ إنهاء الدور مبكراً", on_click=end_taboo_round_offline, width=280, height=45, bgcolor=ft.Colors.AMBER_400, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                ft.Divider(height=15, thickness=1),
                score_display_offline_container,
            ])

        elif s["step"] == "round_summary":
            summary_data = s.get("current_round_summary_data", {})
            team_name = summary_data.get("team", "فريق")
            words = summary_data.get("words", [])

            summary_word_list_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=150) # Max height for scroll
            if not words:
                summary_word_list_col.controls.append(ft.Text("لم يتم لعب أي كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=16))
            else:
                for log_item in words:
                    summary_word_list_col.controls.append(
                        ft.Text(f"- {log_item['word']} ({'✔ تم التخمين' if log_item['correct'] else '✘ تخطي/ممنوعة'})",
                                  color=ft.Colors.GREEN_800 if log_item["correct"] else ft.Colors.RED_800,
                                  size=16, text_align=ft.TextAlign.CENTER)
                    )
            summary_word_list_container = ft.Container( # Wrap word list
                content=summary_word_list_col,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=8,
                padding=10,
                width=page.width * 0.9 if page.width else 320,
                alignment=ft.alignment.top_center
            )


            def next_team_taboo_offline(e):
                s["current_team_index"] += 1
                if s["current_team_index"] >= len(s["teams"]):
                    s["current_team_index"] = 0
                    s["round"] += 1
                # Check for game over before starting new round/intro
                if s["round"] > s.get("max_rounds", 3):
                    set_taboo_offline_step("game_over")
                else:
                    set_taboo_offline_step("team_intro_offline")


            offline_main_column.controls.extend([
                ft.Text(f"⏰ انتهى الوقت! فريق: {team_name}", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER), # Larger
                ft.Text("🔤 الكلمات التي ظهرت:", size=22, text_align=ft.TextAlign.CENTER), # Larger
                summary_word_list_container,
                ft.Container(height=10), #Spacer
                ft.ElevatedButton("▶ الفريق التالي / الجولة التالية", on_click=next_team_taboo_offline, width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                ft.ElevatedButton("🏠 العودة للرئيسية", on_click=safe_go_home_taboo_offline, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif s["step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة! النتائج النهائية:", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            
            final_scores_data_taboo = []
            for team, score in sorted(s.get("scores",{}).items(), key=lambda item: item[1], reverse=True):
                final_scores_data_taboo.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(team, weight=ft.FontWeight.BOLD, size=18)),
                    ft.DataCell(ft.Text(f"{float(score):.1f} نقطة", size=18)),
                ]))
            
            if final_scores_data_taboo:
                offline_main_column.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD), numeric=True),
                            ],
                            rows=final_scores_data_taboo,
                            column_spacing=30,
                            data_row_max_height=45,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.8 if page.width else 300,
                        alignment=ft.alignment.center
                    )
                )
            else:
                offline_main_column.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER))

            buttons_game_over_row_taboo = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("🔄 العب مرة أخرى", on_click=reset_taboo_offline_game, col={"xs":12, "sm":6}, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                    ft.ElevatedButton("🏠 العودة للرئيسية", on_click=safe_go_home_taboo_offline, col={"xs":12, "sm":6}, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                ],
                alignment=ft.MainAxisAlignment.CENTER, run_spacing=10, spacing=10
            )
            offline_main_column.controls.append(buttons_game_over_row_taboo)
        else:
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'"))
            offline_main_column.controls.append(ft.ElevatedButton("العودة للرئيسية", on_click=safe_go_home_taboo_offline, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        if page.client_storage: page.update()

    # Correct and Skip buttons are now created within update_taboo_offline_ui when step is "playing_round"

    reset_taboo_offline_game()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=10, vertical=15) # Overall padding
        )
    ]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def taboo_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    page_title = ft.Text(f"لعبة تابو - غرفة: {room_code}", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Larger
    status_text = ft.Text("قيد التحميل...", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Larger
    
    player_list_display_online_taboo = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Renamed and centered
    team_score_display_online_taboo = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Renamed and centered
    action_area_online_taboo = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15, scroll=ft.ScrollMode.ADAPTIVE) # Renamed and increased spacing
    word_card_display_online_taboo = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8) # Renamed and adjusted spacing
    online_timer_display_taboo_control = ft.Text("الوقت: --", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700) # Renamed, larger, colored

    online_main_content_column_taboo = ft.Column( # This is the content for the padded container
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15 # Consistent spacing
    )

    def log_debug_online_taboo(msg): # Renamed
        print(f"[Taboo_Online_Client:{current_player_name} session:{page.session_id}] {msg}")

    def update_ui_from_server_state_online_taboo(room_state_from_server):
        if not page.client_storage:
            log_debug_online_taboo("Page detached, skipping UI update.")
            return

        gs = room_state_from_server.get("game_state",{})
        players_in_room = room_state_from_server.get("players",{})
        teams_data = gs.get("teams_online", {})
        current_player_data = players_in_room.get(current_player_name, {})
        is_host = current_player_data.get("is_host", False)
        my_team_name = current_player_data.get("team_name")
        current_phase = gs.get("phase", "LOBBY")

        log_debug_online_taboo(f"Taboo online UI update, phase: {current_phase}, My Team: {my_team_name}")
        status_text.value = gs.get("status_message", "...")
        status_text.text_align = ft.TextAlign.CENTER

        player_list_display_online_taboo.controls.clear()
        player_list_display_online_taboo.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=18))
        for p_name, p_data in players_in_room.items():
            team_tag = f" (فريق {p_data.get('team_name', '؟')})" if p_data.get('team_name') else ""
            player_list_display_online_taboo.controls.append(
                ft.Text(f"• {p_data.get('name','Unknown')} {'👑' if p_data.get('is_host') else ''}{team_tag}", text_align=ft.TextAlign.CENTER, size=16)
            )

        team_score_display_online_taboo.controls.clear()
        team_score_display_online_taboo.controls.append(ft.Text("📊 النقاط:", weight=ft.FontWeight.BOLD, size=20, text_align=ft.TextAlign.CENTER))
        if teams_data:
            for team_name_iter, team_info in teams_data.items():
                team_score_display_online_taboo.controls.append(ft.Text(f"فريق {team_name_iter}: {float(team_info.get('score',0.0)):.1f}", size=18, text_align=ft.TextAlign.CENTER))
        else:
            team_score_display_online_taboo.controls.append(ft.Text("لم يتم تحديد الفرق بعد.", text_align=ft.TextAlign.CENTER))

        action_area_online_taboo.controls.clear()
        word_card_display_online_taboo.controls.clear()
        word_card_display_online_taboo.visible = False
        timer_val_taboo = gs.get('timer_value', '--') # Renamed
        online_timer_display_taboo_control.value = f"⏳ الوقت: {timer_val_taboo}" if gs.get("round_active") else "الوقت: --"
        online_timer_display_taboo_control.visible = gs.get("round_active", False)


        if current_phase == "LOBBY":
            action_area_online_taboo.controls.append(ft.Text("في انتظار الهوست لتحديد الفرق وبدء اللعبة.", text_align=ft.TextAlign.CENTER, size=18)) # Larger
            if is_host:
                team_inputs_host_taboo = [] # Renamed
                for i in range(2):
                    tf_container_online = ft.Container(
                        content=ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8),
                        width=page.width * 0.8 if page.width else 280,
                        alignment=ft.alignment.center
                    )
                    team_inputs_host_taboo.append(tf_container_online.content) # Store TextField
                    action_area_online_taboo.controls.append(tf_container_online)

                def setup_taboo_teams_host(e):
                    team_names = [tf.value.strip() for tf in team_inputs_host_taboo if tf.value.strip()]
                    if len(team_names) != 2 or any(not name for name in team_names):
                        page.snack_bar = ft.SnackBar(ft.Text("تحتاج لإدخال اسمي الفريقين بالضبط وبشكل صحيح."),open=True)
                        if page.client_storage: page.update()
                        return
                    if len(set(team_names)) != len(team_names):
                        page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب أن تكون فريدة."),open=True)
                        if page.client_storage: page.update()
                        return
                    send_action_fn("SETUP_TABOO_GAME_HOST", {"team_names": team_names})
                action_area_online_taboo.controls.append(ft.ElevatedButton("🏆 إعداد فرق تابو والبدء", on_click=setup_taboo_teams_host, width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Wider

        elif current_phase == "TEAMS_SET_TABOO":
            action_area_online_taboo.controls.append(ft.Text("تم تحديد فرق تابو!", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            if teams_data:
                for team_name_iter, team_info in teams_data.items():
                    player_names_in_team = ", ".join(team_info.get("players", []))
                    action_area_online_taboo.controls.append(ft.Text(f"فريق {team_name_iter}: {player_names_in_team}", text_align=ft.TextAlign.CENTER, size=16)) # Larger
            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("▶️ بدء الدور الأول لتابو", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN_TABOO"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                action_area_online_taboo.controls.append(ft.Text("في انتظار الهوست لبدء الدور الأول...", text_align=ft.TextAlign.CENTER, size=16))

        elif current_phase == "TEAM_INTRO_TABOO":
            acting_team = gs.get("current_acting_team_online")
            current_actor = gs.get("current_actor_name_online")
            action_area_online_taboo.controls.append(ft.Text(f"استعداد فريق: {acting_team}", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            if current_player_name == current_actor:
                action_area_online_taboo.controls.append(ft.Text("أنت من سيصف الكلمات هذه الجولة!", size=20, color=ft.Colors.GREEN_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Bolder
                action_area_online_taboo.controls.append(ft.ElevatedButton("👀 عرض الكلمة والبدء", on_click=lambda e: send_action_fn("ACTOR_READY_START_ROUND_TABOO"), width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Larger
            elif my_team_name == acting_team:
                action_area_online_taboo.controls.append(ft.Text(f"{current_actor} من فريقكم سيصف الكلمات. استعدوا للتخمين!", size=18, text_align=ft.TextAlign.CENTER))
            else:
                action_area_online_taboo.controls.append(ft.Text(f"{current_actor} من فريق {acting_team} سيصف الكلمات.", size=18, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ACTING_ROUND_TABOO":
            word_card_display_online_taboo.visible = True
            current_actor = gs.get("current_actor_name_online")
            current_word_obj = gs.get("current_word_obj_online", {})
            acting_team_online = gs.get("current_acting_team_online") # Renamed

            secret_word_text = current_word_obj.get("secret", "تحميل...")
            if current_player_name != current_actor and my_team_name == acting_team_online:
                secret_word_text = "الكلمة السرية: ؟؟؟"

            word_card_display_online_taboo.controls.append(ft.Text("الكلمة لوصفها:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            word_card_display_online_taboo.controls.append(
                ft.Text(secret_word_text, size=34, weight=ft.FontWeight.BOLD, # Larger
                        color=(ft.Colors.BLUE_ACCENT_700 if current_player_name == current_actor or my_team_name != acting_team_online else ft.Colors.BLUE_GREY_300), # Adjusted color for guesser
                        text_align=ft.TextAlign.CENTER, selectable=True
                       )
            )

            if current_player_name == current_actor or (my_team_name and my_team_name != acting_team_online):
                word_card_display_online_taboo.controls.append(ft.Container(height=10)) # Spacer
                word_card_display_online_taboo.controls.append(
                     ft.Row(
                        [
                            ft.Icon(ft.Icons.BLOCK_ROUNDED, color=ft.Colors.RED_ACCENT_700, size=28),
                            ft.Text("كلمات ممنوعة:", size=22, color=ft.Colors.RED_ACCENT_700, weight=ft.FontWeight.BOLD) # Larger
                        ],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=8
                    )
                )
                forbidden_col_online = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3) # Renamed
                for fb_word in current_word_obj.get("forbidden", []):
                    forbidden_col_online.controls.append(ft.Text(f"• {fb_word}", size=18, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER)) # Larger
                word_card_display_online_taboo.controls.append(forbidden_col_online)

            if current_player_name == current_actor:
                action_area_online_taboo.controls.append(
                    ft.Text(f"الجولة {gs.get('current_game_round_online','?')} - دورك للوصف!", size=18, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER)
                )
                actor_buttons_row_online = ft.ResponsiveRow( # Renamed
                    [
                        ft.ElevatedButton("✅ خمنوها صح!", key="taboo_correct", on_click=lambda e: send_action_fn("WORD_GUESSED_CORRECT_TABOO"), col={"xs":6}, height=70, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                        ft.ElevatedButton("⏭ تخطي / ممنوعة", key="taboo_skip", on_click=lambda e: send_action_fn("SKIP_WORD_TABOO"), col={"xs":6}, height=70, bgcolor=ft.Colors.ORANGE_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=15
                )
                action_area_online_taboo.controls.append(actor_buttons_row_online)
            elif my_team_name == acting_team_online:
                 action_area_online_taboo.controls.append(ft.Text(f"{current_actor} يصف الكلمات. استعدوا للتخمين!", size=18, italic=True, text_align=ft.TextAlign.CENTER)) # Larger
            else:
                action_area_online_taboo.controls.append(ft.Text("راقبوا استخدام الكلمات الممنوعة!", size=18, italic=True, text_align=ft.TextAlign.CENTER)) # Larger


        elif current_phase == "ROUND_SUMMARY_TABOO":
            summary_data = gs.get("summary_for_ui_taboo", {})
            summary_team = summary_data.get("team_name", "فريق")
            summary_round_num = summary_data.get("round_number", gs.get("current_game_round_online","?"))
            summary_words = summary_data.get("words", [])

            summary_word_list_col_online = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=150) # Renamed, max height
            if not summary_words:
                summary_word_list_col_online.controls.append(ft.Text("لم يتم لعب أي كلمات في هذا الدور.", italic=True, text_align=ft.TextAlign.CENTER, size=16))
            else:
                for log_item_online_sum in summary_words: # Renamed
                    summary_word_list_col_online.controls.append(
                        ft.Text(f"- {log_item_online_sum['word']} ({'✔ تم التخمين' if log_item_online_sum['correct'] else '✘ تخطي/ممنوعة'})",
                                  color=ft.Colors.GREEN_800 if log_item_online_sum["correct"] else ft.Colors.RED_800,
                                  size=16, text_align=ft.TextAlign.CENTER)
                    )
            summary_word_list_container_online = ft.Container( # Wrap word list
                content=summary_word_list_col_online,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=8,
                padding=10,
                width=page.width * 0.9 if page.width else 320,
                alignment=ft.alignment.top_center
            )

            action_area_online_taboo.controls.extend([
                ft.Text(f"⏰ ملخص دور فريق: {summary_team} (الجولة {summary_round_num})", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER), # Larger
                ft.Text("🔤 الكلمات:", size=22, text_align=ft.TextAlign.CENTER), # Larger
                summary_word_list_container_online,
                ft.Container(height=10) # Spacer
            ])

            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("▶ الدور التالي / الجولة التالية", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN_TABOO"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                action_area_online_taboo.controls.append(ft.Text("في انتظار الهوست للمتابعة...", text_align=ft.TextAlign.CENTER, size=16))

        elif current_phase == "GAME_OVER_TABOO":
            action_area_online_taboo.controls.append(ft.Text("🏁 انتهت لعبة تابو! النتائج النهائية:", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            
            final_scores_data_taboo_online = [] # Renamed
            if teams_data:
                sorted_teams = sorted(teams_data.items(), key=lambda item: item[1].get('score',0.0), reverse=True)
                for team_name_iter, team_info_iter in sorted_teams:
                    final_scores_data_taboo_online.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(team_name_iter, weight=ft.FontWeight.BOLD, size=18)),
                        ft.DataCell(ft.Text(f"{float(team_info_iter.get('score',0.0)):.1f} نقطة", size=18)),
                    ]))
            
            if final_scores_data_taboo_online:
                action_area_online_taboo.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD), numeric=True),
                            ],
                            rows=final_scores_data_taboo_online,
                            column_spacing=30,
                            data_row_max_height=45,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.8 if page.width else 300,
                        alignment=ft.alignment.center
                    )
                )
            else:
                 action_area_online_taboo.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER))


            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("🔄 العب تابو مرة أخرى بنفس الفرق", on_click=lambda e: send_action_fn("RESTART_GAME_SAME_TEAMS_TABOO"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Wider

        if page.client_storage:
            log_debug_online_taboo(f"EXECUTING page.update() for Taboo phase {current_phase}")
            page.update()

    def on_server_message_online_taboo(*args_received):
        if not page.client_storage: return
        # log_debug_online_taboo(f"TABOO_PUBSUB_RAW_ARGS_RECEIVED: {args_received}")
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
        # log_debug_online_taboo(f"Processing Taboo PubSub: Type: {msg_type}")
        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online_taboo(room_state)
        elif msg_type == "ACTION_ERROR":
            error_msg = msg_data.get("message", "حدث خطأ في تابو.")
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text(error_msg, text_align=ft.TextAlign.CENTER), open=True)
                page.update()

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online_taboo)
    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data: update_ui_from_server_state_online_taboo(initial_room_data)
    else: status_text.value = "خطأ في تحميل بيانات الغرفة."


    # Construct main online layout
    online_main_content_column_taboo.controls.extend([
        ft.Row(
            [page_title, ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=30)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=5, thickness=1.5),
        status_text,
        online_timer_display_taboo_control, # Add the timer here
        ft.Divider(height=5, thickness=1.5),
        word_card_display_online_taboo,
        ft.ResponsiveRow(
            [
                ft.Container( # Player List & Team Scores Container
                    content=ft.Column([
                        player_list_display_online_taboo,
                        ft.Divider(height=10),
                        team_score_display_online_taboo
                    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.6, ft.Colors.OUTLINE)),
                    border_radius=10,
                    col={"xs": 12, "md": 4},
                    margin=ft.margin.only(bottom=15 if page.width and page.width < 768 else 0)
                ),
                ft.Container( # Main Action Area Container
                    content=action_area_online_taboo,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    col={"xs": 12, "md": 8},
                    alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            alignment=ft.MainAxisAlignment.SPACE_AROUND
        )
    ])
    return [
        ft.Container( # Outermost container for padding
            content=online_main_content_column_taboo,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=10, vertical=10)
        )
    ]


# --- GAME ENTRY POINT ---
def taboo_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return taboo_offline_logic(page, go_home_fn)
    else:
        if not all([room_code, player_name, game_rooms_ref is not None]): # Check game_rooms_ref properly
             return [ft.Container(content=ft.Text("خطأ في تحميل لعبة تابو أونلاين."), alignment=ft.alignment.center, expand=True)]

        def send_taboo_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "taboo", action_type, payload or {})

        return taboo_online_logic(page, go_home_fn, send_taboo_action_to_server_wrapper, room_code, player_name, game_rooms_ref)