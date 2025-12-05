import asyncio
import threading
from . import FroggerEnv, WIDTH, HEIGHT, CELL, ROWS, COLS

try:
    import tkinter as tk
except ImportError:
    raise ImportError("tkinter is required for FroggerTkFrontend")


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
        state = self.sim_env.step(action, dt=dt)
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
