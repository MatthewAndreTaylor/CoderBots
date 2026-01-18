from typing import Any

import numpy as np

# It is encouraged to implement your own Space classes or use existing ones from external libraries.


class Space:
    """A minimal implementation of the Space class for TinySim."""

    def sample(self) -> Any:
        """Randomly sample an element from this space."""
        raise NotImplementedError

    def contains(self, x: Any) -> bool:
        """Return boolean specifying if x is a valid member of this space."""
        raise NotImplementedError

    def __contains__(self, x: Any) -> bool:
        return self.contains(x)


class Discrete(Space):
    """A discrete space in TinySim."""

    def __init__(self, n: int):
        assert n >= 0, "n (number of elements) must be non-negative"
        self.n = n

    def sample(self) -> int:
        return np.random.randint(0, self.n)

    def contains(self, x: Any) -> bool:
        return isinstance(x, int) and 0 <= x < self.n


class Box(Space):
    """A box space in TinySim."""

    def __init__(self, low: float, high: float, shape: tuple, dtype=np.float32):
        self.low = np.full(shape, low, dtype=dtype)
        self.high = np.full(shape, high, dtype=dtype)
        self.shape = shape
        self.dtype = dtype

    def sample(self) -> Any:
        return np.random.uniform(self.low, self.high, self.shape)

    def contains(self, x: Any) -> bool:
        x = np.array(x)
        return (
            x.shape == self.shape and np.all(x >= self.low) and np.all(x <= self.high)
        )


class Dict(Space):
    """A dictionary space in TinySim."""

    def __init__(self, spaces: dict):
        self.spaces = spaces

    def sample(self) -> dict:
        return {key: space.sample() for key, space in self.spaces.items()}

    def contains(self, x: Any) -> bool:
        if isinstance(x, dict) and x.keys() == self.spaces.keys():
            return all(x[key] in self.spaces[key] for key in self.spaces.keys())
        return False
