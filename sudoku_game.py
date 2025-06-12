# sudoku_game.py
import flet as ft
import time
from sudoku_utils import get_sudoku_puzzle, check_solution_correctness, copy_board, validate_board_rules_and_get_conflicts, is_board_full

# --- Sizing Constants ---
FONT_SIZE_NORMAL = 14
FONT_SIZE_MEDIUM = 16
FONT_SIZE_LARGE = 18
FONT_SIZE_XLARGE = 20 # For cell numbers
FONT_SIZE_TITLE = 22
BUTTON_HEIGHT_NORMAL = 40
CONTAINER_PADDING_NORMAL = ft.padding.symmetric(horizontal=5, vertical=3)
STANDARD_BORDER_RADIUS = 8
TITLE_ICON_SIZE = 26
SUDOKU_CELL_SIZE = 38
SUDOKU_GRID_BORDER_THICKNESS_NORMAL = 1
SUDOKU_GRID_BORDER_THICKNESS_BOLD = 2.5
NUMBER_PALETTE_BUTTON_SIZE = 40

# --- OFFLINE MODE LOGIC ---
def sudoku_offline_logic(page: ft.Page, go_home_fn):
    offline_state = {
        "puzzle_board": None, "solution_board": None, "user_board": None,
        "difficulty": "normal", "step": "difficulty_select", # playing, game_over, solution_shown
        "initial_cells": set(), "selected_cell_coord": None,
        "conflicting_cells": set()
    }

    status_text_offline = ft.Text("اختر مستوى الصعوبة.", size=FONT_SIZE_LARGE, text_align=ft.TextAlign.CENTER)
    sudoku_grid_container_offline = ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)
    number_palette_offline = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
    offline_action_area = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    offline_main_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )

    text_controls_offline = [[None for _ in range(9)] for _ in range(9)]

    USER_ENTERED_COLOR = ft.Colors.ORANGE_ACCENT_700
    INITIAL_NUMBER_COLOR = ft.Colors.BLACK87
    CONFLICT_BORDER_COLOR = ft.Colors.RED_ACCENT_700
    DEFAULT_BORDER_COLOR = ft.Colors.BLACK54
    SELECTED_CELL_BG_COLOR = ft.Colors.LIGHT_BLUE_ACCENT_100
    INITIAL_CELL_BG_COLOR = ft.Colors.BLUE_GREY_50
    NORMAL_CELL_BG_COLOR = ft.Colors.WHITE
    SOLUTION_SHOWN_COLOR = ft.Colors.GREEN_ACCENT_700

    def update_cell_display_offline(r, c, value_to_display, is_initial, is_selected, is_conflicting, is_solution_shown=False):
        cell_text_control = text_controls_offline[r][c]
        if cell_text_control:
            cell_text_control.value = str(value_to_display) if value_to_display != 0 else ""

            if is_initial:
                cell_text_control.color = INITIAL_NUMBER_COLOR
                cell_text_control.weight = ft.FontWeight.BOLD
            elif is_solution_shown and value_to_display != 0:
                 cell_text_control.color = SOLUTION_SHOWN_COLOR
                 cell_text_control.weight = ft.FontWeight.BOLD
            elif value_to_display != 0:
                cell_text_control.color = USER_ENTERED_COLOR
                cell_text_control.weight = ft.FontWeight.NORMAL
            else:
                cell_text_control.color = USER_ENTERED_COLOR

            cell_container = cell_text_control.parent
            if cell_container:
                if is_selected and not is_solution_shown and offline_state["step"] == "playing":
                    cell_container.bgcolor = SELECTED_CELL_BG_COLOR
                elif is_initial:
                    cell_container.bgcolor = INITIAL_CELL_BG_COLOR
                else:
                    cell_container.bgcolor = NORMAL_CELL_BG_COLOR

                current_border_color = CONFLICT_BORDER_COLOR if is_conflicting and not is_initial and not is_solution_shown else DEFAULT_BORDER_COLOR

                cell_container.border = ft.border.Border(
                    top=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if r % 3 == 0 else SUDOKU_GRID_BORDER_THICKNESS_NORMAL, current_border_color),
                    left=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if c % 3 == 0 else SUDOKU_GRID_BORDER_THICKNESS_NORMAL, current_border_color),
                    right=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if c == 8 else (SUDOKU_GRID_BORDER_THICKNESS_NORMAL if c % 3 != 2 else SUDOKU_GRID_BORDER_THICKNESS_BOLD) , current_border_color),
                    bottom=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if r == 8 else (SUDOKU_GRID_BORDER_THICKNESS_NORMAL if r % 3 != 2 else SUDOKU_GRID_BORDER_THICKNESS_BOLD), current_border_color)
                )

    def create_sudoku_grid_ui_offline():
        sudoku_grid_container_offline.controls.clear()
        puzzle = offline_state["puzzle_board"]
        offline_state["initial_cells"].clear()
        grid_rows = []
        for r_idx in range(9):
            row_controls = []
            for c_idx in range(9):
                val = puzzle[r_idx][c_idx]
                is_initial = (val != 0)
                if is_initial:
                    offline_state["initial_cells"].add((r_idx, c_idx))
                # Create Text control first
                cell_text = ft.Text(size=FONT_SIZE_XLARGE, text_align=ft.TextAlign.CENTER)
                text_controls_offline[r_idx][c_idx] = cell_text
                # Then create Container and add Text to it
                cell_container = ft.Container(
                    content=cell_text, # Add text here
                    width=SUDOKU_CELL_SIZE, height=SUDOKU_CELL_SIZE,
                    alignment=ft.alignment.center, data=(r_idx, c_idx),
                    on_click=lambda e, r=r_idx, c=c_idx: handle_cell_click_offline(r, c),
                    # Initial border, will be updated by refresh_grid_display_offline
                    border=ft.border.Border(
                        top=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if r_idx % 3 == 0 else SUDOKU_GRID_BORDER_THICKNESS_NORMAL, DEFAULT_BORDER_COLOR),
                        left=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if c_idx % 3 == 0 else SUDOKU_GRID_BORDER_THICKNESS_NORMAL, DEFAULT_BORDER_COLOR),
                        right=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if c_idx == 8 else (SUDOKU_GRID_BORDER_THICKNESS_NORMAL if c_idx % 3 != 2 else SUDOKU_GRID_BORDER_THICKNESS_BOLD), DEFAULT_BORDER_COLOR),
                        bottom=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if r_idx == 8 else (SUDOKU_GRID_BORDER_THICKNESS_NORMAL if r_idx % 3 != 2 else SUDOKU_GRID_BORDER_THICKNESS_BOLD), DEFAULT_BORDER_COLOR)
                    ),
                )
                row_controls.append(cell_container)
            grid_rows.append(ft.Row(row_controls, spacing=0, alignment=ft.MainAxisAlignment.CENTER))
        sudoku_grid_container_offline.controls.extend(grid_rows)
        sudoku_grid_container_offline.visible = True
        # DO NOT call refresh_grid_display_offline() here. Let the caller do it.

    def refresh_grid_display_offline():
        user_board = offline_state["user_board"]
        if not user_board: return
        selected_r, selected_c = offline_state.get("selected_cell_coord") or (-1, -1)
        show_conflicts = offline_state["difficulty"] == "easy"
        conflicts_to_show = offline_state.get("conflicting_cells", set()) if show_conflicts else set()
        is_solution_shown_state = offline_state["step"] == "solution_shown"
        for r in range(9):
            for c in range(9):
                is_initial = (r,c) in offline_state["initial_cells"]
                is_selected = (r == selected_r and c == selected_c)
                is_conflicting_for_cell = show_conflicts and (r,c) in conflicts_to_show
                current_value_to_display = offline_state["solution_board"][r][c] if is_solution_shown_state else user_board[r][c]
                update_cell_display_offline(r, c, current_value_to_display, is_initial, is_selected, is_conflicting_for_cell, is_solution_shown_state)

    def handle_cell_click_offline(r_clicked, c_clicked):
        if (r_clicked, c_clicked) in offline_state["initial_cells"] or \
           offline_state["step"] in ["game_over", "solution_shown"]:
            offline_state["selected_cell_coord"] = None
            number_palette_offline.visible = False
        else:
            if offline_state.get("selected_cell_coord") == (r_clicked, c_clicked):
                offline_state["selected_cell_coord"] = None
                number_palette_offline.visible = False
            else:
                offline_state["selected_cell_coord"] = (r_clicked, c_clicked)
                number_palette_offline.visible = True
        
        refresh_grid_display_offline() 
        if page.client_storage:
            page.update()

    def handle_palette_number_click_offline(num_clicked):
        if offline_state["step"] not in ["playing"]: return
        selected_coord = offline_state.get("selected_cell_coord")
        if selected_coord:
            r, c = selected_coord
            offline_state["user_board"][r][c] = num_clicked
            if offline_state["difficulty"] == "easy":
                _, new_conflicts = validate_board_rules_and_get_conflicts(offline_state["user_board"])
                offline_state["conflicting_cells"] = new_conflicts
            else:
                offline_state["conflicting_cells"] = set()
            refresh_grid_display_offline() 
            if page.client_storage:
                page.update()

    def create_number_palette_offline():
        number_palette_offline.controls.clear()
        row1_controls = []
        for i in range(1, 6):
            btn = ft.ElevatedButton(
                str(i), on_click=lambda e, num=i: handle_palette_number_click_offline(num),
                width=NUMBER_PALETTE_BUTTON_SIZE, height=NUMBER_PALETTE_BUTTON_SIZE,
                style=ft.ButtonStyle(padding=0)
            )
            row1_controls.append(btn)
        row2_controls = []
        for i in range(6, 10):
            btn = ft.ElevatedButton(
                str(i), on_click=lambda e, num=i: handle_palette_number_click_offline(num),
                width=NUMBER_PALETTE_BUTTON_SIZE, height=NUMBER_PALETTE_BUTTON_SIZE,
                style=ft.ButtonStyle(padding=0)
            )
            row2_controls.append(btn)
        clear_btn = ft.ElevatedButton(
            content=ft.Icon(ft.Icons.BACKSPACE_OUTLINED, size=NUMBER_PALETTE_BUTTON_SIZE*0.6),
            on_click=lambda e: handle_palette_number_click_offline(0),
            width=NUMBER_PALETTE_BUTTON_SIZE, height=NUMBER_PALETTE_BUTTON_SIZE,
            tooltip="Clear cell", style=ft.ButtonStyle(padding=0)
        )
        row2_controls.append(clear_btn)
        row1 = ft.Row(controls=row1_controls, alignment=ft.MainAxisAlignment.CENTER, spacing=5)
        row2 = ft.Row(controls=row2_controls, alignment=ft.MainAxisAlignment.CENTER, spacing=5)
        number_palette_offline.controls.extend([row1, row2])

    def start_new_offline_game(difficulty):
        offline_state["difficulty"] = difficulty
        puzzle, solution = get_sudoku_puzzle(difficulty)
        offline_state["puzzle_board"] = puzzle
        offline_state["solution_board"] = solution
        offline_state["user_board"] = copy_board(puzzle)
        offline_state["initial_cells"].clear()
        offline_state["selected_cell_coord"] = None
        offline_state["conflicting_cells"] = set()
        offline_state["step"] = "playing"
        status_text_offline.value = f"بالتوفيق بدأت اللعبة"
        if difficulty != "easy":
            status_text_offline.value += " (مساعدة تظليل الأخطاء معطلة)"
        update_offline_ui_layout()

    def check_solution_offline(e=None):
        if offline_state["step"] != "playing": return
        user_board = offline_state["user_board"]
        solution = offline_state["solution_board"]
        is_correct, conflicts_from_check = check_solution_correctness(user_board, solution)
        if offline_state["difficulty"] == "easy":
            offline_state["conflicting_cells"] = conflicts_from_check
        else:
            offline_state["conflicting_cells"] = set()
        if is_correct:
            offline_state["step"] = "game_over"
            status_text_offline.value = "🎉 رائع! لقد حللت لغز السودوكو بنجاح!"
            offline_state["selected_cell_coord"] = None
        elif not is_board_full(user_board):
            status_text_offline.value = "⚠️ اللغز لم يكتمل. أكمل ملء الخانات!"
        else:
            if offline_state["difficulty"] == "easy" and offline_state["conflicting_cells"]:
                status_text_offline.value = "⚠️ هناك أخطاء في الحل. الخلايا المخالفة محددة."
            else:
                status_text_offline.value = "⚠️ الحل الذي أدخلته غير صحيح."
        update_offline_ui_layout()

    def show_solution_offline(e):
        if offline_state["step"] in ["playing", "game_over"]:
            offline_state["step"] = "solution_shown"
            status_text_offline.value = "💡 هذا هو الحل الصحيح!"
            offline_state["selected_cell_coord"] = None
            offline_state["conflicting_cells"] = set()
            update_offline_ui_layout()

    def update_offline_ui_layout():
        offline_main_column.controls.clear()
        title_bar = ft.Row(
            [
                ft.Text("🧩 سودوكو (أوفلاين)", size=FONT_SIZE_TITLE, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
                ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للقائمة الرئيسية", on_click=lambda e: go_home_fn(), icon_size=TITLE_ICON_SIZE)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        offline_main_column.controls.append(title_bar)
        offline_main_column.controls.append(status_text_offline)
        offline_action_area.controls.clear()

        if offline_state["step"] == "difficulty_select":
            sudoku_grid_container_offline.visible = False
            number_palette_offline.visible = False
            offline_action_area.controls.extend([
                ft.Text("اختر مستوى الصعوبة:", size=FONT_SIZE_MEDIUM),
                ft.ElevatedButton("سهل (مع مساعدة)", on_click=lambda e: start_new_offline_game("easy"), width=200, height=BUTTON_HEIGHT_NORMAL),
                ft.ElevatedButton("متوسط", on_click=lambda e: start_new_offline_game("normal"), width=200, height=BUTTON_HEIGHT_NORMAL),
                ft.ElevatedButton("صعب", on_click=lambda e: start_new_offline_game("hard"), width=200, height=BUTTON_HEIGHT_NORMAL),
            ])
        elif offline_state["step"] == "playing":
            if not offline_state["user_board"] or not sudoku_grid_container_offline.controls:
                create_sudoku_grid_ui_offline() 
            # Grid structure is now built. Refresh its display based on current state.
            refresh_grid_display_offline()
            sudoku_grid_container_offline.visible = True # Ensure visible

            if not number_palette_offline.controls:
                create_number_palette_offline()
            # Visibility of number_palette_offline is updated by handle_cell_click_offline
            
            offline_action_area.controls.append(
                ft.ElevatedButton("✅ تحقق من الحل", on_click=check_solution_offline, width=200, height=BUTTON_HEIGHT_NORMAL)
            )
            offline_action_area.controls.append(
                ft.ElevatedButton("🏳️ استسلام (أظهر الحل)", on_click=show_solution_offline, width=220, height=BUTTON_HEIGHT_NORMAL, bgcolor=ft.Colors.AMBER_200)
            )
            offline_action_area.controls.append(
                ft.ElevatedButton("🔄 لعبة جديدة (مستوى آخر)", on_click=lambda e: reset_to_difficulty_select(), width=250, height=BUTTON_HEIGHT_NORMAL)
            )
        elif offline_state["step"] == "game_over":
            if not sudoku_grid_container_offline.controls and offline_state["user_board"]: # Ensure grid is built if game was played
                create_sudoku_grid_ui_offline()
            refresh_grid_display_offline() 
            sudoku_grid_container_offline.visible = True
            number_palette_offline.visible = False 
            offline_action_area.controls.append(
                ft.ElevatedButton("🎉 العب مرة أخرى؟", on_click=lambda e: reset_to_difficulty_select(), width=200, height=BUTTON_HEIGHT_NORMAL)
            )
        elif offline_state["step"] == "solution_shown":
            if not sudoku_grid_container_offline.controls and offline_state["user_board"]: # Ensure grid is built
                create_sudoku_grid_ui_offline()
            refresh_grid_display_offline() 
            sudoku_grid_container_offline.visible = True
            number_palette_offline.visible = False
            offline_action_area.controls.append(
                ft.ElevatedButton("🔄 ابدأ لعبة جديدة", on_click=lambda e: reset_to_difficulty_select(), width=200, height=BUTTON_HEIGHT_NORMAL)
            )

        offline_main_column.controls.append(sudoku_grid_container_offline)
        offline_main_column.controls.append(number_palette_offline)
        offline_main_column.controls.append(offline_action_area)
        
        if page.client_storage: page.update()

    def reset_to_difficulty_select():
        offline_state["step"] = "difficulty_select"
        offline_state["puzzle_board"] = None
        offline_state["user_board"] = None
        offline_state["solution_board"] = None
        offline_state["initial_cells"] = set()
        offline_state["selected_cell_coord"] = None
        offline_state["conflicting_cells"] = set()
        status_text_offline.value = "اختر مستوى الصعوبة لبدء اللعبة."
        sudoku_grid_container_offline.controls.clear()
        sudoku_grid_container_offline.visible = False
        number_palette_offline.visible = False
        number_palette_offline.controls.clear()
        update_offline_ui_layout()

    reset_to_difficulty_select()
    return [ft.Container(content=offline_main_column, expand=True, alignment=ft.alignment.top_center, padding=ft.padding.all(10))]

# --- ONLINE MODE CLIENT-SIDE LOGIC ---
def sudoku_online_logic(page: ft.Page, go_home_fn, send_action_fn, room_code: str, current_player_name: str, game_rooms_ref):
    online_state = {
        "user_board": None,
        "puzzle_board_from_server": None,
        "solution_board_from_server": None,
        "initial_cells": set(),
        "selected_cell_coord": None,
        "conflicting_cells": set(),
        "is_game_over_globally": False,
        "difficulty_online": "normal",
        "client_solution_check_passed": False,
        "local_game_step": "playing"
    }

    status_text_online = ft.Text("...", size=FONT_SIZE_LARGE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    player_list_display_online = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    action_area_online = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    sudoku_grid_container_online = ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)
    number_palette_online = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)

    text_controls_online = [[None for _ in range(9)] for _ in range(9)]

    online_main_content_column = ft.Column(
        expand=True, scroll=ft.ScrollMode.ADAPTIVE,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6
    )
    ONLINE_USER_ENTERED_COLOR = ft.Colors.DEEP_PURPLE_ACCENT_700
    ONLINE_INITIAL_NUMBER_COLOR = ft.Colors.BLACK87
    ONLINE_CONFLICT_BORDER_COLOR = ft.Colors.RED_ACCENT_700
    ONLINE_DEFAULT_BORDER_COLOR = ft.Colors.BLACK54
    ONLINE_SELECTED_CELL_BG_COLOR = ft.Colors.LIGHT_GREEN_ACCENT_100
    ONLINE_INITIAL_CELL_BG_COLOR = ft.Colors.BLUE_GREY_50
    ONLINE_NORMAL_CELL_BG_COLOR = ft.Colors.WHITE
    ONLINE_SOLUTION_SHOWN_COLOR = ft.Colors.GREEN_ACCENT_700

    def update_cell_display_online(r, c, value_to_display, is_initial, is_selected, is_conflicting, is_solution_shown=False):
        cell_text_control = text_controls_online[r][c]
        if cell_text_control: # Check if control exists
            cell_text_control.value = str(value_to_display) if value_to_display != 0 else ""

            if is_initial:
                cell_text_control.color = ONLINE_INITIAL_NUMBER_COLOR
                cell_text_control.weight = ft.FontWeight.BOLD
            elif is_solution_shown and value_to_display != 0:
                 cell_text_control.color = ONLINE_SOLUTION_SHOWN_COLOR
                 cell_text_control.weight = ft.FontWeight.BOLD
            elif value_to_display != 0:
                cell_text_control.color = ONLINE_USER_ENTERED_COLOR
                cell_text_control.weight = ft.FontWeight.NORMAL
            else:
                cell_text_control.color = ONLINE_USER_ENTERED_COLOR

            cell_container = cell_text_control.parent
            if cell_container: # Check if parent container exists
                if is_selected and not online_state.get("is_game_over_globally") and not is_solution_shown:
                    cell_container.bgcolor = ONLINE_SELECTED_CELL_BG_COLOR
                elif is_initial:
                    cell_container.bgcolor = ONLINE_INITIAL_CELL_BG_COLOR
                else:
                    cell_container.bgcolor = ONLINE_NORMAL_CELL_BG_COLOR

                current_border_color = ONLINE_CONFLICT_BORDER_COLOR if is_conflicting and not is_initial and not is_solution_shown else ONLINE_DEFAULT_BORDER_COLOR

                cell_container.border = ft.border.Border(
                    top=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if r % 3 == 0 else SUDOKU_GRID_BORDER_THICKNESS_NORMAL, current_border_color),
                    left=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if c % 3 == 0 else SUDOKU_GRID_BORDER_THICKNESS_NORMAL, current_border_color),
                    right=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if c == 8 else (SUDOKU_GRID_BORDER_THICKNESS_NORMAL if c % 3 != 2 else SUDOKU_GRID_BORDER_THICKNESS_BOLD) , current_border_color),
                    bottom=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if r == 8 else (SUDOKU_GRID_BORDER_THICKNESS_NORMAL if r % 3 != 2 else SUDOKU_GRID_BORDER_THICKNESS_BOLD), current_border_color)
                )

    def create_sudoku_grid_ui_online(puzzle_board_from_server):
        online_state["puzzle_board_from_server"] = copy_board(puzzle_board_from_server)
        online_state["user_board"] = copy_board(puzzle_board_from_server)
        online_state["initial_cells"].clear()
        online_state["conflicting_cells"] = set()

        sudoku_grid_container_online.controls.clear()
        grid_rows = []
        for r_idx in range(9):
            row_controls = []
            for c_idx in range(9):
                val = online_state["puzzle_board_from_server"][r_idx][c_idx]
                is_initial = (val != 0)
                if is_initial:
                    online_state["initial_cells"].add((r_idx, c_idx))
                
                # Create Text control first
                cell_text = ft.Text(size=FONT_SIZE_XLARGE, text_align=ft.TextAlign.CENTER)
                text_controls_online[r_idx][c_idx] = cell_text # Store reference

                # Then create Container and add Text to it
                cell_container = ft.Container(
                    content=cell_text, # Add the created text control here
                    width=SUDOKU_CELL_SIZE, height=SUDOKU_CELL_SIZE,
                    alignment=ft.alignment.center, data=(r_idx, c_idx),
                    on_click=lambda e, r=r_idx, c=c_idx: handle_cell_click_online(r, c),
                    # Initial border, will be updated by refresh_grid_display_online
                    border=ft.border.Border( 
                        top=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if r_idx % 3 == 0 else SUDOKU_GRID_BORDER_THICKNESS_NORMAL, ONLINE_DEFAULT_BORDER_COLOR),
                        left=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if c_idx % 3 == 0 else SUDOKU_GRID_BORDER_THICKNESS_NORMAL, ONLINE_DEFAULT_BORDER_COLOR),
                        right=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if c_idx == 8 else (SUDOKU_GRID_BORDER_THICKNESS_NORMAL if c_idx % 3 != 2 else SUDOKU_GRID_BORDER_THICKNESS_BOLD), ONLINE_DEFAULT_BORDER_COLOR),
                        bottom=ft.border.BorderSide(SUDOKU_GRID_BORDER_THICKNESS_BOLD if r_idx == 8 else (SUDOKU_GRID_BORDER_THICKNESS_NORMAL if r_idx % 3 != 2 else SUDOKU_GRID_BORDER_THICKNESS_BOLD), ONLINE_DEFAULT_BORDER_COLOR)
                    ),
                )
                row_controls.append(cell_container)
            grid_rows.append(ft.Row(row_controls, spacing=0, alignment=ft.MainAxisAlignment.CENTER))
        
        sudoku_grid_container_online.controls.extend(grid_rows)
        sudoku_grid_container_online.visible = True
        # DO NOT call refresh_grid_display_online() here. Let the caller (update_ui_from_server_state_online_sudoku) do it.

    def refresh_grid_display_online():
        if not online_state["user_board"]: return
        selected_r, selected_c = online_state.get("selected_cell_coord") or (-1, -1)
        is_solution_shown_locally = online_state["local_game_step"] == "solution_shown"

        show_conflicts = online_state.get("difficulty_online") == "easy"
        conflicts_to_show = online_state.get("conflicting_cells", set()) if show_conflicts else set()

        for r in range(9):
            for c in range(9):
                is_initial = (r,c) in online_state["initial_cells"]
                is_selected = (r == selected_r and c == selected_c)
                is_conflicting_for_cell = show_conflicts and (r,c) in conflicts_to_show
                current_value_to_display = online_state["solution_board_from_server"][r][c] if is_solution_shown_locally and online_state["solution_board_from_server"] else online_state["user_board"][r][c]
                update_cell_display_online(r, c, current_value_to_display, is_initial, is_selected, is_conflicting_for_cell, is_solution_shown_locally)

    def handle_cell_click_online(r_clicked, c_clicked):
        if (r_clicked, c_clicked) in online_state["initial_cells"] or \
           online_state.get("is_game_over_globally") or \
           online_state["local_game_step"] == "solution_shown":
            online_state["selected_cell_coord"] = None
            number_palette_online.visible = False
        else:
            if online_state.get("selected_cell_coord") == (r_clicked, c_clicked):
                online_state["selected_cell_coord"] = None
                number_palette_online.visible = False
            else:
                online_state["selected_cell_coord"] = (r_clicked, c_clicked)
                number_palette_online.visible = True
        
        refresh_grid_display_online() 
        if page.client_storage:
            page.update()

    def handle_palette_number_click_online(num_clicked):
        if online_state.get("is_game_over_globally") or online_state["local_game_step"] == "solution_shown": return
        selected_coord = online_state.get("selected_cell_coord")
        if selected_coord and online_state["user_board"]:
            r, c = selected_coord
            online_state["user_board"][r][c] = num_clicked
            online_state["client_solution_check_passed"] = False

            if online_state.get("difficulty_online") == "easy":
                _, new_conflicts = validate_board_rules_and_get_conflicts(online_state["user_board"])
                online_state["conflicting_cells"] = new_conflicts
            else:
                online_state["conflicting_cells"] = set()

            # Refresh display first (updates control properties in memory)
            refresh_grid_display_online()
            
            # Then, call the main UI orchestrator which will call page.update()
            # This ensures that all state changes from this click (board, conflicts)
            # are reflected before the single page.update() in update_ui_from_server_state_online_sudoku.
            if page.client_storage:
                current_room_state = game_rooms_ref.get(room_code, {})
                # update_ui_from_server_state_online_sudoku will be called, which calls page.update()
                # For direct feedback on the grid from palette click, this might be too indirect.
                # Let's see if the existing structure with update_ui_from_server_state_online_sudoku calling page.update() is enough.
                # If not, a direct page.update() here might be needed *after* refresh_grid_display_online()
                # and before or instead of update_ui_from_server_state_online_sudoku if that's too heavy.
                # For now, relying on update_ui_from_server_state_online_sudoku from the original code.
                update_ui_from_server_state_online_sudoku(current_room_state)


    def create_number_palette_online():
        number_palette_online.controls.clear()
        row1_controls = []
        for i in range(1, 6):
            btn = ft.ElevatedButton(str(i), on_click=lambda e, num=i: handle_palette_number_click_online(num), width=NUMBER_PALETTE_BUTTON_SIZE, height=NUMBER_PALETTE_BUTTON_SIZE, style=ft.ButtonStyle(padding=0))
            row1_controls.append(btn)
        row2_controls = []
        for i in range(6, 10):
            btn = ft.ElevatedButton(str(i), on_click=lambda e, num=i: handle_palette_number_click_online(num), width=NUMBER_PALETTE_BUTTON_SIZE, height=NUMBER_PALETTE_BUTTON_SIZE, style=ft.ButtonStyle(padding=0))
            row2_controls.append(btn)
        clear_btn = ft.ElevatedButton(content=ft.Icon(ft.Icons.BACKSPACE_OUTLINED, size=NUMBER_PALETTE_BUTTON_SIZE*0.6), on_click=lambda e: handle_palette_number_click_online(0), width=NUMBER_PALETTE_BUTTON_SIZE, height=NUMBER_PALETTE_BUTTON_SIZE, tooltip="Clear cell", style=ft.ButtonStyle(padding=0))
        row2_controls.append(clear_btn)
        row1 = ft.Row(controls=row1_controls, alignment=ft.MainAxisAlignment.CENTER, spacing=5)
        row2 = ft.Row(controls=row2_controls, alignment=ft.MainAxisAlignment.CENTER, spacing=5)
        number_palette_online.controls.extend([row1, row2])

    def client_check_solution_online(e):
        print(f"[DEBUG] 'تحقق من حلي' button clicked by {current_player_name}")
        if not page.client_storage:
            print("[DEBUG] page.client_storage not available")
            return
        if online_state["user_board"]:
            print("[DEBUG] Current board state:")
            for i, row_val in enumerate(online_state["user_board"]):
                print(f"[DEBUG] Row {i+1}: {row_val}")
        if not online_state["user_board"] or online_state.get("is_game_over_globally") or online_state["local_game_step"] == "solution_shown":
            print("[DEBUG] Validation skipped - invalid state")
            return

        snack_message = ""
        snack_bgcolor = None
        temp_client_solution_check_passed = False
        solution_board = online_state["solution_board_from_server"]
        print(f"[DEBUG] Solution board available: {bool(solution_board)}")

        if not solution_board:
            snack_message = "بيانات الحل غير متوفرة للتحقق المحلي."
        elif not is_board_full(online_state["user_board"]):
            snack_message = "⚠️ اللغز لم يكتمل. أكمل ملء الخانات!"
        else:
            is_correct_locally, _ = check_solution_correctness(online_state["user_board"], solution_board)
            print(f"[DEBUG] Local validation result: {'Correct' if is_correct_locally else 'Incorrect'}")
            if is_correct_locally:
                snack_message = "✅ يبدو أن الحل صحيح! يمكنك الآن إرساله للخادم."
                snack_bgcolor = ft.Colors.GREEN_ACCENT_700
                temp_client_solution_check_passed = True
            else:
                snack_message = "⚠️ الحل الذي أدخلته غير صحيح محلياً. راجعه."
                snack_bgcolor = ft.Colors.RED_ACCENT_100
        online_state["client_solution_check_passed"] = temp_client_solution_check_passed
        print(f"[DEBUG] Validation state updated: {temp_client_solution_check_passed}")

        if snack_message and page.client_storage:
            snackbar = ft.SnackBar(
                content=ft.Text(snack_message, text_align=ft.TextAlign.CENTER),
                bgcolor=snack_bgcolor, duration=5000
            )
            page.overlay.append(snackbar) # Add to overlay
            snackbar.open = True # Then open it
            print(f"[DEBUG] Showing snackbar: {snack_message}")
            # page.update() # An update will be called by update_ui_from_server_state_online_sudoku

        print("[DEBUG] Updating UI from server state after client check")
        current_room_state = game_rooms_ref.get(room_code, {})
        update_ui_from_server_state_online_sudoku(current_room_state)


    def submit_solution_to_server_online(e):
        if not online_state["user_board"] or \
           online_state.get("is_game_over_globally") or \
           online_state["local_game_step"] == "solution_shown" or \
           not online_state["client_solution_check_passed"]:
            if page.client_storage and not online_state["client_solution_check_passed"]:
                 page.snack_bar = ft.SnackBar(ft.Text("الرجاء الضغط على 'تحقق من حلي' أولاً والتأكد أنه صحيح محلياً."), open=True)
                 page.update() 
            return
        send_action_fn("SUBMIT_SUDOKU_SOLUTION", {"board": online_state["user_board"]})
        online_state["client_solution_check_passed"] = False
        if page.client_storage: 
            update_ui_from_server_state_online_sudoku(game_rooms_ref.get(room_code, {}))

    def show_solution_online_client_side(e):
        if online_state["local_game_step"] == "playing" and online_state["solution_board_from_server"] and not online_state.get("is_game_over_globally"):
            online_state["local_game_step"] = "solution_shown"
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("💡 تم عرض الحل لك. لا يمكنك الإرسال الآن."), open=True)
            online_state["selected_cell_coord"] = None
            number_palette_online.visible = False 
            refresh_grid_display_online() 
            if page.client_storage: 
                update_ui_from_server_state_online_sudoku(game_rooms_ref.get(room_code, {}))
        elif not online_state["solution_board_from_server"] and page.client_storage:
            page.snack_bar = ft.SnackBar(ft.Text("بيانات الحل غير متوفرة لعرضها."), open=True)
            page.update()

    def update_ui_from_server_state_online_sudoku(room_state_from_server):
        if not page.client_storage: return 

        gs = room_state_from_server.get("game_state", {})
        players_in_room = room_state_from_server.get("players", {})
        is_host = players_in_room.get(current_player_name, {}).get("is_host", False)
        current_phase = gs.get("phase", "LOBBY")

        status_text_online.value = gs.get("status_message", "...")
        online_state["is_game_over_globally"] = (current_phase == "GAME_OVER")
        online_state["difficulty_online"] = gs.get("difficulty", "normal")
        if "solution_board" in gs and gs["solution_board"]:
            online_state["solution_board_from_server"] = gs["solution_board"]

        player_list_display_online.controls.clear()
        player_list_display_online.controls.append(ft.Text(f"اللاعبون ({len(players_in_room)}):", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
        for p_name_iter, p_data_iter in players_in_room.items():
            player_list_display_online.controls.append(
                ft.Text(f"• {p_data_iter.get('name','Unknown')} {'👑' if p_data_iter.get('is_host') else ''}", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_NORMAL)
            )

        action_area_online.controls.clear()

        if current_phase == "LOBBY":
            online_state["local_game_step"] = "playing"
            online_state["client_solution_check_passed"] = False
            sudoku_grid_container_online.visible = False
            sudoku_grid_container_online.controls.clear() 
            number_palette_online.visible = False
            number_palette_online.controls.clear() 
            online_state["user_board"] = None
            online_state["puzzle_board_from_server"] = None
            online_state["solution_board_from_server"] = None
            online_state["conflicting_cells"] = set()
            online_state["selected_cell_coord"] = None
            online_state["initial_cells"] = set()

            action_area_online.controls.append(ft.Text("الهوست يختار مستوى الصعوبة ويبدأ.", text_align=ft.TextAlign.CENTER, size=FONT_SIZE_MEDIUM))
            if is_host:
                difficulty_dropdown = ft.Dropdown(label="اختر مستوى الصعوبة", options=[ft.dropdown.Option("easy", "سهل"), ft.dropdown.Option("normal", "متوسط"), ft.dropdown.Option("hard", "صعب")], value=gs.get("difficulty", "normal"), width=200)
                action_area_online.controls.append(difficulty_dropdown)
                action_area_online.controls.append(ft.ElevatedButton("🚀 ابدأ سودوكو", on_click=lambda e: send_action_fn("SETUP_SUDOKU_GAME", {"difficulty": difficulty_dropdown.value}), width=250, height=BUTTON_HEIGHT_NORMAL))

        elif current_phase == "PLAYING":
            puzzle_board = gs.get("puzzle_board")
            grid_needs_creation = not online_state["puzzle_board_from_server"] or \
                                  online_state["puzzle_board_from_server"] != puzzle_board or \
                                  not sudoku_grid_container_online.controls
            
            if puzzle_board and grid_needs_creation:
                 online_state["local_game_step"] = "playing"
                 online_state["client_solution_check_passed"] = False
                 create_sudoku_grid_ui_online(puzzle_board) # Builds structure
            
            # Always refresh display properties if in PLAYING phase and grid exists or was just created
            if puzzle_board and sudoku_grid_container_online.controls:
                 refresh_grid_display_online() 
                 sudoku_grid_container_online.visible = True


            if not number_palette_online.controls: create_number_palette_online()
            
            can_interact_client = not online_state.get("is_game_over_globally") and online_state["local_game_step"] == "playing"
            
            if online_state.get("selected_cell_coord") and can_interact_client:
                number_palette_online.visible = True
            elif not can_interact_client: 
                number_palette_online.visible = False
            # If no cell selected and game playing, palette visibility remains as is (likely false from deselect)

            action_area_online.controls.append(
                ft.ElevatedButton("🤔 تحقق من حلي", on_click=client_check_solution_online, width=200, height=BUTTON_HEIGHT_NORMAL,
                                  disabled=not can_interact_client)
            )
            action_area_online.controls.append(
                ft.ElevatedButton("🏁 إرسال الحل للخادم", on_click=submit_solution_to_server_online, width=220, height=BUTTON_HEIGHT_NORMAL,
                                  disabled=not (can_interact_client and online_state["client_solution_check_passed"]),
                                  bgcolor=ft.Colors.GREEN_ACCENT_200 if (can_interact_client and online_state["client_solution_check_passed"]) else None)
            )
            if online_state["solution_board_from_server"]:
                action_area_online.controls.append(
                    ft.ElevatedButton("🏳️ استسلام (أظهر الحل لي)", on_click=show_solution_online_client_side, width=250, height=BUTTON_HEIGHT_NORMAL,
                                      bgcolor=ft.Colors.AMBER_200, disabled=not can_interact_client)
                )

            difficulty_display = gs.get("difficulty", "غير محدد")
            action_area_online.controls.append(ft.Text(f"مستوى الصعوبة: {difficulty_display}", size=FONT_SIZE_MEDIUM))

        elif current_phase == "GAME_OVER":
            if not sudoku_grid_container_online.controls and (online_state["user_board"] or gs.get("puzzle_board")):
                # Ensure grid is built if it wasn't (e.g., if player joined during game over)
                board_to_display = online_state["user_board"] if online_state["user_board"] else gs.get("puzzle_board")
                if board_to_display:
                    create_sudoku_grid_ui_online(board_to_display)

            if sudoku_grid_container_online.controls: # Only refresh if grid exists
                refresh_grid_display_online() 
                sudoku_grid_container_online.visible = True
            else: # Should not happen if board_to_display was valid
                sudoku_grid_container_online.visible = False
                sudoku_grid_container_online.controls.clear()
                sudoku_grid_container_online.controls.append(ft.Text("انتهت اللعبة.", text_align=ft.TextAlign.CENTER))


            number_palette_online.visible = False 
            online_state["selected_cell_coord"] = None 

            winner_name = gs.get("winner", "غير معروف")
            action_area_online.controls.append(ft.Text(f"🏆 الفائز: {winner_name}", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_700))
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى؟", on_click=lambda e: send_action_fn("RESTART_SUDOKU_GAME"), width=200, height=BUTTON_HEIGHT_NORMAL))

        page.update()

    def on_server_message_online_sudoku(*args_received):
        if not page.client_storage: return
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")

        current_room_full_state = game_rooms_ref.get(room_code, {}) 
        if not current_room_full_state: return 

        current_gs_from_room = current_room_full_state.get("game_state", {})

        if msg_type == "GAME_STATE_UPDATE":
            room_state_from_msg = msg_data.get("room_state")
            if room_state_from_msg and isinstance(room_state_from_msg, dict) and room_state_from_msg.get("game_type") == "sudoku":
                gs_updated = room_state_from_msg.get("game_state",{})
                if "solution_board" in gs_updated and gs_updated["solution_board"]: 
                     online_state["solution_board_from_server"] = gs_updated["solution_board"]
                update_ui_from_server_state_online_sudoku(room_state_from_msg)
        elif msg_type == "SUDOKU_SUBMISSION_FEEDBACK":
            if msg_data.get("feedback_for_player") == current_player_name:
                feedback_txt = msg_data.get("feedback_message", "تم استلام الرد.")
                if page.client_storage: 
                    page.snack_bar = ft.SnackBar(ft.Text(feedback_txt, text_align=ft.TextAlign.CENTER), open=True)
                    page.update() 

                if "كان الأسرع" in feedback_txt or \
                   (current_gs_from_room.get("phase") == "GAME_OVER" and "فاز باللعبة" in current_gs_from_room.get("status_message","")):
                    online_state["is_game_over_globally"] = True 
                    if page.client_storage: 
                        update_ui_from_server_state_online_sudoku(game_rooms_ref.get(room_code, {})) 
        elif msg_type == "SUDOKU_SOLUTION_UPDATE": 
            solution_board = msg_data.get("solution_board")
            if solution_board:
                online_state["solution_board_from_server"] = solution_board
                update_ui_from_server_state_online_sudoku(game_rooms_ref.get(room_code, {})) 


        elif msg_type in ["PLAYER_JOINED", "PLAYER_LEFT"]:
             room_state_from_msg = msg_data.get("room_state") 
             if room_state_from_msg and isinstance(room_state_from_msg, dict) and room_state_from_msg.get("game_type") == "sudoku":
                gs_updated = room_state_from_msg.get("game_state",{})
                if "solution_board" in gs_updated and gs_updated["solution_board"]:
                     online_state["solution_board_from_server"] = gs_updated["solution_board"]
                update_ui_from_server_state_online_sudoku(room_state_from_msg) 

    page.pubsub.subscribe_topic(f"room_{room_code}", on_server_message_online_sudoku)

    online_main_content_column.controls.clear()
    online_main_content_column.controls.extend([
        ft.Row(
            [
                ft.Text(f"🧩 سودوكو - غرفة: {room_code}", size=FONT_SIZE_TITLE, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
                ft.IconButton(ft.Icons.HOME_ROUNDED, tooltip="العودة للرئيسية", on_click=go_home_fn, icon_size=TITLE_ICON_SIZE)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        ft.Divider(height=1, thickness=0.5), status_text_online, ft.Divider(height=3, thickness=1),
        ft.ResponsiveRow(
            [
                ft.Container(
                    content=player_list_display_online, padding=8,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.OUTLINE)),
                    border_radius=STANDARD_BORDER_RADIUS, col={"xs": 12, "md": 4},
                    margin=ft.margin.only(bottom=8 if page.width and page.width < 768 else 0, top=5)
                ),
                ft.Container(
                    content=ft.Column([
                        sudoku_grid_container_online, ft.Container(height=10),
                        number_palette_online, ft.Container(height=10),
                        action_area_online
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=CONTAINER_PADDING_NORMAL, col={"xs": 12, "md": 8},
                    alignment=ft.alignment.top_center
                )
            ], vertical_alignment=ft.CrossAxisAlignment.START, alignment=ft.MainAxisAlignment.SPACE_AROUND, spacing=10, run_spacing=10
        )
    ])

    initial_room_data = game_rooms_ref.get(room_code)
    if initial_room_data:
        gs_initial = initial_room_data.get("game_state", {})
        if "solution_board" in gs_initial and gs_initial["solution_board"]:
            online_state["solution_board_from_server"] = gs_initial["solution_board"]
        update_ui_from_server_state_online_sudoku(initial_room_data) 
    else:
        status_text_online.value = "خطأ في الاتصال بالغرفة."
        if page.client_storage: page.update()

    return [ft.Container(content=online_main_content_column, expand=True, alignment=ft.alignment.top_center, padding=10)]


# --- GAME ENTRY POINT ---
def sudoku_game_entry(page: ft.Page, go_home_fn, process_action_fn, is_online: bool, room_code: str = None, player_name: str = None, game_rooms_ref=None):
    if not is_online:
        return sudoku_offline_logic(page, go_home_fn)
    else:
        if not room_code or not player_name or game_rooms_ref is None:
            return [ft.Container(content=ft.Text("خطأ: بيانات اللاعب أو الغرفة غير متوفرة لسودوكو أونلاين."), alignment=ft.alignment.center, expand=True)]

        def send_sudoku_action_to_server_wrapper(action_type: str, payload: dict = None):
            process_action_fn(page, room_code, player_name, "sudoku", action_type, payload or {})

        return sudoku_online_logic(page, go_home_fn, send_sudoku_action_to_server_wrapper, room_code, player_name, game_rooms_ref)