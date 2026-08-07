from . import CELL, COLS, HEIGHT, ROWS, WIDTH, FroggerEnv

try:
    import tkinter as tk

    from .._tk_base import TkBaseFrontend
except ImportError:
    raise ImportError("tkinter is required for FroggerTkFrontend")


class FroggerTkFrontend(TkBaseFrontend):

    def __init__(self, viewport_size=(800, 600), sim_env=FroggerEnv()):
        super().__init__(sim_env)
        self._viewport_size = viewport_size
        self.keys = set()

        if sim_env.num_envs != 1:
            raise ValueError(
                "FroggerTkFrontend currently only supports single environment."
            )

    def _create_window(self, root):
        w, h = self._viewport_size
        root.title("Frogger")
        canvas = tk.Canvas(root, width=w, height=h, bg="#1E1E1E")
        canvas.pack(fill="both", expand=True)
        self._root = root
        self._canvas = canvas

        root.bind("<KeyPress>", lambda e: self.keys.add(e.keysym))
        root.bind("<KeyRelease>", lambda e: self.keys.discard(e.keysym))

        self.bring_to_front(root)
        self._draw_state()
        self._pump()
        root.mainloop()

    def _draw_state(self, state=None):
        sim_env = self.sim_env
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
