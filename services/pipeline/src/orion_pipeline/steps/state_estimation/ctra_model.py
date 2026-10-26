import numpy as np
from numpy.typing import NDArray

from .phys_model_config import PhysicsModelConfig
from .state import OMEGA, PX, PY, STATE_SIZE, THETA, A, V, wrap_angle

FloatArray = NDArray[np.float64]


class CTRAModel:
    def __init__(self, config: PhysicsModelConfig) -> None:
        self.config = config

    def predict_forward(self, state: FloatArray, dt: float) -> FloatArray:
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

        # Not turning
        straight = np.abs(turn_rate) < self.config.straight_threshold

        # Straight case: d = v*t + 1/2*a*t^2
        distance = velocity * dt + 0.5 * acceleration * dt**2
        straight_x = distance * np.cos(heading)
        straight_y = distance * np.sin(heading)

        # Turning case.
        w = np.where(straight, 1.0, turn_rate)

        x_from_speed = velocity * (np.sin(new_heading) - np.sin(heading)) / w
        y_from_speed = velocity * (np.cos(heading) - np.cos(new_heading)) / w

        x_from_accel = acceleration * (
            dt * np.sin(new_heading) / w
            + (np.cos(new_heading) - np.cos(heading)) / w**2
        )
        y_from_accel = acceleration * (
            -dt * np.cos(new_heading) / w
            + (np.sin(new_heading) - np.sin(heading)) / w**2
        )

        turning_x = x_from_speed + x_from_accel
        turning_y = y_from_speed + y_from_accel

        out = state.copy()
        out[..., PX] = x + np.where(straight, straight_x, turning_x)
        out[..., PY] = y + np.where(straight, straight_y, turning_y)
        out[..., V] = velocity + acceleration * dt
        out[..., THETA] = wrap_angle(new_heading)

        return out

    def process_noise(self, dt: float) -> FloatArray:
        """Process noise Q for a step of dt seconds.

        Q adds a little extra doubt for that:

        - sigma_jerk: how much acceleration can randomly change (affects speed).
        - sigma_alpha: how much turn rate can randomly change (affects heading).

        Position (PX, PY) gets no direct noise. It becomes uncertain indirectly,
        because errors in speed and heading carry into position.

        Args:
            dt: Time step

        Returns:
            Array of shape (STATE_SIZE, STATE_SIZE).
        """
        accel_jerk = self.config.model_params.get("sigma_jerk", 1.0)
        heading_jerk = self.config.model_params.get("sigma_alpha", 0.1)

        q = np.zeros((STATE_SIZE, STATE_SIZE))
        for rate, integrated, sigma in (
            (A, V, accel_jerk),
            (OMEGA, THETA, heading_jerk),
        ):
            var = sigma**2
            q[integrated, integrated] = var * dt**3 / 3
            q[integrated, rate] = q[rate, integrated] = var * dt**2 / 2
            q[rate, rate] = var * dt

        return q
