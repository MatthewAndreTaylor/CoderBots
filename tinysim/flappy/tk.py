import asyncio

try:
    import tkinter as tk
    from .. import _tk_base
except ImportError:
    raise ImportError("tkinter is required for FlappyTkFrontend")

from . import (
    FlappyEnv,
    WIDTH,
    HEIGHT,
    PIPE_WIDTH,
    BIRD_SIZE,
    BIRD_X,
    PIPE_GAP,
)


class FlappyTkFrontend(_tk_base.TkBaseFrontend):

    def __init__(self, viewport_size=(800, 600), sim_env=None):
        super().__init__()
        if sim_env is None:
            sim_env = FlappyEnv()

        self.sim_env = sim_env
        self._viewport_size = viewport_size

    async def step(self, action, dt=0.02):
        state = self.sim_env.step(action, dt=dt)
        if self._root:
            self._root.after(0, lambda: self._draw_state(state))

        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        if self._root:
            self._draw_state(state)
        return state

    def _create_window(self, root):
        w, h = self._viewport_size
        root.title("Flappy Bird")
        canvas = tk.Canvas(root, width=w, height=h, bg="#1E1E1E")
        canvas.pack(fill="both", expand=True)
        self._root = root
        self._canvas = canvas
        self.bring_to_front(root)
        self._draw_state(self.sim_env.reset())
        self._pump()
        root.mainloop()

    def _draw_state(self, state):
        if not self._canvas:
            return

        canvas = self._canvas
        canvas.delete("all")
        canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#70C5CE", outline="")
        canvas.create_rectangle(
            0, HEIGHT - 80, WIDTH, HEIGHT, fill="#DED895", outline=""
        )

        # bird
        by = state["bird_y"]

        if not state.get("done", False):
            canvas.create_oval(
                BIRD_X,
                by,
                BIRD_X + BIRD_SIZE,
                by + BIRD_SIZE,
                fill="#FFD700",
                outline="#000",
            )

        # pipes
        for x, y in zip(state["pipes_x"], state["pipes_y"]):
            # Upper pipe
            canvas.create_rectangle(
                x, 0, x + PIPE_WIDTH, y, fill="#228B22", outline="#4a8d34"
            )
            # Lower pipe
            canvas.create_rectangle(
                x,
                y + PIPE_GAP,
                x + PIPE_WIDTH,
                HEIGHT,
                fill="#228B22",
                outline="#4a8d34",
            )
