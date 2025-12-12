import random

# drawing size
WIDTH, HEIGHT = 800, 600

# Maze grid size
ROWS = 15
COLS = 21

TILE_SIZE = min(WIDTH // COLS, HEIGHT // ROWS)

# Cell types
EMPTY = 0
WALL = 1


def _empty_grid(rows, cols):
    return [[EMPTY for _ in range(cols)] for _ in range(rows)]


def _add_outer_walls(maze):
    rows = len(maze)
    cols = len(maze[0])
    for r in range(rows):
        maze[r][0] = WALL
        maze[r][cols - 1] = WALL
    for c in range(cols):
        maze[0][c] = WALL
        maze[rows - 1][c] = WALL


def _recursive_divide(maze, top, left, bottom, right):
    """Recursive division maze generation."""
    width = right - left
    height = bottom - top

    # Stop if the region is too small to divide further
    if width < 3 or height < 3:
        return

    horizontal = height > width

    if horizontal:
        # Choose a horizontal wall row
        possible_rows = [r for r in range(top + 2, bottom, 2)]
        if not possible_rows:
            return
        wall_row = random.choice(possible_rows)

        for c in range(left + 1, right):
            maze[wall_row][c] = WALL

        gap_col = random.randrange(left + 1, right, 2)
        maze[wall_row][gap_col] = EMPTY

        _recursive_divide(maze, top, left, wall_row, right)
        _recursive_divide(maze, wall_row, left, bottom, right)
    else:
        possible_cols = [c for c in range(left + 2, right, 2)]
        if not possible_cols:
            return
        wall_col = random.choice(possible_cols)

        for r in range(top + 1, bottom):
            maze[r][wall_col] = WALL

        gap_row = random.randrange(top + 1, bottom, 2)
        maze[gap_row][wall_col] = EMPTY

        # Recurse left and right
        _recursive_divide(maze, top, left, bottom, wall_col)
        _recursive_divide(maze, top, wall_col, bottom, right)


def generate_maze(rows=ROWS, cols=COLS):
    """Generate a new maze using recursive division."""
    maze = _empty_grid(rows, cols)
    _add_outer_walls(maze)
    _recursive_divide(maze, 0, 0, rows - 1, cols - 1)
    return maze


class MazeRunnerEnv:
    """Simple random-maze navigation environment.
    0 = up, 1 = right, 2 = down, 3 = left
    """

    def __init__(self, rows=ROWS, cols=COLS):
        self.rows = rows
        self.cols = cols
        self.reset()

    def reset(self):
        self.maze = generate_maze(self.rows, self.cols)
        # Start in top-left open cell inside the border
        self.agent_r, self.agent_c = 1, 1
        if self.maze[self.agent_r][self.agent_c] == WALL:
            self.maze[self.agent_r][self.agent_c] = EMPTY

        self.goal_r, self.goal_c = self.rows - 2, self.cols - 2
        if self.maze[self.goal_r][self.goal_c] == WALL:
            self.maze[self.goal_r][self.goal_c] = EMPTY

        self.steps = 0
        self.done = False
        return self._get_state()

    def _valid(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols and self.maze[r][c] != WALL

    def _get_state(self):
        return {
            "maze": self.maze,
            "agent": {"r": self.agent_r, "c": self.agent_c},
            "goal": {"r": self.goal_r, "c": self.goal_c},
            "done": self.done,
            "steps": self.steps,
            "rows": self.rows,
            "cols": self.cols,
        }

    def step(self, action):
        """Move one step in the maze."""
        if self.done:
            return self._get_state()

        drc = {
            0: (-1, 0),  # up
            1: (0, 1),  # right
            2: (1, 0),  # down
            3: (0, -1),  # left
        }

        dr, dc = drc.get(action, (0, 0))
        nr = self.agent_r + dr
        nc = self.agent_c + dc

        if self._valid(nr, nc):
            self.agent_r, self.agent_c = nr, nc

        self.steps += 1

        if self.agent_r == self.goal_r and self.agent_c == self.goal_c:
            self.done = True

        return self._get_state()
