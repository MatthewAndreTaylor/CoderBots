"""Small CLI to preview map JSON files in coderbot_package/maps using pygame.

Controls:
  Left/Right arrows - cycle maps in the maps folder
  + / -            - increase/decrease ppm (pixels per meter) used for display scale
  r                - reload current map from disk
  q or ESC         - quit

Usage:
  python preview_map.py                # opens first map found
  python preview_map.py path/to/map.json
"""
import argparse
import json
import os
import sys

try:
    import pygame
except Exception:
    print("pygame is required to run this preview. Install via pip: pip install pygame")
    raise

try:
    from Box2D import b2World, b2CircleShape
except Exception:
    print("pybox2d (Box2D) is required for physics. Install via pip: pip install box2d-py")
    raise

from coderbot_package.maps.loader import load_map as loader_create_static_bodies


MAPS_DIR = os.path.join(os.path.dirname(__file__), "coderbot_package", "maps")


def find_map_files():
    if not os.path.isdir(MAPS_DIR):
        return []
    return [os.path.join(MAPS_DIR, f) for f in os.listdir(MAPS_DIR) if f.lower().endswith('.json')]


def load_map(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ppm = data.get('ppm', 10)
    shapes = data.get('shapes', [])
    name = data.get('name', os.path.basename(path))
    return {'path': path, 'name': name, 'ppm': ppm, 'shapes': shapes}


def build_physics_for_map(map_path, ppm):
    """Create a fresh b2World and load static bodies from the map JSON using the loader."""
    world = b2World(gravity=(0, 0), doSleep=True)
    # loader_create_static_bodies will read the file and create static bodies scaled by ppm
    loader_create_static_bodies(world, map_path, ppm=ppm)
    return world


def create_player(world, start_px, radius_px, ppm):
    # create a dynamic circle body centered at start_px (pixels). Convert to meters.
    start_m = (start_px[0] / ppm, start_px[1] / ppm)
    radius_m = radius_px / ppm
    body = world.CreateDynamicBody(position=start_m, linearDamping=1.0, angularDamping=1.0)
    circle = b2CircleShape(radius=radius_m)
    body.CreateFixture(shape=circle, density=1.0, friction=0.3, restitution=0.1)
    return body


def draw_map(screen, mapdata, ppm):
    screen.fill((40, 40, 48))
    w, h = screen.get_size()

    # optional: draw grid
    grid_color = (50, 50, 60)
    step = max(10, int(ppm))
    for x in range(0, w, step):
        pygame.draw.line(screen, grid_color, (x, 0), (x, h))
    for y in range(0, h, step):
        pygame.draw.line(screen, grid_color, (0, y), (w, y))

    # draw shapes
    for s in mapdata['shapes']:
        stype = s.get('type')
        if stype == 'rectangle':
            x = s.get('x', 0)
            y = s.get('y', 0)
            width = s.get('width', 10)
            height = s.get('height', 10)
            angle = s.get('angle', 0)

            rect = pygame.Rect(0, 0, width, height)
            rect.center = (int(x), int(y))
            # rotation: create a surface and rotate
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(surf, (200, 180, 140), surf.get_rect())
            if angle != 0:
                surf = pygame.transform.rotate(surf, -angle)
            # compute new rect to blit at center
            br = surf.get_rect()
            br.center = rect.center
            screen.blit(surf, br.topleft)

        elif stype in ('triangle', 'polygon'):
            verts = s.get('vertices', [])
            if len(verts) == 0:
                continue
            # accept flat list too
            if isinstance(verts[0], (int, float)):
                verts = list(zip(verts[0::2], verts[1::2]))

            pts = [(int(x), int(y)) for x, y in verts]
            pygame.draw.polygon(screen, (160, 200, 180), pts)
            pygame.draw.polygon(screen, (30, 30, 30), pts, width=2)

        else:
            # unknown shape; draw a small marker
            x = s.get('x', None)
            y = s.get('y', None)
            if x is not None and y is not None:
                pygame.draw.circle(screen, (220, 120, 120), (int(x), int(y)), 4)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument('map', nargs='?', help='path to map json (optional)')
    args = parser.parse_args(argv)

    files = find_map_files()
    if args.map:
        if os.path.isfile(args.map):
            files = [args.map]
        else:
            print(f"Map file not found: {args.map}")
            return 1

    if not files:
        print('No map JSON files found in', MAPS_DIR)
        return 1

    idx = 0
    current_map = load_map(files[idx])
    ppm = current_map.get('ppm', 10)

    # Build physics world for the first map
    world = build_physics_for_map(current_map['path'], ppm)

    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption('Map Preview (physics)')
    clock = pygame.time.Clock()

    # create player at center of screen
    screen_w, screen_h = screen.get_size()
    player_radius_px = 12
    player = create_player(world, (screen_w // 2, screen_h // 2), player_radius_px, ppm)

    # movement params (pixels/sec -> convert to m/s by dividing ppm)
    move_speed_px = 240

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE or ev.key == pygame.K_q:
                    running = False
                elif ev.key == pygame.K_RIGHT:
                    idx = (idx + 1) % len(files)
                    current_map = load_map(files[idx])
                    ppm = current_map.get('ppm', ppm)
                    # rebuild physics world and reset player
                    world = build_physics_for_map(current_map['path'], ppm)
                    player = create_player(world, (screen_w // 2, screen_h // 2), player_radius_px, ppm)
                elif ev.key == pygame.K_LEFT:
                    idx = (idx - 1) % len(files)
                    current_map = load_map(files[idx])
                    ppm = current_map.get('ppm', ppm)
                    world = build_physics_for_map(current_map['path'], ppm)
                    player = create_player(world, (screen_w // 2, screen_h // 2), player_radius_px, ppm)
                elif ev.key == pygame.K_r:
                    current_map = load_map(files[idx])
                    ppm = current_map.get('ppm', ppm)
                    world = build_physics_for_map(current_map['path'], ppm)
                    player = create_player(world, (screen_w // 2, screen_h // 2), player_radius_px, ppm)
                elif ev.unicode == '+' or ev.key == pygame.K_EQUALS:
                    ppm = max(1, ppm + 1)
                elif ev.unicode == '-' or ev.key == pygame.K_MINUS:
                    ppm = max(1, ppm - 1)

        # movement input -> set player linearVelocity each frame
        keys = pygame.key.get_pressed()
        vx = vy = 0.0
        if keys[pygame.K_a]:
            vx -= 1
        if keys[pygame.K_d]:
            vx += 1
        if keys[pygame.K_w]:
            vy -= 1
        if keys[pygame.K_s]:
            vy += 1

        if player:
            # normalize direction
            if vx != 0 or vy != 0:
                import math
                mag = math.hypot(vx, vy)
                vx = vx / mag
                vy = vy / mag
                speed_m = move_speed_px / ppm
                player.linearVelocity = (vx * speed_m, vy * speed_m)
            else:
                # small damping will slow the player; optionally zero velocity
                player.linearVelocity = (0.0, 0.0)

        # step physics (fixed timestep)
        time_step = 1.0 / 60.0
        vel_iters = 6
        pos_iters = 2
        world.Step(time_step, vel_iters, pos_iters)

        # Draw -- shapes from JSON (visual) and player from physics
        draw_map(screen, current_map, ppm)

        # draw player by converting body position (meters) -> pixels
        if player:
            pos = player.position
            px = int(pos[0] * ppm)
            py = int(pos[1] * ppm)
            pygame.draw.circle(screen, (80, 160, 220), (px, py), player_radius_px)
            pygame.draw.circle(screen, (20, 40, 60), (px, py), player_radius_px, width=2)

        # HUD
        font = pygame.font.SysFont(None, 20)
        text = font.render(f"{os.path.basename(current_map['path'])}  ppm={ppm}  [{idx+1}/{len(files)}]  Left/Right: cycle  +/-: zoom  R:reload  Q/Esc:quit", True, (220, 220, 220))
        screen.blit(text, (8, 8))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
