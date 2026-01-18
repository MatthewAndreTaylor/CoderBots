import pathlib

import traitlets

from .._widget_base import BaseWidget
from . import MountainCarEnv


class MountainCarWidget(BaseWidget):
    _esm = pathlib.Path(__file__).parent / "sim.js"
    _css = pathlib.Path(__file__).parent / "styles.css"

    sim_state = traitlets.Dict(default_value={}).tag(sync=True)
    _viewport_size = traitlets.Tuple(default_value=(600, 400)).tag(sync=True)
    _manual_control = traitlets.Bool(default_value=False).tag(sync=True)

    def __init__(
        self, manual_control=False, viewport_size=(600, 400), sim_env=MountainCarEnv()
    ):
        super().__init__(sim_env)
        self._manual_control = manual_control
        self._viewport_size = viewport_size

        if sim_env.num_envs != 1:
            raise ValueError(
                "MountainCarWidget currently only supports single environment."
            )
