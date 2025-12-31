import argparse
import warp as wp
import numpy as np
from tinysim_warp.simple_quadruped import SimpleRobotDogExample

import torch
import torch.nn as nn
import torch.distributions as D
import torch.optim as optim


class PPOPolicy(nn.Module):
    def __init__(self, obs_dim, act_dim):
        super().__init__()

        self.shared = nn.Sequential(
            nn.Linear(obs_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
        )

        self.mu = nn.Linear(64, act_dim)
        self.value = nn.Linear(64, 1)
        self.log_std = nn.Parameter(torch.zeros(act_dim))

    def forward(self, obs):
        x = self.shared(obs)
        return self.mu(x), self.value(x)

    def get_action(self, obs):
        mu, value = self(obs)
        std = torch.exp(self.log_std)
        dist = D.Normal(mu, std)

        action = dist.sample()
        log_prob = dist.log_prob(action).sum(-1)

        return action, log_prob, value.squeeze(-1)

    def evaluate(self, obs, action):
        mu, value = self(obs)
        std = torch.exp(self.log_std)
        dist = D.Normal(mu, std)

        log_prob = dist.log_prob(action).sum(-1)
        entropy = dist.entropy().sum(-1)

        return log_prob, entropy, value.squeeze(-1)


def ppo_loss(
    policy,
    obs,
    actions,
    old_log_probs,
    returns,
    advantages,
    clip_eps=0.2,
    value_coef=0.5,
    entropy_coef=0.02,
):
    log_probs, entropy, values = policy.evaluate(obs, actions)

    ratios = torch.exp(log_probs - old_log_probs)
    clipped = torch.clamp(ratios, 1 - clip_eps, 1 + clip_eps)

    policy_loss = -torch.mean(torch.min(ratios * advantages, clipped * advantages))

    value_loss = torch.mean((returns - values) ** 2)
    entropy_loss = -torch.mean(entropy)

    return policy_loss + value_coef * value_loss + entropy_coef * entropy_loss


# ---------------- CONFIG ---------------- #

parser = argparse.ArgumentParser()
parser.add_argument("--device", type=str, default=None)
args = parser.parse_known_args()[0]

OBS_DIM = 7
ACT_DIM = 8
GAMMA = 0.99
LR = 3e-4
ROLLOUT = 400
NUM_EPOCHS = 50
ACTION_SCALE = 0.4

policy = PPOPolicy(OBS_DIM, ACT_DIM)
optimizer = optim.Adam(policy.parameters(), lr=LR)


def yaw_from_quat(q):
    x, y, z, w = q
    return np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def get_obs(example, phase):
    root = example.state_0.body_q.numpy()[0]
    rootd = example.state_0.body_qd.numpy()[0]

    lin_vel = rootd[0:2]
    yaw_rate = rootd[5]
    yaw = yaw_from_quat(root[3:7])

    obs = np.concatenate(
        [
            lin_vel,
            [yaw_rate],
            [np.sin(yaw), np.cos(yaw)],
            [np.sin(phase), np.cos(phase)],
        ]
    )

    return torch.tensor(obs, dtype=torch.float32)


def compute_reward(example):
    rootd = example.state_0.body_qd.numpy()[0]
    forward_vel = rootd[0]

    return forward_vel


with wp.ScopedDevice(args.device):

    for epoch in range(NUM_EPOCHS):
        example = SimpleRobotDogExample(num_envs=1)

        obs_buf, act_buf, logp_buf, rew_buf, val_buf = [], [], [], [], []
        phase = 0.0

        for _ in range(ROLLOUT):
            obs = get_obs(example, phase)

            action, logp, value = policy.get_action(obs)

            action_np = torch.tanh(action).detach().numpy() * ACTION_SCALE
            example.step(action_np)
            example.render()

            reward = compute_reward(example)

            obs_buf.append(obs)
            act_buf.append(action)
            logp_buf.append(logp)
            rew_buf.append(reward)
            val_buf.append(value)

            phase += example.frame_dt * 2.0

        returns = []
        advs = []
        G = 0.0

        for r, v in zip(reversed(rew_buf), reversed(val_buf)):
            G = r + GAMMA * G
            returns.insert(0, G)
            advs.insert(0, G - v.item())

        adv_t = torch.tensor(advs, dtype=torch.float32)
        adv_t = (adv_t - adv_t.mean()) / (adv_t.std() + 1e-8)

        obs_t = torch.stack(obs_buf)
        act_t = torch.stack(act_buf)
        logp_t = torch.stack(logp_buf)
        ret_t = torch.tensor(returns, dtype=torch.float32)

        loss = ppo_loss(policy, obs_t, act_t, logp_t, ret_t, adv_t)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        print(f"Epoch {epoch+1}/{NUM_EPOCHS} | Loss: {loss.item():.4f}")

        example.renderer.close()
