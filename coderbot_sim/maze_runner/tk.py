import asyncio
import threading
import tkinter as tk
from . import MazeRunnerEnv, TILE_SIZE, WALL, EMPTY


class MazeRunnerTkFrontend:
    """
    Tkinter frontend for MazeRunner.
    Matches style of FlappyTkFrontend / FroggerTkFrontend.
    """

    def __init__(self, viewport_size=None, sim_env=None):
        self.sim_env = sim_env or MazeRunnerEnv()
        self.sim_env.reset()

        self.rows = self.sim_env.rows
        self.cols = self.sim_env.cols
        self.cell_size = TILE_SIZE

        w = self.cols * self.cell_size
        h = self.rows * self.cell_size
        self.viewport_size = (w, h)

        self._root = None
        self._canvas = None
        self._thread = None


    def render(self):
        """Create Tk window in a background thread."""
        if self._thread:
            return
        self._thread = threading.Thread(target=self._create_window, daemon=True)
        self._thread.start()


    def _create_window(self):
        """Builds the Tk window."""
        w, h = self.viewport_size

        root = tk.Tk()
        root.title("MazeRunner")
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        canvas = tk.Canvas(root, width=w, height=h, bg="#0d1117")
        canvas.pack(fill="both", expand=True)

        self._root = root
        self._canvas = canvas

        # Initial draw
        self._draw_state()

        # Start update loop
        self._pump()

        root.mainloop()


    def _pump(self):
        """Keeps the Tk window alive and refreshing."""
        if not self._root:
            return

        try:
            self._root.update_idletasks()
            self._root.update()
        except tk.TclError:
            return

        # Schedule next update
        self._root.after(30, self._pump)


    def _on_close(self):
        """Handle window close."""
        if self._root:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
        self._root = None
        self._canvas = None


    async def step(self, action, dt=0.02):
        """Async step, same as anywidget version."""
        state = self.sim_env.step(action)
        if self._canvas:
            self._root.after(0, self._draw_state)
        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        if self._canvas:
            self._draw_state()
        return state


    def _draw_state(self):
        """Draw maze + agent + goal."""
        if not self._canvas:
            return

        canvas = self._canvas
        canvas.delete("all")
        maze = self.sim_env.maze

        # Draw maze grid
        for r in range(self.rows):
            for c in range(self.cols):
                x1 = c * self.cell_size
                y1 = r * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                color = "#161b22" if maze[r][c] == WALL else "#21262d"
                canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

        # Draw agent
        agent = self.sim_env.agent_r, self.sim_env.agent_c
        r, c = agent
        ax1 = c * self.cell_size + self.cell_size // 4
        ay1 = r * self.cell_size + self.cell_size // 4
        ax2 = ax1 + self.cell_size // 2
        ay2 = ay1 + self.cell_size // 2
        canvas.create_oval(ax1, ay1, ax2, ay2, fill="yellow", outline="")

        # Draw goal
        gr, gc = self.sim_env.goal_r, self.sim_env.goal_c
        gx1 = gc * self.cell_size + self.cell_size // 4
        gy1 = gr * self.cell_size + self.cell_size // 4
        gx2 = gx1 + self.cell_size // 2
        gy2 = gy1 + self.cell_size // 2
        canvas.create_oval(gx1, gy1, gx2, gy2, fill="red", outline="")
