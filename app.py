# app.py
import flet as ft
import os
import random # Already present, used by online_helpers
import string   # Already present, used by online_helpers
import time     # Already present, used by online_helpers and potentially game logic
# import importlib # Not actively used in the provided snippet, can be removed if not needed elsewhere

# Game UI imports
from bara_alsalfa_game import bara_alsalfa_game_entry
from bedoon_kalam_game import bedoon_kalam_game_entry
from heads_up_game import heads_up_game_entry
from mafia_game import mafia_game_entry
from min_fina_game import min_fina_game_entry
from taboo_game import taboo_game_entry
from trivia_battle_game import trivia_battle_game_entry
from sudoku_game import sudoku_game_entry # <-- ADDED FOR SUDOKU

# Server-side action processors
from server_actions.bara_alsalfa_actions import process_bara_alsalfa_action
from server_actions.bedoon_kalam_actions import process_bedoon_kalam_action
from server_actions.min_fina_actions import process_min_fina_action
from server_actions.taboo_actions import process_taboo_action
from server_actions.trivia_battle_actions import process_trivia_battle_action
from server_actions.sudoku_actions import process_sudoku_action # <-- ADDED FOR SUDOKU

# Helpers
from online_helpers import generate_room_code, start_server_timer # Ensure start_server_timer is used or remove if not

GAME_ROOMS = {}
ONLINE_PLAYER_SESSIONS = {}

