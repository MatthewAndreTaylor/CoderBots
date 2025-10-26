"""CoderBot package exports.

This module exposes package submodules so tests and external runtimes (like
JupyterLite) can `import coderbot_package.simple_client` and `coderbot_package.lidar_module`.
"""

from . import simple_client  # noqa: F401
from . import lidar_module  # noqa: F401

__all__ = ["simple_client", "lidar_module"]
