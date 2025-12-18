import numpy as np

class SimpleWalkGait:
    def __init__(self, num_envs, freq=1.5, amp=0.4):
        self.num_envs = num_envs
        self.freq = freq
        self.amp = amp
        self.phase = 0.0

    def step(self, dt):
        self.phase += 2 * np.pi * self.freq * dt

        # 12 joints per dog
        actions = np.zeros((self.num_envs, 12))

        # joint indices:
        # [FR, FL, BR, BL] legs × [hip, thigh, calf]
        # Using Matt's joint ordering

        for env in range(self.num_envs):
            # diagonal trot
            phase_a = self.phase
            phase_b = self.phase + np.pi

            # front-right & back-left
            actions[env, 1] = self.amp * np.sin(phase_a)
            actions[env, 7] = self.amp * np.sin(phase_a)

            # front-left & back-right
            actions[env, 4] = self.amp * np.sin(phase_b)
            actions[env, 10] = self.amp * np.sin(phase_b)

        return actions
