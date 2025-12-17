import json
import math
from pathlib import Path
from .. import SimEnvironment


try:
    with open(Path(__file__).parent / "track_0.json", "r") as f:
        track = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("Unable to load track data.")

RAY_COUNT = 5
RAY_SPREAD = math.radians(75)  # total fan angle
RAY_LENGTH = 12.0  # world units

MAX_VEL = 20.0
ACCELERATION = 8.0
VEL_FRICT = 2.0
TURN_SPEED = math.radians(100)

CAR_LENGTH = 1.6  # WORLD units (smaller)
CAR_WIDTH = 0.8
CAR_RADIUS = 0.5

WORLD_WALLS = []
xs, ys = [], []

LOCAL_WALLS = track["walls"]
CHECKPOINTS = track["checkpoints"]

for x, y, w, h, rot in LOCAL_WALLS:
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

def cast_rays(sim_env):
    hits = []
    base = sim_env.angle
    start = base - RAY_SPREAD * 0.5

    for i in range(RAY_COUNT):
        a = start + RAY_SPREAD * i / (RAY_COUNT - 1)
        dx = math.cos(a)
        dy = math.sin(a)
        best_t = RAY_LENGTH

        for wx, wy, w, h, rot in WORLD_WALLS:
            t = raycast_wall(sim_env.x, sim_env.y, dx, dy, wx, wy, w, h, rot)
            if t is not None and t < best_t:
                best_t = t

        hits.append((a, best_t))

    return hits


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

class TopDownDrivingEnv(SimEnvironment):
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = -85.0
        self.y = -42.0
        self.angle = 0.0
        self.velocity = 0.0
        self.rays = []

    def step(self, action, dt=0.02):
        throttle = action.get("throttle", 0.0)
        steer = action.get("steer", 0.0)

        self.velocity += throttle * ACCELERATION * dt
        self.velocity = max(0.0, min(self.velocity, MAX_VEL))
        self.angle -= steer * TURN_SPEED * dt

        dx = math.cos(self.angle) * self.velocity * dt
        dy = math.sin(self.angle) * self.velocity * dt
        nx, ny = self.x + dx, self.y + dy

        if not collides(nx, ny):
            self.x, self.y = nx, ny
        else:
            self.velocity = 0.0

        # Friction
        if abs(throttle) < 1e-3:
            self.velocity = max(0.0, self.velocity - VEL_FRICT * dt)
            
        self.rays = cast_rays(self)
        reward = 0.0
        
        # TODO: checkpoint logic
        
        return {
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "velocity": self.velocity,
            "rays": self.rays,
            "reward": reward,
        }

