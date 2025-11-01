import pathlib
import anywidget
import traitlets
import asyncio

class RobotSim(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"
    _css = pathlib.Path(__file__).parent / "styles.css"

    mapData = traitlets.Dict().tag(sync=True)
    show_controls = traitlets.Bool(default_value=False).tag(sync=True)
    controls = traitlets.Dict().tag(sync=True)
    sensorData = traitlets.Dict().tag(sync=True)
    debugDraw = traitlets.Bool(default_value=False).tag(sync=True)

    reset_state = traitlets.Bool(default_value=False).tag(sync=True)

    def __init__(self, env_map, show_controls=False, debugDraw=False):
        super().__init__()
        self.env_map = env_map
        self.robot_data = self.env_map.get("robot", {"pos": [200, 200], "angle": 0})
        self.mapData = {
            "map": self.env_map.get("map", []),
            "robot": self.robot_data
        }
        self.show_controls = show_controls
        self.debugDraw = debugDraw

    def sensor(self):
        """Signal to check the robot's sensors."""
        return self.sensorData

    def move(self, **kwargs):
        """Control robot from Python."""
        data = dict(kwargs)
        self.controls = { "data": data, "_sync": id(data) }

    async def step(self, dt, **kwargs):
        """Step the simulation forward in time."""
        stop = { "forward": False, "backward": False, "left": False, "right": False }
        self.move(**kwargs)
        await asyncio.sleep(dt)
        self.move(**stop)

    def reset(self):
        self.reset_state = True

