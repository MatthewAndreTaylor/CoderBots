import pathlib

import traitlets

from .._widget_base import BaseWidget
from . import FlappyEnv


class FlappySim(BaseWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    _viewport_size = traitlets.Tuple(default_value=(800, 600)).tag(sync=True)
    _manual_control = traitlets.Bool(default_value=False).tag(sync=True)

    def __init__(
        self, viewport_size=(800, 600), manual_control=False, sim_env=FlappyEnv()
    ):
        super().__init__(sim_env)
        self._viewport_size = viewport_size
        self._manual_control = manual_control

        if sim_env.num_envs != 1:
            raise ValueError("FlappySim currently only supports single environment.")
