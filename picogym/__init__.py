from abc import ABC, abstractmethod

from .spaces import Space


class SimEnvironment(ABC):

    action_space: Space

    @abstractmethod
    def step(self, *args, **kwargs):
        pass

    @abstractmethod
    def reset(self, *args, **kwargs):
        pass
