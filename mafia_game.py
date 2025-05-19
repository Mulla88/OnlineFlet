# mafia_game.py
import flet as ft
import random

_mafia_offline_state = {}

def mafia_offline_logic(page: ft.Page, go_home_fn):

    offline_main_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20 # Increased default spacing
    )
    name_inputs_list_mafia = [] # To store TextField instances

    def update_offline_ui():
        offline_main_column.controls.clear()
        s = _mafia_offline_state

        if s["page_step"] == "setup_player_count":
            offline_main_column.controls.append(ft.Text("🎭 لعبة المافيا", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Game Title
            offline_main_column.controls.append(ft.Text("إعداد عدد اللاعبين (5-15):", size=24, text_align=ft.TextAlign.CENTER))
            num_display_offline = ft.Text(str(s['num_players']), size=30, weight=ft.FontWeight.BOLD) # Larger

            def update_num_offline_mafia(change):
                s['num_players'] = max(5, min(15, s['num_players'] + change))
                num_display_offline.value = str(s['num_players'])
                if page.client_storage: num_display_offline.update() # Update only the text

            offline_main_column.controls.extend([
                ft.ResponsiveRow( # Use ResponsiveRow for +/-
                    [
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e: update_num_offline_mafia(-1), col={"xs": 4}, icon_size=30),
                        ft.Container(content=num_display_offline, col={"xs": 4}, alignment=ft.alignment.center),
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e: update_num_offline_mafia(1), col={"xs": 4}, icon_size=30),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.ElevatedButton("التالي: إدخال الأسماء", on_click=lambda e: set_page_step("input_player_names"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                ft.ElevatedButton("🏠 العودة للقائمة", on_click=go_home_fn, width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])
        elif s["page_step"] == "input_player_names":
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء اللاعبين:", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            name_inputs_list_mafia.clear() # Clear previous instances
            for i in range(s["num_players"]):
                tf = ft.TextField(label=f"اللاعب {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8)
                name_inputs_list_mafia.append(tf) # Store actual TextField
                offline_main_column.controls.append(
                    ft.Container(content=tf, width=page.width * 0.85 if page.width else 300, alignment=ft.alignment.center)
                )

            def save_names_mafia(e):
                names = [tf.value.strip() for tf in name_inputs_list_mafia if tf.value.strip()]
                if len(names) != s["num_players"] or len(set(names)) != len(names) or any(not n for n in names):
                    page.snack_bar = ft.SnackBar(ft.Text("الأسماء يجب أن تكون فريدة وغير فارغة ومكتملة!"), open=True)
                    if page.client_storage: page.update()
                    return
                s["players"] = names
                s["eliminated_players"] = []
                s["log"] = ["بدأت اللعبة!"] # Initial log
                assign_roles() # This will set next page step
            offline_main_column.controls.append(ft.ElevatedButton("تأكيد وتوزيع الأدوار", on_click=save_names_mafia, width=300, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            offline_main_column.controls.append(ft.ElevatedButton("🔙 رجوع للعدد", on_click=lambda e: set_page_step("setup_player_count"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))


        elif s["page_step"] == "show_individual_role_handoff":
            player_name = s["players"][s["current_player_role_reveal_idx"]]
            offline_main_column.controls.extend([
                ft.Text(f"📱 أعطِ الجهاز للاعب:", size=24, text_align=ft.TextAlign.CENTER),
                ft.Text(player_name, size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("👀 عرض دوري", on_click=lambda e: set_page_step("display_individual_role_screen"), width=280, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif s["page_step"] == "display_individual_role_screen":
            player_name = s["players"][s["current_player_role_reveal_idx"]]
            role = s["roles"].get(player_name, "غير معروف")
            desc_map = {'مافيا': "مهمتك قتل المدنيين ليلاً والتعاون مع زملائك المافيا. لا تكشف عن هويتك!",
                          'طبيب': "مهمتك إنقاذ لاعب واحد كل ليلة من القتل. لا يمكنك إنقاذ نفس اللاعب مرتين متتاليتين.",
                          'محقق': "مهمتك التحقق من هوية لاعب واحد كل ليلة لمعرفة ما إذا كان من المافيا أم لا.",
                          'مواطن': "مهمتك اكتشاف أفراد المافيا خلال النهار والتصويت لطردهم. حاول البقاء على قيد الحياة!"}
            role_color = ft.Colors.BLACK
            if role == "مافيا": role_color = ft.Colors.RED_ACCENT_700
            elif role == "طبيب": role_color = ft.Colors.GREEN_ACCENT_700
            elif role == "محقق": role_color = ft.Colors.BLUE_ACCENT_700
            elif role == "مواطن": role_color = ft.Colors.TEAL_700


            offline_main_column.controls.extend([
                ft.Text(f"{player_name}، دورك هو:", size=24, text_align=ft.TextAlign.CENTER),
                ft.Text(role, size=32, weight=ft.FontWeight.BOLD, color=role_color, text_align=ft.TextAlign.CENTER),
                ft.Container( # Container for description for padding
                    content=ft.Text(desc_map.get(role, "وصف غير متوفر."), size=18, text_align=ft.TextAlign.CENTER, selectable=True),
                    padding=ft.padding.symmetric(horizontal=10)
                )
            ])
            if role == "مافيا":
                other_mafia = [p for p, r_val in s["roles"].items() if r_val == "مافيا" and p != player_name]
                if other_mafia:
                    offline_main_column.controls.append(ft.Text(f"زملاؤك في المافيا: {', '.join(other_mafia)}", color=ft.Colors.RED_700, size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Bolder

            def next_player_role_reveal(e):
                s["current_player_role_reveal_idx"] += 1
                if s["current_player_role_reveal_idx"] < len(s["players"]):
                    set_page_step("show_individual_role_handoff")
                else:
                    s["current_player_role_reveal_idx"] = 0
                    s["night_action_step"] = "mafia_action"
                    s["night_counter"] = 1
                    s["last_doctor_save"] = None
                    s["night_results"] = {}
                    set_page_step("night_phase_intro")
            offline_main_column.controls.append(ft.ElevatedButton("فهمت، التالي", on_click=next_player_role_reveal, width=280, height=60, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        elif s["page_step"] == "night_phase_intro":
            step_texts = {"mafia_action": "😴 الجميع ينام... المافيا تستيقظ لاختيار ضحية.",
                          "doctor_action": "😴 المافيا تنام... الطبيب يستيقظ لاختيار من سينقذه.",
                          "detective_action": "😴 الطبيب ينام... المحقق يستيقظ لاختيار من سيتحقق منه."}
            s["detective_action_result_text"] = ""
            offline_main_column.controls.extend([
                ft.Text(f"ليل {s['night_counter']}", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text(step_texts.get(s["night_action_step"],"..."), size=22, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500),
                ft.ElevatedButton("التالي", on_click=lambda e: set_page_step(s["night_action_step"]), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ])

        elif s["page_step"] in ["mafia_action", "doctor_action", "detective_action"]:
            action_prompts = {"mafia_action": "☠️ المافيا، اتفقوا واختاروا ضحية:",
                              "doctor_action": "⚕️ أيها الطبيب، اختر من تنقذه هذا الليل:",
                              "detective_action": "🕵️ أيها المحقق، اختر من تتحقق من هويته:"}
            offline_main_column.controls.append(ft.Text(action_prompts[s["page_step"]], size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))

            action_buttons_row = ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10, run_spacing=10
            )
            error_text_mafia = ft.Text("", color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD) # For doctor error

            alive_players = [p for p in s["players"] if p not in s["eliminated_players"]]
            target_options = []

            if s["page_step"] == "mafia_action":
                target_options = [p for p in alive_players if s["roles"].get(p) != 'مافيا']
            elif s["page_step"] == "doctor_action":
                target_options = list(alive_players)
            elif s["page_step"] == "detective_action":
                detective_name = next((p_name for p_name, r_val in s["roles"].items() if r_val == 'محقق' and p_name in alive_players), None)
                target_options = [p for p in alive_players if p != detective_name]


            def submit_night_action_from_button(e, choice): # Modified for button click
                if s["page_step"] == "mafia_action":
                    s["night_results"]["mafia_target"] = choice
                    s["night_action_step"] = "doctor_action"
                    set_page_step("night_phase_intro")
                elif s["page_step"] == "doctor_action":
                    if choice == s.get("last_doctor_save") and choice is not None:
                        error_text_mafia.value = "لا يمكنك إنقاذ نفس الشخص مرتين متتاليتين!"
                        if page.client_storage: error_text_mafia.update()
                        return
                    s["night_results"]["doctor_save"] = choice
                    s["last_doctor_save"] = choice
                    s["night_action_step"] = "detective_action"
                    set_page_step("night_phase_intro")
                elif s["page_step"] == "detective_action":
                    s["night_results"]["detective_target"] = choice
                    feedback_text = ""
                    if choice:
                        target_role = s['roles'].get(choice, 'مدني') # Default to مدني if role not found
                        is_mafia = "نعم، هذا اللاعب من المافيا 💀" if target_role == 'مافيا' else "لا، هذا اللاعب ليس من المافيا ✅"
                        feedback_text = f"نتيجة التحقيق في اللاعب {choice}: {is_mafia}"
                        s["log"].append(f"ليلة {s['night_counter']}: المحقق فحص {choice} (كان {target_role}).")
                    else:
                        feedback_text = "المحقق لم يختر أحدًا هذا الليل."
                        s["log"].append(f"ليلة {s['night_counter']}: المحقق لم يفحص أحدًا.")

                    s["detective_action_result_text"] = feedback_text
                    set_page_step("detective_feedback") # New step to show feedback

            if s["page_step"] == "detective_action" and s.get("detective_action_result_text"): # This logic is now in detective_feedback
                 pass # Will be handled by the new step
            else:
                if target_options:
                    for p_opt in target_options:
                        btn = ft.ElevatedButton(
                            text=p_opt,
                            on_click=lambda e, ch=p_opt: submit_night_action_from_button(e, ch),
                            col={"xs": 6, "sm": 4}, # 2-3 buttons per row
                            height=55,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                        )
                        action_buttons_row.controls.append(ft.Container(content=btn, alignment=ft.alignment.center))
                    offline_main_column.controls.append(action_buttons_row)
                else:
                    offline_main_column.controls.append(ft.Text("لا يوجد أهداف متاحة لهذا الدور.", italic=True, text_align=ft.TextAlign.CENTER, size=16))
                    # Provide a way to continue if no targets
                    offline_main_column.controls.append(ft.ElevatedButton("تخطي / لا يوجد هدف", on_click=lambda e: submit_night_action_from_button(e, None), width=250, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
                offline_main_column.controls.append(error_text_mafia)

        elif s["page_step"] == "detective_feedback": # New step
            offline_main_column.controls.append(ft.Text("🕵️ نتيجة تحقيق المحقق:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            if s.get("detective_action_result_text"):
                offline_main_column.controls.append(
                    ft.Text(s["detective_action_result_text"], size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800, text_align=ft.TextAlign.CENTER)
                )
            else: # Should not happen if logic is correct
                offline_main_column.controls.append(ft.Text("لم يتم إجراء تحقيق.", text_align=ft.TextAlign.CENTER))
            offline_main_column.controls.append(
                ft.ElevatedButton("متابعة إلى ملخص الليل",
                                 on_click=lambda e: set_page_step("night_summary"),
                                 width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            )

        elif s["page_step"] == "night_summary":
            s["detective_action_result_text"] = "" # Clear for next night

            offline_main_column.controls.append(ft.Text(f"📜 ملخص ليلة {s['night_counter']}:", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            mafia_target = s["night_results"].get("mafia_target")
            doctor_save = s["night_results"].get("doctor_save")
            eliminated_this_night = False

            if mafia_target and mafia_target == doctor_save:
                offline_main_column.controls.append(ft.Text(f"✅ تم إنقاذ {mafia_target} بواسطة الطبيب!", color=ft.Colors.GREEN_700, size=20, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
                s["log"].append(f"ليلة {s['night_counter']}: الطبيب أنقذ {doctor_save}.")
            elif mafia_target:
                offline_main_column.controls.append(ft.Text(f"☠️ تم قتل {mafia_target} بواسطة المافيا!", color=ft.Colors.RED_700, size=20, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD))
                if mafia_target not in s["eliminated_players"]:
                    s["eliminated_players"].append(mafia_target)
                    eliminated_this_night = True
                s["log"].append(f"ليلة {s['night_counter']}: المافيا قتلت {mafia_target}.")
            else:
                offline_main_column.controls.append(ft.Text("لم تختر المافيا أحداً أو لم يكن هناك هدف متاح.", italic=True, size=16, text_align=ft.TextAlign.CENTER))
                s["log"].append(f"ليلة {s['night_counter']}: المافيا لم تقتل أحداً.")


            if game_over_check(): # Check game over after processing night results
                set_page_step("game_over")
            else:
                offline_main_column.controls.append(ft.ElevatedButton("🌞 الانتقال إلى النهار", on_click=lambda e: set_page_step("day_discussion"), width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            s["night_results"] = {}

        elif s["page_step"] == "day_discussion":
            offline_main_column.controls.append(ft.Text("🌞 مرحلة النهار: النقاش والتصويت", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            
            log_container = ft.Container( # Container for logs
                content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                height=120, # Max height for scroll
                border=ft.border.all(1, ft.Colors.BLACK26),
                border_radius=5,
                padding=8,
                width=page.width * 0.9 if page.width else 320
            )
            if s["log"]:
                log_container.content.controls.append(ft.Text("أحداث اللعبة (آخر 5):", weight=ft.FontWeight.BOLD, size=16))
                for entry in reversed(s["log"][-5:]): log_container.content.controls.append(ft.Text(entry, size=14, text_align=ft.TextAlign.CENTER))
            else:
                log_container.content.controls.append(ft.Text("لا توجد أحداث بعد.", italic=True, size=14))
            offline_main_column.controls.append(log_container)
            offline_main_column.controls.append(ft.Container(height=10)) # Spacer

            offline_main_column.controls.append(ft.Text("اللاعبون الأحياء:", weight=ft.FontWeight.BOLD, size=20, text_align=ft.TextAlign.CENTER))
            alive_players_text = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            for p_alive in [p for p in s["players"] if p not in s["eliminated_players"]]:
                alive_players_text.controls.append(ft.Text(f"• {p_alive}", size=18))
            offline_main_column.controls.append(alive_players_text)
            offline_main_column.controls.append(ft.Container(height=10)) # Spacer
            offline_main_column.controls.append(ft.ElevatedButton("🗳️ بدء التصويت لطرد لاعب", on_click=lambda e: set_page_step("day_voting"), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))

        elif s["page_step"] == "day_voting":
            offline_main_column.controls.append(ft.Text("☀️ التصويت النهاري", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            offline_main_column.controls.append(ft.Text("اختر من تصوت لطرده:", size=20, text_align=ft.TextAlign.CENTER))
            alive_players_for_vote = [p for p in s["players"] if p not in s["eliminated_players"]]

            if not alive_players_for_vote or len(alive_players_for_vote) < 2: # Needs at least 2 to vote one out
                offline_main_column.controls.append(ft.Text("لا يوجد عدد كاف من اللاعبين للتصويت.", text_align=ft.TextAlign.CENTER, size=16))
                offline_main_column.controls.append(ft.ElevatedButton("متابعة لليل", on_click=lambda e: continue_to_night(), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))
            else:
                day_vote_buttons_row = ft.ResponsiveRow(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10, run_spacing=10
                )
                def vote_out_player_from_button(e, selected_player):
                    if selected_player:
                        s["eliminated_players"].append(selected_player)
                        elim_role = s['roles'].get(selected_player,'?')
                        s["log"].append(f"نهار {s['night_counter']}: تم طرد {selected_player} بالتصويت (كان {elim_role}).")
                        if game_over_check():
                            set_page_step("game_over")
                        else:
                            set_page_step("daily_summary")
                    # No else needed as button click implies a selection
                
                for p_opt_vote in alive_players_for_vote:
                    btn_vote = ft.ElevatedButton(
                        text=p_opt_vote,
                        on_click=lambda e, ch_vote=p_opt_vote: vote_out_player_from_button(e, ch_vote),
                        col={"xs": 6, "sm": 4},
                        height=55,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                    day_vote_buttons_row.controls.append(ft.Container(content=btn_vote, alignment=ft.alignment.center))
                offline_main_column.controls.append(day_vote_buttons_row)

        elif s["page_step"] == "daily_summary":
            offline_main_column.controls.append(ft.Text("📊 ملخص اليوم:", size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            day_elimination_log = next((log_entry for log_entry in reversed(s.get("log",[])) if f"نهار {s['night_counter']}" in log_entry and "تم طرد" in log_entry), None)
            if day_elimination_log:
                offline_main_column.controls.append(ft.Text(day_elimination_log.replace(f"نهار {s['night_counter']}: ", ""), color=ft.Colors.ORANGE_900, weight=ft.FontWeight.BOLD, size=18, text_align=ft.TextAlign.CENTER)) # Darker orange

            offline_main_column.controls.append(ft.Text("اللاعبون المتبقون:", weight=ft.FontWeight.BOLD, size=20, text_align=ft.TextAlign.CENTER))
            remaining_players_col = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            for player in s["players"]:
                if player not in s["eliminated_players"]:
                    remaining_players_col.controls.append(ft.Text(f"• {player} (حي)", size=18))
            offline_main_column.controls.append(remaining_players_col)
            offline_main_column.controls.append(ft.Container(height=10))

            if game_over_check(): # Re-check after displaying summary
                set_page_step("game_over")
            else:
                offline_main_column.controls.append(ft.ElevatedButton("الاستمرار إلى الليل التالي 🌙", on_click=lambda e: continue_to_night(), width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))))


        elif s["page_step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة!", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            winner = s.get("winner", "غير محدد")
            winner_color = ft.Colors.BLACK
            if winner == "المدنيون": winner_color = ft.Colors.GREEN_800
            elif winner == "المافيا": winner_color = ft.Colors.RED_800
            offline_main_column.controls.append(ft.Text(f"🏆 {winner} يفوزون!", color=winner_color, size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Larger and bolder

            offline_main_column.controls.append(ft.Text("📜 الأدوار النهائية:", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))
            
            roles_datatable_rows = []
            for player, role in s["roles"].items():
                status_icon = "✅ (حي)" if player not in s["eliminated_players"] else "💀 (تم إقصاؤه)"
                roles_datatable_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(player, size=16)),
                        ft.DataCell(ft.Text(role, size=16)),
                        ft.DataCell(ft.Text(status_icon, size=16)),
                    ])
                )
            if roles_datatable_rows:
                 offline_main_column.controls.append(
                    ft.Container(
                        content= ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("اللاعب")),
                                ft.DataColumn(ft.Text("الدور")),
                                ft.DataColumn(ft.Text("الحالة")),
                            ],
                            rows=roles_datatable_rows,
                            column_spacing=20,
                            data_row_max_height=40,
                            horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12)
                        ),
                        width=page.width * 0.95 if page.width else 380, # Responsive width
                        alignment=ft.alignment.center
                    )
                 )
            
            buttons_game_over_row = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: reset_game_state(), col={"xs":12, "sm":6}, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
                    ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home_fn, col={"xs":12, "sm":6}, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
                ],
                alignment=ft.MainAxisAlignment.CENTER, run_spacing=10, spacing=10
            )
            offline_main_column.controls.append(buttons_game_over_row)
        else:
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['page_step']}'"))
            offline_main_column.controls.append(ft.ElevatedButton("العودة للرئيسية", on_click=go_home_fn))


        if page.client_storage: page.update()


    def reset_game_state():
        _mafia_offline_state.clear()
        _mafia_offline_state.update({
            "log": [], "page_step": "setup_player_count",
            "players": [], "roles": {}, "num_players": 5,
            "current_player_role_reveal_idx": 0, "eliminated_players": [], "night_results": {},
            "night_action_step": "mafia_action", "last_doctor_save": None, "night_counter": 1,
            "day_vote_target": None,
            "detective_action_result_text": "",
            "winner": None,
            "name_inputs": [] # This was in s, should be in _mafia_offline_state if used like s["name_inputs"]
        })
        name_inputs_list_mafia.clear() # Clear the global list of TextFields too
        update_offline_ui()

    def set_page_step(step_name):
        _mafia_offline_state["page_step"] = step_name
        update_offline_ui()

    def assign_roles():
        s = _mafia_offline_state
        players = s.get("players", []) # Use .get for safety
        if not players:
            print("Error: No players to assign roles to.")
            set_page_step("input_player_names") # Go back if no players
            return

        num_p = len(players)

        # Simplified role assignment for balance and clarity
        if num_p < 5: # Minimum players
            page.snack_bar = ft.SnackBar(ft.Text(f"تحتاج إلى 5 لاعبين على الأقل للعبة مافيا متوازنة."), open=True)
            set_page_step("setup_player_count")
            if page.client_storage: page.update()
            return

        mafia_count = 1
        if 6 <= num_p <= 8: mafia_count = 2
        elif num_p >= 9: mafia_count = 3
        # Cap mafia at 3 for up to 15 players for better balance, adjust if needed for very large games

        roles_list = ['مافيا'] * mafia_count
        roles_list.append("طبيب")
        roles_list.append("محقق")

        num_civilians = num_p - len(roles_list)
        if num_civilians < 0 : # Should not happen with min 5 players and above logic
            print(f"Error in role assignment: not enough players for special roles. Players: {num_p}")
            # Fallback to simpler assignment or error
            page.snack_bar = ft.SnackBar(ft.Text("خطأ في توزيع الأدوار لعدد اللاعبين الحالي."), open=True)
            set_page_step("setup_player_count")
            if page.client_storage: page.update()
            return

        roles_list += ['مواطن'] * num_civilians

        random.shuffle(roles_list)
        s["roles"] = {player: role for player, role in zip(players, roles_list)}
        s["current_player_role_reveal_idx"] = 0
        set_page_step("show_individual_role_handoff")


    def game_over_check():
        s = _mafia_offline_state
        alive_players = [p for p in s.get("players", []) if p not in s.get("eliminated_players", [])]

        if not s.get("players"):
            s["winner"] = "خطأ في إعداد اللعبة"
            return True
        if not alive_players and s.get("players"): # All players eliminated
            s["winner"] = "لا أحد (تعادل كارثي!)"
            return True

        mafia_alive_count = 0
        non_mafia_alive_count = 0
        for p in alive_players:
            role = s.get("roles", {}).get(p)
            if role == 'مافيا':
                mafia_alive_count += 1
            elif role: # Any non-mafia role
                non_mafia_alive_count += 1
        
        if mafia_alive_count == 0 and non_mafia_alive_count > 0:
            s["winner"] = "المدنيون" # Civilians, Doctor, Detective
            return True
        # If only mafia are left, they win
        if mafia_alive_count > 0 and non_mafia_alive_count == 0:
            s["winner"] = "المافيا"
            return True
        # If mafia count is equal to or greater than non-mafia, mafia win
        if mafia_alive_count > 0 and mafia_alive_count >= non_mafia_alive_count:
            s["winner"] = "المافيا"
            return True

        return False

    def continue_to_night():
        s = _mafia_offline_state
        s["night_counter"] += 1
        s["night_action_step"] = "mafia_action"
        s["night_results"] = {}
        s["detective_action_result_text"] = ""
        set_page_step("night_phase_intro")

    reset_game_state()
    return [
        ft.Container(
            content=offline_main_column,
            expand=True,
            alignment=ft.alignment.top_center, # Changed from center for better scroll start
            padding=ft.padding.symmetric(horizontal=10, vertical=15) # Overall padding
        )
    ]


# --- ONLINE MODE LOGIC (Mafia is offline only) ---
def mafia_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    return [
        ft.Container(
            content=ft.Column([
                ft.Text("🎭 لعبة المافيا", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text("متاحة حالياً في وضع الأوفلاين فقط.", size=20, text_align=ft.TextAlign.CENTER),
                ft.Container(height=20),
                ft.ElevatedButton("🔙 العودة للقائمة", on_click=lambda e: go_home_fn(), width=250, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
            spacing=20
            ),
            expand=True,
            alignment=ft.alignment.center,
            padding=20
        )
    ]

# --- GAME ENTRY POINT ---
def mafia_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return mafia_offline_logic(page, go_home_fn)
    else:
        # This part should ideally not be reached if app.py prevents online mode for Mafia.
        return mafia_online_logic(page, go_home_fn, process_action_fn, room_code, player_name, game_rooms_ref)