import math
from Box2D import b2World, b2CircleShape
from coderbot_package.maps.loader import load_map
from lidar_module import lidar_scan
import pathlib
import anywidget
import traitlets
from IPython.display import display, update_display
import time

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
    position=(WIDTH / 2 / ppm, HEIGHT / 2 / ppm), linearDamping=0.5, angularDamping=0.5
)
player_body.CreateFixture(
    shape=b2CircleShape(radius=player_radius_px / ppm), density=1.0, friction=0.3
)

velocity = (0, 0)
move_speed_px = 240

player_initial_data = {
    "pos": [float(player_body.position.x), float(player_body.position.y)],
    # "yaw": player_body.angle,
}


class RobotPanel(anywidget.AnyWidget):
    _esm = pathlib.Path("simple_client.js")

    title = traitlets.Unicode("Robot Control Panel").tag(sync=True)
    controls = traitlets.Bool(default_value=False).tag(sync=True)
    result = traitlets.Dict().tag(sync=True)
    
    env_map = traitlets.Dict(default_value=map_data).tag(sync=True)
    player_data = traitlets.Dict(default_value=player_initial_data).tag(sync=True)
    
    def _set_result(self, result_type, data):
        # Always create a new dict reference to trigger frontend update
        self.result = {"type": result_type, "data": data, "_sync": id(data)}
        
        
    def __init__(self):
        super().__init__()
        self.reset()

    def show(self):
        display(self)
        time.sleep(1.0)
        
        
    def robot_env(self):
        player_data = {
            "pos": [float(player_body.position.x), float(player_body.position.y)],
            # "yaw": player_body.angle,
        }
        return {"map": self.env_map, "robot": player_data}
    
    def step(self, num_steps):
        """Signal to step the robot."""
        dt = 1 / 20
        for _ in range(num_steps):
            world.Step(dt, 1, 1)

            player_data = {
                "pos": [float(player_body.position.x), float(player_body.position.y)],
                # "yaw": player_body.angle,
            }
            self._set_result("step", player_data)
            yield player_data
            
    
    def sensor(self, num_beams=60, max_range=1000.0, noise_std=0, fov=6.28):
        """Signal to get sensor data."""
        origin = player_body.position.x, player_body.position.y
        
        hit_points, tags = lidar_scan(
            world,
            origin,
            player_body.angle,
            robot_body=player_body,
            num_beams=num_beams,
            fov=fov,
            noise_std=noise_std,
            max_range=max_range,
        )

        lidar_data = {"hit_points": hit_points, "tags": tags}
        self._set_result("sensor", lidar_data)
        
        update_display(self, display_id=id(self))
        
        return lidar_data
    
    def move(self, vx, vy, rotation):
        """Signal to move the robot."""
        
        if vx != 0 or vy != 0:
            mag = math.hypot(vx, vy)
            vx = vx / mag
            vy = vy / mag
            speed_m = move_speed_px / ppm
            player_body.linearVelocity = (vx * speed_m, vy * speed_m)
        else:
            player_body.linearVelocity = (0, 0)
            
            
    def reset(self):
        """Signal to reset the robot position."""
        player_body.position = (WIDTH / 2 / ppm, HEIGHT / 2 / ppm)
        player_body.linearVelocity = (0, 0)