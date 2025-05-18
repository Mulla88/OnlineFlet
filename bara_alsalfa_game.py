# bara_alsalfa_game.py
import flet as ft
import random
from categories import categories 

# --- OFFLINE MODE LOGIC ---
def bara_alsalfa_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {}

    def reset_offline_state():
        offline_state.clear()
        offline_state.update({
            "page": "setup_players", # CHANGED: Start with player setup
            "num_players": 3,
            "player_names": [],
            "selected_category": None,
            "bara_player": None,
            "game_word": None,
            "roles": {}, 
            "current_role_reveal_index": 0,
            "question_pairs": [],
            "current_question_pair_index": 0,
            "votes": {}, 
            "current_voting_player_index": 0,
            "round_scores": {}, 
            "global_scores": {}, 
            "guess_word_options": [],
            "bara_guess_result_text": "",
            "used_words_in_category": set()
        })
        update_offline_ui() # Update UI after reset

    offline_content_area = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)

    def update_offline_ui():
        offline_content_area.controls.clear()
        s = offline_state 

        # "rules" step is handled by app.py now
        if s["page"] == "setup_players":
            offline_content_area.controls.extend([
                ft.Text("عدد اللاعبين:", size=18),
                ft.Row([
                    ft.IconButton(ft.icons.REMOVE, on_click=lambda e: change_num_players_offline(-1)),
                    ft.Text(str(s["num_players"]), size=24),
                    ft.IconButton(ft.icons.ADD, on_click=lambda e: change_num_players_offline(1)),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.ElevatedButton("التالي", on_click=lambda e: set_offline_page("input_names"), width=200, height=50),
                ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home_fn, width=200, height=50)
            ])
        elif s["page"] == "input_names":
            name_inputs = [ft.TextField(label=f"اسم اللاعب {i+1}", width=300) for i in range(s["num_players"])]
            offline_content_area.controls.append(ft.Text("أدخل أسماء اللاعبين:", size=20))
            offline_content_area.controls.extend(name_inputs)
            def save_player_names_offline(e):
                names = [tf.value.strip() for tf in name_inputs if tf.value.strip()]
                if len(names) != s["num_players"] or len(set(names)) != len(names):
                    page.snack_bar = ft.SnackBar(ft.Text("الأسماء يجب أن تكون فريدة ومكتملة!"), open=True)
                    if page.client_storage: page.update()
                    return
                s["player_names"] = names
                s["global_scores"] = {name: 0 for name in names}
                set_offline_page("select_category")
            offline_content_area.controls.append(ft.ElevatedButton("تأكيد الأسماء", on_click=save_player_names_offline, width=200, height=50))

        elif s["page"] == "select_category":
            cat_dropdown = ft.Dropdown(label="اختر القائمة", options=[ft.dropdown.Option(key=cat, text=cat) for cat in categories.keys()], width=300)
            def confirm_cat_offline(e):
                if cat_dropdown.value:
                    s["selected_category"] = cat_dropdown.value
                    s["used_words_in_category"] = set() 
                    assign_roles_and_word_offline()
                    set_offline_page("role_reveal_handoff")
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("الرجاء اختيار قائمة."), open=True)
                    if page.client_storage: page.update()
            offline_content_area.controls.extend([
                ft.Text("اختر قائمة الكلمات:", size=20), cat_dropdown,
                ft.ElevatedButton("تأكيد القائمة", on_click=confirm_cat_offline, width=200, height=50)
            ])

        elif s["page"] == "role_reveal_handoff":
            player_to_see_role = s["player_names"][s["current_role_reveal_index"]]
            offline_content_area.controls.extend([
                ft.Text(f"📱 أعطِ الجهاز إلى: {player_to_see_role}", size=24, weight="bold"),
                ft.ElevatedButton("👀 عرض دوري", on_click=lambda e: set_offline_page("display_individual_role"), width=200, height=50)
            ])
        
        elif s["page"] == "display_individual_role":
            player_name = s["player_names"][s["current_role_reveal_index"]]
            role = s["roles"][player_name]
            offline_content_area.controls.extend([
                ft.Text(f"{player_name}، دورك هو:", size=22),
                ft.Text(role, size=28, weight="bold", color=(ft.colors.RED_ACCENT_700 if role == "برة السالفة" else ft.colors.GREEN_ACCENT_700)),
                ft.Text(f"القائمة: {s['selected_category']}", size=18),
            ])
            if role == "داخل السالفة" and s.get("game_word"):
                offline_content_area.controls.append(ft.Text(f"الكلمة السرية هي: {s['game_word']}", size=20, color=ft.colors.BLUE_700))
            
            offline_content_area.controls.append(ft.ElevatedButton("فهمت، التالي", on_click=next_player_role_reveal_offline, width=200, height=50))

        elif s["page"] == "discussion_or_vote":
            offline_content_area.controls.extend([
                ft.Text("الجميع عرف دوره!", size=24, weight="bold"),
                ft.Text("يمكنكم الآن البدء في طرح الأسماء على بعضكم البعض أو الانتقال مباشرة للتصويت.", size=18, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("🎤 بدء جولة أسئلة (اختياري)", on_click=start_question_round_offline, width=250, height=50),
                ft.ElevatedButton("🗳️ الانتقال للتصويت", on_click=start_voting_offline, width=250, height=50)
            ])
        
        elif s["page"] == "question_time_offline":
            if s["current_question_pair_index"] < len(s["question_pairs"]):
                asker, askee = s["question_pairs"][s["current_question_pair_index"]]
                offline_content_area.controls.extend([
                    ft.Text(f"🎤 {asker} يسأل {askee}", size=22),
                    ft.Text("اطرح سؤالك وحاول كشف من هو 'برة السالفة'!", size=16, text_align=ft.TextAlign.CENTER),
                    ft.ElevatedButton("السؤال التالي", on_click=next_question_pair_offline, width=200, height=50)
                ])
            else: 
                set_offline_page("discussion_or_vote")


        elif s["page"] == "voting_offline":
            voter_name = s["player_names"][s["current_voting_player_index"]]
            options = [ft.dropdown.Option(text=p_name_iter) for p_name_iter in s["player_names"] if p_name_iter != voter_name] 
            vote_dropdown = ft.Dropdown(label=f"{voter_name}، صوت ضد من تعتقد أنه 'برة السالفة'", options=options, width=300)
            
            def cast_vote_offline_click(e):
                if vote_dropdown.value:
                    s["votes"][voter_name] = vote_dropdown.value
                    s["current_voting_player_index"] += 1
                    if s["current_voting_player_index"] >= len(s["player_names"]):
                        process_voting_results_offline()
                        set_offline_page("vote_results_offline")
                    else:
                        update_offline_ui() 
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("الرجاء اختيار لاعب للتصويت ضده."), open=True)
                    if page.client_storage: page.update()

            offline_content_area.controls.extend([
                ft.Text(f"دور {voter_name} للتصويت:", size=22),
                vote_dropdown,
                ft.ElevatedButton("تأكيد التصويت", on_click=cast_vote_offline_click, width=200, height=50)
            ])

        elif s["page"] == "vote_results_offline":
            offline_content_area.controls.append(ft.Text("📊 نتائج التصويت:", size=24, weight="bold"))
            vote_summary_rows = []
            for voter, voted_for in s["votes"].items():
                vote_summary_rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(voter)), ft.DataCell(ft.Text(voted_for))]))
            
            if vote_summary_rows:
                 offline_content_area.controls.append(ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("اللاعب المصوِّت")), ft.DataColumn(ft.Text("صوَّت ضد"))],
                    rows=vote_summary_rows
                 ))

            offline_content_area.controls.extend([
                ft.Text(f"الشخص الذي كان 'برة السالفة' هو: {s['bara_player']}", size=20, color=ft.colors.RED_700),
                ft.Text("النقاط من التصويت الصحيح:", size=18)
            ])
            initial_round_scores = s.get("initial_round_scores_from_voting", {})
            for p_name, score_increase in initial_round_scores.items():
                if score_increase > 0 : 
                    offline_content_area.controls.append(ft.Text(f"{p_name}: +{score_increase} نقاط", color=ft.colors.GREEN))
            
            offline_content_area.controls.append(ft.ElevatedButton(f"دع {s['bara_player']} يخمن الكلمة", on_click=lambda e: set_offline_page("bara_guess_word_offline"), width=250, height=50))


        elif s["page"] == "bara_guess_word_offline":
            offline_content_area.controls.append(ft.Text(f"{s['bara_player']}، حاول تخمين الكلمة السرية!", size=22))
            offline_content_area.controls.append(ft.Text(f"القائمة كانت: {s['selected_category']}", size=16))
            
            options_container = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            temp_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
            
            for i, word_option in enumerate(s.get("guess_word_options", [])):
                btn = ft.ElevatedButton(
                    word_option, 
                    on_click=lambda e, wo=word_option: handle_bara_guess_offline(wo),
                    width=180, height=50
                )
                temp_row.controls.append(btn)
                if (i + 1) % 2 == 0 or i == len(s["guess_word_options"]) - 1 : 
                    options_container.controls.append(temp_row)
                    temp_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
            if temp_row.controls: 
                 options_container.controls.append(temp_row)

            offline_content_area.controls.append(options_container)


        elif s["page"] == "round_over_offline":
            offline_content_area.controls.extend([
                ft.Text("🎉 انتهت الجولة!", size=26, weight="bold"),
                ft.Text(s["bara_guess_result_text"], size=20, weight="bold", text_align=ft.TextAlign.CENTER,
                          color=(ft.colors.GREEN_700 if "صحيح" in s["bara_guess_result_text"] else ft.colors.RED_700)),
                ft.Text("النقاط الإجمالية:", size=22)
            ])
            score_rows = []
            sorted_global_scores = sorted(s["global_scores"].items(), key=lambda item: item[1], reverse=True)
            for p_name, total_score in sorted_global_scores:
                 score_rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(p_name)), ft.DataCell(ft.Text(str(total_score)))]))
            
            if score_rows:
                offline_content_area.controls.append(ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("اللاعب")), ft.DataColumn(ft.Text("النقاط"))],
                    rows=score_rows
                ))

            offline_content_area.controls.extend([
                ft.ElevatedButton("🔄 جولة جديدة بنفس اللاعبين", on_click=restart_round_offline, width=250, height=50),
                ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home_fn, width=250, height=50)
            ])

        else: 
            offline_content_area.controls.append(ft.Text(f"صفحة غير معروفة: {s['page']}"))
            offline_content_area.controls.append(ft.ElevatedButton("ابدأ من جديد", on_click=lambda e: set_offline_page("setup_players"))) # Go to setup
        
        if page.client_storage: page.update()

    def set_offline_page(page_name):
        offline_state["page"] = page_name
        update_offline_ui()

    def change_num_players_offline(delta):
        offline_state["num_players"] = max(3, min(15, offline_state["num_players"] + delta))
        update_offline_ui()

    def assign_roles_and_word_offline():
        s = offline_state
        if not s["player_names"]: 
            print("Error in assign_roles_and_word_offline: No player names.")
            set_offline_page("input_names") 
            return
        s["bara_player"] = random.choice(s["player_names"])
        
        cat_words = categories.get(s.get("selected_category",""), [])
        available_words = [word for word in cat_words if word not in s["used_words_in_category"]]
        if not available_words and cat_words: 
            s["used_words_in_category"] = set() 
            available_words = list(cat_words)
        
        if not available_words: 
            s["game_word"] = "لا توجد كلمات!" 
        else:
            s["game_word"] = random.choice(available_words)
            s["used_words_in_category"].add(s["game_word"])

        s["roles"] = {name: ("برة السالفة" if name == s["bara_player"] else "داخل السالفة") for name in s["player_names"]}
        s["current_role_reveal_index"] = 0
        s["round_scores"] = {name: 0 for name in s["player_names"]}


    def next_player_role_reveal_offline(e):
        s = offline_state
        s["current_role_reveal_index"] += 1
        if s["current_role_reveal_index"] >= len(s["player_names"]):
            set_offline_page("discussion_or_vote")
        else:
            set_offline_page("role_reveal_handoff")
            
    def start_question_round_offline(e):
        s = offline_state
        player_list = list(s["player_names"])
        random.shuffle(player_list)
        s["question_pairs"] = [(player_list[i], player_list[(i + 1) % len(player_list)]) for i in range(len(player_list))]
        s["current_question_pair_index"] = 0
        if s["question_pairs"]:
            set_offline_page("question_time_offline")
        else: 
            set_offline_page("discussion_or_vote")

    def next_question_pair_offline(e):
        s = offline_state
        s["current_question_pair_index"] += 1
        if s["current_question_pair_index"] >= len(s.get("question_pairs",[])):
            set_offline_page("discussion_or_vote") 
        else:
            update_offline_ui() 

    def start_voting_offline(e):
        s = offline_state
        s["votes"] = {}
        s["current_voting_player_index"] = 0
        set_offline_page("voting_offline")

    def process_voting_results_offline():
        s = offline_state
        s["initial_round_scores_from_voting"] = {name: 0 for name in s["player_names"]}
        
        correct_voters_count = 0
        for voter, voted_target in s.get("votes", {}).items():
            if voted_target == s.get("bara_player"):
                s["initial_round_scores_from_voting"][voter] = s["initial_round_scores_from_voting"].get(voter, 0) + 5
                correct_voters_count +=1
        
        if correct_voters_count == 0 and len(s["player_names"]) > 1 and s.get("bara_player"):
            s["initial_round_scores_from_voting"][s["bara_player"]] = s["initial_round_scores_from_voting"].get(s["bara_player"], 0) + (len(s["player_names"]) - 1) * 2
        
        s["round_scores"] = s["initial_round_scores_from_voting"].copy()

        cat_words = categories.get(s.get("selected_category",""), [])
        other_words = [word for word in cat_words if word != s.get("game_word")]
        
        num_options_needed = min(7, len(other_words)) 
        s["guess_word_options"] = random.sample(other_words, num_options_needed)
        if s.get("game_word") and s.get("game_word") not in s["guess_word_options"]: # Ensure game_word is an option
            s["guess_word_options"].append(s["game_word"])
        random.shuffle(s["guess_word_options"])
        
    def handle_bara_guess_offline(guessed_word):
        s = offline_state
        if guessed_word == s.get("game_word"):
            s["round_scores"][s["bara_player"]] = s["round_scores"].get(s["bara_player"], 0) + 10
            s["bara_guess_result_text"] = f"✅ صحيح! {s.get('bara_player','')} خمن الكلمة ({s.get('game_word','')}) وحصل على 10 نقاط إضافية."
        else:
            s["bara_guess_result_text"] = f"❌ خطأ! الكلمة الصحيحة كانت {s.get('game_word', 'غير محددة')}."
        
        for p_name, r_score in s.get("round_scores",{}).items():
            s["global_scores"][p_name] = s["global_scores"].get(p_name, 0) + r_score
            
        set_offline_page("round_over_offline")

    def restart_round_offline(e):
        s = offline_state
        # Don't reset global_scores here, only round-specific things
        s["page"] = "select_category" 
        s["selected_category"] = None 
        s["bara_player"] = None
        s["game_word"] = None
        s["roles"] = {}
        s["current_role_reveal_index"] = 0
        s["question_pairs"] = []
        s["current_question_pair_index"] = 0
        s["votes"] = {}
        s["current_voting_player_index"] = 0
        s["round_scores"] = {name: 0 for name in s["player_names"]} 
        s["initial_round_scores_from_voting"] = {}
        s["guess_word_options"] = []
        s["bara_guess_result_text"] = ""
        s["used_words_in_category"] = set() # Reset for the new category choice
        update_offline_ui() 

    reset_offline_state() # This now calls update_offline_ui()
    return [ft.Container(content=offline_content_area, expand=True, alignment=ft.alignment.top_center, padding=10)]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def bara_alsalfa_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    
    page_title = ft.Text(f"لعبة برة السالفة - غرفة: {room_code}", size=20, weight="bold")
    status_text = ft.Text("...", size=18, weight="bold", text_align=ft.TextAlign.CENTER)
    player_list_display = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=5, height=150, alignment=ft.MainAxisAlignment.START)
    action_area = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, scroll=ft.ScrollMode.ADAPTIVE) 
    role_display_area = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10) 
    
    online_container = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    def log_debug(msg):
        print(f"[BaraAlsalfa_Online_Client:{current_player_name} session:{page.session_id}] {msg}")

    def update_ui_from_server_state(room_state_from_server):
        if not page.client_storage: 
            log_debug("Page detached, skipping UI update.")
            return

        log_debug(f"Updating UI. Phase: {room_state_from_server.get('game_state',{}).get('phase')}")
        gs = room_state_from_server.get("game_state",{}) 
        players_in_room = room_state_from_server.get("players",{})
        is_host = players_in_room.get(current_player_name, {}).get("is_host", False)
        current_phase = gs.get("phase", "LOBBY")

        status_text.value = gs.get("status_message", "...")
        
        player_list_display.controls.clear()
        player_list_display.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight="bold"))
        for p_name_iter, p_data_iter in players_in_room.items():
            player_list_display.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}")
            )

        action_area.controls.clear()
        role_display_area.visible = False 

        if current_phase == "LOBBY":
            if is_host:
                cat_options = [ft.dropdown.Option(key_val) for key_val in categories.keys()] 
                category_dropdown = ft.Dropdown(
                    label="اختر القائمة", 
                    options=cat_options, 
                    width=300, 
                    value=gs.get("selected_category") 
                )
                
                start_game_button_lobby = ft.ElevatedButton(
                    "🚀 ابدأ اللعبة الآن",
                    on_click=lambda e: send_action_fn("START_GAME_HOST"),
                    width=200, height=40
                )
                
                action_area.controls.extend([
                    ft.Text("أنت الهوست. الرجاء اختيار قائمة الكلمات:"),
                    category_dropdown,
                    ft.ElevatedButton("تأكيد القائمة", 
                                     on_click=lambda e: send_action_fn("SELECT_CATEGORY_HOST", {"category": category_dropdown.value}) if category_dropdown.value else None,
                                     width=200, height=40),
                    start_game_button_lobby 
                ])

                can_start_game = gs.get("selected_category") and len(players_in_room) >= gs.get("min_players_for_game", 3)
                start_game_button_lobby.disabled = not can_start_game

                if not gs.get("selected_category"):
                    action_area.controls.append(ft.Text("(اختر قائمة أولاً لتفعيل زر بدء اللعبة)", size=12, color=ft.colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER))
                elif len(players_in_room) < gs.get("min_players_for_game", 3):
                    remaining_to_join = gs.get("min_players_for_game", 3) - len(players_in_room)
                    action_area.controls.append(ft.Text(f" (تحتاج {remaining_to_join} لاعبين إضافيين لبدء اللعبة)", size=12, color=ft.colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER))
                else: 
                     action_area.controls.append(ft.Text("(جاهز لبدء اللعبة!)", size=12, color=ft.colors.GREEN_ACCENT_700, text_align=ft.TextAlign.CENTER))
            
            else: 
                action_area.controls.append(ft.Text("في انتظار الهوست لاختيار القائمة وبدء اللعبة...", text_align=ft.TextAlign.CENTER))

        elif current_phase == "CATEGORY_SELECTED":
            action_area.controls.append(ft.Text(f"القائمة المختارة: {gs.get('selected_category', '...')}", weight="bold", text_align=ft.TextAlign.CENTER))
            if is_host:
                can_start_game_cat_selected = len(players_in_room) >= gs.get("min_players_for_game", 3)
                start_game_button_cat_selected = ft.ElevatedButton(
                    "🚀 ابدأ اللعبة الآن", 
                    on_click=lambda e: send_action_fn("START_GAME_HOST"), 
                    width=200, height=40,
                    disabled = not can_start_game_cat_selected 
                )
                action_area.controls.append(start_game_button_cat_selected)

                if not can_start_game_cat_selected:
                    remaining_to_join = gs.get("min_players_for_game", 3) - len(players_in_room)
                    action_area.controls.append(ft.Text(f" (تحتاج {remaining_to_join} لاعبين إضافيين لبدء اللعبة)", text_align=ft.TextAlign.CENTER, size=12, color=ft.colors.ON_SURFACE_VARIANT))
                else:
                    action_area.controls.append(ft.Text("(جاهز لبدء اللعبة!)", size=12, color=ft.colors.GREEN_ACCENT_700, text_align=ft.TextAlign.CENTER))
            
            else: 
                action_area.controls.append(ft.Text("في انتظار الهوست لبدء اللعبة...", text_align=ft.TextAlign.CENTER))
        
        elif current_phase == "ROLES_REVEAL":
            player_reveal_order = gs.get("player_reveal_order", [])
            current_reveal_idx = gs.get("current_role_reveal_index", 0)
            player_to_see_role = player_reveal_order[current_reveal_idx] if player_reveal_order and current_reveal_idx < len(player_reveal_order) else None
            
            if player_to_see_role == current_player_name:
                role_display_area.visible = True
                role_display_area.controls.clear()
                my_role_data = players_in_room.get(current_player_name, {})
                my_role = my_role_data.get("role", "...")
                role_display_area.controls.extend([
                    ft.Text(f"دورك هو: {my_role}", size=24, weight="bold", color=(ft.colors.RED_ACCENT_700 if my_role == "برة السالفة" else ft.colors.GREEN_ACCENT_700)),
                    ft.Text(f"القائمة: {gs.get('selected_category', '...')}", size=18)
                ])
                if my_role == "داخل السالفة" and gs.get("game_word"):
                    role_display_area.controls.append(ft.Text(f"الكلمة السرية: {gs.get('game_word', '...')}", size=20, color=ft.colors.BLUE_700))
                role_display_area.controls.append(ft.ElevatedButton("✅ تم، فهمت دوري", on_click=lambda e: send_action_fn("PLAYER_ACK_ROLE"), width=200, height=40))
                action_area.controls.append(ft.Text("الرجاء تفقد دورك في الأعلى ثم اضغط 'تم'.", text_align=ft.TextAlign.CENTER))
            elif player_to_see_role:
                action_area.controls.append(ft.Text(f"في انتظار {player_to_see_role} لتفقد دوره...", text_align=ft.TextAlign.CENTER))
            else: 
                action_area.controls.append(ft.Text("في انتظار اللاعبين لتفقد أدوارهم...", text_align=ft.TextAlign.CENTER))


        elif current_phase == "DISCUSSION":
            action_area.controls.append(ft.Text("مرحلة النقاش! حاولوا معرفة من هو 'برة السالفة'.", size=18, text_align=ft.TextAlign.CENTER))
            if is_host:
                action_area.controls.extend([
                    ft.ElevatedButton("🎤 بدء جولة أسئلة (اختياري)", on_click=lambda e: send_action_fn("START_QUESTION_ROUND_HOST"), width=250, height=40),
                    ft.ElevatedButton("🗳️ الانتقال للتصويت الآن", on_click=lambda e: send_action_fn("INITIATE_VOTE_HOST"), width=250, height=40)
                ])
            else:
                action_area.controls.append(ft.Text("الهوست يمكنه بدء جولة أسئلة أو الانتقال للتصويت.", text_align=ft.TextAlign.CENTER))

        elif current_phase == "QUESTION_TIME":
            question_pairs_list = gs.get("question_pairs", [])
            current_q_idx = gs.get("current_question_pair_index", 0)
            pair = question_pairs_list[current_q_idx] if question_pairs_list and current_q_idx < len(question_pairs_list) else (None, None)
            
            if pair[0] and pair[1]:
                 action_area.controls.append(ft.Text(f"🎤 {pair[0]} يسأل {pair[1]}", size=20, text_align=ft.TextAlign.CENTER))
            if is_host:
                action_area.controls.append(ft.ElevatedButton("السؤال التالي ⏭️", on_click=lambda e: send_action_fn("NEXT_QUESTION_PAIR_HOST"), width=200, height=40))
                action_area.controls.append(ft.ElevatedButton("إنهاء الأسئلة والانتقال للتصويت", on_click=lambda e: send_action_fn("INITIATE_VOTE_HOST"), width=250, height=40))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست لإدارة جولة الأسئلة.", text_align=ft.TextAlign.CENTER))

        elif current_phase == "VOTING":
            already_voted = current_player_name in gs.get("players_who_voted", [])
            if already_voted:
                action_area.controls.append(ft.Text("شكراً لك، تم تسجيل صوتك. في انتظار بقية اللاعبين...", size=18, text_align=ft.TextAlign.CENTER))
            else:
                vote_options = [ft.dropdown.Option(text=p_name_iter) for p_name_iter in players_in_room if p_name_iter != current_player_name] 
                vote_dropdown = ft.Dropdown(label="صوّت ضد من تعتقد أنه 'برة السالفة'", options=vote_options, width=300)
                action_area.controls.extend([
                    ft.Text("حان وقت التصويت!", size=20, text_align=ft.TextAlign.CENTER),
                    vote_dropdown,
                    ft.ElevatedButton("تأكيد التصويت", 
                                     on_click=lambda e: send_action_fn("CAST_VOTE", {"voted_for": vote_dropdown.value}) if vote_dropdown.value else None,
                                     width=200, height=40)
                ])
        
        elif current_phase == "VOTE_RESULTS":
            action_area.controls.append(ft.Text("📊 نتائج التصويت:", size=22, weight="bold"))
            
            vote_details = gs.get("votes", {})
            vote_rows = []
            for voter, voted_for in vote_details.items():
                if voted_for: 
                    vote_rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(voter)), ft.DataCell(ft.Text(voted_for))]))
            
            if vote_rows:
                action_area.controls.append(ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("اللاعب المصوِّت")), ft.DataColumn(ft.Text("صوَّت ضد"))],
                    rows=vote_rows
                ))
            else:
                action_area.controls.append(ft.Text("لم يتم تسجيل أي أصوات.", text_align=ft.TextAlign.CENTER))

            action_area.controls.append(ft.Text(f"'برة السالفة' كان: {gs.get('bara_player', '...')}", size=20, color=ft.colors.RED_700, text_align=ft.TextAlign.CENTER))
            
            round_scores_for_display = gs.get("round_scores", {})
            points_text_elements = []
            for p_name_iter, score_val in round_scores_for_display.items():
                if score_val != 0 : 
                    points_text_elements.append(ft.Text(f"{p_name_iter}: {score_val} نقاط", color=ft.colors.GREEN, text_align=ft.TextAlign.CENTER))
            
            if points_text_elements:
                action_area.controls.append(ft.Text("النقاط المكتسبة (قبل تخمين 'برة السالفة'):", size=18, text_align=ft.TextAlign.CENTER))
                action_area.controls.extend(points_text_elements)
            
            if current_player_name == gs.get("bara_player"):
                action_area.controls.append(ft.Text("أنت 'برة السالفة'! حاول تخمين الكلمة:", size=18, text_align=ft.TextAlign.CENTER))
                
                options_container_online = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                temp_row_online = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
                guess_options = gs.get("bara_guess_options", [])

                for i, word_opt in enumerate(guess_options):
                    btn = ft.ElevatedButton(word_opt, on_click=lambda e, wo=word_opt: send_action_fn("BARA_GUESS_WORD", {"word": wo}), width=150, height=40)
                    temp_row_online.controls.append(btn)
                    if (i + 1) % 2 == 0 or i == len(guess_options) - 1:
                        options_container_online.controls.append(temp_row_online)
                        temp_row_online = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
                if temp_row_online.controls:
                    options_container_online.controls.append(temp_row_online)
                action_area.controls.append(options_container_online)
            else:
                action_area.controls.append(ft.Text(f"في انتظار {gs.get('bara_player', '...')} لتخمين الكلمة...", size=18, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ROUND_OVER":
            action_area.controls.extend([
                ft.Text("🎉 انتهت الجولة!", size=26, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Text(gs.get("bara_guess_result", "..."), size=20, weight="bold", text_align=ft.TextAlign.CENTER, 
                          color=(ft.colors.GREEN_700 if "صحيح" in gs.get("bara_guess_result", "") else ft.colors.RED_700)),
                ft.Text("النقاط الإجمالية:", size=22, text_align=ft.TextAlign.CENTER)
            ])
            
            global_scores_display = gs.get("global_scores", {})
            score_table_rows = []
            sorted_scores = sorted(global_scores_display.items(), key=lambda item: item[1], reverse=True)

            for p_name_iter, total_score in sorted_scores:
                score_table_rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(p_name_iter)), ft.DataCell(ft.Text(str(total_score)))]))
            
            if score_table_rows:
                 action_area.controls.append(ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("اللاعب")), ft.DataColumn(ft.Text("النقاط"))],
                    rows=score_table_rows
                 ))
            
            if is_host:
                action_area.controls.append(ft.ElevatedButton("🔄 ابدأ جولة جديدة", on_click=lambda e: send_action_fn("NEXT_ROUND_HOST"), width=200, height=40))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست لبدء جولة جديدة...", text_align=ft.TextAlign.CENTER))


        if page.client_storage:
            log_debug(f"EXECUTING page.update() for phase {current_phase}")
            page.update()
        else:
            log_debug(f"SKIPPING page.update() because page.client_storage is None for phase {current_phase}")

    def on_server_message(*args_received): 
        if not page.client_storage: 
            log_debug("on_server_message: Page disposed.")
            return

        log_debug(f"PUBSUB_RAW_ARGS_RECEIVED: {args_received}")

        if not args_received or len(args_received) < 2: 
            log_debug("Not enough arguments received in on_server_message.")
            return
        
        msg_data = args_received[1]   
        
        if not isinstance(msg_data, dict): 
            log_debug(f"Error: Extracted msg_data is not a dictionary: type={type(msg_data)}, value={msg_data}")
            return

        msg_type = msg_data.get("type")
        log_debug(f"Processing PubSub: Type: {msg_type} from msg_data: {msg_data}") 

        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state") 
            if room_state and isinstance(room_state, dict): 
                update_ui_from_server_state(room_state)
            else:
                log_debug(f"Error: No valid room_state in message for {msg_type}. room_state: {room_state}")
        elif msg_type == "ACTION_ERROR": 
            error_msg = msg_data.get("message", "حدث خطأ ما.")
            log_debug(f"Action Error from server: {error_msg}")
            if page.client_storage:
                 page.snack_bar = ft.SnackBar(ft.Text(error_msg), open=True)
                 page.update()
        else:
            log_debug(f"Unknown message type received: {msg_type}")

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message)
    log_debug(f"Subscribed to topic: room_{room_code}")

    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        log_debug("Found initial room data on client load. Updating UI.")
        update_ui_from_server_state(initial_room_data)
    else:
        log_debug(f"Room {room_code} not found in game_rooms_ref on client load. This is problematic and client UI might be stale.")
        status_text.value = "خطأ في الاتصال بالغرفة. قد تحتاج للعودة والمحاولة مجدداً."

    online_container.controls.extend([
        ft.Row([page_title, ft.IconButton(ft.icons.HOME, tooltip="العودة للرئيسية", on_click=go_home_fn)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        status_text,
        ft.Divider(),
        role_display_area, 
        ft.Row(
            [
                ft.Container(
                    content=player_list_display, 
                    padding=10, border=ft.border.all(1, ft.colors.OUTLINE), border_radius=5,
                    width=250, margin=ft.margin.only(right=10), alignment=ft.alignment.top_left,
                ),
                ft.VerticalDivider(width=10),
                ft.Container(
                    content=action_area, 
                    padding=10, expand=True, alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    ])
    return [online_container]


# --- GAME ENTRY POINT (Called by app.py) ---
def bara_alsalfa_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return bara_alsalfa_offline_logic(page, go_home_fn)
    else:
        if not room_code or not player_name or game_rooms_ref is None:
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة للعب أونلاين."), alignment=ft.alignment.center, expand=True)]
        
        # This wrapper is called by the client UI. It then calls the main dispatcher (process_game_action in app.py)
        def send_bara_alsalfa_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "bara_alsalfa", action_type, payload or {})

        return bara_alsalfa_online_logic(page, go_home_fn, send_bara_alsalfa_action_to_server_wrapper, room_code, player_name, game_rooms_ref)