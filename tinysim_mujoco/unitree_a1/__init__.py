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


class UnitreeA1BaseEnv:

    def __init__(self, headless=False, **kwargs):
        model_path = str(pathlib.Path(__file__).parent / "unitree_a1/scene.xml")
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.action_space_size = self.model.nu
        mujoco.mj_forward(self.model, self.data)

        self.default_joint_position = np.array(
            [-0.05, 0.8, -1.5, 0.05, 0.8, -1.5, -0.03, 0.9, -1.4, 0.03, 0.9, -1.4],
            dtype=np.float32,
        )

        if not headless:
            if kwargs.get("notebook", False):
                self.viewer = NotebookViewer(self.model, self.data)
            else:
                self.viewer = GLViewer(self.model, self.data)
        else:
            self.viewer = None

    def step(self, actions, n_frames=20):
        self.render()

        if len(actions) != self.action_space_size:
            raise ValueError(
                f"Expected {self.action_space_size} actions, but got {len(actions)}"
            )

        self.data.ctrl[:] = actions
        mujoco.mj_step(self.model, self.data, nstep=n_frames)
        mujoco.mj_rnePostConstraint(self.model, self.data)

    def render(self):
        if self.viewer:
            self.viewer.render()

    def reset(self):
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[0:3] = [0.0, 0.0, 0.3]
        self.data.qpos[7:19] = self.default_joint_position.copy()
        self.data.qvel[:] = 0
        self.data.ctrl[:] = 0
        mujoco.mj_forward(self.model, self.data)

    def get_position_data(self):
        return self.data.qpos[0:3].copy()

    def get_joint_data(self):
        return self.data.qpos[7:19].copy()

    def get_joint_effort(self):
        return self.data.ctrl[:12].copy()

    def get_velocity_data(self):
        return self.data.qvel.copy()


