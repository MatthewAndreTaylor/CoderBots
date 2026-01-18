import threading
import tkinter as tk
from abc import ABC, abstractmethod

from . import SimEnvironment


class TkBaseFrontend(ABC):

    def __init__(self, sim_env: SimEnvironment):
        self.sim_env = sim_env
        self._root = None
        self._canvas = None
        self._thread = None

    def render(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._window_hook, daemon=True)
        self._thread.start()

    def step(self, *args, **kwargs):
        state = self.sim_env.step(*args, **kwargs)
        if self._root:
            self._root.after(0, lambda: self._draw_state(state))
        return state

    def reset(self, *args, **kwargs):
        state = self.sim_env.reset()
        if self._canvas:
            self._draw_state(state)
        return state

    def _draw_state(self, state):
        raise NotImplementedError

    def _window_hook(self):
        root = tk.Tk()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._create_window(root)

    @abstractmethod
    def _create_window(self, root):
        pass

    def bring_to_front(self, root):
        root.lift()
        root.attributes("-topmost", True)
        root.after_idle(root.attributes, "-topmost", False)
        root.focus_force()

    def _on_close(self):
        if self._root:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
        self._root = None
        self._canvas = None

    def _pump(self):
        if not self._root:
            return

        try:
            self._root.update_idletasks()
            self._root.update()
        except tk.TclError:
            return

        if self._root:
            self._root.after(20, self._pump)
