import pathlib
import numpy as np

from tinysim_warp import WarpBaseEnv

import warp as wp
import warp.examples


class RobotDogBaseEnv(WarpBaseEnv):
    def build_model(self):
        builder = wp.sim.ModelBuilder()
        articulation_builder = wp.sim.ModelBuilder()
        rot_x = wp.quat_from_axis_angle(wp.vec3(1.0, 0.0, 0.0), -np.pi * 0.5)
        rot_y = wp.quat_from_axis_angle(wp.vec3(0.0, 1.0, 0.0), np.pi * 0.5)
        xform = wp.transform(wp.vec3(0.0, 0.65, 0.0), rot_y * rot_x)
        wp.sim.parse_urdf(
            str(pathlib.Path(warp.examples.get_asset_directory()) / "quadruped.urdf"),
            articulation_builder,
            xform=xform,
            floating=True,
            density=900,
            armature=0.01,
            stiffness=200,
            damping=1,
            contact_ke=1.0e4,
            contact_kd=1.0e2,
            contact_kf=1.0e2,
            contact_mu=1.0,
            limit_ke=1.0e4,
            limit_kd=1.0e1,
        )

        for i in range(self.num_envs):
            builder.add_builder(
                articulation_builder,
                xform=wp.transform(self.env_offsets[i], wp.quat_identity()),
            )
            builder.joint_q[-12:] = [0.2, 0.4, -0.6, -0.2, -0.4, 0.6, -0.2, 0.4, -0.6, 0.2, -0.4, 0.6] # fmt: skip
            builder.joint_act[-12:] = [0.2, 0.4, -0.6, -0.2, -0.4, 0.6, -0.2, 0.4, -0.6, 0.2, -0.4, 0.6] # fmt: skip
            builder.joint_axis_mode = [wp.sim.JOINT_MODE_TARGET_POSITION] * len(
                builder.joint_axis_mode
            )

        model = builder.finalize()
        model.joint_attach_ke = 16000.0
        model.joint_attach_kd = 200.0
        return model

    def solver(self):
        return wp.sim.FeatherstoneIntegrator(
            self.model, use_tile_gemm=False, fuse_cholesky=False
        )

    def apply_actions(self, actions):
        # Set the target positions for all legs
        action_space_size = 12 * self.num_envs
        if len(actions) != action_space_size:
            raise ValueError(
                f"Expected {action_space_size} actions, but got {len(actions)}"
            )

        wp.copy(self.model.joint_act, wp.array(actions, dtype=wp.float32))

    def get_obs(self):
        return
