import pathlib

import traitlets

from .._widget_base import BaseWidget
from . import LOCAL_WALLS, TopDownDrivingEnv


class TopDownDrivingWidget(BaseWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    wall_positions = traitlets.List(default_value=LOCAL_WALLS).tag(sync=True)
    _viewport_size = traitlets.Tuple(default_value=(800, 600)).tag(sync=True)

    def __init__(self, viewport_size=(800, 600), sim_env=TopDownDrivingEnv()):
        super().__init__(sim_env)
        self._viewport_size = viewport_size

    def _update_props(self, sim_state):
        self.sim_state = {
            "x": sim_state["x"].tolist(),
            "y": sim_state["y"].tolist(),
            "angle": sim_state["angle"].tolist(),
        }
