import pathlib
import anywidget
import traitlets
import asyncio
from IPython.display import display
from jupyter_ui_poll import ui_events

from . import MountainCarEnv


class MountainCarWidget(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"
    _css = pathlib.Path(__file__).parent / "styles.css"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    _viewport_size = traitlets.Tuple(
        traitlets.Int(), traitlets.Int(), default_value=(600, 400)
    ).tag(sync=True)
    _view_ready = traitlets.Bool(default_value=False).tag(sync=True)
    _manual_control = traitlets.Bool(default_value=False).tag(sync=True)

    def __init__(self, manual_control=False, viewport_size=(600, 400), sim_env=None):
        self._manual_control = manual_control
        self._viewport_size = viewport_size
        super().__init__()
        if sim_env is None:
            sim_env = MountainCarEnv()

        if sim_env.num_envs != 1:
            raise ValueError(
                "MountainCarWidget currently only supports single environment."
            )

        self.sim_env = sim_env
        self.sim_state = self.sim_env.reset()

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
