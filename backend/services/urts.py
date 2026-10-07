"""
URTS -- Unscented Rauch-Tung-Striebel smoother.

The UKF runs forward in time, so its estimate at tick k only knows about readings up to tick k.
URTS runs backward over the finished UKF output so every tick also benefits from readings that came after it.
It never looks at sensors: everything it knows about them is already inside the UKF's xs and Ps.

All tensors should be float64 -- float32 loses too much precision in covariance math.
"""
import math

import torch

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


def urts_smooth(xs: torch.Tensor, Ps: torch.Tensor, dt: float, fx, Q: torch.Tensor, sigma_points):
    """
    Smooth a completed UKF forward pass.

    Parameters
    ----------
    xs : (N, 6) filtered states from the UKF, one per 10 ms tick
    Ps : (N, 6, 6) filtered covariances from the UKF
    dt : seconds between ticks (0.01 for 100 Hz)
    fx : motion model function, fx(state, dt) -> next state  (ctra_predict)
    Q : (6, 6) process noise -- must be the same Q the UKF used
    sigma_points : function, sigma_points(x, P) -> (points, Wm, Wc), same settings as the UKF
        TODO: import this from ukf.py once it exists instead of passing it in

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
        # 1. Spread sigma points around the filtered estimate at tick k
        points, Wm, Wc = sigma_points(xs[k], Ps[k])

        # 2. Push every sigma point through the motion model to tick k+1
        predicted_points = torch.stack([fx(point, dt) for point in points])

        # 3. What tick k expected tick k+1 to look like.
        #    Heading can't be averaged directly (179 deg and -179 deg would average to 0), so average
        #    each point's wrapped difference from the center point and add that back on.
        x_pred = Wm @ predicted_points
        center_theta = predicted_points[0, THETA]
        x_pred[THETA] = _wrap_angle(center_theta + Wm @ _wrap_angle(predicted_points[:, THETA] - center_theta))

        # 4. How unsure that expectation is, plus Q for "the motion model isn't perfect"
        pred_diffs = _residual(predicted_points, x_pred)
        P_pred = pred_diffs.T @ torch.diag(Wc) @ pred_diffs + Q

        # 5. How errors at tick k line up with errors at tick k+1
        point_diffs = _residual(points, xs[k])
        cross_cov = point_diffs.T @ torch.diag(Wc) @ pred_diffs

        # 6. Smoother gain: how much tick k should listen to tick k+1 (cross_cov @ inv(P_pred))
        gain = torch.linalg.solve(P_pred, cross_cov.T).T

        # 7. Nudge tick k by how far the smoothed k+1 landed from what tick k expected
        x_smooth[k] = xs[k] + gain @ _residual(x_smooth[k + 1], x_pred)
        x_smooth[k, THETA] = _wrap_angle(x_smooth[k, THETA])

        P_k = Ps[k] + gain @ (P_smooth[k + 1] - P_pred) @ gain.T
        P_smooth[k] = (P_k + P_k.T) / 2  # keep it exactly symmetric despite rounding

    return x_smooth, P_smooth
