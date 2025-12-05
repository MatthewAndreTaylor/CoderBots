import pathlib
import anywidget
import traitlets
import math
import asyncio
from IPython.display import display
from jupyter_ui_poll import ui_events
from .. import SimEnvironment


class MountainCarEnv(SimEnvironment):
    def __init__(self):
        # environment constants
        self.min_position = -1.2
        self.max_position = 0.6
        self.max_speed = 0.07
        self.force = 0.001
        self.gravity = 0.0025
        self.goal_position = 0.5

        # initial state
        self.position = -0.5
        self.velocity = 0.0

    def step(self, action: int) -> dict:
        a = int(action)
        force_term = (a - 1) * self.force
        self.velocity += force_term + math.cos(3 * self.position) * (-self.gravity)
        self.velocity = max(min(self.velocity, self.max_speed), -self.max_speed)

        self.position += self.velocity
        self.position = max(min(self.position, self.max_position), self.min_position)
        if self.position == self.min_position and self.velocity < 0:
            self.velocity = 0.0

        return {
            "position": self.position,
            "velocity": self.velocity,
            "done": bool(self.position >= self.goal_position),
        }

    def reset(self) -> dict:
        self.position = -0.5
        self.velocity = 0.0
        return {
            "position": self.position,
            "velocity": self.velocity,
            "done": bool(self.position >= self.goal_position),
        }


class MountainCarWidget(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"
    _css = pathlib.Path(__file__).parent / "styles.css"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    _viewport_size = traitlets.Tuple(
        traitlets.Int(), traitlets.Int(), default_value=(600, 400)
    ).tag(sync=True)
    _manual_control = traitlets.Bool(default_value=False).tag(sync=True)
    _view_ready = traitlets.Bool(default_value=False).tag(sync=True)

    def __init__(self, viewport_size=(600, 400), manual_control=False, sim_env=None):
        self._viewport_size = viewport_size
        self._manual_control = manual_control
        super().__init__()
        if sim_env is None:
            sim_env = MountainCarEnv()
        self.sim_env = sim_env

    def render(self):
        display(self)

        try:
            with ui_events() as ui_poll:
                while not self._view_ready:
                    ui_poll(100)
        except Exception:
            pass

    async def step(self, action: int, dt: float = 0.01) -> dict:
        sim_state = self.sim_env.step(action)
        self.sim_state = sim_state
        await asyncio.sleep(dt)
        return sim_state

    async def reset(self) -> dict:
        sim_state = self.sim_env.reset()
        self.sim_state = sim_state
        return sim_state
