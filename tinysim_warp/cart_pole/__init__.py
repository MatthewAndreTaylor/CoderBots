# written by: Matthew Taylor
# source: https://github.com/MatthewAndreTaylor/WarpSimBalance

try:
    import warp as wp
    import warp.sim.render
except ImportError:
    raise ImportError(
        "Warp is not installed. Install using `pip install coderbot_sim[warp]`"
    )

import numpy as np


def compute_env_offsets(num_envs, env_offset=(5.0, 0.0, 0.0)):
    env_offset = np.array(env_offset, dtype=float)
    axis = np.nonzero(env_offset)[0]
    axis = axis[0] if len(axis) else 0
    env_offsets = np.zeros((num_envs, 3))
    env_offsets[:, axis] = np.arange(num_envs) * env_offset[axis]
    env_offsets -= env_offsets.mean(axis=0)
    env_offsets[:, 1] = 0.0
    return env_offsets


class CartPoleExample:
    def __init__(self, use_cuda_graph=False, headless=False, num_envs=3):
        self.actions = np.array([0.0, 0.5, -0.5])
        self.num_envs = num_envs

        fps = 60
        self.frame_dt = 1.0 / fps
        self.sim_substeps = 10
        self.sim_dt = self.frame_dt / self.sim_substeps

        self.initialize()

        self.integrator = wp.sim.SemiImplicitIntegrator()
        self.renderer = wp.sim.render.SimRendererOpenGL(
            self.model, "example", headless=headless
        )

        # CUDA graph
        self.use_cuda_graph = (
            use_cuda_graph
            and wp.get_device().is_cuda
            and wp.is_mempool_enabled(wp.get_device())
        )
        if self.use_cuda_graph:
            with wp.ScopedCapture() as capture:
                self.simulate()
            self.graph = capture.graph

        self.step(actions=[1] * self.num_envs)

    def create_cartpole(self):
        """Create cartpole system using pure Python/Warp API"""
        builder = wp.sim.ModelBuilder(gravity=-0.3)
        pole_size = wp.vec3(0.04, 1.0, 0.06)
        cart_body = builder.add_body(
            origin=wp.transform(wp.vec3(0.0, 2.0, 0.0), wp.quat_identity()), m=1.0
        )
        builder.add_shape_sphere(body=cart_body, radius=0.1, density=100.0)
        pole_body = builder.add_body(
            origin=wp.transform(wp.vec3(0.0, 2.5, 0.0), wp.quat_identity()), m=0.01
        )
        builder.add_shape_box(
            body=pole_body,
            pos=wp.vec3(0.0, 0.0, 0.0),
            hx=pole_size[0] / 2.0,
            hy=pole_size[1] / 2.0,
            hz=pole_size[2] / 2.0,
            density=50.0,
        )
        builder.add_joint_revolute(
            parent=cart_body,
            child=pole_body,
            axis=wp.vec3(0.0, 0.0, 1.0),  # rotation around Z-axis
            parent_xform=wp.transform(wp.vec3(0.0, 0.0, 0.0), wp.quat_identity()),
            child_xform=wp.transform(
                wp.vec3(0.0, -0.5, 0.0), wp.quat_identity()
            ),  # joint at pole base
            limit_ke=1.0e4,
            limit_kd=1.0e1,
        )
        builder.add_joint_prismatic(
            parent=-1,
            child=cart_body,
            axis=wp.vec3(1.0, 0.0, 0.0),
            parent_xform=wp.transform(wp.vec3(0.0, 2.0, 0.0), wp.quat_identity()),
            child_xform=wp.transform(wp.vec3(0.0, 0.0, 0.0), wp.quat_identity()),
            limit_lower=-5.0,
            limit_upper=5.0,
            limit_ke=1.0e4,
            limit_kd=1.0e2,
        )
        builder.joint_axis_mode = [wp.sim.JOINT_MODE_FORCE] * len(
            builder.joint_axis_mode
        )
        return builder

    def set_cart_trajectory(self, actions):
        if len(actions) != self.num_envs:
            raise ValueError("Length of actions must match number of environments.")

        act = np.zeros(self.model.joint_dof_count, dtype=np.float32)
        dof_indices = np.arange(self.num_envs) * 2 + 1
        act[dof_indices] = self.actions[actions]
        wp.copy(self.model.joint_act, wp.array(act, dtype=wp.float32))

    def is_fallen(self, pole_quat):
        qw = float(np.clip(pole_quat[3], -1.0, 1.0))
        tilt = 2.0 * np.arccos(qw)  # radians, in [0, pi]
        max_tilt = np.deg2rad(90.0)
        return tilt > max_tilt

    def step(self, actions):
        """Apply action and step the simulation for one environment timestep.

        Returns (observation, reward, terminated)
        """
        self.set_cart_trajectory(actions)
        if self.use_cuda_graph:
            wp.capture_launch(self.graph)
        else:
            self.simulate()

        self.sim_time += self.frame_dt
        obs = self.get_state_vector()
        pole_quat = obs[1:5]
        terminated = self.is_fallen(pole_quat)
        return obs, 1.0, terminated

    def simulate(self):
        for _ in range(self.sim_substeps):
            self.state.clear_forces()
            self.state = self.integrator.simulate(
                self.model, self.state, self.state, self.sim_dt
            )

    def reset(self):
        self.initialize()
        return self.step(actions=[1] * self.num_envs)

    def initialize(self):
        self.sim_time = 0.0
        builder = wp.sim.ModelBuilder()
        offsets = compute_env_offsets(self.num_envs)

        for i in range(self.num_envs):
            builder.add_builder(
                self.create_cartpole(),
                xform=wp.transform(offsets[i], wp.quat_identity()),
            )

        self.model = builder.finalize()
        self.model.joint_attach_ke = 1000.0
        self.model.joint_attach_kd = 1.0
        self.state = self.model.state()

        wp.sim.eval_fk(
            self.model, self.model.joint_q, self.model.joint_qd, None, self.state
        )
        self.joint_act_np = np.zeros(self.model.joint_dof_count, dtype=np.float32)
        self.joint_act_wp = wp.array(
            self.joint_act_np, dtype=float, device=wp.get_device()
        )
        self.model.joint_act = self.joint_act_wp

    def render(self):
        self.renderer.begin_frame(self.sim_time)
        self.renderer.render(self.state)
        self.renderer.end_frame()

    def get_state_vector(self):
        cart_id = 0
        pole_id = 1

        # convert transforms to numpy
        body_q = self.state.body_q.numpy()
        body_qd = self.state.body_qd.numpy()

        # --- Cart ---
        cart_pos = body_q[cart_id]  # [px, py, pz, qx, qy, qz, qw]
        # cart_pos = cart_pos[[0, 2]]
        cart_pos = cart_pos[[0]]

        # --- Pole ---
        pole_quat = body_q[pole_id][3:]  # quaternion part
        pole_vel = body_qd[pole_id][3:]  # angular velocity part

        return np.concatenate([cart_pos, pole_quat, pole_vel])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--device", type=str, default=None, help="Override the default Warp device."
    )
    parser.add_argument(
        "--num-frames", type=int, default=1200, help="Total number of frames."
    )
    parser.add_argument(
        "--manual-control", action="store_true", help="Enable manual control."
    )

    args = parser.parse_known_args()[0]

    if args.manual_control:
        print("Manual control enabled")
        import keyboard

    with wp.ScopedDevice(args.device):
        example = CartPoleExample(use_cuda_graph=True)

        terminated = False
        check_terminated = True

        for i in range(args.num_frames):
            if args.manual_control:
                # Manual control logic
                if keyboard.is_pressed("k"):
                    action = 2
                elif keyboard.is_pressed("l"):
                    action = 1
                else:
                    action = 0

            else:
                # Example control signals
                if i < 200:
                    action = 0
                elif i < 255:  # 260
                    action = 2
                else:
                    action = 0

            obs, reward, terminated = example.step(actions=[action] * example.num_envs)
            # print(f"Step {i}")

            if check_terminated and terminated:
                print("Pole fallen")
                check_terminated = False

            example.render()

            # print("State Vector:", obs)
            # print("Reward:", reward)
            # print("Terminated:", terminated)

        state = example.reset()
        print("Reset State Vector:", state)
        example.render()

        example.renderer.save()
