import numpy as np

from gymnasium import Env, spaces
from sb3_contrib import TQC

import torch as th
import torch.nn as nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.torch_layers import NatureCNN

from picogym_mujoco.manipulation.push_env_cam import ManipulationEnvV1


class CustomCombinedExtractor(BaseFeaturesExtractor):
    def __init__(self, observation_space: spaces.Dict):
        super().__init__(observation_space, features_dim=1)

        extractors = {}
        total_size = 0

        # CNN for image
        obs_cap_space = observation_space.spaces["observation_cap"]
        extractors["observation_cap"] = NatureCNN(obs_cap_space, features_dim=16)
        total_size += 16

        # MLP for low-dim observations
        for key in ["observation", "achieved_goal", "desired_goal"]:
            space = observation_space.spaces[key]
            extractors[key] = nn.Flatten()
            total_size += int(np.prod(space.shape))

        self.extractors = nn.ModuleDict(extractors)
        self._features_dim = total_size

    def forward(self, observations):
        encoded = []

        for key, extractor in self.extractors.items():
            encoded.append(extractor(observations[key]))

        return th.cat(encoded, dim=1)


# stable-baselines3 requires wrapping environemnts with gym.Env for training
class ManipulationGymWrapper(ManipulationEnvV1, Env):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        obs = self._get_obs()
        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype="float32")
        self.observation_space = spaces.Dict(
            dict(
                observation_cap=spaces.Box(
                    0, 255, shape=obs["observation_cap"].shape, dtype="uint8"
                ),
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


env = ManipulationGymWrapper(headless=False, show_cam_renders=False)

model = TQC(
    # Not sure if can be done with CNNPolicy (obs of joints seems very important)
    policy="MultiInputPolicy",
    env=env,
    learning_rate=0.001,
    buffer_size=100000,
    batch_size=64,
    learning_starts=512,
    policy_kwargs=dict(
        features_extractor_class=CustomCombinedExtractor,
        net_arch=dict(
            pi=[128, 128],
            qf=[128, 128],
        ),
    ),
    tau=0.05,
    gamma=0.95,
    device="cuda",
)


model.learn(total_timesteps=50000, progress_bar=True)
model.save("tqc_manipulation_cam")

model = TQC.load("tqc_manipulation_cam", env=env)

obs, info = env.reset()

while True:
    action, _states = model.predict(obs, deterministic=True)
    obs, rewards, terminated, truncated, info = env.step(action)

    if terminated or truncated:
        break
