import numpy as np
import pytest

from orion_pipeline.steps.state_estimation.ctra_model import CTRAModel
from orion_pipeline.steps.state_estimation.kalman_step.kalman_filter import (
    UnscentedKalmanFilter,
)
from orion_pipeline.steps.state_estimation.phys_model_config import PhysicsModelConfig
from orion_pipeline.steps.state_estimation.state import (
    OMEGA,
    PX,
    PY,
    STATE_SIZE,
    THETA,
    A,
    V,
)

DT = 0.01
GPS_STD_M = 1.5
SPEED_STD_MPS = 0.5
P0 = np.diag([GPS_STD_M**2, GPS_STD_M**2, 1.0**2, 0.3**2, 0.5**2, 2.0**2])


def gps(states):
    return states[:, [PX, PY]]


def speed(states):
    return states[:, [V]]


@pytest.fixture
def model() -> CTRAModel:
    return CTRAModel(
        PhysicsModelConfig("ctra", {"sigma_jerk": 1.0, "sigma_alpha": 0.1})
    )


def make_state(px=0.0, py=0.0, v=0.0, theta=0.0, omega=0.0, a=0.0) -> np.ndarray:
    state = np.zeros(STATE_SIZE)
    state[[PX, PY, V, THETA, OMEGA, A]] = px, py, v, theta, omega, a
    return state


def drive(model, truth, steps, seed=0, turn_at=None, turn_rate=0.0):
    """Move a true car with CTRA and run the filter on noisy GPS (10 Hz) and speed (100 Hz).

    The filter starts at the true state. Returns the true and estimated states per tick.
    """
    rng = np.random.default_rng(seed)
    truth = truth.copy()
    ukf = UnscentedKalmanFilter(model, truth.copy(), P0)

    true_states, estimates = [], []
    for k in range(steps):
        if k == turn_at:
            truth[OMEGA] = turn_rate
        truth = model.predict_forward(truth, DT)

        ukf.predict(DT)
        ukf.update(
            truth[[V]] + rng.normal(0, SPEED_STD_MPS, 1),
            speed,
            np.array([[SPEED_STD_MPS**2]]),
            gate=6.63,
        )
        if k % 10 == 0:
            ukf.update(
                truth[[PX, PY]] + rng.normal(0, GPS_STD_M, 2),
                gps,
                np.eye(2) * GPS_STD_M**2,
                gate=9.21,
            )

        true_states.append(truth.copy())
        estimates.append(ukf.x.copy())
    return np.array(true_states), np.array(estimates)


def position_errors(true_states, estimates):
    return np.hypot(*(estimates[:, [PX, PY]] - true_states[:, [PX, PY]]).T)


# Straight line


def test_straight_line(model):
    """tracks position and speed"""
    truth, est = drive(model, make_state(v=15.0, theta=0.7), steps=3000)
    second_half = slice(1500, None)

    assert np.median(position_errors(truth, est)[second_half]) < 1.0
    assert np.median(np.abs(est[second_half, V] - truth[second_half, V])) < 0.2
    assert np.median(np.abs(est[second_half, OMEGA])) < 0.05


def test_braking_in_a_straight_line(model):
    """Should show deceleration"""
    # 25 m/s braking at 3 m/s^2 for 5 s
    truth, est = drive(model, make_state(v=25.0, theta=-1.2, a=-3.0), steps=500)
    last_second = slice(400, None)

    assert np.median(position_errors(truth, est)[last_second]) < 2.0
    assert np.median(np.abs(est[last_second, V] - truth[last_second, V])) < 0.5
    assert np.median(est[last_second, A]) == pytest.approx(-3.0, abs=1.0)


# Turns


@pytest.mark.parametrize("turn_rate", [0.3, -0.3, 1.0])
def test_steady_turn(model, turn_rate):
    """Tracks position and turn rate"""
    # turn_rate 1.0 goes around ~5 times, so heading crosses +/-pi along the way
    truth, est = drive(model, make_state(v=15.0, omega=turn_rate), steps=3000)
    second_half = slice(1500, None)

    assert np.median(position_errors(truth, est)[second_half]) < 2.0
    assert np.median(est[second_half, OMEGA]) == pytest.approx(turn_rate, abs=0.05)
    assert np.all(np.abs(est[:, THETA]) <= np.pi)


def test_turn_after_driving_straight(model):
    """The filter should notice the turn and not get lost."""
    # 10 s straight, then a 0.5 rad/s turn the filter wasn't expecting
    truth, est = drive(
        model, make_state(v=15.0), steps=2000, turn_at=1000, turn_rate=0.5
    )
    errors = position_errors(truth, est)

    assert errors[1000:1300].max() < 5.0  # doesn't get lost turning in
    assert np.median(errors[1500:]) < 2.0  # settles back onto the path
    assert np.median(est[1250:1350, OMEGA]) > 0.25  # has noticed the turn by ~3 s
