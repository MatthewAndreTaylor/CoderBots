from tinysim_mujoco import UnitreeA1BaseEnv
import numpy as np

# %pip install stable-baselines3[extra] gymnasium

from stable_baselines3 import PPO
import gymnasium as gym
from gymnasium import spaces


class UnitreeA1WalkEnv(UnitreeA1BaseEnv, gym.Env):

    def __init__(self, headless=False):
        super().__init__(headless=headless)
        self.frame_skip = 20

        obs_dim = 46
        obs_high = np.array([np.inf] * obs_dim * 2, dtype=np.float32)
        self.observation_space = spaces.Box(-obs_high, obs_high, dtype=np.float32)
        self._previous_observation = np.zeros(obs_dim, dtype=np.float32)
        self._default_joint_position = np.array(
            [-0.05, 0.8, -1.5, 0.05, 0.8, -1.5, -0.03, 0.9, -1.4, 0.03, 0.9, -1.4]
        )
        self.joint_limits_low = np.array(
            [-0.1, 0.25, -2.0, -0.1, 0.25, -2.0, -0.03, 0.25, -1.6, 0.03, 0.25, -1.6]
        )
        self.joint_limits_high = np.array(
            [0.1, 1.2, -0.5, 0.1, 1.2, -0.5, 0.03, 1.2, -1.1, 0.03, 1.2, -1.1]
        )

        self.action_space = spaces.Box(
            low=self.joint_limits_low,
            high=self.joint_limits_high,
            shape=(12,),
            dtype=np.float32,
        )
        self._gravity_vector = np.array(self.model.opt.gravity)
        self._feet_air_time = np.zeros(4)
        self._last_contacts = np.zeros(4)

        self.episode_reward_ = 0.0
        self.tracking_lin_vel_reward_ = 0
        self.tracking_ang_vel_reward_ = 0
        self.helthy_reward_ = 0
        self.feet_air_time_reward_ = 0

        self.torque_cost_ = 0
        self.action_diff_penalty_ = 0
        self.lin_vel_z_penalty_ = 0
        self.xy_angular_velocity_cost_ = 0
        self.action_sym_ = 0
        self.acceleration_cost_ = 0
        self.orientation_penalty_ = 0
        self.default_joint_position_cost_ = 0
        self.step_counter = 0
        self.episode_counter = 0
        self.log_episode_count = 20
        self.prev_x = 0.0
        self.reached_target = False

        self.goal_distance = 9.0
        self.tracking_sigma = 0.25
        self.maximum_episode_steps = 1024
        self._max_episode_time_sec = 15.0
        self._curriculum_base = 0.3
        self.prev_action = np.zeros_like(self._default_joint_position)

        self.target_lin_vel = self.set_target_velocity()
        self.target_ang_vel = 0.0
        self._healthy_z_range = (0.3, 0.335)
        self._healthy_pitch_range = (-np.deg2rad(6), np.deg2rad(6))
        self._healthy_roll_range = (-np.deg2rad(6), np.deg2rad(6))
        self._healthy_yaw_range = (-np.deg2rad(10), np.deg2rad(10))
        self._cfrc_ext_feet_indices = [4, 7, 10, 13]
        dof_position_limit_multiplier = 0.9
        ctrl_range_offset = (
            0.5
            * (1 - dof_position_limit_multiplier)
            * (
                self.model.actuator_ctrlrange[:, 1]
                - self.model.actuator_ctrlrange[:, 0]
            )
        )

        self._soft_joint_range = np.copy(self.model.actuator_ctrlrange)
        self._soft_joint_range[:, 0] += ctrl_range_offset
        self._soft_joint_range[:, 1] -= ctrl_range_offset
        self.reward_weights = {}
        self.cost_weights = {}

    def set_weights(self, reward_weights, cost_weights):
        self.reward_weights = reward_weights
        self.cost_weights = cost_weights

    def set_target_velocity(self):
        return np.array([0.5, 0.0])

    def reset(self, **kwargs):
        super().reset()
        self.step_counter = 0
        self._feet_air_time = np.zeros(4)
        self._last_contacts = np.zeros(4)
        self.prev_action = self._default_joint_position.copy()

        self.prev_x = 0.0
        self.episode_reward_ = 0.0
        self.tracking_lin_vel_reward_ = 0
        self.tracking_ang_vel_reward_ = 0
        self.helthy_reward_ = 0
        self.feet_air_time_reward_ = 0

        self.torque_cost_ = 0
        self.action_diff_penalty_ = 0
        self.lin_vel_z_penalty_ = 0
        self.xy_angular_velocity_cost_ = 0
        self.action_sym_ = 0
        self.acceleration_cost_ = 0
        self.orientation_penalty_ = 0
        self.default_joint_position_cost_ = 0
        self.target_lin_vel = self.set_target_velocity()

        current_obs = self._get_obs()
        self._previous_observation = np.zeros_like(current_obs)
        full_obs = np.concatenate([current_obs, self._previous_observation])
        self._previous_observation = current_obs.copy()
        return full_obs, {}

    def step(self, action):
        if self.viewer is not None:
            self.render()

        self.step_counter += 1
        a = 0.7
        action_filtered = a * self.prev_action + (1 - a) * action
        if self.step_counter < 1:
            action_filtered = self._default_joint_position.copy()
        self._step(action_filtered, self.frame_skip)

        current_obs = self._get_obs()
        obs = np.concatenate([current_obs, self._previous_observation])
        reward = self._compute_reward(current_obs, action)
        is_healthy_ = self.is_healthy
        terminated = not is_healthy_
        truncated = self.step_counter >= self.maximum_episode_steps

        info = {
            "terminated": terminated,
            "truncated:": truncated,
        }
        self.prev_action = action_filtered
        self._previous_observation = current_obs.copy()

        if terminated or truncated:
            self.episode_counter += 1
            info.update(
                {
                    "total_reward": self.episode_reward_,
                    "tracking_lin_vel_reward": self.tracking_lin_vel_reward_,
                    "tracking_ang_vel_reward": self.tracking_ang_vel_reward_,
                    "healthy_reward": self.helthy_reward_,
                    "feet_air_time_reward": self.feet_air_time_reward_,
                    "torque_cost": self.torque_cost_,
                    "action_diff_penalty": self.action_diff_penalty_,
                    "lin_vel_z_penalty": self.lin_vel_z_penalty_,
                    "xy_angular_velocity_cost": self.xy_angular_velocity_cost_,
                    "action_sym": self.action_sym_,
                    "acceleration_cost": self.acceleration_cost_,
                    "orientation_penalty": self.orientation_penalty_,
                    "default_joint_position_cost": self.default_joint_position_cost_,
                    "terminated": terminated,
                    "truncated": truncated,
                }
            )

        return obs, reward, terminated, truncated, info

    def _get_obs(self):
        base_ang_vel = self._get_roll_pitch_yaw()
        joint_positions = self._get_joint_data()
        joint_velocities = self._get_joint_velocity()
        previous_action = self.prev_action
        target_lin_vel = self.target_lin_vel
        target_ang_vel = np.array([0.0])
        feet_contact_force_mag = self.feet_contact_forces
        curr_contact = feet_contact_force_mag > 1.0
        curr_contact = np.array(curr_contact, dtype=np.float32)
        obs = np.concatenate(
            (
                base_ang_vel,
                joint_positions,
                joint_velocities,
                curr_contact,
                target_lin_vel,
                target_ang_vel,
                previous_action,
            ),
            dtype=np.float32,
        )
        return obs

    def _compute_reward(self, obs, action):
        joint_velocities = self._get_joint_velocity()
        lin_vel = self._get_linear_velocity()
        ang_vel = self._get_angular_velocity()
        lin_vel = np.array(lin_vel)
        ang_vel = np.array(ang_vel)

        tracking_lin_vel_reward, tracking_ang_vel_reward, lin_vel_z_penalty = (
            self._tracking_velocity_penalty(lin_vel, ang_vel)
        )
        helthy_reward = self.is_healthy
        feet_air_time_reward = self.feet_air_time_reward

        torque_cost = self.torque_cost(joint_velocities)
        action_diff_penalty = self._action_diff_penalty(action)
        xy_angular_velocity_cost = self.xy_angular_velocity_cost
        acceleration_cost = self.acceleration_cost
        orientation_cost = self.non_flat_base_cost
        default_joint_position_cost = self.default_joint_position_cost
        action_sym = self.action_sym(action)

        Positive_rewards = (
            tracking_lin_vel_reward * self.reward_weights["linear_vel_tracking"]
            + tracking_ang_vel_reward * self.reward_weights["angular_vel_tracking"]
            + helthy_reward * self.reward_weights["healthy"]
            + feet_air_time_reward * self.reward_weights["feet_airtime"]
        )

        Negative_rewards = (
            torque_cost * self.cost_weights["torque"]
            + action_diff_penalty * self.cost_weights["action_rate"]
            + lin_vel_z_penalty * self.cost_weights["vertical_vel"]
            + xy_angular_velocity_cost * self.cost_weights["xy_angular_vel"]
            + action_sym * self.cost_weights["action_sym"]
            + acceleration_cost * self.cost_weights["joint_acceleration"]
            + orientation_cost * self.cost_weights["orientation"]
            + default_joint_position_cost * self.cost_weights["default_joint_position"]
        )
        reward = Positive_rewards - Negative_rewards

        self.tracking_lin_vel_reward_ += (
            tracking_lin_vel_reward * self.reward_weights["linear_vel_tracking"]
        )
        self.tracking_ang_vel_reward_ += (
            tracking_ang_vel_reward * self.reward_weights["angular_vel_tracking"]
        )
        self.helthy_reward_ += helthy_reward * self.reward_weights["healthy"]
        self.feet_air_time_reward_ += (
            feet_air_time_reward * self.reward_weights["feet_airtime"]
        )

        self.torque_cost_ -= torque_cost * self.cost_weights["torque"]
        self.action_diff_penalty_ -= (
            action_diff_penalty * self.cost_weights["action_rate"]
        )
        self.lin_vel_z_penalty_ -= lin_vel_z_penalty * self.cost_weights["vertical_vel"]
        self.xy_angular_velocity_cost_ -= (
            xy_angular_velocity_cost * self.cost_weights["xy_angular_vel"]
        )
        self.action_sym_ -= action_sym * self.cost_weights["action_sym"]
        self.acceleration_cost_ -= (
            acceleration_cost * self.cost_weights["joint_acceleration"]
        )
        self.orientation_penalty_ -= orientation_cost * self.cost_weights["orientation"]
        self.default_joint_position_cost_ -= (
            default_joint_position_cost * self.cost_weights["default_joint_position"]
        )

        self.episode_reward_ += reward
        return reward

    def _action_diff_penalty(self, action):
        if not hasattr(self, "prev_action"):
            self.prev_action = np.zeros_like(action)

        action_diff_penalty = np.sum(np.abs(action - self.prev_action))
        return action_diff_penalty

    def _height_penalty(self):
        z = self._get_position_data()[-1]
        height_penalty = -((z - 0.3) ** 2) / 0.05**2
        return height_penalty

    def _tracking_velocity_penalty(self, lin_vel, ang_vel):
        v_x = lin_vel[0]
        lin_vel_error = np.sum(np.abs(self.target_lin_vel[0] - v_x))
        tracking_lin_vel_reward = np.exp(-lin_vel_error / self.tracking_sigma)
        ang_vel_error = np.sum(np.square(self.target_ang_vel - ang_vel[2]))
        tracking_ang_vel_reward = np.exp(-ang_vel_error / self.tracking_sigma)
        lin_vel_z_penalty = np.square((lin_vel[2]))
        return tracking_lin_vel_reward, tracking_ang_vel_reward, lin_vel_z_penalty

    @property
    def feet_air_time_reward(self):
        feet_contact_force_mag = self.feet_contact_forces
        curr_contact = feet_contact_force_mag > 1.0
        contact_filter = np.logical_or(curr_contact, self._last_contacts)
        self._last_contacts = curr_contact
        first_contact = (self._feet_air_time > 0.0) * contact_filter
        self._feet_air_time += self.model.opt.timestep * self.frame_skip
        air_time_reward = np.sum((self._feet_air_time) * first_contact)
        air_time_reward *= np.linalg.norm(self.target_lin_vel) > 0.1
        self._feet_air_time *= ~contact_filter
        return air_time_reward

    def torque_cost(self, joint_velocities):
        motor_torques = self.get_joint_effort()
        return np.sum(np.abs(motor_torques))

    @property
    def xy_angular_velocity_cost(self):
        return np.sum(np.square(self.data.qvel[5]))

    @property
    def is_healthy(self):
        _, _, z = self._get_position_data()
        roll, pitch, yaw = self._get_roll_pitch_yaw()
        min_z, max_z = self._healthy_z_range
        if not (min_z <= z <= max_z):
            return False

        min_roll, max_roll = self._healthy_roll_range
        if not (min_roll <= roll <= max_roll):
            return False

        min_pitch, max_pitch = self._healthy_pitch_range
        if not (min_pitch <= pitch <= max_pitch):
            return False

        min_yaw, max_yaw = self._healthy_yaw_range
        if not (min_yaw <= yaw <= max_yaw):
            return False

        return True

    @property
    def feet_contact_forces(self):
        feet_contact_forces = self.data.cfrc_ext[self._cfrc_ext_feet_indices].copy()
        return np.linalg.norm(feet_contact_forces, axis=1)

    @property
    def non_flat_base_cost(self):
        roll, pitch, _ = self._get_roll_pitch_yaw()
        return np.square(roll) + np.square(pitch)

    @property
    def default_joint_position_cost(self):
        joint_pos = self._get_joint_data()
        soft_joint_limits_low = self.joint_limits_low * 0.9
        soft_joint_limits_high = self.joint_limits_high * 0.9

        lower_violation = np.maximum(soft_joint_limits_low - joint_pos, 0)
        upper_violation = np.maximum(joint_pos - soft_joint_limits_high, 0)
        total_violation = lower_violation + upper_violation
        return np.sum(np.square(total_violation))

    def action_sym(self, action):
        in_phase_pairs_thigh = [(1, 7), (4, 10)]
        out_of_phase_pairs_thigh = [(1, 4), (7, 10)]
        out_of_phase_pairs_calf = [(2, 5), (8, 11)]
        in_phase_pairs_calf = [(2, 8), (5, 11)]

        jointpositions = self._get_joint_data()
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
        total_loss = loss_in + loss_out
        return total_loss

    @property
    def acceleration_cost(self):
        return np.sum(np.square(self.data.qacc[6:]))

    @property
    def projected_gravity(self):
        w, x, y, z = self.data.qpos[3:7]
        euler_orientation = np.array(self.euler_from_quaternion(w, x, y, z))
        projected_gravity_not_normalized = (
            np.dot(self._gravity_vector, euler_orientation) * euler_orientation
        )
        if np.linalg.norm(projected_gravity_not_normalized) == 0:
            return projected_gravity_not_normalized
        else:
            return projected_gravity_not_normalized / np.linalg.norm(
                projected_gravity_not_normalized
            )

    @staticmethod
    def euler_from_quaternion(w, x, y, z):
        roll  = np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
        pitch = np.arcsin(np.clip(2*(w*y - z*x), -1.0, 1.0))
        yaw   = np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
        return roll, pitch, yaw


env = UnitreeA1WalkEnv(headless=False)

reward_weights = {
    "linear_vel_tracking": 10.0,
    "angular_vel_tracking": 0.1,
    "healthy": 1.0,
    "feet_airtime": 20.0,
}
cost_weights = {
    "torque": 0.2,
    "vertical_vel": 0.0,
    "xy_angular_vel": 0.5,
    "action_rate": 0.2,
    "action_sym": 2.5,
    "joint_velocity": 0.01 * 0,
    "joint_acceleration": 2.5e-7 * 0,
    "orientation": 1.0 * 0,
    "collision": 1.0 * 0,
    "default_joint_position": 0.0,
}

env.set_weights(reward_weights, cost_weights)

policy_kwargs = {"net_arch": [dict(pi=[256, 128], vf=[256, 128])]}

model = PPO(
    "MlpPolicy",
    env,
    learning_rate=0.001,
    n_steps=500,
    batch_size=64,
    n_epochs=3,
    gamma=0.99,
    gae_lambda=0.92,
    clip_range=0.2,
    ent_coef=0.01,
    policy_kwargs=policy_kwargs,
)

model.learn(
    total_timesteps=100000,
    progress_bar=True,
)

env.close()
