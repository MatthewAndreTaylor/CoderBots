import math
import numpy as np
from Box2D import b2Vec2, b2RayCastCallback


class LidarCallback(b2RayCastCallback):
    def __init__(self, body_to_ignore=None):
        super().__init__()
        self.hit = False
        self.point = None
        self.normal = None
        self.fraction = 1.0  # closest fraction along the ray

        self.body_to_ignore = body_to_ignore

    def ReportFixture(self, fixture, point, normal, fraction):
        # Ignore the robot’s own body (or any specified body)
        if self.body_to_ignore is not None and fixture.body == self.body_to_ignore:
            return -1.0  # keep going, ignore this fixture

        # Keep the closest hit
        if fraction < self.fraction:
            self.hit = True
            self.point = b2Vec2(point)
            self.normal = b2Vec2(normal)
            self.fraction = fraction
            self.body = fixture.body

        # Return the fraction to clip at this intersection (optimization)
        return fraction


def lidar_scan(
    world,
    origin,
    yaw,
    robot_body=None,
    num_beams=360,
    fov=2 * math.pi,
    max_range=1000.0,
    noise_std=0.0,
):
    origin = b2Vec2(origin)
    angles = np.linspace(-fov / 2, fov / 2, num_beams) + yaw
    tags = [None] * num_beams
    hit_points = [None] * num_beams

    cos_angles = np.cos(angles)
    sin_angles = np.sin(angles)

    for i, (dx, dy) in enumerate(zip(cos_angles, sin_angles)):
        p1 = origin
        p2 = b2Vec2(origin.x + dx * max_range, origin.y + dy * max_range)
        cb = LidarCallback(body_to_ignore=robot_body)
        world.RayCast(cb, p1, p2)

        dist = max_range
        if cb.hit:
            dist = cb.fraction * max_range
            if noise_std > 0:
                dist += np.random.normal(0, noise_std)
                dist = np.clip(dist, 0, max_range)
            tags[i] = cb.body.userData

        hit_points[i] = (origin.x + dist * dx, origin.y + dist * dy)

    return hit_points, tags
