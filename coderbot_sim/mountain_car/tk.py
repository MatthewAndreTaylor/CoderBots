import asyncio
import math
import threading
from . import MountainCarEnv

try:
    import tkinter as tk
except ImportError:
    raise ImportError("tkinter is required for MountainCarTkFrontend")


class MountainCarTkFrontend:
    def __init__(self, viewport_size=(600, 400), sim_env=None):
        if sim_env is None:
            sim_env = MountainCarEnv()
        self.sim_env = sim_env
        self._viewport_size = viewport_size
        self._root = None
        self._canvas = None
        self._last_state = None
        self._started = False

    def render(self):
        """Create Tk window in a new thread, start pump."""
        if self._started:
            return
        self._started = True
        t = threading.Thread(target=self._create_window, daemon=True)
        t.start()

    def bring_to_front(self, root):
        root.lift()
        root.attributes("-topmost", True)
        root.after_idle(root.attributes, "-topmost", False)
        root.focus_force()

    def _create_window(self):
        w, h = self._viewport_size
        root = tk.Tk()
        root.title("Mountain Car")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        canvas = tk.Canvas(root, width=w, height=h, bg="#eeeeee")
        canvas.pack(fill="both", expand=True)
        self.bring_to_front(root)

        self._root = root
        self._canvas = canvas
        state = self.sim_env.reset()
        self._last_state = state
        self._draw_state(state)
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
            self._root.after(0, lambda s=state: self._draw_state(s))

        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        self._last_state = state
        if self._canvas:
            self._draw_state(state)
        return state

    def _draw_state(self, state: dict):
        if not self._canvas:
            return

        c = self._canvas
        w = int(c.winfo_width() or self._viewport_size[0])
        h = int(c.winfo_height() or self._viewport_size[1])
        c.delete("all")

        min_x = self.sim_env.min_position
        max_x = self.sim_env.max_position
        world_width = max_x - min_x
        scale = w / world_width
        clearance = 10

        def heightFn(x):
            return math.sin(3 * x) * 0.45 + 0.55

        terrain_pts = []
        for px in range(w):
            x_world = min_x + px / w * world_width
            y_world = heightFn(x_world)
            y_screen = h - (y_world * scale)
            terrain_pts.append((px, y_screen))

        # terrain
        for i in range(len(terrain_pts) - 1):
            c.create_line(*terrain_pts[i], *terrain_pts[i + 1], fill="#444444", width=2)

        position = state["position"]
        velocity = state["velocity"]
        done = state["done"]

        x_world = position
        y_world = heightFn(x_world)

        x_screen = (x_world - min_x) * scale
        y_screen = h - y_world * scale - clearance

        slope = math.cos(3 * x_world)
        angle = -math.atan(slope)

        car_width, car_height = 40, 20
        wheel_r = car_height * 0.4

        def rot(px, py, ang):
            s, c0 = math.sin(ang), math.cos(ang)
            return px * c0 - py * s, px * s + py * c0

        # body
        body_local = [
            (-car_width / 2, -car_height),
            (car_width / 2, -car_height),
            (car_width / 2, 0),
            (-car_width / 2, 0),
        ]
        body_screen = []
        for px, py in body_local:
            rx, ry = rot(px, py, angle)
            body_screen.append((x_screen + rx, y_screen + ry))

        c.create_polygon(body_screen, fill="#000000", outline="")

        # wheels
        for wx in (-car_width / 3, car_width / 3):
            rx, ry = rot(wx, 0, angle)
            cx = x_screen + rx
            cy = y_screen + ry
            c.create_oval(
                cx - wheel_r,
                cy - wheel_r,
                cx + wheel_r,
                cy + wheel_r,
                fill="#777777",
                outline="",
            )

        gx = self.sim_env.goal_position
        gy = heightFn(gx)
        goal_x = (gx - min_x) * scale
        goal_y = h - gy * scale

        c.create_line(goal_x, goal_y, goal_x, goal_y - 40, fill="#000", width=2)
        c.create_polygon(
            goal_x,
            goal_y - 40,
            goal_x + 25,
            goal_y - 35,
            goal_x,
            goal_y - 30,
            fill="#ffff00",
            outline="",
        )

        c.create_text(
            10,
            10,
            anchor="nw",
            fill="#000",
            text=f"x={x_world:.3f}  v={velocity:.3f}  done={done}",
        )

    async def step(self, action: int, dt: float = 0.01):
        state = self.sim_env.step(action)
        self._last_state = state
        if self._root:
            self._root.after(0, lambda s=state: self._draw_state(s))

        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        self._last_state = state
        if self._canvas:
            self._draw_state(state)
        return state
