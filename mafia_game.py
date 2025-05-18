# mafia_game.py
import flet as ft
import random
from flet import colors

_mafia_offline_state = {}

def mafia_offline_logic(page: ft.Page, go_home_fn):
    
    offline_main_column = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, 
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
    
    # No separate dialog needed for this approach

    def update_offline_ui():
        offline_main_column.controls.clear()
        s = _mafia_offline_state

        # ... (setup_player_count, input_player_names, show_individual_role_handoff, display_individual_role_screen, night_phase_intro steps are unchanged from your last working version)
        if s["page_step"] == "setup_player_count": 
            offline_main_column.controls.append(ft.Text("🎭 إعداد عدد اللاعبين (5-15):", size=24))
            num_display_offline = ft.Text(str(s['num_players']), size=22)
            def update_num_offline_mafia(change): 
                s['num_players'] = max(5, min(15, s['num_players'] + change))
                num_display_offline.value = str(s['num_players'])
                if page.client_storage: page.update(num_display_offline) 
            offline_main_column.controls.extend([
                num_display_offline,
                ft.Row([
                    ft.IconButton(ft.icons.REMOVE, on_click=lambda e: update_num_offline_mafia(-1)),
                    ft.IconButton(ft.icons.ADD, on_click=lambda e: update_num_offline_mafia(1)),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.ElevatedButton("التالي: إدخال الأسماء", on_click=lambda e: set_page_step("input_player_names"), width=200)
            ])
        elif s["page_step"] == "input_player_names":
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء اللاعبين:", size=24))
            s["name_inputs"] = [ft.TextField(label=f"اللاعب {i+1}", width=300) for i in range(s["num_players"])]
            offline_main_column.controls.extend(s["name_inputs"])
            def save_names_mafia(e):
                names = [tf.value.strip() for tf in s["name_inputs"] if tf.value.strip()]
                if len(names) != s["num_players"] or len(set(names)) != len(names):
                    page.snack_bar = ft.SnackBar(ft.Text("الأسماء يجب أن تكون فريدة ومكتملة!"), open=True)
                    if page.client_storage: page.update()
                    return
                s["players"] = names
                s["eliminated_players"] = [] 
                s["log"] = []
                assign_roles() 
            offline_main_column.controls.append(ft.ElevatedButton("تأكيد وتوزيع الأدوار", on_click=save_names_mafia, width=200))
        
        elif s["page_step"] == "show_individual_role_handoff":
            player_name = s["players"][s["current_player_role_reveal_idx"]]
            offline_main_column.controls.extend([
                ft.Text(f"📱 أعطِ الجهاز للاعب: {player_name}", size=22),
                ft.ElevatedButton("👀 عرض دوري", on_click=lambda e: set_page_step("display_individual_role_screen"), width=200)
            ])

        elif s["page_step"] == "display_individual_role_screen":
            player_name = s["players"][s["current_player_role_reveal_idx"]]
            role = s["roles"].get(player_name, "غير معروف")
            desc_map = {'مافيا': "مهمتك قتل المدنيين ليلاً والتعاون مع زملائك.", 
                          'طبيب': "أنقذ لاعبًا كل ليلة (لا تنقذ نفس الشخص مرتين متتاليتين).", 
                          'محقق': "تحقق من هوية لاعب كل ليلة (هل هو مافيا أم لا).", 
                          'مواطن': "اكتشف المافيا واطردهم في النهار."}
            offline_main_column.controls.extend([
                ft.Text(f"{player_name}، دورك هو: {role}", size=22, weight="bold", color=colors.PRIMARY),
                ft.Text(desc_map.get(role, ""), size=18, text_align=ft.TextAlign.CENTER),
            ])
            if role == "مافيا":
                other_mafia = [p for p, r_val in s["roles"].items() if r_val == "مافيا" and p != player_name]
                if other_mafia:
                    offline_main_column.controls.append(ft.Text(f"زملاؤك في المافيا: {', '.join(other_mafia)}", color=colors.RED_ACCENT_700, size=16))
            
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
            offline_main_column.controls.append(ft.ElevatedButton("فهمت، التالي", on_click=next_player_role_reveal, width=200))

        elif s["page_step"] == "night_phase_intro":
            step_texts = {"mafia_action": "😴 الجميع ينام... المافيا تستيقظ.",
                          "doctor_action": "😴 المافيا تنام... الطبيب يستيقظ.",
                          "detective_action": "😴 الطبيب ينام... المحقق يستيقظ."}
            s["detective_action_result_text"] = "" # Clear previous detective result before new night action sequence
            offline_main_column.controls.extend([
                ft.Text(f"ليل {s['night_counter']}", size=26, weight="bold"),
                ft.Text(step_texts.get(s["night_action_step"],"..."), size=20, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("التالي", on_click=lambda e: set_page_step(s["night_action_step"]), width=200)
            ])

        elif s["page_step"] in ["mafia_action", "doctor_action", "detective_action"]:
            action_prompts = {"mafia_action": "☠️ المافيا تختار ضحية:",
                              "doctor_action": "⚕️ الطبيب يختار من ينقذه:",
                              "detective_action": "🕵️ المحقق يختار من يتحقق منه:"}
            offline_main_column.controls.append(ft.Text(action_prompts[s["page_step"]], size=20))
            
            action_dropdown = None # Define to ensure it's in scope for submit_night_action

            # If it's detective action AND feedback has already been generated for this turn
            if s["page_step"] == "detective_action" and s.get("detective_action_result_text"):
                offline_main_column.controls.append(
                    ft.Text(s["detective_action_result_text"], size=18, weight="bold", color=colors.BLUE_700)
                )
                offline_main_column.controls.append(
                    ft.ElevatedButton("متابعة إلى ملخص الليل", 
                                     on_click=lambda e: set_page_step("night_summary"), 
                                     width=250, height=50)
                )
            else: # Standard action input phase (or detective before feedback)
                alive_players = [p for p in s["players"] if p not in s["eliminated_players"]]
                target_options = []

                if s["page_step"] == "mafia_action":
                    target_options = [p for p in alive_players if s["roles"].get(p) != 'مافيا']
                elif s["page_step"] == "doctor_action":
                    target_options = list(alive_players) 
                elif s["page_step"] == "detective_action":
                    detective_name = next((p_name for p_name, r_val in s["roles"].items() if r_val == 'محقق' and p_name in alive_players), None)
                    target_options = [p for p in alive_players if p != detective_name] 

                if target_options:
                    action_dropdown = ft.Dropdown(label="اختر اللاعب", options=[ft.dropdown.Option(p_opt) for p_opt in target_options], width=300)
                    offline_main_column.controls.append(action_dropdown)
                else:
                    offline_main_column.controls.append(ft.Text("لا يوجد أهداف متاحة لهذا الدور.", italic=True))

                error_text_mafia = ft.Text(color=colors.RED_700) 
                offline_main_column.controls.append(error_text_mafia)

                def submit_night_action(e):
                    choice = action_dropdown.value if action_dropdown and action_dropdown.value else None
                    
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
                            target_role = s['roles'].get(choice, 'مدني') 
                            is_mafia = "نعم" if target_role == 'مافيا' else "لا"
                            feedback_text = f"هل اللاعب {choice} من المافيا؟ {is_mafia}"
                            s["log"].append(f"ليلة {s['night_counter']}: المحقق فحص {choice} ووجد: {is_mafia} (كان {target_role}).")
                        else:
                            feedback_text = "المحقق لم يختر أحدًا."
                            s["log"].append(f"ليلة {s['night_counter']}: المحقق لم يفحص أحدًا.")
                        
                        s["detective_action_result_text"] = feedback_text # Store feedback
                        update_offline_ui() # Re-render current page to show feedback and new button
                
                if target_options:
                    offline_main_column.controls.append(ft.ElevatedButton("تأكيد الاختيار", on_click=submit_night_action, width=200))
                else: 
                    offline_main_column.controls.append(ft.ElevatedButton("تخطي / لا يوجد هدف", on_click=submit_night_action, width=200))
        
        elif s["page_step"] == "night_summary": 
            s["detective_action_result_text"] = "" # Clear for next night
            
            offline_main_column.controls.append(ft.Text(f"📜 ملخص ليلة {s['night_counter']}:", size=20, weight="bold"))
            mafia_target = s["night_results"].get("mafia_target")
            doctor_save = s["night_results"].get("doctor_save")
            
            if mafia_target and mafia_target == doctor_save:
                offline_main_column.controls.append(ft.Text(f"✅ تم إنقاذ {mafia_target} بواسطة الطبيب!", color=colors.GREEN_700))
            elif mafia_target:
                offline_main_column.controls.append(ft.Text(f"☠️ تم قتل {mafia_target} بواسطة المافيا!", color=colors.RED_700))
                if mafia_target not in s["eliminated_players"]:
                    s["eliminated_players"].append(mafia_target)
            else: 
                offline_main_column.controls.append(ft.Text("لم تختر المافيا أحداً أو لم يكن هناك هدف متاح.", italic=True))

            if game_over_check(): 
                set_page_step("game_over")
            else:
                offline_main_column.controls.append(ft.ElevatedButton("🌞 الانتقال إلى النهار", on_click=lambda e: set_page_step("day_discussion"), width=200))
            s["night_results"] = {} 

        elif s["page_step"] == "day_discussion": 
            offline_main_column.controls.append(ft.Text("🌞 مرحلة النهار: النقاش والتصويت", size=24, weight="bold"))
            if s["log"]:
                offline_main_column.controls.append(ft.Text("أحداث اللعبة (آخر 5):", weight="bold"))
                log_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=100, spacing=2)
                for entry in reversed(s["log"][-5:]): log_col.controls.append(ft.Text(entry, size=12))
                offline_main_column.controls.append(log_col)

            offline_main_column.controls.append(ft.Text("اللاعبون الأحياء:", weight="bold"))
            for p_alive in [p for p in s["players"] if p not in s["eliminated_players"]]:
                offline_main_column.controls.append(ft.Text(f"- {p_alive}"))
            offline_main_column.controls.append(ft.ElevatedButton("🗳️ بدء التصويت لطرد لاعب", on_click=lambda e: set_page_step("day_voting"), width=250))

        elif s["page_step"] == "day_voting": 
            offline_main_column.controls.append(ft.Text("☀️ التصويت النهاري", size=22))
            alive_players_for_vote = [p for p in s["players"] if p not in s["eliminated_players"]]
            if not alive_players_for_vote or len(alive_players_for_vote) < 2: 
                offline_main_column.controls.append(ft.Text("لا يوجد عدد كاف من اللاعبين للتصويت."))
                offline_main_column.controls.append(ft.ElevatedButton("متابعة لليل", on_click=lambda e: continue_to_night()))
            else:
                vote_out_dd = ft.Dropdown(label="اختر من تصوت لطرده", options=[ft.dropdown.Option(p_opt) for p_opt in alive_players_for_vote], width=300)
                offline_main_column.controls.append(vote_out_dd)
                def vote_out_player(e): 
                    selected = vote_out_dd.value
                    if selected:
                        s["eliminated_players"].append(selected)
                        elim_role = s['roles'].get(selected,'?')
                        s["log"].append(f"نهار {s['night_counter']}: تم طرد {selected} بالتصويت (كان {elim_role}).")
                        if game_over_check(): 
                            set_page_step("game_over")
                        else: 
                            set_page_step("daily_summary") 
                    else:
                        page.snack_bar = ft.SnackBar(ft.Text("الرجاء اختيار لاعب لطرده."),open=True)
                        if page.client_storage: page.update()
                offline_main_column.controls.append(ft.ElevatedButton("تأكيد التصويت بالطرد", on_click=vote_out_player))

        elif s["page_step"] == "daily_summary": 
            offline_main_column.controls.append(ft.Text("📊 ملخص اليوم:", size=22, weight="bold"))
            day_elimination_log = next((log_entry for log_entry in reversed(s.get("log",[])) if "نهار" in log_entry and "تم طرد" in log_entry), None)
            if day_elimination_log:
                offline_main_column.controls.append(ft.Text(day_elimination_log.replace(f"نهار {s['night_counter']}: ", ""), color=colors.ORANGE_800, weight="bold"))

            offline_main_column.controls.append(ft.Text("اللاعبون المتبقون:", weight="bold"))
            for player in s["players"]:
                if player not in s["eliminated_players"]:
                    offline_main_column.controls.append(ft.Text(f"- {player} (حي)"))
            
            if game_over_check():
                set_page_step("game_over") 
            else:
                offline_main_column.controls.append(ft.ElevatedButton("الاستمرار إلى الليل التالي", on_click=lambda e: continue_to_night()))


        elif s["page_step"] == "game_over": 
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة!", size=28, weight="bold"))
            winner = s.get("winner", "غير محدد")
            if winner == "المدنيون":
                offline_main_column.controls.append(ft.Text("🏆 فاز المدنيون!", color=colors.GREEN_700, size=24))
            elif winner == "المافيا":
                offline_main_column.controls.append(ft.Text("🏴 فازت المافيا!", color=colors.RED_700, size=24))
            else:
                 offline_main_column.controls.append(ft.Text(f"نتيجة: {winner}", size=24))

            offline_main_column.controls.append(ft.Text("📜 الأدوار النهائية:", size=20, weight="bold"))
            for player, role in s["roles"].items():
                status = "✅" if player not in s["eliminated_players"] else "💀"
                offline_main_column.controls.append(ft.Text(f"{player}: {role} {status}"))
            
            offline_main_column.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: reset_game_state())) 
            offline_main_column.controls.append(ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home_fn))
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
            "detective_action_result_text": "", # Initialized
            "winner": None,
            "name_inputs": [] 
        })
        update_offline_ui()

    def set_page_step(step_name):
        _mafia_offline_state["page_step"] = step_name
        update_offline_ui()

    def assign_roles():
        s = _mafia_offline_state
        players = s["players"]
        num_p = len(players)
        
        if num_p < 4: 
            page.snack_bar = ft.SnackBar(ft.Text(f"عدد اللاعبين ({num_p}) قليل جداً للعبة مافيا متوازنة (4 كحد أدنى)."), open=True)
            set_page_step("setup_player_count") 
            if page.client_storage: page.update()
            return

        mafia_count = 1
        if 7 <= num_p <= 9: mafia_count = 2
        elif num_p >= 10: mafia_count = 3
        
        roles_list = ['مافيا'] * mafia_count
        
        if num_p >= 4: 
            roles_list.append("طبيب")
        if num_p >= 5: 
            roles_list.append("محقق")
        
        num_civilians = num_p - len(roles_list)
        if num_civilians < 0: 
            print(f"Error: Negative civilians ({num_civilians}) for {num_p} players. Roles: {roles_list}")
            roles_list = roles_list[:num_p] 
            num_civilians = num_p - len(roles_list) 
            if num_civilians < 0: num_civilians = 0 
        
        roles_list += ['مواطن'] * num_civilians

        if len(roles_list) != num_p:
            print(f"CRITICAL ERROR in role assignment: Role count {len(roles_list)} != Player count {num_p}. Roles: {roles_list}")
            page.snack_bar = ft.SnackBar(ft.Text("خطأ في توزيع الأدوار!"), open=True)
            set_page_step("setup_player_count")
            if page.client_storage: page.update()
            return

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
        if not alive_players : 
            s["winner"] = "لا أحد (تعادل كارثي!)" 
            return True 

        mafia_alive_count = 0
        non_mafia_alive_count = 0
        for p in alive_players:
            if s.get("roles", {}).get(p) == 'مافيا':
                mafia_alive_count += 1
            else:
                non_mafia_alive_count += 1
        
        if mafia_alive_count == 0 and non_mafia_alive_count > 0: 
            s["winner"] = "المدنيون"
            return True
        if mafia_alive_count > 0 and non_mafia_alive_count == 0: 
            s["winner"] = "المافيا"
            return True
        if mafia_alive_count > 0 and mafia_alive_count >= non_mafia_alive_count :
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
    return [ft.Container(content=offline_main_column, expand=True, alignment=ft.alignment.top_center, padding=10)]


# --- ONLINE MODE LOGIC (Mafia is offline only) ---
def mafia_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    return [
        ft.Container(
            content=ft.Column([
                ft.Text("لعبة المافيا متاحة حالياً في وضع الأوفلاين فقط.", size=20, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("🔙 العودة للقائمة", on_click=lambda e: go_home_fn(), width=200)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, vertical_alignment=ft.MainAxisAlignment.CENTER, expand=True),
            expand=True, alignment=ft.alignment.center
        )
    ]

# --- GAME ENTRY POINT ---
def mafia_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online: 
        return mafia_offline_logic(page, go_home_fn)
    else:
        return mafia_online_logic(page, go_home_fn, process_action_fn, room_code, player_name, game_rooms_ref)