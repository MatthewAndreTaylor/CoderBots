import argparse
import warp as wp
import numpy as np
from tinysim_warp.simple_quadruped import SimpleRobotDogExample

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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

    HIP_AMP = 0.3
    THIGH_AMP = 0.5

    freq = 5.0
    phase = 0.0

    # Joint indices per leg: (hip, thigh)
    LEGS = [
        (0, 1),  # FRONT RIGHT
        (2, 3),  # FRONT LEFT
        (4, 5),  # BACK RIGHT
        (6, 7),  # BACK LEFT
    ]

    def step_frames(dt, phase):
        phase += 2 * np.pi * freq * dt
        phase = phase % (2 * np.pi)
        actions = np.zeros(8)

        # Which leg is active this cycle quarter
        leg_idx = int((phase / (2 * np.pi)) * 4)
        hip_i, thigh_i = LEGS[leg_idx]

        # Local phase within this leg's window [0, π/2]
        local_phase = (phase % (2 * np.pi / 4)) * 4

        hip_val = HIP_AMP * np.sin(local_phase)
        thigh_val = THIGH_AMP * np.sin(local_phase)
        actions[hip_i] = hip_val
        actions[thigh_i] = thigh_val

        # fmt: off
        directions = np.array([
            1,  1,   # right front leg outward, forward
            -1, -1,   # left front leg inward, backward
            -1, -1,   # right back leg inward, backward
            1,  1    # left back leg outward, forward
        ])
        # fmt: on

        return np.repeat(actions * directions, args.num_envs), phase

    for frame in range(args.num_frames):
        actions, phase = step_frames(example.frame_dt, phase)
        example.step(actions)
        example.render()

example.renderer.save()
