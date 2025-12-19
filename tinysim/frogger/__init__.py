import numpy as np
from .. import SimEnvironment

WIDTH, HEIGHT = 800, 600
CELL = 40
ROWS, COLS = HEIGHT // CELL, WIDTH // CELL


class FroggerEnv(SimEnvironment):
    def __init__(self, num_envs=1):
        self.num_envs = num_envs
        self.total_height = ROWS - 1
        self.num_cars_per_lane = 4
        self.car_width = CELL * 2
        self.traffic_rows = np.array([4, 5, 6, 8, 9])
        self.speeds = np.array([120, -150, 200, -180, 140], dtype=np.float32)
        self.reset()

    def reset(self):
        # Frog positions for all environments (num_envs, 2)
        self.frog_pos = np.tile(np.array([COLS // 2, ROWS - 1]), (self.num_envs, 1))

        # Cars (num_lanes, num_cars_per_lane)
        self.car_x = np.zeros(
            (len(self.traffic_rows), self.num_cars_per_lane), dtype=np.float32
        )
        for i in range(self.num_cars_per_lane):
            self.car_x[:, i] = i * (WIDTH // self.num_cars_per_lane)

        # Score and crossings per environment
        self.crossings = np.zeros(self.num_envs, dtype=np.float32)
        self.score = np.zeros(self.num_envs, dtype=np.float32)
        return self.step(np.zeros(self.num_envs, dtype=np.int32), dt=0.0)

    def _build_car_grid(self):
        grid = np.zeros((ROWS, COLS), dtype=bool)
        for lane_idx, row in enumerate(self.traffic_rows):
            x0 = self.car_x[lane_idx, :]
            x1 = x0 + self.car_width
            col_start = np.clip((x0 // CELL).astype(int), 0, COLS - 1)
            col_end = np.clip((x1 // CELL).astype(int), 0, COLS - 1)
            for start, end in zip(col_start, col_end):
                grid[row, start : end + 1] = True
        return grid

    def step(self, action, dt=0.01):
        if np.isscalar(action):
            action = np.full(self.num_envs, action, dtype=np.float32)
        else:
            action = np.asarray(action, dtype=np.float32)
            if action.shape[0] != self.num_envs:
                raise ValueError(
                    f"Expected actions of shape ({self.num_envs},), got {action.shape}"
                )
        action_map = {
            0: (0, 0),
            1: (-1, 0),
            2: (1, 0),
            3: (0, -1),
            4: (0, 1),
        }
        dx = np.array([action_map[a][0] for a in action])
        dy = np.array([action_map[a][1] for a in action])

        # Move frogs
        self.frog_pos[:, 0] = np.clip(self.frog_pos[:, 0] + dx, 0, COLS - 1)
        self.frog_pos[:, 1] = np.clip(self.frog_pos[:, 1] + dy, 0, ROWS - 1)

        # Update car positions
        self.car_x += self.speeds[:, None] * dt

        # Wrap cars
        pos_mask_pos = self.speeds[:, None] > 0
        pos_mask_neg = self.speeds[:, None] < 0
        self.car_x[pos_mask_pos & (self.car_x > WIDTH + 50)] = -self.car_width - 50
        self.car_x[pos_mask_neg & (self.car_x < -self.car_width - 50)] = WIDTH + 50

        done = np.zeros(self.num_envs, dtype=bool)
        frog_rects = np.stack(
            [
                self.frog_pos[:, 0] * CELL,
                self.frog_pos[:, 1] * CELL,
                np.full(self.num_envs, CELL),
                np.full(self.num_envs, CELL),
            ],
            axis=1,
        )

        self.car_rects = []
        for lane_idx, row in enumerate(self.traffic_rows):
            self.car_rects.append(
                np.stack(
                    [
                        self.car_x[lane_idx, :],  # x positions
                        np.full(self.num_cars_per_lane, row * CELL + 8),  # y positions
                        np.full(self.num_cars_per_lane, self.car_width),  # widths
                        np.full(self.num_cars_per_lane, CELL - 16),  # heights
                    ],
                    axis=1,
                )
            )  # shape: (num_cars_per_lane, 4)

        for env_idx in range(self.num_envs):
            ax, ay, aw, ah = frog_rects[env_idx]
            collision = False
            for car_rects in self.car_rects:
                bx, by, bw, bh = (
                    car_rects[:, 0],
                    car_rects[:, 1],
                    car_rects[:, 2],
                    car_rects[:, 3],
                )
                overlap = (
                    (ax < bx + bw) & (ax + aw > bx) & (ay < by + bh) & (ay + ah > by)
                )
                if np.any(overlap):
                    collision = True
                    break
            done[env_idx] = collision

        # Handle frogs that reached the top
        reached_top = self.frog_pos[:, 1] == 0
        self.crossings[reached_top] += 1
        self.frog_pos[reached_top] = [COLS // 2, ROWS - 1]

        # Update score
        current_height = self.total_height - self.frog_pos[:, 1]
        self.score = self.crossings + current_height / self.total_height

        frog_pos = self.frog_pos.tolist()
        grid = self._build_car_grid().tolist()
        scores = self.score.tolist()
        done = done.tolist()

        if self.num_envs == 1:
            frog_pos = frog_pos[0]
            done = done[0]
            scores = scores[0]

        return {
            "frog_pos": frog_pos,
            "grid": grid,
            "done": done,
            "score": scores,
        }
