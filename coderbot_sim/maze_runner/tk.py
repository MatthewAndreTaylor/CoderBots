import asyncio
import threading

try:
    import tkinter as tk
except ImportError:
    raise ImportError("tkinter is required for MazeRunnerTkFrontend")

from . import MazeRunnerEnv, WIDTH, HEIGHT, ROWS, COLS, WALL


class MazeRunnerTkFrontend:
    def __init__(self, viewport_size=(800, 600), sim_env=None):
        if sim_env is None:
            sim_env = MazeRunnerEnv()

        self.sim_env = sim_env
        self._viewport_size = viewport_size
        self._root = None
        self._canvas = None
        self._thread = None
        self._last_state = None

    def render(self):
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
        root.title("MazeRunner")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        canvas = tk.Canvas(root, width=w, height=h, bg="#111827")
        canvas.pack(fill="both", expand=True)
        self._root = root
        self._canvas = canvas
        self.bring_to_front(root)
        self._draw_state(self.sim_env._get_state())

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

        self._root.after(20, self._pump)

    async def step(self, action, dt=0.02):
        state = self.sim_env.step(action, dt=dt)
        self._last_state = state

        if self._root:
            self._root.after(0, lambda: self._draw_state(state))

        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        if self._root:
            self._draw_state(state)
        return state

    def _draw_state(self, state):
        if not self._canvas:
            return

        canvas = self._canvas
        canvas.delete("all")

        w = int(canvas.winfo_width())
        h = int(canvas.winfo_height())

        rows = state["rows"]
        cols = state["cols"]
        maze = state["maze"]
        agent = state["agent"]
        goal = state["goal"]

        cell_w = w / cols
        cell_h = h / rows

        # Background
        canvas.create_rectangle(0, 0, w, h, fill="#111827", outline="")

        # Walls
        for r in range(rows):
            for c in range(cols):
                if maze[r][c] == WALL:
                    x0 = c * cell_w
                    y0 = r * cell_h
                    x1 = x0 + cell_w
                    y1 = y0 + cell_h
                    canvas.create_rectangle(
                        x0, y0, x1, y1, fill="#4B5563", outline="#1F2933"
                    )

        # Goal
        gx = goal["c"] * cell_w
        gy = goal["r"] * cell_h
        canvas.create_rectangle(
            gx + cell_w * 0.15,
            gy + cell_h * 0.15,
            gx + cell_w * 0.85,
            gy + cell_h * 0.85,
            fill="#22C55E",
            outline="",
        )

        # Agent
        ax = agent["c"] * cell_w
        ay = agent["r"] * cell_h
        canvas.create_oval(
            ax + cell_w * 0.2,
            ay + cell_h * 0.2,
            ax + cell_w * 0.8,
            ay + cell_h * 0.8,
            fill="#FACC15",
            outline="#000000",
        )

        # Steps text
        canvas.create_text(
            10,
            10,
            text=f"Steps: {state['steps']}",
            anchor="nw",
            fill="white",
            font=("Arial", 14, "bold"),
        )
