import pathlib

import numpy as np

try:
    import mujoco
    from ..gl_viewer import GLViewer
    from ..notebook_viewer import NotebookViewer
except ImportError:
    raise ImportError(
        "Mujoco is not properly installed. Install using `pip install tinysim[mujoco]`"
    )


class ManipulationBaseEnv:

    def __init__(self, headless=False, **kwargs):
        model_path = str(pathlib.Path(__file__).parent / "xmls/scene.xml")
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)

        if not headless:
            if kwargs.get("notebook", False):
                self.viewer = NotebookViewer(self.model, self.data)
            else:
                self.viewer = GLViewer(self.model, self.data)
        else:
            self.viewer = None

    def step(self, action=None, n_frames=20):
        self.render()
        mujoco.mj_step(self.model, self.data, nstep=n_frames)
        mujoco.mj_rnePostConstraint(self.model, self.data)

    def render(self):
        if self.viewer:
            self.viewer.render()
