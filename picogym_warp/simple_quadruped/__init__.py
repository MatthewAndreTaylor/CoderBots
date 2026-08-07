import pathlib

import numpy as np
import warp as wp

from picogym_warp import WarpBaseEnv


class SimpleRobotDogBaseEnv(WarpBaseEnv):
    def build_model(self):
        builder = wp.sim.ModelBuilder()
        articulation_builder = wp.sim.ModelBuilder()
        rot_x = wp.quat_from_axis_angle(wp.vec3(1.0, 0.0, 0.0), -np.pi * 0.5)
        rot_y = wp.quat_from_axis_angle(wp.vec3(0.0, 1.0, 0.0), np.pi * 0.5)
        xform = wp.transform(wp.vec3(0.0, 0.35, 0.0), rot_y * rot_x)
        wp.sim.parse_urdf(
            # os.path.join(warp.examples.get_asset_directory(), "quadruped.urdf"),
            str(pathlib.Path(__file__).parent / "simple_quadruped.urdf"),
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
            builder.joint_q[-8:] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] # fmt: skip
            builder.joint_act[-8:] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] # fmt: skip
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
        action_space_size = 8 * self.num_envs
        if len(actions) != action_space_size:
            raise ValueError(
                f"Expected {action_space_size} actions, but got {len(actions)}"
            )

        wp.copy(self.model.joint_act, wp.array(actions, dtype=wp.float32))

    def get_obs(self):
        return


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--device", type=str, default=None, help="Override the default Warp device."
    )
    parser.add_argument(
        "--num-frames", type=int, default=1500, help="Total number of frames."
    )
    parser.add_argument(
        "--num-envs",
        type=int,
        default=3,
        help="Total number of simulated environments.",
    )

    args = parser.parse_known_args()[0]

    with wp.ScopedDevice(args.device):
        example = SimpleRobotDogBaseEnv(num_envs=args.num_envs)

        for frame in range(args.num_frames):
            example.step(np.zeros(8).repeat(args.num_envs))
            example.render()

    example.renderer.save()
