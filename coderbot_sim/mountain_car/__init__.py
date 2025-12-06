import math
from .. import SimEnvironment


class MountainCarEnv(SimEnvironment):
    def __init__(self):
        # environment constants
        self.min_position = -1.2
        self.max_position = 0.6
        self.max_speed = 0.07
        self.force = 0.001
        self.gravity = 0.0025
        self.goal_position = 0.5

        # initial state
        self.position = -0.5
        self.velocity = 0.0

    def step(self, action: int) -> dict:
        a = int(action)
        force_term = (a - 1) * self.force
        self.velocity += force_term + math.cos(3 * self.position) * (-self.gravity)
        self.velocity = max(min(self.velocity, self.max_speed), -self.max_speed)

        self.position += self.velocity
        self.position = max(min(self.position, self.max_position), self.min_position)
        if self.position == self.min_position and self.velocity < 0:
            self.velocity = 0.0

        return {
            "position": self.position,
            "velocity": self.velocity,
            "done": bool(self.position >= self.goal_position),
        }

    def reset(self) -> dict:
        self.position = -0.5
        self.velocity = 0.0
        return {
            "position": self.position,
            "velocity": self.velocity,
            "done": bool(self.position >= self.goal_position),
        }
