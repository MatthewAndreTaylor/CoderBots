import asyncio

WIDTH, HEIGHT = 800, 600
CELL = 40
ROWS, COLS = HEIGHT // CELL, WIDTH // CELL


class Frog:
    def __init__(self):
        self.reset()

    def reset(self):
        self.col = COLS // 2
        self.row = ROWS - 1

    @property
    def rect(self):
        return (self.col * CELL, self.row * CELL, CELL, CELL)

    def move(self, dx, dy):
        self.col = max(0, min(COLS - 1, self.col + dx))
        self.row = max(0, min(ROWS - 1, self.row + dy))


class Car:
    def __init__(self, lane_row, x, speed):
        self.row = lane_row
        self.x = x
        self.speed = speed
        self.width = CELL * 2

    @property
    def rect(self):
        return (
            self.x,
            self.row * CELL + 8,
            self.width,
            CELL - 16,
        )

    def update(self, dt):
        self.x += self.speed * dt

        # wrap around when off screen
        if self.speed > 0 and self.x > WIDTH + 50:
            self.x = -self.width - 50
        elif self.speed < 0 and self.x < -self.width - 50:
            self.x = WIDTH + 50


def make_cars():
    lanes = []
    # pick some rows to be roads
    traffic_rows = [4, 5, 6, 8, 9]
    speeds = [120, -150, 200, -180, 140]  # pixels/second
    for row, speed in zip(traffic_rows, speeds):
        lane = []
        # put 4 cars in each lane
        for i in range(4):
            x = i * (WIDTH // 4)
            lane.append(Car(row, x, speed))
        lanes.append(lane)
    return lanes


def rects_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def build_car_grid(cars_by_lane):
    grid = [[False for _ in range(COLS)] for _ in range(ROWS)]

    for lane in cars_by_lane:
        for car in lane:
            # Car bounding box
            x0 = car.x
            x1 = car.x + car.width

            # Convert pixel ranges → column indices
            col_start = max(0, int(x0 // CELL))
            col_end = min(COLS - 1, int(x1 // CELL))

            # Mark all cells the car overlaps
            r = car.row
            for c in range(col_start, col_end + 1):
                grid[r][c] = True

    return grid


class FroggerEnv:

    def __init__(self):
        self.reset()

    def reset(self):
        self.frog = Frog()
        self.lanes = make_cars()
        self.score = 0.0
        self.crossings = 0
        self.total_height = ROWS - 1

    def _update_score(self):
        """Compute fractional score: crossings + (current height / total height)."""
        current_height = self.total_height - self.frog.row
        frac = current_height / self.total_height
        self.score = self.crossings + frac

    def step(self, action, dt=0.01):
        # action 0: nothing, 1 left, 2 right, 3 up, 4 down
        action_map = {
            0: (0, 0),
            1: (-1, 0),
            2: (1, 0),
            3: (0, -1),
            4: (0, 1),
        }
        dx, dy = action_map.get(action, (0, 0))
        self.frog.move(dx, dy)
        done = False
        frog_rect = self.frog.rect

        for lane in self.lanes:
            for car in lane:
                car.update(dt)
                if rects_overlap(frog_rect, car.rect):
                    done = True

        # Reached the top, reset it and increment crossings
        if self.frog.row == 0:
            self.crossings += 1
            self.frog.reset()

        self._update_score()
        return {
            "frog_pos": (self.frog.col, self.frog.row),
            "grid": build_car_grid(self.lanes),
            "done": done,
            "score": self.score,
        }


import tkinter as tk
import threading


class FroggerTkFrontend:

    def __init__(self, viewport_size=(800, 600), sim_env=None):
        if sim_env is None:
            sim_env = FroggerEnv()
        self.sim_env = sim_env
        self._viewport_size = viewport_size
        self._root = None
        self._canvas = None
        self._last_state = None
        self._thread = None

    def render(self):
        """Create Tk window in a new thread, start pump."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._create_window, daemon=True)
        self._thread.start()

    def bring_to_front(self, root):
        root.lift()
        root.attributes("-topmost", True)
        root.after_idle(root.attributes, "-topmost", False)
        root.focus_force()

    def _create_window(self):
        w, h = self._viewport_size
        root = tk.Tk()
        root.title("Frogger")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        canvas = tk.Canvas(root, width=w, height=h, bg="#1E1E1E")
        canvas.pack(fill="both", expand=True)
        self.bring_to_front(root)

        self._root = root
        self._canvas = canvas
        self._draw_state(self.sim_env)
        self._pump()
        root.mainloop()

    def _on_close(self):
        if self._root:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = None
            self._canvas = None

    def _pump(self):
        if not self._root:
            return

        try:
            self._root.update_idletasks()
            self._root.update()
        except tk.TclError:
            return

        self._root.after(15, self._pump)

    async def step(self, action, dt=0.01):
        state = self.sim_env.step(action)
        self._last_state = state

        if self._root:
            self._root.after(0, lambda: self._draw_state(self.sim_env))

        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        if self._canvas:
            self._draw_state(self.sim_env)
        return state

    def _draw_state(self, sim_env: FroggerEnv):
        if not self._canvas:
            return

        canvas = self._canvas
        canvas.delete("all")

        # safe zones
        canvas.create_rectangle(0, 0, WIDTH, CELL, fill="#000050", outline="")
        canvas.create_rectangle(
            0, (ROWS - 1) * CELL, WIDTH, HEIGHT, fill="#004000", outline=""
        )

        # cars
        for lane in sim_env.lanes:
            for car in lane:
                x, y, w, h = car.rect
                canvas.create_rectangle(x, y, x + w, y + h, fill="#B43232", outline="")

        # frog
        fx, fy, fw, fh = sim_env.frog.rect
        canvas.create_oval(
            fx + 5, fy + 5, fx + fw - 5, fy + fh - 5, fill="#32DC32", outline=""
        )

        # grid
        for r in range(ROWS):
            y = r * CELL
            canvas.create_line(0, y, WIDTH, y, fill="#282828")
        for c in range(COLS):
            x = c * CELL
            canvas.create_line(x, 0, x, HEIGHT, fill="#282828")

        # score
        canvas.create_text(
            10,
            10,
            anchor="nw",
            text=f"Score: {sim_env.score:.2f}",
            fill="white",
            font=("Arial", 16),
        )
