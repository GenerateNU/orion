from collections.abc import Callable

import numpy as np

from orion_pipeline.steps.state_estimation.ctra_model import CTRAModel
from orion_pipeline.steps.state_estimation.state import THETA, wrap_angle


class UnscentedKalmanFilter:
    """Unscented Kalman filter over the car's state (layout in state.py).

    Pushes 2n + 1 sigma points through the physics model instead of
    linearizing it. Each sensor is applied as its own update.

    Args:
        model: The physics model
        x0: starting state
        P0: Starting uncertainty
        alpha: spread around current state
        beta: shape of error based on prior distribution
        kappa: spread
    """

    def __init__(
        self,
        model: CTRAModel,
        x0: np.ndarray,
        P0: np.ndarray,
        alpha: float = 0.5,
        beta: float = 2.0,
        kappa: float = 0.0,
    ) -> None:
        self.model = model
        self.x = np.array(x0, dtype=np.float64)
        self.P = np.array(P0, dtype=np.float64)

        n = len(self.x)
        lam = alpha**2 * (n + kappa) - n
        self.c = n + lam

        self.Wm = np.full(2 * n + 1, 1 / (2 * self.c))
        self.Wc = np.full(2 * n + 1, 1 / (2 * self.c))
        self.Wm[0] = lam / self.c
        self.Wc[0] = lam / self.c + (1 - alpha**2 + beta)

    def predict(self, dt: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Move the state forward dt seconds.

        Returns copies of (x_pred, P_pred, C) for the smoother, where C is the
        cross covariance between the old and the moved sigma points.
        """
        sigmas = self._sigma_points()
        # TODO: control_input in ctra is not used - remove?
        moved = self.model.predict_forward(sigmas, dt)

        x_pred = self._state_mean(moved)
        d_sigmas = self._state_residuals(sigmas, self.x)
        d_moved = self._state_residuals(moved, x_pred)

        # TODO: currently no process noise function
        P_pred = self._weighted_cov(d_moved, d_moved)  # + self.model.process_noise(dt)
        C = self._weighted_cov(d_sigmas, d_moved)

        self.x, self.P = x_pred, P_pred
        return x_pred.copy(), P_pred.copy(), C

    def update(
        self,
        z: np.ndarray,
        h: Callable[[np.ndarray], np.ndarray],
        R: np.ndarray,
        gate: float | None = None,
    ) -> bool:
        """Correct the state with one sensor's measurement.

        z (m,) is the reading, h maps states (N, n) -> (N, m), R (m, m) is the
        sensor noise. If gate is set, readings with NIS above it are skipped.
        Returns whether the reading was applied.
        """
        sigmas = self._sigma_points()
        Z = h(sigmas)

        z_hat = self.Wm @ Z
        dZ = Z - z_hat
        dX = self._state_residuals(sigmas, self.x)

        S = self._weighted_cov(dZ, dZ) + R
        Pxz = self._weighted_cov(dX, dZ)

        y = z - z_hat
        if gate is not None and y @ np.linalg.solve(S, y) > gate:
            return False

        K = np.linalg.solve(S, Pxz.T).T

        self.x = self.x + K @ y
        self.x[THETA] = wrap_angle(self.x[THETA])

        self.P = self.P - K @ S @ K.T
        self.P = (self.P + self.P.T) / 2
        return True

    def _sigma_points(self) -> np.ndarray:
        """2n + 1 points around x: x, then x +/- each column of chol(c P)."""
        L = np.linalg.cholesky(self.c * self.P)
        sigmas = np.vstack([self.x, self.x + L.T, self.x - L.T])
        sigmas[:, THETA] = wrap_angle(sigmas[:, THETA])
        return sigmas

    def _state_mean(self, sigmas: np.ndarray) -> np.ndarray:
        """Weighted mean of states, averaging heading as offsets from the center point."""
        mean = self.Wm @ sigmas
        offsets = wrap_angle(sigmas[:, THETA] - sigmas[0, THETA])
        mean[THETA] = wrap_angle(sigmas[0, THETA] + self.Wm @ offsets)
        return mean

    def _state_residuals(self, sigmas: np.ndarray, mean: np.ndarray) -> np.ndarray:
        """sigmas - mean, with heading wrapped."""
        d = sigmas - mean
        d[:, THETA] = wrap_angle(d[:, THETA])
        return d

    def _weighted_cov(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Sum of Wc_i * a_i b_i^T."""
        return (self.Wc[:, None] * a).T @ b
