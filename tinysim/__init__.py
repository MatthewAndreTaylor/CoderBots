from abc import ABC, abstractmethod


class SimEnvironment(ABC):
    @abstractmethod
    def step(self, action) -> dict:
        pass

    @abstractmethod
    def reset(self) -> dict:
        pass
