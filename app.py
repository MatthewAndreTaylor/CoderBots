from flask import Flask, render_template, jsonify, request
from Box2D import b2World, b2CircleShape
from coderbot_package.maps.loader import load_map
from flask_cors import CORS
from lidar_module import lidar_scan
import math
# Server should send player physics data
# when the server starts send a list 

app = Flask(__name__)
CORS(app)

WIDTH, HEIGHT = 800, 1000
ppm = 10

world = b2World(gravity=(0, 0), doSleep=True)

# Load a map from a JSON file (shapes defined in pixels). The loader converts
# pixels -> meters using the ppm (pixels per meter) value. Capture the loaded
# map data so we can return it to clients.
map_data = load_map(world, "coderbot_package/maps/rect_triangle_map.json", ppm=10)

# create player after map is loaded
player_radius_px = 10
player_body = world.CreateDynamicBody(
    position=(WIDTH / 2 / ppm, HEIGHT / 2 / ppm),
    linearDamping=0.5,
    angularDamping=0.5
)
player_body.CreateFixture(
    shape=b2CircleShape(radius=player_radius_px / ppm),
    density=1.0,
    friction=0.3
)

velocity = (0, 0)
move_speed_px = 240

@app.route('/', methods=['GET',"POST"])
def home():
    return render_template("index.html")

@app.route('/robot_scenario_env')
def render_robot_scenario():
    player_data = {
        "position": [float(player_body.position.x), float(player_body.position.y)],
        "angle": player_body.angle
    }
    return jsonify({"map": map_data, "player": player_data})


@app.route('/robot_scenario_step')
def robot_scenario_step():

    dt = 1 / 60
    world.Step(dt, 1, 1)

    # Get the player position and angle
    player_data = {
        "position": [float(player_body.position.x), float(player_body.position.y)],
        "angle": player_body.angle
    }
    return jsonify({"player": player_data})


@app.route('/robot_scenario_sensor', methods=['POST'])
def robot_scenario_sensor():

    request_data = request.json
    num_beams = request_data.get("num_beams", 60)
    fov = request_data.get("fov", 2 * math.pi)
    max_range = request_data.get("max_range", 1000.0)
    noise_std = request_data.get("noise_std", 0.0)

    origin = player_body.position

    ranges, points, normals, angles = lidar_scan(
        world, origin, player_body.angle, robot_body=player_body,
        num_beams=num_beams, fov=fov, noise_std=noise_std, max_range=max_range
    )

    hit_points = []

    for i, dist in enumerate(ranges):
        a = angles[i]
        x_end = origin[0] + dist * math.cos(a)
        y_end = origin[1] + dist * math.sin(a)
        hit_points.append((x_end, y_end))

    lidar_data = {
        "hit_points": hit_points
    }

    return jsonify(lidar_data)


@app.route('/robot_scenario_move', methods=['POST'])
def robot_scenario_move():
    # Get the movement data from the request
    desired_movement = request.json

    # Process the movement data
    vx = desired_movement.get("x", 0)
    vy = desired_movement.get("y", 0)
    rotation = desired_movement.get("rotation", 0)

    # Update the player body velocity
    if vx != 0 or vy != 0:
        mag = math.hypot(vx, vy)
        vx = vx / mag
        vy = vy / mag
        speed_m = move_speed_px / ppm
        player_body.linearVelocity = (vx * speed_m, vy * speed_m)
    else:
        player_body.linearVelocity = (0, 0)

    return jsonify()

if __name__ == "__main__":
    app.run(debug=True)