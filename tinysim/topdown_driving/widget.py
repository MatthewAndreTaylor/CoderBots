import pathlib
import anywidget
import traitlets
import asyncio
import numpy as np
from IPython.display import display
from jupyter_ui_poll import ui_events

from . import TopDownDrivingEnv, LOCAL_WALLS


class TopDownDrivingWidget(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    wall_positions = traitlets.List(default_value=LOCAL_WALLS).tag(sync=True)
    
    _viewport_size = traitlets.Tuple(
        traitlets.Int(), traitlets.Int(), default_value=(800, 600)
    ).tag(sync=True)
    _view_ready = traitlets.Bool(default_value=False).tag(sync=True)

    def __init__(self, viewport_size=(800, 600), sim_env=None):
        self._viewport_size = viewport_size
        super().__init__()
        if sim_env is None:
            sim_env = TopDownDrivingEnv()

        self.sim_env = sim_env
        self.copy_py_state(self.sim_env.reset())

    def render(self):
        display(self)

        try:
            with ui_events() as ui_poll:
                while not self._view_ready:
                    ui_poll(100)
        except Exception:
            pass
        
    
    def copy_py_state(self, sim_state: dict):
        self.sim_state = {
            "x": sim_state["x"].tolist(),
            "y": sim_state["y"].tolist(),
            "angle": sim_state["angle"].tolist(),
        }

    async def step(self, action: int, dt: float = 0.01) -> dict:
        sim_state = self.sim_env.step(action)
        self.copy_py_state(sim_state)

        await asyncio.sleep(dt)
        return sim_state

    async def reset(self) -> dict:
        sim_state = self.sim_env.reset()
        self.copy_py_state(sim_state)
        return sim_state