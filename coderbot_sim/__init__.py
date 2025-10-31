import pathlib
import anywidget
import traitlets
import asyncio

from example_maps import gen_simple_map


class RobotSim(anywidget.AnyWidget):
    _esm = pathlib.Path("sim.js")
    _css = pathlib.Path("styles.css")

    mapData = traitlets.Dict().tag(sync=True)
    show_controls = traitlets.Bool(default_value=False).tag(sync=True)
    controls = traitlets.Dict().tag(sync=True)

    def __init__(self, env_map, show_controls=False):
        super().__init__()
        self.env_map = env_map
        self.robot_data = env_map.get("robot", {"pos": [200, 200], "angle": 0})
        self.mapData = {"map": env_map.get("map", []), "robot": self.robot_data}
        self.show_controls = show_controls

    def sensor(self):
        """Signal to check the robot's sensors."""
        pass

    def move(self, **kwargs):
        """Control robot from Python."""
        data = dict(kwargs)
        self.controls = {"data": data, "_sync": id(data)}

    async def step(self, dt, **kwargs):
        """Step the simulation forward in time."""
        stop = {"forward": False, "backward": False, "left": False, "right": False}
        self.move(**kwargs)
        await asyncio.sleep(dt)
        self.move(**stop)
