# taboo_game.py
import flet as ft
import random
import threading
import time
from taboo_words import WORD_BANK 

# --- OFFLINE MODE LOGIC ---
_taboo_offline_state = {} 

def taboo_offline_logic(page: ft.Page, go_home_fn):
    team_name_fields_offline = []
    word_display_offline_container = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
    score_display_offline_container = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
    
    correct_btn_offline = ft.ElevatedButton("✅ إجابة صحيحة", visible=False, width=180, height=50, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE)
    skip_btn_offline = ft.ElevatedButton("⏭ تخطي/ممنوعة", visible=False, width=180, height=50, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE)
    timer_text_offline = ft.Text("الوقت: 60", size=24, weight="bold")
    last_round_warning_offline = ft.Text("", size=18, color="red", visible=False)

    offline_main_column = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, 
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)

    def destroy_taboo_offline_state(): 
        event = _taboo_offline_state.get("stop_timer_event")
        if isinstance(event, threading.Event):
            event.set()
            time.sleep(0.1)
        _taboo_offline_state.clear()

    def reset_taboo_offline_game(): 
        destroy_taboo_offline_state()
        _taboo_offline_state.update({
            "teams": [], "scores": {}, "current_team_index": 0, "used_words_secrets": [],
            "word_log": [], "current_word_obj": None, "game_started": False,
            "round": 1, "step": "input_teams", 
            "stop_timer_event": threading.Event(),
            "max_rounds": 3, "round_duration": 60,
        })
        update_taboo_offline_ui() 

    def get_new_taboo_word_offline(): 
        remaining = [w for w in WORD_BANK if isinstance(w, dict) and w.get("secret") and w["secret"] not in _taboo_offline_state.get("used_words_secrets", [])]
        if not remaining:
            _taboo_offline_state["used_words_secrets"] = [] 
            remaining = [w for w in WORD_BANK if isinstance(w, dict) and w.get("secret")]
            if not remaining:
                return None 
        word_obj = random.choice(remaining)
        _taboo_offline_state.setdefault("used_words_secrets", []).append(word_obj["secret"])
        return word_obj

    def _get_taboo_word_display_content(): # For Offline
        controls = []
        word_obj = _taboo_offline_state.get("current_word_obj")
        if word_obj:
            controls.append(ft.Text(f"الكلمة السرية: {word_obj['secret']}", size=26, weight="bold", color=ft.Colors.BLUE_700, text_align=ft.TextAlign.CENTER))
            controls.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.DO_NOT_DISTURB_ON_OUTLINED, color=ft.Colors.RED_700, size=24),
                        ft.Text("كلمات ممنوعة:", size=20, color=ft.Colors.RED_700, weight="bold")
                    ], 
                    alignment=ft.MainAxisAlignment.CENTER, spacing=5
                )
            )
            forbidden_list_col = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2) 
            for w_forbidden in word_obj.get("forbidden", []):
                forbidden_list_col.controls.append(ft.Text(f"• {w_forbidden}", color=ft.Colors.RED_700, size=16)) # Using bullet point
            controls.append(forbidden_list_col)
        elif _taboo_offline_state.get("current_word_obj") is None and _taboo_offline_state.get("step") == "playing_round":
             controls.append(ft.Text("انتهت الكلمات!", size=24, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER))
        return controls

    def _get_taboo_score_display_content():
        controls = []
        if _taboo_offline_state.get("scores"):
            for team, score in _taboo_offline_state.get("scores",{}).items():
                controls.append(ft.Text(f"فريق {team}: {score} نقطة", size=18))
        return controls
    
    # ... (rest of offline logic: end_taboo_round_offline, start_taboo_timer_offline, etc. remains the same)
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
        timer_text_offline.value = f"⏳ الوقت المتبقي: {duration} ثانية"
        if page.client_storage: timer_text_offline.update() 

        def run_timer():
            for i in range(duration, -1, -1):
                if not page.client_storage or stop_event.is_set(): return
                timer_text_offline.value = f"⏳ الوقت المتبقي: {i} ثانية"
                if page.client_storage: timer_text_offline.update()
                if i == 0:
                    if not stop_event.is_set() and page.client_storage:
                        page.run_thread_safe(lambda: end_taboo_round_offline(None))
                    return
                time.sleep(1)
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
            timer_text_offline.value = "لا توجد كلمات لبدء الجولة!"
            if page.client_storage: timer_text_offline.update()

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
        if s["step"] == "playing_round": 
            update_taboo_offline_ui() 
        if not s["current_word_obj"]: end_taboo_round_offline()


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
        if s["step"] == "playing_round": 
            update_taboo_offline_ui()
        if not s["current_word_obj"]: end_taboo_round_offline()

    def start_taboo_game_from_inputs_offline(e): 
        s = _taboo_offline_state
        team_names = [tf.value.strip() for tf in team_name_fields_offline if tf.value.strip()]
        if len(team_names) < 2:
            page.snack_bar = ft.SnackBar(ft.Text("❗ أدخل على الأقل اسمين لفريقين."), open=True)
            if page.client_storage: page.update()
            return
        s["teams"] = team_names
        s["scores"] = {team: 0.0 for team in team_names}
        s["game_started"] = True
        s["round"] = 1
        s["current_team_index"] = 0
        s["used_words_secrets"] = []
        s["word_log"] = []
        start_taboo_round_offline() 

    def set_taboo_offline_step(step_name): 
        _taboo_offline_state["step"] = step_name
        update_taboo_offline_ui()

    def safe_go_home_taboo_offline(e=None): 
        destroy_taboo_offline_state()
        go_home_fn()

    def update_taboo_offline_ui(): 
        offline_main_column.controls.clear()
        s = _taboo_offline_state

        if s["step"] == "input_teams":
            offline_main_column.controls.append(ft.Text("🎯 لعبة تابو", size=26, weight="bold"))
            offline_main_column.controls.append(ft.Text("👥 أدخل أسماء الفرق (فريقان):", size=20))
            team_name_fields_offline.clear()
            for i in range(2): 
                tf = ft.TextField(label=f"اسم الفريق {i+1}", width=300)
                team_name_fields_offline.append(tf)
                offline_main_column.controls.append(tf)
            offline_main_column.controls.append(ft.ElevatedButton("🚀 ابدأ اللعبة", on_click=start_taboo_game_from_inputs_offline, width=200, height=50))
            offline_main_column.controls.append(ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=safe_go_home_taboo_offline, width=200, height=50))

        elif s["step"] == "playing_round":
            current_team = s["teams"][s["current_team_index"]]
            last_round_warning_offline.visible = (s["round"] == s.get("max_rounds",3))
            last_round_warning_offline.value = "⚠️ هذا هو الدور الأخير!" if last_round_warning_offline.visible else ""
            
            word_display_offline_container.controls = _get_taboo_word_display_content()
            score_display_offline_container.controls = _get_taboo_score_display_content()
            word_display_offline_container.visible = True
            score_display_offline_container.visible = True
            correct_btn_offline.visible = True
            skip_btn_offline.visible = True
            
            offline_main_column.controls.extend([
                ft.Text(f"🎮 الجولة {s['round']} - فريق: {current_team}", size=20, color=ft.Colors.BLUE_700),
                last_round_warning_offline,
                timer_text_offline,
                word_display_offline_container, 
                ft.Row([correct_btn_offline, skip_btn_offline], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                ft.ElevatedButton("⏹ إنهاء الدور", on_click=end_taboo_round_offline, width=200, height=40, bgcolor=ft.Colors.AMBER_ACCENT_100),
                ft.Divider(height=10),
                ft.Text("📊 النقاط:", size=20),
                score_display_offline_container, 
            ])

        elif s["step"] == "round_summary":
            summary_data = s.get("current_round_summary_data", {})
            team_name = summary_data.get("team", "فريق")
            words = summary_data.get("words", [])
            
            summary_controls_content = [ 
                ft.Text(f"⏰ انتهى الوقت! فريق: {team_name}", size=22, weight="bold", color="primary"),
                ft.Text("🔤 الكلمات التي ظهرت:", size=20)
            ]
            if not words:
                summary_controls_content.append(ft.Text("لم يتم لعب أي كلمات.", italic=True))
            for log_item in words:
                summary_controls_content.append(ft.Text(f"- {log_item['word']} ({'✔' if log_item['correct'] else '✘'})", 
                                                color=ft.Colors.GREEN_700 if log_item["correct"] else ft.Colors.RED_700))
            
            def next_team_taboo_offline(e):
                s["current_team_index"] += 1
                if s["current_team_index"] >= len(s["teams"]):
                    s["current_team_index"] = 0
                    s["round"] += 1
                start_taboo_round_offline() 

            offline_main_column.controls.extend(summary_controls_content)
            offline_main_column.controls.append(ft.ElevatedButton("▶ الفريق التالي / الجولة التالية", on_click=next_team_taboo_offline, width=250, height=50))
            offline_main_column.controls.append(ft.ElevatedButton("🏠 العودة للرئيسية", on_click=safe_go_home_taboo_offline, width=200, height=40))

        elif s["step"] == "game_over":
            offline_main_column.controls.append(ft.Text("🏁 انتهت اللعبة! النتائج النهائية:", size=24, weight="bold"))
            sorted_scores = sorted(s.get("scores",{}).items(), key=lambda item: item[1], reverse=True)
            for team, score in sorted_scores:
                 offline_main_column.controls.append(ft.Text(f"فريق {team}: {score} نقطة", size=20))

            offline_main_column.controls.extend([
                ft.ElevatedButton("🔄 العب مرة أخرى", on_click=reset_taboo_offline_game, width=200, height=50),
                ft.ElevatedButton("🏠 العودة للرئيسية", on_click=safe_go_home_taboo_offline, width=200, height=50)
            ])
        else: 
            offline_main_column.controls.append(ft.Text(f"خطأ: صفحة غير معروفة '{s['step']}'"))
            offline_main_column.controls.append(ft.ElevatedButton("العودة للرئيسية", on_click=safe_go_home_taboo_offline))

        if page.client_storage: page.update()
    
    correct_btn_offline.on_click = handle_correct_taboo_offline
    skip_btn_offline.on_click = handle_skip_taboo_offline

    reset_taboo_offline_game() 
    return [ft.Container(content=offline_main_column, expand=True, alignment=ft.alignment.top_center, padding=10)]


# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def taboo_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    page_title = ft.Text(f"لعبة تابو - غرفة: {room_code}", size=20, weight="bold")
    status_text = ft.Text("قيد التحميل...", size=18, weight="bold", text_align=ft.TextAlign.CENTER)
    player_list_display_online = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=5, height=120, alignment=ft.MainAxisAlignment.START)
    team_score_display_online = ft.Column(spacing=5, alignment=ft.MainAxisAlignment.START)
    action_area_online = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, scroll=ft.ScrollMode.ADAPTIVE) 
    word_card_display_online = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5) 
    online_timer_display_taboo = ft.Text("الوقت: --", size=22, weight="bold")
    
    online_main_container = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    def log_debug_online(msg):
        print(f"[Taboo_Online_Client:{current_player_name} session:{page.session_id}] {msg}")

    def update_ui_from_server_state_online_taboo(room_state_from_server):
        if not page.client_storage: 
            log_debug_online("Page detached, skipping UI update.")
            return

        gs = room_state_from_server.get("game_state",{}) 
        players_in_room = room_state_from_server.get("players",{})
        teams_data = gs.get("teams_online", {}) 
        current_player_data = players_in_room.get(current_player_name, {})
        is_host = current_player_data.get("is_host", False)
        my_team_name = current_player_data.get("team_name")
        current_phase = gs.get("phase", "LOBBY")

        log_debug_online(f"Taboo online UI update, phase: {current_phase}, My Team: {my_team_name}")
        status_text.value = gs.get("status_message", "...")
        
        player_list_display_online.controls.clear()
        player_list_display_online.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight="bold"))
        for p_name, p_data in players_in_room.items():
            team_tag = f" (فريق {p_data.get('team_name', '؟')})" if p_data.get('team_name') else ""
            player_list_display_online.controls.append(
                ft.Text(f"• {p_data.get('name','Unknown')} {'👑' if p_data.get('is_host') else ''}{team_tag}")
            )
        
        team_score_display_online.controls.clear()
        team_score_display_online.controls.append(ft.Text("النقاط:", weight="bold"))
        if teams_data:
            for team_name_iter, team_info in teams_data.items():
                team_score_display_online.controls.append(ft.Text(f"فريق {team_name_iter}: {team_info.get('score',0)}"))
        else:
            team_score_display_online.controls.append(ft.Text("لم يتم تحديد الفرق بعد."))

        action_area_online.controls.clear()
        word_card_display_online.controls.clear()
        word_card_display_online.visible = False
        online_timer_display_taboo.value = f"الوقت: {gs.get('timer_value', '--')}" if gs.get("round_active") else "الوقت: --"


        if current_phase == "LOBBY":
            action_area_online.controls.append(ft.Text("في انتظار الهوست لتحديد الفرق وبدء اللعبة.", text_align=ft.TextAlign.CENTER))
            if is_host:
                team_inputs_host = [ft.TextField(label=f"اسم الفريق {i+1}", width=250) for i in range(2)] 
                action_area_online.controls.extend(team_inputs_host)
                
                def setup_taboo_teams_host(e):
                    team_names = [tf.value.strip() for tf in team_inputs_host if tf.value.strip()]
                    if len(team_names) != 2: 
                        page.snack_bar = ft.SnackBar(ft.Text("تحتاج لإدخال اسمي الفريقين بالضبط."),open=True)
                        if page.client_storage: page.update()
                        return
                    send_action_fn("SETUP_TABOO_GAME_HOST", {"team_names": team_names})
                action_area_online.controls.append(ft.ElevatedButton("🏆 إعداد فرق تابو والبدء", on_click=setup_taboo_teams_host, width=250, height=50))

        elif current_phase == "TEAMS_SET_TABOO":
            action_area_online.controls.append(ft.Text("تم تحديد فرق تابو!", size=20, weight="bold", text_align=ft.TextAlign.CENTER))
            if teams_data:
                for team_name_iter, team_info in teams_data.items():
                    player_names_in_team = ", ".join(team_info.get("players", []))
                    action_area_online.controls.append(ft.Text(f"فريق {team_name_iter}: {player_names_in_team}", text_align=ft.TextAlign.CENTER))
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("▶️ بدء الدور الأول لتابو", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN_TABOO"), width=250, height=50))
            else:
                action_area_online.controls.append(ft.Text("في انتظار الهوست لبدء الدور الأول...", text_align=ft.TextAlign.CENTER))

        elif current_phase == "TEAM_INTRO_TABOO":
            acting_team = gs.get("current_acting_team_online")
            current_actor = gs.get("current_actor_name_online") 
            action_area_online.controls.append(ft.Text(f"استعداد فريق: {acting_team}", size=22, weight="bold", text_align=ft.TextAlign.CENTER))
            if current_player_name == current_actor:
                action_area_online.controls.append(ft.Text("أنت من سيصف الكلمات هذه الجولة!", size=18, color=ft.Colors.GREEN_700, text_align=ft.TextAlign.CENTER))
                action_area_online.controls.append(ft.ElevatedButton("👀 عرض الكلمة والبدء", on_click=lambda e: send_action_fn("ACTOR_READY_START_ROUND_TABOO"), width=250, height=50))
            elif my_team_name == acting_team:
                action_area_online.controls.append(ft.Text(f"{current_actor} من فريقكم سيصف الكلمات. استعدوا للتخمين!", size=18, text_align=ft.TextAlign.CENTER))
            else: 
                action_area_online.controls.append(ft.Text(f"{current_actor} من فريق {acting_team} سيصف الكلمات.", size=18, text_align=ft.TextAlign.CENTER))

        elif current_phase == "ACTING_ROUND_TABOO":
            word_card_display_online.visible = True
            current_actor = gs.get("current_actor_name_online")
            current_word_obj = gs.get("current_word_obj_online", {})
            
            # Common display for secret word (if applicable)
            secret_word_text = current_word_obj.get("secret", "تحميل...")
            if current_player_name != current_actor and my_team_name == gs.get("current_acting_team_online"):
                secret_word_text = "الكلمة السرية: ؟؟؟" # Teammates don't see the word

            word_card_display_online.controls.append(
                ft.Text(secret_word_text, size=30, weight="bold", 
                        color=(ft.Colors.BLUE_ACCENT_700 if current_player_name == current_actor or my_team_name != gs.get("current_acting_team_online") else ft.Colors.GREY_700)
                       )
            )

            # Display forbidden words for actor and opposing team
            if current_player_name == current_actor or (my_team_name and my_team_name != gs.get("current_acting_team_online")):
                word_card_display_online.controls.append(
                     ft.Row(
                        [
                            ft.Icon(ft.Icons.DO_NOT_DISTURB_ON_OUTLINED, color=ft.Colors.RED_700, size=24),
                            ft.Text("كلمات ممنوعة:", size=20, color=ft.Colors.RED_700, weight="bold")
                        ], 
                        alignment=ft.MainAxisAlignment.CENTER, spacing=5
                    )
                )
                forbidden_col = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)
                for fb_word in current_word_obj.get("forbidden", []):
                    forbidden_col.controls.append(ft.Text(f"• {fb_word}", size=16, color=ft.Colors.RED_700)) # Using bullet
                word_card_display_online.controls.append(forbidden_col)
            
            # Action buttons for actor
            if current_player_name == current_actor:
                action_area_online.controls.extend([
                    ft.ElevatedButton("✅ خمنوها صح!", key="taboo_correct", on_click=lambda e: send_action_fn("WORD_GUESSED_CORRECT_TABOO"), width=180, height=50, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE),
                    ft.ElevatedButton("⏭ تخطي / كلمة ممنوعة", key="taboo_skip", on_click=lambda e: send_action_fn("SKIP_WORD_TABOO"), width=180, height=50, bgcolor=ft.Colors.ORANGE_ACCENT_700, color=ft.Colors.WHITE),
                ])
            elif my_team_name == gs.get("current_acting_team_online"): # Teammate of actor
                 action_area_online.controls.append(ft.Text(f"{current_actor} يصف الكلمات. استعدوا للتخمين!", size=16, italic=True, text_align=ft.TextAlign.CENTER))
            else: # Opposing team
                action_area_online.controls.append(ft.Text("راقبوا استخدام الكلمات الممنوعة!", size=16, italic=True, text_align=ft.TextAlign.CENTER))


        elif current_phase == "ROUND_SUMMARY_TABOO":
            summary_data = gs.get("summary_for_ui_taboo", {}) 
            summary_team = summary_data.get("team_name", "فريق")
            summary_round_num = summary_data.get("round_number", gs.get("current_game_round_online","?"))
            summary_words = summary_data.get("words", [])
            
            word_list_controls = [ft.Text(f"- {log['word']} ({'✔' if log['correct'] else '✘'})", color=ft.Colors.GREEN_700 if log["correct"] else ft.Colors.RED_700) for log in summary_words]
            if not word_list_controls: word_list_controls.append(ft.Text("لم يتم لعب أي كلمات في هذا الدور.", italic=True))

            action_area_online.controls.extend([
                ft.Text(f"⏰ ملخص دور فريق: {summary_team} (الجولة {summary_round_num})", size=22, weight="bold", color="primary"),
                ft.Text("🔤 الكلمات:", size=20)] + word_list_controls)
            
            if is_host: 
                action_area_online.controls.append(ft.ElevatedButton("▶ الدور التالي / الجولة التالية", on_click=lambda e: send_action_fn("PROCEED_TO_NEXT_TURN_TABOO"), width=300, height=50))
            else:
                action_area_online.controls.append(ft.Text("في انتظار الهوست للمتابعة...", text_align=ft.TextAlign.CENTER))

        elif current_phase == "GAME_OVER_TABOO":
            action_area_online.controls.append(ft.Text("🏁 انتهت لعبة تابو! النتائج النهائية:", size=24, weight="bold", text_align=ft.TextAlign.CENTER))
            if teams_data:
                sorted_teams = sorted(teams_data.items(), key=lambda item: item[1].get('score',0), reverse=True)
                for team_name_iter, team_info_iter in sorted_teams:
                    action_area_online.controls.append(ft.Text(f"فريق {team_name_iter}: {team_info_iter.get('score',0)} نقطة", size=20, text_align=ft.TextAlign.CENTER))
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("🔄 العب تابو مرة أخرى بنفس الفرق", on_click=lambda e: send_action_fn("RESTART_GAME_SAME_TEAMS_TABOO"), width=250, height=50))
        
        if page.client_storage:
            log_debug_online(f"EXECUTING page.update() for Taboo phase {current_phase}")
            page.update()

    def on_server_message_online_taboo(*args_received):
        if not page.client_storage: return
        log_debug_online(f"TABOO_PUBSUB_RAW_ARGS_RECEIVED: {args_received}")
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]   
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")
        log_debug_online(f"Processing Taboo PubSub: Type: {msg_type}")
        if msg_type in ["GAME_STATE_UPDATE", "PLAYER_JOINED", "PLAYER_LEFT"]:
            room_state = msg_data.get("room_state")
            if room_state and isinstance(room_state, dict):
                update_ui_from_server_state_online_taboo(room_state)
        elif msg_type == "ACTION_ERROR":
            error_msg = msg_data.get("message", "حدث خطأ في تابو.")
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text(error_msg), open=True); page.update()

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online_taboo)
    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data: update_ui_from_server_state_online_taboo(initial_room_data)

    online_main_container.controls.extend([
        ft.Row([page_title, ft.IconButton(ft.Icons.HOME, tooltip="العودة للرئيسية", on_click=go_home_fn)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(), status_text, online_timer_display_taboo, ft.Divider(),
        word_card_display_online, 
        ft.Row([
            ft.Container(content=ft.Column([player_list_display_online, ft.Divider(), team_score_display_online]), 
                         padding=10, border=ft.border.all(1, "outline"), border_radius=5, width=280, margin=ft.margin.only(right=10)),
            ft.VerticalDivider(),
            ft.Container(content=action_area_online, padding=10, expand=True, alignment=ft.alignment.top_center)
        ], vertical_alignment=ft.CrossAxisAlignment.START, expand=True),
    ])
    return [online_main_container]


# --- GAME ENTRY POINT ---
def taboo_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return taboo_offline_logic(page, go_home_fn)
    else:
        if not all([room_code, player_name, game_rooms_ref]):
             return [ft.Container(content=ft.Text("خطأ في تحميل لعبة تابو أونلاين."), alignment=ft.alignment.center, expand=True)]
        
        def send_taboo_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "taboo", action_type, payload or {})
            
        return taboo_online_logic(page, go_home_fn, send_taboo_action_to_server_wrapper, room_code, player_name, game_rooms_ref)