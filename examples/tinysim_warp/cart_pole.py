import argparse

import warp as wp

from tinysim_warp.cart_pole import CartPoleBaseEnv

# requirements: `pip install tinysim[warp]`

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
    example = CartPoleBaseEnv(use_cuda_graph=True)

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

    example.renderer.save()
