import math

MAX_DIST = 10.0
MIN_DIST = 0.01

# TODO : Replace with proper map loading
WALLS = [
    (0, 0, 20, 0.5),
    (0, 0, 0.5, 20),
    (0, 19.5, 20, 20),
    (19.5, 0, 20, 20),
    (5, 5, 15, 5.5),
    (5, 5, 5.5, 15),
    (5, 14.5, 15, 15),
    (14.5, 5, 15, 15),
    (8, 8, 12, 8.5),
    (8, 8, 8.5, 12),
    (8, 11.5, 12, 12),
    (11.5, 8, 12, 12),
]



def ray_aabb(px, py, dx, dy, box):
    xmin, ymin, xmax, ymax = box
    tmin, tmax = -1e9, 1e9
    for p, d, mn, mx in ((px, dx, xmin, xmax), (py, dy, ymin, ymax)):
        if abs(d) < 1e-9:
            if p < mn or p > mx:
                return None
        else:
            t1, t2 = (mn - p) / d, (mx - p) / d
            tmin, tmax = max(tmin, min(t1, t2)), min(tmax, max(t1, t2))
            if tmin > tmax:
                return None
    return tmin if tmin > 0 else None

class Car:
    def __init__(self, x=10, y=10, angle=0.0):
        self.x, self.y, self.angle = x, y, angle
        self.sensors = [-math.pi/4, -math.pi/8, 0, math.pi/8, math.pi/4]

    def step(self, speed=0.1, steer=0.0):
        self.angle += steer
        nx = self.x + math.cos(self.angle) * speed
        ny = self.y + math.sin(self.angle) * speed
        
        done = False

        for w in WALLS:
            if w[0] <= nx <= w[2] and w[1] <= ny <= w[3]:
                done = True
                break

        self.x, self.y = nx, ny
        return self.sense(), done

    def sense(self):
        readings = []
        for a in self.sensors:
            dx = math.cos(self.angle + a)
            dy = math.sin(self.angle + a)
            dist = MAX_DIST
            for w in WALLS:
                t = ray_aabb(self.x, self.y, dx, dy, w)
                if t is not None:
                    dist = min(dist, t)
            readings.append(max(MIN_DIST, dist))
        return readings
