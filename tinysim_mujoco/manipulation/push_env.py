import numpy as np

try:
    import mujoco
    from . import ManipulationBaseEnv
except ImportError:
    raise ImportError(
        "Mujoco is not properly installed. Install using `pip install tinysim[mujoco]`"
    )

_FLOAT_EPS = np.finfo(np.float64).eps
_EPS4 = _FLOAT_EPS * 4.0

from gymnasium import spaces


class ManipulationEnvV0:

    def __init__(self, **kwargs):
        self.env = ManipulationBaseEnv(**kwargs)
        self._model = self.env.model
        self._data = self.env.data
        self.frame_skip = 50
        self.dt = self._model.opt.timestep * self.frame_skip

        self._body_name2id = {}
        for body_id in range(self._model.nbody):
            name = mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_BODY, body_id)
            if name is not None:
                self._body_name2id[name] = body_id

        print("Body name to ID mapping:", self._body_name2id)

        self.joint_names = []
        for j in range(self._model.njnt):
            name = mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_JOINT, j)
            if name is not None:
                self.joint_names.append(name)

        # print each type of joint in the model
        print("Joint names:", self.joint_names)

        distance_threshold = 0.05
        self.neutral_joint_values = np.array(
            [0.00, 0.41, 0.00, -1.85, 0.00, 2.26, 0.79]
        )

        self.maximum_episode_steps = 128
        self.current_step = 0
        self.distance_threshold = distance_threshold

        self.goal = self.get_site_xpos(self._model, self._data, "goal_site").copy()
        self.initial_object_pos = self.get_site_xpos(
            self._model, self._data, "obj_site"
        ).copy()
        obs = self._get_obs()

        self.action_space = spaces.Box(-1.0, 1.0, shape=(7,), dtype="float32")
        self.observation_space = spaces.Dict(
            dict(
                desired_goal=spaces.Box(
                    -np.inf, np.inf, shape=obs["achieved_goal"].shape, dtype="float64"
                ),
                achieved_goal=spaces.Box(
                    -np.inf, np.inf, shape=obs["achieved_goal"].shape, dtype="float64"
                ),
                observation=spaces.Box(
                    -np.inf, np.inf, shape=obs["observation"].shape, dtype="float64"
                ),
            )
        )

        free_joint_index = self.joint_names.index("obj_joint")
        self.arm_joint_names = self.joint_names[:free_joint_index][0:7]
        # self.gripper_joint_names = self.joint_names[:free_joint_index][7:9]
        self.set_joint_neutral()

        mujoco.mj_forward(self._model, self._data)
        self.env.step(n_frames=self.frame_skip)

    def step(self, action):
        self.current_step += 1
        self._data.ctrl[:] = action
        self.env.step(n_frames=self.frame_skip)
        obs = self._get_obs()
        terminated = self._is_success(obs["achieved_goal"], self.goal)
        truncated = self.current_step >= self.maximum_episode_steps
        reward = self.compute_reward(obs["achieved_goal"], self.goal)
        return obs, reward, terminated, truncated, {}

    def mat2euler(self, mat):
        mat = np.asarray(mat, dtype=np.float64)
        cy = np.sqrt(mat[..., 2, 2] * mat[..., 2, 2] + mat[..., 1, 2] * mat[..., 1, 2])
        condition = cy > _EPS4
        euler = np.empty(mat.shape[:-1], dtype=np.float64)
        euler[..., 2] = np.where(
            condition,
            -np.arctan2(mat[..., 0, 1], mat[..., 0, 0]),
            -np.arctan2(-mat[..., 1, 0], mat[..., 1, 1]),
        )
        euler[..., 1] = np.where(
            condition,
            -np.arctan2(-mat[..., 0, 2], cy),
            -np.arctan2(-mat[..., 0, 2], cy),
        )
        euler[..., 0] = np.where(
            condition, -np.arctan2(mat[..., 1, 2], mat[..., 2, 2]), 0.0
        )
        return euler

    def get_site_xpos(self, model, data, name):
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)
        assert site_id != -1, f"Site with name '{name}' is not part of the model!"
        return data.site_xpos[site_id]

    def get_site_xvelp(self, model, data, name):
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)
        assert site_id != -1, f"Site with name '{name}' is not part of the model!"
        jacp = self.get_site_jacp(model, data, site_id)
        xvelp = jacp @ data.qvel
        return xvelp

    def get_site_jacp(self, model, data, site_id):
        jacp = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jacp, None, site_id)
        return jacp

    def _get_obs(self) -> dict:
        ee_position = self.get_site_xpos(self._model, self._data, "tip").copy()
        ee_velocity = (
            self.get_site_xvelp(self._model, self._data, "tip").copy() * self.dt
        )
        object_position = self.get_site_xpos(self._model, self._data, "obj_site").copy()
        object_rotation = self.mat2euler(
            self.get_site_xmat(self._model, self._data, "obj_site")
        )

        return {
            "observation": np.concatenate(
                [
                    ee_position,
                    ee_velocity,
                    object_position,
                    object_rotation,
                ]
            ).copy(),
            "achieved_goal": object_position.copy(),
            "desired_goal": self.goal.copy(),
        }

    def set_joint_qpos(self, model, data, name, value):
        """Set the joint positions (qpos) of the model."""
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        joint_addr = model.jnt_qposadr[joint_id]
        # All joints are assumed to be of type mjJNT_HINGE in this environment
        data.qpos[joint_addr] = value

    def set_object_qpos(self, model, data):
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "obj_joint")
        joint_addr = model.jnt_qposadr[joint_id]
        data.qpos[joint_addr : joint_addr + 3] = np.array(self.initial_object_pos)
        # reset orientation
        data.qpos[joint_addr + 3 : joint_addr + 7] = np.array([1.0, 0.0, 0.0, 0.0])

    def _sample_goal(self):
        goal = np.array([0.3, 0.0, 0.0])
        return goal

    def goal_distance(self, goal_a, goal_b):
        assert goal_a.shape == goal_b.shape
        return np.linalg.norm(goal_a - goal_b, axis=-1)

    def compute_reward(self, achieved_goal, desired_goal, info=None):
        d = self.goal_distance(achieved_goal, desired_goal)
        # give reward for the end effector being close to the object
        # ee_position = self.get_site_xpos(self._model, self._data, "tip")
        # object_position = self.get_site_xpos(self._model, self._data, "obj_site")
        # ee_object_distance = np.linalg.norm(ee_position - object_position, axis=-1)

        # # the arm tries to cheat by moving the object with the side of the gripper
        # # negative ward if the arm contacts the ground with
        # effector_distance_reward = -0.1 * (ee_object_distance > 0.05).astype(np.float32)
        # reward = -d + effector_distance_reward
        return -(d > self.distance_threshold).astype(np.float32)

    def _is_success(self, achieved_goal, desired_goal):
        d = self.goal_distance(achieved_goal, desired_goal)
        return (d < self.distance_threshold).astype(np.float32)

    def set_joint_neutral(self):
        for name, value in zip(self.arm_joint_names, self.neutral_joint_values):
            self.set_joint_qpos(self._model, self._data, name, value)

    def _reset_sim(self) -> bool:
        self.set_joint_neutral()
        self.set_object_qpos(self._model, self._data)
        mujoco.mj_forward(self._model, self._data)

    def reset(self, **kwargs):
        self.current_step = 0
        self._reset_sim()
        obs = self._get_obs()

        # self.env.step(n_frames=self.frame_skip)
        # frame = self.env.viewer.capture_frame()
        # import matplotlib.pyplot as plt
        # plt.imsave("debug_frame.png", frame)
        # raise Exception("Debug")
        return obs, {}

    def get_site_xmat(self, model, data, name: str):
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)
        assert site_id != -1, f"Site with name '{name}' is not part of the model!"
        return data.site_xmat[site_id].reshape(3, 3)

    def get_body_state(self, name):
        body_id = self._body_name2id[name]
        body_xpos = self._data.xpos[body_id]
        body_xquat = self._data.xquat[body_id]
        return np.concatenate([body_xpos, body_xquat])