import asyncio
import math
import numpy as np
from . import MountainCarEnv

try:
    import tkinter as tk
    from .. import _tk_base
except ImportError:
    raise ImportError("tkinter is required for MountainCarTkFrontend")


class MountainCarTkFrontend(_tk_base.TkBaseFrontend):

    def __init__(self, viewport_size=(600, 400), sim_env=None):
        super().__init__()
        if sim_env is None:
            sim_env = MountainCarEnv()
        self.sim_env = sim_env
        self._viewport_size = viewport_size

    async def step(self, action, dt=0.01):
        state = self.sim_env.step(action)

        if self._root:
            self._root.after(0, lambda s=state: self._draw_state(s))

        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        if self._canvas:
            self._draw_state(state)
        return state

    def _create_window(self, root):
        w, h = self._viewport_size
        root.title("Mountain Car")
        canvas = tk.Canvas(root, width=w, height=h, bg="#eeeeee")
        canvas.pack(fill="both", expand=True)
        self.bring_to_front(root)
        self._root = root
        self._canvas = canvas
        self._draw_state(self.sim_env.reset())
        self._pump()
        root.mainloop()

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
            return np.sin(3 * x) * 0.45 + 0.55

        # Terrain
        terrain_pts = []
        for px in range(w):
            x_world = min_x + px / w * world_width
            y_world = heightFn(x_world)
            y_screen = h - y_world * scale
            terrain_pts.append((px, y_screen))
        for i in range(len(terrain_pts) - 1):
            c.create_line(*terrain_pts[i], *terrain_pts[i + 1], fill="#444444", width=2)

        # Goal
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

        # Draw each car
        positions = np.atleast_1d(state["position"])
        car_width, car_height = 40, 20
        wheel_r = car_height * 0.4

        def rot(px, py, ang):
            s, c0 = math.sin(ang), math.cos(ang)
            return px * c0 - py * s, px * s + py * c0

        colors = ["#ff0000", "#00aa00", "#0000ff", "#ffaa00"]

        for i, x_world in enumerate(positions):
            y_world = heightFn(x_world)
            x_screen = (x_world - min_x) * scale
            y_screen = h - y_world * scale - clearance

            slope = math.cos(3 * x_world)
            angle = -math.atan(slope)

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

            c.create_polygon(
                body_screen, fill=colors[i % len(colors)], outline="", stipple="gray75"
            )

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
