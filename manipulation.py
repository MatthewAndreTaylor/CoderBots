from tinysim_mujoco.manipulation import ManipulationBaseEnv

env = ManipulationBaseEnv(headless=False)

for _ in range(100):
    env.step()

env.viewer.close()


# from tinysim_mujoco.unitree_a1 import UnitreeA1BaseEnv


# env = UnitreeA1BaseEnv(headless=False)

# for _ in range(1000):
#     env.render()


# env.viewer.close()
