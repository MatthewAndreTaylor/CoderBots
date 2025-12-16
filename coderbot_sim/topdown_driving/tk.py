import json
import math
import tkinter as tk

from pathlib import Path

with open(Path(__file__).parent / "track_0.json", "r") as f:
    rectangles = json.load(f)

xs, ys = [], []
for x, y, w, h, _ in rectangles:
    xs.extend([x - w / 2, x + w / 2])
    ys.extend([y - h / 2, y + h / 2])

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)

world_w = max_x - min_x
world_h = max_y - min_y


CANVAS_W = 800
CANVAS_H = 600
PADDING = 40

scale = min(
    (CANVAS_W - 2 * PADDING) / world_w,
    (CANVAS_H - 2 * PADDING) / world_h
)

offset_x = -min_x * scale + PADDING
offset_y = max_y * scale + PADDING

root = tk.Tk()
root.title("Top-Down Driving")

canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg="white")
canvas.pack()

def rotated_rect(cx, cy, w, h, deg):
    rad = math.radians(-deg)
    c, s = math.cos(rad), math.sin(rad)
    hw, hh = w / 2, h / 2

    pts = []
    for x, y in [(-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh)]:
        rx = x * c - y * s
        ry = x * s + y * c
        pts.extend([cx + rx, cy + ry])
    return pts

for x, y, w, h, rot in rectangles:
    cx = x * scale + offset_x
    cy = -y * scale + offset_y
    pts = rotated_rect(cx, cy, w * scale, h * scale, rot)

    canvas.create_polygon(
        pts,
        outline="black",
        fill="#cccccc"
    )


# draw car at x=-75, y=-42
car_x = -86 * scale + offset_x
car_y = 43 * scale + offset_y
car_len = 16
car_wid = 10
canvas.create_rectangle(
    car_x - car_len/2, car_y - car_wid/2,
    car_x + car_len/2, car_y + car_wid/2,
    outline="blue",
    fill="blue"
)

root.mainloop()
