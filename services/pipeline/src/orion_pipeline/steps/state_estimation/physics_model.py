from abc import ABC, abstractmethod

import numpy as np

from .phys_model_config import PhysicsModelConfig


class PhysicsModel(ABC):
    """How the car moves between ticks. The filter only talks to a model through
    this interface, so models can be swapped without touching the filter.

    States follow the layout in state.py: shape (STATE_SIZE,) or (N, STATE_SIZE).
    """

    def __init__(self, config: PhysicsModelConfig) -> None:
        self.config = config

    @abstractmethod
    def predict_forward(self, state: np.ndarray, dt: float) -> np.ndarray:
        """Given the current car's physical state and the time step, predict the next state of the car using the physics model.
        Returns the same shape as `state`, so a batch of sigma points moves in one call."""

    @abstractmethod
    def process_noise(self, dt: float) -> np.ndarray:
        """Process noise Q for a step of dt seconds, shape (STATE_SIZE, STATE_SIZE).
        Covers what the model leaves out, e.g. changes in acceleration and turn rate within the step."""
