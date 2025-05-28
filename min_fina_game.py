# min_fina_game.py
import flet as ft
import random
from min_fina_questions import min_fina_questions

# --- OFFLINE MODE LOGIC ---
def min_fina_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {}
    name_inputs_offline_controls = []

    # --- OFFLINE UI ENHANCEMENT: Persistent Home Button ---
    offline_title_bar_minfina = ft.Row(
        [
            ft.Text("👀 لعبة من فينا؟ (أوفلاين)", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=go_home_fn, # Direct call to go_home_fn as offline_state clear is in reset
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
        spacing=15 # Adjusted spacing
    )

    def reset_offline_state():
        nonlocal name_inputs_offline_controls
        offline_state.clear()
        name_inputs_offline_controls.clear() # Also clear the control list
        offline_state.update({
            "page_step": "setup_player_count",
            "num_players": 3, "player_names": [],
            "current_question": None, "used_questions": set(),
            "votes": {},
            "current_voting_player_index": 0,
            "skip_chances_offline": 2,
        })
        update_offline_ui()


    def set_offline_page_step(step_name):
        offline_state["page_step"] = step_name
        update_offline_ui()

    def choose_new_question_offline():
        s = offline_state
        available = list(set(min_fina_questions) - s.get("used_questions", set()))
        if not available and min_fina_questions:
            s["used_questions"] = set()
            available = list(min_fina_questions)
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("تم إعادة تعيين الأسئلة المستخدمة."), open=True)
                page.update()

        if not available:
            s["current_question"] = "لا توجد أسئلة متبقية في القائمة!"
            return
        s["current_question"] = random.choice(available)
        s.setdefault("used_questions", set()).add(s["current_question"])


    def update_offline_ui():
        nonlocal name_inputs_offline_controls
        if not page.client_storage: return

        offline_main_column.controls.clear()
        offline_main_column.controls.append(offline_title_bar_minfina)
        offline_main_column.controls.append(ft.Divider(height=1, thickness=0.5))
        s = offline_state

        if s["page_step"] == "setup_player_count":
            # Title is in offline_title_bar_minfina
            offline_main_column.controls.append(ft.Text("اختر عدد اللاعبين (3-12):", size=22, text_align=ft.TextAlign.CENTER)) # Adjusted
            num_display_offline = ft.Text(str(s["num_players"]), size=28, weight=ft.FontWeight.BOLD) # Adjusted
            def update_num_offline(delta):
                s["num_players"] = max(3, min(12, s["num_players"] + delta))
                num_display_offline.value = str(s["num_players"])
                if page.client_storage: num_display_offline.update()
            offline_main_column.controls.extend([
                 ft.ResponsiveRow(
                    [
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e: update_num_offline(-1), col={"xs": 4}, icon_size=28), # Adjusted
                        ft.Container(content=num_display_offline, col={"xs": 4}, alignment=ft.alignment.center),
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e: update_num_offline(1), col={"xs": 4}, icon_size=28), # Adjusted
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5 # Adjusted
                ),
                ft.ElevatedButton("التالي: إدخال الأسماء", on_click=lambda e: set_offline_page_step("input_player_names"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                # Redundant home button removed
            ])
        elif s["page_step"] == "input_player_names":
            offline_main_column.controls.append(ft.Text("📝 أدخل أسماء اللاعبين:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            name_inputs_offline_controls.clear()
            for i in range(s["num_players"]):
                tf = ft.TextField(label=f"اللاعب {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8, height=45, text_size=14) # Adjusted
                name_inputs_offline_controls.append(tf)
                offline_main_column.controls.append(
                    ft.Container(content=tf, width=page.width * 0.85 if page.width else 280, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3)) # Adjusted
                )

            def save_names_offline_minfina(e):
                names = [tf.value.strip() for tf in name_inputs_offline_controls if tf.value.strip()]
                if len(names) != s["num_players"] or len(set(names)) != len(names) or any(not n for n in names):
                    if page.client_storage:
                        page.snack_bar = ft.SnackBar(ft.Text("الأسماء يجب أن تكون فريدة وغير فارغة ومكتملة!"), open=True)
                        page.update()
                    return
                s["player_names"] = names
                s["used_questions"] = set()
                s["skip_chances_offline"] = 2
                choose_new_question_offline()
                set_offline_page_step("question_display_offline")
            offline_main_column.controls.append(ft.ElevatedButton("ابدأ اللعبة", on_click=save_names_offline_minfina, width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            offline_main_column.controls.append(ft.ElevatedButton("🔙 رجوع للعدد", on_click=lambda e: set_offline_page_step("setup_player_count"), width=260, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif s["page_step"] == "question_display_offline":
            current_q = s.get("current_question", "تحميل السؤال...")
            offline_main_column.controls.extend([
                ft.Text("من فينا؟ 👀", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Container(
                    content=ft.Text(current_q, size=24, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, selectable=True), # Adjusted
                    padding=ft.padding.symmetric(horizontal=8), # Adjusted
                    margin=ft.margin.symmetric(vertical=8) # Adjusted
                )
            ])
            if current_q.startswith("لا توجد أسئلة"):
                 pass # Home button is already persistent
            else:
                if s["skip_chances_offline"] > 0:
                    offline_main_column.controls.append(ft.Text(f"🔄 فرص تغيير السؤال: {s['skip_chances_offline']}", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
                    offline_main_column.controls.append(ft.ElevatedButton("غير السؤال", on_click=lambda e: skip_question_offline(), width=260, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
                else:
                    offline_main_column.controls.append(ft.Text("❌ لا يمكن تغيير السؤال.", size=16, color=ft.Colors.RED_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Adjusted
                offline_main_column.controls.append(ft.ElevatedButton("🗳️ بدء التصويت", on_click=lambda e: start_voting_offline(), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif s["page_step"] == "voting_offline":
            voter = s["player_names"][s["current_voting_player_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"دور اللاعب: {voter} للتصويت", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Container(
                    content=ft.Text(f"السؤال: {s.get('current_question','')}", size=18, text_align=ft.TextAlign.CENTER, selectable=True), # Adjusted
                    padding=3 # Adjusted
                ),
                ft.Text("اختر اللاعب:", size=16, text_align=ft.TextAlign.CENTER) # Adjusted
            ])

            vote_buttons_row = ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8, run_spacing=8 # Adjusted
            )
            for p_name_option in s["player_names"]:
                player_vote_btn = ft.ElevatedButton(
                    p_name_option,
                    height=50, # Adjusted
                    on_click=lambda e, choice=p_name_option: cast_vote_offline(choice),
                    col={"xs": 6, "sm": 4},
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                )
                vote_buttons_row.controls.append(player_vote_btn) # No container needed
            offline_main_column.controls.append(vote_buttons_row)

        elif s["page_step"] == "results_offline":
            offline_main_column.controls.extend([
                ft.Text("📊 نتيجة التصويت", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Container(
                    content=ft.Text(f"السؤال كان: {s.get('current_question', '')}", size=18, text_align=ft.TextAlign.CENTER, selectable=True), # Adjusted
                    padding=3 # Adjusted
                )
            ])
            vote_counts = {name: 0 for name in s["player_names"]}
            for voted_player in s.get("votes", {}).values():
                if voted_player in vote_counts:
                    vote_counts[voted_player] += 1

            total_votes_cast = len(s.get("votes", {}))
            sorted_results = sorted(vote_counts.items(), key=lambda item: item[1], reverse=True)

            rows = []
            for name, count in sorted_results:
                percentage = (count / total_votes_cast * 100) if total_votes_cast > 0 else 0
                rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(name, size=15)), # Adjusted
                    ft.DataCell(ft.Text(str(count), size=15)), # Adjusted
                    ft.DataCell(ft.Text(f"{percentage:.1f}%", size=15)), # Adjusted
                ]))

            dt = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("اللاعب", weight=ft.FontWeight.BOLD, size=14)), # Adjusted
                    ft.DataColumn(ft.Text("الأصوات", weight=ft.FontWeight.BOLD, size=14), numeric=True), # Adjusted
                    ft.DataColumn(ft.Text("النسبة", weight=ft.FontWeight.BOLD, size=14), numeric=True) # Adjusted
                ],
                rows=rows,
                column_spacing=20, # Adjusted
                data_row_max_height=40, # Adjusted
                horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12)
            )
            offline_main_column.controls.append(
                ft.Container(content=dt, width=page.width * 0.9 if page.width else 360, alignment=ft.alignment.center) # Adjusted
            )

            if total_votes_cast > 0 and sorted_results and sorted_results[0][1] > 0:
                max_vote_count = sorted_results[0][1]
                most_voted_players = [name for name, count in sorted_results if count == max_vote_count]
                offline_main_column.controls.append(ft.Text(f"الأكثر تصويتاً: {', '.join(most_voted_players)}", size=20, weight="bold", color=ft.Colors.PRIMARY, text_align=ft.TextAlign.CENTER)) # Adjusted
            else:
                 offline_main_column.controls.append(ft.Text("لم يتم تسجيل أصوات.", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted

            buttons_results_row = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("🔁 سؤال جديد", on_click=lambda e: restart_round_offline(), col={"xs":12}, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Single button full width
                    # Redundant home button removed
                ],
                alignment=ft.MainAxisAlignment.CENTER, run_spacing=8, spacing=8 # Adjusted
            )
            offline_main_column.controls.append(buttons_results_row)
        else: # Fallback
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['page_step']}'", size=18, color=ft.Colors.RED_700))
            # Redundant home button removed

        if page.client_storage: page.update()

    def skip_question_offline():
        s = offline_state
        if s["skip_chances_offline"] > 0:
            s["skip_chances_offline"] -= 1
            choose_new_question_offline()
            update_offline_ui()
        else:
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("لا توجد فرص متبقية لتغيير السؤال!"), open=True)
                page.update()

    def start_voting_offline():
        s = offline_state
        s["votes"] = {}
        s["current_voting_player_index"] = 0
        set_offline_page_step("voting_offline")

    def cast_vote_offline(chosen_player):
        s = offline_state
        if s["current_voting_player_index"] >= len(s["player_names"]):
            print(f"Error: current_voting_player_index ({s['current_voting_player_index']}) out of bounds.")
            set_offline_page_step("results_offline")
            return

        voter = s["player_names"][s["current_voting_player_index"]]
        s["votes"][voter] = chosen_player
        s["current_voting_player_index"] += 1
        if s["current_voting_player_index"] >= len(s["player_names"]):
            set_offline_page_step("results_offline")
        else:
            update_offline_ui()

    def restart_round_offline():
        s = offline_state
        s["skip_chances_offline"] = 2
        s["votes"] = {}
        s["current_voting_player_index"] = 0
        choose_new_question_offline()
        set_offline_page_step("question_display_offline")

    reset_offline_state()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=8, vertical=10) # Adjusted overall padding
        )
    ]

# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def min_fina_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    # page_title moved to the main content column
    status_text = ft.Text("...", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Adjusted
    
    player_list_display = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=4, # Adjusted
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    action_area = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12, # Adjusted
        scroll=ft.ScrollMode.ADAPTIVE
    )
    question_display_area = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8, # Adjusted
        alignment=ft.MainAxisAlignment.CENTER
    )

    online_main_content_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12 # Adjusted
    )

    def log_debug_online(msg):
        print(f"[MinFina_Online_Client:{current_player_name} session:{page.session_id}] {msg}")

    def update_ui_from_server_state_online(room_state_from_server):
        if not page.client_storage:
            log_debug_online("Page detached, skipping UI update.")
            return

        gs = room_state_from_server.get("game_state",{})
        players_in_room = room_state_from_server.get("players",{})
        is_host = players_in_room.get(current_player_name, {}).get("is_host", False)
        current_phase = gs.get("phase", "LOBBY")

        # log_debug_online(f"Updating UI. Phase: {current_phase}") # Less verbose
        status_text.value = gs.get("status_message", "...")
        status_text.text_align = ft.TextAlign.CENTER

        player_list_display.controls.clear()
        num_players_denominator = gs.get("num_players_setting", len(players_in_room))
        player_list_display.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}/{num_players_denominator}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=16)) # Adjusted

        for p_name_iter, p_data_iter in players_in_room.items():
            voted_status = " (صوّت ✔️)" if p_name_iter in gs.get("players_voted_this_round", []) and current_phase == "VOTING" else ""
            player_list_display.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}{voted_status}", text_align=ft.TextAlign.CENTER, size=14) # Adjusted
            )

        action_area.controls.clear()
        question_display_area.controls.clear()

        if current_phase == "LOBBY":
            min_players_to_start = 3
            current_player_count = len(players_in_room)

            action_area.controls.append(
                ft.Text("اللعبة تبدأ عند وجود 3 لاعبين أو أكثر.", text_align=ft.TextAlign.CENTER, size=16)
            )

            if is_host:
                can_host_start = current_player_count >= min_players_to_start

                start_button = ft.ElevatedButton(
                    "🚀 ابدأ اللعبة",
                    on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"),
                    disabled=not can_host_start,
                    width=280,
                    height=50,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                )
                action_area.controls.append(start_button)

                if not can_host_start:
                    players_needed = min_players_to_start - current_player_count
                    action_area.controls.append(
                        ft.Text(f"تحتاج إلى {players_needed} لاعبين إضافيين.", color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER, size=13)
                    )
            else:
                action_area.controls.append(
                    ft.Text("في انتظار الهوست لبدء اللعبة.", text_align=ft.TextAlign.CENTER, size=15)
                )


        elif current_phase == "QUESTION_DISPLAY":
            current_q_online = gs.get("current_question", "انتظر السؤال...")
            question_display_area.controls.extend([
                ft.Text("من فينا؟ 👀", size=28, weight="bold", text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Container(
                    content=ft.Text(current_q_online, size=24, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, selectable=True), # Adjusted
                    padding=ft.padding.symmetric(horizontal=5),
                    margin=ft.margin.symmetric(vertical=3) # Adjusted
                )
            ])
            if current_q_online.startswith("لا توجد أسئلة"):
                if is_host:
                    action_area.controls.append(ft.ElevatedButton("إعادة تعيين وبدء", on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            elif is_host:
                if gs.get("skip_chances_left",0) > 0:
                    action_area.controls.append(ft.Text(f"🔄 فرص التغيير: {gs['skip_chances_left']}", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
                    action_area.controls.append(ft.ElevatedButton("غير السؤال", on_click=lambda e: send_action_fn("SKIP_QUESTION_HOST"), width=260, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
                else:
                    action_area.controls.append(ft.Text("❌ لا يمكن تغيير السؤال.", size=16, color=ft.Colors.RED_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Adjusted
                action_area.controls.append(ft.ElevatedButton("🗳️ ابدأ التصويت", on_click=lambda e: send_action_fn("INITIATE_VOTING_HOST"), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            else:
                action_area.controls.append(ft.Text("انتظار الهوست...", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted

        elif current_phase == "VOTING":
            question_display_area.controls.extend([
                 ft.Text("من فينا؟ 👀", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Adjusted
                 ft.Container(
                    content=ft.Text(f"السؤال: {gs.get('current_question', '...')}", size=20, text_align=ft.TextAlign.CENTER, selectable=True), # Adjusted
                    padding=3 # Adjusted
                 )
            ])
            if current_player_name in gs.get("players_voted_this_round", []):
                action_area.controls.append(ft.Text("شكراً، تم التصويت. انتظار البقية...", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
            else:
                action_area.controls.append(ft.Text("اختر اللاعب:", size=18, text_align=ft.TextAlign.CENTER)) # Adjusted
                
                online_vote_buttons_row = ft.ResponsiveRow(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8, run_spacing=8 # Adjusted
                )
                for p_name_option_online in players_in_room.keys():
                    vote_btn_online = ft.ElevatedButton(
                        p_name_option_online,
                        height=50, # Adjusted
                        on_click=lambda e, choice=p_name_option_online: send_action_fn("CAST_PLAYER_VOTE", {"voted_for": choice}),
                        col={"xs": 6, "sm": 4},
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                    online_vote_buttons_row.controls.append(vote_btn_online) # No container needed
                action_area.controls.append(online_vote_buttons_row)

        elif current_phase == "RESULTS":
            question_display_area.controls.extend([
                ft.Text("📊 نتيجة التصويت:", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Container(
                    content=ft.Text(f"{gs.get('last_question_answered', '...')}", size=18, text_align=ft.TextAlign.CENTER, selectable=True), # Adjusted
                    padding=3 # Adjusted
                )
            ])

            vote_counts_results = gs.get("last_vote_counts", {})
            total_votes_cast_results = sum(vote_counts_results.values())
            sorted_vote_results = sorted(vote_counts_results.items(), key=lambda item: item[1], reverse=True)

            rows_online = []
            for name, count in sorted_vote_results:
                percentage = (count / total_votes_cast_results * 100) if total_votes_cast_results > 0 else 0
                rows_online.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(name, size=15)), # Adjusted
                    ft.DataCell(ft.Text(str(count), size=15)), # Adjusted
                    ft.DataCell(ft.Text(f"{percentage:.1f}%", size=15)), # Adjusted
                ]))

            dt_results_online = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("اللاعب", weight=ft.FontWeight.BOLD, size=14)), # Adjusted
                    ft.DataColumn(ft.Text("الأصوات", weight=ft.FontWeight.BOLD, size=14), numeric=True), # Adjusted
                    ft.DataColumn(ft.Text("النسبة", weight=ft.FontWeight.BOLD, size=14), numeric=True) # Adjusted
                ],
                rows=rows_online,
                column_spacing=20, # Adjusted
                data_row_max_height=40, # Adjusted
                horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12)
            )
            action_area.controls.append(
                ft.Container(content=dt_results_online, width=page.width*0.9 if page.width else 360, alignment=ft.alignment.center) # Adjusted
            )

            if total_votes_cast_results > 0 and sorted_vote_results and sorted_vote_results[0][1] > 0:
                max_vote_count_res = sorted_vote_results[0][1]
                most_voted_players_res = [name for name, count in sorted_vote_results if count == max_vote_count_res]
                action_area.controls.append(ft.Text(f"الأكثر تصويتاً: {', '.join(most_voted_players_res)}", size=20, weight="bold", color=ft.Colors.PRIMARY, text_align=ft.TextAlign.CENTER)) # Adjusted
            else:
                 action_area.controls.append(ft.Text("لم يتم تسجيل أصوات.", size=16, text_align=ft.TextAlign.CENTER)) # Adjusted

            if is_host:
                 action_area.controls.append(ft.ElevatedButton("🔁 سؤال جديد", on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            else:
                 action_area.controls.append(ft.Text("انتظار الهوست...", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted

        if page.client_storage:
            # log_debug_online(f"EXECUTING page.update() for phase {current_phase}") # Less verbose
            page.update()

    def on_server_message_online(*args_received):
        if not page.client_storage: return
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT", "HOST_CHANGED_NUM_PLAYERS"]:
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
        # log_debug_online("Found initial room data for Min Fina on client load.") # Less verbose
        update_ui_from_server_state_online(initial_room_data)
    else:
        # log_debug_online(f"Room {room_code} not found for Min Fina on client load.") # Less verbose
        status_text.value = "خطأ في الاتصال بغرفة 'من فينا؟'."

    online_main_content_column.controls.extend([
        ft.Row(
            [
                ft.Text(f"👀 من فينا؟ - غرفة: {room_code}", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER), # Game title
                ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=28) # Home button
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=1, thickness=0.5),
        status_text,
        ft.Divider(height=3, thickness=1), # Adjusted
        question_display_area,
        ft.ResponsiveRow(
            [
                ft.Container(
                    content=player_list_display,
                    padding=8, # Adjusted
                    border=ft.border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.OUTLINE)), # Adjusted
                    border_radius=8, # Adjusted
                    col={"xs": 12, "md": 4},
                    margin=ft.margin.only(bottom=8 if page.width and page.width < 768 else 0, top=5) # Added top margin, adjusted
                ),
                ft.Container(
                    content=action_area,
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

# --- GAME ENTRY POINT ---
def min_fina_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return min_fina_offline_logic(page, go_home_fn)
    else:
        if not all([room_code, player_name, game_rooms_ref is not None]):
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة للعب 'من فينا؟' أونلاين."), alignment=ft.alignment.center, expand=True)]

        def send_minfina_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "min_fina", action_type, payload or {})

        return min_fina_online_logic(page, go_home_fn, send_minfina_action_to_server_wrapper, room_code, player_name, game_rooms_ref)