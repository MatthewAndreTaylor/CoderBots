import math
import os
import pathlib

import numpy as np

try:
    import warp as wp
    import warp.sim.render
except ImportError:
    raise ImportError(
        "Warp is not installed. Install using `pip install tinysim[warp]`"
    )


def compute_env_offsets(num_envs, env_offset=(5.0, 0.0, 0.0)):
    env_offset = np.array(env_offset, dtype=float)
    axis = np.nonzero(env_offset)[0]
    axis = axis[0] if len(axis) else 0
    env_offsets = np.zeros((num_envs, 3))
    env_offsets[:, axis] = np.arange(num_envs) * env_offset[axis]
    env_offsets -= env_offsets.mean(axis=0)
    env_offsets[:, 1] = 0.0
    return env_offsets


class SimpleRobotDogExample:
    def __init__(self, use_cuda_graph=False, headless=False, num_envs=8):
        articulation_builder = wp.sim.ModelBuilder()
        rot_x = wp.quat_from_axis_angle(wp.vec3(1.0, 0.0, 0.0), -math.pi * 0.5)
        rot_y = wp.quat_from_axis_angle(wp.vec3(0.0, 1.0, 0.0), math.pi * 0.5)
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

        builder = wp.sim.ModelBuilder()

        self.sim_time = 0.0
        fps = 100
        self.frame_dt = 1.0 / fps

        self.sim_substeps = 10
        self.sim_dt = self.frame_dt / self.sim_substeps

        self.num_envs = num_envs
        offsets = compute_env_offsets(self.num_envs)

        for i in range(self.num_envs):
            builder.add_builder(
                articulation_builder, xform=wp.transform(offsets[i], wp.quat_identity())
            )
            builder.joint_q[-8:] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] # fmt: skip
            builder.joint_act[-8:] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] # fmt: skip
            builder.joint_axis_mode = [wp.sim.JOINT_MODE_TARGET_POSITION] * len(
                builder.joint_axis_mode
            )

        # finalize model
        self.model = builder.finalize()
        self.model.ground = True
        self.model.joint_attach_ke = 16000.0
        self.model.joint_attach_kd = 200.0
        self.use_tile_gemm = False
        self.fuse_cholesky = False

        self.integrator = wp.sim.FeatherstoneIntegrator(
            self.model,
            use_tile_gemm=self.use_tile_gemm,
            fuse_cholesky=self.fuse_cholesky,
        )

        self.renderer = wp.sim.render.SimRendererOpenGL(
            self.model, "example", headless=headless
        )
        self.state_0 = self.model.state()
        self.state_1 = self.model.state()

        wp.sim.eval_fk(
            self.model, self.model.joint_q, self.model.joint_qd, None, self.state_0
        )

        self.use_cuda_graph = (
            use_cuda_graph
            and wp.get_device().is_cuda
            and wp.is_mempool_enabled(wp.get_device())
        )
        if self.use_cuda_graph:
            with wp.ScopedCapture() as capture:
                self.simulate()
            self.graph = capture.graph

    def simulate(self):
        for _ in range(self.sim_substeps):
            self.state_0.clear_forces()
            wp.sim.collide(self.model, self.state_0)
            self.integrator.simulate(
                self.model, self.state_0, self.state_1, self.sim_dt
            )
            self.state_0, self.state_1 = self.state_1, self.state_0

    def set_leg_poses(self, actions):
        action_space_size = 8 * self.num_envs
        if len(actions) != action_space_size:
            raise ValueError(
                f"Expected {action_space_size} actions, but got {len(actions)}"
            )

        wp.copy(self.model.joint_act, wp.array(actions, dtype=wp.float32))

    def step(self, actions):
        self.set_leg_poses(actions)

        if self.use_cuda_graph:
            wp.capture_launch(self.graph)
        else:
            self.simulate()
        self.sim_time += self.frame_dt

    def render(self):
        self.renderer.begin_frame(self.sim_time)
        self.renderer.render(self.state_0)
        self.renderer.end_frame()


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
        example = SimpleRobotDogExample(num_envs=args.num_envs)

        for frame in range(args.num_frames):
            example.step(np.zeros(8).repeat(args.num_envs))
            example.render()

    example.renderer.save()
