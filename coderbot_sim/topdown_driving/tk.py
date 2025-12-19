import asyncio
import math
from . import (
    TopDownDrivingEnv,
    CAR_LENGTH,
    CAR_WIDTH,
    LOCAL_WALLS,
    CHECKPOINTS,
    RAY_COUNT,
    RAY_SPREAD,
)

try:
    import tkinter as tk
    from .. import _tk_base
except ImportError:
    raise ImportError("tkinter is required for MountainCarTkFrontend")


CHECKPOINT_RADIUS = 0.85
COLOR_MAP = ["red", "orange", "yellow", "green", "blue", "indigo", "violet"]

xs, ys = [], []

for x, y, w, h, rot in LOCAL_WALLS:
    r = math.hypot(w, h) * 0.5
    xs.extend([x - r, x + r])
    ys.extend([y - r, y + r])


min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)

CANVAS_W, CANVAS_H = 800, 600
scale = min((CANVAS_W - 2) / (max_x - min_x), (CANVAS_H - 2) / (max_y - min_y))
offset_x = -min_x * scale
offset_y = max_y * scale


def rotated_rect(cx, cy, w, h, deg):
    rad = math.radians(-deg)
    c, s = math.cos(rad), math.sin(rad)
    hw, hh = w / 2, h / 2
    pts = []
    for x, y in [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]:
        rx = x * c - y * s
        ry = x * s + y * c
        pts.extend([cx + rx, cy + ry])
    return pts


def world_to_screen(x, y):
    return x * scale + offset_x, -y * scale + offset_y


class TopDownDrivingTkFrontend(_tk_base.TkBaseFrontend):

    def __init__(self, viewport_size=(800, 600), sim_env=None):
        super().__init__()
        if sim_env is None:
            sim_env = TopDownDrivingEnv()
        self.sim_env = sim_env
        self._viewport_size = viewport_size
        self.show_rays = False

        self.keys = set()

    async def step(self, action, dt=0.02):
        state = self.sim_env.step(action)

        if self._root:
            self._root.after(0, lambda s=state: self._draw_state(self.sim_env))

        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        if self._canvas:
            self._draw_state(self.sim_env)
        return state

    def _create_window(self, root):
        w, h = self._viewport_size
        root.title("Top Down Driving")
        canvas = tk.Canvas(root, width=w, height=h, bg="white")
        canvas.pack(expand=True)

        for x, y, w, h, rot in LOCAL_WALLS:
            cx, cy = world_to_screen(x, y)
            pts = rotated_rect(cx, cy, w * scale, h * scale, rot)
            canvas.create_polygon(pts, fill="#cccccc", outline="black")

        r = CHECKPOINT_RADIUS * scale
        for i, (x, y) in enumerate(CHECKPOINTS):
            sx, sy = world_to_screen(x, y)

            canvas.create_oval(
                sx - r,
                sy - r,
                sx + r,
                sy + r,
                fill="green",
                outline="",
                stipple="gray25",
            )
            # add checkpoint number
            canvas.create_text(
                sx, sy, text=str(i + 1), fill="white", font=("Arial", int(r))
            )

        root.bind("<KeyPress>", lambda e: self.keys.add(e.keysym))
        root.bind("<KeyRelease>", lambda e: self.keys.discard(e.keysym))

        self.bring_to_front(root)
        self._root = root
        self._canvas = canvas
        self._draw_state(self.sim_env)
        self._pump()
        root.mainloop()

    def _draw_state(self, sim_env):
        if not self._canvas:
            return

        c = self._canvas
        c.delete("car")
        c.delete("ray")

        xs = sim_env.x
        ys = sim_env.y
        angles = sim_env.angle
        n = len(xs)

        for i in range(n):
            cx, cy = world_to_screen(xs[i], ys[i])

            pts = rotated_rect(
                cx,
                cy,
                CAR_LENGTH * scale,
                CAR_WIDTH * scale,
                math.degrees(angles[i]),
            )
            c.create_polygon(
                pts,
                fill=COLOR_MAP[i % len(COLOR_MAP)],
                outline="black",
                tags="car",
            )

        if not self.show_rays:
            return

        ray_offsets = [
            -RAY_SPREAD * 0.5 + RAY_SPREAD * i / (RAY_COUNT - 1)
            for i in range(RAY_COUNT)
        ]

        for i in range(n):
            ox, oy = xs[i], ys[i]
            base = angles[i]

            sx1, sy1 = world_to_screen(ox, oy)

            for r_idx, dist in enumerate(sim_env.rays[i]):
                a = base + ray_offsets[r_idx]
                x2 = ox + math.cos(a) * dist
                y2 = oy + math.sin(a) * dist
                sx2, sy2 = world_to_screen(x2, y2)

                c.create_line(
                    sx1,
                    sy1,
                    sx2,
                    sy2,
                    fill="red",
                    width=1,
                    tags="ray",
                )
