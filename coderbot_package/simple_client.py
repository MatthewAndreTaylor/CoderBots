import math
from Box2D import b2World, b2CircleShape, b2ContactListener, b2Filter
from coderbot_package.maps.loader import load_map
from .lidar_module import lidar_scan
import pathlib
import anywidget
import traitlets
from IPython.display import display, update_display
import time

class ProjectileContactListener(b2ContactListener):
    def BeginContact(self, contact):
        body_a = contact.fixtureA.body
        body_b = contact.fixtureB.body
        bodies = (body_a, body_b)

        for body in bodies:
            if getattr(body, "userData", None) != "projectile":
                continue

            other = body_b if body is body_a else body_a
            if getattr(other, "userData", None) in ("obstacle", "goal"):
                body.userData = "destroy"
                        
                        
CATEGORY_PLAYER = 0x0002
CATEGORY_PROJECTILE = 0x0004

WIDTH, HEIGHT = 800, 1000
ppm = 10
world = b2World(gravity=(0, 0), doSleep=True)
world.contactListener = ProjectileContactListener()

# Load a map from a JSON file (shapes defined in pixels). The loader converts
# pixels -> meters using the ppm (pixels per meter) value. Capture the loaded
# map data so we can return it to clients.
map_data = {}


def load_robot_map(world, json_file, ppm):
    """
    Load a robot simulation map from a JSON file.
    """
    global map_data
    map_data = load_map(world, json_file, ppm)


load_robot_map(world, "coderbot_package/maps/rect_triangle_map.json", ppm=10)


# create player after map is loaded
player_radius_px = 10
player_body = world.CreateDynamicBody(
    position=(WIDTH / 2 / ppm, HEIGHT / 2 / ppm), linearDamping=0.5, angularDamping=0.5
)
player_fixture = player_body.CreateFixture(
    shape=b2CircleShape(radius=player_radius_px / ppm), density=1.0, friction=0.3
)
player_fixture.filterData.categoryBits = CATEGORY_PLAYER
player_fixture.filterData.maskBits = 0xFFFF & ~CATEGORY_PROJECTILE

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
        
        self.projectiles = []

    def show(self):
        display(self)
        
        time.sleep(1.0)  # allow time for display to initialize
        
        
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
            live_projectiles = []
            proj_data = []
            for proj in self.projectiles:
                if proj.userData == "destroy" or not (0 <= proj.position.x <= WIDTH/ppm and 0 <= proj.position.y <= HEIGHT/ppm):
                    world.DestroyBody(proj)
                else:
                    live_projectiles.append(proj)
                    proj_data.append([proj.position.x, proj.position.y])
            self.projectiles = live_projectiles

            self._set_result("step", {"robot": player_data, "projectiles": proj_data})
            yield {"robot": player_data, "projectiles": proj_data}

            
    
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
            
    
    def fire(self, speed=5000.0, angle=None):
        """Fire a projectile from the robot's current position."""
        if angle is None:
            # Use the robot's current facing angle
            angle = 0.0  # or use player_body.angle if you track yaw

        # Create a small projectile body
        radius = 2 / ppm  # 2 pixels radius
        proj_body = world.CreateDynamicBody(
            position=player_body.position,
            bullet=True,  # improves fast-moving body collision
            userData="projectile",
        )
        proj_body.CreateFixture(
            shape=b2CircleShape(radius=radius),
            density=1.0,
            friction=0.0,
            restitution=0.5,
            filter=b2Filter(
                categoryBits=CATEGORY_PROJECTILE,
                maskBits=0xFFFF & ~CATEGORY_PLAYER
            )
        )

        # Initial velocity
        vx = math.cos(angle) * speed / ppm
        vy = math.sin(angle) * speed / ppm
        proj_body.linearVelocity = (vx, vy)

        self.projectiles.append(proj_body)
        self._set_result("fire", {"pos": list(proj_body.position), "velocity": (vx, vy)})
            
            
    def reset(self):
        """Signal to reset the robot position."""
        player_body.position = (WIDTH / 2 / ppm, HEIGHT / 2 / ppm)
        player_body.linearVelocity = (0, 0)
