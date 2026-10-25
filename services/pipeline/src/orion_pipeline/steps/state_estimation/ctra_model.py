
import numpy as np
from numpy.typing import NDArray

from .state import A, OMEGA, PX, PY, STATE_SIZE, THETA, V, wrap_angle

FloatArray = NDArray[np.float64]

class CTRAModel:
    def __init__(self, config: any) -> None:
        self.config = config

    def predict(self, state: FloatArray, dt: float = 0.1) -> FloatArray:

        """Move the state forward by dt seconds.

        Args:
            state: Array of shape (STATE_SIZE,) or (N, STATE_SIZE).
            dt: Time step in seconds.

        Returns:
            The predicted state, same shape as the input.

        Raises:
            ValueError: If the last dimension is not STATE_SIZE.
        """

        if state.shape[-1] != STATE_SIZE:
            raise ValueError(f"State must have last dimension {STATE_SIZE}.")

        x, y = state[..., PX], state[..., PY]
        velocity, heading = state[..., V], state[..., THETA]
        turn_rate, acceleration = state[..., OMEGA], state[..., A]

        new_heading = heading + turn_rate * dt

        # Not turning (same 1e-6 check as the original).
        straight = np.abs(turn_rate) < 1e-6

        # Straight case: d = v*t + 1/2*a*t^2
        distance = velocity * dt + 0.5 * acceleration * dt**2
        straight_x = distance * np.cos(heading)
        straight_y = distance * np.sin(heading)

        # Turning case.
        w = np.where(straight, 1.0, turn_rate)

        x_from_speed = velocity * (np.sin(new_heading) - np.sin(heading)) / w
        y_from_speed = velocity * (np.cos(heading) - np.cos(new_heading)) / w

        x_from_accel = acceleration * (
            dt * np.sin(new_heading) / w + (np.cos(new_heading) - np.cos(heading)) / w**2
        )
        y_from_accel = acceleration * (
            -dt * np.cos(new_heading) / w + (np.sin(new_heading) - np.sin(heading)) / w**2
        )

        turning_x = x_from_speed + x_from_accel
        turning_y = y_from_speed + y_from_accel

        out = state.copy()
        out[..., PX] = x + np.where(straight, straight_x, turning_x)
        out[..., PY] = y + np.where(straight, straight_y, turning_y)
        out[..., V] = velocity + acceleration * dt
        out[..., THETA] = wrap_angle(new_heading)

        return out