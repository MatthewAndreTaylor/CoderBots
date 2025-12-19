import random
import math
import copy

empty_map = {
    "name": "rect_triangle_map",
    "robot": {
        "pos": [500, 300],
        "angle": 0,
    },  # speed: 0.01, turn_speed: 0.04, lidar: { numBeams: 30, fov: 6.28, maxRange: 1000}
    "map": [
        {
            "type": "rectangle",
            "x": 400,
            "y": 0,
            "width": 800,
            "height": 30,
            "bodyInfo": {"angle": 0, "render": {"fillStyle": "#2f6f8f"}},
            "label": "Wall",
        },
        {
            "type": "rectangle",
            "x": 400,
            "y": 590,
            "width": 800,
            "height": 20,
            "bodyInfo": {"angle": 0, "render": {"fillStyle": "#2f6f8f"}},
            "label": "Wall",
        },
        {
            "type": "rectangle",
            "x": 10,
            "y": 500,
            "width": 20,
            "height": 1000,
            "bodyInfo": {"angle": 0, "render": {"fillStyle": "#2f6f8f"}},
            "label": "Wall",
        },
        {
            "type": "rectangle",
            "x": 790,
            "y": 500,
            "width": 20,
            "height": 1000,
            "bodyInfo": {"angle": 0, "render": {"fillStyle": "#2f6f8f"}},
            "label": "Wall",
        },
    ],
}


def gen_simple_map():
    map_data = copy.deepcopy(empty_map)
    width = 800
    height = 600

    # Generate static obstacles
    for _ in range(6):
        w = 60 + random.random() * 120
        h = 40 + random.random() * 100
        x = 120 + random.random() * (width - 240)
        y = 120 + random.random() * (height - 240)
        angle = random.random() * math.pi
        rect = {
            "type": "rectangle",
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "bodyInfo": {
                "angle": angle,
                "render": {"fillStyle": "#2f6f8f"},
                "label": "Obstacle",
            },
        }
        map_data["map"].append(rect)

    # Generate dynamic pushable boxes
    for _ in range(3):
        size = 40 + random.random() * 20
        x = 100 + random.random() * (width - 200)
        y = 100 + random.random() * (height - 200)
        box = {
            "type": "rectangle",
            "x": x,
            "y": y,
            "width": size,
            "height": size,
            "bodyInfo": {
                "isStatic": False,
                "frictionAir": 0.1,
                "friction": 0.5,
                "restitution": 0.2,
                "density": 0.002,
                "render": {"fillStyle": "#b2df8a"},
                "label": "Pushable Box",
            },
        }
        map_data["map"].append(box)

    for i in range(2):
        size = 40 + random.random() * 20
        x = 100 + random.random() * (width - 200)
        y = 100 + random.random() * (height - 200)
        angle = random.random() * math.pi
        box = {
            "type": "rectangle",
            "x": x,
            "y": y,
            "width": size,
            "height": size,
            "bodyInfo": {
                "isStatic": True,
                "angle": angle,
                "label": "Goal",
                "render": {"fillStyle": "#ffffff"},
            },
        }
        map_data["map"].append(box)

    return map_data
