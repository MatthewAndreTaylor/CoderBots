import numpy as np
from .. import SimEnvironment

WIDTH, HEIGHT = 800, 600
GRAVITY = 900.0
FLAP_STRENGTH = -300.0
PIPE_SPEED = -200.0
PIPE_WIDTH = 80
PIPE_GAP = 200
PIPE_INTERVAL = 1.6

BIRD_X = 200
BIRD_SIZE = 35


class FlappyEnv(SimEnvironment):
    def __init__(self, num_envs: int = 1):
        self.num_envs = num_envs
        self.reset()

    def reset(self):
        # birds (vectorized)
        self.bird_y = np.full(self.num_envs, HEIGHT / 2, dtype=np.float32)
        self.bird_vel = np.zeros(self.num_envs, dtype=np.float32)
        self.done = np.zeros(self.num_envs, dtype=bool)

        # shared pipes
        self.pipes_x = np.empty(0, dtype=np.float32)
        self.pipes_y = np.empty(0, dtype=np.float32)
        self.time_since_pipe = PIPE_INTERVAL
        return self.step(np.zeros(self.num_envs, dtype=np.int32), dt=0.0)

    def _step_physics(self, action, dt):
        flap_mask = (action == 1) & (~self.done)
        self.bird_vel[flap_mask] = FLAP_STRENGTH
        self.bird_vel += GRAVITY * dt
        self.bird_y += self.bird_vel * dt

    def _spawn_pipe(self):
        pipe_y = np.random.randint(120, HEIGHT - 120 - PIPE_GAP)
        self.pipes_x = np.append(self.pipes_x, WIDTH)
        self.pipes_y = np.append(self.pipes_y, pipe_y)

    def _update_pipes(self, dt):
        self.time_since_pipe += dt
        if self.time_since_pipe > PIPE_INTERVAL:
            self.time_since_pipe = 0.0
            self._spawn_pipe()

        self.pipes_x += PIPE_SPEED * dt

        # keep pipes on screen
        keep = self.pipes_x > -PIPE_WIDTH
        self.pipes_x = self.pipes_x[keep]
        self.pipes_y = self.pipes_y[keep]

    def _check_collisions(self):  # world bounds
        hit_bounds = (self.bird_y < 0) | (self.bird_y + BIRD_SIZE > HEIGHT)
        bx = BIRD_X
        by = self.bird_y[:, None]
        px = self.pipes_x[None, :]
        upper_y = np.zeros_like(self.pipes_y)[None, :]
        upper_h = self.pipes_y[None, :]
        lower_y = (self.pipes_y + PIPE_GAP)[None, :]
        lower_h = (HEIGHT - (self.pipes_y + PIPE_GAP))[None, :]
        x_overlap = (bx < px + PIPE_WIDTH) & (bx + BIRD_SIZE > px)
        upper_hit = x_overlap & (by < upper_y + upper_h) & (by + BIRD_SIZE > upper_y)
        lower_hit = x_overlap & (by < lower_y + lower_h) & (by + BIRD_SIZE > lower_y)
        hit_pipe = (upper_hit | lower_hit).any(axis=1)
        self.done |= hit_bounds | hit_pipe

    def step(self, action, dt=0.02):
        if np.isscalar(action):
            action = np.full(self.num_envs, action, dtype=np.float32)
        else:
            action = np.asarray(action, dtype=np.float32)
            if action.shape[0] != self.num_envs:
                raise ValueError(
                    f"Expected actions of shape ({self.num_envs},), got {action.shape}"
                )

        # mask done environments to have no action
        action = action * (~self.done)
        self._step_physics(action, dt)
        self._update_pipes(dt)
        self._check_collisions()

        bird_y = self.bird_y.tolist()
        bird_vel = self.bird_vel.tolist()
        done = self.done.tolist()

        if self.num_envs == 1:
            bird_y = self.bird_y[0]
            bird_vel = self.bird_vel[0]
            done = bool(self.done[0])

        return {
            "bird_y": bird_y,
            "bird_vel": bird_vel,
            "pipes_x": self.pipes_x.tolist(),
            "pipes_y": self.pipes_y.tolist(),
            "done": done,
        }
