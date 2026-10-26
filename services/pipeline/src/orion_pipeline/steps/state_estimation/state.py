"""Layout of the car's state vector, shared by the physics model, the filter and the step.

A state is a float64 array of shape (STATE_SIZE,), or (N, STATE_SIZE) for a batch
such as sigma points. Index it with x[..., IDX] so code works for both shapes.

    PX     m     east of the run's origin (first GPS fix)
    PY     m     north of the run's origin
    V      m/s   forward speed
    THETA  rad   heading, wrapped to [-pi, pi]
    OMEGA  rad/s turn rate
    A      m/s^2 forward acceleration
"""

import numpy as np

PX, PY, V, THETA, OMEGA, A = range(6)
STATE_SIZE = 6

def wrap_angle(theta: np.ndarray) -> np.ndarray:
    """Wrap angles to [-pi, pi]."""
    return (theta + np.pi) % (2 * np.pi) - np.pi
