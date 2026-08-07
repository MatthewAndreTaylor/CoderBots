import numpy as np
import warp as wp

from picogym_warp import WarpBaseEnv

quat_id = wp.quat_identity()


class CartPoleBaseEnv(WarpBaseEnv):

    actions = np.array([0.0, 0.5, -0.5])

    def build_model(self):
        builder = wp.sim.ModelBuilder()
        for i in range(self.num_envs):
            builder.add_builder(
                self.create_cartpole(),
                xform=wp.transform(self.env_offsets[i], quat_id),
            )

        model = builder.finalize()
        model.joint_attach_ke = 1000.0
        model.joint_attach_kd = 1.0
        self.joint_act_np = np.zeros(model.joint_dof_count, dtype=np.float32)
        self.joint_act_wp = wp.array(
            self.joint_act_np, dtype=float, device=wp.get_device()
        )
        model.joint_act = self.joint_act_wp
        return model

    def create_cartpole(self):
        """Create cartpole system using pure Python/Warp API"""
        builder = wp.sim.ModelBuilder(gravity=-0.3)
        cart_body = builder.add_body(
            origin=wp.transform(wp.vec3(0.0, 2.0, 0.0), quat_id), m=1.0
        )
        builder.add_shape_sphere(body=cart_body, radius=0.1, density=100.0)

        # Start angled pole
        pole_body = builder.add_body(
            origin=wp.transform(wp.vec3(0.0, 2.5, 0.0), quat_id), m=0.01
        )
        pole_size = wp.vec3(0.04, 1.0, 0.06)
        builder.add_shape_box(
            body=pole_body,
            hx=pole_size[0] / 2.0,
            hy=pole_size[1] / 2.0,
            hz=pole_size[2] / 2.0,
            density=50.0,
        )
        # Joint starts with a small initial angle
        q = wp.quat_from_axis_angle(wp.vec3(0.0, 0.0, 1.0), 0.01)
        builder.add_joint_revolute(
            parent=cart_body,
            child=pole_body,
            axis=wp.vec3(0.0, 0.0, 1.0),  # rotation around Z-axis
            child_xform=wp.transform(wp.vec3(0.0, -0.5, 0.0), q),
            limit_ke=1.0e4,
            limit_kd=1.0e1,
        )
        builder.add_joint_prismatic(
            parent=-1,
            child=cart_body,
            parent_xform=wp.transform(wp.vec3(0.0, 2.0, 0.0), quat_id),
            limit_lower=-5.0,
            limit_upper=5.0,
            limit_ke=1.0e4,
            limit_kd=1.0e2,
        )
        builder.joint_axis_mode = [wp.sim.JOINT_MODE_FORCE] * len(
            builder.joint_axis_mode
        )
        return builder

    def solver(self):
        return wp.sim.SemiImplicitIntegrator()

    def apply_actions(self, actions):
        if len(actions) != self.num_envs:
            raise ValueError("Length of actions must match number of environments.")

        act = np.zeros(self.model.joint_dof_count, dtype=np.float32)
        dof_indices = np.arange(self.num_envs) * 2 + 1
        act[dof_indices] = self.actions[actions]
        wp.copy(self.model.joint_act, wp.array(act, dtype=wp.float32))

    def get_state_vector(self):
        cart_id, pole_id = 0, 1  # body indices
        body_q = self.state_0.body_q.numpy()
        body_qd = self.state_0.body_qd.numpy()
        cart_pos = body_q[cart_id]  # [px, py, pz, qx, qy, qz, qw]
        cart_pos = cart_pos[[0]]  # cart_pos = cart_pos[[0, 2]]
        pole_quat = body_q[pole_id][3:]  # quaternion part
        pole_vel = body_qd[pole_id][3:]  # angular velocity part
        return np.concatenate([cart_pos, pole_quat, pole_vel])

    def get_obs(self):
        obs = self.get_state_vector()
        pole_quat = obs[1:5]
        qw = float(np.clip(pole_quat[3], -1.0, 1.0))
        tilt = 2.0 * np.arccos(qw)  # radians, in [0, pi]
        max_tilt = np.deg2rad(90.0)
        return obs, 1.0, tilt > max_tilt
