import json
import math
import tkinter as tk
from pathlib import Path

with open(Path(__file__).parent / "track_0.json", "r") as f:
    rectangles = json.load(f)

RAY_COUNT = 5
RAY_SPREAD = math.radians(75)  # total fan angle
RAY_LENGTH = 12.0  # world units

WORLD_WALLS = []
xs, ys = [], []

for x, y, w, h, rot in rectangles:
    WORLD_WALLS.append((x, y, w, h, math.radians(rot)))
    r = math.hypot(w, h) * 0.5
    xs.extend([x - r, x + r])
    ys.extend([y - r, y + r])

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)

CANVAS_W, CANVAS_H = 800, 600

scale = min((CANVAS_W - 2) / (max_x - min_x), (CANVAS_H - 2) / (max_y - min_y))

offset_x = -min_x * scale
offset_y = max_y * scale

root = tk.Tk()
canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg="white")
canvas.pack()


def raycast_wall(ox, oy, dx, dy, wx, wy, w, h, rot):
    # transform ray into wall local space
    c = math.cos(-rot)
    s = math.sin(-rot)
    rox = (ox - wx) * c - (oy - wy) * s
    roy = (ox - wx) * s + (oy - wy) * c
    rdx = dx * c - dy * s
    rdy = dx * s + dy * c
    hw = w * 0.5
    hh = h * 0.5
    tmin = -1e9
    tmax = 1e9

    if abs(rdx) > 1e-6:
        tx1 = (-hw - rox) / rdx
        tx2 = (hw - rox) / rdx
        tmin = max(tmin, min(tx1, tx2))
        tmax = min(tmax, max(tx1, tx2))
    else:
        if rox < -hw or rox > hw:
            return None

    if abs(rdy) > 1e-6:
        ty1 = (-hh - roy) / rdy
        ty2 = (hh - roy) / rdy
        tmin = max(tmin, min(ty1, ty2))
        tmax = min(tmax, max(ty1, ty2))
    else:
        if roy < -hh or roy > hh:
            return None

    if tmax >= tmin and tmax > 0:
        return tmin if tmin > 0 else tmax

    return None


def cast_rays(car):
    hits = []

    base = car.angle
    start = base - RAY_SPREAD * 0.5

    for i in range(RAY_COUNT):
        a = start + RAY_SPREAD * i / (RAY_COUNT - 1)
        dx = math.cos(a)
        dy = math.sin(a)
        best_t = RAY_LENGTH

        for wx, wy, w, h, rot in WORLD_WALLS:
            t = raycast_wall(car.x, car.y, dx, dy, wx, wy, w, h, rot)
            if t is not None and t < best_t:
                best_t = t

        hits.append((a, best_t))

    return hits


def draw_rays(car):
    canvas.delete("ray")
    rays = cast_rays(car)

    for angle, dist in rays:
        x2 = car.x + math.cos(angle) * dist
        y2 = car.y + math.sin(angle) * dist
        sx1, sy1 = world_to_screen(car.x, car.y)
        sx2, sy2 = world_to_screen(x2, y2)

        canvas.create_line(sx1, sy1, sx2, sy2, fill="red", width=1, tags="ray")


def world_to_screen(x, y):
    return x * scale + offset_x, -y * scale + offset_y


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


for x, y, w, h, rot in rectangles:
    cx, cy = world_to_screen(x, y)
    pts = rotated_rect(cx, cy, w * scale, h * scale, rot)
    canvas.create_polygon(pts, fill="#cccccc", outline="black")


MAX_VEL = 20.0
ACCELERATION = 8.0
VEL_FRICT = 2.0
TURN_SPEED = math.radians(100)
DT = 1 / 60.0

CAR_LENGTH = 1.6  # WORLD units (smaller)
CAR_WIDTH = 0.8
CAR_RADIUS = 0.5


def collides(cx, cy):
    r = CAR_RADIUS

    for wx, wy, w, h, rot in WORLD_WALLS:
        # transform circle center into wall local space
        dx = cx - wx
        dy = cy - wy
        c = math.cos(-rot)
        s = math.sin(-rot)
        lx = dx * c - dy * s
        ly = dx * s + dy * c
        hw = w * 0.5
        hh = h * 0.5
        px = max(-hw, min(hw, lx))
        py = max(-hh, min(hh, ly))
        ddx = lx - px
        ddy = ly - py
        if ddx * ddx + ddy * ddy <= r * r:
            return True

    return False


class Car:
    def __init__(self, x, y, angle=0.0):
        self.x = x
        self.y = y
        self.angle = angle
        self.velocity = 0.0
        self.throttle = 0.0
        self.steer = 0.0

    def update(self):
        self.velocity += self.throttle * ACCELERATION * DT
        self.velocity = max(0.0, min(self.velocity, MAX_VEL))
        self.angle -= self.steer * TURN_SPEED * DT

        dx = math.cos(self.angle) * self.velocity * DT
        dy = math.sin(self.angle) * self.velocity * DT
        nx, ny = self.x + dx, self.y + dy

        if not collides(nx, ny):
            self.x, self.y = nx, ny
        else:
            self.velocity = 0.0

        # Friction
        if abs(self.throttle) < 1e-3:
            self.velocity = max(0.0, self.velocity - VEL_FRICT * DT)


# Input handling

keys = set()
root.bind("<KeyPress>", lambda e: keys.add(e.keysym))
root.bind("<KeyRelease>", lambda e: keys.discard(e.keysym))


def handle_input(car):
    car.throttle = 0
    car.steer = 0
    if "Up" in keys:
        car.throttle = 1
    if "Down" in keys:
        car.throttle = -1
    if "Left" in keys:
        car.steer = -1
    if "Right" in keys:
        car.steer = 1


def draw_car(car):
    canvas.delete("car")
    cx, cy = world_to_screen(car.x, car.y)
    pts = rotated_rect(
        cx, cy, CAR_LENGTH * scale, CAR_WIDTH * scale, math.degrees(car.angle)
    )
    canvas.create_polygon(pts, fill="blue", outline="black", tags="car")


# starts facing RIGHT
car = Car(x=-85, y=-42, angle=0.0)


def tick():
    handle_input(car)
    car.update()
    draw_car(car)
    draw_rays(car)
    root.after(int(DT * 1000), tick)


tick()
root.mainloop()
