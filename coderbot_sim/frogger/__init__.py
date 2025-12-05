WIDTH, HEIGHT = 800, 600
CELL = 40
ROWS, COLS = HEIGHT // CELL, WIDTH // CELL


class Frog:
    def __init__(self):
        self.reset()

    def reset(self):
        self.col = COLS // 2
        self.row = ROWS - 1

    @property
    def rect(self):
        return (self.col * CELL, self.row * CELL, CELL, CELL)

    def move(self, dx, dy):
        self.col = max(0, min(COLS - 1, self.col + dx))
        self.row = max(0, min(ROWS - 1, self.row + dy))


class Car:
    def __init__(self, lane_row, x, speed):
        self.row = lane_row
        self.x = x
        self.speed = speed
        self.width = CELL * 2

    @property
    def rect(self):
        return (
            self.x,
            self.row * CELL + 8,
            self.width,
            CELL - 16,
        )

    def update(self, dt):
        self.x += self.speed * dt

        # wrap around when off screen
        if self.speed > 0 and self.x > WIDTH + 50:
            self.x = -self.width - 50
        elif self.speed < 0 and self.x < -self.width - 50:
            self.x = WIDTH + 50


def make_cars():
    lanes = []
    # pick some rows to be roads
    traffic_rows = [4, 5, 6, 8, 9]
    speeds = [120, -150, 200, -180, 140]  # pixels/second
    for row, speed in zip(traffic_rows, speeds):
        lane = []
        # put 4 cars in each lane
        for i in range(4):
            x = i * (WIDTH // 4)
            lane.append(Car(row, x, speed))
        lanes.append(lane)
    return lanes


def rects_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def build_car_grid(cars_by_lane):
    grid = [[False for _ in range(COLS)] for _ in range(ROWS)]

    for lane in cars_by_lane:
        for car in lane:
            # Car bounding box
            x0 = car.x
            x1 = car.x + car.width

            # Convert pixel ranges → column indices
            col_start = max(0, int(x0 // CELL))
            col_end = min(COLS - 1, int(x1 // CELL))

            # Mark all cells the car overlaps
            r = car.row
            for c in range(col_start, col_end + 1):
                grid[r][c] = True

    return grid


class FroggerEnv:

    def __init__(self):
        self.reset()

    def reset(self):
        self.frog = Frog()
        self.lanes = make_cars()
        self.score = 0.0
        self.crossings = 0
        self.total_height = ROWS - 1

    def _update_score(self):
        """Compute fractional score: crossings + (current height / total height)."""
        current_height = self.total_height - self.frog.row
        frac = current_height / self.total_height
        self.score = self.crossings + frac

    def step(self, action, dt=0.01):
        # action 0: nothing, 1 left, 2 right, 3 up, 4 down
        action_map = {
            0: (0, 0),
            1: (-1, 0),
            2: (1, 0),
            3: (0, -1),
            4: (0, 1),
        }
        dx, dy = action_map.get(action, (0, 0))
        self.frog.move(dx, dy)
        done = False
        frog_rect = self.frog.rect

        for lane in self.lanes:
            for car in lane:
                car.update(dt)
                if rects_overlap(frog_rect, car.rect):
                    done = True

        # Reached the top, reset it and increment crossings
        if self.frog.row == 0:
            self.crossings += 1
            self.frog.reset()

        self._update_score()
        return {
            "frog_pos": (self.frog.col, self.frog.row),
            "grid": build_car_grid(self.lanes),
            "done": done,
            "score": self.score,
        }
