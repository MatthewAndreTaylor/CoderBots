import numpy as np

class SimpleWalkGait:
    def __init__(self, num_envs, freq=1.2):
        self.num_envs = num_envs
        self.freq = freq
        self.phase = 0.0

        # amplitudes (SAFE)
        self.hip_amp   = 0.15
        self.thigh_amp = 0.35
        self.calf_amp  = 0.6

        # startup
        self.startup_time = 0.5
        self.elapsed = 0.0

        # stable standing pose
        self.stand_pose = np.array([
            0.0, 0.4, -0.7,
            0.0, 0.4, -0.7,
            0.0, 0.4, -0.7,
            0.0, 0.4, -0.7,
        ])

    def step(self, dt):
        self.elapsed += dt
        blend = np.clip(self.elapsed / self.startup_time, 0.0, 1.0)

        self.phase += 2 * np.pi * self.freq * dt
        actions = np.zeros((self.num_envs, 12))

        for env in range(self.num_envs):
            a = self.phase
            b = self.phase + np.pi

            # FRONT RIGHT
            actions[env, 0] =  self.hip_amp   * np.sin(a)
            actions[env, 1] =  self.thigh_amp * np.sin(a)
            actions[env, 2] = -self.calf_amp  * np.sin(a)

            # FRONT LEFT
            actions[env, 3] = -self.hip_amp   * np.sin(b)
            actions[env, 4] =  self.thigh_amp * np.sin(b)
            actions[env, 5] = -self.calf_amp  * np.sin(b)

            # BACK RIGHT
            actions[env, 6] =  self.hip_amp   * np.sin(b)
            actions[env, 7] =  self.thigh_amp * np.sin(b)
            actions[env, 8] = -self.calf_amp  * np.sin(b)

            # BACK LEFT
            actions[env, 9]  = -self.hip_amp   * np.sin(a)
            actions[env, 10] =  self.thigh_amp * np.sin(a)
            actions[env, 11] = -self.calf_amp  * np.sin(a)

        # --- STARTUP BLEND ---
        actions = (1.0 - blend) * self.stand_pose + blend * actions

        # lock hips until feet are planted
        if blend < 1.0:
            actions[:, [0, 3, 6, 9]] = 0.0

        return actions
