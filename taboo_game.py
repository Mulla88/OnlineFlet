# taboo_game.py
import flet as ft
import random
import threading
import time
from taboo_words import WORD_BANK

# --- OFFLINE MODE LOGIC ---
_taboo_offline_state = {}

def taboo_offline_logic(page: ft.Page, go_home_fn):
    team_name_fields_offline_controls = []
    word_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=5 # Increased spacing for horizontal emphasis
    )
    score_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=3
    )
    # Increased sizes for horizontal view emphasis
    timer_text_offline_control = ft.Text("الوقت: 60", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700)
    last_round_warning_offline_text = ft.Text("", size=16, color=ft.Colors.RED_700, visible=False, weight=ft.FontWeight.BOLD)

    offline_title_bar_taboo = ft.Row(
        [
            ft.Text("🚫 لعبة تابو (أوفلاين)", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=lambda e: safe_go_home_taboo_offline(),
                icon_size=28
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    offline_main_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12
    )

    def destroy_taboo_offline_state():
        event = _taboo_offline_state.get("stop_timer_event")
        if isinstance(event, threading.Event):
            event.set()
            time.sleep(0.1)
        _taboo_offline_state.clear()

    def reset_taboo_offline_game(e=None):
        destroy_taboo_offline_state()
        _taboo_offline_state.update({
            "teams": [], "scores": {}, "current_team_index": 0, "used_words_secrets": set(),
            "word_log": [], "current_word_obj": None, "game_started": False,
            "round": 1, "step": "input_teams",
            "stop_timer_event": threading.Event(),
            "max_rounds": 3, "round_duration": 60,
            "current_round_summary_data": {}
        })
        update_taboo_offline_ui()

    def get_new_taboo_word_offline():
        remaining = [w for w in WORD_BANK if isinstance(w, dict) and w.get("secret") and w["secret"] not in _taboo_offline_state.get("used_words_secrets", set())]
        if not remaining:
            if not WORD_BANK:
                if page.client_storage:
                    page.snack_bar = ft.SnackBar(ft.Text("قائمة الكلمات فارغة!"), open=True)
                    page.update()
                return None
            _taboo_offline_state["used_words_secrets"] = set()
            remaining = [w for w in WORD_BANK if isinstance(w, dict) and w.get("secret")]
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("تم إعادة تعيين الكلمات المستخدمة."), open=True)
                page.update()
            if not remaining:
                return None
        word_obj = random.choice(remaining)
        _taboo_offline_state.setdefault("used_words_secrets", set()).add(word_obj["secret"])
        return word_obj

    def _get_taboo_word_display_content_offline(): # For Horizontal View
        controls = []
        word_obj = _taboo_offline_state.get("current_word_obj")
        if word_obj:
            controls.append(ft.Text(f"الكلمة السرية:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            controls.append(ft.Text(f"{word_obj['secret']}", size=36, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER, selectable=True)) # Much Larger
            controls.append(ft.Container(height=8)) # Increased spacer
            controls.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.BLOCK_ROUNDED, color=ft.Colors.RED_ACCENT_700, size=24), # Larger
                        ft.Text("كلمات ممنوعة:", size=20, color=ft.Colors.RED_ACCENT_700, weight=ft.FontWeight.BOLD) # Larger
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=5
                )
            )
            # For horizontal, maybe a Row of Texts or a Wrap for forbidden words if many
            forbidden_words_display = ft.Wrap( # Use Wrap for better horizontal layout
                spacing=8, run_spacing=4, alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
            for w_forbidden in word_obj.get("forbidden", []):
                forbidden_words_display.controls.append(
                    ft.Chip( # Use Chip for better visual separation
                        label=ft.Text(f"{w_forbidden}", color=ft.Colors.WHITE, size=16, weight=ft.FontWeight.BOLD), # Larger
                        bgcolor=ft.Colors.RED_700,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4)
                    )
                )
            controls.append(forbidden_words_display)
        elif _taboo_offline_state.get("current_word_obj") is None and _taboo_offline_state.get("step") == "playing_round":
             controls.append(ft.Text("انتهت الكلمات!", size=24, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
        return controls

    def _get_taboo_score_display_content_offline():
        controls = []
        if _taboo_offline_state.get("scores"):
            controls.append(ft.Text("📊 النقاط الحالية:", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            for team, score in _taboo_offline_state.get("scores",{}).items():
                controls.append(ft.Text(f"فريق {team}: {float(score):.1f} نقطة", size=16, text_align=ft.TextAlign.CENTER)) # Larger
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
                        end_taboo_round_offline(None)
                    return
                time.sleep(1)
                if stop_event.is_set(): return
        threading.Thread(target=run_timer, daemon=True).start()

    def start_taboo_round_offline():
        s = _taboo_offline_state
        if s["round"] > s.get("max_rounds", 3):
            set_taboo_offline_step("game_over")
            return
        s["step"] = "playing_round"
        s["current_word_obj"] = get_new_taboo_word_offline()
        update_taboo_offline_ui()
        if s["current_word_obj"]:
            start_taboo_timer_offline()
        else:
            timer_text_offline_control.value = "لا توجد كلمات لبدء الجولة!"
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
        if s["step"] == "playing_round": update_taboo_offline_ui()
        if not s["current_word_obj"] and page.client_storage and not s["stop_timer_event"].is_set():
             end_taboo_round_offline()

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
        if s["step"] == "playing_round": update_taboo_offline_ui()
        if not s["current_word_obj"] and page.client_storage and not s["stop_timer_event"].is_set():
            end_taboo_round_offline()

    def start_taboo_game_from_inputs_offline(e):
        s = _taboo_offline_state
        team_names = [tf.value.strip() for tf in team_name_fields_offline_controls if tf.value.strip()]
        if len(team_names) != 2 or any(not name for name in team_names):
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("❗ تحتاج لإدخال اسمي الفريقين بشكل صحيح."), open=True)
                page.update()
            return
        if len(set(team_names)) != len(team_names):
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء الفرق يجب أن تكون فريدة."), open=True)
                page.update()
            return
        s["teams"] = team_names
        s["scores"] = {team: 0.0 for team in team_names}
        s["game_started"] = True
        s["round"] = 1
        s["current_team_index"] = 0
        s["used_words_secrets"] = set()
        s["word_log"] = []
        set_taboo_offline_step("team_intro_offline")

    def set_taboo_offline_step(step_name):
        _taboo_offline_state["step"] = step_name
        update_taboo_offline_ui()

    def safe_go_home_taboo_offline(e=None):
        destroy_taboo_offline_state()
        go_home_fn()

    def update_taboo_offline_ui():
        nonlocal team_name_fields_offline_controls
        if not page.client_storage: return

        offline_main_column.controls.clear()
        offline_main_column.controls.append(offline_title_bar_taboo)
        offline_main_column.controls.append(ft.Divider(height=1, thickness=0.5))
        s = _taboo_offline_state

        if s["step"] == "input_teams":
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء الفرق (فريقان):", size=22, text_align=ft.TextAlign.CENTER))
            team_name_fields_offline_controls.clear()
            for i in range(2):
                tf = ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8, height=50) # Adjusted height
                team_name_fields_offline_controls.append(tf)
                offline_main_column.controls.append(
                    ft.Container(content=tf, width=page.width * 0.7 if page.width else 280, alignment=ft.alignment.center, padding=ft.padding.only(bottom=5)) # Adjusted width
                )
            offline_main_column.controls.append(ft.ElevatedButton("🚀 ابدأ اللعبة", on_click=start_taboo_game_from_inputs_offline, width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        elif s["step"] == "team_intro_offline":
            if not s.get("teams") or s.get("current_team_index", -1) >= len(s["teams"]):
                set_taboo_offline_step("input_teams")
                return
            current_team = s["teams"][s["current_team_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"استعد يا فريق", size=28, text_align=ft.TextAlign.CENTER), # Larger for intro
                ft.Text(f"{current_team}", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_ACCENT_700), # Larger
                ft.Text(f"سيقوم أحد أعضاء فريقكم بوصف الكلمات.", size=20, text_align=ft.TextAlign.CENTER), # Larger
                ft.ElevatedButton(f"🚀 ابدأ الدور {s['round']} لفريق {current_team}",
                                 on_click=lambda e: start_taboo_round_offline(), width=320, height=60, # Larger button
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
                    ft.ElevatedButton("✅ صح", on_click=handle_correct_taboo_offline, col={"xs": 6}, height=45, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Slightly larger buttons
                    ft.ElevatedButton("⏭ تخطي", on_click=handle_skip_taboo_offline, col={"xs": 6}, height=45, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                ],
                alignment=ft.MainAxisAlignment.CENTER, spacing=15 # Increased spacing
            )
            no_word = not s.get("current_word_obj")
            for btn_control in buttons_playing_row.controls:
                if isinstance(btn_control, ft.ElevatedButton):
                    btn_control.disabled = no_word

            offline_main_column.controls.extend([
                ft.Text(f"🎮 الجولة {s['round']} - فريق: {current_team}", size=20, color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD), # Larger
                last_round_warning_offline_text,
                timer_text_offline_control,
                ft.Divider(height=6, thickness=1), # Spacing
                word_display_offline_container,
                ft.Divider(height=6, thickness=1),
                buttons_playing_row,
                ft.Container(height=6),
                ft.ElevatedButton("⏹ إنهاء الدور مبكراً", on_click=end_taboo_round_offline, width=280, height=35, bgcolor=ft.Colors.AMBER_400, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))), # Slightly larger
                ft.Divider(height=6, thickness=1),
                score_display_offline_container,
            ])

        elif s["step"] == "round_summary":
            summary_data = s.get("current_round_summary_data", {})
            team_name = summary_data.get("team", "فريق")
            words = summary_data.get("words", [])

            # For summary, we try to fit more words if possible, or allow scroll.
            # A Wrap layout might be better if word count is high and screen is wide.
            summary_word_list_display = ft.Wrap( # Changed to Wrap
                spacing=8, run_spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
                height=150, # Max height for the wrap area, will scroll if overflows
                scroll=ft.ScrollMode.AUTO
            )

            if not words:
                summary_word_list_display.controls.append(ft.Text("لم يتم لعب أي كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=16)) # Larger
            else:
                for log_item in words:
                    chip_color = ft.Colors.GREEN_100 if log_item["correct"] else ft.Colors.RED_100
                    text_color = ft.Colors.GREEN_900 if log_item["correct"] else ft.Colors.RED_900
                    icon = ft.icons.CHECK_CIRCLE_OUTLINE if log_item["correct"] else ft.icons.CANCEL_OUTLINE
                    summary_word_list_display.controls.append(
                        ft.Chip(
                            leading=ft.Icon(icon, color=text_color),
                            label=ft.Text(f"{log_item['word']}", size=16, color=text_color, weight=ft.FontWeight.BOLD), # Larger text
                            bgcolor=chip_color,
                            padding=ft.padding.symmetric(horizontal=10, vertical=5)
                        )
                    )
            summary_word_list_container = ft.Container(
                content=summary_word_list_display, # Using Wrap now
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=8,
                padding=10,
                width=page.width * 0.9 if page.width else 400, # Wider for horizontal
                alignment=ft.alignment.top_center
            )

            def next_team_taboo_offline(e):
                s["current_team_index"] += 1
                if s["current_team_index"] >= len(s["teams"]):
                    s["current_team_index"] = 0
                    s["round"] += 1
                if s["round"] > s.get("max_rounds", 3):
                    set_taboo_offline_step("game_over")
                else:
                    set_taboo_offline_step("team_intro_offline")

            offline_main_column.controls.extend([
                ft.Text(f"⏰ انتهى الوقت! فريق: {team_name}", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER), # Larger
                ft.Text("🔤 الكلمات التي ظهرت:", size=22, text_align=ft.TextAlign.CENTER), # Larger
                summary_word_list_container,
                ft.Container(height=10),
                ft.ElevatedButton("▶ الفريق التالي / الجولة التالية", on_click=next_team_taboo_offline, width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
            ])

        elif s["step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة! النتائج النهائية:", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            final_scores_data_taboo = []
            for team, score in sorted(s.get("scores",{}).items(), key=lambda item: item[1], reverse=True):
                final_scores_data_taboo.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(team, weight=ft.FontWeight.BOLD, size=18)), # Larger
                    ft.DataCell(ft.Text(f"{float(score):.1f} نقطة", size=18)), # Larger
                ]))
            if final_scores_data_taboo:
                offline_main_column.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD, size=16)), # Larger
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=16), numeric=True), # Larger
                            ],
                            rows=final_scores_data_taboo,
                            column_spacing=30, data_row_max_height=45,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.85 if page.width else 350, # Wider
                        alignment=ft.alignment.center
                    )
                )
            else:
                offline_main_column.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER, size=16)) # Larger
            buttons_game_over_row_taboo = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("🔄 العب مرة أخرى", on_click=reset_taboo_offline_game, col={"xs":12}, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                ],
                alignment=ft.MainAxisAlignment.CENTER, run_spacing=10, spacing=10
            )
            offline_main_column.controls.append(buttons_game_over_row_taboo)
        else:
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'", size=18, color=ft.Colors.RED_700))

        if page.client_storage: page.update()

    reset_taboo_offline_game()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=8, vertical=10)
        )
    ]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def taboo_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    status_text = ft.Text("قيد التحميل...", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    player_list_display_online_taboo = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    team_score_display_online_taboo = ft.Column(spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    action_area_online_taboo = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8, scroll=ft.ScrollMode.ADAPTIVE)
    word_card_display_online_taboo = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5) # Increased spacing
    online_timer_display_taboo_control = ft.Text("الوقت: --", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700) # Larger

    online_main_content_column_taboo = ft.Column( 
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8
    )

    def log_debug_online_taboo(msg): 
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

        status_text.value = gs.get("status_message", "...")
        status_text.text_align = ft.TextAlign.CENTER

        player_list_display_online_taboo.controls.clear()
        player_list_display_online_taboo.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=16)) # Larger
        for p_name, p_data in players_in_room.items():
            team_tag = f" (فريق {p_data.get('team_name', '؟')})" if p_data.get('team_name') else ""
            player_list_display_online_taboo.controls.append(
                ft.Text(f"• {p_data.get('name','Unknown')} {'👑' if p_data.get('is_host') else ''}{team_tag}", text_align=ft.TextAlign.CENTER, size=14)) # Larger

        team_score_display_online_taboo.controls.clear()
        team_score_display_online_taboo.controls.append(ft.Text("📊 النقاط:", weight=ft.FontWeight.BOLD, size=18, text_align=ft.TextAlign.CENTER)) # Larger
        if teams_data:
            for team_name_iter, team_info in teams_data.items():
                team_score_display_online_taboo.controls.append(ft.Text(f"فريق {team_name_iter}: {float(team_info.get('score',0.0)):.1f}", size=16, text_align=ft.TextAlign.CENTER)) # Larger
        else:
            team_score_display_online_taboo.controls.append(ft.Text("لم يتم تحديد الفرق.", text_align=ft.TextAlign.CENTER, size=14))

        action_area_online_taboo.controls.clear()
        word_card_display_online_taboo.controls.clear()
        word_card_display_online_taboo.visible = False
        timer_val_taboo = gs.get('timer_value', '--') 
        online_timer_display_taboo_control.value = f"⏳ الوقت: {timer_val_taboo}" if gs.get("round_active") else "الوقت: --"
        online_timer_display_taboo_control.visible = gs.get("round_active", False)


        if current_phase == "LOBBY":
            action_area_online_taboo.controls.append(ft.Text("الهوست يحدد الفرق ويبدأ اللعبة.", text_align=ft.TextAlign.CENTER, size=16)) # Larger
            if is_host:
                team_inputs_host_taboo = [] 
                for i in range(2):
                    tf_container_online = ft.Container(
                        content=ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8, height=50), # Adjusted
                        width=page.width * 0.7 if page.width else 260, alignment=ft.alignment.center, padding=ft.padding.only(bottom=5) # Adjusted
                    )
                    team_inputs_host_taboo.append(tf_container_online.content) 
                    action_area_online_taboo.controls.append(tf_container_online)

                def setup_taboo_teams_host(e):
                    team_names = [tf.value.strip() for tf in team_inputs_host_taboo if tf.value.strip()]
                    if len(team_names) != 2 or any(not name for name in team_names):
                        if page.client_storage:
                            page.snack_bar = ft.SnackBar(ft.Text("تحتاج لإدخال اسمي الفريقين بشكل صحيح."),open=True)
                            page.update()
                        return
                    if len(set(team_names)) != len(team_names):
                        if page.client_storage:
                            page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب أن تكون فريدة."),open=True)
                            page.update()
                        return
                    send_action_fn("SETUP_TABOO_GAME_HOST", {"team_names": team_names})
                action_area_online_taboo.controls.append(ft.ElevatedButton("🏆 إعداد فرق والبدء", on_click=setup_taboo_teams_host, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Larger

        elif current_phase == "TEAMS_SET_TABOO":
            action_area_online_taboo.controls.append(ft.Text("تم تحديد فرق تابو!", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            if teams_data:
                for team_name_iter, team_info in teams_data.items():
                    player_names_in_team = ", ".join(team_info.get("players", []))
                    action_area_online_taboo.controls.append(ft.Text(f"فريق {team_name_iter}: {player_names_in_team}", text_align=ft.TextAlign.CENTER, size=16)) # Larger
            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("▶️ بدء الدور الأول", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN_TABOO"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Larger
            else:
                action_area_online_taboo.controls.append(ft.Text("انتظار الهوست لبدء الدور...", text_align=ft.TextAlign.CENTER, size=16)) # Larger

        elif current_phase == "TEAM_INTRO_TABOO":
            acting_team = gs.get("current_acting_team_online")
            current_actor = gs.get("current_actor_name_online")
            action_area_online_taboo.controls.append(ft.Text(f"استعداد فريق: {acting_team}", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            if current_player_name == current_actor:
                action_area_online_taboo.controls.append(ft.Text("أنت ستصف الكلمات!", size=20, color=ft.Colors.GREEN_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Larger
                action_area_online_taboo.controls.append(ft.ElevatedButton("👀 عرض الكلمة والبدء", on_click=lambda e: send_action_fn("ACTOR_READY_START_ROUND_TABOO"), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Larger
            elif my_team_name == acting_team:
                action_area_online_taboo.controls.append(ft.Text(f"{current_actor} سيصف. استعدوا للتخمين!", size=18, text_align=ft.TextAlign.CENTER)) # Larger
            else:
                action_area_online_taboo.controls.append(ft.Text(f"{current_actor} من فريق {acting_team} سيصف.", size=18, text_align=ft.TextAlign.CENTER)) # Larger

        elif current_phase == "ACTING_ROUND_TABOO": # For Horizontal View
            word_card_display_online_taboo.visible = True
            current_actor = gs.get("current_actor_name_online")
            current_word_obj = gs.get("current_word_obj_online", {})
            acting_team_online = gs.get("current_acting_team_online")

            secret_word_text = current_word_obj.get("secret", "تحميل...")
            if current_player_name != current_actor and my_team_name == acting_team_online:
                secret_word_text = "الكلمة السرية: ؟؟؟"

            word_card_display_online_taboo.controls.append(ft.Text("الكلمة:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            word_card_display_online_taboo.controls.append(
                ft.Text(secret_word_text, size=38, weight=ft.FontWeight.BOLD, # Much Larger
                        color=(ft.Colors.BLUE_ACCENT_700 if current_player_name == current_actor or my_team_name != acting_team_online else ft.Colors.BLUE_GREY_300), 
                        text_align=ft.TextAlign.CENTER, selectable=True
                       )
            )

            if current_player_name == current_actor or (my_team_name and my_team_name != acting_team_online):
                word_card_display_online_taboo.controls.append(ft.Container(height=8)) # Increased spacer
                word_card_display_online_taboo.controls.append(
                     ft.Row(
                        [
                            ft.Icon(ft.Icons.BLOCK_ROUNDED, color=ft.Colors.RED_ACCENT_700, size=24), # Larger
                            ft.Text("ممنوع:", size=20, color=ft.Colors.RED_ACCENT_700, weight=ft.FontWeight.BOLD) # Larger
                        ],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=5 # Increased
                    )
                )
                forbidden_wrap_online = ft.Wrap( # Use Wrap for horizontal
                    spacing=10, run_spacing=5, alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
                for fb_word in current_word_obj.get("forbidden", []):
                     forbidden_wrap_online.controls.append(
                        ft.Chip(
                            label=ft.Text(f"{fb_word}", size=18, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), # Larger
                            bgcolor=ft.Colors.RED_700,
                            padding=ft.padding.symmetric(horizontal=12,vertical=5)
                        )
                    )
                word_card_display_online_taboo.controls.append(forbidden_wrap_online)

            if current_player_name == current_actor:
                action_area_online_taboo.controls.append(
                    ft.Text(f"ج {gs.get('current_game_round_online','?')}: دورك للوصف!", size=16, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER) # Larger
                )
                actor_buttons_row_online = ft.ResponsiveRow( 
                    [
                        ft.ElevatedButton("✅ صح", on_click=lambda e: send_action_fn("WORD_GUESSED_CORRECT_TABOO"), col={"xs":6}, height=45, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Larger buttons
                        ft.ElevatedButton("⏭ تخطي", on_click=lambda e: send_action_fn("SKIP_WORD_TABOO"), col={"xs":6}, height=45, bgcolor=ft.Colors.ORANGE_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=12 # Increased spacing
                )
                action_area_online_taboo.controls.append(actor_buttons_row_online)
            elif my_team_name == acting_team_online:
                 action_area_online_taboo.controls.append(ft.Text(f"{current_actor} يصف. خمنوا!", size=18, italic=True, text_align=ft.TextAlign.CENTER)) # Larger
            else:
                action_area_online_taboo.controls.append(ft.Text("راقبوا الكلمات الممنوعة!", size=18, italic=True, text_align=ft.TextAlign.CENTER)) # Larger

        elif current_phase == "ROUND_SUMMARY_TABOO":
            summary_data = gs.get("summary_for_ui_taboo", {})
            summary_team = summary_data.get("team_name", "فريق")
            summary_round_num = summary_data.get("round_number", gs.get("current_game_round_online","?"))
            summary_words = summary_data.get("words", [])

            summary_word_list_display_online = ft.Wrap( # Changed to Wrap
                spacing=10, run_spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
                height=180, # Increased height, allow scroll if needed
                scroll=ft.ScrollMode.AUTO
            )
            if not summary_words:
                summary_word_list_display_online.controls.append(ft.Text("لم يتم لعب أي كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=16)) # Larger
            else:
                for log_item_online_sum in summary_words: 
                    chip_color_sum = ft.Colors.GREEN_100 if log_item_online_sum["correct"] else ft.Colors.RED_100
                    text_color_sum = ft.Colors.GREEN_900 if log_item_online_sum["correct"] else ft.Colors.RED_900
                    icon_sum = ft.icons.CHECK_CIRCLE_OUTLINE if log_item_online_sum["correct"] else ft.icons.CANCEL_OUTLINE
                    summary_word_list_display_online.controls.append(
                        ft.Chip(
                            leading=ft.Icon(icon_sum, color=text_color_sum),
                            label=ft.Text(f"{log_item_online_sum['word']}", size=18, color=text_color_sum, weight=ft.FontWeight.BOLD), # Larger
                            bgcolor=chip_color_sum,
                            padding=ft.padding.symmetric(horizontal=12, vertical=6)
                        )
                    )
            summary_word_list_container_online = ft.Container( 
                content=summary_word_list_display_online,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=8, padding=10,
                width=page.width * 0.9 if page.width else 450, # Wider
                alignment=ft.alignment.top_center
            )

            action_area_online_taboo.controls.extend([
                ft.Text(f"⏰ ملخص دور فريق: {summary_team} (ج {summary_round_num})", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER), # Larger
                ft.Text("🔤 الكلمات:", size=20, text_align=ft.TextAlign.CENTER), # Larger
                summary_word_list_container_online,
                ft.Container(height=10)
            ])
            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("▶ الدور التالي", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN_TABOO"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                action_area_online_taboo.controls.append(ft.Text("انتظار الهوست للمتابعة...", text_align=ft.TextAlign.CENTER, size=16)) # Larger

        elif current_phase == "GAME_OVER_TABOO":
            action_area_online_taboo.controls.append(ft.Text("🏁 انتهت لعبة تابو!", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger
            final_scores_data_taboo_online = [] 
            if teams_data:
                sorted_teams = sorted(teams_data.items(), key=lambda item: item[1].get('score',0.0), reverse=True)
                for team_name_iter, team_info_iter in sorted_teams:
                    final_scores_data_taboo_online.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(team_name_iter, weight=ft.FontWeight.BOLD, size=18)), # Larger
                        ft.DataCell(ft.Text(f"{float(team_info_iter.get('score',0.0)):.1f}", size=18)), # Larger
                    ]))
            if final_scores_data_taboo_online:
                action_area_online_taboo.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD, size=16)), # Larger
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=16), numeric=True), # Larger
                            ],
                            rows=final_scores_data_taboo_online,
                            column_spacing=25, data_row_max_height=40,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.85 if page.width else 350, # Wider
                        alignment=ft.alignment.center
                    )
                )
            else:
                 action_area_online_taboo.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER, size=16)) # Larger
            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: send_action_fn("RESTART_GAME_SAME_TEAMS_TABOO"), width=300, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Larger

        if page.client_storage: page.update()

    def on_server_message_online_taboo(*args_received):
        if not page.client_storage: return
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
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

    online_main_content_column_taboo.controls.extend([
        ft.Row(
            [
                ft.Text(f"🚫 تابو - غرفة: {room_code}", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
                ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=28)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=1, thickness=0.5),
        status_text,
        online_timer_display_taboo_control, 
        ft.Divider(height=3, thickness=1),
        word_card_display_online_taboo,
        ft.ResponsiveRow(
            [
                ft.Container( 
                    content=ft.Column([
                        player_list_display_online_taboo,
                        ft.Divider(height=3),
                        team_score_display_online_taboo
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=8, border=ft.border.all(1, ft.Colors.with_opacity(0.4, ft.Colors.OUTLINE)),
                    border_radius=8, col={"xs": 12, "md": 4},
                    margin=ft.margin.only(bottom=8 if page.width and page.width < 768 else 0, top=5)
                ),
                ft.Container( 
                    content=action_area_online_taboo,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    col={"xs": 12, "md": 8}, alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START, alignment=ft.MainAxisAlignment.SPACE_AROUND,
            spacing=5, run_spacing=5 # Spacing between the two main containers if they wrap
        )
    ])
    return [
        ft.Container( 
            content=online_main_content_column_taboo,
            expand=True, alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=6, vertical=6)
        )
    ]

# --- GAME ENTRY POINT ---
def taboo_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return taboo_offline_logic(page, go_home_fn)
    else:
        if not all([room_code, player_name, game_rooms_ref is not None]): 
             return [ft.Container(content=ft.Text("خطأ في تحميل لعبة تابو أونلاين."), alignment=ft.alignment.center, expand=True)]
        def send_taboo_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "taboo", action_type, payload or {})
        return taboo_online_logic(page, go_home_fn, send_taboo_action_to_server_wrapper, room_code, player_name, game_rooms_ref)