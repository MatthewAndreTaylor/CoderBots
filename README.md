
# TinySim 

[![PyPI](https://img.shields.io/pypi/v/tinysim.svg)](https://pypi.org/project/tinysim)
[![Jupyterlite](https://jupyterlite.rtfd.io/en/latest/_static/badge.svg)](https://matthewandretaylor.github.io/TinySim)

The goal of this project is to create more minimal simulation environments for robotics and machine learning.

Existing solutions like [ROS 2](https://github.com/ros2) and [Gymnasium](https://gymnasium.farama.org/) come with many heavy dependencies.

Additionally they are usually difficult to get setup and may require domain specific knowledge to use.
Simulation environments should be able to run in any notebook environment and require fewer dependencies.


## Get Started 🚀

To use the baseline Python only simulation environments.

```bash
pip install tinysim
```

| [MountainCarEnv](https://github.com/MatthewAndreTaylor/TinySim/blob/main/tinysim/mountain_car) | [TopDownDrivingEnv](https://github.com/MatthewAndreTaylor/TinySim/blob/main/tinysim/topdown_driving) |
|:-------------------------:|:-------------------------:|
| <img width="312" alt="mountain_car" src="https://github.com/user-attachments/assets/adbde7f4-6b4e-4c06-8dd3-ea278d5576ad" /> | <img width="312" alt="topdown_driving" src="https://github.com/user-attachments/assets/79dcbf45-055e-4a4e-b6ff-38e938e99a4e" /> |

| [FroggerEnv](https://github.com/MatthewAndreTaylor/TinySim/blob/main/tinysim/frogger) | [FlappyEnv](https://github.com/MatthewAndreTaylor/TinySim/blob/main/tinysim/flappy) |
|:-------------------------:|:-------------------------:|
| <img width="312" alt="frogger" src="https://github.com/user-attachments/assets/bb9a8382-b9a0-4280-ae23-cbd02e2d78f6" /> | <img width="312" alt="flappy" src="https://github.com/user-attachments/assets/b5e2a502-d9fe-4ff1-9e4e-a47f7e50ebd9" /> |


To use the [warp](https://github.com/NVIDIA/warp) simulation environments.

```bash
pip install tinysim[warp]
```

| [CartPoleBaseEnv](https://github.com/MatthewAndreTaylor/TinySim/tree/main/tinysim_warp/cart_pole) | [SimpleRobotDogBaseEnv](https://github.com/MatthewAndreTaylor/TinySim/tree/main/tinysim_warp/simple_quadruped) |
|:-------------------------:|:-------------------------:|
| <img width="312" alt="warp_cart_pole" src="https://github.com/user-attachments/assets/f29f3749-d836-4afa-9f27-8578aca020dc" /> | <img width="312" alt="warp_simple_quadruped" src="https://github.com/user-attachments/assets/a966e881-358e-47ee-b0e1-b67eba903987" /> |


To use the [mujoco](https://github.com/google-deepmind/mujoco) simulation environments.

```bash
pip install tinysim[mujoco]
```
| [UnitreeA1WalkEnv](https://github.com/MatthewAndreTaylor/TinySim/tree/main/tinysim_mujoco/unitree_a1) | [ManipulationEnvV0](https://github.com/MatthewAndreTaylor/TinySim/tree/main/tinysim_mujoco/manipulation) |
|:-------------------------:|:-------------------------:|
| <img width="312" alt="mujoco_sim" src="https://github.com/user-attachments/assets/1109488e-0563-4694-8926-682edd0c8278" /> | <img width="312" alt="mujoco_sim" src="https://github.com/user-attachments/assets/07b406b5-15fc-4cfd-83c4-cf6b855d773a" /> |

