import numpy as np

from gymnasium import Env, spaces
from sb3_contrib import TQC

# from stable_baselines3 import SAC
from stable_baselines3.her import HerReplayBuffer

from tinysim_mujoco.manipulation.push_env import ManipulationEnvV0


# stable-baselines3 requires wrapping environemnts with gym.Env for training
class ManipulationGymWrapper(ManipulationEnvV0, Env):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        obs = self._get_obs()
        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype="float32")
        self.observation_space = spaces.Dict(
            dict(
                desired_goal=spaces.Box(
                    -np.inf, np.inf, shape=obs["achieved_goal"].shape, dtype="float64"
                ),
                achieved_goal=spaces.Box(
                    -np.inf, np.inf, shape=obs["achieved_goal"].shape, dtype="float64"
                ),
                observation=spaces.Box(
                    -np.inf, np.inf, shape=obs["observation"].shape, dtype="float64"
                ),
            )
        )


env = ManipulationGymWrapper(headless=False, use_d405_camera=False)

model = TQC(
    policy="MultiInputPolicy",
    env=env,
    learning_rate=0.001,
    buffer_size=100000,
    batch_size=512,
    learning_starts=1024,
    policy_kwargs=dict(net_arch=[256, 256, 256]),
    replay_buffer_class=HerReplayBuffer,
    replay_buffer_kwargs=dict(n_sampled_goal=4, goal_selection_strategy="future"),
    tau=0.05,
    gamma=0.95,
)


model.learn(total_timesteps=50000, progress_bar=True)
model.save("tqc_manipulation")

model = TQC.load("tqc_manipulation", env=env)

obs, info = env.reset()

while True:
    action, _states = model.predict(obs, deterministic=True)
    obs, rewards, terminated, truncated, info = env.step(action)

    if terminated or truncated:
        break
