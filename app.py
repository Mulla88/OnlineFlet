# app.py
import flet as ft
import os
import random # Already present, used by online_helpers
import string   # Already present, used by online_helpers
import time     # Already present, used by online_helpers and potentially game logic
import threading # Required for Timer Event in go_home

# Game UI imports
from bara_alsalfa_game import bara_alsalfa_game_entry
from bedoon_kalam_game import bedoon_kalam_game_entry
from heads_up_game import heads_up_game_entry
from mafia_game import mafia_game_entry
from min_fina_game import min_fina_game_entry
from taboo_game import taboo_game_entry
from trivia_battle_game import trivia_battle_game_entry
from sudoku_game import sudoku_game_entry

# Server-side action processors
from server_actions.bara_alsalfa_actions import process_bara_alsalfa_action
from server_actions.bedoon_kalam_actions import process_bedoon_kalam_action
from server_actions.min_fina_actions import process_min_fina_action
from server_actions.taboo_actions import process_taboo_action
from server_actions.trivia_battle_actions import process_trivia_battle_action
from server_actions.sudoku_actions import process_sudoku_action

# Helpers
from online_helpers import generate_room_code, start_server_timer

GAME_ROOMS = {}
ONLINE_PLAYER_SESSIONS = {}

# --- MAFIA SERVER-SIDE ACTION PROCESSING (Placeholder - Offline Only) ---
def process_mafia_action_placeholder(page_ref: ft.Page, room_code: str, player_name: str, action_type: str, payload: dict, game_rooms_ref: dict):
    print(f"Mafia action received (Note: Mafia is offline only): {action_type} by {player_name}")
    pass

# --- GENERIC ACTION PROCESSOR ---
def process_game_action(page_ref: ft.Page, room_code: str, player_name: str, game_type: str, action_type: str, payload: dict):
    print(f"Server processing: Game: {game_type}, Room: {room_code}, Player: {player_name}, Action: {action_type}, Payload: {payload}")
    
    if room_code not in GAME_ROOMS:
        print(f"Error: Room {room_code} does not exist for action {action_type} by {player_name}.")
        if page_ref.client_storage:
            page_ref.snack_bar = ft.SnackBar(ft.Text(f"خطأ: الغرفة {room_code} غير موجودة."), open=True)
            page_ref.update()
        return

    if "game_state" not in GAME_ROOMS[room_code]:
        print(f"Error: game_state missing for room {room_code}. Action {action_type} by {player_name} cannot be processed.")
        if page_ref.client_storage:
            page_ref.snack_bar = ft.SnackBar(ft.Text(f"خطأ داخلي في الغرفة {room_code}."), open=True)
            page_ref.update()
        return
        
    action_map = {
        "bara_alsalfa": process_bara_alsalfa_action,
        "bedoon_kalam": process_bedoon_kalam_action,
        "mafia": process_mafia_action_placeholder,
        "min_fina": process_min_fina_action,
        "taboo": process_taboo_action,
        "trivia_battle": process_trivia_battle_action,
        "sudoku": process_sudoku_action,
    }
    
    handler = action_map.get(game_type)
    if handler:
        handler(page_ref, room_code, player_name, action_type, payload, GAME_ROOMS)
    else:
        print(f"Error: No action handler for game_type '{game_type}'")


