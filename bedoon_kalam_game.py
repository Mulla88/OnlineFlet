# bedoon_kalam_game.py
import flet as ft
import random
import threading 
import time      
from bedoon_kalam_words import WORD_BANK

# --- OFFLINE MODE LOGIC ---
def bedoon_kalam_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {} 

    team_name_fields_offline = []
    # These are now just containers whose content will be managed by update_offline_ui
    word_display_offline_container = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    score_display_offline_container = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    correct_btn_offline = ft.ElevatedButton("✅ إجابة صحيحة", visible=False, width=180, height=50, bgcolor=ft.colors.GREEN_ACCENT_700, color=ft.colors.WHITE)
    skip_btn_offline = ft.ElevatedButton("⏭ تخطي", visible=False, width=180, height=50, bgcolor=ft.colors.RED_ACCENT_700, color=ft.colors.WHITE)
    timer_text_offline = ft.Text("الوقت: 90 ثانية", size=24, weight="bold")
    last_round_warning_offline = ft.Text("", size=18, color="red", visible=False)
    
    offline_main_column = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)

    def destroy_offline_game_state():
        event = offline_state.get("stop_timer_event")
        if isinstance(event, threading.Event):
            event.set()
            time.sleep(0.1) 
        offline_state.clear()

    def reset_offline_state_and_ui(): 
        destroy_offline_game_state()
        offline_state.update({
            "teams": [], "scores": {}, "current_team_index": 0, "used_words": [],
            "word_log": [], "current_word": None, "game_started": False,
            "round": 1, "step": "input_teams", 
            "stop_timer_event": threading.Event(),
            "max_rounds": 3, "round_duration": 90, 
        })
        update_offline_ui() 


    def get_new_word_offline():
        remaining = [w for w in WORD_BANK if w not in offline_state.get("used_words", [])]
        if not remaining:
            offline_state["used_words"] = [] 
            remaining = list(WORD_BANK)
            if not remaining:
                return "انتهت الكلمات!"
        word = random.choice(remaining)
        offline_state.setdefault("used_words", []).append(word)
        return word

    # These helper functions now just prepare the content, they don't call .update()
    def _get_word_display_content():
        controls = []
        word = offline_state.get("current_word") 
        if word and word != "انتهت الكلمات!":
            controls.append(ft.Text(f"الكلمة: {word}", size=30, weight="bold", color=ft.colors.BLUE_700, text_align=ft.TextAlign.CENTER))
        elif word: 
            controls.append(ft.Text(word, size=24, color=ft.colors.RED_700, text_align=ft.TextAlign.CENTER))
        return controls

    def _get_score_display_content():
        controls = []
        if offline_state.get("scores"):
            for team, score in offline_state.get("scores",{}).items():
                controls.append(ft.Text(f"فريق {team}: {score} نقطة", size=18))
        return controls


    def handle_end_round_offline(e=None): 
        if "stop_timer_event" in offline_state: 
            offline_state["stop_timer_event"].set()
        
        if not offline_state.get("teams") or offline_state.get("current_team_index", -1) < 0:
            print("Error: Cannot end round, team data missing in offline state.")
            set_offline_step("input_teams") 
            return

        current_team_name = offline_state["teams"][offline_state["current_team_index"]]
        round_words_summary = [
            log for log in offline_state.get("word_log", []) 
            if log.get("team") == current_team_name and log.get("round") == offline_state.get("round")
        ]

        offline_state["step"] = "round_summary"
        offline_state["current_round_summary_team"] = current_team_name
        offline_state["current_round_summary_words"] = round_words_summary
        update_offline_ui()


    def start_timer_offline():
        if "stop_timer_event" not in offline_state: return
        stop_event = offline_state["stop_timer_event"]
        stop_event.clear()
        
        round_duration = offline_state.get("round_duration", 90)
        timer_text_offline.value = f"⏳ الوقت المتبقي: {round_duration} ثانية"
        # The timer_text_offline will be part of offline_main_column, so page.update() in update_offline_ui will refresh it.
        # However, for frequent updates like a timer, updating just the control is more efficient.
        if page.client_storage: timer_text_offline.update()


        def run_timer():
            for i in range(round_duration, -1, -1): 
                if page.client_storage is None: break 
                if stop_event.is_set(): return

                timer_text_offline.value = f"⏳ الوقت المتبقي: {i} ثانية"
                if page.client_storage: timer_text_offline.update() # Efficient update for timer
                
                if i == 0: 
                    if not stop_event.is_set():
                        if page.client_storage:
                            page.run_thread_safe(lambda: handle_end_round_offline(None))
                        else: 
                            return
                    return
                time.sleep(1)

        threading.Thread(target=run_timer, daemon=True).start()
        

    def show_team_intro_offline():
        offline_state["step"] = "team_intro"
        update_offline_ui()

    def start_round_logic_offline(): 
        offline_state["step"] = "playing_round"
        offline_state["current_word"] = get_new_word_offline()
        update_offline_ui() 
        start_timer_offline()


    def handle_correct_offline(e):
        if not offline_state.get("teams") or offline_state.get("current_word", "").startswith("انتهت الكلمات"): return
        team = offline_state["teams"][offline_state["current_team_index"]]
        offline_state["scores"][team] = offline_state["scores"].get(team, 0) + 2
        offline_state.setdefault("word_log",[]).append({"team": team, "word": offline_state["current_word"], "correct": True, "round": offline_state["round"]})
        
        new_word = get_new_word_offline()
        offline_state["current_word"] = new_word
        # Instead of direct updates, let the main UI update handle it if the step is "playing_round"
        if offline_state["step"] == "playing_round":
            update_offline_ui() # This will rebuild word and score display
        
        if new_word == "انتهت الكلمات!":
            handle_end_round_offline() 


    def handle_skip_offline(e):
        if not offline_state.get("teams") or offline_state.get("current_word", "").startswith("انتهت الكلمات"): return
        team = offline_state["teams"][offline_state["current_team_index"]]
        offline_state["scores"][team] = offline_state["scores"].get(team, 0) - 0.5
        offline_state.setdefault("word_log",[]).append({"team": team, "word": offline_state["current_word"], "correct": False, "round": offline_state["round"]})

        new_word = get_new_word_offline()
        offline_state["current_word"] = new_word
        if offline_state["step"] == "playing_round":
            update_offline_ui() # This will rebuild word and score display

        if new_word == "انتهت الكلمات!":
            handle_end_round_offline()


    def start_game_setup_offline(e): 
        team_names = [tf.value.strip() for tf in team_name_fields_offline if tf.value.strip()]
        if len(team_names) < 2: 
            page.snack_bar = ft.SnackBar(ft.Text("❗ تحتاج لفريقين على الأقل."), open=True)
            if page.client_storage: page.update()
            return
        offline_state["teams"] = team_names
        offline_state["scores"] = {team: 0 for team in team_names}
        offline_state["game_started"] = True
        offline_state["round"] = 1
        offline_state["current_team_index"] = 0 
        offline_state["used_words"] = []
        offline_state["word_log"] = []
        show_team_intro_offline()


    def update_offline_ui():
        offline_main_column.controls.clear()
        s = offline_state

        if s["step"] == "input_teams":
            offline_main_column.controls.append(ft.Text("🎯 لعبة بدون كلام", size=26, weight="bold"))
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء الفرق (2 على الأقل):", size=20))
            team_name_fields_offline.clear()
            for i in range(2): 
                tf = ft.TextField(label=f"اسم الفريق {i+1}", width=300)
                team_name_fields_offline.append(tf)
                offline_main_column.controls.append(tf)
            offline_main_column.controls.append(ft.ElevatedButton("🚀 بدء اللعبة بالفرق المدخلة", on_click=start_game_setup_offline, width=250, height=50))
            offline_main_column.controls.append(ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=safe_go_home_offline, width=200, height=50))
        
        elif s["step"] == "team_intro":
            current_team = s["teams"][s["current_team_index"]]
            offline_main_column.controls.extend([
                ft.Text(f"استعد يا فريق {current_team}!", size=26, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Text(f"سيقوم أحد أعضاء فريق {current_team} بالتمثيل.", size=20, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(f"🚀 ابدأ الجولة {s['round']} لفريق {current_team}", 
                                 on_click=lambda e: start_round_logic_offline(), width=300, height=60)
            ])

        elif s["step"] == "playing_round":
            current_team = s["teams"][s["current_team_index"]]
            
            # Populate word_display_offline_container
            word_display_offline_container.controls = _get_word_display_content()
            word_display_offline_container.visible = True
            
            # Populate score_display_offline_container
            score_display_offline_container.controls = _get_score_display_content()
            score_display_offline_container.visible = True

            correct_btn_offline.visible = True
            skip_btn_offline.visible = True
            last_round_warning_offline.visible = (s["round"] == s["max_rounds"])
            last_round_warning_offline.value = "⚠️ هذا هو الدور الأخير!" if last_round_warning_offline.visible else ""

            offline_main_column.controls.extend([
                ft.Text(f"🎮 الجولة {s['round']} - فريق: {current_team}", size=20, color=ft.colors.BLUE_700),
                last_round_warning_offline,
                timer_text_offline,
                word_display_offline_container, # Add the container
                ft.Row([correct_btn_offline, skip_btn_offline], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                ft.ElevatedButton("⏹ إنهاء الجولة مبكراً", on_click=handle_end_round_offline, width=250, height=40, bgcolor=ft.colors.RED_ACCENT_100),
                ft.Divider(height=20),
                ft.Text("📊 النقاط:", size=20, weight="bold"),
                score_display_offline_container # Add the container
            ])

        elif s["step"] == "round_summary":
            summary_team = s.get("current_round_summary_team", "فريق")
            summary_words = s.get("current_round_summary_words", [])
            
            word_list_controls = [
                ft.Text(f"- {log['word']} ({'✔' if log['correct'] else '✘'})", 
                          color=ft.colors.GREEN_700 if log["correct"] else ft.colors.RED_700)
                for log in summary_words
            ]
            if not word_list_controls:
                word_list_controls.append(ft.Text("لم يتم تخمين أي كلمات.", italic=True))

            summary_column_content = ft.Column( # Renamed to avoid confusion
                controls=[
                    ft.Text(f"⏰ انتهى وقت فريق: {summary_team}", size=22, weight="bold", color="primary"),
                    ft.Text("🔤 الكلمات التي ظهرت في هذا الدور:", size=20),
                ] + word_list_controls,
                scroll=ft.ScrollMode.AUTO,
                spacing=5
            )
            def proceed_to_next_team_or_end_offline(e): 
                s["current_team_index"] += 1
                if s["current_team_index"] >= len(s["teams"]): 
                    s["current_team_index"] = 0
                    s["round"] += 1
                
                if s["round"] > s["max_rounds"]:
                    set_offline_step("game_over")
                else:
                    show_team_intro_offline() 

            offline_main_column.controls.extend([
                summary_column_content,
                ft.ElevatedButton("▶ الفريق التالي / الجولة التالية", on_click=proceed_to_next_team_or_end_offline, width=300, height=50),
                ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=safe_go_home_offline, width=200, height=40)
            ])

        elif s["step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة! النتائج النهائية:", size=24, weight="bold"))
            final_scores_list = [ft.Text(f"فريق {team}: {score} نقطة", size=20) for team, score in sorted(s.get("scores",{}).items(), key=lambda item: item[1], reverse=True)]
            offline_main_column.controls.extend(final_scores_list)
            offline_main_column.controls.extend([
                ft.ElevatedButton("🔄 العب مرة أخرى", on_click=lambda e: reset_offline_state_and_ui(), width=200, height=50),
                ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=safe_go_home_offline, width=200, height=50)
            ])
        else: 
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'"))
            offline_main_column.controls.append(ft.ElevatedButton("العودة للرئيسية", on_click=safe_go_home_offline))


        if page.client_storage: page.update()

    def set_offline_step(step_name):
        offline_state["step"] = step_name
        update_offline_ui()
        
    def safe_go_home_offline(e=None): 
        destroy_offline_game_state()
        go_home_fn() 

    correct_btn_offline.on_click = handle_correct_offline
    skip_btn_offline.on_click = handle_skip_offline
    
    reset_offline_state_and_ui() 
    return [ft.Container(content=offline_main_column, expand=True, alignment=ft.alignment.top_center, padding=10)]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
