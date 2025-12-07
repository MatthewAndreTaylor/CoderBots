import asyncio
import threading

try:
    import tkinter as tk
except ImportError:
    raise ImportError("tkinter is required for FlappyTkFrontend")

from . import FlappyEnv, WIDTH, HEIGHT, PIPE_WIDTH, PIPE_HEIGHT, BIRD_SIZE, BIRD_X


class FlappyTkFrontend:

    def __init__(self, viewport_size=(800, 600), sim_env=None):
        if sim_env is None:
            sim_env = FlappyEnv()

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
        root.title("Flappy Bird")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        canvas = tk.Canvas(root, width=w, height=h, bg="#1E1E1E")
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
        canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#70C5CE", outline="")
        canvas.create_rectangle(
            0, HEIGHT - 80, WIDTH, HEIGHT, fill="#DED895", outline=""
        )

        # bird
        by = state["bird_y"]
        canvas.create_oval(
            BIRD_X,
            by,
            BIRD_X + BIRD_SIZE,
            by + BIRD_SIZE,
            fill="#FFD700",
            outline="#000",
        )

        # pipes
        for pair in state["pipes"]:
            upper = pair[0]
            lower = pair[1]

            ux = upper["x"]
            uy = upper["y"]
            lx = lower["x"]
            ly = lower["y"]

            # upper pipe
            canvas.create_rectangle(
                ux,
                uy,
                ux + PIPE_WIDTH,
                uy + PIPE_HEIGHT,
                fill="#7EC850",
                outline="#4a8d34",
            )

            # lower pipe
            canvas.create_rectangle(
                lx,
                ly,
                lx + PIPE_WIDTH,
                ly + PIPE_HEIGHT,
                fill="#7EC850",
                outline="#4a8d34",
            )

        # score
        canvas.create_text(
            WIDTH // 2,
            30,
            text=f"{state['score']}",
            fill="white",
            font=("Arial", 32, "bold"),
        )
