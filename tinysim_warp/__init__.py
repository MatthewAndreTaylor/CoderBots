from abc import ABC, abstractmethod

import numpy as np

try:
    import warp as wp
    import warp.sim.render
except ImportError:
    raise ImportError(
        "Warp is not installed. Install using `pip install tinysim[warp]`"
    )


class WarpBaseEnv(ABC):
    def __init__(self, use_cuda_graph=False, headless=False, num_envs=1, fps=60):
        self.try_use_cuda_graph = use_cuda_graph
        self.headless = headless
        self.num_envs = num_envs

        self.fps = fps
        self.sim_time = 0.0
        self.frame_dt = 1.0 / fps
        self.sim_substeps = 10  # todo: make configurable
        self.sim_dt = self.frame_dt / self.sim_substeps
        self.num_envs = num_envs
        self.env_offsets = self.comp_env_offsets()
        self.model = self.build_model()
        self.integrator = self.solver()

        self.renderer = wp.sim.render.SimRendererOpenGL(
            self.model, "viewer", headless=headless
        )
        self.state_0 = self.model.state()
        self.state_1 = self.model.state()
        wp.sim.eval_fk(
            self.model, self.state_0.joint_q, self.state_0.joint_qd, None, self.state_0
        )
        self.capture_graph()

    @abstractmethod
    def build_model(self):
        raise NotImplementedError("build_model() must be implemented in subclass.")

    @abstractmethod
    def solver(self):
        raise NotImplementedError("solver() must be implemented in subclass.")

    @abstractmethod
    def apply_actions(self, actions):
        raise NotImplementedError("apply_actions() must be implemented in subclass.")

    @abstractmethod
    def get_obs(self):
        raise NotImplementedError("get_obs() must be implemented in subclass.")

    def comp_env_offsets(self, offset=(5.0, 0.0, 0.0)):
        offset = np.array(offset, dtype=float)
        axis = np.nonzero(offset)[0]
        axis = axis[0] if len(axis) else 0
        t = np.arange(self.num_envs) * offset[axis]
        offsets = np.zeros((self.num_envs, 3))
        offsets[:, axis] = t - t.mean()
        return offsets

    def capture_graph(self):
        # CUDA graph
        self.use_cuda_graph = (
            self.try_use_cuda_graph
            and wp.get_device().is_cuda
            and wp.is_mempool_enabled(wp.get_device())
        )
        if self.try_use_cuda_graph and not self.use_cuda_graph:
            raise Warning(
                """Unable to enable CUDA graph capture.
                Please verify that Warp is using CUDA and that the memory pool is enabled.
                """
            )

        if self.use_cuda_graph:
            with wp.ScopedCapture() as capture:
                self.simulate()
            self.graph = capture.graph

    def simulate(self):
        for _ in range(self.sim_substeps):
            self.state_0.clear_forces()
            wp.sim.collide(self.model, self.state_0)
            self.integrator.simulate(
                self.model, self.state_0, self.state_1, self.sim_dt
            )
            self.state_0, self.state_1 = self.state_1, self.state_0

    def step(self, actions):
        self.apply_actions(actions)

        if self.use_cuda_graph:
            wp.capture_launch(self.graph)
        else:
            self.simulate()

        self.sim_time += self.frame_dt
        return self.get_obs()

    def render(self):
        self.renderer.begin_frame(self.sim_time)
        self.renderer.render(self.state_0)
        self.renderer.end_frame()

    def reset(self, **kwargs):
        raise NotImplementedError("reset() must be implemented in subclass.")
