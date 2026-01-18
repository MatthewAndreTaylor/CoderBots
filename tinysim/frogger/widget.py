import pathlib

import numpy as np
import traitlets

from .._widget_base import BaseWidget
from . import FroggerEnv


class FroggerWidget(BaseWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    car_positions = traitlets.List(default_value=[]).tag(sync=True)
    _viewport_size = traitlets.Tuple(default_value=(800, 600)).tag(sync=True)

    def get_car_positions(self):
        return np.vstack(self.sim_env.car_rects).flatten().tolist()

    def __init__(self, viewport_size=(800, 600), sim_env=FroggerEnv()):
        super().__init__(sim_env)
        self._viewport_size = viewport_size

        if sim_env.num_envs != 1:
            raise ValueError(
                "FroggerWidget currently only supports single environment."
            )

    def _update_props(self, sim_state):
        self.sim_state = sim_state
        self.car_positions = self.get_car_positions()
