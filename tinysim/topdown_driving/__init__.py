import json
import math
import numpy as np
from pathlib import Path
from .. import SimEnvironment


try:
    with open(Path(__file__).parent / "track_0.json", "r") as f:
        track = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("Unable to load track data.")


MAX_VEL = 20.0
ACCELERATION = 8.0
VEL_FRICT = 2.0
TURN_SPEED = math.radians(100)

CAR_LENGTH = 1.6  # WORLD units (smaller)
CAR_WIDTH = 0.8
CAR_RADIUS = 0.5

LOCAL_WALLS = track["walls"]
CHECKPOINTS = np.array(track["checkpoints"], dtype=np.float32)
CHECKPOINT_RADIUS = 3.0

WORLD_WALLS = np.array(
    [(x, y, w, h, math.radians(rot)) for x, y, w, h, rot in LOCAL_WALLS],
    dtype=np.float32,
)

W_X, W_Y, W_W, W_H, W_ROT = WORLD_WALLS.T
W_HW = W_W * 0.5
W_HH = W_H * 0.5
W_COS = np.cos(-W_ROT)
W_SIN = np.sin(-W_ROT)

# Precompute ray offsets
RAY_SPREAD = math.radians(75)  # total fan angle
RAY_LENGTH = 12.0  # world units
RAY_COUNT = 5
ray_offsets = np.linspace(
    -RAY_SPREAD * 0.5, RAY_SPREAD * 0.5, RAY_COUNT, dtype=np.float32
)
EPS = 1e-6


def cast_rays(x, y, angle):
    # x,y,angle: (N,)
    a = angle[:, None] + ray_offsets[None, :]  # (N,R)
    dx = np.cos(a)
    dy = np.sin(a)
    best_t = np.full((x.shape[0], RAY_COUNT), RAY_LENGTH, dtype=np.float32)

    # Expand dims for broadcasting
    ox = x[:, None, None]
    oy = y[:, None, None]
    rdx = dx[:, :, None]
    rdy = dy[:, :, None]

    wx = W_X[None, None, :]
    wy = W_Y[None, None, :]

    # transform ray to wall space
    rox = (ox - wx) * W_COS - (oy - wy) * W_SIN
    roy = (ox - wx) * W_SIN + (oy - wy) * W_COS
    rdxl = rdx * W_COS - rdy * W_SIN
    rdyl = rdx * W_SIN + rdy * W_COS

    tmin = np.full_like(rox, -1e9)
    tmax = np.full_like(rox, 1e9)
    mask_x = np.abs(rdxl) > EPS
    safe_rdxl = np.where(mask_x, rdxl, 1.0)
    tx1 = (-W_HW - rox) / safe_rdxl
    tx2 = (W_HW - rox) / safe_rdxl
    tmin = np.where(mask_x, np.maximum(tmin, np.minimum(tx1, tx2)), tmin)
    tmax = np.where(mask_x, np.minimum(tmax, np.maximum(tx1, tx2)), tmax)
    mask_y = np.abs(rdyl) > EPS
    safe_rdyl = np.where(mask_y, rdyl, 1.0)
    ty1 = (-W_HH - roy) / safe_rdyl
    ty2 = (W_HH - roy) / safe_rdyl
    tmin = np.where(mask_y, np.maximum(tmin, np.minimum(ty1, ty2)), tmin)
    tmax = np.where(mask_y, np.minimum(tmax, np.maximum(ty1, ty2)), tmax)
    valid = (tmax >= tmin) & (tmax > 0.0)
    t = np.where(valid, np.where(tmin > 0, tmin, tmax), np.inf)
    best_t = np.minimum(best_t, t.min(axis=2))
    return best_t


def collides(cx, cy):
    dx = cx[:, None] - W_X[None, :]
    dy = cy[:, None] - W_Y[None, :]
    lx = dx * W_COS[None, :] - dy * W_SIN[None, :]
    ly = dx * W_SIN[None, :] + dy * W_COS[None, :]
    px = np.clip(lx, -W_HW[None, :], W_HW[None, :])
    py = np.clip(ly, -W_HH[None, :], W_HH[None, :])
    ddx = lx - px
    ddy = ly - py
    hit = (ddx**2 + ddy**2) <= CAR_RADIUS**2
    return hit.any(axis=1)


class TopDownDrivingEnv(SimEnvironment):
    def __init__(self, num_envs: int = 1):
        self.num_envs = num_envs
        self.reset()

    def reset(self):
        self.x = np.full(self.num_envs, -85.0, dtype=np.float32)
        self.y = np.full(self.num_envs, -42.0, dtype=np.float32)
        self.angle = np.zeros(self.num_envs, dtype=np.float32)
        self.velocity = np.zeros(self.num_envs, dtype=np.float32)
        self.rays = []

        self.checkpoint_idx = np.zeros(self.num_envs, dtype=np.int32)
        cx, cy = CHECKPOINTS[0]
        self.prev_dist = np.hypot(self.x - cx, self.y - cy)
        return {
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "velocity": self.velocity,
            "rays": self.rays,
        }

    def step(self, action, dt=0.02):
        throttle = action.get("throttle", 0.0)
        steer = action.get("steer", 0.0)

        if np.isscalar(throttle) and np.isscalar(steer):
            throttle = np.full(self.num_envs, throttle, dtype=np.float32)
            steer = np.full(self.num_envs, steer, dtype=np.float32)
        elif isinstance(throttle, np.ndarray) and isinstance(steer, np.ndarray):
            throttle = np.asarray(throttle, dtype=np.float32)
            steer = np.asarray(steer, dtype=np.float32)
            if throttle.shape[0] != self.num_envs or steer.shape[0] != self.num_envs:
                raise ValueError(
                    f"Expected actions of shape ({self.num_envs},), got {throttle.shape} and {steer.shape}"
                )
        else:
            raise ValueError(
                "Inputs throttle and steer must both be either scalars or numpy arrays."
            )

        self.velocity += throttle * ACCELERATION * dt
        self.velocity = np.clip(self.velocity, 0.0, MAX_VEL)
        self.angle -= steer * TURN_SPEED * dt

        dx = np.cos(self.angle) * self.velocity * dt
        dy = np.sin(self.angle) * self.velocity * dt
        nx, ny = self.x + dx, self.y + dy

        hit = collides(nx, ny)
        self.x = np.where(hit, self.x, nx)
        self.y = np.where(hit, self.y, ny)
        self.velocity = np.where(hit, 0.0, self.velocity)

        mask = np.abs(throttle) < 1e-3
        self.velocity = np.where(
            mask, np.maximum(0.0, self.velocity - VEL_FRICT * dt), self.velocity
        )
        self.rays = cast_rays(self.x, self.y, self.angle)

        # TODO: should reward be scaled by the distance between checkpoints?
        # return done if the car hits a wall?
        cp = CHECKPOINTS[self.checkpoint_idx]
        dist = np.hypot(self.x - cp[:, 0], self.y - cp[:, 1])

        # Reward is the delta to see if the car is getting closer to the checkpoint
        reward = self.prev_dist - dist
        reached = dist <= CHECKPOINT_RADIUS

        bonus = 1.0
        reward += np.where(reached, bonus, 0.0)
        self.checkpoint_idx = np.where(
            reached, self.checkpoint_idx + 1, self.checkpoint_idx
        )

        cp = CHECKPOINTS[self.checkpoint_idx]
        self.prev_dist = np.hypot(self.x - cp[:, 0], self.y - cp[:, 1])

        return {
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "velocity": self.velocity,
            "rays": self.rays,
            "reward": reward,
        }
