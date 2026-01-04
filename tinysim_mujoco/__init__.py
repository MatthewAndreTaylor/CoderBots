import pathlib

import numpy as np

try:
    import mujoco
    import glfw
except ImportError:
    raise ImportError(
        "Mujoco is not properly installed. Install using `pip install tinysim[mujoco]`"
    )


class Viewer:
    def __init__(self, model, data, width=1200, height=900):
        self.model = model
        self.data = data
        self.width = width
        self.height = height

        self.window = None
        self.scene = None
        self.context = None
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")

        self._create_window()

    def _create_window(self):
        glfw.window_hint(glfw.VISIBLE, glfw.TRUE)
        self.window = glfw.create_window(self.width, self.height, "Viewer", None, None)
        if not self.window:
            raise RuntimeError("Failed to create GLFW window")

        glfw.make_context_current(self.window)
        glfw.swap_interval(1)
        glfw.set_window_close_callback(self.window, self._on_close)

        self.cam = mujoco.MjvCamera()
        self.opt = mujoco.MjvOption()
        self.scene = mujoco.MjvScene(self.model, maxgeom=500)
        self.context = mujoco.MjrContext(
            self.model, mujoco.mjtFontScale.mjFONTSCALE_150
        )

        self.cam.azimuth = 90.0
        self.cam.elevation = -25.0
        self.cam.distance = 4.0
        self.cam.lookat[:] = np.array([0.0, 0.0, 0.0])
        self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE

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
            self.context = None


class UnitreeA1BaseEnv:

    def __init__(self, headless=False):
        model_path = str(pathlib.Path(__file__).parent / "unitree_a1/scene.xml")
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.action_space_size = self.model.nu

        if not headless:
            self.viewer = Viewer(self.model, self.data)
        else:
            self.viewer = None

    def _step(self, actions, n_frames=20):
        if len(actions) != self.action_space_size:
            raise ValueError(
                f"Expected {self.action_space_size} actions, but got {len(actions)}"
            )

        self.data.ctrl[:] = actions
        mujoco.mj_step(self.model, self.data, nstep=n_frames)
        mujoco.mj_rnePostConstraint(self.model, self.data)
        return self.data.qpos.copy(), self.data.qvel.copy()

    def render(self):
        if self.viewer is None:
            return
        self.viewer.render()

    def set_state(self, qpos, qvel):
        self.data.qpos[:] = qpos
        self.data.qvel[:] = qvel
        mujoco.mj_forward(self.model, self.data)

    def close(self):
        self.viewer.close()

    def reset(self):
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[0:3] = [0.0, 0.0, 0.3]
        self.data.qpos[7:19] = self._default_joint_position.copy()
        self.data.qvel[:] = 0
        self.data.ctrl[:] = 0
        mujoco.mj_forward(self.model, self.data)

    def _get_position_data(self):
        return self.data.qpos[0:3].copy()

    def _get_joint_data(self):
        return self.data.qpos[7:19].copy()

    def _get_roll_pitch_yaw(self):
        quat = self.data.qpos[3:7].copy()
        w, x, y, z = quat
        roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        pitch = np.arcsin(2 * (w * y - z * x))
        yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        return roll, pitch, yaw

    def get_joint_effort(self):
        return self.data.ctrl[:12].copy()

    def _get_velocity_data(self):
        return self.data.qvel.copy()

    def _get_linear_velocity(self):
        return self._get_velocity_data()[0:3]

    def _get_angular_velocity(self):
        return self._get_velocity_data()[3:6]

    def _get_joint_velocity(self):
        return self._get_velocity_data()[6:]

    def set_joint_positions(self, joint_angles):
        self.data.ctrl[:12] = joint_angles
