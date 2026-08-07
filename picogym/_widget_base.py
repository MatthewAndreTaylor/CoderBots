import anywidget
import traitlets
from IPython.display import display
from jupyter_ui_poll import ui_events

from . import SimEnvironment


class BaseWidget(anywidget.AnyWidget):

    sim_env: SimEnvironment
    _view_ready = traitlets.Bool(default_value=False).tag(sync=True)

    def __init__(self, sim_env: SimEnvironment):
        super().__init__()
        self.sim_env = sim_env
        self.sim_state = self.sim_env.reset()
        self._update_props(self.sim_state)

    def render(self):
        display(self)

        try:
            with ui_events() as ui_poll:
                while not self._view_ready:
                    ui_poll(100)
        except Exception:
            pass

    def _update_props(self, sim_state):
        self.sim_state = sim_state

    def step(self, *args, **kwargs):
        sim_state = self.sim_env.step(*args, **kwargs)
        self._update_props(sim_state)
        return sim_state

    def reset(self, *args, **kwargs):
        sim_state = self.sim_env.reset(*args, **kwargs)
        self._update_props(sim_state)
        return sim_state
