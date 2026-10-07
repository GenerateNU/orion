"""
URTS -- Unscented Rauch-Tung-Striebel smoother.

The UKF runs forward in time, so its estimate at tick k only knows about readings up to tick k.
URTS runs backward over the finished UKF output so every tick also benefits from readings that came after it.
It never looks at sensors: everything it knows about them is already inside the UKF's xs and Ps.

All tensors should be float64 -- float32 loses too much precision in covariance math.
"""
import math

import torch

from services.ctra import ctra
from services.ukf import UKF

# Index of heading in the state vector [x, y, v, theta, omega, a] -- angles need wrapping
THETA = 3


def _wrap_angle(angle: torch.Tensor) -> torch.Tensor:
    """Wrap an angle (or tensor of angles) into [-pi, pi]."""
    return torch.remainder(angle + math.pi, 2 * math.pi) - math.pi


def _residual(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """a - b, with the heading difference wrapped so 359 deg - 1 deg comes out as -2 deg, not 358."""
    diff = a - b
    diff[..., THETA] = _wrap_angle(diff[..., THETA])
    return diff


def ukf_sigma_points(x: torch.Tensor, P: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Sigma points and weights from the UKF, so URTS spreads points exactly the way the UKF did.
    The UKF keeps these as methods on its own state, so build a throwaway UKF holding x and P to get them."""
    ukf = UKF(x, P)
    Wm, Wc = ukf.calculate_weights()
    return ukf.generate_sigma_points(), Wm, Wc


def urts_smooth(xs: torch.Tensor, Ps: torch.Tensor, dt: float, Q: torch.Tensor, fx=ctra, sigma_points=ukf_sigma_points):
    """
    Smooth a completed UKF forward pass.

    Parameters
    ----------
    xs : (N, 6) filtered states from the UKF, one per 10 ms tick
        - describes UKF's assumption of where the car is
    Ps : (N, 6, 6) filtered covariances from the UKF
        - describes how sure the UKF is about its assumption
    dt : seconds between ticks (0.01 for 100 Hz)
        - describes time between ticks
    Q : (6, 6) process noise -- must be the same Q the UKF used
        - noise factor that was also used for ukf
    fx : motion model, fx(state, dt) -> next state. Defaults to CTRA.
    sigma_points : sigma_points(x, P) -> (points, Wm, Wc). Defaults to the UKF's.
        Tests pass simpler stand-ins for both so they check URTS on its own.
        - picks 13 points 
        - Wm: how much each point coun

    Returns
    -------
    x_smooth : (N, 6) smoothed states
    P_smooth : (N, 6, 6) smoothed covariances
    """
    n_ticks, n = xs.shape
    if Ps.shape != (n_ticks, n, n):
        raise ValueError(f"Ps must have shape ({n_ticks}, {n}, {n}), got {tuple(Ps.shape)}")

    x_smooth = xs.clone()
    P_smooth = Ps.clone()

    # The last tick has no future to learn from, so it stays as the UKF left it.
    # Walk backward from the second-to-last tick to the first.
    for k in range(n_ticks - 2, -1, -1):
        # Spread sigma points around the filtered estimate at tick k
        points, Wm, Wc = sigma_points(xs[k], Ps[k])

        # Push every sigma point through the motion model to tick k+1
        predicted_points = torch.stack([fx(point, dt) for point in points])

        # What tick k expected tick k+1 to look like.
        # Heading can't be averaged directly (179 deg and -179 deg would average to 0), so average
        # each point's wrapped difference from the center point and add that back on.
        x_pred = Wm @ predicted_points
        center_theta = predicted_points[0, THETA]
        x_pred[THETA] = _wrap_angle(center_theta + Wm @ _wrap_angle(predicted_points[:, THETA] - center_theta))

        # Measures how unsure that expectation is, plus Q
        pred_diffs = _residual(predicted_points, x_pred)
        P_pred = pred_diffs.T @ torch.diag(Wc) @ pred_diffs + Q

        # How errors at tick k line up with errors at tick k+1
        point_diffs = _residual(points, xs[k])
        cross_cov = point_diffs.T @ torch.diag(Wc) @ pred_diffs

        # Smoother gain: how much tick k should listen to tick k+1 (cross_cov @ inv(P_pred))
        gain = torch.linalg.solve(P_pred, cross_cov.T).T

        # Nudge tick k by how far the smoothed k+1 landed from what tick k expected
        x_smooth[k] = xs[k] + gain @ _residual(x_smooth[k + 1], x_pred)
        x_smooth[k, THETA] = _wrap_angle(x_smooth[k, THETA])

        P_k = Ps[k] + gain @ (P_smooth[k + 1] - P_pred) @ gain.T
        P_smooth[k] = (P_k + P_k.T) / 2  # keep it exactly symmetric despite rounding

    return x_smooth, P_smooth
