import json
import math
import os
from Box2D import b2PolygonShape


def load_map(world, filepath, ppm=10):
    """Load a map JSON and create static bodies in the given Box2D world.

    Map JSON format example:
    {
      "name": "example",
      "ppm": 10,
      "shapes": [
        {"type":"rectangle", "x":400, "y":50, "width":800, "height":20, "angle":0},
        {"type":"triangle", "vertices":[[100,200],[200,400],[50,400]]}
      ]
    }

    All numeric coordinates are in pixels; loader converts to meters by dividing
    by ppm.
    """
    if not os.path.isabs(filepath):
        filepath = os.path.join(os.getcwd(), filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    ppm = data.get("ppm", ppm)

    shapes = data.get("shapes", [])

    for s in shapes:
        stype = s.get("type")
        if stype == "rectangle":
            x = s.get("x", 0)
            y = s.get("y", 0)
            w = s.get("width", 10)
            h = s.get("height", 10)
            angle = math.radians(s.get("angle", 0))

            hx = (w / 2.0) / ppm
            hy = (h / 2.0) / ppm
            center = (x / ppm, y / ppm)

            # Create polygon shape and set as box using SetAsBox (avoids unsupported kwargs)
            shape = b2PolygonShape()
            # b2PolygonShape.SetAsBox expects positional args: hx, hy, center, angle
            shape.SetAsBox(hx, hy, center, angle)
            body = world.CreateStaticBody(position=(0, 0))
            body.CreateFixture(shape=shape, density=0.0, friction=0.3, restitution=0.0)

        elif stype in ("triangle", "polygon"):
            verts = s.get("vertices", [])
            # accept [[x,y],[x,y],...] or flat [x,y,x,y,...]
            if len(verts) == 0:
                continue
            if isinstance(verts[0], (int, float)):
                # flat list
                verts = list(zip(verts[0::2], verts[1::2]))

            verts_m = [(_x / ppm, _y / ppm) for (_x, _y) in verts]
            # Box2D requires vertices in CCW order and a convex polygon.
            shape = b2PolygonShape(vertices=verts_m)
            body = world.CreateStaticBody(position=(0, 0))
            body.CreateFixture(shape=shape, density=0.0, friction=0.3, restitution=0.0)

        else:
            # Unknown shape type; skip
            continue
