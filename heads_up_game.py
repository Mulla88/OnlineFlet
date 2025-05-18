
# heads_up_game.py
import flet as ft
import random
import threading
import time
from heads_up_words import HEADS_UP_WORDS 

_game_state_heads_up = {} 

def heads_up_game_offline_logic(page: ft.Page, go_home_fn):
    word_text_control = ft.Text("", size=50, weight="bold", text_align=ft.TextAlign.CENTER, height=100)
    timer_text_control = ft.Text("الوقت: 60", size=30, color=ft.Colors.RED_ACCENT_700, weight="bold")
    score_text_control = ft.Text("النقاط: 0", size=24, color=ft.Colors.GREEN_700)
    
    main_content_area = ft.Column(
        expand=True, 
        scroll=ft.ScrollMode.ADAPTIVE, 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
        spacing=20,
    )

    def initialize_game_state():
        _game_state_heads_up.clear()
        _game_state_heads_up.update({
            "num_players": 2,
            "players_names_list": [],
            "current_player_index": 0,
            "is_playing_round": False,
            "words_shown_this_round_unique": set(), 
            "current_round_word_log": [], 
            "current_round_score": 0,
            "all_player_scores": {},
            "current_active_word": "", 
            "current_page_step": "select_num_players", # Start with setup after rules (from app.py)
            "stop_timer_event": threading.Event(),
            "round_duration": 60,
        })
        update_main_ui() # Update UI after setting initial state

    def cleanup_and_go_home_offline(e=None):
        if "stop_timer_event" in _game_state_heads_up:
            _game_state_heads_up["stop_timer_event"].set()
            time.sleep(0.1) 
        _game_state_heads_up.clear() 
        go_home_fn() 

    def get_new_word_for_round():
        shown_this_round = _game_state_heads_up.get("words_shown_this_round_unique", set())
        available_words = [w for w in HEADS_UP_WORDS if w not in shown_this_round]
        
        if not available_words:
            if not HEADS_UP_WORDS: return "لا توجد كلمات في القائمة!"
            return "انتهت الكلمات الفريدة لهذه الجولة!"

        word = random.choice(available_words)
        _game_state_heads_up.setdefault("words_shown_this_round_unique", set()).add(word)
        return word

    def _log_word_action(word, status):
        if word and not word.startswith("انتهت الكلمات"):
            _game_state_heads_up.setdefault("current_round_word_log", []).append({"word": word, "status": status})

    def _display_new_active_word():
        if not _game_state_heads_up.get("is_playing_round"): return
        
        new_word = get_new_word_for_round()
        _game_state_heads_up["current_active_word"] = new_word
        word_text_control.value = new_word

        if new_word.startswith("انتهت الكلمات"):
             word_text_control.color = ft.Colors.RED_700
        else:
             word_text_control.color = ft.Colors.BLACK # Default color
        
        if page.client_storage:
            page.update(word_text_control)

    def handle_correct_guess(e=None):
        if not _game_state_heads_up.get("is_playing_round"): return
        
        current_word = _game_state_heads_up.get("current_active_word", "")
        if current_word.startswith("انتهت الكلمات"): return

        _log_word_action(current_word, "correct")
        _game_state_heads_up["current_round_score"] += 1.0 
        score_text_control.value = f"النقاط: {_game_state_heads_up['current_round_score']}"
        if page.client_storage: page.update(score_text_control)
        
        _display_new_active_word() 

    def handle_skip_action(e=None): 
        if not _game_state_heads_up.get("is_playing_round"): return

        current_word = _game_state_heads_up.get("current_active_word", "")
        if current_word and not current_word.startswith("انتهت الكلمات"):
            _log_word_action(current_word, "skipped")
            _game_state_heads_up["current_round_score"] -= 0.5
            score_text_control.value = f"النقاط: {_game_state_heads_up['current_round_score']}"
            if page.client_storage: page.update(score_text_control)
        
        _display_new_active_word() 

    def handle_round_end(e=None): 
        if _game_state_heads_up.get("is_playing_round"): 
            _game_state_heads_up["stop_timer_event"].set() 
            _game_state_heads_up["is_playing_round"] = False
            
            current_word_at_end = _game_state_heads_up.get("current_active_word", "")
            last_logged_entry = _game_state_heads_up.get("current_round_word_log", [])[-1] if _game_state_heads_up.get("current_round_word_log") else None
            if current_word_at_end and not current_word_at_end.startswith("انتهت الكلمات"):
                if not last_logged_entry or last_logged_entry["word"] != current_word_at_end: # Avoid double logging
                     _log_word_action(current_word_at_end, "skipped") 

            player_name = _game_state_heads_up["players_names_list"][_game_state_heads_up["current_player_index"]]
            current_total_score = _game_state_heads_up.get("all_player_scores", {}).get(player_name, 0.0)
            _game_state_heads_up["all_player_scores"][player_name] = current_total_score + _game_state_heads_up["current_round_score"]
            
            set_current_page_step("round_summary") 
            
    def start_timer_for_round():
        _game_state_heads_up["stop_timer_event"].clear()
        duration = _game_state_heads_up.get("round_duration", 60)
        timer_text_control.value = f"الوقت: {duration}"
        if page.client_storage: page.update(timer_text_control) 

        def timer_thread_run():
            for i in range(duration, -1, -1):
                if not page.client_storage or _game_state_heads_up.get("stop_timer_event", threading.Event()).is_set():
                    return
                
                timer_text_control.value = f"الوقت: {i}"
                if page.client_storage: page.update(timer_text_control) 

                if i == 0:
                    if not _game_state_heads_up.get("stop_timer_event", threading.Event()).is_set():
                        if page.client_storage: page.run_thread_safe(lambda: handle_round_end(None)) 
                    return
                time.sleep(1)
        
        threading.Thread(target=timer_thread_run, daemon=True).start()

    def start_player_round():
        _game_state_heads_up["is_playing_round"] = True
        _game_state_heads_up["current_page_step"] = "playing_round_active"
        _game_state_heads_up["current_round_score"] = 0.0 
        _game_state_heads_up["words_shown_this_round_unique"] = set() 
        _game_state_heads_up["current_round_word_log"] = [] 
        
        score_text_control.value = "النقاط: 0.0" 
        word_text_control.color = ft.Colors.BLACK 
        
        update_main_ui() 
        _display_new_active_word() 
        start_timer_for_round()

    def proceed_from_summary():
        _game_state_heads_up["current_player_index"] += 1
        if _game_state_heads_up["current_player_index"] >= len(_game_state_heads_up["players_names_list"]):
            set_current_page_step("final_results")
        else:
            set_current_page_step("handoff_to_next_player")

    def restart_full_game():
        initialize_game_state() # This will call update_main_ui
        
    def set_current_page_step(step_name):
        _game_state_heads_up["current_page_step"] = step_name
        update_main_ui()

    def update_main_ui():
        if not page.client_storage or not _game_state_heads_up: return 
        
        main_content_area.controls.clear()
        current_step = _game_state_heads_up.get("current_page_step", "select_num_players") # Default to setup

        main_content_area.vertical_alignment = ft.MainAxisAlignment.CENTER
        main_content_area.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        if current_step == "select_num_players":
            main_content_area.controls.extend([
                ft.Text("📱 الجوال على الرأس", size=30, weight="bold"),
                ft.Text("عدد اللاعبين:", size=18),
                ft.Row([
                    ft.IconButton(ft.Icons.REMOVE, on_click=lambda e: update_num_players_offline(-1)),
                    ft.Text(str(_game_state_heads_up["num_players"]), size=24),
                    ft.IconButton(ft.Icons.ADD, on_click=lambda e: update_num_players_offline(1)),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.ElevatedButton("التالي", on_click=lambda e: set_current_page_step("input_player_names"), width=150, height=40),
                # Assuming rules are now handled globally, no "back to rules" from here.
                # If a game-specific rules recap is needed, add it back.
                 ft.ElevatedButton("🏠 العودة للقائمة", on_click=cleanup_and_go_home_offline, width=150, height=40)
            ])
        elif current_step == "input_player_names":
            name_inputs_offline = [ft.TextField(label=f"اسم اللاعب {i+1}", width=300, text_align=ft.TextAlign.CENTER) for i in range(_game_state_heads_up["num_players"])]
            main_content_area.controls.append(ft.Text("✏️ أدخل أسماء اللاعبين:", size=24))
            main_content_area.controls.extend(name_inputs_offline)
            def save_player_names_and_proceed(e):
                names = [tf.value.strip() for tf in name_inputs_offline if tf.value.strip()]
                if len(names) != _game_state_heads_up["num_players"] or len(set(names)) != len(names) or any(not n for n in names):
                    page.snack_bar = ft.SnackBar(ft.Text("❗ أسماء اللاعبين يجب أن تكون فريدة وغير فارغة."), open=True)
                    if page.client_storage: page.update()
                    return
                _game_state_heads_up["players_names_list"] = names
                _game_state_heads_up["all_player_scores"] = {name: 0.0 for name in names} 
                _game_state_heads_up["current_player_index"] = 0 
                set_current_page_step("handoff_to_next_player")
            main_content_area.controls.append(ft.ElevatedButton("تأكيد وبدء اللعبة", on_click=save_player_names_and_proceed, width=200, height=50))
            main_content_area.controls.append(ft.ElevatedButton("🔙 رجوع لاختيار العدد", on_click=lambda e: set_current_page_step("select_num_players"), width=200, height=40))

        elif current_step == "handoff_to_next_player":
            player_name = _game_state_heads_up["players_names_list"][_game_state_heads_up["current_player_index"]]
            main_content_area.controls.extend([
                ft.Text(f"📱 أعطِ الجوال إلى: {player_name}", size=26, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Text("تأكد من وضع الجوال بشكل أفقي على الرأس قبل البدء!", size=20, color=ft.Colors.ORANGE_ACCENT_700, text_align=ft.TextAlign.CENTER),
                ft.Text("عندما تكون جاهزاً، اضغط 'ابدأ الجولة'", size=16, text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton("🚀 ابدأ الجولة", on_click=lambda e: start_player_round(), width=200, height=60)
            ])

        elif current_step == "playing_round_active":
            main_content_area.alignment = ft.MainAxisAlignment.SPACE_EVENLY 
            main_content_area.controls.extend([
                timer_text_control,
                word_text_control, 
                score_text_control,
                ft.Row([
                    ft.ElevatedButton("✅ صحيح", on_click=handle_correct_guess, width=150, height=70, bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE),
                    ft.ElevatedButton("⏭️ تخطي", on_click=handle_skip_action, width=150, height=70, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE) 
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.ElevatedButton("⏹️ إنهاء الجولة مبكراً", on_click=lambda e: handle_round_end(None), width=250, height=40, bgcolor=ft.Colors.AMBER_ACCENT_100)
            ])

        elif current_step == "round_summary":
            player_name = _game_state_heads_up["players_names_list"][_game_state_heads_up["current_player_index"]]
            round_score = _game_state_heads_up["current_round_score"]
            total_score = _game_state_heads_up["all_player_scores"].get(player_name, 0.0)
            
            word_log_display = ft.Column(scroll=ft.ScrollMode.AUTO, height=150, spacing=2, width=300, alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            word_log_display.controls.append(ft.Text("الكلمات في هذه الجولة:", weight="bold", text_align=ft.TextAlign.CENTER))
            
            round_words = _game_state_heads_up.get("current_round_word_log", [])
            if not round_words:
                word_log_display.controls.append(ft.Text("لم يتم لعب كلمات.", italic=True, text_align=ft.TextAlign.CENTER))
            else:
                for item in round_words:
                    status_symbol = "✅" if item["status"] == "correct" else "⏭️"
                    color = ft.Colors.GREEN_700 if item["status"] == "correct" else ft.Colors.RED_700
                    word_log_display.controls.append(ft.Text(f"{status_symbol} {item['word']}", color=color, text_align=ft.TextAlign.CENTER))

            main_content_area.controls.extend([
                ft.Text(f"⏰ انتهى دور اللاعب: {player_name}", size=24, weight="bold"),
                ft.Text(f"النقاط في هذه الجولة: {round_score}", size=22),
                ft.Text(f"إجمالي نقاط {player_name}: {total_score}", size=18),
                ft.Divider(height=10),
                word_log_display, 
                ft.Divider(height=10),
                ft.ElevatedButton("▶ اللاعب التالي / عرض النتائج", on_click=lambda e: proceed_from_summary(), width=250, height=50)
            ])

        elif current_step == "final_results":
            main_content_area.controls.append(ft.Text("🏁 انتهت اللعبة!", size=28, weight="bold"))
            main_content_area.controls.append(ft.Text("📊 النتائج النهائية:", size=22))
            
            sorted_scores = sorted(_game_state_heads_up.get("all_player_scores", {}).items(), key=lambda x: x[1], reverse=True)
            for name, final_score in sorted_scores:
                main_content_area.controls.append(ft.Text(f"{name}: {final_score} نقطة", size=20))
            
            main_content_area.controls.extend([
                ft.Row([
                    ft.ElevatedButton("🔁 العب مرة أخرى", on_click=lambda e: restart_full_game(), width=180, height=50),
                    ft.ElevatedButton("🏠 القائمة الرئيسية", on_click=cleanup_and_go_home_offline, width=180, height=50)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
            ])
        
        if page.client_storage: page.update()

    def update_num_players_offline(delta):
        _game_state_heads_up["num_players"] = max(2, min(10, _game_state_heads_up["num_players"] + delta))
        update_main_ui()

    initialize_game_state() # This now calls update_main_ui()
    
    return [ft.Container(content=main_content_area, expand=True, alignment=ft.alignment.center, padding=10)]


# --- GAME ENTRY POINT (Called by app.py) ---
def heads_up_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    # Heads Up is offline only
    if is_online: # This case should ideally be prevented by app.py routing
        return [
            ft.Container(
                content=ft.Column([
                    ft.Text("لعبة 'الجوال على الرأس' متاحة فقط في وضع الأوفلاين حالياً.", size=20, text_align=ft.TextAlign.CENTER),
                    ft.ElevatedButton("🔙 العودة للقائمة", on_click=lambda e: go_home_fn(), width=200, height=40)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, vertical_alignment=ft.MainAxisAlignment.CENTER, expand=True),
                expand=True, alignment=ft.alignment.center
            )
        ]
    else:
        return heads_up_game_offline_logic(page, go_home_fn)