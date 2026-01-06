import tkinter as tk
import threading
from abc import ABC, abstractmethod

from PIL import Image
import io


class TkBaseFrontend(ABC):

    def __init__(self):
        self._root = None
        self._canvas = None
        self._thread = None

    def render(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._window_hook, daemon=True)
        self._thread.start()

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


    def capture_canvas(self):
        """Capture the current canvas as a PIL Image."""
        if not self._canvas:
            return None
        
        ps = self._canvas.postscript(colormode='color')
        img = Image.open(io.BytesIO(ps.encode('utf-8')))
        return img
