# written by: Matthew Taylor
# source: https://github.com/MatthewAndreTaylor/WarpSimBalance

import warp as wp
import warp.sim.render
import numpy as np
import enum


@wp.kernel
def set_cart_kernel(
    body_q: wp.array(dtype=wp.transform), control_pos: wp.array(dtype=wp.vec3)
):
    body_q[0] = wp.transform(control_pos[0], wp.quat_identity())


class ActionSpaceType(enum.Enum):
    CONTINUOUS = enum.auto()
    DISCRETE = enum.auto()


class CartPoleExample:
    def __init__(self, use_cuda_graph=False, headless=False):
        self.gravity = -1.0
        builder = wp.sim.ModelBuilder(gravity=self.gravity)
        self.create_cartpole(builder)

        self.action_space_type = ActionSpaceType.DISCRETE
        self.actions = [
            wp.vec3(0.0, 0.0, 0.0),  # No movement
            wp.vec3(0.05, 0.0, 0.0),  # Move right
            wp.vec3(-0.05, 0.0, 0.0),  # Move left
        ]

        self.sim_time = 0.0
        self.current_pos = wp.vec3(0.0, 2.0, 0.0)
        self.current_pos_array = wp.array(
            [self.current_pos], dtype=wp.vec3, device=wp.get_device()
        )
        self.curr_speed = wp.vec3(0.0, 0.0, 0.0)

        fps = 120
        self.frame_dt = 1.0 / fps

        self.sim_substeps = 30
        self.sim_dt = self.frame_dt / self.sim_substeps

        # finalize model
        self.model = builder.finalize()
        self.model.ground = False
        self.model.joint_attach_ke = 150.0
        self.model.joint_attach_kd = 1.0

        self.integrator = wp.sim.SemiImplicitIntegrator()
        self.renderer = wp.sim.render.SimRendererOpenGL(
            self.model, "example", headless=headless
        )
        self.state = self.model.state()

        wp.sim.eval_fk(self.model, self.model.joint_q, self.model.joint_qd, None, self.state)

        # CUDA graph
        self.use_cuda_graph = use_cuda_graph and wp.get_device().is_cuda and wp.is_mempool_enabled(wp.get_device())
        self.graph = None
        if self.use_cuda_graph:
            with wp.ScopedCapture() as capture:
                self.simulate()
            self.graph = capture.graph

        self.step(action=1)

    def create_cartpole(self, builder):
        """Create cartpole system using pure Python/Warp API"""
        pole_size = wp.vec3(0.04, 1.0, 0.06)
        cart_body = builder.add_body(
            origin=wp.transform(wp.vec3(0.0, 2.0, 0.0), wp.quat_identity()), m=0.0
        )
        builder.add_shape_sphere(body=cart_body, radius=0.1, density=0.0)
        pole_body = builder.add_body(
            origin=wp.transform(wp.vec3(0.0, 2.5, 0.0), wp.quat_identity()),
        )
        builder.add_shape_box(
            body=pole_body,
            pos=wp.vec3(0.0, 0.0, 0.0),
            hx=pole_size[0] / 2.0,
            hy=pole_size[1] / 2.0,
            hz=pole_size[2] / 2.0,
            density=50.0,
        )
        # builder.add_joint_ball(
        #     parent=cart_body,
        #     child=pole_body,
        #     parent_xform=wp.transform(wp.vec3(0.0, 0.0, 0.0), wp.quat_identity()),
        #     child_xform=wp.transform(wp.vec3(0.0, -0.5, 0.0), wp.quat_identity()),
        # )
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

    def set_cart_trajectory(self, action):

        if self.action_space_type == ActionSpaceType.CONTINUOUS:
            raise NotImplementedError("Continuous action space not implemented")

        elif self.action_space_type == ActionSpaceType.DISCRETE:
            discrete_action = self.actions[action]
            # Add velocity damping/friction
            damping = 0.97  # 0 < damping < 1, lower = more friction
            self.curr_speed *= damping
            self.curr_speed += discrete_action
            self.current_pos += self.curr_speed * self.frame_dt

            # copy buffer
            new_pos = wp.array(
                [self.current_pos], dtype=wp.vec3, device=wp.get_device()
            )
            wp.copy(self.current_pos_array, new_pos)

    def is_fallen(self, pole_quat):
        qw = float(np.clip(pole_quat[3], -1.0, 1.0))
        tilt = 2.0 * np.arccos(qw)  # radians, in [0, pi]

        # threshold: 90 degrees (tunable)
        max_tilt = np.deg2rad(90.0)
        return tilt > max_tilt

    def reset(self):
        self.current_pos = wp.vec3(0.0, 2.0, 0.0)
        self.current_speed = wp.vec3(0.0, 0.0, 0.0)
        self.sim_time = 0.0
        builder = wp.sim.ModelBuilder(gravity=self.gravity)
        self.create_cartpole(builder)
        self.model = builder.finalize()
        self.model.joint_attach_ke = 150.0
        self.model.joint_attach_kd = 1.0
        self.state = self.model.state()
        self.step(action=1)
        return self.get_state_vector()

    def step(self, action):
        """Apply action and step the simulation for one environment timestep.

        Returns (observation, reward, terminated)
        """
        self.set_cart_trajectory(action)

        if self.use_cuda_graph:
            wp.capture_launch(self.graph)
        else:
            self.simulate()

        self.sim_time += self.frame_dt
        obs = self.get_state_vector()
        pole_quat = obs[1:5]  # quaternion part (qx, qy, qz, qw)

        # Check if the pole has fallen by computing the tilt angle from the
        # quaternion. For the upright pole the quaternion is identity (angle=0).
        # We compute angle = 2*arccos(qw). If it exceeds a threshold the pole
        # is considered fallen.
        terminated = self.is_fallen(pole_quat)
        return obs, 1.0, terminated

    def simulate(self):
        for _ in range(self.sim_substeps):
            self.state.clear_forces()
            self.state = self.integrator.simulate(
                self.model, self.state, self.state, self.sim_dt
            )

        wp.launch(
            set_cart_kernel, dim=1, inputs=[self.state.body_q, self.current_pos_array]
        )

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
        example = CartPoleExample(use_cuda_graph=False)

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

            obs, reward, terminated = example.step(action=action)
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