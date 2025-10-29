import json
import pathlib
import anywidget
import traitlets
import requests
from IPython.display import display


class RobotPanel(anywidget.AnyWidget):
    _esm = pathlib.Path("rest_client.js")

    endpoint = traitlets.Unicode().tag(sync=True)
    title = traitlets.Unicode("Robot Control Panel").tag(sync=True)
    controls = traitlets.Bool(default_value=False).tag(sync=True)

    result = traitlets.Dict().tag(sync=True)

    def _set_result(self, result_type, data):
        # Always create a new dict reference to trigger frontend update
        self.result = {"type": result_type, "data": data, "_sync": id(data)}

    def __init__(self, endpoint = "localhost:5000"):
        super().__init__()
        self.endpoint = endpoint
        self.reset()


    def show(self):
        display(self)

    def robot_env(self):
        """Get the current environment of the robot."""
        url = f"http://{self.endpoint}/robot_scenario_env"
        response = requests.get(url)
        return response.json()

    def step(self, num_steps):
        """Signal to step the robot."""
        url = f"http://{self.endpoint}/robot_scenario_step"
        l = len(b"data: ")
        with requests.post(url, json={"num_steps": num_steps}, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    if line.startswith(b"data: "):
                        data = line[l:]
                        json_data = json.loads(data)
                        yield json_data
                        self._set_result("step", json_data)

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