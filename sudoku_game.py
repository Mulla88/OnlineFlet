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
                cell_text = ft.Text(str(val) if is_initial else "", size=FONT_SIZE_XLARGE, text_align=ft.TextAlign.CENTER)
                text_controls_offline[r_idx][c_idx] = cell_text
                cell_container = ft.Container(
                    content=cell_text, width=SUDOKU_CELL_SIZE, height=SUDOKU_CELL_SIZE,
                    alignment=ft.alignment.center, data=(r_idx, c_idx),
                    on_click=lambda e, r=r_idx, c=c_idx: handle_cell_click_offline(r, c),
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
        refresh_grid_display_offline()

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
        # REMOVED: if page.client_storage: page.update()

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
        
        refresh_grid_display_offline() # This no longer calls page.update()
        
        if page.client_storage:
            # Update the whole page to reflect grid selection and palette visibility.
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
            
            refresh_grid_display_offline() # This no longer calls page.update()
            
            if page.client_storage:
                page.update() # Update the page to reflect changes on the grid

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
        
        if offline_state["difficulty"] == "easy": # Update conflicts regardless of correctness for 'easy'
            offline_state["conflicting_cells"] = conflicts_from_check
        else:
            offline_state["conflicting_cells"] = set()

        if is_correct:
            offline_state["step"] = "game_over"
            status_text_offline.value = "🎉 رائع! لقد حللت لغز السودوكو بنجاح!"
            offline_state["selected_cell_coord"] = None
            # Visibility of number_palette_offline handled by update_offline_ui_layout
        elif not is_board_full(user_board):
            status_text_offline.value = "⚠️ اللغز لم يكتمل. أكمل ملء الخانات!"
        else:
            if offline_state["difficulty"] == "easy" and offline_state["conflicting_cells"]: # Check after updating conflicts
                status_text_offline.value = "⚠️ هناك أخطاء في الحل. الخلايا المخالفة محددة."
            else:
                status_text_offline.value = "⚠️ الحل الذي أدخلته غير صحيح."
        
        # update_offline_ui_layout will call refresh_grid_display_offline and page.update()
        update_offline_ui_layout()

    def show_solution_offline(e):
        if offline_state["step"] in ["playing", "game_over"]:
            offline_state["step"] = "solution_shown"
            status_text_offline.value = "💡 هذا هو الحل الصحيح!"
            offline_state["selected_cell_coord"] = None
            offline_state["conflicting_cells"] = set()
            # Visibility of number_palette_offline and grid refresh handled by update_offline_ui_layout
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
            if not offline_state["user_board"]:
                create_sudoku_grid_ui_offline() # This calls refresh_grid_display_offline (which doesn't page.update())
            else:
                sudoku_grid_container_offline.visible = True
                if not sudoku_grid_container_offline.controls:
                    create_sudoku_grid_ui_offline()
                else:
                    refresh_grid_display_offline() # Doesn't page.update()
            
            if not number_palette_offline.controls:
                create_number_palette_offline()
            # Visibility of number_palette_offline is handled by handle_cell_click_offline,
            # which now calls page.update() itself.
            # Here we just ensure it's part of the layout.
            # Its visibility state is managed by handle_cell_click_offline.
            
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
            sudoku_grid_container_offline.visible = True
            number_palette_offline.visible = False # Explicitly set for game_over state
            refresh_grid_display_offline() # Doesn't page.update()
            offline_action_area.controls.append(
                ft.ElevatedButton("🎉 العب مرة أخرى؟", on_click=lambda e: reset_to_difficulty_select(), width=200, height=BUTTON_HEIGHT_NORMAL)
            )
        elif offline_state["step"] == "solution_shown":
            sudoku_grid_container_offline.visible = True
            number_palette_offline.visible = False # Explicitly set for solution_shown state
            refresh_grid_display_offline() # Doesn't page.update()
            offline_action_area.controls.append(
                ft.ElevatedButton("🔄 ابدأ لعبة جديدة", on_click=lambda e: reset_to_difficulty_select(), width=200, height=BUTTON_HEIGHT_NORMAL)
            )

        offline_main_column.controls.append(sudoku_grid_container_offline)
        offline_main_column.controls.append(number_palette_offline) # Add to layout, visibility managed elsewhere or here
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
        if cell_text_control:
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
            if cell_container:
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
                cell_text = ft.Text(str(val) if is_initial else "", size=FONT_SIZE_XLARGE, text_align=ft.TextAlign.CENTER)
                text_controls_online[r_idx][c_idx] = cell_text
                cell_container = ft.Container(
                    content=cell_text, width=SUDOKU_CELL_SIZE, height=SUDOKU_CELL_SIZE,
                    alignment=ft.alignment.center, data=(r_idx, c_idx),
                    on_click=lambda e, r=r_idx, c=c_idx: handle_cell_click_online(r, c),
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
        refresh_grid_display_online() # Doesn't call page.update()

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
        # REMOVED: if page.client_storage: page.update()

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
        
        refresh_grid_display_online() # This no longer calls page.update()
        
        if page.client_storage:
            # Update the whole page to reflect grid selection and palette visibility.
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

            refresh_grid_display_online() # Doesn't call page.update()
            
            # The UI update related to the board change will be handled by update_ui_from_server_state_online_sudoku
            # if this action also triggers a server state update.
            # However, for immediate local feedback (like conflict highlighting), we might need an update.
            # The current structure calls update_ui_from_server_state_online_sudoku, which handles page.update().
            if page.client_storage:
                current_room_state = game_rooms_ref.get(room_code, {})
                update_ui_from_server_state_online_sudoku(current_room_state) # This will call page.update()

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
            for i, row in enumerate(online_state["user_board"]):
                print(f"[DEBUG] Row {i+1}: {row}")

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
            temp_client_solution_check_passed = False
        elif not is_board_full(online_state["user_board"]):
            snack_message = "⚠️ اللغز لم يكتمل. أكمل ملء الخانات!"
            temp_client_solution_check_passed = False
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
                temp_client_solution_check_passed = False

        online_state["client_solution_check_passed"] = temp_client_solution_check_passed
        print(f"[DEBUG] Validation state updated: {temp_client_solution_check_passed}")

        if snack_message and page.client_storage: # Check page.client_storage before accessing page.overlay
            snackbar = ft.SnackBar(
                content=ft.Text(snack_message, text_align=ft.TextAlign.CENTER),
                bgcolor=snack_bgcolor,
                duration=5000
            )
            snackbar.open = True # This should trigger its own update if attached to page.overlay
            page.overlay.append(snackbar) # Make sure snackbar is on the page
            print(f"[DEBUG] Showing snackbar: {snack_message}")

        print("[DEBUG] Updating UI from server state after client check")
        current_room_state = game_rooms_ref.get(room_code, {})
        update_ui_from_server_state_online_sudoku(current_room_state) # This calls page.update()

        # The page.update() inside update_ui_from_server_state_online_sudoku should handle snackbar display
        # if it's correctly added to page.overlay before that call.
        # If snackbar doesn't show, an explicit page.update() here might be needed, but try without first.
        # if page.client_storage:
        #    page.update() 
        #    print("[DEBUG] Page updated after snackbar and UI update from server state")


    def submit_solution_to_server_online(e):
        if not online_state["user_board"] or \
           online_state.get("is_game_over_globally") or \
           online_state["local_game_step"] == "solution_shown" or \
           not online_state["client_solution_check_passed"]:
            if page.client_storage and not online_state["client_solution_check_passed"]:
                 page.snack_bar = ft.SnackBar(ft.Text("الرجاء الضغط على 'تحقق من حلي' أولاً والتأكد أنه صحيح محلياً."), open=True)
                 page.update() # For snackbar
            return
        send_action_fn("SUBMIT_SUDOKU_SOLUTION", {"board": online_state["user_board"]})
        online_state["client_solution_check_passed"] = False
        if page.client_storage: 
            update_ui_from_server_state_online_sudoku(game_rooms_ref.get(room_code, {})) # This calls page.update()

    def show_solution_online_client_side(e):
        if online_state["local_game_step"] == "playing" and online_state["solution_board_from_server"] and not online_state.get("is_game_over_globally"):
            online_state["local_game_step"] = "solution_shown"
            if page.client_storage:
                page.snack_bar = ft.SnackBar(ft.Text("💡 تم عرض الحل لك. لا يمكنك الإرسال الآن."), open=True)
                # page.update() here might be good for the snackbar if not handled by open=True and the main update below
            online_state["selected_cell_coord"] = None
            number_palette_online.visible = False # This state change will be reflected by update_ui
            refresh_grid_display_online() # Doesn't call page.update()
            if page.client_storage: 
                update_ui_from_server_state_online_sudoku(game_rooms_ref.get(room_code, {})) # This calls page.update()
        elif not online_state["solution_board_from_server"] and page.client_storage:
            page.snack_bar = ft.SnackBar(ft.Text("بيانات الحل غير متوفرة لعرضها."), open=True)
            page.update() # For snackbar

    def update_ui_from_server_state_online_sudoku(room_state_from_server):
        if not page.client_storage: return # Early exit if page is not valid

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
            sudoku_grid_container_online.controls.clear() # Clear old grid
            number_palette_online.visible = False
            number_palette_online.controls.clear() # Clear old palette
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
            if puzzle_board and (not online_state["puzzle_board_from_server"] or online_state["puzzle_board_from_server"] != puzzle_board or not sudoku_grid_container_online.controls) :
                 online_state["local_game_step"] = "playing"
                 online_state["client_solution_check_passed"] = False
                 create_sudoku_grid_ui_online(puzzle_board) # Calls refresh (no update)
            elif puzzle_board and sudoku_grid_container_online.visible: # Grid exists, just refresh
                 refresh_grid_display_online() # No update
            elif puzzle_board: # Should be caught by first condition if grid needs creation
                online_state["local_game_step"] = "playing"
                online_state["client_solution_check_passed"] = False
                create_sudoku_grid_ui_online(puzzle_board) # Calls refresh (no update)

            if not number_palette_online.controls: create_number_palette_online()
            # Visibility of number_palette_online is handled by handle_cell_click_online or here if game over

            can_interact_client = not online_state.get("is_game_over_globally") and online_state["local_game_step"] == "playing"
            
            # Palette visibility if game is playing
            if online_state.get("selected_cell_coord") and can_interact_client:
                number_palette_online.visible = True
            elif not can_interact_client: # e.g. game over or solution shown locally
                number_palette_online.visible = False
            # else: keep current visibility if no cell selected but game is on.

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
            sudoku_grid_container_online.visible = True
            number_palette_online.visible = False # Explicitly hide palette
            online_state["selected_cell_coord"] = None # Deselect cells

            if online_state["user_board"]: # User board might not be the solution if they didn't win
                refresh_grid_display_online() # No update
            elif gs.get("puzzle_board"): # Fallback to puzzle if user_board is not set
                 create_sudoku_grid_ui_online(gs.get("puzzle_board")) # Calls refresh (no update)
                 # refresh_grid_display_online() # create_sudoku_grid_ui_online already calls refresh
            else:
                sudoku_grid_container_online.controls.clear()
                sudoku_grid_container_online.controls.append(ft.Text("انتهت اللعبة.", text_align=ft.TextAlign.CENTER))

            winner_name = gs.get("winner", "غير معروف")
            action_area_online.controls.append(ft.Text(f"🏆 الفائز: {winner_name}", size=FONT_SIZE_XLARGE, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_700))
            if is_host:
                action_area_online.controls.append(ft.ElevatedButton("🔄 العب مرة أخرى؟", on_click=lambda e: send_action_fn("RESTART_SUDOKU_GAME"), width=200, height=BUTTON_HEIGHT_NORMAL))

        page.update() # Single update at the end of UI orchestration

    def on_server_message_online_sudoku(*args_received):
        if not page.client_storage: return
        if not args_received or len(args_received) < 2: return
        msg_data = args_received[1]
        if not isinstance(msg_data, dict): return
        msg_type = msg_data.get("type")

        # It's generally safer to fetch the latest room state before updating UI
        # unless the message itself contains the complete new state.
        current_room_full_state = game_rooms_ref.get(room_code, {}) 
        if not current_room_full_state: return # Room might have been removed

        current_gs_from_room = current_room_full_state.get("game_state", {})

        if msg_type == "GAME_STATE_UPDATE":
            room_state_from_msg = msg_data.get("room_state")
            if room_state_from_msg and isinstance(room_state_from_msg, dict) and room_state_from_msg.get("game_type") == "sudoku":
                gs_updated = room_state_from_msg.get("game_state",{})
                if "solution_board" in gs_updated and gs_updated["solution_board"]: # Ensure local state has solution if server sends it
                     online_state["solution_board_from_server"] = gs_updated["solution_board"]
                update_ui_from_server_state_online_sudoku(room_state_from_msg) # This calls page.update()
        elif msg_type == "SUDOKU_SUBMISSION_FEEDBACK":
            if msg_data.get("feedback_for_player") == current_player_name:
                feedback_txt = msg_data.get("feedback_message", "تم استلام الرد.")
                if page.client_storage: # Check client_storage before accessing page.snack_bar
                    page.snack_bar = ft.SnackBar(ft.Text(feedback_txt, text_align=ft.TextAlign.CENTER), open=True)
                    page.update() # Explicit update for snackbar, as update_ui might not be called or might be too late

                # If feedback implies game over, ensure UI reflects it.
                # The GAME_STATE_UPDATE should handle this, but as a fallback:
                if "كان الأسرع" in feedback_txt or \
                   (current_gs_from_room.get("phase") == "GAME_OVER" and "فاز باللعبة" in current_gs_from_room.get("status_message","")):
                    online_state["is_game_over_globally"] = True # Update local flag
                    if page.client_storage: # Re-fetch and update UI if game is over
                        update_ui_from_server_state_online_sudoku(game_rooms_ref.get(room_code, {})) # Calls page.update()
        elif msg_type == "SUDOKU_SOLUTION_UPDATE": # Server sends solution board, e.g., at game start
            solution_board = msg_data.get("solution_board")
            if solution_board:
                online_state["solution_board_from_server"] = solution_board
                # No immediate UI update needed unless this implies game start or other change.
                # The next GAME_STATE_UPDATE or user action will refresh.
                # Or, if this IS the trigger for game start, then update:
                update_ui_from_server_state_online_sudoku(game_rooms_ref.get(room_code, {})) # Calls page.update()


        elif msg_type in ["PLAYER_JOINED", "PLAYER_LEFT"]:
             room_state_from_msg = msg_data.get("room_state") # Assume PLAYER_JOINED/LEFT provides full room_state
             if room_state_from_msg and isinstance(room_state_from_msg, dict) and room_state_from_msg.get("game_type") == "sudoku":
                gs_updated = room_state_from_msg.get("game_state",{})
                if "solution_board" in gs_updated and gs_updated["solution_board"]:
                     online_state["solution_board_from_server"] = gs_updated["solution_board"]
                update_ui_from_server_state_online_sudoku(room_state_from_msg) # Calls page.update()

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
        update_ui_from_server_state_online_sudoku(initial_room_data) # Calls page.update()
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