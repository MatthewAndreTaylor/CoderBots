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
    
    def __init__(self, headless=False):
        model_path = str(pathlib.Path(__file__).parent / "xmls/scene.xml")
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        
        if not headless:
            self.viewer = Viewer(self.model, self.data)
        else:
            self.viewer = None
            
            
    def step(self, action=None, n_frames=20):
        self.render()
        mujoco.mj_step(self.model, self.data, nstep=n_frames)
        mujoco.mj_rnePostConstraint(self.model, self.data)
            
            
            
    def render(self):
        if self.viewer:
            self.viewer.render()