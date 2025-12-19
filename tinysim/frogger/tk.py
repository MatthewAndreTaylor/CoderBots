import asyncio
from . import FroggerEnv, WIDTH, HEIGHT, CELL, ROWS, COLS

try:
    import tkinter as tk
    from .. import _tk_base
except ImportError:
    raise ImportError("tkinter is required for FroggerTkFrontend")


class FroggerTkFrontend(_tk_base.TkBaseFrontend):

    def __init__(self, viewport_size=(800, 600), sim_env=None):
        super().__init__()
        if sim_env is None:
            sim_env = FroggerEnv()
        if sim_env.num_envs != 1:
            raise ValueError(
                "FroggerTkFrontend currently only supports single environment."
            )
        self.sim_env = sim_env
        self._viewport_size = viewport_size

    async def step(self, action, dt=0.01):
        state = self.sim_env.step(action, dt=dt)
        if self._root:
            self._root.after(0, lambda: self._draw_state(self.sim_env))

        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        if self._canvas:
            self._draw_state(self.sim_env)
        return state

    def _create_window(self, root):
        w, h = self._viewport_size
        root.title("Frogger")
        canvas = tk.Canvas(root, width=w, height=h, bg="#1E1E1E")
        canvas.pack(fill="both", expand=True)
        self._root = root
        self._canvas = canvas
        self.bring_to_front(root)
        self._draw_state(self.sim_env)
        self._pump()
        root.mainloop()

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
        for lane_rects in sim_env.car_rects:  # lane_rects shape: (num_cars_per_lane, 4)
            for x, y, w, h in lane_rects:
                canvas.create_rectangle(x, y, x + w, y + h, fill="#B43232", outline="")

        # frog
        fx, fy, fw, fh = (
            sim_env.frog_pos[0, 0] * CELL,
            sim_env.frog_pos[0, 1] * CELL,
            CELL,
            CELL,
        )
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
            text=f"Score: {sim_env.score[0]:.2f}",
            fill="white",
            font=("Arial", 16),
        )
