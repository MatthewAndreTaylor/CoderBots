import pathlib
import anywidget
import traitlets
import asyncio
from IPython.display import display
from jupyter_ui_poll import ui_events

from . import FlappyEnv


class FlappySim(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    _viewport_size = traitlets.Tuple(
        traitlets.Int(), traitlets.Int(), default_value=(800, 600)
    ).tag(sync=True)
    _manual_control = traitlets.Bool(default_value=False).tag(sync=True)
    _view_ready = traitlets.Bool(default_value=False).tag(sync=True)

    def __init__(self, viewport_size=(800, 600), manual_control=False, sim_env=None):
        super().__init__()
        self._viewport_size = viewport_size
        self._manual_control = manual_control
        if sim_env is None:
            sim_env = FlappyEnv()
        if sim_env.num_envs != 1:
            raise ValueError("FlappySim currently only supports single environment.")

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

    async def step(self, action, dt=0.02):
        state = self.sim_env.step(action, dt=dt)
        self.sim_state = state
        await asyncio.sleep(dt)
        return state

    async def reset(self):
        state = self.sim_env.reset()
        self.sim_state = state
        await asyncio.sleep(0)
        return state
