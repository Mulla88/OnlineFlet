import flet as ft
import random
import threading
import time
# Assuming taboo_words.py is in the same directory or accessible
from taboo_words import WORD_BANK

# --- Sizing Constants (Global for both modes) ---
FONT_SIZE_NORMAL = 14
FONT_SIZE_MEDIUM = 16
FONT_SIZE_LARGE = 18
FONT_SIZE_XLARGE = 20
FONT_SIZE_TITLE = 22
FONT_SIZE_SECTION_TITLE = 20
FONT_SIZE_SECRET_WORD = 30
FONT_SIZE_FORBIDDEN = 16
BUTTON_HEIGHT_NORMAL = 40
BUTTON_HEIGHT_LARGE = 50
BUTTON_HEIGHT_SMALL = 30
CONTAINER_PADDING_NORMAL = ft.padding.symmetric(horizontal=5, vertical=3)
INPUT_HEIGHT = 45 # For TextFields
STANDARD_BORDER_RADIUS = 8
STANDARD_ICON_SIZE = 22
TITLE_ICON_SIZE = 26

# --- OFFLINE MODE LOGIC --- (Same as your last version, sizing constants applied)
_taboo_offline_state = {}

def taboo_offline_logic(page: ft.Page, go_home_fn):
    team_name_fields_offline_controls = []
    word_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=3
    )
    score_display_offline_container = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=2
    )
    timer_text_offline_control = ft.Text("الوقت: 60", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700)
    last_round_warning_offline_text = ft.Text("", size=FONT_SIZE_MEDIUM, color=ft.Colors.RED_700, visible=False, weight=ft.FontWeight.BOLD)

    offline_title_bar_taboo = ft.Row(
        [
            ft.Text("🚫 لعبة تابو (أوفلاين)", size=FONT_SIZE_TITLE, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=lambda e: safe_go_home_taboo_offline(),
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

    def _get_taboo_word_display_content_offline():
        controls = []
        word_obj = _taboo_offline_state.get("current_word_obj")
        if word_obj:
            controls.append(ft.Text(f"الكلمة السرية:", size=FONT_SIZE_SECTION_TITLE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            controls.append(ft.Text(f"{word_obj['secret']}", size=FONT_SIZE_SECRET_WORD, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER, selectable=True))
            controls.append(ft.Container(height=5))
            controls.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.BLOCK_ROUNDED, color=ft.Colors.RED_ACCENT_700, size=STANDARD_ICON_SIZE),
                        ft.Text("كلمات ممنوعة:", size=FONT_SIZE_LARGE, color=ft.Colors.RED_ACCENT_700, weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=3
                )
            )
            forbidden_list_col = ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2
            )
            for w_forbidden in word_obj.get("forbidden", []):
                forbidden_list_col.controls.append(
                    ft.Text(f"• {w_forbidden}", color=ft.Colors.RED_700, size=FONT_SIZE_FORBIDDEN, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
                )
            controls.append(forbidden_list_col)
        elif _taboo_offline_state.get("current_word_obj") is None and _taboo_offline_state.get("step") == "playing_round":
             controls.append(ft.Text("انتهت الكلمات!", size=FONT_SIZE_XLARGE, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
        return controls

    def _get_taboo_score_display_content_offline():
        controls = []
        if _taboo_offline_state.get("scores"):
            controls.append(ft.Text("📊 النقاط الحالية:", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            for team, score in _taboo_offline_state.get("scores",{}).items():
                controls.append(ft.Text(f"فريق {team}: {float(score):.1f} نقطة", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))
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
            current_time = duration
            while current_time >= 0:
                if not page.client_storage or stop_event.is_set(): return
                timer_text_offline_control.value = f"⏳ الوقت المتبقي: {current_time} ثانية"
                if page.client_storage: timer_text_offline_control.update()
                if current_time == 0:
                    if not stop_event.is_set() and page.client_storage:
                        page.run_thread(end_taboo_round_offline, None)
                    return
                time.sleep(1)
                if stop_event.is_set(): return
                current_time -=1
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
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء الفرق (فريقان):", size=FONT_SIZE_TITLE, text_align=ft.TextAlign.CENTER))
            team_name_fields_offline_controls.clear()
            for i in range(2):
                tf = ft.TextField(label=f"اسم الفريق {i+1}", text_align=ft.TextAlign.CENTER, border_radius=STANDARD_BORDER_RADIUS, height=INPUT_HEIGHT)
                team_name_fields_offline_controls.append(tf)
                offline_main_column.controls.append(
                    ft.Container(content=tf, width=page.width * 0.7 if page.width and page.width > 400 else 280, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3))
                )
            offline_main_column.controls.append(ft.ElevatedButton("🚀 ابدأ اللعبة", on_click=start_taboo_game_from_inputs_offline, width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))

        elif s["step"] == "team_intro_offline":
            if not s.get("teams") or s.get("current_team_index", -1) >= len(s["teams"]) or s.get("current_team_index", -1) < 0:
                set_taboo_offline_step("input_teams")
                return
            current_team = s["teams"][s["current_team_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"استعد يا فريق", size=FONT_SIZE_XLARGE, text_align=ft.TextAlign.CENTER),
                ft.Text(f"{current_team}", size=FONT_SIZE_XLARGE + 4, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_ACCENT_700),
                ft.Text(f"سيقوم أحد أعضاء فريقكم بوصف الكلمات.", size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(f"🚀 ابدأ الدور {s['round']} لفريق {current_team}",
                                 on_click=lambda e: start_taboo_round_offline(), width=300, height=BUTTON_HEIGHT_LARGE,
                                 style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS)))
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
                    ft.ElevatedButton("✅ صح", on_click=handle_correct_taboo_offline, col={"xs": 6}, height=BUTTON_HEIGHT_NORMAL, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
                    ft.ElevatedButton("⏭ تخطي", on_click=handle_skip_taboo_offline, col={"xs": 6}, height=BUTTON_HEIGHT_NORMAL, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS)))
                ],
                alignment=ft.MainAxisAlignment.CENTER, spacing=10
            )
            no_word = not s.get("current_word_obj")
            for btn_control in buttons_playing_row.controls:
                if isinstance(btn_control, ft.ElevatedButton):
                    btn_control.disabled = no_word

            offline_main_column.controls.extend([
                ft.Text(f"🎮 الجولة {s['round']} - فريق: {current_team}", size=FONT_SIZE_XLARGE, color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD),
                last_round_warning_offline_text,
                timer_text_offline_control,
                ft.Divider(height=3, thickness=1),
                word_display_offline_container,
                ft.Divider(height=3, thickness=1),
                buttons_playing_row,
                ft.Container(height=3),
                ft.ElevatedButton("⏹ إنهاء الدور مبكراً", on_click=end_taboo_round_offline, width=260, height=BUTTON_HEIGHT_SMALL, bgcolor=ft.Colors.AMBER_400, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
                ft.Divider(height=3, thickness=1),
                score_display_offline_container,
            ])

        elif s["step"] == "round_summary":
            summary_data = s.get("current_round_summary_data", {})
            team_name = summary_data.get("team", "فريق")
            words = summary_data.get("words", [])

            summary_word_list_col = ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )

            if not words:
                summary_word_list_col.controls.append(ft.Text("لم يتم لعب أي كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            else:
                for log_item in words:
                    status_text = "✔ تم" if log_item["correct"] else "✘ تخطي"
                    text_color = ft.Colors.GREEN_800 if log_item["correct"] else ft.Colors.RED_800
                    summary_word_list_col.controls.append(
                         ft.Text(f"• {log_item['word']} ({status_text})", size=FONT_SIZE_MEDIUM, color=text_color, weight=ft.FontWeight.NORMAL, text_align=ft.TextAlign.CENTER)
                    )

            summary_scroll_container = ft.Container(
                content=summary_word_list_col,
                height=150,
                width=page.width * 0.85 if page.width and page.width > 400 else 290,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=STANDARD_BORDER_RADIUS,
                padding=8,
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
                ft.Text(f"⏰ انتهى الوقت! فريق: {team_name}", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER),
                ft.Text("🔤 الكلمات التي ظهرت:", size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER),
                summary_scroll_container,
                ft.Container(height=5),
                ft.ElevatedButton("▶ الفريق التالي / الجولة التالية", on_click=next_team_taboo_offline, width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
            ])

        elif s["step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة! النتائج النهائية:", size=FONT_SIZE_XLARGE + 2, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            final_scores_data_taboo = []
            for team, score in sorted(s.get("scores",{}).items(), key=lambda item: item[1], reverse=True):
                final_scores_data_taboo.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(team, weight=ft.FontWeight.BOLD, size=FONT_SIZE_MEDIUM)),
                    ft.DataCell(ft.Text(f"{float(score):.1f} نقطة", size=FONT_SIZE_MEDIUM)),
                ]))
            if final_scores_data_taboo:
                offline_main_column.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL)),
                                ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL), numeric=True),
                            ],
                            rows=final_scores_data_taboo,
                            column_spacing=20, data_row_max_height=35,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                        ),
                        width=page.width * 0.8 if page.width and page.width > 400 else 300,
                        alignment=ft.alignment.center
                    )
                )
            else:
                offline_main_column.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            buttons_game_over_row_taboo = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("🔄 العب مرة أخرى", on_click=reset_taboo_offline_game, col={"xs":12}, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
                ],
                alignment=ft.MainAxisAlignment.CENTER, run_spacing=8, spacing=8
            )
            offline_main_column.controls.append(buttons_game_over_row_taboo)
        else:
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'", size=FONT_SIZE_LARGE, color=ft.Colors.RED_700))

        if page.client_storage: page.update()

    reset_taboo_offline_game()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=5, vertical=5)
        )
    ]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def taboo_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    status_text = ft.Text("قيد التحميل...", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    player_list_display_online_taboo = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    team_score_display_online_taboo = ft.Column(spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    action_area_online_taboo = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5, scroll=ft.ScrollMode.ADAPTIVE)
    word_card_display_online_taboo = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
    online_timer_display_taboo_control = ft.Text("الوقت: --", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT_700)

    # --- Controls for Host LOBBY UI (New Approach) ---
    team_name_input_fields_online_taboo = [
        ft.TextField(label="اسم الفريق 1", text_align=ft.TextAlign.CENTER, border_radius=STANDARD_BORDER_RADIUS, height=INPUT_HEIGHT),
        ft.TextField(label="اسم الفريق 2", text_align=ft.TextAlign.CENTER, border_radius=STANDARD_BORDER_RADIUS, height=INPUT_HEIGHT)
    ]
    player_assignment_dropdowns_online_taboo = {} # To store Dropdown instances {player_name: Dropdown}
    player_assignment_column_container_online_taboo = ft.Container(
        content=ft.Column( # This inner Column will hold the dropdowns
            visible=False, # Start hidden
            spacing=3,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ADAPTIVE,
            # height=150 # Max height for scrollability
        ),
        # width=page.width * 0.8 if page.width and page.width > 400 else 300, # Width for the container of dropdowns
        # border=ft.border.all(1, ft.colors.BLACK26), # Optional border
        # border_radius=STANDARD_BORDER_RADIUS,
        padding=ft.padding.only(top=5, bottom=5)
    )
    confirm_manual_assignment_button_online_taboo = ft.ElevatedButton(
        "✔️ تأكيد التخصيص والبدء",
        visible=False, # Start hidden
        on_click=lambda e: _handle_start_game_online(manual_assignment=True), # Placeholder, will be defined in update_ui
        width=280, height=BUTTON_HEIGHT_LARGE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))
    )
    # --- End Controls for Host LOBBY UI ---

    _initial_ui_build_done = False

    online_main_content_column_taboo = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=5
    )

    def log_debug_online_taboo(msg):
        print(f"[Taboo_Online_Client:{current_player_name} session:{page.session_id}] {msg}")


    def _handle_start_game_online(manual_assignment=False):
        if not page.client_storage: return

        team_names = [tf.value.strip() for tf in team_name_input_fields_online_taboo if tf.value.strip()]
        if len(team_names) != 2 or any(not name for name in team_names):
            page.snack_bar = ft.SnackBar(ft.Text("تحتاج لإدخال اسمي الفريقين بشكل صحيح."), open=True); page.update()
            return
        if len(set(team_names)) != len(team_names):
            page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب أن تكون فريدة."), open=True); page.update()
            return

        payload_to_send = {"team_names": team_names}
        current_players_in_room_keys = list(game_rooms_ref.get(room_code, {}).get("players", {}).keys()) # Get fresh player list

        if manual_assignment:
            payload_to_send["assignment_mode"] = "manual"
            assignments = {}
            team1_player_count = 0
            team2_player_count = 0

            for p_name_key in current_players_in_room_keys:
                dd_widget = player_assignment_dropdowns_online_taboo.get(p_name_key)
                if not dd_widget or not dd_widget.value:
                    page.snack_bar = ft.SnackBar(ft.Text(f"الرجاء تخصيص فريق للاعب {p_name_key}."), open=True); page.update()
                    return
                assignments[p_name_key] = dd_widget.value
                if dd_widget.value == team_names[0]: team1_player_count +=1
                elif dd_widget.value == team_names[1]: team2_player_count +=1
            
            min_players_per_team = 1 if len(current_players_in_room_keys) >= 2 else 0
            if len(current_players_in_room_keys) >= 2 and (team1_player_count < min_players_per_team or team2_player_count < min_players_per_team):
                page.snack_bar = ft.SnackBar(ft.Text("كل فريق يجب أن يحتوي على لاعب واحد على الأقل (إذا كان هناك لاعبان أو أكثر)."), open=True); page.update()
                return
            payload_to_send["assignments"] = assignments
        else: # Random assignment
            payload_to_send["assignment_mode"] = "random"
            if len(current_players_in_room_keys) < 2:
                page.snack_bar = ft.SnackBar(ft.Text("تحتاج للاعبين اثنين على الأقل للتوزيع العشوائي."), open=True); page.update()
                return
        
        send_action_fn("SETUP_TABOO_GAME_HOST", payload_to_send)


    def update_ui_from_server_state_online_taboo(room_state_from_server):
        nonlocal _initial_ui_build_done
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
        player_list_display_online_taboo.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
        for p_name, p_data in players_in_room.items():
            team_tag = f" (فريق {p_data.get('team_name', '؟')})" if p_data.get('team_name') else ""
            player_list_display_online_taboo.controls.append(
                ft.Text(f"• {p_data.get('name','Unknown')} {'👑' if p_data.get('is_host') else ''}{team_tag}", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_NORMAL))

        team_score_display_online_taboo.controls.clear()
        team_score_display_online_taboo.controls.append(ft.Text("📊 النقاط:", weight=ft.FontWeight.BOLD, size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER))
        if teams_data:
            for team_name_iter, team_info_data in teams_data.items():
                team_score_display_online_taboo.controls.append(ft.Text(f"فريق {team_name_iter}: {float(team_info_data.get('score',0.0)):.1f}", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))
        else:
            team_score_display_online_taboo.controls.append(ft.Text("لم يتم تحديد الفرق.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_NORMAL))

        action_area_online_taboo.controls.clear()
        word_card_display_online_taboo.controls.clear()
        word_card_display_online_taboo.visible = False
        timer_val_taboo = gs.get('timer_value', '--')
        online_timer_display_taboo_control.value = f"⏳ الوقت: {timer_val_taboo}" if gs.get("round_active") else "الوقت: --"
        online_timer_display_taboo_control.visible = gs.get("round_active", False)


        if current_phase == "LOBBY":
            action_area_online_taboo.controls.append(ft.Text("الهوست يحدد الفرق ويبدأ اللعبة.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            if is_host:
                for tf_host_lobby in team_name_input_fields_online_taboo:
                    action_area_online_taboo.controls.append(
                        ft.Container(content=tf_host_lobby, width=page.width * 0.75 if page.width and page.width > 400 else 290, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3))
                    )
                
                start_random_button = ft.ElevatedButton(
                    "🎲 بدء بتوزيع عشوائي",
                    on_click=lambda e: _handle_start_game_online(manual_assignment=False),
                    width=280, height=BUTTON_HEIGHT_LARGE,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))
                )
                
                def _show_manual_assignment_ui(e):
                    if not page.client_storage: return
                    t1_name = team_name_input_fields_online_taboo[0].value.strip()
                    t2_name = team_name_input_fields_online_taboo[1].value.strip()

                    if not t1_name or not t2_name:
                        page.snack_bar = ft.SnackBar(ft.Text("الرجاء إدخال اسمي الفريقين أولاً."), open=True); page.update()
                        return
                    if t1_name == t2_name:
                        page.snack_bar = ft.SnackBar(ft.Text("أسماء الفرق يجب أن تكون مختلفة."), open=True); page.update()
                        return

                    # Populate dropdowns
                    inner_column = player_assignment_column_container_online_taboo.content
                    inner_column.controls.clear()
                    player_assignment_dropdowns_online_taboo.clear()
                    team_options = [ft.dropdown.Option(t1_name), ft.dropdown.Option(t2_name)]
                    
                    current_players_in_room = game_rooms_ref.get(room_code, {}).get("players", {}) # Fresh player list

                    for p_name_iter in current_players_in_room.keys():
                        dd = ft.Dropdown(
                            hint_text=f"فريق لـ {p_name_iter}",
                            options=list(team_options), 
                            data=p_name_iter, 
                            border_radius=STANDARD_BORDER_RADIUS,
                            content_padding=ft.padding.symmetric(horizontal=8, vertical=5),
                            text_size=FONT_SIZE_NORMAL -1,
                            dense=True
                        )
                        player_assignment_dropdowns_online_taboo[p_name_iter] = dd
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
                    confirm_manual_assignment_button_online_taboo.visible = True
                    if page.client_storage:
                        player_assignment_column_container_online_taboo.update() # Update the container holding the column
                        confirm_manual_assignment_button_online_taboo.update()
                        # Potentially hide the "start random" and "start manual" buttons here if needed
                        # start_random_button.visible = False; start_random_button.update()
                        # e.control.visible = False; e.control.update() # Hides the "start manual" button itself


                start_manual_button = ft.ElevatedButton(
                    "✍️ بدء بتخصيص يدوي",
                    on_click=_show_manual_assignment_ui,
                    width=280, height=BUTTON_HEIGHT_LARGE,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))
                )
                
                action_area_online_taboo.controls.append(start_random_button)
                action_area_online_taboo.controls.append(start_manual_button)
                action_area_online_taboo.controls.append(player_assignment_column_container_online_taboo) # Add container for dropdowns
                action_area_online_taboo.controls.append(confirm_manual_assignment_button_online_taboo) # Add confirm button
                
                # Link the confirm button's on_click to the correctly scoped handler
                confirm_manual_assignment_button_online_taboo.on_click=lambda e_confirm: _handle_start_game_online(manual_assignment=True)

        # ... (rest of elif current_phase == ... blocks for TEAMS_SET_TABOO, TEAM_INTRO_TABOO, etc.) ...
        elif current_phase == "TEAMS_SET_TABOO":
            action_area_online_taboo.controls.append(ft.Text("تم تحديد فرق تابو!", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            if teams_data:
                for team_name_iter, team_info_data_set in teams_data.items():
                    player_names_in_team = ", ".join(team_info_data_set.get("players", []))
                    action_area_online_taboo.controls.append(ft.Text(f"فريق {team_name_iter}: {player_names_in_team}", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("▶️ بدء الدور الأول", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN_TABOO"), width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))
            else:
                action_area_online_taboo.controls.append(ft.Text("انتظار الهوست لبدء الدور...", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))

        elif current_phase == "TEAM_INTRO_TABOO":
            acting_team = gs.get("current_acting_team_online")
            current_actor = gs.get("current_actor_name_online")
            my_team_name = current_player_data.get("team_name")
            action_area_online_taboo.controls.append(ft.Text(f"استعداد فريق: {acting_team}", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            if current_player_name == current_actor:
                action_area_online_taboo.controls.append(ft.Text("أنت ستصف الكلمات!", size=FONT_SIZE_LARGE, color=ft.Colors.GREEN_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
                action_area_online_taboo.controls.append(ft.ElevatedButton("👀 عرض الكلمة والبدء", on_click=lambda e: send_action_fn("ACTOR_READY_START_ROUND_TABOO"), width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))
            elif my_team_name == acting_team:
                action_area_online_taboo.controls.append(ft.Text(f"{current_actor} سيصف. استعدوا للتخمين!", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))
            else:
                action_area_online_taboo.controls.append(ft.Text(f"{current_actor} من فريق {acting_team} سيصف.", size=FONT_SIZE_MEDIUM, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ACTING_ROUND_TABOO":
            word_card_display_online_taboo.visible = True
            current_actor = gs.get("current_actor_name_online")
            current_word_obj = gs.get("current_word_obj_online", {})
            acting_team_online = gs.get("current_acting_team_online")
            my_team_name = current_player_data.get("team_name")
            secret_word_text = current_word_obj.get("secret", "تحميل...")
            if current_player_name != current_actor and my_team_name == acting_team_online: secret_word_text = "الكلمة السرية: ؟؟؟"

            word_card_display_online_taboo.controls.append(ft.Text("الكلمة:", size=FONT_SIZE_SECTION_TITLE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            word_card_display_online_taboo.controls.append(
                ft.Text(secret_word_text, size=FONT_SIZE_SECRET_WORD, weight=ft.FontWeight.BOLD,
                        color=(ft.Colors.BLUE_ACCENT_700 if current_player_name == current_actor or my_team_name != acting_team_online else ft.Colors.BLUE_GREY_300),
                        text_align=ft.TextAlign.CENTER, selectable=True))
            if current_player_name == current_actor or (my_team_name and my_team_name != acting_team_online):
                word_card_display_online_taboo.controls.append(ft.Container(height=5))
                word_card_display_online_taboo.controls.append(
                     ft.Row(
                        [ft.Icon(ft.Icons.BLOCK_ROUNDED, color=ft.Colors.RED_ACCENT_700, size=STANDARD_ICON_SIZE),
                         ft.Text("ممنوع:", size=FONT_SIZE_LARGE, color=ft.Colors.RED_ACCENT_700, weight=ft.FontWeight.BOLD)],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=3))
                forbidden_col_online = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)
                for fb_word in current_word_obj.get("forbidden", []):
                     forbidden_col_online.controls.append(
                         ft.Text(f"• {fb_word}", size=FONT_SIZE_FORBIDDEN, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
                    )
                word_card_display_online_taboo.controls.append(forbidden_col_online)

            if current_player_name == current_actor:
                action_area_online_taboo.controls.append(ft.Text(f"ج {gs.get('current_game_round_online','?')}: دورك للوصف!", size=FONT_SIZE_MEDIUM, color=ft.Colors.BLUE_GREY_700, text_align=ft.TextAlign.CENTER))
                actor_buttons_row_online = ft.ResponsiveRow(
                    [ft.ElevatedButton("✅ صح", on_click=lambda e: send_action_fn("WORD_GUESSED_CORRECT_TABOO"), col={"xs":6}, height=BUTTON_HEIGHT_NORMAL, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))),
                     ft.ElevatedButton("⏭ تخطي", on_click=lambda e: send_action_fn("SKIP_WORD_TABOO"), col={"xs":6}, height=BUTTON_HEIGHT_NORMAL, bgcolor=ft.Colors.ORANGE_ACCENT_700, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS)))],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=10)
                action_area_online_taboo.controls.append(actor_buttons_row_online)
                action_area_online_taboo.controls.append(ft.Container(height=3))
                action_area_online_taboo.controls.append(
                    ft.ElevatedButton("⏹ إنهاء الدور مبكراً",
                                     on_click=lambda e: send_action_fn("END_ROUND_EARLY_TABOO"),
                                     width=260, height=BUTTON_HEIGHT_SMALL, bgcolor=ft.Colors.AMBER_400,
                                     style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS)))
                )
            elif my_team_name == acting_team_online:
                 action_area_online_taboo.controls.append(ft.Text(f"{current_actor} يصف. خمنوا!", size=FONT_SIZE_MEDIUM, italic=True, text_align=ft.TextAlign.CENTER))
            else:
                action_area_online_taboo.controls.append(ft.Text("راقبوا الكلمات الممنوعة!", size=FONT_SIZE_MEDIUM, italic=True, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ROUND_SUMMARY_TABOO":
            summary_data = gs.get("summary_for_ui_taboo", {})
            summary_team = summary_data.get("team_name", "فريق")
            summary_round_num = summary_data.get("round_number", gs.get("current_game_round_online","?"))
            summary_words = summary_data.get("words", [])

            summary_word_list_col_online = ft.Column(
                scroll=ft.ScrollMode.AUTO, spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            summary_scroll_container_online = ft.Container(
                content=summary_word_list_col_online,
                height=150 if summary_words else 50,
                width=page.width * 0.85 if page.width and page.width > 400 else 290,
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=STANDARD_BORDER_RADIUS, padding=8, alignment=ft.alignment.top_center
            )
            if not summary_words:
                summary_word_list_col_online.controls.append(ft.Text("لم يتم لعب أي كلمات.", italic=True, text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            else:
                for log_item_online_sum in summary_words:
                    status_text_sum = "✔ تم" if log_item_online_sum["correct"] else "✘ تخطي"
                    text_color_sum = ft.Colors.GREEN_800 if log_item_online_sum["correct"] else ft.Colors.RED_800
                    summary_word_list_col_online.controls.append(
                        ft.Text(f"• {log_item_online_sum['word']} ({status_text_sum})", size=FONT_SIZE_MEDIUM, color=text_color_sum, weight=ft.FontWeight.NORMAL, text_align=ft.TextAlign.CENTER)
                    )
            action_area_online_taboo.controls.extend([
                ft.Text(f"⏰ ملخص دور فريق: {summary_team} (ج {summary_round_num})", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700, text_align=ft.TextAlign.CENTER),
                ft.Text("🔤 الكلمات:", size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER),
                summary_scroll_container_online,
                ft.Container(height=5)])
            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("▶ الدور التالي", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN_TABOO"), width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))
            else:
                action_area_online_taboo.controls.append(ft.Text("انتظار الهوست للمتابعة...", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))

        elif current_phase == "GAME_OVER_TABOO":
            action_area_online_taboo.controls.append(ft.Text("🏁 انتهت لعبة تابو!", size=FONT_SIZE_XLARGE + 2, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            final_scores_data_taboo_online = []
            if teams_data:
                sorted_teams = sorted(teams_data.items(), key=lambda item: item[1].get('score',0.0), reverse=True)
                for team_name_iter, team_info_iter_go in sorted_teams:
                    final_scores_data_taboo_online.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(team_name_iter, weight=ft.FontWeight.BOLD, size=FONT_SIZE_MEDIUM)),
                        ft.DataCell(ft.Text(f"{float(team_info_iter_go.get('score',0.0)):.1f}", size=FONT_SIZE_MEDIUM))]))
            if final_scores_data_taboo_online:
                action_area_online_taboo.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[ft.DataColumn(ft.Text("الفريق", weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL)),
                                     ft.DataColumn(ft.Text("النقاط", weight=ft.FontWeight.BOLD, size=FONT_SIZE_NORMAL), numeric=True)],
                            rows=final_scores_data_taboo_online, column_spacing=20, data_row_max_height=35,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12)),
                        width=page.width * 0.8 if page.width and page.width > 400 else 300,
                        alignment=ft.alignment.center))
            else:
                 action_area_online_taboo.controls.append(ft.Text("لا توجد نتائج لعرضها.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            if is_host:
                action_area_online_taboo.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: send_action_fn("RESTART_GAME_SAME_TEAMS_TABOO"), width=280, height=BUTTON_HEIGHT_LARGE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=STANDARD_BORDER_RADIUS))))

        if page.client_storage:
            page.update()
        _initial_ui_build_done = True


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

    online_main_content_column_taboo.controls.extend([
        ft.Row(
            [ft.Text(f"🚫 تابو - غرفة: {room_code}", size=FONT_SIZE_TITLE, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
             ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=TITLE_ICON_SIZE)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Divider(height=1, thickness=0.5),
        status_text,
        online_timer_display_taboo_control,
        ft.Divider(height=2, thickness=1),
        word_card_display_online_taboo,
        ft.ResponsiveRow(
            [ft.Container(content=ft.Column([player_list_display_online_taboo, ft.Divider(height=2), team_score_display_online_taboo],
                                            spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                          padding=CONTAINER_PADDING_NORMAL, border=ft.border.all(1, ft.Colors.with_opacity(0.4, ft.Colors.OUTLINE)),
                          border_radius=STANDARD_BORDER_RADIUS, col={"xs": 12, "md": 4},
                          margin=ft.margin.only(bottom=5 if page.width and page.width < 768 else 0, top=3)),
             ft.Container(content=action_area_online_taboo, padding=CONTAINER_PADDING_NORMAL,
                          col={"xs": 12, "md": 8}, alignment=ft.alignment.top_center)],
            vertical_alignment=ft.CrossAxisAlignment.START, alignment=ft.MainAxisAlignment.SPACE_AROUND,
            spacing=3, run_spacing=3)
    ])

    initial_room_data_from_ref = game_rooms_ref.get(room_code)
    if initial_room_data_from_ref:
        update_ui_from_server_state_online_taboo(initial_room_data_from_ref)
    else:
        status_text.value = "في انتظار بيانات الغرفة من الخادم..."
        if page.client_storage: status_text.update()

    return [ft.Container(content=online_main_content_column_taboo, expand=True, alignment=ft.alignment.top_center,
                         padding=ft.padding.symmetric(horizontal=5, vertical=5))]


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