class UnitreeA1WalkEnv:
    def __init__(self, reward_weights, cost_weights, **kwargs):
        self.env = UnitreeA1BaseEnv(**kwargs)
        self.viewer = self.env.viewer
        self.frame_skip = 20
        self.obs_dim = 45
        self._previous_observation = np.zeros(self.obs_dim, dtype=np.float32)
        self.joint_limits_low = np.array(
            [-0.1, 0.25, -2.0, -0.1, 0.25, -2.0, -0.03, 0.25, -1.6, 0.03, 0.25, -1.6],
            dtype=np.float32,
        )
        self.joint_limits_high = np.array(
            [0.1, 1.2, -0.5, 0.1, 1.2, -0.5, 0.03, 1.2, -1.1, 0.03, 1.2, -1.1],
            dtype=np.float32,
        )

        self._feet_air_time = np.zeros(4)
        self._last_contacts = np.zeros(4)
        self.step_counter = 0
        self.tracking_sigma = 0.25
        self.maximum_episode_steps = 1024
        self.prev_action = np.zeros_like(self.env.default_joint_position)
        self.target_lin_vel = np.array([0.5, 0.0])
        self.target_ang_vel = 0.0
        self._healthy_z_range = (0.3, 0.335)
        self._healthy_rotation = np.array(
            [np.deg2rad(6), np.deg2rad(6), np.deg2rad(10)]
        )

        self._cfrc_ext_feet_indices = [4, 7, 10, 13]
        self.reward_weights = reward_weights
        self.cost_weights = cost_weights
        # TODO: requires keys

    def reset(self, **kwargs):
        self.env.reset()
        self.step_counter = 0
        self._feet_air_time = np.zeros(4)
        self._last_contacts = np.zeros(4)
        self.prev_action = self.env.default_joint_position.copy()
        self.target_lin_vel = np.array([0.5, 0.0])
        current_obs = self._get_obs()
        self._previous_observation = np.zeros_like(current_obs)
        full_obs = np.concatenate([current_obs, self._previous_observation])
        self._previous_observation = current_obs.copy()
        return full_obs, {}

    def step(self, action):
        self.step_counter += 1
        a = 0.7
        action_filtered = a * self.prev_action + (1 - a) * action
        if self.step_counter < 1:
            action_filtered = self.env.default_joint_position.copy()
        self.env.step(action_filtered, self.frame_skip)

        current_obs = self._get_obs()
        obs = np.concatenate([current_obs, self._previous_observation])
        reward = self._compute_reward(action)
        terminated = not self.is_healthy
        truncated = self.step_counter >= self.maximum_episode_steps
        self.prev_action = action_filtered
        self._previous_observation = current_obs.copy()
        return obs, reward, terminated, truncated, {}

    def _get_obs(self):
        base_ang_vel = self.euler_from_quaternion(*self.env.data.qpos[3:7])
        joint_positions = self.env.get_joint_data()
        joint_velocities = self.env.get_velocity_data()[6:]
        curr_contact = self.feet_contact_forces > 1.0
        return np.concatenate(
            (
                base_ang_vel,
                joint_positions,
                joint_velocities,
                curr_contact,
                self.target_lin_vel,
                self.prev_action,
            ),
            dtype=np.float32,
        )

    def _compute_reward(self, action):
        vel = self.env.get_velocity_data()
        lin_vel = np.array(vel[:3])
        ang_vel = np.array(vel[3:6])

        tracking_lin_vel_reward, tracking_ang_vel_reward, lin_vel_z_penalty = (
            self._tracking_velocity_penalty(lin_vel, ang_vel)
        )
        action_diff_penalty = np.sum(np.abs(action - self.prev_action))
        action_sym = self.action_sym()

        rewards = (
            tracking_lin_vel_reward * self.reward_weights["linear_vel_tracking"]
            + tracking_ang_vel_reward * self.reward_weights["angular_vel_tracking"]
            + self.is_healthy * self.reward_weights["healthy"]
            + self.feet_air_time_reward * self.reward_weights["feet_airtime"]
        )

        neg_rewards = (
            self.torque_cost * self.cost_weights["torque"]
            + action_diff_penalty * self.cost_weights["action_rate"]
            + lin_vel_z_penalty * self.cost_weights["vertical_vel"]
            + self.xy_angular_velocity_cost * self.cost_weights["xy_angular_vel"]
            + action_sym * self.cost_weights["action_sym"]
            + self.acceleration_cost * self.cost_weights["joint_acceleration"]
            + self.orientation_cost * self.cost_weights["orientation"]
            + self.default_joint_pos_cost * self.cost_weights["default_joint_pos"]
        )
        return rewards - neg_rewards

    def _tracking_velocity_penalty(self, lin_vel, ang_vel):
        lin_vel_error = np.sum(np.abs(self.target_lin_vel[0] - lin_vel[0]))
        tracking_lin_vel_reward = np.exp(-lin_vel_error / self.tracking_sigma)
        ang_vel_error = np.sum(np.square(self.target_ang_vel - ang_vel[2]))
        tracking_ang_vel_reward = np.exp(-ang_vel_error / self.tracking_sigma)
        lin_vel_z_penalty = np.square((lin_vel[2]))
        return tracking_lin_vel_reward, tracking_ang_vel_reward, lin_vel_z_penalty

    @property
    def feet_air_time_reward(self):
        curr_contact = self.feet_contact_forces > 1.0
        contact_filter = np.logical_or(curr_contact, self._last_contacts)
        self._last_contacts = curr_contact
        first_contact = (self._feet_air_time > 0.0) * contact_filter
        self._feet_air_time += self.env.model.opt.timestep * self.frame_skip
        air_time_reward = np.sum((self._feet_air_time) * first_contact)
        air_time_reward *= np.linalg.norm(self.target_lin_vel) > 0.1
        self._feet_air_time *= ~contact_filter
        return air_time_reward

    @property
    def torque_cost(self):
        return np.sum(np.abs(self.env.get_joint_effort()))

    @property
    def xy_angular_velocity_cost(self):
        return np.sum(np.square(self.env.data.qvel[5]))

    @property
    def is_healthy(self):
        _, _, z = self.env.get_position_data()
        min_z, max_z = self._healthy_z_range
        if not (min_z <= z <= max_z):
            return False

        r = self.euler_from_quaternion(*self.env.data.qpos[3:7])
        return np.all(np.abs(r) <= self._healthy_rotation)

    @property
    def feet_contact_forces(self):
        contact_forces = self.env.data.cfrc_ext[self._cfrc_ext_feet_indices].copy()
        return np.linalg.norm(contact_forces, axis=1)

    @property
    def orientation_cost(self):
        roll, pitch, _ = self.euler_from_quaternion(*self.env.data.qpos[3:7])
        return np.square(roll) + np.square(pitch)

    @property
    def default_joint_pos_cost(self):
        joint_pos = self.env.get_joint_data()
        soft_joint_limits_low = self.joint_limits_low * 0.9
        soft_joint_limits_high = self.joint_limits_high * 0.9

        lower_violation = np.maximum(soft_joint_limits_low - joint_pos, 0)
        upper_violation = np.maximum(joint_pos - soft_joint_limits_high, 0)
        return np.sum(np.square(lower_violation + upper_violation))

    def action_sym(self):
        in_phase_pairs_thigh = [(1, 7), (4, 10)]
        out_of_phase_pairs_thigh = [(1, 4), (7, 10)]
        out_of_phase_pairs_calf = [(2, 5), (8, 11)]
        in_phase_pairs_calf = [(2, 8), (5, 11)]

        jointpositions = self.env.get_joint_data()
        loss_in_thigh = sum(
            (jointpositions[i] - jointpositions[j]) ** 2
            for i, j in in_phase_pairs_thigh
        )
        loss_out_thigh = sum(
            (jointpositions[i] + jointpositions[j] - 1.5) ** 2
            for i, j in out_of_phase_pairs_thigh
        )
        loss_in_calf = sum(
            (jointpositions[i] - jointpositions[j]) ** 2 for i, j in in_phase_pairs_calf
        )
        loss_out_calf = sum(
            (jointpositions[i] + jointpositions[j] + 3.6) ** 2
            for i, j in out_of_phase_pairs_calf
        )
        loss_in = loss_in_thigh + 0.1 * loss_in_calf
        loss_out = loss_out_thigh + 0.1 * loss_out_calf
        return loss_in + loss_out

    @property
    def acceleration_cost(self):
        return np.sum(np.square(self.env.data.qacc[6:]))

    @staticmethod
    def euler_from_quaternion(w, x, y, z):
        roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1.0, 1.0))
        yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        return roll, pitch, yaw
