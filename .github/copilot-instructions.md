# TinySim AI Coding Agent Instructions

## Project Overview
TinySim is a lightweight simulation framework for robotics and ML, designed as a minimal alternative to ROS 2 and Gymnasium. The project provides:
- **tinysim**: Python-only simulation environments with browser-based visualization (anywidget/JavaScript)
- **tinysim_warp**: GPU-accelerated physics simulations using NVIDIA Warp for robotics

## Architecture

### Two-Track Design Pattern
All environments follow a dual implementation strategy:

1. **Core Environment** (`tinysim/<env>/__init__.py`): Pure Python physics/logic inheriting from `SimEnvironment` abstract base class
   - Implements `step(action) -> dict` and `reset() -> dict`
   - Vectorized numpy operations for multi-environment support
   - No rendering dependencies

2. **Frontend Implementations**:
   - **widget.py**: Jupyter integration via `anywidget.AnyWidget` with JavaScript rendering (`sim.js`)
   - **tk.py**: Tkinter-based desktop frontend using `TkBaseFrontend` with threading

Example from [tinysim/flappy/__init__.py](tinysim/flappy/__init__.py):
```python
class FlappyEnv(SimEnvironment):
    def __init__(self, num_envs: int = 1): ...
    def reset(self) -> dict: ...
    def step(self, action, dt) -> dict: ...
```

### Anywidget Integration Pattern
JavaScript frontends use anywidget for Jupyter:
- `_esm = pathlib.Path(__file__).parent / "sim.js"` loads ES module
- `traitlets.Dict(...).tag(sync=True)` syncs state between Python and JavaScript
- `jupyter_ui_poll` enables async/await in notebook cells

See [tinysim/flappy/widget.py](tinysim/flappy/widget.py) for reference implementation.

### Warp Physics (tinysim_warp)
High-performance simulations using NVIDIA Warp:
- URDF parsing for articulated robots (e.g., [simple_quadruped.urdf](tinysim_warp/simple_quadruped/simple_quadruped.urdf))
- CUDA graph optimization via `use_cuda_graph=True` (check `wp.get_device().is_cuda` and `wp.is_mempool_enabled()`)
- supports changing the pyhsics integrator [`FeatherstoneIntegrator`, `XPBDIntegrator`, ...]  for efficient multi-environment physics
- Direct action space mapping to `model.joint_act` (see [example_simple_quadruped.py](example_simple_quadruped.py))

## Development Workflows

### Adding a New Environment
1. Create `tinysim/<env>/__init__.py` with `SimEnvironment` subclass
2. Implement vectorized physics with numpy
3. Add `widget.py` with `anywidget.AnyWidget` + `sim.js` for visualization
4. Optional: Add `tk.py` for desktop frontend
5. Create `<env>_example.ipynb` demonstrating usage

### Package Structure
- Declared in [pyproject.toml](pyproject.toml): `packages = ["tinysim", "tinysim_warp"]`
- Package data includes all files: `tinysim = ["**/*"]` (critical for .js, .urdf, .json assets)
- Install with `pip install -e .` for development
- Optional dependencies: `pip install tinysim[warp]` for GPU features

### Build & Deployment
- Build distribution: `python -m build` (creates wheels in dist/)
- JupyterLite deployment via GitHub Actions (see [.github/workflows/deploy.yml](.github/workflows/deploy.yml))
- Builds to `site_dist/jupyterlite` with `jupyter lite build --contents example.ipynb`

### Example Notebooks Pattern
All Jupyter examples follow this structure:
1. Import widget/environment
2. Instantiate and render: `env = FlappySim(); env.render()`
3. Async step loop: `await env.step(action)`
4. Demonstrates both hardcoded and RL solutions

## Key Conventions

### State Dictionary Format
All `step()` and `reset()` methods return consistent dict structure:
```python
{
    "observation": np.array(...),  # Agent observations
    "reward": float or np.array,   # Scalar or vectorized rewards
    "done": bool or np.array,      # Episode termination flags
    # Environment-specific additional keys
}
```

### Vectorized Environments
Multi-environment support pattern (see [tinysim/flappy/__init__.py](tinysim/flappy/__init__.py)):
- `num_envs` parameter in `__init__`
- Per-environment state arrays: `self.bird_y = np.full(num_envs, ...)`
- Shared global state: `self.pipes_x` (single array for all envs)
- Boolean masking for done states: `flap_mask = (action == 1) & (~self.done)`

### Warp Integration Details
When working with `tinysim_warp`:
- Always wrap in `with wp.ScopedDevice(args.device):` for device management
- Action space size = joints × num_envs (e.g., 8 joints × 3 envs = 24 actions)
- Copy actions to device: `wp.copy(model.joint_act, wp.array(actions, dtype=wp.float32))`
- Simulation loop in `simulate()` method: collide → integrate → swap states

### Tkinter Threading Pattern
Desktop frontends use daemon threads ([_tk_base.py](tinysim/_tk_base.py)):
- `render()` spawns `threading.Thread(target=self._window_hook, daemon=True)`
- `_pump()` method for `update_idletasks()` / `update()` in async loops
- `bring_to_front()` for window focus management

## Dependencies & Compatibility
- **Core**: numpy, anywidget, jupyter-ui-poll
- **Optional**: warp-lang==1.8.1 (GPU simulations)
- **Python**: >=3.9 (specified in pyproject.toml)
- No ROS, Gymnasium, or heavy framework dependencies by design

## File Naming Conventions
- Environment examples: `<env>_example.ipynb` or `example_<task>.py`


## Common Pitfalls
- Warp CUDA graphs require mempool enabled and CUDA device check
- Tkinter must run in separate thread to avoid blocking notebook execution
