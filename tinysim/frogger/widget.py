import pathlib
import anywidget
import traitlets
import asyncio
import numpy as np
from IPython.display import display
from jupyter_ui_poll import ui_events

from . import FroggerEnv


class FroggerWidget(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    car_positions = traitlets.List(default_value=[]).tag(sync=True)
    _viewport_size = traitlets.Tuple(
        traitlets.Int(), traitlets.Int(), default_value=(800, 600)
    ).tag(sync=True)
    _view_ready = traitlets.Bool(default_value=False).tag(sync=True)

    def get_car_positions(self):
        return np.vstack(self.sim_env.car_rects).flatten().tolist()

    def __init__(self, viewport_size=(800, 600), sim_env=None):
        self._viewport_size = viewport_size
        super().__init__()
        if sim_env is None:
            sim_env = FroggerEnv()

        if sim_env.num_envs != 1:
            raise ValueError(
                "FroggerWidget currently only supports single environment."
            )

        self.sim_env = sim_env
        self.sim_state = self.sim_env.reset()
        self.car_positions = self.get_car_positions()

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
        self.car_positions = self.get_car_positions()
        await asyncio.sleep(dt)
        return sim_state

    async def reset(self) -> dict:
        sim_state = self.sim_env.reset()
        self.sim_state = sim_state
        return sim_state
