import mujoco
import numpy as np
from IPython.display import display
from PIL import Image as PILImage


class NotebookViewer:
    def __init__(self, model, data, width=640, height=480):
        self.model = model
        self.data = data
        self.cam = mujoco.MjvCamera()
        self.opt = mujoco.MjvOption()
        self.renderer = mujoco.Renderer(model, height, width, max_geom=500)

        self.cam.azimuth = 90
        self.cam.elevation = -25
        self.cam.distance = 4
        self.cam.lookat[:] = np.array([0.0, 0.0, 0.0])
        self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.renderer.update_scene(self.data, camera=self.cam)
        pil = PILImage.fromarray(self.renderer.render())
        self.display = display(pil, display_id=True)

    def render(self):
        self.renderer.update_scene(self.data, camera=self.cam)
        pil = PILImage.fromarray(self.renderer.render())
        self.display.update(pil)

    def close(self):
        self.renderer.close()
