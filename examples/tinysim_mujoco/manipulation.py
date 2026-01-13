from tinysim_mujoco.manipulation import ManipulationBaseEnv

env = ManipulationBaseEnv(headless=False)

for _ in range(100):
    env.step()

env.viewer.close()
