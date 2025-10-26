import pathlib
import anywidget
import traitlets
import requests
from IPython.display import display


class RobotPanel(anywidget.AnyWidget):
    _esm = pathlib.Path("client.js")

    endpoint = traitlets.Unicode("localhost:5000").tag(sync=True)
    title = traitlets.Unicode("Robot Control Panel").tag(sync=True)
    controls = traitlets.Bool(default_value=False).tag(sync=True)

    result = traitlets.Dict().tag(sync=True)

    def __init__(self):
        super().__init__()
        self.reset()
        display(self)

    def _set_result(self, result_type, data):
        # Always create a new dict reference to trigger frontend update
        self.result = {"type": result_type, "data": data, "_sync": id(data)}

    def step(self, time):
        """Signal to step the robot."""
        url = f"http://{self.endpoint}/robot_scenario_step"
        response = requests.post(url, json={"t": time})
        data = response.json()
        self._set_result("step", data)
        return response.json()

    def sensor(self, num_beams=60, max_range=1000.0, noise_std=0, fov=6.28):
        """Signal to get sensor data."""
        url = f"http://{self.endpoint}/robot_scenario_sensor"
        data = {
            "num_beams": num_beams,
            "max_range": max_range,
            "noise_std": noise_std,
            "fov": fov,
        }
        response = requests.post(url, json=data)
        self._set_result("sensor", response.json())

        return response.json()

    def move(self, x, y, rotation):
        """Signal to move the robot."""
        url = f"http://{self.endpoint}/robot_scenario_move"
        data = {"x": x, "y": y, "rotation": rotation}
        requests.post(url, json=data)


    def reset(self):
        """Signal to reset the robot."""
        url = f"http://{self.endpoint}/robot_scenario_reset"
        requests.post(url)