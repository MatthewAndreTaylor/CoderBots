import pathlib

import numpy as np

try:
    import mujoco
    from .. import Viewer
except ImportError:
    raise ImportError(
        "Mujoco is not properly installed. Install using `pip install tinysim[mujoco]`"
    )


class ManipulationBaseEnv:
    pass
