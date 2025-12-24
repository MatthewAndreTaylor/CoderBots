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

        # Learnable log-std (global, stable)
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
    entropy_coef=0.01,
):
    log_probs, entropy, values = policy.evaluate(obs, actions)

    ratios = torch.exp(log_probs - old_log_probs)

    clipped = torch.clamp(ratios, 1 - clip_eps, 1 + clip_eps)
    policy_loss = -torch.mean(torch.min(ratios * advantages, clipped * advantages))

    value_loss = 0.5 * torch.mean((returns - values) ** 2)

    entropy_loss = -torch.mean(entropy)

    total_loss = (
        policy_loss
        + value_coef * value_loss
        + entropy_coef * entropy_loss
    )

    return total_loss


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

OBS_DIM = 14
ACT_DIM = 8
ROLLOUT = 256
GAMMA = 0.99
LR = 3e-4

policy = PPOPolicy(OBS_DIM, ACT_DIM)
optimizer = optim.Adam(policy.parameters(), lr=LR)


def yaw_from_quat(q):
    x, y, z, w = q
    return np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))

def get_obs(example, phase):
    root = example.state_0.body_q.numpy()
    rootd = example.state_0.body_qd.numpy()
    
    root = root[0]
    rootd = rootd[0]

    lin_vel = rootd[0:2]
    yaw_rate = rootd[5]
    yaw = yaw_from_quat(root[3:7])

    obs = np.concatenate([
        lin_vel,
        [yaw_rate],
        [np.sin(yaw), np.cos(yaw)],
        [np.sin(phase), np.cos(phase)],
        np.zeros(7),  # padding for simplicity
    ])

    return torch.tensor(obs, dtype=torch.float32)

def compute_reward(example):
    rootd = example.state_0.body_qd.numpy()
    rootd = rootd[0]
    
    forward = rootd[0]
    lateral = abs(rootd[1])
    yaw_rate = abs(rootd[5])
    return forward - 0.5 * lateral - 0.8 * yaw_rate


HIP_AMP = 0.3
THIGH_AMP = 0.5
freq = 5.0
phase = 0.0

LEGS = [(0,1),(2,3),(4,5),(6,7)]

def scripted_action(dt, phase):
    phase += 2*np.pi*freq*dt
    phase %= 2*np.pi

    actions = np.zeros(8)
    leg_idx = int((phase / (2*np.pi)) * 4)
    hip_i, thigh_i = LEGS[leg_idx]
    local = (phase % (2*np.pi/4)) * 4

    actions[hip_i] = HIP_AMP*np.sin(local)
    actions[thigh_i] = THIGH_AMP*np.sin(local)

    directions = np.array([1,1,-1,-1,-1,-1,1,1])
    return actions * directions, phase




with wp.ScopedDevice(args.device):
    example = SimpleRobotDogExample(num_envs=1)

    obs_buf, act_buf, logp_buf, rew_buf, val_buf = [], [], [], [], []

    for frame in range(args.num_frames):

        obs = get_obs(example, phase)
        action_res, logp, value = policy.get_action(obs)

        base_action, phase = scripted_action(example.frame_dt, phase)
        final_action = base_action + 0.1 * action_res.detach().numpy()

        example.step(final_action)
        example.render()

        reward = compute_reward(example)

        obs_buf.append(obs)
        act_buf.append(action_res)
        logp_buf.append(logp)
        rew_buf.append(reward)
        val_buf.append(value)

        if len(obs_buf) >= ROLLOUT:
            returns, advs = [], []
            G = 0
            for r, v in zip(reversed(rew_buf), reversed(val_buf)):
                G = r + GAMMA * G
                returns.insert(0, G)
                advs.insert(0, G - v.item())

            obs_t = torch.stack(obs_buf)
            act_t = torch.stack(act_buf)
            logp_t = torch.stack(logp_buf)
            ret_t = torch.tensor(returns)
            adv_t = torch.tensor(advs)

            loss = ppo_loss(policy, obs_t, act_t, logp_t, ret_t, adv_t)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            obs_buf.clear()
            act_buf.clear()
            logp_buf.clear()
            rew_buf.clear()
            val_buf.clear()

example.renderer.save()