# --- MAFIA SERVER-SIDE ACTION PROCESSING (Placeholder - Offline Only) ---
def process_mafia_action_placeholder(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    print(f"Mafia action received (Note: Mafia is offline only): {action_type} by {player_name}")
    # This function is a placeholder as Mafia is offline. No actual server processing.
    pass

# --- GENERIC ACTION PROCESSOR ---
def process_game_action(page_ref: ft.Page, room_code: str, player_name: str, game_type: str, action_type: str, payload: dict):
    print(f"Server processing: Game: {game_type}, Room: {room_code}, Player: {player_name}, Action: {action_type}, Payload: {payload}")
    
    if room_code not in GAME_ROOMS:
        print(f"Error: Room {room_code} does not exist for action {action_type} by {player_name}.")
        if page_ref.client_storage: # Check if client is still connected
            page_ref.snack_bar = ft.SnackBar(ft.Text(f"خطأ: الغرفة {room_code} غير موجودة."), open=True)
            page_ref.update()
        return

    # Ensure game_state exists
    if "game_state" not in GAME_ROOMS[room_code]:
        print(f"Error: game_state missing for room {room_code}. Action {action_type} by {player_name} cannot be processed.")
        if page_ref.client_storage:
            page_ref.snack_bar = ft.SnackBar(ft.Text(f"خطأ داخلي في الغرفة {room_code}."), open=True)
            page_ref.update()
        return
        
    if game_type == "bara_alsalfa":
        process_bara_alsalfa_action(page_ref, room_code, player_name, action_type, payload, GAME_ROOMS)
    elif game_type == "bedoon_kalam":
        process_bedoon_kalam_action(page_ref, room_code, player_name, action_type, payload, GAME_ROOMS)
    elif game_type == "mafia": # Though offline, the dispatcher might still call it if a UI element mistakenly sends an action
        process_mafia_action_placeholder(page_ref, room_code, player_name, action_type, payload, GAME_ROOMS)
    elif game_type == "min_fina": 
        process_min_fina_action(page_ref, room_code, player_name, action_type, payload, GAME_ROOMS)
    elif game_type == "taboo": 
        process_taboo_action(page_ref, room_code, player_name, action_type, payload, GAME_ROOMS)
    elif game_type == "trivia_battle": 
        process_trivia_battle_action(page_ref, room_code, player_name, action_type, payload, GAME_ROOMS)
    elif game_type == "sudoku": # <-- ADDED FOR SUDOKU
        process_sudoku_action(page_ref, room_code, player_name, action_type, payload, GAME_ROOMS)
    else:
        print(f"Error: No action handler for game_type '{game_type}'")


# --- FLET APP MAIN FUNCTION (Routing and Views) ---
def main(page: ft.Page):
    page.title = "🎉 ألعابنا"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT 
    page.scroll = ft.ScrollMode.ADAPTIVE

    def go_home(e=None):
        if page.session_id in ONLINE_PLAYER_SESSIONS:
            details = ONLINE_PLAYER_SESSIONS.pop(page.session_id)
            rc = details["room_code"]
            pn = details["player_name"]

            if rc in GAME_ROOMS:
                room_data = GAME_ROOMS[rc]
                gs = room_data.get("game_state", {}) 

                if pn in room_data["players"]:
                    is_leaving_player_host = room_data["players"][pn].get("is_host", False)
                    del room_data["players"][pn]
                    print(f"Player {pn} removed from room {rc}.")

                    if not room_data["players"]: 
                        # If a timer was active for this room, ensure it's stopped.
                        # This requires the timer event to be stored in room_data.
                        # Example for games that use start_server_timer:
                        timer_event = room_data.get("active_timer_event") 
                        if timer_event and isinstance(timer_event, ft.threading.Event) and not timer_event.is_set():
                            timer_event.set()
                            print(f"Room {rc}: Timer event set as room is being deleted due to no players.")

                        del GAME_ROOMS[rc]
                        print(f"Room {rc} is empty and has been deleted.")
                    else: 
                        if is_leaving_player_host:
                            new_host_name = list(room_data["players"].keys())[0] # Assign to the next player
                            room_data["players"][new_host_name]["is_host"] = True
                            room_data["host_id"] = new_host_name # Update host_id in room_data
                            if gs: gs["status_message"] = f"الهوست ({pn}) غادر. الهوست الجديد هو {new_host_name}."
                            print(f"Host {pn} left room {rc}. New host is {new_host_name}.")
                        else:
                            if gs: gs["status_message"] = f"اللاعب {pn} غادر الغرفة."
                        
                        if page.client_storage: # Ensure client is still connected before pubsub
                             page.pubsub.send_all_on_topic(
                                 f"room_{rc}",
                                 {"type": "PLAYER_LEFT", "player_name": pn, "room_state": room_data}
                             )
            else:
                print(f"Player {pn} was in session for room {rc}, but room no longer exists.")
        
        page.go("/")


    available_games = [
        ("برة السالفة", "bara_alsalfa"),
        ("بدون كلام 🤫", "bedoon_kalam"), 
        ("📱 الجوال على الرأس (أوفلاين فقط)", "heads_up"),
        ("🕵️‍♂️ المافيا (أوفلاين فقط)", "mafia"), 
        ("👀 من فينا؟", "min_fina"),          
        ("🚫 تابو", "taboo"),                     
        ("🧠 تريفيا باتل", "trivia_battle"),
        ("🧩 سودوكو", "sudoku"), # <-- ADDED FOR SUDOKU
    ]

    def view_home_page():
         print("--- Building Home Page View ---")
         return ft.View(
             "/",
             [
                 ft.Text("🎮 أهلاً بك في ألعابنا!", size=32, weight="bold", text_align="center"),
                 ft.Text("اختر اللعبة:", size=20, text_align="center"),
                 ft.Column(
                     [ft.ElevatedButton(text, on_click=lambda e, gt=game_type_val: page.go(f"/rules/{gt}"), width=250, height=50) 
                      for text, game_type_val in available_games],
                     alignment=ft.MainAxisAlignment.CENTER,
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                     spacing=10
                 )
             ],
             vertical_alignment=ft.MainAxisAlignment.CENTER,
             horizontal_alignment=ft.CrossAxisAlignment.CENTER,
             spacing=20,
             scroll=ft.ScrollMode.AUTO
         )

    def view_rules_page(game_type: str):
         print(f"--- Building Rules Page View for {game_type} ---")
         rules_content = []
         game_display_name = "لعبة" 
         
         # Find game display name from available_games list
         for name, g_type_val in available_games:
             if g_type_val == game_type:
                 game_display_name = name
                 break
         
         if game_type == "bara_alsalfa":
             rules_content.extend([
                 ft.Text("📜 قوانين لعبة برا السالفة", size=28, weight="bold"),
                 ft.Text("👥 عدد اللاعبين (أونلاين): 3-15", size=18),
                 ft.Text("🎯 فكرة اللعبة: أحد اللاعبين لا يعرف الكلمة (برة السالفة)، بينما البقية يعرفونها.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🕹 كيفية اللعب: اللاعبون يتبادلون الأسئلة لمحاولة كشف من هو برة السالفة، ثم يصوتون عليه. بعد التصويت، يحاول اللاعب المشتبه به تخمين الكلمة السرية.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🏁 النتيجة: نقاط تُمنح لمن يخمن برة السالفة بشكل صحيح (+5)، و+10 نقاط إذا خمن برة السالفة الكلمة. إذا لم يتم كشف 'برة السالفة'، يحصل على نقاط إضافية.", size=16, text_align=ft.TextAlign.CENTER),
             ])
         elif game_type == "bedoon_kalam":
             rules_content.extend([
                 ft.Text("📜 قوانين لعبة بدون كلام", size=28, weight="bold"),
                 ft.Text("👥 عدد الفرق: فريقان (يتم توزيع اللاعبين بينهما)", size=18),
                 ft.Text("🎯 فكرة اللعبة: كل فريق يحاول تمثيل الكلمة بدون كلام ليخمنها أعضاء فريقه.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🕹️ كيفية اللعب: لكل فريق دور للتمثيل لمدة 90 ثانية. كل إجابة صحيحة = +2 نقاط، وكل تخطي = -0.5 نقطة.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🏁 النتيجة: اللعبة تتكون من 3 جولات لكل فريق. الفريق الذي يحقق أعلى مجموع نقاط يفوز.", size=16, text_align=ft.TextAlign.CENTER),
             ])
         elif game_type == "heads_up": 
             rules_content.extend([
                 ft.Text("📜 قوانين لعبة الجوال على الرأس", size=28, weight="bold"),
                 ft.Text("👥 عدد اللاعبين: 2-10 (أوفلاين فقط)", size=18),
                 ft.Text("🎯 فكرة اللعبة: كل لاعب يضع الجوال على رأسه، ويحاول تخمين الكلمة الظاهرة بناءً على تلميحات الآخرين.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🕹️ كيفية اللعب: كل لاعب يلعب جولة واحدة مدتها 60 ثانية. مرر الجهاز للأعلى إذا خمنت الكلمة (أو اضغط ✅)، وللأسفل لتخطيها (أو اضغط ⏭️).", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🏁 النتائج: بعد أن يلعب الجميع، تُعرض النقاط ويُعلن الفائز.", size=16, text_align=ft.TextAlign.CENTER),
             ])
         elif game_type == "mafia": 
             rules_content.extend([
                 ft.Text("📜 قوانين لعبة المافيا (أوفلاين فقط)", size=28, weight="bold"), 
                 ft.Text("🎯 الهدف: إذا كنت مدنيًا، اكتشف المافيا. إذا كنت مافيا، اقضِ على المدنيين.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("👥 عدد اللاعبين: 5-15.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🧠 الأدوار: مافيا، طبيب، محقق، مواطن.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🌙 الليل: المافيا تقتل، الطبيب ينقذ، المحقق يتحقق.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("☀️ النهار: نقاش وتصويت لطرد لاعب.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🏆 الفوز: للمدنيين بطرد كل المافيا، وللمافيا عندما يتساوى عددهم مع المدنيين أو يزيد.", size=16, text_align=ft.TextAlign.CENTER),
             ])
         elif game_type == "min_fina": 
             rules_content.extend([
                 ft.Text("📜 قوانين لعبة: من فينا؟ 👀", size=28, weight="bold"),
                 ft.Text("👥 عدد اللاعبين: 3-12 (أونلاين).", size=18),
                 ft.Text("🎯 فكرة اللعبة: سؤال \"من فينا...؟\" والتصويت بسرية على اللاعب الذي ينطبق عليه السؤال.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🔁 الجولات: الهوست يبدأ سؤال جديد، ويمكنه تخطي السؤال مرتين. الجميع يصوت. ثم تعرض النتائج.", size=16, text_align=ft.TextAlign.CENTER),
             ])
         elif game_type == "taboo": 
             rules_content.extend([
                 ft.Text("📜 قوانين لعبة تابو", size=28, weight="bold"),
                 ft.Text("👥 عدد الفرق: فريقان (في الوضع الأونلاين، الهوست يشكل الفرق).", size=18),
                 ft.Text("🎯 فكرة اللعبة: الفريق يحاول جعل العضو الممثل يخمن الكلمة السرية دون استخدام الكلمات الممنوعة.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🕹️ كيفية اللعب: كل فريق يلعب لمدة 60 ثانية. +1 للإجابة الصحيحة، -0.5 للتخطي/الكلمة الممنوعة.", size=16, text_align=ft.TextAlign.CENTER),
                 ft.Text("🏁 النتيجة: 3 جولات لكل فريق. الأعلى نقاطاً يفوز.", size=16, text_align=ft.TextAlign.CENTER),
             ])
         elif game_type == "trivia_battle": 
             rules_content.extend([
                ft.Text("📜 قوانين تريفيا باتل", size=28, weight="bold"),
                ft.Text("👥 عدد اللاعبين: 2-6 لاعبين.", size=18), 
                ft.Text("🎯 فكرة اللعبة: مسابقة معلومات فردية بين اللاعبين.", size=16, text_align=ft.TextAlign.CENTER), 
                ft.Text("🕹️ كيفية اللعب: الهوست يختار فئة الأسئلة. كل لاعب يتناوب للإجابة على 10 أسئلة. نقطة لكل إجابة صحيحة.", size=16, text_align=ft.TextAlign.CENTER), 
                ft.Text("🏁 النتيجة: اللاعب صاحب أعلى مجموع نقاط يفوز بعد انتهاء جميع الأسئلة.", size=16, text_align=ft.TextAlign.CENTER), 
            ])
         elif game_type == "sudoku": # <-- ADDED FOR SUDOKU
            rules_content.extend([
                ft.Text("📜 قوانين لعبة سودوكو", size=28, weight="bold"),
                ft.Text("👥 عدد اللاعبين (أوفلاين): لاعب واحد في كل مرة", size=18),
                ft.Text("👥 عدد اللاعبين (أونلاين): عدة لاعبين، والفوز لمن ينهي اللغز أولًا بشكل صحيح", size=18),
                ft.Text("🎯 فكرة اللعبة: يجب ملء شبكة مكونة من 9 صفوف و9 أعمدة بالأرقام من 1 إلى 9، بحيث لا يتكرر أي رقم في نفس الصف الأفقي، أو العمود العمودي، أو داخل أي مربع فرعي (3×3).", size=16, text_align=ft.TextAlign.CENTER),
                ft.Text("🕹 كيفية اللعب (أوفلاين): اختر مستوى الصعوبة، واستخدم لوحة الأرقام لإكمال الخانات الفارغة. عند الانتهاء، اضغط على 'تحقق من الحل' لمعرفة الخلايا الصحيحة والخاطئة.", size=16, text_align=ft.TextAlign.CENTER),
                ft.Text("💻 كيفية اللعب (أونلاين): يبدأ المضيف اللعبة، ويتلقى جميع اللاعبين نفس اللغز. من يتمكن من إرسال حل صحيح أولًا يُعلن فائزًا. المحاولات الخاطئة تظهر فقط لصاحبها.", size=16, text_align=ft.TextAlign.CENTER),
            ])
         else:
             # Fallback if game_type isn't matched above, uses game_display_name found earlier
             rules_content.append(ft.Text(f"قوانين لعبة {game_display_name} غير محددة بعد."))

         rules_content.append(ft.ElevatedButton(f"▶ المتابعة إلى اختيار وضع اللعب لـ {game_display_name}", 
                                                 on_click=lambda e, gt=game_type: page.go(f"/select_mode/{gt}"), 
                                                 width=350, height=50))
         
         rules_content.append(ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home, width=200, height=40))

         return ft.View(
             f"/rules/{game_type}",
             controls=rules_content,
             vertical_alignment=ft.MainAxisAlignment.CENTER,
             horizontal_alignment=ft.CrossAxisAlignment.CENTER,
             spacing=15,
             scroll=ft.ScrollMode.AUTO,
             padding=20
         )

    def view_select_mode_page(game_type: str):
         print(f"--- Building Select Mode Page View for {game_type} ---")
         game_display_name = next((text for text, val in available_games if val == game_type), game_type.replace("_", " ").title())
         # Sudoku is online capable, so "heads_up", "mafia" are the only offline-only games.
         is_online_capable = not (game_type in ["heads_up", "mafia"])
         local_player_name_input = ft.TextField(label="اسمك (للعب أونلاين)", width=300, text_align=ft.TextAlign.CENTER, visible=is_online_capable)

         def attempt_go_to_online_options(e):
             p_name = local_player_name_input.value.strip()
             if not p_name:
                 page.snack_bar = ft.SnackBar(ft.Text("الرجاء إدخال اسمك للعب أونلاين!"), open=True)
                 if page.client_storage: page.update()
                 return
             page.go(f"/online_options/{game_type}/{p_name}")
         
         online_button_text = "🌐 لعب أونلاين (عدة أجهزة)"
         if not is_online_capable: online_button_text = "🌐 لعب أونلاين (غير متاح لهذه اللعبة)"

         return ft.View(
             f"/select_mode/{game_type}",
             [
                 ft.Text(f"اختر وضع اللعب لـ: {game_display_name}", size=24, weight="bold"),
                 ft.ElevatedButton("📱 لعب أوفلاين (جهاز واحد)", on_click=lambda e: page.go(f"/game/{game_type}/offline"), width=300, height=60),
                 ft.Divider(height=10, visible=is_online_capable),
                 ft.Text("للعب أونلاين، أدخل اسمك:", size=16, visible=is_online_capable),
                 local_player_name_input, 
                 ft.ElevatedButton(online_button_text, on_click=attempt_go_to_online_options if is_online_capable else None, width=300, height=60, disabled=not is_online_capable),
                 ft.ElevatedButton("🔙 رجوع للقوانين", on_click=lambda e, gt=game_type: page.go(f"/rules/{gt}"), width=200),
                 ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home, width=200)
             ],
             vertical_alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15
         )

    def view_online_options_page(game_type: str, current_player_name_from_route: str):
         print(f"--- Building Online Options Page View for {game_type} ---")
         game_display_name = next((text for text, val in available_games if val == game_type), game_type.replace("_", " ").title())
         room_code_input = ft.TextField(label="أدخل كود الغرفة", width=250, text_align=ft.TextAlign.CENTER, capitalization=ft.TextCapitalization.CHARACTERS)
         p_name_for_session = current_player_name_from_route 

         def create_room_click(e):
            new_code = generate_room_code()
            while new_code in GAME_ROOMS: new_code = generate_room_code()

            initial_gs = {"phase": "LOBBY", "status_message": "في انتظار اللاعبين..."}
            # Common initial setup for all games
            GAME_ROOMS[new_code] = {
                "game_type": game_type,
                "players": {p_name_for_session: {"name": p_name_for_session, "page_id": page.session_id, "is_host": True}},
                "host_id": p_name_for_session, # Store host name directly for easier access
                "game_state": initial_gs,
                "active_timer_event": None # Placeholder for games that use timers
            }
            
            # Game-specific initial_gs modifications
            if game_type == "bara_alsalfa":
                 initial_gs["status_message"] = "في انتظار اللاعبين... الهوست يمكنه اختيار القائمة وبدء اللعبة."
                 initial_gs["global_scores"] = {p_name_for_session: 0.0} 
                 initial_gs["used_words"] = [] 
                 initial_gs["min_players_for_game"] = 3 
            elif game_type == "bedoon_kalam": 
                 initial_gs["status_message"] = "في انتظار اللاعبين... الهوست سيقوم بإعداد الفرق."
                 initial_gs["teams"] = {} 
                 initial_gs["used_words"] = []
                 initial_gs["max_game_rounds"] = 3 
                 initial_gs["round_duration_seconds"] = 90
                 initial_gs["min_players_for_game"] = 2 
            elif game_type == "min_fina": 
                initial_gs["status_message"] = "في انتظار اللاعبين... الهوست يمكنه تحديد العدد وبدء اللعبة."
                initial_gs["min_players_for_game"] = 3 
                initial_gs["num_players_setting"] = 3 
                initial_gs["used_questions"] = []
                initial_gs["initial_skip_chances"] = 2 
                initial_gs["skip_chances_left"] = 2
            elif game_type == "taboo": 
                initial_gs["status_message"] = "في انتظار اللاعبين... الهوست سيقوم بإعداد الفرق (فريقان)."
                initial_gs["teams_online"] = {} # Or just "teams" if consistent with Bedoon Kalam
                initial_gs["used_words_secrets"] = []
                initial_gs["max_rounds"] = 3 
                initial_gs["round_duration"] = 60 
                initial_gs["min_players_for_game"] = 2 
            elif game_type == "trivia_battle": 
                initial_gs["status_message"] = "في انتظار اللاعبين... الهوست يختار الفئة عند اكتمال العدد." 
                initial_gs["players_scores_online"] = {} 
                initial_gs["questions_per_player"] = 10 
                initial_gs["min_players_for_game"] = 2  
                initial_gs["max_players_for_game"] = 6  
                initial_gs["question_pool_online"] = []
            elif game_type == "sudoku": # <-- ADDED FOR SUDOKU
                initial_gs["status_message"] = "في انتظار الهوست لبدء لعبة سودوكو."
                initial_gs["puzzle_board"] = None # Server generates this on "SETUP_SUDOKU_GAME"
                initial_gs["solution_board"] = None
                initial_gs["difficulty"] = "normal" # Host can choose before starting
                initial_gs["winner"] = None
                initial_gs["min_players_for_game"] = 1 # Can be 1+ for online

            ONLINE_PLAYER_SESSIONS[page.session_id] = {"room_code": new_code, "player_name": p_name_for_session}
            print(f"Room {new_code} created by {p_name_for_session} for {game_type}.")
            page.go(f"/game/{game_type}/online/{new_code}/{p_name_for_session}")


         def join_room_click(e):
             code_to_join = room_code_input.value.strip().upper()
             if not code_to_join:
                 page.snack_bar = ft.SnackBar(ft.Text("الرجاء إدخال كود الغرفة!"), open=True)
                 if page.client_storage: page.update()
                 return

             if code_to_join in GAME_ROOMS:
                 room = GAME_ROOMS[code_to_join]
                 room_gs = room.get("game_state", {})

                 if room["game_type"] != game_type:
                     page.snack_bar = ft.SnackBar(ft.Text(f"هذه الغرفة للعبة {room['game_type']}!"), open=True)
                     if page.client_storage: page.update()
                     return
                 if p_name_for_session in room["players"]:
                     page.snack_bar = ft.SnackBar(ft.Text("هذا الاسم مستخدم بالفعل في الغرفة!"), open=True)
                     if page.client_storage: page.update()
                     return

                 game_in_progress = False
                 game_specific_message = f"عذراً، لعبة {game_display_name} قد بدأت بالفعل!"

                 if game_type == "bara_alsalfa" and room_gs.get("phase") not in ["LOBBY", "CATEGORY_SELECTED"]:
                     game_in_progress = True
                 elif game_type == "bedoon_kalam" and room_gs.get("phase") not in ["LOBBY", "TEAMS_SET"]:
                     game_in_progress = True
                 elif game_type == "min_fina" and room_gs.get("phase") not in ["LOBBY", "QUESTION_DISPLAY"]:
                    game_in_progress = True
                 elif game_type == "taboo" and room_gs.get("phase") not in ["LOBBY", "TEAMS_SET_TABOO"]: # Use specific phase for Taboo if different
                     game_in_progress = True
                 elif game_type == "trivia_battle" and room_gs.get("phase") != "LOBBY":
                     game_in_progress = True
                 elif game_type == "sudoku" and room_gs.get("phase") != "LOBBY": # <-- ADDED FOR SUDOKU
                     game_in_progress = True
                 
                 if game_in_progress:
                     page.snack_bar = ft.SnackBar(ft.Text(game_specific_message), open=True)
                     if page.client_storage: page.update()
                     return
                 
                 # Define max players per game type
                 absolute_max_players = 15 # Default max
                 if game_type == "min_fina": absolute_max_players = 12
                 elif game_type == "taboo": absolute_max_players = 10 
                 elif game_type == "trivia_battle": absolute_max_players = 6
                 elif game_type == "sudoku": absolute_max_players = 15 # Sudoku can also have many players competing
                 
                 if len(room["players"]) >= absolute_max_players:
                     page.snack_bar = ft.SnackBar(ft.Text("عذراً، الغرفة ممتلئة بالحد الأقصى للعبة!"), open=True)
                     if page.client_storage: page.update()
                     return

                 room["players"][p_name_for_session] = {"name": p_name_for_session, "page_id": page.session_id, "is_host": False}
                 # Game-specific actions on player join
                 if game_type == "bara_alsalfa" and "global_scores" in room_gs: 
                     room_gs["global_scores"][p_name_for_session] = 0.0
                 elif game_type == "trivia_battle" and "players_scores_online" in room_gs:
                    room_gs["players_scores_online"][p_name_for_session] = 0
                 # No specific action for Sudoku on join, scores/progress are not tracked this way
                 
                 ONLINE_PLAYER_SESSIONS[page.session_id] = {"room_code": code_to_join, "player_name": p_name_for_session}
                 
                 if room_gs: room_gs["status_message"] = f"اللاعب {p_name_for_session} انضم إلى الغرفة!"
                 page.pubsub.send_all_on_topic(
                     f"room_{code_to_join}",
                     {"type": "PLAYER_JOINED", "player_name": p_name_for_session, "room_state": room}
                 )
                 print(f"Player {p_name_for_session} joined room {code_to_join}. Sent PLAYER_JOINED update.")
                 page.go(f"/game/{game_type}/online/{code_to_join}/{p_name_for_session}")
             else:
                 page.snack_bar = ft.SnackBar(ft.Text("كود الغرفة غير صحيح!"), open=True)
                 if page.client_storage: page.update()

         return ft.View(f"/online_options/{game_type}/{current_player_name_from_route}", 
             [
                 ft.Text(f"مرحباً {current_player_name_from_route}!", size=18, weight="bold"),
                 ft.Text(f"خيارات اللعب أونلاين لـ: {game_display_name}", size=22, weight="bold"),
                 ft.ElevatedButton("🚪 إنشاء غرفة جديدة", on_click=create_room_click, width=250, height=50),
                 ft.Divider(),
                 room_code_input,
                 ft.ElevatedButton("🔗 الانضمام لغرفة", on_click=join_room_click, width=250, height=50),
                 ft.ElevatedButton("🔙 رجوع لاختيار الوضع", on_click=lambda e, gt=game_type: page.go(f"/select_mode/{gt}"), width=200)
             ],
             vertical_alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15
         )

    def view_game_launcher(game_type: str, mode: str, room_code: str = None, p_name: str = None):
         print(f"--- Building Game Launcher View for {game_type}, Mode: {mode} ---")
         game_controls = []
         is_online = (mode == "online")

         if is_online: 
             if not p_name or not room_code: 
                 print(f"Game launcher error: Online mode but missing p_name ({p_name}) or room_code ({room_code}).")
                 go_home() # Redirect to home if essential online data is missing
                 return ft.View(page.route, [ft.Text("خطأ في بيانات الغرفة أو اللاعب.")]) # Show error view

             if page.session_id not in ONLINE_PLAYER_SESSIONS:
                 # Attempt to re-establish session if player is still in room data (e.g., page refresh)
                 if room_code in GAME_ROOMS and GAME_ROOMS[room_code]["players"].get(p_name):
                     ONLINE_PLAYER_SESSIONS[page.session_id] = {"room_code": room_code, "player_name": p_name}
                     GAME_ROOMS[room_code]["players"][p_name]["page_id"] = page.session_id # Update page_id
                     print(f"Re-established session for {p_name} in room {room_code} on page load.")
                 else:
                     print(f"Session {page.session_id} for {p_name} in {room_code} is invalid. Room/player missing or player was removed. Redirecting home.")
                     go_home()
                     return ft.View(page.route, [ft.Text("انتهت الغرفة أو الجلسة غير صالحة.")])

         if game_type == "bara_alsalfa":
             game_controls = bara_alsalfa_game_entry(page, go_home, process_game_action, is_online, room_code, p_name, GAME_ROOMS)
         elif game_type == "bedoon_kalam": 
             game_controls = bedoon_kalam_game_entry(page, go_home, process_game_action, is_online, room_code, p_name, GAME_ROOMS)
         elif game_type == "heads_up": 
             # Heads Up is offline only, process_action_fn is None
             game_controls = heads_up_game_entry(page, go_home, None, False, None, None, None) 
         elif game_type == "mafia": 
             # Mafia is offline only, process_action_fn is None
             game_controls = mafia_game_entry(page, go_home, None, False, None, None, None) 
         elif game_type == "min_fina": 
             game_controls = min_fina_game_entry(page, go_home, process_game_action, is_online, room_code, p_name, GAME_ROOMS)
         elif game_type == "taboo": 
             game_controls = taboo_game_entry(page, go_home, process_game_action, is_online, room_code, p_name, GAME_ROOMS)
         elif game_type == "trivia_battle": 
             game_controls = trivia_battle_game_entry(page, go_home, process_game_action, is_online, room_code, p_name, GAME_ROOMS)
         elif game_type == "sudoku": # <-- ADDED FOR SUDOKU
             game_controls = sudoku_game_entry(page, go_home, process_game_action, is_online, room_code, p_name, GAME_ROOMS)
         else:
             game_controls = [ft.Text(f"لعبة '{game_type}' غير مدعومة حاليًا أو في وضع '{mode}'.")]
             
         return ft.View(
             page.route, # Use the current route for the view's route attribute
             game_controls, 
             scroll=ft.ScrollMode.ADAPTIVE, 
             vertical_alignment=ft.MainAxisAlignment.START, # Ensure game content starts from top
             padding=10 # Consistent padding for game views
         )

    def route_change(e: ft.RouteChangeEvent):
        target_route = e.route
        # Prevent building the same view if it's already the top one (e.g., from internal page.update())
        # This is a simplified check; more complex scenarios might need refinement.
        if page.views and page.views[-1].route == target_route and len(page.views) == 1:
            print(f"Route change to {target_route} is current top view. Skipping rebuild unless forced.")
            # If the view content might have changed due to external factors (like pubsub),
            # an update might still be needed. However, pubsub handlers should ideally call page.update().
            # For direct page.go() to the same route, this helps avoid unnecessary rebuilds.
            if page.client_storage: page.update() # Ensure current view is up-to-date
            return

        print(f"--- ROUTE CHANGE START --- Target Route: {target_route}, Current Top View: {page.views[-1].route if page.views else 'None'}, page.views count: {len(page.views)}")
        
        page.views.clear() # Clear existing views to build the new stack
        print(f"page.views cleared. Now empty.")
        
        route_parts = target_route.strip("/").split("/")
        current_route_base = route_parts[0] if route_parts and route_parts[0] else ""
        print(f"Parsed Route base: '{current_route_base}', Parts: {route_parts}")

        new_view_to_append = None 

        if current_route_base == "":
            print("Action: Routing to Home Page")
            new_view_to_append = view_home_page()
        elif current_route_base == "rules" and len(route_parts) == 2: 
            game_type_for_rules = route_parts[1]
            print(f"Action: Routing to Rules Page for {game_type_for_rules}")
            new_view_to_append = view_rules_page(game_type_for_rules)
        elif current_route_base == "select_mode" and len(route_parts) == 2:
            game_type_for_select_mode = route_parts[1]
            print(f"Action: Routing to Select Mode Page for {game_type_for_select_mode}")
            new_view_to_append = view_select_mode_page(game_type_for_select_mode)
        elif current_route_base == "online_options" and len(route_parts) == 3: 
            game_type_for_online_opt = route_parts[1]
            player_name_for_online_opt = route_parts[2]
            print(f"Action: Routing to Online Options for {game_type_for_online_opt}, Player: {player_name_for_online_opt}")
            if game_type_for_online_opt in ["heads_up", "mafia"]: # Redirect offline-only games
                print(f"Redirect: Online options not for offline-only game {game_type_for_online_opt}. Redirecting to select_mode.")
                page.go(f"/select_mode/{game_type_for_online_opt}") # This will trigger another route_change
                return # Exit this route_change handler
            new_view_to_append = view_online_options_page(game_type_for_online_opt, player_name_for_online_opt)
        elif current_route_base == "game" and len(route_parts) >= 3:
            game_type = route_parts[1]
            mode = route_parts[2]
            room_code_from_route = route_parts[3] if mode == "online" and len(route_parts) > 3 else None
            p_name_from_route = route_parts[4] if mode == "online" and len(route_parts) > 4 else None
            print(f"Action: Routing to Game Launcher for {game_type}, Mode: {mode}, Room: {room_code_from_route}, Player: {p_name_from_route}")
            if mode == "online" and game_type in ["heads_up", "mafia"]: # Redirect offline-only games
                print(f"Redirect: Online game mode not for offline-only game {game_type}. Redirecting to offline mode.")
                page.go(f"/game/{game_type}/offline") # This will trigger another route_change
                return # Exit this route_change handler
            new_view_to_append = view_game_launcher(game_type, mode, room_code_from_route, p_name_from_route)
        else:
            print(f"Action: Routing to Home Page (Fallback for unknown route: {target_route})")
            new_view_to_append = view_home_page()

        if new_view_to_append:
            page.views.append(new_view_to_append)
            print(f"View appended: {new_view_to_append.route}. page.views count after append: {len(page.views)}")
        else:
            # This case should be rare if all routes are handled or fall back to home.
            # If a view function returns None unexpectedly, this could be hit.
            print(f"CRITICAL Error: No view was created for route {target_route}. Appending home page as fallback.")
            page.views.append(view_home_page()) # Ensure a view is always appended

        if page.client_storage:
            print("Calling page.update()")
            page.update()
            print("page.update() finished.")
        else:
            print("page.client_storage is None (e.g., server-side context or disconnected client), skipping page.update().")
        print(f"--- ROUTE CHANGE END --- New top view: {page.views[-1].route if page.views else 'EMPTY'}, page.route is now: {page.route}")


    def view_pop(e: ft.ViewPopEvent):
        current_view_route_being_popped = e.view.route if e.view else "N/A"
        print(f"--- VIEW POP START --- Popping: '{current_view_route_being_popped}'. page.views count BEFORE Flet's internal pop: {len(page.views)}")

        # Special handling for leaving an online game view via back button/gesture
        if e.view and e.view.route and e.view.route.startswith("/game/") and "/online/" in e.view.route:
            print(f"Online game view pop detected for route: {e.view.route}. Triggering go_home to clean up session.")
            go_home() # This will handle player removal, session cleanup, and navigate to "/"
                      # go_home itself calls page.go("/"), which will trigger route_change.
            print(f"--- VIEW POP END (after go_home for online game) ---")
            return # Prevent Flet's default pop mechanism since go_home handles navigation

        # For all other views, let Flet's default pop mechanism proceed.
        # Flet will pop the view from page.views and then call on_route_change
        # with the route of the new page.views[-1].
        # Our on_route_change will then build the correct view.
        # No need to manually call page.go() here for standard pops.
        page.views.pop()
        if len(page.views) > 0:
            top_view = page.views[-1]
            page.go(top_view.route) # This triggers route_change to build the previous view
        else:
            page.go("/") # If stack is empty, go home

        print(f"Standard pop for '{current_view_route_being_popped}'. page.views count AFTER pop: {len(page.views)}")
        print(f"--- VIEW POP END (default Flet handling or explicit navigation) ---")


    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route) # Initial route loading

ft.app(
    target=main, 
    assets_dir="assets", # Create this folder in your project root if you have assets (images, fonts)
    port=int(os.environ.get("PORT", 8550)), # Standard port, adjustable
    view=ft.WEB_BROWSER # Or ft.FLET_APP for desktop packaging
    # Consider adding other ft.app parameters as needed, e.g., web_renderer
)