# sudoku_utils.py
import random

class SudokuGenerator:
    def __init__(self, size=9):
        self.size = size
        self.grid = [[0 for _ in range(size)] for _ in range(size)]
        self.sqrt_size = int(size**0.5)

    def _is_safe(self, grid, row, col, num): # Added grid parameter
        # Check row
        if num in grid[row]:
            return False
        # Check col
        if num in [grid[i][col] for i in range(self.size)]:
            return False
        # Check 3x3 box
        start_row, start_col = row - row % self.sqrt_size, col - col % self.sqrt_size
        for i in range(self.sqrt_size):
            for j in range(self.sqrt_size):
                if grid[i + start_row][j + start_col] == num:
                    return False
        return True

    def _fill_grid_recursive(self, grid_ref): # Works on a reference to the grid
        for r in range(self.size):
            for c in range(self.size):
                if grid_ref[r][c] == 0:
                    nums = list(range(1, self.size + 1))
                    random.shuffle(nums)
                    for num in nums:
                        if self._is_safe(grid_ref, r, c, num):
                            grid_ref[r][c] = num
                            if self._fill_grid_recursive(grid_ref): # Recurse
                                return True
                            grid_ref[r][c] = 0 # Backtrack
                    return False # No valid number found
        return True # Grid is filled

    def generate_filled_grid(self):
        new_grid = [[0 for _ in range(self.size)] for _ in range(self.size)]
        self._fill_grid_recursive(new_grid)
        return new_grid

    def _count_solutions_recursive(self, board_to_solve):
        for r in range(self.size):
            for c in range(self.size):
                if board_to_solve[r][c] == 0:
                    count = 0
                    for num in range(1, self.size + 1):
                        if self._is_safe(board_to_solve, r, c, num):
                            board_to_solve[r][c] = num
                            count += self._count_solutions_recursive(board_to_solve)
                            board_to_solve[r][c] = 0 # Backtrack
                            if count > 1: # Optimization
                                return count
                    return count
        return 1 # A solution is found

    def _has_unique_solution(self, puzzle_board):
        board_copy = copy_board(puzzle_board)
        return self._count_solutions_recursive(board_copy) == 1

    def generate_puzzle(self, difficulty="normal"):
        solution = self.generate_filled_grid()
        puzzle = copy_board(solution)

        if difficulty == "easy":
            holes = 35 # Adjust as needed
        elif difficulty == "hard":
            holes = 55 # Adjust as needed
        else: # normal
            holes = 45 # Adjust as needed
        
        # Ensure minimum clues (e.g., 17 is a common theoretical minimum for unique solution)
        max_possible_holes = self.size * self.size - 17 
        holes_to_make = min(holes, max_possible_holes)
        
        cells_removed = 0
        all_cells = [(r, c) for r in range(self.size) for c in range(self.size)]
        random.shuffle(all_cells)

        for r, c in all_cells:
            if cells_removed >= holes_to_make:
                break
            
            if puzzle[r][c] != 0:
                temp_val = puzzle[r][c]
                puzzle[r][c] = 0
                
                # Check for unique solution after removing. This can be slow.
                # For a faster, "good enough" puzzle, you might skip this or use a heuristic.
                if not self._has_unique_solution(puzzle):
                    puzzle[r][c] = temp_val # Put it back if it breaks unique solution
                else:
                    cells_removed += 1
        
        # If not enough holes were made because of unique solution constraint,
        # try a simpler poking method (less guarantee of perfect difficulty/uniqueness)
        if cells_removed < holes_to_make:
            # Fallback: just poke holes until desired count without strict unique check on each poke
            current_holes = cells_removed
            random.shuffle(all_cells) # Re-shuffle
            for r_f, c_f in all_cells:
                if current_holes >= holes_to_make:
                    break
                if puzzle[r_f][c_f] != 0:
                    puzzle[r_f][c_f] = 0
                    current_holes +=1
                    
        return puzzle, solution

def get_sudoku_puzzle(difficulty: str = "normal"):
    generator = SudokuGenerator()
    return generator.generate_puzzle(difficulty)

def is_board_full(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0 or not isinstance(board[r][c], int) or not (1 <= board[r][c] <= 9) : # Also check type
                return False
    return True

def validate_board_rules_and_get_conflicts(board):
    conflicting_cells = set()
    is_valid = True

    for r_idx in range(9):
        row_values = {} # val: [col_indices]
        for c_idx in range(9):
            val = board[r_idx][c_idx]
            if val != 0 and isinstance(val, int) and 1 <= val <= 9:
                if val in row_values:
                    is_valid = False
                    conflicting_cells.add((r_idx, c_idx))
                    for prev_c in row_values[val]:
                        conflicting_cells.add((r_idx, prev_c))
                    row_values[val].append(c_idx)
                else:
                    row_values[val] = [c_idx]

    for c_idx in range(9):
        col_values = {} # val: [row_indices]
        for r_idx in range(9):
            val = board[r_idx][c_idx]
            if val != 0 and isinstance(val, int) and 1 <= val <= 9:
                if val in col_values:
                    is_valid = False
                    conflicting_cells.add((r_idx, c_idx))
                    for prev_r in col_values[val]:
                        conflicting_cells.add((prev_r, c_idx))
                    col_values[val].append(r_idx)
                else:
                    col_values[val] = [r_idx]

    for box_r_start in range(0, 9, 3):
        for box_c_start in range(0, 9, 3):
            box_values = {} # val: [(r,c) coords]
            for r_offset in range(3):
                for c_offset in range(3):
                    r_idx, c_idx = box_r_start + r_offset, box_c_start + c_offset
                    val = board[r_idx][c_idx]
                    if val != 0 and isinstance(val, int) and 1 <= val <= 9:
                        if val in box_values:
                            is_valid = False
                            conflicting_cells.add((r_idx, c_idx))
                            for prev_r_s, prev_c_s in box_values[val]:
                                conflicting_cells.add((prev_r_s, prev_c_s))
                            box_values[val].append((r_idx, c_idx))
                        else:
                            box_values[val] = [(r_idx, c_idx)]
    return is_valid, conflicting_cells

def check_solution_correctness(user_board, solution_board):
    if not is_board_full(user_board):
        # Even if not full, check existing numbers for conflicts
        _, rule_conflicts = validate_board_rules_and_get_conflicts(user_board)
        return False, rule_conflicts # Not full

    is_valid_rules, conflicting_cells = validate_board_rules_and_get_conflicts(user_board)
    if not is_valid_rules:
        return False, conflicting_cells

    if solution_board: # If a specific solution is expected (as with our generator)
        for r in range(9):
            for c in range(9):
                if user_board[r][c] != solution_board[r][c]:
                    # The board is valid by rules, but not THE solution.
                    # It's hard to say *which* cell is "wrong" if it's a different valid Sudoku.
                    # For a game context, this is an incorrect submission.
                    # We can return the rule_conflicts found so far (which should be empty if it got here)
                    return False, conflicting_cells # Valid but not THE solution
    
    return True, set() # Correct and matches solution (if provided)

def copy_board(board):
    if not board: return None
    return [row[:] for row in board]