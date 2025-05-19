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
            "page": "setup_players",
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
        update_offline_ui()

    offline_content_area = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15
    )

    def update_offline_ui():
        offline_content_area.controls.clear()
        s = offline_state

        if s["page"] == "setup_players":
            offline_content_area.controls.extend([
                ft.Text("عدد اللاعبين:", size=20, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(
                    [
                        ft.IconButton(ft.Icons.REMOVE, on_click=lambda e: change_num_players_offline(-1), col={"xs": 4, "sm": 3}),
                        ft.Text(str(s["num_players"]), size=28, weight=ft.FontWeight.BOLD, col={"xs": 4, "sm": 6}, text_align=ft.TextAlign.CENTER),
                        ft.IconButton(ft.Icons.ADD, on_click=lambda e: change_num_players_offline(1), col={"xs": 4, "sm": 3}),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.ElevatedButton("التالي", on_click=lambda e: set_offline_page("input_names"), width=250, height=50),
                ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home_fn, width=250, height=50)
            ])

        elif s["page"] == "input_names":
            name_input_containers = []
            for i in range(s["num_players"]):
                name_input_containers.append(
                    ft.Container(
                        content=ft.TextField(label=f"اسم اللاعب {i+1}", text_align=ft.TextAlign.CENTER), # Centered text in TextField
                        width=page.width * 0.85 if page.width else 300,
                        alignment=ft.alignment.center
                    )
                )
            offline_content_area.controls.append(ft.Text("أدخل أسماء اللاعبين:", size=20, weight=ft.FontWeight.BOLD))
            name_inputs_actual_textfields = [container.content for container in name_input_containers]
            offline_content_area.controls.extend(name_input_containers)

            def save_player_names_offline(e):
                names = [tf.value.strip() for tf in name_inputs_actual_textfields if tf.value.strip()]
                if len(names) != s["num_players"] or len(set(names)) != len(names) or any(not n for n in names): # Added check for empty names
                    page.snack_bar = ft.SnackBar(ft.Text("الأسماء يجب أن تكون فريدة وغير فارغة ومكتملة!"), open=True)
                    if page.client_storage: page.update()
                    return
                s["player_names"] = names
                s["global_scores"] = {name: 0 for name in names}
                set_offline_page("select_category")
            offline_content_area.controls.append(ft.ElevatedButton("تأكيد الأسماء", on_click=save_player_names_offline, width=250, height=50))

        elif s["page"] == "select_category":
            cat_dropdown = ft.Dropdown(
                label="اختر القائمة",
                options=[ft.dropdown.Option(key=cat, text=cat) for cat in categories.keys()]
            )
            cat_dropdown_container = ft.Container(
                content=cat_dropdown,
                width=page.width * 0.85 if page.width else 300,
                alignment=ft.alignment.center
            )

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
                ft.Text("اختر قائمة الكلمات:", size=20, weight=ft.FontWeight.BOLD),
                cat_dropdown_container,
                ft.ElevatedButton("تأكيد القائمة", on_click=confirm_cat_offline, width=250, height=50)
            ])

        elif s["page"] == "role_reveal_handoff":
            player_to_see_role = s["player_names"][s["current_role_reveal_index"]]
            offline_content_area.controls.extend([
                ft.Text(f"📱 أعطِ الجهاز إلى:", size=22, text_align=ft.TextAlign.CENTER),
                ft.Text(player_to_see_role, size=28, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("👀 عرض دوري", on_click=lambda e: set_offline_page("display_individual_role"), width=250, height=60)
            ])

        elif s["page"] == "display_individual_role":
            player_name = s["player_names"][s["current_role_reveal_index"]]
            role = s["roles"][player_name]
            offline_content_area.controls.extend([
                ft.Text(f"{player_name}، دورك هو:", size=22, text_align=ft.TextAlign.CENTER),
                ft.Text(role, size=30, weight="bold",
                          color=(ft.Colors.RED_ACCENT_700 if role == "برة السالفة" else ft.Colors.GREEN_ACCENT_700),
                          text_align=ft.TextAlign.CENTER),
                ft.Text(f"القائمة: {s['selected_category']}", size=20, text_align=ft.TextAlign.CENTER),
            ])
            if role == "داخل السالفة" and s.get("game_word"):
                offline_content_area.controls.append(
                    ft.Text(f"الكلمة السرية هي: {s['game_word']}", size=22, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)
                )
            offline_content_area.controls.append(ft.ElevatedButton("فهمت، التالي", on_click=next_player_role_reveal_offline, width=250, height=60))

        elif s["page"] == "discussion_or_vote":
            offline_content_area.controls.extend([
                ft.Text("الجميع عرف دوره!", size=26, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Text("يمكنكم الآن البدء في طرح الأسماء على بعضكم البعض أو الانتقال مباشرة للتصويت.", size=18, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("🎤 بدء جولة أسئلة (اختياري)", on_click=start_question_round_offline, width=300, height=55),
                ft.ElevatedButton("🗳️ الانتقال للتصويت", on_click=start_voting_offline, width=300, height=55)
            ])

        elif s["page"] == "question_time_offline":
            if s["current_question_pair_index"] < len(s["question_pairs"]):
                asker, askee = s["question_pairs"][s["current_question_pair_index"]]
                offline_content_area.controls.extend([
                    ft.Text(f"🎤 {asker} يسأل {askee}", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text("اطرح سؤالك وحاول كشف من هو 'برة السالفة'!", size=18, text_align=ft.TextAlign.CENTER),
                    ft.ElevatedButton("السؤال التالي", on_click=next_question_pair_offline, width=250, height=55)
                ])
            else:
                set_offline_page("discussion_or_vote")

        elif s["page"] == "voting_offline":
            voter_name = s["player_names"][s["current_voting_player_index"]]
            offline_content_area.controls.append(
                ft.Text(f"دور {voter_name} للتصويت:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
            )
            offline_content_area.controls.append(
                ft.Text("اختر اللاعب الذي تعتقد أنه 'برة السالفة':", size=18, text_align=ft.TextAlign.CENTER)
            )

            def handle_vote_button_click_offline(e, voted_for_player): # Renamed from cast_vote_offline_click for clarity
                s["votes"][voter_name] = voted_for_player
                s["current_voting_player_index"] += 1
                if s["current_voting_player_index"] >= len(s["player_names"]):
                    process_voting_results_offline()
                    set_offline_page("vote_results_offline")
                else:
                    update_offline_ui()

            vote_buttons_row = ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                run_spacing=10
            )
            players_to_vote_for = [p_name_iter for p_name_iter in s["player_names"] if p_name_iter != voter_name]

            if not players_to_vote_for:
                 offline_content_area.controls.append(ft.Text("لا يوجد لاعبون آخرون للتصويت ضدهم.", text_align=ft.TextAlign.CENTER))
            else:
                for p_name_option in players_to_vote_for:
                    player_button = ft.ElevatedButton(
                        text=p_name_option,
                        on_click=lambda e, choice=p_name_option: handle_vote_button_click_offline(e, choice),
                        col={"xs": 6, "sm": 4, "md": 3},
                        height=55,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                    )
                    vote_buttons_row.controls.append(ft.Container(content=player_button, alignment=ft.alignment.center))
            offline_content_area.controls.append(vote_buttons_row)

        elif s["page"] == "vote_results_offline":
            offline_content_area.controls.append(ft.Text("📊 نتائج التصويت:", size=24, weight="bold", text_align=ft.TextAlign.CENTER))
            vote_summary_rows = []
            for voter, voted_for in s["votes"].items():
                vote_summary_rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(voter)), ft.DataCell(ft.Text(voted_for))]))

            if vote_summary_rows:
                 offline_content_area.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[ft.DataColumn(ft.Text("اللاعب المصوِّت")), ft.DataColumn(ft.Text("صوَّت ضد"))],
                            rows=vote_summary_rows,
                            column_spacing=20
                        ),
                        width=page.width * 0.9 if page.width else 350,
                        alignment=ft.alignment.center
                    )
                 )
            else: # Ensure some message if no votes (though should not happen)
                offline_content_area.controls.append(ft.Text("لم يتم تسجيل أي أصوات.", text_align=ft.TextAlign.CENTER))


            offline_content_area.controls.extend([
                ft.Text(f"الشخص الذي كان 'برة السالفة' هو: {s['bara_player']}", size=20, color=ft.Colors.RED_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD),
                ft.Text("النقاط من التصويت الصحيح:", size=18, text_align=ft.TextAlign.CENTER)
            ])
            initial_round_scores = s.get("initial_round_scores_from_voting", {})
            has_scores_from_voting = False
            for p_name, score_increase in initial_round_scores.items():
                if score_increase > 0 :
                    offline_content_area.controls.append(ft.Text(f"{p_name}: +{score_increase} نقاط", color=ft.Colors.GREEN_ACCENT_700, text_align=ft.TextAlign.CENTER))
                    has_scores_from_voting = True
            if not has_scores_from_voting:
                offline_content_area.controls.append(ft.Text("لا نقاط من التصويت هذه الجولة.", text_align=ft.TextAlign.CENTER, color=ft.Colors.ON_SURFACE_VARIANT))


            offline_content_area.controls.append(ft.ElevatedButton(f"دع {s['bara_player']} يخمن الكلمة", on_click=lambda e: set_offline_page("bara_guess_word_offline"), width=300, height=55))

        elif s["page"] == "bara_guess_word_offline":
            offline_content_area.controls.append(ft.Text(f"{s['bara_player']}، حاول تخمين الكلمة السرية!", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            offline_content_area.controls.append(ft.Text(f"القائمة كانت: {s['selected_category']}", size=18, text_align=ft.TextAlign.CENTER))

            options_responsive_row = ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10, run_spacing=10
            )
            guess_options_list = s.get("guess_word_options", [])
            if not guess_options_list: # Handle case where options might be empty
                options_responsive_row.controls.append(ft.Text("لا توجد خيارات تخمين متاحة.", text_align=ft.TextAlign.CENTER))
            else:
                for word_option in guess_options_list:
                    btn = ft.ElevatedButton(
                        word_option,
                        on_click=lambda e, wo=word_option: handle_bara_guess_offline(wo),
                        col={"xs": 6, "sm": 4}
                    )
                    options_responsive_row.controls.append(ft.Container(content=btn, alignment=ft.alignment.center))

            offline_content_area.controls.append(options_responsive_row)

        elif s["page"] == "round_over_offline":
            offline_content_area.controls.extend([
                ft.Text("🎉 انتهت الجولة!", size=28, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Text(s["bara_guess_result_text"], size=20, weight="bold", text_align=ft.TextAlign.CENTER,
                          color=(ft.Colors.GREEN_700 if "صحيح" in s["bara_guess_result_text"] else ft.Colors.RED_700)),
                ft.Text("النقاط الإجمالية:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
            ])
            score_rows = []
            sorted_global_scores = sorted(s["global_scores"].items(), key=lambda item: item[1], reverse=True)
            for p_name, total_score in sorted_global_scores:
                 score_rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(p_name)), ft.DataCell(ft.Text(str(total_score)))]))

            if score_rows:
                offline_content_area.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[ft.DataColumn(ft.Text("اللاعب")), ft.DataColumn(ft.Text("النقاط"))],
                            rows=score_rows,
                            # Added for better display on small screens
                            horizontal_lines=ft.border.BorderSide(1, "black12"),
                            # vertical_lines=ft.border.BorderSide(1, "black12"), # Optional
                            data_row_max_height=40,
                        ),
                        width=page.width * 0.9 if page.width else 350,
                        alignment=ft.alignment.center
                    )
                )
            offline_content_area.controls.append(
                ft.ResponsiveRow(
                    [
                        ft.ElevatedButton("🔄 جولة جديدة بنفس اللاعبين", on_click=restart_round_offline, col={"xs":12, "sm":6}, height=55),
                        ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home_fn, col={"xs":12, "sm":6}, height=55)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    run_spacing=10
                )
            )

        else:
            offline_content_area.controls.append(ft.Text(f"صفحة غير معروفة: {s['page']}"))
            offline_content_area.controls.append(ft.ElevatedButton("ابدأ من جديد", on_click=lambda e: set_offline_page("setup_players")))

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
            page.snack_bar = ft.SnackBar(ft.Text(f"لا توجد كلمات جديدة في قائمة '{s.get('selected_category')}'. تم إعادة تعيين الكلمات المستخدمة."), open=True) # Notify user
            if cat_words: # If category had words, reset and try again
                s["used_words_in_category"] = set()
                available_words = list(cat_words)
                if available_words:
                    s["game_word"] = random.choice(available_words)
                    s["used_words_in_category"].add(s["game_word"])
                else: # Should not happen if cat_words was not empty initially
                    s["game_word"] = "خطأ: لا توجد كلمات على الإطلاق!"
            else: # Category itself is empty
                 s["game_word"] = "خطأ: القائمة المختارة فارغة!"

        elif s["game_word"] != "لا توجد كلمات!": # Only assign if a valid word was found initially
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
        game_word = s.get("game_word", "لا توجد كلمة!") # Get game_word or default

        # Ensure game_word is not "لا توجد كلمات!" or similar error messages before proceeding
        if game_word.startswith("لا توجد كلمات") or game_word.startswith("خطأ:"):
            s["guess_word_options"] = [game_word] # Show the error as the only "option"
            return


        other_words = [word for word in cat_words if word != game_word]

        num_options_needed = min(7, len(other_words))
        options = []
        if other_words:
            options = random.sample(other_words, num_options_needed)

        s["guess_word_options"] = options
        if game_word and game_word not in s["guess_word_options"]:
            if len(s["guess_word_options"]) >= 8: # Max 8 options
                 s["guess_word_options"].pop(random.randrange(len(s["guess_word_options"])))
            s["guess_word_options"].append(game_word)
        elif not game_word and not s["guess_word_options"]: # Should be caught by earlier check
            s["guess_word_options"] = ["لا توجد خيارات"]


        random.shuffle(s["guess_word_options"])
        if not s["guess_word_options"] and game_word:
            s["guess_word_options"] = [game_word]
        elif not s["guess_word_options"]:
             s["guess_word_options"] = ["لا توجد كلمة لتخمينها"]


    def handle_bara_guess_offline(guessed_word):
        s = offline_state
        game_word = s.get("game_word", "غير محددة") # Default if game_word is missing

        # Handle cases where game_word might be an error message itself
        if game_word.startswith("لا توجد كلمات") or game_word.startswith("خطأ:"):
            s["bara_guess_result_text"] = f"❌ لا يمكن التخمين، {game_word}"
        elif guessed_word == game_word:
            s["round_scores"][s["bara_player"]] = s["round_scores"].get(s["bara_player"], 0) + 10
            s["bara_guess_result_text"] = f"✅ صحيح! {s.get('bara_player','')} خمن الكلمة ({game_word}) وحصل على 10 نقاط إضافية."
        else:
            s["bara_guess_result_text"] = f"❌ خطأ! الكلمة الصحيحة كانت {game_word}."

        for p_name, r_score in s.get("round_scores",{}).items():
            s["global_scores"][p_name] = s["global_scores"].get(p_name, 0) + r_score

        set_offline_page("round_over_offline")

    def restart_round_offline(e):
        s = offline_state
        # Reset only round-specific items, keep global_scores
        # Keep player_names
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
        # Reset round_scores for all players who are still in s["player_names"]
        s["round_scores"] = {name: 0 for name in s.get("player_names", [])}
        s["initial_round_scores_from_voting"] = {}
        s["guess_word_options"] = []
        s["bara_guess_result_text"] = ""
        s["used_words_in_category"] = set() # Reset for the new category choice
        update_offline_ui()

    reset_offline_state()
    return [
        ft.Container(
            content=offline_content_area,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=15, vertical=10)
        )
    ]

# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def bara_alsalfa_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    page_title = ft.Text(f"لعبة برة السالفة - غرفة: {room_code}", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    status_text = ft.Text("...", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

    player_list_display = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE, spacing=5,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    action_area = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
        scroll=ft.ScrollMode.ADAPTIVE
        # Removed padding, will be handled by parent container
    )
    role_display_area = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )

    online_container_content = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )

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
        status_text.text_align = ft.TextAlign.CENTER

        player_list_display.controls.clear()
        player_list_display.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
        for p_name_iter, p_data_iter in players_in_room.items():
            player_list_display.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}", text_align=ft.TextAlign.CENTER)
            )

        action_area.controls.clear()
        role_display_area.visible = False

        if current_phase == "LOBBY":
            if is_host:
                cat_options = [ft.dropdown.Option(key_val) for key_val in categories.keys()]
                category_dropdown = ft.Dropdown(
                    label="اختر القائمة",
                    options=cat_options,
                    value=gs.get("selected_category")
                )
                category_dropdown_container = ft.Container(
                    content=category_dropdown,
                    width=page.width * 0.8 if page.width else 280,
                    alignment=ft.alignment.center
                )

                start_game_button_lobby = ft.ElevatedButton(
                    "🚀 ابدأ اللعبة الآن",
                    on_click=lambda e: send_action_fn("START_GAME_HOST"),
                    width=280, height=50,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                )

                action_area.controls.extend([
                    ft.Text("أنت الهوست. الرجاء اختيار قائمة الكلمات:", text_align=ft.TextAlign.CENTER),
                    category_dropdown_container,
                    ft.ElevatedButton("تأكيد القائمة",
                                     on_click=lambda e: send_action_fn("SELECT_CATEGORY_HOST", {"category": category_dropdown.value}) if category_dropdown.value else None,
                                     width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                    start_game_button_lobby
                ])
                can_start_game = gs.get("selected_category") and len(players_in_room) >= gs.get("min_players_for_game", 3)
                start_game_button_lobby.disabled = not can_start_game

                if not gs.get("selected_category"):
                    action_area.controls.append(ft.Text("(اختر قائمة أولاً لتفعيل زر بدء اللعبة)", size=12, color="onSurfaceVariant", text_align=ft.TextAlign.CENTER))
                elif len(players_in_room) < gs.get("min_players_for_game", 3):
                    remaining_to_join = gs.get("min_players_for_game", 3) - len(players_in_room)
                    action_area.controls.append(ft.Text(f" (تحتاج {remaining_to_join} لاعبين إضافيين لبدء اللعبة)", size=12, color="onSurfaceVariant", text_align=ft.TextAlign.CENTER))
                else:
                     action_area.controls.append(ft.Text("(جاهز لبدء اللعبة!)", size=14, color=ft.Colors.GREEN_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست لاختيار القائمة وبدء اللعبة...", text_align=ft.TextAlign.CENTER, size=16))

        elif current_phase == "CATEGORY_SELECTED":
            action_area.controls.append(ft.Text(f"القائمة المختارة: {gs.get('selected_category', '...')}", weight="bold", text_align=ft.TextAlign.CENTER, size=20))
            if is_host:
                can_start_game_cat_selected = len(players_in_room) >= gs.get("min_players_for_game", 3)
                start_game_button_cat_selected = ft.ElevatedButton(
                    "🚀 ابدأ اللعبة الآن",
                    on_click=lambda e: send_action_fn("START_GAME_HOST"),
                    width=280, height=50,
                    disabled = not can_start_game_cat_selected,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                )
                action_area.controls.append(start_game_button_cat_selected)

                if not can_start_game_cat_selected:
                    remaining_to_join = gs.get("min_players_for_game", 3) - len(players_in_room)
                    action_area.controls.append(ft.Text(f" (تحتاج {remaining_to_join} لاعبين إضافيين لبدء اللعبة)", text_align=ft.TextAlign.CENTER, size=12, color=ft.Colors.ON_SURFACE_VARIANT))
                else:
                    action_area.controls.append(ft.Text("(جاهز لبدء اللعبة!)", size=14, color=ft.Colors.GREEN_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست لبدء اللعبة...", text_align=ft.TextAlign.CENTER, size=16))

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
                    ft.Text(f"دورك هو:", size=22, text_align=ft.TextAlign.CENTER),
                    ft.Text(my_role, size=28, weight="bold",
                              color=(ft.Colors.RED_ACCENT_700 if my_role == "برة السالفة" else ft.Colors.GREEN_ACCENT_700),
                              text_align=ft.TextAlign.CENTER),
                    ft.Text(f"القائمة: {gs.get('selected_category', '...')}", size=18, text_align=ft.TextAlign.CENTER)
                ])
                if my_role == "داخل السالفة" and gs.get("game_word"):
                    role_display_area.controls.append(ft.Text(f"الكلمة السرية: {gs.get('game_word', '...')}", size=22, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
                role_display_area.controls.append(ft.ElevatedButton("✅ تم، فهمت دوري", on_click=lambda e: send_action_fn("PLAYER_ACK_ROLE"), width=250, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
                action_area.controls.append(ft.Text("الرجاء تفقد دورك في الأعلى ثم اضغط 'تم'.", text_align=ft.TextAlign.CENTER, size=16))
            elif player_to_see_role:
                action_area.controls.append(ft.Text(f"في انتظار {player_to_see_role} لتفقد دوره...", text_align=ft.TextAlign.CENTER, size=16))
            else:
                action_area.controls.append(ft.Text("في انتظار اللاعبين لتفقد أدوارهم...", text_align=ft.TextAlign.CENTER, size=16))

        elif current_phase == "DISCUSSION":
            action_area.controls.append(ft.Text("مرحلة النقاش! حاولوا معرفة من هو 'برة السالفة'.", size=18, text_align=ft.TextAlign.CENTER))
            if is_host:
                action_area.controls.extend([
                    ft.ElevatedButton("🎤 بدء جولة أسئلة (اختياري)", on_click=lambda e: send_action_fn("START_QUESTION_ROUND_HOST"), width=300, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                    ft.ElevatedButton("🗳️ الانتقال للتصويت الآن", on_click=lambda e: send_action_fn("INITIATE_VOTE_HOST"), width=300, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                ])
            else:
                action_area.controls.append(ft.Text("الهوست يمكنه بدء جولة أسئلة أو الانتقال للتصويت.", text_align=ft.TextAlign.CENTER, size=16))

        elif current_phase == "QUESTION_TIME":
            question_pairs_list = gs.get("question_pairs", [])
            current_q_idx = gs.get("current_question_pair_index", 0)
            pair = question_pairs_list[current_q_idx] if question_pairs_list and current_q_idx < len(question_pairs_list) else (None, None)

            if pair[0] and pair[1]:
                 action_area.controls.append(ft.Text(f"🎤 {pair[0]} يسأل {pair[1]}", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            if is_host:
                action_area.controls.append(ft.ElevatedButton("السؤال التالي ⏭️", on_click=lambda e: send_action_fn("NEXT_QUESTION_PAIR_HOST"), width=250, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
                action_area.controls.append(ft.ElevatedButton("إنهاء الأسئلة والانتقال للتصويت", on_click=lambda e: send_action_fn("INITIATE_VOTE_HOST"), width=300, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست لإدارة جولة الأسئلة.", text_align=ft.TextAlign.CENTER, size=16))

        elif current_phase == "VOTING":
            already_voted = current_player_name in gs.get("players_who_voted", [])
            if already_voted:
                action_area.controls.append(ft.Text("شكراً لك، تم تسجيل صوتك. في انتظار بقية اللاعبين...", size=18, text_align=ft.TextAlign.CENTER))
            else:
                action_area.controls.append(
                    ft.Text("حان وقت التصويت!", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
                )
                action_area.controls.append(
                    ft.Text("اختر اللاعب الذي تعتقد أنه 'برة السالفة':", size=18, text_align=ft.TextAlign.CENTER)
                )

                online_vote_buttons_row = ft.ResponsiveRow(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                    run_spacing=10
                )
                players_to_vote_for_online = [p_name_iter for p_name_iter in players_in_room if p_name_iter != current_player_name]

                if not players_to_vote_for_online:
                    action_area.controls.append(ft.Text("لا يوجد لاعبون آخرون للتصويت ضدهم.", text_align=ft.TextAlign.CENTER))
                else:
                    for p_name_option in players_to_vote_for_online:
                        player_button_online = ft.ElevatedButton(
                            text=p_name_option,
                            on_click=lambda e, choice=p_name_option: send_action_fn("CAST_VOTE", {"voted_for": choice}),
                            col={"xs": 6, "sm": 4, "md": 3},
                            height=55,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                        )
                        online_vote_buttons_row.controls.append(ft.Container(content=player_button_online, alignment=ft.alignment.center))
                action_area.controls.append(online_vote_buttons_row)

        elif current_phase == "VOTE_RESULTS":
            action_area.controls.append(ft.Text("📊 نتائج التصويت:", size=24, weight="bold", text_align=ft.TextAlign.CENTER))

            vote_details = gs.get("votes", {})
            vote_rows = []
            for voter, voted_for in vote_details.items():
                if voted_for: # Only show actual votes cast
                    vote_rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(voter)), ft.DataCell(ft.Text(voted_for))]))

            if vote_rows:
                action_area.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[ft.DataColumn(ft.Text("اللاعب المصوِّت")), ft.DataColumn(ft.Text("صوَّت ضد"))],
                            rows=vote_rows,
                            column_spacing=20,
                            horizontal_lines=ft.border.BorderSide(1, "black12"), # Added for better display
                            data_row_max_height=40,
                        ),
                        width=page.width * 0.9 if page.width else 350,
                        alignment=ft.alignment.center
                    )
                )
            else:
                action_area.controls.append(ft.Text("لم يتم تسجيل أي أصوات.", text_align=ft.TextAlign.CENTER))

            action_area.controls.append(ft.Text(f"'برة السالفة' كان: {gs.get('bara_player', '...')}", size=20, color=ft.Colors.RED_ACCENT_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))

            round_scores_for_display = gs.get("round_scores", {})
            points_text_elements = []
            has_round_scores = False
            for p_name_iter, score_val in round_scores_for_display.items():
                if score_val != 0 :
                    points_text_elements.append(ft.Text(f"{p_name_iter}: {score_val} نقاط", color=ft.Colors.GREEN_ACCENT_700, text_align=ft.TextAlign.CENTER))
                    has_round_scores = True

            if points_text_elements:
                action_area.controls.append(ft.Text("النقاط المكتسبة (قبل تخمين 'برة السالفة'):", size=18, text_align=ft.TextAlign.CENTER))
                action_area.controls.extend(points_text_elements)
            elif not has_round_scores: # If no one got points from voting
                action_area.controls.append(ft.Text("لا نقاط من التصويت هذه الجولة.", text_align=ft.TextAlign.CENTER, color=ft.Colors.ON_SURFACE_VARIANT))


            if current_player_name == gs.get("bara_player"):
                action_area.controls.append(ft.Text("أنت 'برة السالفة'! حاول تخمين الكلمة:", size=20, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))

                options_responsive_row_online = ft.ResponsiveRow(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10, run_spacing=10
                )
                guess_options = gs.get("bara_guess_options", [])
                if not guess_options:
                    options_responsive_row_online.controls.append(ft.Text("لا توجد خيارات تخمين.", text_align=ft.TextAlign.CENTER))
                else:
                    for word_opt in guess_options:
                        btn = ft.ElevatedButton(word_opt, on_click=lambda e, wo=word_opt: send_action_fn("BARA_GUESS_WORD", {"word": wo}), col={"xs":6, "sm":4})
                        options_responsive_row_online.controls.append(ft.Container(content=btn, alignment=ft.alignment.center))
                action_area.controls.append(options_responsive_row_online)
            else:
                action_area.controls.append(ft.Text(f"في انتظار {gs.get('bara_player', '...')} لتخمين الكلمة...", size=18, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ROUND_OVER":
            action_area.controls.extend([
                ft.Text("🎉 انتهت الجولة!", size=28, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Text(gs.get("bara_guess_result", "..."), size=20, weight="bold", text_align=ft.TextAlign.CENTER,
                          color=(ft.Colors.GREEN_700 if "صحيح" in gs.get("bara_guess_result", "") else ft.Colors.RED_700)),
                ft.Text("النقاط الإجمالية:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
            ])

            global_scores_display = gs.get("global_scores", {})
            score_table_rows = []
            sorted_scores = sorted(global_scores_display.items(), key=lambda item: item[1], reverse=True)

            for p_name_iter, total_score in sorted_scores:
                score_table_rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(p_name_iter)), ft.DataCell(ft.Text(str(total_score)))]))

            if score_table_rows:
                 action_area.controls.append(
                    ft.Container(
                        content=ft.DataTable(
                            columns=[ft.DataColumn(ft.Text("اللاعب")), ft.DataColumn(ft.Text("النقاط"))],
                            rows=score_table_rows,
                            horizontal_lines=ft.border.BorderSide(1, "black12"), # Added for better display
                            data_row_max_height=40,
                        ),
                        width=page.width * 0.9 if page.width else 350,
                        alignment=ft.alignment.center
                    )
                 )

            if is_host:
                action_area.controls.append(ft.ElevatedButton("🔄 ابدأ جولة جديدة", on_click=lambda e: send_action_fn("NEXT_ROUND_HOST"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست لبدء جولة جديدة...", text_align=ft.TextAlign.CENTER, size=16))

        if page.client_storage:
            log_debug(f"EXECUTING page.update() for phase {current_phase}")
            page.update()
        else:
            log_debug(f"SKIPPING page.update() because page.client_storage is None for phase {current_phase}")

    def on_server_message(*args_received):
        if not page.client_storage:
            log_debug("on_server_message: Page disposed.")
            return
        # log_debug(f"PUBSUB_RAW_ARGS_RECEIVED: {args_received}") # Can be very verbose
        if not args_received or len(args_received) < 2:
            log_debug("Not enough arguments received in on_server_message.")
            return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict):
            log_debug(f"Error: Extracted msg_data is not a dictionary: type={type(msg_data)}, value={msg_data}")
            return

        msg_type = msg_data.get("type")
        # log_debug(f"Processing PubSub: Type: {msg_type} from msg_data: {msg_data}") # Can be verbose

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
                 page.snack_bar = ft.SnackBar(ft.Text(error_msg, text_align=ft.TextAlign.CENTER), open=True)
                 page.update()
        # else:
            # log_debug(f"Unknown message type received: {msg_type}") # Can be verbose

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message)
    log_debug(f"Subscribed to topic: room_{room_code}")

    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        log_debug("Found initial room data on client load. Updating UI.")
        update_ui_from_server_state(initial_room_data)
    else:
        log_debug(f"Room {room_code} not found in game_rooms_ref on client load. This is problematic and client UI might be stale.")
        status_text.value = "خطأ في الاتصال بالغرفة. قد تحتاج للعودة والمحاولة مجدداً."

    online_container_content.controls.extend([
        ft.Row(
            [
                page_title,
                ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=28)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=5, thickness=1),
        status_text,
        ft.Divider(height=5, thickness=1),
        role_display_area,
        ft.ResponsiveRow(
            [
                ft.Container(
                    content=player_list_display,
                    padding=10,
                    border=ft.border.all(1, ft.colors.with_opacity(0.5, ft.colors.ON_SURFACE_VARIANT)),
                    border_radius=8,
                    col={"xs": 12, "md": 4, "lg":3}, # Player list takes less space on wider screens
                    margin=ft.margin.only(bottom=10 if page.width and page.width < 768 else 0) # Bottom margin only on small screens
                ),
                ft.Container(
                    content=action_area,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5), # Consistent padding
                    col={"xs": 12, "md": 8, "lg":9}, # Action area takes more space
                    alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            alignment=ft.MainAxisAlignment.START # Align row content to the start
        )
    ])

    return [
        ft.Container(
            content=online_container_content,
            expand=True,
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=10, vertical=10) # Reduced horizontal padding
        )
    ]

# --- GAME ENTRY POINT (Called by app.py) ---
def bara_alsalfa_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return bara_alsalfa_offline_logic(page, go_home_fn)
    else:
        if not room_code or not player_name or game_rooms_ref is None:
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة للعب أونلاين."), alignment=ft.alignment.center, expand=True)]

        def send_bara_alsalfa_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "bara_alsalfa", action_type, payload or {})

        return bara_alsalfa_online_logic(page, go_home_fn, send_bara_alsalfa_action_to_server_wrapper, room_code, player_name, game_rooms_ref)