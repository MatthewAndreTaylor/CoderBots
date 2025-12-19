import pathlib
import anywidget
import traitlets
import asyncio
from IPython.display import display
from jupyter_ui_poll import ui_events


class RobotSim(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"
    _css = pathlib.Path(__file__).parent / "styles.css"

    mapData = traitlets.Dict().tag(sync=True)
    show_controls = traitlets.Bool(default_value=False).tag(sync=True)
    controls = traitlets.Dict().tag(sync=True)
    sensorData = traitlets.Dict().tag(sync=True)
    debugDraw = traitlets.Bool(default_value=False).tag(sync=True)
    _reset_state = traitlets.Bool(default_value=False).tag(sync=True)
    _viewport_size = traitlets.Tuple(
        traitlets.Int(), traitlets.Int(), default_value=(800, 600)
    ).tag(sync=True)

    def __init__(
        self, env_map, show_controls=False, debugDraw=False, viewport_size=(800, 600)
    ):
        """Initialize the robot simulation."""
        super().__init__()
        self.env_map = env_map
        self.robot_data = self.env_map.get("robot", {"pos": [200, 200], "angle": 0})
        self.mapData = {"map": self.env_map.get("map", []), "robot": self.robot_data}
        self.show_controls = show_controls
        self.debugDraw = debugDraw
        self._viewport_size = viewport_size

        self.num_scans = 0

    def render(self):
        display(self)
        import time

        time.sleep(1)  # Allow time for the widget to initialize (TODO: better way?)

    def move(self, **kwargs):
        """Control robot from Python."""
        data = dict(kwargs)
        self.controls = {"data": data, "_sync": id(data), "num_scans": self.num_scans}

    async def step(self, dt, **kwargs):
        """Step the simulation forward in time."""
        stop = {"forward": False, "backward": False, "left": False, "right": False}

        self.move(**kwargs)
        await asyncio.sleep(dt)

        self.num_scans += 1
        self.move(**stop)

        try:
            # https://github.com/Kirill888/jupyter-ui-poll/issues/23
            # polling simulation state updates from the widget may not be supported by all jupyter kernels
            async with ui_events() as ui_poll:
                while self.sensorData.get("scanId", 0) < self.num_scans:
                    # print(self.sensorData)
                    await ui_poll(100)
        except Exception:
            # TODO: should raise... sensorData will be stale
            pass

        return self.sensorData

    def reset(self):
        """Reset the simulation state."""
        self._reset_state = True
