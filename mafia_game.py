# mafia_game.py
import flet as ft
import random

_mafia_offline_state = {}

def mafia_offline_logic(page: ft.Page, go_home_fn):

    # --- OFFLINE UI ENHANCEMENT: Persistent Home Button ---
    offline_title_bar_mafia = ft.Row(
        [
            ft.Text("🎭 لعبة المافيا (أوفلاين)", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=lambda e: safe_go_home_mafia_offline(),
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
        spacing=15 # Adjusted default spacing
    )
    name_inputs_list_mafia = []

    def safe_go_home_mafia_offline():
        # Mafia offline state is simple, reset_game_state handles it.
        # No complex event threads like timers in other games.
        reset_game_state() # Clear state before going home
        go_home_fn()

    def update_offline_ui():
        if not page.client_storage: return

        offline_main_column.controls.clear()
        offline_main_column.controls.append(offline_title_bar_mafia)
        offline_main_column.controls.append(ft.Divider(height=1, thickness=0.5))
        s = _mafia_offline_state

        current_step = s.get("page_step", "setup_player_count") # Ensure current_step is defined

        if current_step == "setup_player_count":
            # Title in offline_title_bar_mafia
            offline_main_column.controls.append(ft.Text("إعداد اللاعبين (5-15):", size=22, text_align=ft.TextAlign.CENTER)) # Adjusted
            num_display_offline = ft.Text(str(s['num_players']), size=28, weight=ft.FontWeight.BOLD) # Adjusted

            def update_num_offline_mafia(change):
                s['num_players'] = max(5, min(15, s['num_players'] + change))
                num_display_offline.value = str(s['num_players'])
                if page.client_storage: num_display_offline.update()

            offline_main_column.controls.extend([
                ft.ResponsiveRow(
                    [
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e: update_num_offline_mafia(-1), col={"xs": 4}, icon_size=28), # Adjusted
                        ft.Container(content=num_display_offline, col={"xs": 4}, alignment=ft.alignment.center),
                        ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e: update_num_offline_mafia(1), col={"xs": 4}, icon_size=28), # Adjusted
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5 # Adjusted
                ),
                ft.ElevatedButton("التالي: الأسماء", on_click=lambda e: set_page_step("input_player_names"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Adjusted
                # Redundant home button removed
            ])
        elif current_step == "input_player_names":
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء اللاعبين:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            name_inputs_list_mafia.clear()
            for i in range(s["num_players"]):
                tf = ft.TextField(label=f"اللاعب {i+1}", text_align=ft.TextAlign.CENTER, border_radius=8, height=45, text_size=14) # Adjusted
                name_inputs_list_mafia.append(tf)
                offline_main_column.controls.append(
                    ft.Container(content=tf, width=page.width * 0.85 if page.width else 280, alignment=ft.alignment.center, padding=ft.padding.only(bottom=3)) # Adjusted
                )

            def save_names_mafia(e):
                names = [tf.value.strip() for tf in name_inputs_list_mafia if tf.value.strip()]
                if len(names) != s["num_players"] or len(set(names)) != len(names) or any(not n for n in names):
                    if page.client_storage:
                        page.snack_bar = ft.SnackBar(ft.Text("الأسماء فريدة، غير فارغة، ومكتملة!"), open=True) # Compacted
                        page.update()
                    return
                s["players"] = names
                s["eliminated_players"] = []
                s["log"] = ["بدأت اللعبة!"]
                assign_roles()
            offline_main_column.controls.append(ft.ElevatedButton("تأكيد وتوزيع الأدوار", on_click=save_names_mafia, width=280, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            offline_main_column.controls.append(ft.ElevatedButton("🔙 رجوع للعدد", on_click=lambda e: set_page_step("setup_player_count"), width=260, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif current_step == "show_individual_role_handoff":
            player_name = s["players"][s["current_player_role_reveal_idx"]]
            offline_main_column.controls.extend([
                ft.Text(f"📱 أعطِ الجهاز للاعب:", size=22, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text(player_name, size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.ElevatedButton("👀 عرض دوري", on_click=lambda e: set_page_step("display_individual_role_screen"), width=260, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))) # Adjusted
            ])

        elif current_step == "display_individual_role_screen":
            player_name = s["players"][s["current_player_role_reveal_idx"]]
            role = s["roles"].get(player_name, "غير معروف")
            desc_map = {'مافيا': "مهمتك قتل المدنيين ليلاً والتعاون مع زملائك. لا تكشف هويتك!", # Shortened
                          'طبيب': "مهمتك إنقاذ لاعب واحد كل ليلة. لا تنقذ نفس اللاعب مرتين متتاليتين.",
                          'محقق': "مهمتك التحقق من هوية لاعب واحد كل ليلة (هل هو مافيا؟).",
                          'مواطن': "مهمتك اكتشاف المافيا خلال النهار والتصويت لطردهم. ابق حياً!"}
            role_color = ft.Colors.BLACK
            if role == "مافيا": role_color = ft.Colors.RED_ACCENT_700
            elif role == "طبيب": role_color = ft.Colors.GREEN_ACCENT_700
            elif role == "محقق": role_color = ft.Colors.BLUE_ACCENT_700
            elif role == "مواطن": role_color = ft.Colors.TEAL_700

            offline_main_column.controls.extend([
                ft.Text(f"{player_name}، دورك:", size=22, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text(role, size=30, weight=ft.FontWeight.BOLD, color=role_color, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Container(
                    content=ft.Text(desc_map.get(role, "وصف غير متوفر."), size=16, text_align=ft.TextAlign.CENTER, selectable=True), # Adjusted
                    padding=ft.padding.symmetric(horizontal=8), margin=ft.margin.symmetric(vertical=5) # Adjusted
                )
            ])
            if role == "مافيا":
                other_mafia = [p for p, r_val in s["roles"].items() if r_val == "مافيا" and p != player_name]
                if other_mafia:
                    offline_main_column.controls.append(ft.Text(f"زملاؤك: {', '.join(other_mafia)}", color=ft.Colors.RED_700, size=15, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted

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
            offline_main_column.controls.append(ft.ElevatedButton("فهمت، التالي", on_click=next_player_role_reveal, width=260, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif current_step == "night_phase_intro":
            step_texts = {"mafia_action": "😴 الجميع ينام... المافيا تستيقظ.",
                          "doctor_action": "😴 المافيا تنام... الطبيب يستيقظ.",
                          "detective_action": "😴 الطبيب ينام... المحقق يستيقظ."}
            s["detective_action_result_text"] = ""
            offline_main_column.controls.extend([
                ft.Text(f"ليل {s['night_counter']}", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), # Adjusted
                ft.Text(step_texts.get(s["night_action_step"],"..."), size=20, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500), # Adjusted
                ft.ElevatedButton("التالي", on_click=lambda e: set_page_step(s["night_action_step"]), width=260, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))) # Adjusted
            ])

        elif current_step in ["mafia_action", "doctor_action", "detective_action"]:
            action_prompts = {"mafia_action": "☠️ المافيا، اختاروا ضحية:",
                              "doctor_action": "⚕️ الطبيب، اختر من تنقذه:",
                              "detective_action": "🕵️ المحقق، اختر من تتحقق منه:"}
            offline_main_column.controls.append(ft.Text(action_prompts[s["page_step"]], size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            action_buttons_row = ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8, run_spacing=8 # Adjusted
            )
            error_text_mafia = ft.Text("", color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD, size=14) # Adjusted
            alive_players = [p for p in s["players"] if p not in s["eliminated_players"]]
            target_options = []
            if current_step == "mafia_action": target_options = [p for p in alive_players if s["roles"].get(p) != 'مافيا']
            elif current_step == "doctor_action": target_options = list(alive_players)
            elif current_step == "detective_action":
                detective_name = next((p_name for p_name, r_val in s["roles"].items() if r_val == 'محقق' and p_name in alive_players), None)
                target_options = [p for p in alive_players if p != detective_name]

            def submit_night_action_from_button(e, choice):
                if current_step == "mafia_action":
                    s["night_results"]["mafia_target"] = choice
                    s["night_action_step"] = "doctor_action"
                    set_page_step("night_phase_intro")
                elif current_step == "doctor_action":
                    if choice == s.get("last_doctor_save") and choice is not None:
                        error_text_mafia.value = "لا تنقذ نفس الشخص مرتين متتاليتين!" # Compacted
                        if page.client_storage: error_text_mafia.update()
                        return
                    s["night_results"]["doctor_save"] = choice
                    s["last_doctor_save"] = choice
                    s["night_action_step"] = "detective_action"
                    set_page_step("night_phase_intro")
                elif current_step == "detective_action":
                    s["night_results"]["detective_target"] = choice
                    feedback_text = ""
                    if choice:
                        target_role = s['roles'].get(choice, 'مواطن')
                        is_mafia = "نعم، مافيا 💀" if target_role == 'مافيا' else "لا، ليس مافيا ✅" # Compacted
                        feedback_text = f"تحقيق في {choice}: {is_mafia}"
                        s["log"].append(f"ل{s['night_counter']}: المحقق فحص {choice} ({target_role}).") # Compacted
                    else:
                        feedback_text = "المحقق لم يختر أحدًا."
                        s["log"].append(f"ل{s['night_counter']}: المحقق لم يفحص.") # Compacted
                    s["detective_action_result_text"] = feedback_text
                    set_page_step("detective_feedback")

            if current_step == "detective_action" and s.get("detective_action_result_text"): pass
            else:
                if target_options:
                    for p_opt in target_options:
                        btn = ft.ElevatedButton(
                            text=p_opt, on_click=lambda e, ch=p_opt: submit_night_action_from_button(e, ch),
                            col={"xs": 6, "sm": 4}, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), text_style=ft.TextStyle(size=13)) # Adjusted
                        )
                        action_buttons_row.controls.append(btn) # No container
                    offline_main_column.controls.append(action_buttons_row)
                else:
                    offline_main_column.controls.append(ft.Text("لا أهداف متاحة.", italic=True, text_align=ft.TextAlign.CENTER, size=15)) # Adjusted
                    offline_main_column.controls.append(ft.ElevatedButton("تخطي / لا هدف", on_click=lambda e: submit_night_action_from_button(e, None), width=230, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
                offline_main_column.controls.append(error_text_mafia)

        elif current_step == "detective_feedback":
            offline_main_column.controls.append(ft.Text("🕵️ نتيجة التحقيق:", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            if s.get("detective_action_result_text"):
                offline_main_column.controls.append(ft.Text(s["detective_action_result_text"], size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800, text_align=ft.TextAlign.CENTER)) # Adjusted
            else:
                offline_main_column.controls.append(ft.Text("لم يتم تحقيق.", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted
            offline_main_column.controls.append(ft.ElevatedButton("متابعة لملخص الليل", on_click=lambda e: set_page_step("night_summary"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif current_step == "night_summary":
            offline_main_column.controls.append(ft.Text(f"📜 ملخص ليلة {s['night_counter']}:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            mafia_target = s["night_results"].get("mafia_target")
            doctor_save = s["night_results"].get("doctor_save")
            if mafia_target and mafia_target == doctor_save:
                offline_main_column.controls.append(ft.Text(f"✅ تم إنقاذ {mafia_target}!", color=ft.Colors.GREEN_700, size=18, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Adjusted
                s["log"].append(f"ل{s['night_counter']}: الطبيب أنقذ {doctor_save}.") # Compacted
            elif mafia_target:
                offline_main_column.controls.append(ft.Text(f"☠️ تم قتل {mafia_target}!", color=ft.Colors.RED_700, size=18, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)) # Adjusted
                if mafia_target not in s["eliminated_players"]: s["eliminated_players"].append(mafia_target)
                s["log"].append(f"ل{s['night_counter']}: المافيا قتلت {mafia_target}.") # Compacted
            else:
                offline_main_column.controls.append(ft.Text("المافيا لم تختر أحداً.", italic=True, size=15, text_align=ft.TextAlign.CENTER)) # Adjusted
                s["log"].append(f"ل{s['night_counter']}: المافيا لم تقتل.") # Compacted
            if game_over_check(): set_page_step("game_over")
            else: offline_main_column.controls.append(ft.ElevatedButton("🌞 الانتقال للنهار", on_click=lambda e: set_page_step("day_discussion"), width=260, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            s["night_results"] = {}

        elif current_step == "day_discussion":
            offline_main_column.controls.append(ft.Text("🌞 نهار: النقاش والتصويت", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            log_container = ft.Container(
                content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER), # Adjusted
                height=100, border=ft.border.all(1, ft.Colors.BLACK26), border_radius=5, padding=6, # Adjusted
                width=page.width * 0.9 if page.width else 300 # Adjusted
            )
            if s["log"]:
                log_container.content.controls.append(ft.Text("أحداث (آخر 5):", weight=ft.FontWeight.BOLD, size=15)) # Adjusted
                for entry in reversed(s["log"][-5:]): log_container.content.controls.append(ft.Text(entry, size=13, text_align=ft.TextAlign.CENTER)) # Adjusted
            else:
                log_container.content.controls.append(ft.Text("لا أحداث.", italic=True, size=13)) # Adjusted
            offline_main_column.controls.append(log_container)
            offline_main_column.controls.append(ft.Container(height=8)) # Adjusted
            offline_main_column.controls.append(ft.Text("الأحياء:", weight=ft.FontWeight.BOLD, size=18, text_align=ft.TextAlign.CENTER)) # Adjusted
            alive_players_text = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2) # Adjusted
            for p_alive in [p for p in s["players"] if p not in s["eliminated_players"]]:
                alive_players_text.controls.append(ft.Text(f"• {p_alive}", size=16)) # Adjusted
            offline_main_column.controls.append(alive_players_text)
            offline_main_column.controls.append(ft.Container(height=8)) # Adjusted
            offline_main_column.controls.append(ft.ElevatedButton("🗳️ بدء التصويت للطرد", on_click=lambda e: set_page_step("day_voting"), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif current_step == "day_voting":
            offline_main_column.controls.append(ft.Text("☀️ تصويت نهاري", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            offline_main_column.controls.append(ft.Text("اختر من تصوت لطرده:", size=18, text_align=ft.TextAlign.CENTER)) # Adjusted
            alive_players_for_vote = [p for p in s["players"] if p not in s["eliminated_players"]]
            if not alive_players_for_vote or len(alive_players_for_vote) < 2:
                offline_main_column.controls.append(ft.Text("لا يوجد عدد كاف للتصويت.", text_align=ft.TextAlign.CENTER, size=15)) # Adjusted
                offline_main_column.controls.append(ft.ElevatedButton("متابعة لليل", on_click=lambda e: continue_to_night(), width=260, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted
            else:
                day_vote_buttons_row = ft.ResponsiveRow(
                    alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8, run_spacing=8 # Adjusted
                )
                def vote_out_player_from_button(e, selected_player):
                    if selected_player:
                        s["eliminated_players"].append(selected_player)
                        elim_role = s['roles'].get(selected_player,'?')
                        s["log"].append(f"ن{s['night_counter']}: طرد {selected_player} ({elim_role}).") # Compacted
                        if game_over_check(): set_page_step("game_over")
                        else: set_page_step("daily_summary")
                for p_opt_vote in alive_players_for_vote:
                    btn_vote = ft.ElevatedButton(
                        text=p_opt_vote, on_click=lambda e, ch_vote=p_opt_vote: vote_out_player_from_button(e, ch_vote),
                        col={"xs": 6, "sm": 4}, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), text_style=ft.TextStyle(size=13))) # Adjusted
                    day_vote_buttons_row.controls.append(btn_vote) # No container
                offline_main_column.controls.append(day_vote_buttons_row)

        elif current_step == "daily_summary":
            offline_main_column.controls.append(ft.Text("📊 ملخص اليوم:", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            day_elimination_log = next((log_entry for log_entry in reversed(s.get("log",[])) if f"ن{s['night_counter']}" in log_entry and "طرد" in log_entry), None) # Compacted log check
            if day_elimination_log:
                offline_main_column.controls.append(ft.Text(day_elimination_log.replace(f"ن{s['night_counter']}: ", ""), color=ft.Colors.ORANGE_900, weight=ft.FontWeight.BOLD, size=16, text_align=ft.TextAlign.CENTER)) # Adjusted
            offline_main_column.controls.append(ft.Text("المتبقون:", weight=ft.FontWeight.BOLD, size=18, text_align=ft.TextAlign.CENTER)) # Adjusted
            remaining_players_col = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2) # Adjusted
            for player in s["players"]:
                if player not in s["eliminated_players"]: remaining_players_col.controls.append(ft.Text(f"• {player}", size=16)) # Adjusted
            offline_main_column.controls.append(remaining_players_col)
            offline_main_column.controls.append(ft.Container(height=8)) # Adjusted
            if game_over_check(): set_page_step("game_over")
            else: offline_main_column.controls.append(ft.ElevatedButton("الاستمرار لليل 🌙", on_click=lambda e: continue_to_night(), width=280, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))) # Adjusted

        elif current_step == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة!", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            winner = s.get("winner", "غير محدد")
            winner_color = ft.Colors.BLACK
            if winner == "المدنيون": winner_color = ft.Colors.GREEN_800
            elif winner == "المافيا": winner_color = ft.Colors.RED_800
            offline_main_column.controls.append(ft.Text(f"🏆 {winner} يفوزون!", color=winner_color, size=26, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            offline_main_column.controls.append(ft.Text("📜 الأدوار النهائية:", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) # Adjusted
            roles_datatable_rows = []
            for player, role in s["roles"].items():
                status_icon = "✅ حي" if player not in s["eliminated_players"] else "💀 أُقصي" # Compacted
                roles_datatable_rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(player, size=15)), ft.DataCell(ft.Text(role, size=15)), ft.DataCell(ft.Text(status_icon, size=15)) # Adjusted
                ]))
            if roles_datatable_rows:
                 offline_main_column.controls.append(ft.Container(
                    content= ft.DataTable(
                        columns=[ft.DataColumn(ft.Text("اللاعب",size=16)), ft.DataColumn(ft.Text("الدور",size=16)), ft.DataColumn(ft.Text("الحالة",size=16))], # Adjusted
                        rows=roles_datatable_rows, column_spacing=15, data_row_max_height=35, horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12) # Adjusted
                    ), width=page.width * 0.95 if page.width else 360, alignment=ft.alignment.center # Adjusted
                 ))
            buttons_game_over_row = ft.ResponsiveRow(
                [
                    ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: reset_game_state(), col={"xs":12}, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), # Single full width
                    # Redundant home button removed
                ], alignment=ft.MainAxisAlignment.CENTER, run_spacing=8, spacing=8 # Adjusted
            )
            offline_main_column.controls.append(buttons_game_over_row)
        else: # Fallback
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['page_step']}'", size=18, color=ft.Colors.RED_700)) # Adjusted
            # Redundant home button removed

        if page.client_storage: page.update()

    def reset_game_state():
        _mafia_offline_state.clear()
        _mafia_offline_state.update({
            "log": [], "page_step": "setup_player_count",
            "players": [], "roles": {}, "num_players": 5,
            "current_player_role_reveal_idx": 0, "eliminated_players": [], "night_results": {},
            "night_action_step": "mafia_action", "last_doctor_save": None, "night_counter": 1,
            "day_vote_target": None, "detective_action_result_text": "", "winner": None,
        })
        name_inputs_list_mafia.clear()
        update_offline_ui()

    def set_page_step(step_name):
        _mafia_offline_state["page_step"] = step_name
        update_offline_ui()

    def assign_roles():
        s = _mafia_offline_state
        players = s.get("players", [])
        if not players:
            set_page_step("input_player_names")
            return
        num_p = len(players)
        if num_p < 5:
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text(f"تحتاج لـ 5 لاعبين على الأقل."), open=True) # Compacted
                page.update()
            set_page_step("setup_player_count")
            return
        mafia_count = 1
        if 6 <= num_p <= 8: mafia_count = 2
        elif num_p >= 9: mafia_count = 3
        roles_list = ['مافيا'] * mafia_count
        roles_list.append("طبيب")
        roles_list.append("محقق")
        num_civilians = num_p - len(roles_list)
        if num_civilians < 0 :
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("خطأ في توزيع الأدوار."), open=True) # Compacted
                page.update()
            set_page_step("setup_player_count")
            return
        roles_list += ['مواطن'] * num_civilians
        random.shuffle(roles_list)
        s["roles"] = {player: role for player, role in zip(players, roles_list)}
        s["current_player_role_reveal_idx"] = 0
        set_page_step("show_individual_role_handoff")

    def game_over_check():
        s = _mafia_offline_state
        alive_players = [p for p in s.get("players", []) if p not in s.get("eliminated_players", [])]
        if not s.get("players"): s["winner"] = "خطأ"; return True
        if not alive_players and s.get("players"): s["winner"] = "لا أحد!"; return True
        mafia_alive_count = sum(1 for p in alive_players if s.get("roles", {}).get(p) == 'مافيا')
        non_mafia_alive_count = len(alive_players) - mafia_alive_count
        if mafia_alive_count == 0 and non_mafia_alive_count > 0: s["winner"] = "المدنيون"; return True
        if mafia_alive_count > 0 and non_mafia_alive_count == 0: s["winner"] = "المافيا"; return True
        if mafia_alive_count > 0 and mafia_alive_count >= non_mafia_alive_count: s["winner"] = "المافيا"; return True
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
            alignment=ft.alignment.top_center,
            padding=ft.padding.symmetric(horizontal=8, vertical=10) # Adjusted
        )
    ]

# --- ONLINE MODE LOGIC (Mafia is offline only) ---
def mafia_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    online_not_available_title_bar_mafia = ft.Row(
        [
            ft.Text("🎭 لعبة المافيا", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(
                ft.Icons.HOME_ROUNDED,
                tooltip="العودة للقائمة الرئيسية",
                on_click=lambda e: go_home_fn(),
                icon_size=28
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return [
        ft.Container(
            content=ft.Column([
                online_not_available_title_bar_mafia,
                ft.Divider(height=1, thickness=0.5),
                ft.Container(height=20),
                ft.Text("متاحة حالياً في وضع الأوفلاين فقط.", size=18, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD), # Adjusted
                # Redundant home button removed
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=15 # Adjusted
            ),
            expand=True,
            alignment=ft.alignment.top_center, # Align to top
            padding=10 # Adjusted
        )
    ]

# --- GAME ENTRY POINT ---
def mafia_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return mafia_offline_logic(page, go_home_fn)
    else:
        return mafia_online_logic(page, go_home_fn, process_action_fn, room_code, player_name, game_rooms_ref)