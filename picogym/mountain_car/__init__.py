import numpy as np

from .. import SimEnvironment
from ..spaces import Discrete


class MountainCarEnv(SimEnvironment):
    def __init__(self, num_envs: int = 1):
        self.num_envs = num_envs
        # environment constants
        self.min_position = -1.2
        self.max_position = 0.6
        self.max_speed = 0.07
        self.force = 0.001
        self.gravity = 0.0025
        self.goal_position = 0.5
        self.reset()

        # actions: 0 (left), 1 (no push), 2 (right)
        self.action_space = Discrete(3)

    def step(self, action):
        if np.isscalar(action):
            action = np.full(self.num_envs, action, dtype=np.float32)
        else:
            action = np.asarray(action, dtype=np.float32)
            if action.shape[0] != self.num_envs:
                raise ValueError(
                    f"Expected actions of shape ({self.num_envs},), got {action.shape}"
                )

        force_term = (action - 1.0) * self.force
        self.velocity += force_term + np.cos(3 * self.position) * (-self.gravity)
        self.velocity = np.clip(self.velocity, -self.max_speed, self.max_speed)

        self.position += self.velocity
        self.position = np.clip(self.position, self.min_position, self.max_position)

        # handle collision with left wall
        wall_mask = (self.position == self.min_position) & (self.velocity < 0)
        self.velocity[wall_mask] = 0.0
        done = self.position >= self.goal_position

        if self.num_envs == 1:
            self.position = float(self.position[0])
            self.velocity = float(self.velocity[0])
            done = bool(done[0])

        return {"position": self.position, "velocity": self.velocity, "done": done}

    def reset(self, **kwargs) -> dict:
        self.position = np.full(self.num_envs, -0.5, dtype=np.float32)
        self.velocity = np.zeros(self.num_envs, dtype=np.float32)
        done = self.position >= self.goal_position

        if self.num_envs == 1:
            self.position = float(self.position[0])
            self.velocity = float(self.velocity[0])
            done = bool(done[0])

        return {"position": self.position, "velocity": self.velocity, "done": done}
