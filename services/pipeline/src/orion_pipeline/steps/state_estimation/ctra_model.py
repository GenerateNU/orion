import numpy as np

from .physics_model import PhysicsModel
from .state import OMEGA, PX, PY, STATE_SIZE, THETA, A, V, wrap_angle


class CTRAModel(PhysicsModel):
    """Constant turn rate and acceleration: the car drives an arc whose speed
    changes at a steady rate."""

    def predict_forward(self, state: np.ndarray, dt: float) -> np.ndarray:
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

    def process_noise(self, dt: float) -> np.ndarray:
        """Process noise Q for a step of dt seconds, shape (STATE_SIZE, STATE_SIZE).

        The model assumes acceleration and turn rate stay constant, but really
        they drift. Two model_params set how fast:

        - sigma_jerk (m/s^3, default 15.0): acceleration drift, adding doubt to speed.
        - sigma_alpha (rad/s^2, default 0.5): turn rate drift, adding doubt to heading.

        Defaults were picked by sweeping both over recorded runs; alpha >= 2
        made the covariance lose positive definiteness.

        Position (PX, PY) gets no direct noise. It becomes uncertain indirectly,
        because errors in speed and heading carry into position.
        """
        params = self.config.model_params
        q = np.zeros((STATE_SIZE, STATE_SIZE))
        for rate, integrated, sigma in (
            (A, V, params.get("sigma_jerk", 15.0)),
            (OMEGA, THETA, params.get("sigma_alpha", 0.5)),
        ):
            var = sigma**2
            q[integrated, integrated] = var * dt**3 / 3
            q[integrated, rate] = q[rate, integrated] = var * dt**2 / 2
            q[rate, rate] = var * dt

        return q
