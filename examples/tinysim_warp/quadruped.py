import argparse
from tinysim_warp.quadruped import RobotDogBaseEnv

import warp as wp

# requirements: `pip install tinysim[warp]`

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    "--device", type=str, default=None, help="Override the default Warp device."
)
parser.add_argument(
    "--num-frames", type=int, default=300, help="Total number of frames."
)
parser.add_argument(
    "--num-envs",
    type=int,
    default=3,
    help="Total number of simulated environments.",
)

args = parser.parse_known_args()[0]

with wp.ScopedDevice(args.device):
    example = RobotDogBaseEnv(num_envs=args.num_envs)
    # [
    #     (front right leg out),
    #     (front right leg forward),
    #     (front right forearm forward),

    #     (front left leg out),
    #     (front left leg forward),
    #     (front left forearm forward),

    #     (back right leg out),
    #     (back right leg forward),
    #     (back right forearm forward),

    #     (back left leg out),
    #     (back left leg forward),
    #     (back left forearm forward),
    # ]
    # left and right directions are reversed

    actions = [0.2, 0.4, -0.6, -0.2, -0.4, 0.6, -0.2, 0.4, -0.6, 0.2, -0.4, 0.6] * args.num_envs # fmt: skip

    for i in range(args.num_frames):
        example.step(actions)
        example.render()

        if i % 10 == 0:
            # Stretch the right leg to the side
            # actions[0] += 0.1

            # Stretch the right leg forward
            actions[1] += 0.1

            # Strecth the forearm foward
            # actions[2] += 0.1

            # Stretch the left leg forward
            actions[4] -= 0.1

            # Back right leg backwards
            # actions[7] += 0.1

    example.renderer.save()