# --- FLET APP MAIN FUNCTION (Routing and Views) ---
def main(page: ft.Page):
    page.title = "🎉 ألعابنا"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT 
    page.scroll = ft.ScrollMode.ADAPTIVE

    # Store the route that route_change is currently processing or has just finished processing
    # This helps view_pop understand the "intended" state if a ghost pop occurs.
    page.data = {"intended_route_before_pop": None}


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
                        timer_event = room_data.get("active_timer_event") 
                        # Ensure timer_event is a threading.Event (or similar) before calling is_set/set
                        if timer_event and hasattr(timer_event, 'is_set') and hasattr(timer_event, 'set') and not timer_event.is_set():
                            timer_event.set()
                            print(f"Room {rc}: Timer event set as room is being deleted due to no players.")

                        del GAME_ROOMS[rc]
                        print(f"Room {rc} is empty and has been deleted.")
                    else: 
                        if is_leaving_player_host:
                            new_host_name = list(room_data["players"].keys())[0] 
                            room_data["players"][new_host_name]["is_host"] = True
                            room_data["host_id"] = new_host_name 
                            if gs: gs["status_message"] = f"الهوست ({pn}) غادر. الهوست الجديد هو {new_host_name}."
                            print(f"Host {pn} left room {rc}. New host is {new_host_name}.")
                        else:
                            if gs: gs["status_message"] = f"اللاعب {pn} غادر الغرفة."
                        
                        if page.client_storage: 
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
        ("🧩 سودوكو", "sudoku"),
    ]

    def view_home_page():
         # print("--- Building Home Page View ---") # Reduced verbosity
         return ft.View(
             "/",
             [
                 ft.Text("🎮 أهلاً بك في ألعابنا!", size=32, weight="bold", text_align="center"),
                 ft.Text("اختر اللعبة:", size=20, text_align="center"),
                 ft.Column(
                     [ft.ElevatedButton(text, on_click=lambda _, gt=game_type_val: page.go(f"/rules/{gt}"), width=250, height=50) 
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
         # print(f"--- Building Rules Page View for {game_type} ---") # Reduced verbosity
         rules_content = []
         game_display_name = "لعبة" 
         
         for name, g_type_val in available_games:
             if g_type_val == game_type:
                 game_display_name = name
                 break
         
         # ... (rest of rules_content definitions as before, no changes needed here) ...
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
         elif game_type == "sudoku":
            rules_content.extend([
                ft.Text("📜 قوانين لعبة سودوكو", size=28, weight="bold"),
                ft.Text("👥 عدد اللاعبين (أوفلاين): لاعب واحد في كل مرة", size=18),
                ft.Text("👥 عدد اللاعبين (أونلاين): عدة لاعبين، والفوز لمن ينهي اللغز أولًا بشكل صحيح", size=18),
                ft.Text("🎯 فكرة اللعبة: يجب ملء شبكة مكونة من 9 صفوف و9 أعمدة بالأرقام من 1 إلى 9، بحيث لا يتكرر أي رقم في نفس الصف الأفقي، أو العمود العمودي، أو داخل أي مربع فرعي (3×3).", size=16, text_align=ft.TextAlign.CENTER),
                ft.Text("🕹 كيفية اللعب (أوفلاين): اختر مستوى الصعوبة، واستخدم لوحة الأرقام لإكمال الخانات الفارغة. عند الانتهاء، اضغط على 'تحقق من الحل' لمعرفة الخلايا الصحيحة والخاطئة.", size=16, text_align=ft.TextAlign.CENTER),
                ft.Text("💻 كيفية اللعب (أونلاين): يبدأ المضيف اللعبة، ويتلقى جميع اللاعبين نفس اللغز. من يتمكن من إرسال حل صحيح أولًا يُعلن فائزًا. المحاولات الخاطئة تظهر فقط لصاحبها.", size=16, text_align=ft.TextAlign.CENTER),
            ])
         else:
             rules_content.append(ft.Text(f"قوانين لعبة {game_display_name} غير محددة بعد."))


         rules_content.append(ft.ElevatedButton(f"▶ المتابعة إلى اختيار وضع اللعب لـ {game_display_name}", 
                                                 on_click=lambda _, gt=game_type: page.go(f"/select_mode/{gt}"), 
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
         # print(f"--- Building Select Mode Page View for {game_type} ---") # Reduced verbosity
         game_display_name = next((text for text, val in available_games if val == game_type), game_type.replace("_", " ").title())
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
                 ft.ElevatedButton("📱 لعب أوفلاين (جهاز واحد)", on_click=lambda _: page.go(f"/game/{game_type}/offline"), width=300, height=60),
                 ft.Divider(height=10, visible=is_online_capable),
                 ft.Text("للعب أونلاين، أدخل اسمك:", size=16, visible=is_online_capable),
                 local_player_name_input, 
                 ft.ElevatedButton(online_button_text, on_click=attempt_go_to_online_options if is_online_capable else None, width=300, height=60, disabled=not is_online_capable),
                 ft.ElevatedButton("🔙 رجوع للقوانين", on_click=lambda _, gt=game_type: page.go(f"/rules/{gt}"), width=200),
                 ft.ElevatedButton("🏠 العودة للقائمة الرئيسية", on_click=go_home, width=200)
             ],
             vertical_alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15
         )

    def view_online_options_page(game_type: str, current_player_name_from_route: str):
         # print(f"--- Building Online Options Page View for {game_type} ---") # Reduced verbosity
         game_display_name = next((text for text, val in available_games if val == game_type), game_type.replace("_", " ").title())
         room_code_input = ft.TextField(label="أدخل كود الغرفة", width=250, text_align=ft.TextAlign.CENTER, capitalization=ft.TextCapitalization.CHARACTERS)
         p_name_for_session = current_player_name_from_route 

         def create_room_click(e):
            new_code = generate_room_code()
            while new_code in GAME_ROOMS: new_code = generate_room_code()

            initial_gs = {"phase": "LOBBY", "status_message": "في انتظار اللاعبين..."}
            GAME_ROOMS[new_code] = {
                "game_type": game_type,
                "players": {p_name_for_session: {"name": p_name_for_session, "page_id": page.session_id, "is_host": True}},
                "host_id": p_name_for_session,
                "game_state": initial_gs,
                "active_timer_event": None # Ensure this is a threading.Event if used with .set()
            }
            
            # ... (rest of initial_gs setup as before) ...
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
                initial_gs["teams_online"] = {}
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
            elif game_type == "sudoku":
                initial_gs["status_message"] = "في انتظار الهوست لبدء لعبة سودوكو."
                initial_gs["puzzle_board"] = None
                initial_gs["solution_board"] = None
                initial_gs["difficulty"] = "normal"
                initial_gs["winner"] = None
                initial_gs["min_players_for_game"] = 1

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

                 # ... (rest of game_in_progress checks as before) ...
                 if game_type == "bara_alsalfa" and room_gs.get("phase") not in ["LOBBY", "CATEGORY_SELECTED"]:
                     game_in_progress = True
                 elif game_type == "bedoon_kalam" and room_gs.get("phase") not in ["LOBBY", "TEAMS_SET"]:
                     game_in_progress = True
                 elif game_type == "min_fina" and room_gs.get("phase") not in ["LOBBY", "QUESTION_DISPLAY"]:
                    game_in_progress = True
                 elif game_type == "taboo" and room_gs.get("phase") not in ["LOBBY", "TEAMS_SET_TABOO"]:
                     game_in_progress = True
                 elif game_type == "trivia_battle" and room_gs.get("phase") != "LOBBY":
                     game_in_progress = True
                 elif game_type == "sudoku" and room_gs.get("phase") != "LOBBY":
                     game_in_progress = True

                 if game_in_progress:
                     page.snack_bar = ft.SnackBar(ft.Text(game_specific_message), open=True)
                     if page.client_storage: page.update()
                     return
                 
                 absolute_max_players = 15
                 if game_type == "min_fina": absolute_max_players = 12
                 elif game_type == "taboo": absolute_max_players = 10 
                 elif game_type == "trivia_battle": absolute_max_players = 6
                 elif game_type == "sudoku": absolute_max_players = 15 # Or whatever limit you want for online Sudoku
                 
                 if len(room["players"]) >= absolute_max_players:
                     page.snack_bar = ft.SnackBar(ft.Text("عذراً، الغرفة ممتلئة بالحد الأقصى للعبة!"), open=True)
                     if page.client_storage: page.update()
                     return

                 room["players"][p_name_for_session] = {"name": p_name_for_session, "page_id": page.session_id, "is_host": False}
                 if game_type == "bara_alsalfa" and "global_scores" in room_gs: 
                     room_gs["global_scores"][p_name_for_session] = 0.0
                 elif game_type == "trivia_battle" and "players_scores_online" in room_gs:
                    room_gs["players_scores_online"][p_name_for_session] = 0
                 
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
                 ft.ElevatedButton("🔙 رجوع لاختيار الوضع", on_click=lambda _, gt=game_type: page.go(f"/select_mode/{gt}"), width=200)
             ],
             vertical_alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15
         )

    def view_game_launcher(game_type: str, mode: str, room_code: str = None, p_name: str = None):
         # print(f"--- Building Game Launcher View for {game_type}, Mode: {mode} ---") # Reduced verbosity
         game_controls = []
         is_online = (mode == "online")

         if is_online: 
             if not p_name or not room_code: 
                 print(f"Game launcher error: Online mode but missing p_name ({p_name}) or room_code ({room_code}).")
                 go_home() # This will trigger route_change
                 return ft.View(page.route if page.route else "/", [ft.Text("خطأ في بيانات الغرفة أو اللاعب.")]) # Return a valid view for current route

             if page.session_id not in ONLINE_PLAYER_SESSIONS:
                 # Attempt to re-establish session ONLY if room and player are still valid
                 if room_code in GAME_ROOMS and GAME_ROOMS[room_code]["players"].get(p_name) and GAME_ROOMS[room_code]["players"][p_name].get("page_id") is None: # Check if page_id was lost
                     ONLINE_PLAYER_SESSIONS[page.session_id] = {"room_code": room_code, "player_name": p_name}
                     GAME_ROOMS[room_code]["players"][p_name]["page_id"] = page.session_id
                     print(f"Re-established session for {p_name} in room {room_code} on page load for game view.")
                 else: # If player not in room, or page_id already set (meaning another client for this player?), or room gone
                     print(f"Session {page.session_id} for {p_name} in {room_code} is invalid or stale. Room/player state inconsistent. Redirecting home.")
                     go_home()
                     return ft.View(page.route if page.route else "/", [ft.Text("انتهت الغرفة أو الجلسة غير صالحة.")])

         # ... (rest of game_controls assignments as before) ...
         game_entry_map = {
            "bara_alsalfa": bara_alsalfa_game_entry,
            "bedoon_kalam": bedoon_kalam_game_entry,
            "heads_up": heads_up_game_entry,
            "mafia": mafia_game_entry,
            "min_fina": min_fina_game_entry,
            "taboo": taboo_game_entry,
            "trivia_battle": trivia_battle_game_entry,
            "sudoku": sudoku_game_entry,
         }
         
         entry_function = game_entry_map.get(game_type)
         if entry_function:
             # Heads Up and Mafia are offline only and don't use process_game_action or GAME_ROOMS
             if game_type in ["heads_up", "mafia"]:
                 game_controls = entry_function(page, go_home, None, False, None, None, None)
             else:
                 game_controls = entry_function(page, go_home, process_game_action, is_online, room_code, p_name, GAME_ROOMS)
         else:
             game_controls = [ft.Text(f"لعبة '{game_type}' غير مدعومة حاليًا أو في وضع '{mode}'.")]

         current_view_route = f"/game/{game_type}/{mode}"
         if is_online:
             current_view_route += f"/{room_code}/{p_name}"
             
         return ft.View(
             current_view_route, # Ensure view route matches the actual navigation route
             game_controls, 
             scroll=ft.ScrollMode.ADAPTIVE, 
             vertical_alignment=ft.MainAxisAlignment.START,
             padding=10
         )

    def route_change(e: ft.RouteChangeEvent):
        target_route = e.route
        page.data["intended_route_before_pop"] = target_route # Store intended route

        # Optimization: If the target route is the same as the current single top view,
        # AND no ghost pop has emptied the stack, then skip full rebuild.
        if page.views and len(page.views) == 1 and page.views[0].route == target_route:
            print(f"--- ROUTE CHANGE (OPTIMIZED) --- Target: {target_route} is current top. Skipping rebuild.")
            if page.client_storage: page.update() # Ensure UI reflects current state
            return

        print(f"--- ROUTE CHANGE START --- Target: {target_route}, Current Top: {page.views[-1].route if page.views else 'None'}, Views: {len(page.views)}")
        
        page.views.clear()
        # print(f"page.views cleared.") # Reduced verbosity
        
        route_parts = target_route.strip("/").split("/")
        current_route_base = route_parts[0] if route_parts and route_parts[0] else ""
        # print(f"Parsed Route base: '{current_route_base}', Parts: {route_parts}") # Reduced verbosity

        new_view_to_append = None 

        if current_route_base == "":
            # print("Action: Routing to Home Page") # Reduced verbosity
            new_view_to_append = view_home_page()
        elif current_route_base == "rules" and len(route_parts) == 2: 
            game_type_for_rules = route_parts[1]
            # print(f"Action: Routing to Rules Page for {game_type_for_rules}") # Reduced verbosity
            new_view_to_append = view_rules_page(game_type_for_rules)
        elif current_route_base == "select_mode" and len(route_parts) == 2:
            game_type_for_select_mode = route_parts[1]
            # print(f"Action: Routing to Select Mode Page for {game_type_for_select_mode}") # Reduced verbosity
            new_view_to_append = view_select_mode_page(game_type_for_select_mode)
        elif current_route_base == "online_options" and len(route_parts) == 3: 
            game_type_for_online_opt = route_parts[1]
            player_name_for_online_opt = route_parts[2]
            # print(f"Action: Routing to Online Options for {game_type_for_online_opt}, Player: {player_name_for_online_opt}") # Reduced verbosity
            if game_type_for_online_opt in ["heads_up", "mafia"]:
                print(f"Redirect: Online options not for offline-only game {game_type_for_online_opt}. Redirecting.")
                page.go(f"/select_mode/{game_type_for_online_opt}")
                return
            new_view_to_append = view_online_options_page(game_type_for_online_opt, player_name_for_online_opt)
        elif current_route_base == "game" and len(route_parts) >= 3:
            game_type = route_parts[1]
            mode = route_parts[2]
            room_code_from_route = route_parts[3] if mode == "online" and len(route_parts) > 3 else None
            p_name_from_route = route_parts[4] if mode == "online" and len(route_parts) > 4 else None
            # print(f"Action: Routing to Game Launcher for {game_type}, Mode: {mode}, Room: {rc}, Player: {pn}") # Reduced verbosity
            if mode == "online" and game_type in ["heads_up", "mafia"]:
                print(f"Redirect: Online game mode not for offline-only game {game_type}. Redirecting.")
                page.go(f"/game/{game_type}/offline")
                return
            new_view_to_append = view_game_launcher(game_type, mode, room_code_from_route, p_name_from_route)
        else:
            print(f"Action: Routing to Home Page (Fallback for unknown route: {target_route})")
            new_view_to_append = view_home_page()

        if new_view_to_append:
            # Ensure the view being appended has its route property correctly set to target_route
            # This is critical if view_game_launcher, for example, returns a view with page.route
            if new_view_to_append.route != target_route:
                print(f"Warning: View created for {new_view_to_append.route} but target is {target_route}. Overriding view route.")
                new_view_to_append.route = target_route

            page.views.append(new_view_to_append)
            # print(f"View appended: {new_view_to_append.route}. Views count: {len(page.views)}") # Reduced verbosity
        else:
            print(f"CRITICAL Error: No view was created for route {target_route}. Appending home page as fallback.")
            page.views.append(view_home_page()) # Fallback should have route "/"

        if page.client_storage:
            # print("Calling page.update()") # Reduced verbosity
            page.update()
            # print("page.update() finished.") # Reduced verbosity
        # else: # Reduced verbosity
            # print("page.client_storage is None, skipping page.update().")
        print(f"--- ROUTE CHANGE END --- New Top: {page.views[-1].route if page.views else 'EMPTY'}, page.route: {page.route}, Views: {len(page.views)}")


    def view_pop(e: ft.ViewPopEvent):
        intended_current_route = page.data.get("intended_route_before_pop", page.route) # Get route from before this pop
        
        view_that_was_popped_instance = e.view
        view_that_was_popped_route = "N/A (e.view was None)"
        if view_that_was_popped_instance:
            view_that_was_popped_route = view_that_was_popped_instance.route if view_that_was_popped_instance.route else "N/A (e.view.route was None)"

        print(f"--- VIEW POP EVENT START ---")
        print(f"    Event's view (e.view) instance: {'Exists' if view_that_was_popped_instance else 'None'}")
        print(f"    Route of view Flet claims to have popped: '{view_that_was_popped_route}'")
        print(f"    page.route (route before this pop, likely intended): {intended_current_route}")
        print(f"    page.views count (after Flet's internal pop processing): {len(page.views)}")

        # Case 1: GHOST POP (e.view is None)
        if view_that_was_popped_instance is None:
            print(f"    Detected GHOST POP (e.view is None).")
            # If Flet's internal pop processing for this ghost pop emptied page.views,
            # it means Flet errantly cleared the stack. We must try to restore it by
            # re-navigating to the route we intended to be on.
            if not page.views and intended_current_route:
                print(f"    GHOST POP resulted in empty page.views. Attempting to restore/re-navigate to intended route: {intended_current_route}")
                page.go(intended_current_route)
                print(f"--- VIEW POP EVENT END (Ghost pop, re-navigated to {intended_current_route}) ---")
                return
            else:
                # If page.views is NOT empty (e.g., still has 1 element from the route_change),
                # it means Flet's internal pop for the ghost event didn't fully clear the stack OR
                # no re-navigation is needed as the stack seems to reflect the intended state.
                print(f"    GHOST POP but page.views is not empty (count: {len(page.views)}). Assuming stack is relatively intact or reflects current state. No explicit navigation from view_pop.")
                # If page.views has content, we assume the UI should match page.views[-1].
                # If page.route is different from page.views[-1].route, it's an inconsistency.
                # However, forcing page.go here could lead to loops if the stack is already "correct" from route_change.
                # A page.update() might be considered if the UI is stale, but let's be cautious.
                # if page.client_storage:
                #    page.update() # Could potentially help sync UI if it's stale after a ghost pop
                print(f"--- VIEW POP EVENT END (Ghost pop, no re-navigation as stack not empty or already at intended) ---")
                return

        # Case 2: GENUINE POP (e.view is not None) - This is for actual back button presses.
        print(f"    Detected GENUINE POP. Popped view route: {view_that_was_popped_route}")

        # Special handling for leaving an online game view via back button/gesture
        if view_that_was_popped_route and view_that_was_popped_route.startswith("/game/") and "/online/" in view_that_was_popped_route:
            print(f"    Online game view ({view_that_was_popped_route}) was genuinely popped. Triggering go_home() for session cleanup.")
            go_home() # This will trigger its own page.go("/") and thus a route_change
            print(f"--- VIEW POP EVENT END (Genuine pop from online game, go_home called) ---")
            return

        # Standard navigation logic for genuine pops:
        if not page.views: # If stack is empty after Flet popped e.view
            print(f"    View stack is now empty after genuine pop. Navigating to home ('/').")
            page.go("/")
        else: # If views remain, go to the new top view
            new_top_view = page.views[-1]
            print(f"    View stack is not empty after genuine pop. New top view is '{new_top_view.route}'. Navigating to it.")
            page.go(new_top_view.route)
        
        print(f"--- VIEW POP EVENT END (Genuine pop, standard navigation initiated) ---")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Initial route loading. page.route might be None or "/" or a deep link.
    # Ensure page.data["intended_route_before_pop"] is set before the first route_change.
    initial_route = page.route if page.route else "/"
    page.data["intended_route_before_pop"] = initial_route
    page.go(initial_route) 

ft.app(
    target=main, 
    assets_dir="assets",
    port=int(os.environ.get("PORT", 8550)),
    view=ft.WEB_BROWSER,
    # Consider adding other web-specific options if needed, e.g., route_url_strategy
)