import pathlib

import numpy as np

try:
    import mujoco
    from ..gl_viewer import GLViewer, OffScreenRenderer
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

        self.show_cam_renders = False
        use_d405_camera = True
        self.d405_viewer = None

        if use_d405_camera:
            self.cam_id = mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_CAMERA, "camera_d405"
            )
            if self.show_cam_renders:
                self.d405_viewer = GLViewer(self.model, self.data, cam_id=self.cam_id)
            else:
                self.d405_viewer = OffScreenRenderer(self.model, self.data, self.cam_id)

    def step(self, action=None, n_frames=20):
        self.render()
        mujoco.mj_step(self.model, self.data, nstep=n_frames)
        mujoco.mj_rnePostConstraint(self.model, self.data)

        if self.d405_viewer:
            self.d405_viewer.render()
            frame = self.d405_viewer.capture_frame()
            # print("D405 Camera Frame Shape:", frame.shape)

    def render(self):
        if self.viewer:
            self.viewer.render()
