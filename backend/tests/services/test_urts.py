"""
Tests for the URTS smoother.

Uses a linear motion model instead of CTRA so the correct answer can be computed by hand (the textbook RTS smoother).
That way a failure here points at URTS itself, not at CTRA or the UKF.
"""
import pytest
import torch

from services.urts import THETA, urts_smooth

DT = 0.01
Q = torch.eye(6, dtype=torch.float64) * 0.01

# Linear motion: x moves with speed, speed changes with acceleration. Heading passes through unchanged.
F = torch.eye(6, dtype=torch.float64)
F[0, 2] = DT
F[2, 5] = DT


def linear_fx(state, dt):
    return F @ state


def sigma_points(x, P, alpha=0.5, beta=2.0, kappa=0.0):
    """Standard sigma points. TODO: replace with sigma_points from services/ukf.py once it lands."""
    n = x.shape[0]
    lam = alpha**2 * (n + kappa) - n
    L = torch.linalg.cholesky((n + lam) * P)
    points = torch.vstack([x, x + L.T, x - L.T])
    Wm = torch.full((2 * n + 1,), 1 / (2 * (n + lam)), dtype=torch.float64)
    Wc = Wm.clone()
    Wm[0] = lam / (n + lam)
    Wc[0] = lam / (n + lam) + (1 - alpha**2 + beta)
    return points, Wm, Wc


def fake_ukf_output(n_ticks=30):
    """Stand-in for the UKF's saved results: noisy states driving at ~10 m/s, and valid covariances."""
    torch.manual_seed(0)
    xs = torch.randn(n_ticks, 6, dtype=torch.float64) * 0.3
    xs[:, 2] += 10.0
    A = torch.randn(n_ticks, 6, 6, dtype=torch.float64)
    Ps = A @ A.transpose(1, 2) * 0.1 + torch.eye(6, dtype=torch.float64)
    return xs, Ps


def test_matches_textbook_rts():
    """With a linear model, URTS must give exactly the same answer as the textbook RTS smoother."""
    xs, Ps = fake_ukf_output()
    x_smooth, P_smooth = urts_smooth(xs, Ps, DT, linear_fx, Q, sigma_points)

    x_expected, P_expected = xs.clone(), Ps.clone()
    for k in range(len(xs) - 2, -1, -1):
        x_pred = F @ xs[k]
        P_pred = F @ Ps[k] @ F.T + Q
        gain = Ps[k] @ F.T @ torch.linalg.inv(P_pred)
        x_expected[k] = xs[k] + gain @ (x_expected[k + 1] - x_pred)
        P_expected[k] = Ps[k] + gain @ (P_expected[k + 1] - P_pred) @ gain.T

    torch.testing.assert_close(x_smooth, x_expected)
    torch.testing.assert_close(P_smooth, P_expected)


def test_last_tick_is_unchanged():
    """Nothing comes after the last tick, so there's nothing to smooth it with."""
    xs, Ps = fake_ukf_output()
    x_smooth, P_smooth = urts_smooth(xs, Ps, DT, linear_fx, Q, sigma_points)

    assert torch.equal(x_smooth[-1], xs[-1])
    assert torch.equal(P_smooth[-1], Ps[-1])


def wrap(angle):
    return torch.remainder(angle + torch.pi, 2 * torch.pi) - torch.pi


def test_heading_near_180_degrees_matches_heading_near_0():
    """Driving at ~180 deg should smooth exactly like driving at ~0 deg, just rotated.
    180 deg is where angles wrap (179 and -179 are only 2 deg apart), so without wrap handling
    the averages and differences come out wrong there."""
    xs, Ps = fake_ukf_output()
    Ps = Ps * 0.01
    xs[:, THETA] = torch.tensor([0.02, -0.02], dtype=torch.float64).repeat(len(xs) // 2)
    xs_flipped = xs.clone()
    xs_flipped[:, THETA] = wrap(xs[:, THETA] + torch.pi)

    def wrapping_fx(state, dt):
        """Like linear_fx, but wraps heading the way a real motion model might."""
        new = F @ state
        new[THETA] = wrap(new[THETA])
        return new

    x_smooth, _ = urts_smooth(xs, Ps, DT, wrapping_fx, Q, sigma_points)
    x_smooth_flipped, _ = urts_smooth(xs_flipped, Ps, DT, wrapping_fx, Q, sigma_points)

    x_smooth_flipped[:, THETA] = wrap(x_smooth_flipped[:, THETA] - torch.pi)
    torch.testing.assert_close(x_smooth_flipped, x_smooth)


def test_rejects_mismatched_covariances():
    xs, Ps = fake_ukf_output()

    with pytest.raises(ValueError):
        urts_smooth(xs, Ps[:-1], DT, linear_fx, Q, sigma_points)
