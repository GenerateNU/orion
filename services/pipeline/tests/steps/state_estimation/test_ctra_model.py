import numpy as np
import pytest

from orion_pipeline.steps.state_estimation.ctra_model import CTRAModel
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


@pytest.fixture
def model() -> CTRAModel:
    return CTRAModel(PhysicsModelConfig("ctra", {}))


def make_state(px=0.0, py=0.0, v=0.0, theta=0.0, omega=0.0, a=0.0) -> np.ndarray:
    state = np.zeros(STATE_SIZE)
    state[[PX, PY, V, THETA, OMEGA, A]] = px, py, v, theta, omega, a
    return state


def integrate_numerically(state: np.ndarray, dt: float, n: int = 100_000) -> np.ndarray:
    """Reference position after dt, by stepping the CTRA motion in tiny pieces."""
    pos = state[[PX, PY]].copy()
    for i in range(n):
        t = (i + 0.5) * dt / n
        v = state[V] + state[A] * t
        th = state[THETA] + state[OMEGA] * t
        pos += v * np.array([np.cos(th), np.sin(th)]) * dt / n
    return pos


def test_straight_line_uses_distance_formula(model):
    heading = 0.5
    state = make_state(v=10.0, theta=heading, a=2.0)
    out = model.predict(state, dt=2.0)

    distance = 10.0 * 2.0 + 0.5 * 2.0 * 2.0**2
    assert out[PX] == pytest.approx(distance * np.cos(heading))
    assert out[PY] == pytest.approx(distance * np.sin(heading))
    assert out[V] == pytest.approx(14.0)
    assert out[THETA] == pytest.approx(heading)


def test_constant_turn_matches_numerical_integration(model):
    state = make_state(v=10.0, theta=0.3, omega=0.2, a=1.0)
    out = model.predict(state, dt=0.5)

    expected = integrate_numerically(state, dt=0.5)
    np.testing.assert_allclose(out[[PX, PY]], expected, rtol=1e-6)
    assert out[V] == pytest.approx(10.5)
    assert out[THETA] == pytest.approx(0.4)


def test_omega_and_acceleration_carry_over(model):
    state = make_state(v=5.0, omega=0.1, a=-1.0)
    out = model.predict(state, dt=0.1)

    assert out[OMEGA] == state[OMEGA]
    assert out[A] == state[A]


def test_input_state_is_not_modified(model):
    state = make_state(v=5.0, omega=0.1)
    before = state.copy()
    model.predict(state, dt=0.1)

    np.testing.assert_array_equal(state, before)


def test_batch_matches_single_states(model):
    states = np.stack(
        [
            make_state(v=10.0, theta=0.3, omega=0.2, a=1.0),
            make_state(px=3.0, py=-2.0, v=4.0, theta=-1.0, omega=0.0, a=0.5),
            make_state(v=7.0, theta=2.0, omega=-0.4, a=-1.0),
        ]
    )
    batch = model.predict(states, dt=0.3)

    assert batch.shape == states.shape
    for row, out in zip(states, batch, strict=True):
        np.testing.assert_allclose(out, model.predict(row, dt=0.3))


def test_wrong_state_size_raises(model):
    with pytest.raises(ValueError):
        model.predict(np.zeros(STATE_SIZE - 1), dt=0.1)


def test_just_above_threshold_is_close_to_straight(model):
    threshold = model.config.straight_threshold
    straight = model.predict(make_state(v=10.0, theta=0.3, a=1.0), dt=0.1)
    turning = model.predict(
        make_state(v=10.0, theta=0.3, omega=threshold * 10, a=1.0), dt=0.1
    )

    np.testing.assert_allclose(turning[[PX, PY]], straight[[PX, PY]], atol=1e-4)
