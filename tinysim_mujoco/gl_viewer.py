import glfw
import mujoco
import numpy as np


class OffScreenRenderer:
    def __init__(self, model, data, cam_id):
        self.model = model
        self.data = data
        self.cam_id = cam_id
        self.renderer = mujoco.Renderer(self.model)
        self.renderer.update_scene(self.data, camera=self.cam_id)

    def render(self):
        self.renderer.update_scene(self.data, camera=self.cam_id)

    def capture_frame(self):
        return self.renderer.render()


def default_camera():
    cam = mujoco.MjvCamera()
    cam.azimuth = 90.0
    cam.elevation = -25.0
    cam.distance = 4.0
    cam.lookat[:] = np.array([0.0, 0.0, 0.0])
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    return cam


class GLViewer:
    def __init__(self, model, data, cam_id=-1, width=1200, height=900):
        self.width = width
        self.height = height
        self.model = model
        self.data = data
        self.window = None
        self.scene = None
        self.context = None
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")

        if cam_id != -1:
            self.cam = mujoco.MjvCamera()
            self.cam.fixedcamid = cam_id
            self.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
        else:
            self.cam = default_camera()

        self._create_window()

    def _create_window(self):
        glfw.window_hint(glfw.VISIBLE, glfw.TRUE)
        self.window = glfw.create_window(self.width, self.height, "Viewer", None, None)
        if not self.window:
            raise RuntimeError("Failed to create GLFW window")

        glfw.make_context_current(self.window)
        glfw.swap_interval(1)
        glfw.set_window_close_callback(self.window, self._on_close)

        self.opt = mujoco.MjvOption()
        self.scene = mujoco.MjvScene(self.model, maxgeom=500)
        self.context = mujoco.MjrContext(
            self.model, mujoco.mjtFontScale.mjFONTSCALE_150
        )

    def render(self):
        if self.window is None:
            return

        glfw.make_context_current(self.window)
        width, height = glfw.get_framebuffer_size(self.window)
        viewport = mujoco.MjrRect(0, 0, width, height)
        mujoco.mjv_updateScene(
            self.model,
            self.data,
            self.opt,
            None,
            self.cam,
            mujoco.mjtCatBit.mjCAT_ALL,
            self.scene,
        )

        mujoco.mjr_render(viewport, self.scene, self.context)
        glfw.swap_buffers(self.window)
        glfw.poll_events()

    def _on_close(self, window):
        self.close()

    def close(self):
        if self.window is not None:
            glfw.destroy_window(self.window)
            self.window = None
            self.scene = None
            self.context.free()

    def capture_frame(self):
        """Capture the current framebuffer and return as an image array (H, W, 3)."""
        if self.window is None:
            return None

        glfw.make_context_current(self.window)
        width, height = glfw.get_framebuffer_size(self.window)
        viewport = mujoco.MjrRect(0, 0, width, height)

        rgb_buffer = np.zeros((height, width, 3), dtype=np.uint8)
        mujoco.mjr_readPixels(rgb_buffer, None, viewport, self.context)

        # OpenGL framebuffer origin is bottom-left, flip vertically
        rgb_buffer = np.flip(rgb_buffer, axis=0)
        return rgb_buffer
