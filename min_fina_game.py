# min_fina_game.py
import flet as ft
import random
from min_fina_questions import min_fina_questions

# --- OFFLINE MODE LOGIC ---
def min_fina_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {}
    name_inputs_offline_controls = [] # To store TextField controls for offline mode

    def reset_offline_state():
        offline_state.clear()
        offline_state.update({
            "page_step": "setup_player_count",
            "num_players": 3, "player_names": [],
            "current_question": None, "used_questions": set(),
            "votes": {},
            "current_voting_player_index": 0,
            "skip_chances_offline": 2,
            # "name_inputs_offline": [] # This was storing UI elements, now use name_inputs_offline_controls
        })
        update_offline_ui()

    offline_main_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20 # Increased spacing
    )

    def set_offline_page_step(step_name):
        offline_state["page_step"] = step_name
        update_offline_ui()

    def choose_new_question_offline():
        s = offline_state
        available = list(set(min_fina_questions) - s.get("used_questions", set()))
        if not available and min_fina_questions: # Check if original list has questions
            s["used_questions"] = set()
            available = list(min_fina_questions)
            page.snack_bar = ft.SnackBar(ft.Text("تم إعادة تعيين الأسئلة المستخدمة."), open=True) # Notify user
            if page.client_storage: page.update()

        if not available:
            s["current_question"] = "لا توجد أسئلة متبقية في القائمة!" # More specific message
            return
        s["current_question"] = random.choice(available)
        s.setdefault("used_questions", set()).add(s["current_question"])


    def update_offline_ui():
        nonlocal name_inputs_offline_controls # Allow modification of the list
        offline_main_column.controls.clear()
        s = offline_state

        if s["page_step"] == "setup_player_count":
            offline_main_column.controls.append(ft.Text("👥 لعبة من فينا؟", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Title
            offline_main_column.controls.append(ft.Text("اختر عدد اللاعبين (3-12):", size=24, text_align=ft.TextAlign.CENTER)) # Larger
            num_display_offline = ft.Text(str(s["num_players"]), size=30, weight=ft.FontWeight.BOLD) # Larger
            def update_num_offline(delta):
                s["num_players"] = max(3, min(12, s["num_players"] + delta))
                num_display_offline.value = str(s["num_players"])
                if page.client_storage: num_display_offline.update()
            offline_main_column.controls.extend([
                 ft.ResponsiveRow(
                    [
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e: update_num_offline(-1), col={"xs": 4}, icon_size=30),
                        ft.Container(content=num_display_offline, col={"xs": 4}, alignment=ft.alignment.center),
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e: update_num_offline(1), col={"xs": 4}, icon_size=30),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.ElevatedButton("التالي: إدخال الأسماء", on_click=lambda e: set_offline_page_step("input_player_names"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                ft.ElevatedButton("🏠 العودة للقائمة", on_click=go_home_fn, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])
        elif s["page_step"] == "input_player_names":
            offline_main_column.controls.append(ft.Text("📝 أدخل أسماء اللاعبين:", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            name_inputs_offline_controls.clear() # Clear previous TextFields
            for i in range(s["num_players"]):
                tf = ft.TextField(label=f"اللاعب {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8)
                name_inputs_offline_controls.append(tf)
                offline_main_column.controls.append(
                    ft.Container(content=tf, width=page.width * 0.85 if page.width else 300, alignment=ft.alignment.center)
                )

            def save_names_offline_minfina(e):
                names = [tf.value.strip() for tf in name_inputs_offline_controls if tf.value.strip()]
                if len(names) != s["num_players"] or len(set(names)) != len(names) or any(not n for n in names):
                    page.snack_bar = ft.SnackBar(ft.Text("الأسماء يجب أن تكون فريدة وغير فارغة ومكتملة!"), open=True)
                    if page.client_storage: page.update()
                    return
                s["player_names"] = names
                s["used_questions"] = set()
                s["skip_chances_offline"] = 2
                choose_new_question_offline()
                set_offline_page_step("question_display_offline")
            offline_main_column.controls.append(ft.ElevatedButton("ابدأ اللعبة", on_click=save_names_offline_minfina, width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            offline_main_column.controls.append(ft.ElevatedButton("🔙 رجوع للعدد", on_click=lambda e: set_offline_page_step("setup_player_count"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        elif s["page_step"] == "question_display_offline":
            current_q = s.get("current_question", "تحميل السؤال...")
            offline_main_column.controls.extend([
                ft.Text("من فينا؟ 👀", size=34, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Larger
                ft.Container( # Container for question text
                    content=ft.Text(current_q, size=26, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, selectable=True), # Larger, selectable
                    padding=ft.padding.symmetric(horizontal=10),
                    border_radius=8,
                    # border=ft.border.all(1, ft.Colors.BLACK26) if not current_q.startswith("لا توجد أسئلة") else None, # Optional border
                    margin=ft.margin.symmetric(vertical=10)
                )
            ])
            if current_q.startswith("لا توجد أسئلة"):
                 offline_main_column.controls.append(ft.ElevatedButton("🏠 العودة للقائمة", on_click=go_home_fn, width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                if s["skip_chances_offline"] > 0:
                    offline_main_column.controls.append(ft.Text(f"🔄 فرص تغيير السؤال: {s['skip_chances_offline']}", size=18, text_align=ft.TextAlign.CENTER))
                    offline_main_column.controls.append(ft.ElevatedButton("غير السؤال", on_click=lambda e: skip_question_offline(), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
                else:
                    offline_main_column.controls.append(ft.Text("❌ لا يمكن تغيير السؤال هذا الدور.", size=18, color=ft.Colors.RED_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
                offline_main_column.controls.append(ft.ElevatedButton("🗳️ بدء التصويت", on_click=lambda e: start_voting_offline(), width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        elif s["page_step"] == "voting_offline":
            voter = s["player_names"][s["current_voting_player_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"دور اللاعب: {voter} للتصويت", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Larger
                ft.Container(
                    content=ft.Text(f"السؤال: {s.get('current_question','')}", size=20, text_align=ft.TextAlign.CENTER, selectable=True), # Larger
                    padding=5
                ),
                ft.Text("اختر اللاعب الذي ينطبق عليه السؤال:", size=18, text_align=ft.TextAlign.CENTER)
            ])

            vote_buttons_row = ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10, run_spacing=10
            )
            for p_name_option in s["player_names"]: # Voters vote for any player, including themselves
                player_vote_btn = ft.ElevatedButton(
                    p_name_option,
                    width=180, # Will be overridden by col, but good for fallback
                    height=55,
                    on_click=lambda e, choice=p_name_option: cast_vote_offline(choice),
                    col={"xs": 6, "sm": 4}, # 2-3 buttons per row
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                )
                vote_buttons_row.controls.append(ft.Container(content=player_vote_btn, alignment=ft.alignment.center))
            offline_main_column.controls.append(vote_buttons_row)

        elif s["page_step"] == "results_offline":
            offline_main_column.controls.extend([
                ft.Text("📊 نتيجة التصويت", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Larger
                ft.Container(
                    content=ft.Text(f"السؤال كان: {s.get('current_question', '')}", size=20, text_align=ft.TextAlign.CENTER, selectable=True), # Larger
                    padding=5
                )
            ])
            vote_counts = {name: 0 for name in s["player_names"]}
            for voted_player in s.get("votes", {}).values():
                if voted_player in vote_counts: # Ensure player is still in game (though offline this is less an issue)
                    vote_counts[voted_player] += 1

            total_votes_cast = len(s.get("votes", {}))
            sorted_results = sorted(vote_counts.items(), key=lambda item: item[1], reverse=True)

            rows = []
            for name, count in sorted_results:
                percentage = (count / total_votes_cast * 100) if total_votes_cast > 0 else 0
                rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(name, size=16)),
                    ft.DataCell(ft.Text(str(count), size=16)),
                    ft.DataCell(ft.Text(f"{percentage:.1f}%", size=16)),
                ]))

            dt = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("اللاعب", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("الأصوات", weight=ft.FontWeight.BOLD), numeric=True),
                    ft.DataColumn(ft.Text("النسبة", weight=ft.FontWeight.BOLD), numeric=True)
                ],
                rows=rows,
                column_spacing=25, # Increased spacing
                data_row_max_height=45, # Increased row height
                horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12) # Added lines
            )
            offline_main_column.controls.append(
                ft.Container(content=dt, width=page.width * 0.9 if page.width else 380, alignment=ft.alignment.center)
            ) # Responsive width

            if total_votes_cast > 0 and sorted_results and sorted_results[0][1] > 0:
                max_vote_count = sorted_results[0][1]
                most_voted_players = [name for name, count in sorted_results if count == max_vote_count]
                offline_main_column.controls.append(ft.Text(f"الأكثر حصولاً على الأصوات: {', '.join(most_voted_players)}", size=22, weight="bold", color=ft.Colors.PRIMARY, text_align=ft.TextAlign.CENTER)) # Larger
            else:
                 offline_main_column.controls.append(ft.Text("لم يتم تسجيل أي أصوات أو لا يوجد فائز واضح.", size=18, text_align=ft.TextAlign.CENTER))

            buttons_results_row = ft.ResponsiveRow( # For buttons to stack
                [
                    ft.ElevatedButton("🔁 سؤال جديد", on_click=lambda e: restart_round_offline(), col={"xs":12, "sm":6}, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                    ft.ElevatedButton("🏠 العودة للقائمة", on_click=go_home_fn, col={"xs":12, "sm":6}, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                ],
                alignment=ft.MainAxisAlignment.CENTER, run_spacing=10, spacing=10
            )
            offline_main_column.controls.append(buttons_results_row)
        else:
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['page_step']}'"))
            offline_main_column.controls.append(ft.ElevatedButton("العودة للرئيسية", on_click=go_home_fn, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        if page.client_storage: page.update()

    def skip_question_offline():
        s = offline_state
        if s["skip_chances_offline"] > 0:
            s["skip_chances_offline"] -= 1
            choose_new_question_offline()
            update_offline_ui()
        else: # Should not be callable if no chances, but good to have a message
            page.snack_bar = ft.SnackBar(ft.Text("لا توجد فرص متبقية لتغيير السؤال!"), open=True)
            if page.client_storage: page.update()


    def start_voting_offline(): # e argument removed as it's not used
        s = offline_state
        s["votes"] = {}
        s["current_voting_player_index"] = 0
        set_offline_page_step("voting_offline")

    def cast_vote_offline(chosen_player):
        s = offline_state
        # Ensure current_voting_player_index is valid
        if s["current_voting_player_index"] >= len(s["player_names"]):
            print(f"Error: current_voting_player_index ({s['current_voting_player_index']}) out of bounds.")
            set_offline_page_step("results_offline") # Or some error state
            return

        voter = s["player_names"][s["current_voting_player_index"]]
        s["votes"][voter] = chosen_player
        s["current_voting_player_index"] += 1
        if s["current_voting_player_index"] >= len(s["player_names"]):
            set_offline_page_step("results_offline")
        else:
            update_offline_ui() # Refresh UI for the next voter

    def restart_round_offline():
        s = offline_state
        s["skip_chances_offline"] = 2
        # No need to reset votes or current_voting_player_index here,
        # as they are reset when start_voting_offline is called.
        # used_questions is reset in choose_new_question_offline if needed.
        s["votes"] = {}
        s["current_voting_player_index"] = 0
        choose_new_question_offline()
        set_offline_page_step("question_display_offline")

    reset_offline_state()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center, # Usually better for scrollable content
            padding=ft.padding.symmetric(horizontal=10, vertical=15) # Overall padding
        )
    ]

# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def min_fina_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    page_title = ft.Text(f"لعبة من فينا؟ - غرفة: {room_code}", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Larger
    status_text = ft.Text("...", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER) # Larger
    
    player_list_display = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=5,
        # height will be determined by content, or wrapped in a container with height
        horizontal_alignment=ft.CrossAxisAlignment.CENTER # Center player names
    )
    action_area = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15, # Increased spacing
        scroll=ft.ScrollMode.ADAPTIVE
    )
    question_display_area = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10, # Increased spacing
        alignment=ft.MainAxisAlignment.CENTER
    )

    online_main_content_column = ft.Column( # This will be the content of the padded container
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15 # Consistent spacing
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

        log_debug_online(f"Updating UI. Phase: {current_phase}")
        status_text.value = gs.get("status_message", "...")
        status_text.text_align = ft.TextAlign.CENTER

        player_list_display.controls.clear()
        num_players_denominator = gs.get("num_players_setting", len(players_in_room)) # Default to actual if setting not present
        player_list_display.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}/{num_players_denominator}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=18)) # Slightly larger

        for p_name_iter, p_data_iter in players_in_room.items():
            voted_status = " (صوّت ✔️)" if p_name_iter in gs.get("players_voted_this_round", []) and current_phase == "VOTING" else ""
            player_list_display.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}{voted_status}", text_align=ft.TextAlign.CENTER, size=16) # Slightly larger
            )

        action_area.controls.clear()
        question_display_area.controls.clear()

        if current_phase == "LOBBY":
            min_players_to_start = gs.get("min_players_for_game", 3)
            num_players_setting_lobby = gs.get("num_players_setting", min_players_to_start) # Use min_players if setting not there
            current_player_count = len(players_in_room)

            action_area.controls.append(ft.Text(f"في انتظار انضمام اللاعبين. مطلوب {num_players_setting_lobby} لاعبين للبدء.", text_align=ft.TextAlign.CENTER, size=18)) # Larger

            if is_host:
                # Host controls for setting number of players in LOBBY
                num_display_host = ft.Text(str(num_players_setting_lobby), size=28, weight=ft.FontWeight.BOLD)
                def update_num_players_setting_host(delta):
                    current_val = gs.get("num_players_setting", 3) # Get current or default
                    new_val = max(3, min(12, current_val + delta))
                    # Send action to server to update this setting
                    send_action_fn("SET_NUM_PLAYERS_HOST", {"num_players": new_val})
                    # UI will update via pubsub after server processes

                action_area.controls.extend([
                    ft.Text("حدد عدد اللاعبين للعبة:", text_align=ft.TextAlign.CENTER, size=16),
                    ft.ResponsiveRow(
                        [
                            ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e: update_num_players_setting_host(-1), col={"xs":4}, icon_size=28),
                            ft.Container(content=num_display_host, col={"xs":4}, alignment=ft.alignment.center),
                            ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e: update_num_players_setting_host(1), col={"xs":4}, icon_size=28),
                        ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER
                    )
                ])


                can_host_start = current_player_count >= num_players_setting_lobby and \
                                 current_player_count >= min_players_to_start

                start_button = ft.ElevatedButton("🚀 ابدأ اللعبة بسؤال جديد",
                                     on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"),
                                     disabled=not can_host_start,
                                     width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)) # Wider
                                     )
                action_area.controls.append(start_button)

                if not can_host_start:
                    needed_lobby = num_players_setting_lobby - current_player_count
                    if needed_lobby > 0 :
                         action_area.controls.append(ft.Text(f"تحتاج لـ {needed_lobby} لاعبين إضافيين للبدء حسب الإعداد.", color=ft.Colors.ORANGE_ACCENT_700, text_align=ft.TextAlign.CENTER, size=14))
                    elif current_player_count < min_players_to_start: # Separate check for absolute minimum
                         action_area.controls.append(ft.Text(f"تحتاج لـ {min_players_to_start - current_player_count} لاعبين إضافيين كحد أدنى للعبة.", color=ft.Colors.RED_800, text_align=ft.TextAlign.CENTER, size=14)) # Darker Red
            else:
                 action_area.controls.append(ft.Text(f"الهوست يقوم بإعداد اللعبة لـ {num_players_setting_lobby} لاعبين.", text_align=ft.TextAlign.CENTER, size=16)) # Larger

        elif current_phase == "QUESTION_DISPLAY":
            current_q_online = gs.get("current_question", "انتظر السؤال...")
            question_display_area.controls.extend([
                ft.Text("من فينا؟ 👀", size=32, weight="bold", text_align=ft.TextAlign.CENTER), # Larger
                ft.Container( # Container for question
                    content=ft.Text(current_q_online, size=26, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, selectable=True), # Larger
                    padding=ft.padding.symmetric(horizontal=5),
                    margin=ft.margin.symmetric(vertical=5)
                )
            ])
            if current_q_online.startswith("لا توجد أسئلة"):
                if is_host:
                    action_area.controls.append(ft.ElevatedButton("إعادة تعيين الأسئلة والبدء", on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            elif is_host:
                if gs.get("skip_chances_left",0) > 0:
                    action_area.controls.append(ft.Text(f"🔄 فرص تغيير السؤال: {gs['skip_chances_left']}", size=18, text_align=ft.TextAlign.CENTER))
                    action_area.controls.append(ft.ElevatedButton("غير السؤال", on_click=lambda e: send_action_fn("SKIP_QUESTION_HOST"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
                else:
                    action_area.controls.append(ft.Text("❌ لا يمكن تغيير السؤال هذا الدور.", size=18, color=ft.Colors.RED_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
                action_area.controls.append(ft.ElevatedButton("🗳️ ابدأ التصويت على هذا السؤال", on_click=lambda e: send_action_fn("INITIATE_VOTING_HOST"), width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست لبدء التصويت أو تغيير السؤال...", text_align=ft.TextAlign.CENTER, size=16)) # Larger

        elif current_phase == "VOTING":
            question_display_area.controls.extend([
                 ft.Text("من فينا؟ 👀", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Larger
                 ft.Container(
                    content=ft.Text(f"السؤال: {gs.get('current_question', '...')}", size=22, text_align=ft.TextAlign.CENTER, selectable=True), # Larger
                    padding=5
                 )
            ])
            if current_player_name in gs.get("players_voted_this_round", []):
                action_area.controls.append(ft.Text("شكراً، تم تسجيل صوتك. في انتظار الآخرين...", size=18, text_align=ft.TextAlign.CENTER))
            else:
                action_area.controls.append(ft.Text("اختر اللاعب الذي ينطبق عليه السؤال:", size=20, text_align=ft.TextAlign.CENTER)) # Larger
                
                # Using ResponsiveRow for vote buttons
                online_vote_buttons_row = ft.ResponsiveRow(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10, run_spacing=10
                )
                for p_name_option_online in players_in_room.keys(): # Vote for anyone
                    vote_btn_online = ft.ElevatedButton(
                        p_name_option_online,
                        height=55, # Consistent height
                        on_click=lambda e, choice=p_name_option_online: send_action_fn("CAST_PLAYER_VOTE", {"voted_for": choice}),
                        col={"xs": 6, "sm": 4}, # 2-3 buttons per row
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                    online_vote_buttons_row.controls.append(ft.Container(content=vote_btn_online, alignment=ft.alignment.center))
                action_area.controls.append(online_vote_buttons_row)


        elif current_phase == "RESULTS":
            question_display_area.controls.extend([
                ft.Text("📊 نتيجة التصويت للسؤال:", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Larger
                ft.Container(
                    content=ft.Text(f"{gs.get('last_question_answered', '...')}", size=20, text_align=ft.TextAlign.CENTER, selectable=True), # Larger
                    padding=5
                )
            ])

            vote_counts_results = gs.get("last_vote_counts", {})
            total_votes_cast_results = sum(vote_counts_results.values())
            sorted_vote_results = sorted(vote_counts_results.items(), key=lambda item: item[1], reverse=True)

            rows_online = [] # Renamed
            for name, count in sorted_vote_results:
                percentage = (count / total_votes_cast_results * 100) if total_votes_cast_results > 0 else 0
                rows_online.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(name, size=16)),
                    ft.DataCell(ft.Text(str(count), size=16)),
                    ft.DataCell(ft.Text(f"{percentage:.1f}%", size=16)),
                ]))

            dt_results_online = ft.DataTable( # Renamed
                columns=[
                    ft.DataColumn(ft.Text("اللاعب", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("الأصوات", weight=ft.FontWeight.BOLD), numeric=True),
                    ft.DataColumn(ft.Text("النسبة", weight=ft.FontWeight.BOLD), numeric=True)
                ],
                rows=rows_online,
                column_spacing=25,
                data_row_max_height=45,
                horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12)
            )
            action_area.controls.append(
                ft.Container(content=dt_results_online, width=page.width*0.9 if page.width else 380, alignment=ft.alignment.center) # Responsive width
            )

            if total_votes_cast_results > 0 and sorted_vote_results and sorted_vote_results[0][1] > 0:
                max_vote_count_res = sorted_vote_results[0][1]
                most_voted_players_res = [name for name, count in sorted_vote_results if count == max_vote_count_res]
                action_area.controls.append(ft.Text(f"الأكثر حصولاً على الأصوات: {', '.join(most_voted_players_res)}", size=22, weight="bold", color=ft.Colors.PRIMARY, text_align=ft.TextAlign.CENTER))
            else:
                 action_area.controls.append(ft.Text("لم يتم تسجيل أي أصوات أو لا يوجد فائز واضح.", size=18, text_align=ft.TextAlign.CENTER))

            if is_host:
                 action_area.controls.append(ft.ElevatedButton("🔁 سؤال جديد", on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else: # Non-host message
                 action_area.controls.append(ft.Text("في انتظار الهوست لطرح سؤال جديد...", text_align=ft.TextAlign.CENTER, size=16))


        if page.client_storage:
            log_debug_online(f"EXECUTING page.update() for phase {current_phase}")
            page.update()

    def on_server_message_online(*args_received):
        if not page.client_storage: return
        # log_debug_online(f"MINFINA_PUBSUB_RAW_ARGS_RECEIVED: {args_received}") # Can be verbose
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
        # log_debug_online(f"Processing MinFina PubSub: Type: {msg_type}") # Can be verbose
        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT", "HOST_CHANGED_NUM_PLAYERS"]: # Added new type
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online(room_state)
        elif msg_type == "ACTION_ERROR":
            error_msg = msg_data.get("message", "حدث خطأ ما.")
            if page.client_storage:
                 page.snack_bar = ft.SnackBar(ft.Text(error_msg, text_align=ft.TextAlign.CENTER), open=True) # Centered text
                 page.update()

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online)
    log_debug_online(f"Subscribed to topic: room_{room_code}")

    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        log_debug_online("Found initial room data for Min Fina on client load.")
        update_ui_from_server_state_online(initial_room_data)
    else:
        log_debug_online(f"Room {room_code} not found in game_rooms_ref for Min Fina on client load.")
        status_text.value = "خطأ في الاتصال بغرفة 'من فينا'."


    # Construct the main layout
    online_main_content_column.controls.extend([
        ft.Row(
            [page_title, ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=30)], # Larger icon
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=5, thickness=1.5),
        status_text,
        ft.Divider(height=5, thickness=1.5),
        question_display_area,
        ft.ResponsiveRow(
            [
                ft.Container( # Player List Container
                    content=player_list_display,
                    padding=10,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.6, ft.Colors.OUTLINE)),
                    border_radius=10,
                    col={"xs": 12, "md": 4},
                    margin=ft.margin.only(bottom=15 if page.width and page.width < 768 else 0), # Margin when stacked
                    # min_height=150 # Ensure it has some height even if empty initially
                ),
                ft.Container( # Action Area Container
                    content=action_area,
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
            content=online_main_content_column,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=10, vertical=10)
        )
    ]


# --- GAME ENTRY POINT ---
def min_fina_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return min_fina_offline_logic(page, go_home_fn)
    else:
        if not all([room_code, player_name, game_rooms_ref is not None]): # Check game_rooms_ref properly
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة للعب 'من فينا؟' أونلاين."), alignment=ft.alignment.center, expand=True)]

        def send_minfina_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "min_fina", action_type, payload or {})

        return min_fina_online_logic(page, go_home_fn, send_minfina_action_to_server_wrapper, room_code, player_name, game_rooms_ref)