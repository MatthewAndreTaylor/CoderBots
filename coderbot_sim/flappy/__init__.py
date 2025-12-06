import random

WIDTH, HEIGHT = 800, 600

GRAVITY = 900
FLAP_STRENGTH = -300
PIPE_SPEED = -200
PIPE_WIDTH = 80
PIPE_HEIGHT = 320
PIPE_GAP = 200
PIPE_INTERVAL = 1.6

BIRD_X = 200
BIRD_SIZE = 35


def getRandomPipe():
    """Return a new pipe pair (upper, lower)."""
    gapY = random.randint(120, HEIGHT - 120 - PIPE_GAP)
    pipeX = WIDTH + 10

    return [
        {"x": pipeX, "y": gapY - PIPE_HEIGHT},
        {"x": pipeX, "y": gapY + PIPE_GAP},
    ]



def rects_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


class FlappyEnv:

    def __init__(self):
        self.reset()

    def reset(self):
        self.bird_y = HEIGHT // 2
        self.bird_vel = 0
        self.score = 0
        self.done = False
        self.pipes = []
        self.time_since_pipe = 0

        return self._get_state()

    def _get_bird_rect(self):
        return (BIRD_X, self.bird_y, BIRD_SIZE, BIRD_SIZE)

    def _pipe_rects(self, pipe_pair):
        upper = pipe_pair[0]
        lower = pipe_pair[1]
        return [
            (upper["x"], upper["y"], PIPE_WIDTH, PIPE_HEIGHT),
            (lower["x"], lower["y"], PIPE_WIDTH, PIPE_HEIGHT),
        ]

    def _step_physics(self, action, dt):
        # action: 0 = do nothing, 1 = flap
        if action == 1:
            self.bird_vel = FLAP_STRENGTH

        self.bird_vel += GRAVITY * dt
        self.bird_y += self.bird_vel * dt

    def _update_pipes(self, dt):
        self.time_since_pipe += dt

        if self.time_since_pipe > PIPE_INTERVAL:
            self.time_since_pipe = 0
            self.pipes.append(getRandomPipe())

        for pair in self.pipes:
            pair[0]["x"] += PIPE_SPEED * dt
            pair[1]["x"] += PIPE_SPEED * dt

        self.pipes = [p for p in self.pipes if p[0]["x"] > -PIPE_WIDTH]

    def _check_collisions(self):
        bird = self._get_bird_rect()

        # ground or ceiling
        if self.bird_y < 0 or self.bird_y + BIRD_SIZE > HEIGHT:
            return True

        # pipes
        for pair in self.pipes:
            for rect in self._pipe_rects(pair):
                if rects_overlap(bird, rect):
                    return True

        return False

    def _update_score(self):
        for pair in self.pipes:
            pipe_center_x = pair[0]["x"] + PIPE_WIDTH / 2
            if "scored" not in pair and pipe_center_x < BIRD_X:
                pair.append("scored")
                self.score += 1

    def _get_state(self):
        return {
            "bird_y": self.bird_y,
            "bird_vel": self.bird_vel,
            "pipes": self.pipes,
            "done": self.done,
            "score": self.score,
        }

    def step(self, action, dt=0.02):
        # stop simulation on game over
        if self.done:
            return self._get_state()

        self._step_physics(action, dt)
        self._update_pipes(dt)

        if self._check_collisions():
            self.done = True

        self._update_score()
        return self._get_state()
