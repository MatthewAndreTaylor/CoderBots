import pathlib
import anywidget
import traitlets

class RobotPanel(anywidget.AnyWidget):
    _esm = pathlib.Path("client.js")

    endpoint = traitlets.Unicode("localhost:5000").tag(sync=True)
    title = traitlets.Unicode("Robot Control Panel").tag(sync=True)
    controls = traitlets.Bool(default_value=False).tag(sync=True)
