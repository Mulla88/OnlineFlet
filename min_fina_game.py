
# min_fina_game.py
import flet as ft
import random
from min_fina_questions import min_fina_questions 

# --- OFFLINE MODE LOGIC ---
def min_fina_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {}

    def reset_offline_state():
        offline_state.clear()
        offline_state.update({
            "page_step": "setup_player_count", # Start with setup
            "num_players": 3, "player_names": [],
            "current_question": None, "used_questions": set(),
            "votes": {}, 
            "current_voting_player_index": 0, 
            "skip_chances_offline": 2,
            "name_inputs_offline": [] 
        })
        update_offline_ui() # Update UI after reset

    offline_main_column = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, 
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
    
    def set_offline_page_step(step_name):
        offline_state["page_step"] = step_name
        update_offline_ui()

    def choose_new_question_offline():
        s = offline_state
        available = list(set(min_fina_questions) - s.get("used_questions", set()))
        if not available:
            s["used_questions"] = set() 
            available = list(min_fina_questions)
        if not available: 
            s["current_question"] = "لا توجد أسئلة متبقية!"
            return
        s["current_question"] = random.choice(available)
        s.setdefault("used_questions", set()).add(s["current_question"])


    def update_offline_ui():
        offline_main_column.controls.clear()
        s = offline_state

        # "rules" step handled by app.py
        if s["page_step"] == "setup_player_count":
            offline_main_column.controls.append(ft.Text("اختر عدد اللاعبين (3-12):", size=22))
            num_display_offline = ft.Text(str(s["num_players"]), size=24)
            def update_num_offline(delta):
                s["num_players"] = max(3, min(12, s["num_players"] + delta))
                num_display_offline.value = str(s["num_players"])
                if page.client_storage: page.update(num_display_offline) # CORRECTED
            offline_main_column.controls.extend([
                num_display_offline,
                ft.Row([
                    ft.IconButton(ft.icons.REMOVE, on_click=lambda e: update_num_offline(-1)),
                    ft.IconButton(ft.icons.ADD, on_click=lambda e: update_num_offline(1)),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.ElevatedButton("التالي: إدخال الأسماء", on_click=lambda e: set_offline_page_step("input_player_names"), width=200)
            ])
        elif s["page_step"] == "input_player_names":
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء اللاعبين:", size=24))
            s["name_inputs_offline"] = [ft.TextField(label=f"اللاعب {i+1}", width=300) for i in range(s["num_players"])]
            offline_main_column.controls.extend(s["name_inputs_offline"])
            def save_names_offline_minfina(e):
                names = [tf.value.strip() for tf in s["name_inputs_offline"] if tf.value.strip()]
                if len(names) != s["num_players"] or len(set(names)) != len(names):
                    page.snack_bar = ft.SnackBar(ft.Text("الأسماء يجب أن تكون فريدة ومكتملة!"), open=True)
                    if page.client_storage: page.update()
                    return
                s["player_names"] = names
                s["used_questions"] = set() 
                s["skip_chances_offline"] = 2
                choose_new_question_offline()
                set_offline_page_step("question_display_offline")
            offline_main_column.controls.append(ft.ElevatedButton("ابدأ اللعبة", on_click=save_names_offline_minfina, width=200))

        elif s["page_step"] == "question_display_offline":
            offline_main_column.controls.extend([
                ft.Text("من فينا؟ 👀", size=28, weight="bold"),
                ft.Text(s.get("current_question", "تحميل السؤال..."), size=22, text_align=ft.TextAlign.CENTER, weight="bold"),
            ])
            if s.get("current_question", "").startswith("لا توجد أسئلة"):
                 offline_main_column.controls.append(ft.ElevatedButton("🏠 العودة للقائمة", on_click=go_home_fn))
            else:
                if s["skip_chances_offline"] > 0:
                    offline_main_column.controls.append(ft.Text(f"فرص تغيير السؤال المتبقية: {s['skip_chances_offline']}", size=16))
                    offline_main_column.controls.append(ft.ElevatedButton("🔄 تغيير السؤال", on_click=lambda e: skip_question_offline(), width=200))
                else:
                    offline_main_column.controls.append(ft.Text("❌ لا يمكن تغيير السؤال.", size=16, color=ft.colors.RED_ACCENT_700))
                offline_main_column.controls.append(ft.ElevatedButton("🗳️ بدء التصويت", on_click=lambda e: start_voting_offline(), width=200))

        elif s["page_step"] == "voting_offline":
            voter = s["player_names"][s["current_voting_player_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"دور اللاعب: {voter} للتصويت.", size=22, weight="bold"),
                ft.Text(f"السؤال: {s.get('current_question','')}", size=18, text_align=ft.TextAlign.CENTER),
                ft.Text("اختر اللاعب الذي ينطبق عليه السؤال:", size=16)
            ])
            vote_options_area = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            for p_name_option in s["player_names"]:
                vote_options_area.controls.append(
                    ft.ElevatedButton(p_name_option, width=200, on_click=lambda e, choice=p_name_option: cast_vote_offline(choice))
                )
            offline_main_column.controls.append(vote_options_area)

        elif s["page_step"] == "results_offline":
            offline_main_column.controls.extend([
                ft.Text("📊 نتيجة التصويت", size=24, weight="bold"),
                ft.Text(f"السؤال كان: {s.get('current_question', '')}", size=18, text_align=ft.TextAlign.CENTER),
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
                    ft.DataCell(ft.Text(name)),
                    ft.DataCell(ft.Text(str(count))),
                    ft.DataCell(ft.Text(f"{percentage:.1f}%")),
                ]))
            
            dt = ft.DataTable(
                columns=[ft.DataColumn(ft.Text("اللاعب")), ft.DataColumn(ft.Text("الأصوات")), ft.DataColumn(ft.Text("النسبة"))],
                rows=rows,
                column_spacing=20,
            )
            offline_main_column.controls.append(ft.Container(content=dt, width=page.width*0.8 if page.width else 400, alignment=ft.alignment.top_center))


            if total_votes_cast > 0 and sorted_results and sorted_results[0][1] > 0:
                max_vote_count = sorted_results[0][1]
                most_voted_players = [name for name, count in sorted_results if count == max_vote_count]
                offline_main_column.controls.append(ft.Text(f"الأكثر حصولاً على الأصوات: {', '.join(most_voted_players)}", size=20, weight="bold", color="primary"))
            else:
                 offline_main_column.controls.append(ft.Text("لم يتم تسجيل أي أصوات أو لا يوجد فائز واضح.", size=18))
            
            offline_main_column.controls.extend([
                 ft.ElevatedButton("🔁 سؤال جديد", on_click=lambda e: restart_round_offline(), width=200),
                 ft.ElevatedButton("🏠 العودة للقائمة", on_click=go_home_fn, width=200) 
            ])
        else: # Fallback for unknown step
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['page_step']}'"))
            offline_main_column.controls.append(ft.ElevatedButton("العودة للرئيسية", on_click=go_home_fn))


        if page.client_storage: page.update()

    def skip_question_offline():
        s = offline_state
        if s["skip_chances_offline"] > 0:
            s["skip_chances_offline"] -= 1
            choose_new_question_offline()
            update_offline_ui() 

    def start_voting_offline():
        s = offline_state
        s["votes"] = {}
        s["current_voting_player_index"] = 0
        set_offline_page_step("voting_offline")

    def cast_vote_offline(chosen_player):
        s = offline_state
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
        choose_new_question_offline()
        set_offline_page_step("question_display_offline")

    reset_offline_state()
    return [ft.Container(content=offline_main_column, expand=True, alignment=ft.alignment.top_center, padding=10)]

# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def min_fina_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    page_title = ft.Text(f"لعبة من فينا؟ - غرفة: {room_code}", size=20, weight="bold")
    status_text = ft.Text("...", size=18, weight="bold", text_align=ft.TextAlign.CENTER)
    player_list_display = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=5, height=150, alignment=ft.MainAxisAlignment.START)
    action_area = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, scroll=ft.ScrollMode.ADAPTIVE) 
    question_display_area = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5, alignment=ft.MainAxisAlignment.CENTER)
    
    online_main_container = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

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
        
        player_list_display.controls.clear()
        num_players_denominator = gs.get("num_players_setting", len(players_in_room))
        player_list_display.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}/{num_players_denominator}):", weight="bold"))

        for p_name_iter, p_data_iter in players_in_room.items():
            voted_status = " (صوّت ✔️)" if p_name_iter in gs.get("players_voted_this_round", []) and current_phase == "VOTING" else ""
            player_list_display.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}{voted_status}")
            )
        
        action_area.controls.clear()
        question_display_area.controls.clear()

        if current_phase == "LOBBY":
            min_players_to_start = gs.get("min_players_for_game", 3)
            current_player_count = len(players_in_room)
            
            action_area.controls.append(ft.Text(f"في انتظار انضمام اللاعبين. مطلوب {gs.get('num_players_setting', min_players_to_start)} لاعبين للبدء.", text_align=ft.TextAlign.CENTER))
            
            if is_host:
                can_host_start = current_player_count >= gs.get("num_players_setting", min_players_to_start) and \
                                 current_player_count >= min_players_to_start

                start_button = ft.ElevatedButton("🚀 ابدأ اللعبة / سؤال جديد", 
                                     on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"),
                                     disabled=not can_host_start,
                                     width=250, height=50
                                     )
                action_area.controls.append(start_button)

                if not can_host_start:
                    needed = gs.get("num_players_setting", min_players_to_start) - current_player_count
                    if needed > 0 :
                         action_area.controls.append(ft.Text(f"تحتاج لـ {needed} لاعبين إضافيين للبدء.", color=ft.colors.ORANGE_ACCENT_700, text_align=ft.TextAlign.CENTER))
                    elif current_player_count < min_players_to_start:
                         action_area.controls.append(ft.Text(f"تحتاج لـ {min_players_to_start - current_player_count} لاعبين إضافيين كحد أدنى.", color=ft.colors.RED_700, text_align=ft.TextAlign.CENTER))
            else:
                 action_area.controls.append(ft.Text(f"الهوست يقوم بإعداد اللعبة لـ {gs.get('num_players_setting', min_players_to_start)} لاعبين.", text_align=ft.TextAlign.CENTER))
        
        elif current_phase == "QUESTION_DISPLAY":
            question_display_area.controls.extend([
                ft.Text("من فينا؟ 👀", size=28, weight="bold"),
                ft.Text(gs.get("current_question", "انتظر السؤال..."), size=22, text_align=ft.TextAlign.CENTER, weight="bold", selectable=True)
            ])
            if gs.get("current_question","").startswith("لا توجد أسئلة"):
                if is_host:
                    action_area.controls.append(ft.ElevatedButton("إعادة تعيين الأسئلة والبدء", on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"))) 
            elif is_host:
                if gs.get("skip_chances_left",0) > 0:
                    action_area.controls.append(ft.Text(f"فرص تغيير السؤال: {gs['skip_chances_left']}", size=16))
                    action_area.controls.append(ft.ElevatedButton("🔄 تغيير السؤال", on_click=lambda e: send_action_fn("SKIP_QUESTION_HOST")))
                else:
                    action_area.controls.append(ft.Text("❌ لا يمكن تغيير السؤال.", size=16, color=ft.colors.RED_ACCENT_700))
                action_area.controls.append(ft.ElevatedButton("🗳️ ابدأ التصويت على هذا السؤال", on_click=lambda e: send_action_fn("INITIATE_VOTING_HOST")))
            else: 
                action_area.controls.append(ft.Text("في انتظار الهوست لبدء التصويت أو تغيير السؤال...", text_align=ft.TextAlign.CENTER))
        
        elif current_phase == "VOTING":
            question_display_area.controls.extend([
                 ft.Text("من فينا؟ 👀", size=24, weight="bold"),
                 ft.Text(f"السؤال: {gs.get('current_question', '...')}", size=20, text_align=ft.TextAlign.CENTER, selectable=True),
            ])
            if current_player_name in gs.get("players_voted_this_round", []):
                action_area.controls.append(ft.Text("شكراً، تم تسجيل صوتك. في انتظار الآخرين...", size=18, text_align=ft.TextAlign.CENTER))
            else:
                action_area.controls.append(ft.Text("اختر اللاعب الذي ينطبق عليه السؤال:", size=18))
                vote_buttons_grid = ft.GridView(
                    expand=False, runs_count=2, max_extent=150, child_aspect_ratio=2.5, 
                    spacing=5, run_spacing=5, padding=5
                )
                for p_name_option in players_in_room.keys(): 
                    vote_buttons_grid.controls.append(
                        ft.ElevatedButton(p_name_option, width=140, height=50, on_click=lambda e, choice=p_name_option: send_action_fn("CAST_PLAYER_VOTE", {"voted_for": choice}))
                    )
                action_area.controls.append(vote_buttons_grid)

        elif current_phase == "RESULTS":
            question_display_area.controls.extend([
                ft.Text("📊 نتيجة التصويت للسؤال:", size=24, weight="bold"),
                ft.Text(f"{gs.get('last_question_answered', '...')}", size=18, text_align=ft.TextAlign.CENTER, selectable=True),
            ])
            
            vote_counts_results = gs.get("last_vote_counts", {})
            total_votes_cast_results = sum(vote_counts_results.values())
            sorted_vote_results = sorted(vote_counts_results.items(), key=lambda item: item[1], reverse=True)

            rows = []
            for name, count in sorted_vote_results:
                percentage = (count / total_votes_cast_results * 100) if total_votes_cast_results > 0 else 0
                rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(name)),
                    ft.DataCell(ft.Text(str(count))),
                    ft.DataCell(ft.Text(f"{percentage:.1f}%")),
                ]))
            
            dt_results = ft.DataTable(
                columns=[ft.DataColumn(ft.Text("اللاعب")), ft.DataColumn(ft.Text("الأصوات")), ft.DataColumn(ft.Text("النسبة"))],
                rows=rows, column_spacing=20
            )
            action_area.controls.append(ft.Container(content=dt_results, alignment=ft.alignment.top_center))

            if total_votes_cast_results > 0 and sorted_vote_results and sorted_vote_results[0][1] > 0:
                max_vote_count_res = sorted_vote_results[0][1]
                most_voted_players_res = [name for name, count in sorted_vote_results if count == max_vote_count_res]
                action_area.controls.append(ft.Text(f"الأكثر حصولاً على الأصوات: {', '.join(most_voted_players_res)}", size=20, weight="bold", color="primary", text_align=ft.TextAlign.CENTER))
            else:
                 action_area.controls.append(ft.Text("لم يتم تسجيل أي أصوات أو لا يوجد فائز واضح.", size=18, text_align=ft.TextAlign.CENTER))
            
            if is_host:
                 action_area.controls.append(ft.ElevatedButton("🔁 سؤال جديد", on_click=lambda e: send_action_fn("START_NEW_QUESTION_HOST"), width=200))
            # Global home button handles "Back to Main Menu"

        if page.client_storage:
            log_debug_online(f"EXECUTING page.update() for phase {current_phase}")
            page.update()

    def on_server_message_online(*args_received):
        if not page.client_storage: return
        log_debug_online(f"MINFINA_PUBSUB_RAW_ARGS_RECEIVED: {args_received}")
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]   
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
        log_debug_online(f"Processing MinFina PubSub: Type: {msg_type}")
        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online(room_state)
        elif msg_type == "ACTION_ERROR": 
            error_msg = msg_data.get("message", "حدث خطأ ما.")
            if page.client_storage:
                 page.snack_bar = ft.SnackBar(ft.Text(error_msg), open=True); page.update()

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online)
    log_debug_online(f"Subscribed to topic: room_{room_code}")

    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data: 
        log_debug_online("Found initial room data for Min Fina on client load.")
        update_ui_from_server_state_online(initial_room_data)
    else:
        log_debug_online(f"Room {room_code} not found in game_rooms_ref for Min Fina on client load.")
        status_text.value = "خطأ في الاتصال بغرفة 'من فينا'."

    online_main_container.controls.extend([
        ft.Row([page_title, ft.IconButton(ft.icons.HOME, tooltip="العودة للرئيسية", on_click=go_home_fn)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(), status_text, ft.Divider(),
        question_display_area, 
        ft.Row([
            ft.Container(content=player_list_display, padding=10, border=ft.border.all(1, "outline"), border_radius=5, width=250, margin=ft.margin.only(right=10)),
            ft.VerticalDivider(),
            ft.Container(content=action_area, padding=10, expand=True, alignment=ft.alignment.top_center)
        ], vertical_alignment=ft.CrossAxisAlignment.START, expand=True),
    ])
    return [online_main_container]


# --- GAME ENTRY POINT ---
def min_fina_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return min_fina_offline_logic(page, go_home_fn)
    else:
        if not all([room_code, player_name, game_rooms_ref]):
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة للعب 'من فينا؟' أونلاين."), alignment=ft.alignment.center, expand=True)]
        
        def send_minfina_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "min_fina", action_type, payload or {})
            
        return min_fina_online_logic(page, go_home_fn, send_minfina_action_to_server_wrapper, room_code, player_name, game_rooms_ref)