# ... (Keep your existing online logic for bedoon_kalam_online_logic as it was)
def bedoon_kalam_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    
    page_title = ft.Text(f"لعبة بدون كلام - غرفة: {room_code}", size=20, weight="bold")
    status_text = ft.Text("...", size=18, weight="bold", text_align=ft.TextAlign.CENTER)
    player_list_display = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=5, height=120, alignment=ft.MainAxisAlignment.START)
    team_score_display = ft.Column(spacing=5, alignment=ft.MainAxisAlignment.START)
    action_area = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, scroll=ft.ScrollMode.ADAPTIVE) 
    word_to_act_display = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10) 
    online_timer_display = ft.Text("الوقت: --", size=22, weight="bold")
    
    online_main_container = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    def log_debug_online(msg):
        print(f"[BedoonKalam_Online_Client:{current_player_name} session:{page.session_id}] {msg}")

    def update_ui_from_server_state_online(room_state_from_server):
        if not page.client_storage: 
            log_debug_online("Page detached, skipping UI update.")
            return

        gs = room_state_from_server.get("game_state",{}) 
        players_in_room = room_state_from_server.get("players",{})
        teams_data = gs.get("teams", {}) 
        current_player_data = players_in_room.get(current_player_name, {})
        is_host = current_player_data.get("is_host", False)
        my_team = current_player_data.get("team_name")
        current_phase = gs.get("phase", "LOBBY")

        log_debug_online(f"Updating UI. Phase: {current_phase}, My Team: {my_team}")
        status_text.value = gs.get("status_message", "...")
        
        player_list_display.controls.clear()
        player_list_display.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight="bold"))
        for p_name_iter, p_data_iter in players_in_room.items():
            team_tag = f" (فريق {p_data_iter.get('team_name', '؟')})" if p_data_iter.get('team_name') else ""
            player_list_display.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}{team_tag}")
            )
        
        team_score_display.controls.clear()
        team_score_display.controls.append(ft.Text("النقاط:", weight="bold"))
        if teams_data:
            for team_name_iter, team_info in teams_data.items():
                team_score_display.controls.append(ft.Text(f"فريق {team_name_iter}: {team_info.get('score',0)}"))
        else:
            team_score_display.controls.append(ft.Text("لم يتم تحديد الفرق بعد."))


        action_area.controls.clear()
        word_to_act_display.visible = False 
        online_timer_display.value = f"الوقت: {gs.get('timer_value', '--')}" if gs.get("round_active") else "الوقت: --"


        if current_phase == "LOBBY":
            action_area.controls.append(ft.Text("في انتظار الهوست لتحديد الفرق وبدء اللعبة.", text_align=ft.TextAlign.CENTER))
            if is_host:
                team_inputs_online = [] 
                for i in range(2): 
                    tf = ft.TextField(label=f"اسم الفريق {i+1}", width=250)
                    team_inputs_online.append(tf)
                    action_area.controls.append(tf)
                
                def setup_teams_and_start_online(e): 
                    team_names_host = [tf.value.strip() for tf in team_inputs_online if tf.value.strip()]
                    if len(team_names_host) < 2:
                        page.snack_bar = ft.SnackBar(ft.Text("تحتاج لإدخال اسمي الفريقين."),open=True)
                        if page.client_storage: page.update()
                        return
                    send_action_fn("SETUP_TEAMS_AND_START_GAME", {"team_names": team_names_host})

                action_area.controls.append(ft.ElevatedButton("🏆 إعداد الفرق وبدء اللعبة", on_click=setup_teams_and_start_online, width=250, height=50))

        elif current_phase == "TEAMS_SET": 
            action_area.controls.append(ft.Text("تم تحديد الفرق!", size=20, weight="bold", text_align=ft.TextAlign.CENTER))
            if teams_data:
                for team_name_iter, team_info in teams_data.items():
                    player_names_in_team = ", ".join(team_info.get("players", []))
                    action_area.controls.append(ft.Text(f"فريق {team_name_iter}: {player_names_in_team}", text_align=ft.TextAlign.CENTER))
            if is_host:
                action_area.controls.append(ft.ElevatedButton("▶️ بدء الدور الأول", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN"), width=250, height=50))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست لبدء الدور الأول...", text_align=ft.TextAlign.CENTER))


        elif current_phase == "TEAM_INTRO":
            acting_team = gs.get("current_acting_team")
            current_actor = gs.get("current_actor_name") 
            if my_team == acting_team:
                action_area.controls.append(ft.Text(f"استعد يا فريق {acting_team}!", size=22, weight="bold", text_align=ft.TextAlign.CENTER))
                if current_player_name == current_actor:
                    action_area.controls.append(ft.Text("أنت من سيمثل هذه الجولة!", size=18, color=ft.colors.GREEN_700, text_align=ft.TextAlign.CENTER))
                    action_area.controls.append(ft.ElevatedButton("👀 عرض الكلمة والبدء", on_click=lambda e: send_action_fn("ACTOR_READY_START_ROUND"), width=250, height=50))
                else:
                    action_area.controls.append(ft.Text(f"{current_actor} من فريقكم سيمثل. استعدوا للتخمين!", size=18, text_align=ft.TextAlign.CENTER))
            else: 
                action_area.controls.append(ft.Text(f"جولة فريق {acting_team}. {current_actor} سيمثل.", size=18, text_align=ft.TextAlign.CENTER))
            
        elif current_phase == "ACTING_ROUND":
            word_to_act_display.visible = True 
            word_to_act_display.controls.clear()

            acting_team = gs.get("current_acting_team")
            current_actor = gs.get("current_actor_name")
            current_word = gs.get("current_word_to_act", "---")
            
            if current_player_name == current_actor: 
                word_to_act_display.controls.append(ft.Text("مثل الكلمة التالية:", size=20))
                word_to_act_display.controls.append(ft.Text(current_word, size=32, weight="bold", color=ft.colors.BLUE_ACCENT_700))
                action_area.controls.extend([
                    ft.ElevatedButton("✅ خمنوها صح!", on_click=lambda e: send_action_fn("WORD_GUESSED_CORRECT"), width=180, height=50, bgcolor=ft.colors.GREEN_ACCENT_700, color=ft.colors.WHITE),
                    ft.ElevatedButton("⏭ تخطي الكلمة", on_click=lambda e: send_action_fn("SKIP_WORD"), width=180, height=50, bgcolor=ft.colors.ORANGE_ACCENT_700, color=ft.colors.WHITE),
                ])
            elif my_team == acting_team: 
                word_to_act_display.controls.append(ft.Text(f"فريقك يمثل! حاول تخمين الكلمة التي يمثلها {current_actor}.", size=18, text_align=ft.TextAlign.CENTER))
                word_to_act_display.controls.append(ft.Text("الكلمة: ؟؟؟؟؟", size=28, weight="bold", color=ft.colors.GREY_700)) 

            else: # Spectator from other team
                word_to_act_display.controls.append(ft.Text(f"فريق {acting_team} يمثل الآن. {current_actor} هو الممثل.", size=18, text_align=ft.TextAlign.CENTER))
                # MODIFIED: Spectators NOW see the word
                word_to_act_display.controls.append(ft.Text(f"الكلمة التي يمثلونها: {current_word}", size=24, weight="bold", color=ft.colors.DEEP_ORANGE_ACCENT_200)) 
                action_area.controls.append(ft.Text("لا يمكنك التخمين الآن.", size=16, italic=True))

        elif current_phase == "ROUND_SUMMARY":
            summary_data = gs.get("summary_for_ui", {}) 
            summary_team = summary_data.get("team_name", "فريق")
            summary_round_num = summary_data.get("round_number", gs.get("current_game_round","?"))
            summary_words = summary_data.get("words", [])
            
            word_list_controls = [
                ft.Text(f"- {log['word']} ({'✔' if log['correct'] else '✘'})", 
                          color=ft.colors.GREEN_700 if log["correct"] else ft.colors.RED_700)
                for log in summary_words
            ]
            if not word_list_controls:
                word_list_controls.append(ft.Text("لم يتم لعب أي كلمات في هذا الدور.", italic=True))

            action_area.controls.extend([
                ft.Text(f"⏰ ملخص دور فريق: {summary_team} (الجولة {summary_round_num})", size=22, weight="bold", color="primary"),
                ft.Text("🔤 الكلمات:", size=20),
            ] + word_list_controls)
            
            if is_host: 
                action_area.controls.append(ft.ElevatedButton("▶ الدور التالي / الجولة التالية", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN"), width=300, height=50))
            else:
                action_area.controls.append(ft.Text("في انتظار الهوست للمتابعة...", text_align=ft.TextAlign.CENTER))

        elif current_phase == "GAME_OVER":
            action_area.controls.append(ft.Text("🏁 انتهت اللعبة! النتائج النهائية:", size=24, weight="bold", text_align=ft.TextAlign.CENTER))
            if teams_data:
                sorted_teams = sorted(teams_data.items(), key=lambda item: item[1].get('score',0), reverse=True)
                for team_name_iter, team_info_iter in sorted_teams:
                    action_area.controls.append(ft.Text(f"فريق {team_name_iter}: {team_info_iter.get('score',0)} نقطة", size=20, text_align=ft.TextAlign.CENTER))
            
            if is_host:
                action_area.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى بنفس الفرق", on_click=lambda e: send_action_fn("RESTART_GAME_SAME_TEAMS"), width=250, height=50))
        
        if page.client_storage:
            log_debug_online(f"EXECUTING page.update() for phase {current_phase}")
            page.update()
        else:
            log_debug_online(f"SKIPPING page.update() for phase {current_phase} because page.client_storage is None")


    def on_server_message_online(*args_received):
        if not page.client_storage: 
            log_debug_online("Page disposed, skipping on_server_message.")
            return
        log_debug_online(f"PUBSUB_RAW_ARGS_RECEIVED: {args_received}")
        if not args_received or len(args_received) < 2:
            log_debug_online(f"Not enough arguments received in on_server_message: {len(args_received)}")
            return
        
        msg_data = args_received[1]   
        if not isinstance(msg_data, dict): 
            log_debug_online(f"Error: Extracted msg_data is not a dictionary: type={type(msg_data)}, value={msg_data}")
            return

        msg_type = msg_data.get("type")
        log_debug_online(f"Processing PubSub: Type: {msg_type}")

        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online(room_state)
            else:
                log_debug_online(f"Error: No valid room_state in message for {msg_type}. room_state: {room_state}")
        elif msg_type == "ACTION_ERROR": 
            error_msg = msg_data.get("message", "حدث خطأ ما.")
            log_debug_online(f"Action Error from server: {error_msg}")
            if page.client_storage:
                 page.snack_bar = ft.SnackBar(ft.Text(error_msg), open=True)
                 page.update()
        else:
            log_debug_online(f"Unknown message type received: {msg_type}")

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online)
    log_debug_online(f"Subscribed to topic: room_{room_code}")

    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        log_debug_online("Found initial room data on client load. Updating UI.")
        update_ui_from_server_state_online(initial_room_data)
    else:
        log_debug_online(f"Room {room_code} not found in game_rooms_ref on client load.")
        status_text.value = "خطأ في الاتصال بالغرفة."

    online_main_container.controls.extend([
        ft.Row([page_title, ft.IconButton(ft.icons.HOME, tooltip="العودة للرئيسية", on_click=go_home_fn)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        status_text,
        online_timer_display, 
        ft.Divider(),
        word_to_act_display, 
        ft.Row(
            [
                ft.Container( 
                    content=ft.Column([
                        player_list_display, 
                        ft.Divider(),
                        team_score_display
                    ], spacing=10),
                    padding=10, border=ft.border.all(1, "outline"), border_radius=5,
                    width=280, margin=ft.margin.only(right=10), alignment=ft.alignment.top_left,
                ),
                ft.VerticalDivider(width=10),
                ft.Container( 
                    content=action_area, 
                    padding=10, expand=True, alignment=ft.alignment.top_center
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            expand=True 
        )
    ])
    return [online_main_container]


# --- GAME ENTRY POINT (Called by app.py) ---
def bedoon_kalam_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return bedoon_kalam_offline_logic(page, go_home_fn)
    else:
        if not room_code or not player_name or game_rooms_ref is None:
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة للعب أونلاين."), alignment=ft.alignment.center, expand=True)]
        
        def send_bedoon_kalam_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "bedoon_kalam", action_type, payload or {})

        return bedoon_kalam_online_logic(page, go_home_fn, send_bedoon_kalam_action_to_server_wrapper, room_code, player_name, game_rooms_ref)