import pytest
import torch

from services.urts import urts_smooth


def straight_line(state, dt):
    # Simple stand-in for CTRA: x moves forward by speed * dt, nothing else changes
    new_state = state.clone()
    new_state[0] = state[0] + state[2] * dt
    return new_state


def test_urts_output_shape():
    states = torch.tensor([
        [0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        [0.1, 0.0, 10.0, 0.0, 0.0, 0.0],
        [0.2, 0.0, 10.0, 0.0, 0.0, 0.0],
    ], dtype=torch.float64)

    covariances = torch.eye(6, dtype=torch.float64).repeat(3, 1, 1)

    Q = torch.eye(6, dtype=torch.float64) * 0.01

    smoothed_states, smoothed_covariances = urts_smooth(states, covariances, 0.01, Q, fx=straight_line)

    print("Smoothed states:")
    print(smoothed_states)

    assert smoothed_states.shape == (3, 6)
    assert smoothed_covariances.shape == (3, 6, 6)


def test_urts_keeps_last_tick_the_same():
    states = torch.tensor([
        [0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        [0.5, 0.0, 10.0, 0.0, 0.0, 0.0],
    ], dtype=torch.float64)

    covariances = torch.eye(6, dtype=torch.float64).repeat(2, 1, 1)

    Q = torch.eye(6, dtype=torch.float64) * 0.01

    smoothed_states, _ = urts_smooth(states, covariances, 0.01, Q, fx=straight_line)

    print("Last tick before:", states[-1])
    print("Last tick after:", smoothed_states[-1])

    assert torch.equal(smoothed_states[-1], states[-1])


def test_urts_pulls_earlier_tick_toward_later_tick():
    # At 10 m/s the car should move 0.1 m per tick, but the next tick says it moved 1.0 m.
    # Smoothing should pull the first tick forward to agree with what happened next.
    states = torch.tensor([
        [0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        [1.0, 0.0, 10.0, 0.0, 0.0, 0.0],
    ], dtype=torch.float64)

    covariances = torch.eye(6, dtype=torch.float64).repeat(2, 1, 1)

    Q = torch.eye(6, dtype=torch.float64) * 0.01

    smoothed_states, _ = urts_smooth(states, covariances, 0.01, Q, fx=straight_line)

    print("First tick x before:", states[0, 0].item())
    print("First tick x after:", smoothed_states[0, 0].item())

    assert smoothed_states[0, 0] > states[0, 0]


def test_urts_makes_filter_more_confident():
    states = torch.tensor([
        [0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        [0.1, 0.0, 10.0, 0.0, 0.0, 0.0],
    ], dtype=torch.float64)

    # The second tick already had a sensor correction, so it's more certain than the first
    covariances = torch.stack([
        torch.eye(6, dtype=torch.float64),
        torch.eye(6, dtype=torch.float64) * 0.5,
    ])

    Q = torch.eye(6, dtype=torch.float64) * 0.01

    _, smoothed_covariances = urts_smooth(states, covariances, 0.01, Q, fx=straight_line)

    print("First tick uncertainty before:", torch.diagonal(covariances[0]))
    print("First tick uncertainty after:", torch.diagonal(smoothed_covariances[0]))

    assert (torch.diagonal(smoothed_covariances[0]) < torch.diagonal(covariances[0])).all()


def test_urts_heading_near_180_degrees_does_not_flip():
    # 3.13 and -3.13 radians are both almost 180 degrees -- only ~1 degree apart
    states = torch.tensor([
        [0.0, 0.0, 10.0, 3.13, 0.0, 0.0],
        [0.1, 0.0, 10.0, -3.13, 0.0, 0.0],
        [0.2, 0.0, 10.0, 3.13, 0.0, 0.0],
    ], dtype=torch.float64)

    covariances = torch.eye(6, dtype=torch.float64).repeat(3, 1, 1) * 0.01

    Q = torch.eye(6, dtype=torch.float64) * 0.01

    smoothed_states, _ = urts_smooth(states, covariances, 0.01, Q, fx=straight_line)

    print("Headings before:", states[:, 3])
    print("Headings after:", smoothed_states[:, 3])

    # Every heading should still be near +/-180 degrees, not swung around toward 0
    assert (smoothed_states[:, 3].abs() > 3.0).all()


def test_urts_rejects_mismatched_shapes():
    states = torch.zeros(3, 6, dtype=torch.float64)

    covariances = torch.eye(6, dtype=torch.float64).repeat(2, 1, 1)

    Q = torch.eye(6, dtype=torch.float64) * 0.01

    with pytest.raises(ValueError):
        urts_smooth(states, covariances, 0.01, Q, fx=straight_line)


def test_urts_matches_textbook_smoother():
    # With the straight-line model, URTS should give exactly the same numbers as the
    # textbook RTS smoother, which can be written out by hand with plain matrices
    dt = 0.01

    states = torch.tensor([
        [0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        [0.3, 0.1, 10.2, 0.1, 0.0, 0.1],
        [0.2, -0.1, 9.9, 0.0, 0.1, 0.0],
        [0.5, 0.0, 10.1, -0.1, 0.0, 0.2],
    ], dtype=torch.float64)

    covariances = torch.stack([
        torch.eye(6, dtype=torch.float64) * 1.0,
        torch.eye(6, dtype=torch.float64) * 0.8,
        torch.eye(6, dtype=torch.float64) * 0.6,
        torch.eye(6, dtype=torch.float64) * 0.4,
    ])

    Q = torch.eye(6, dtype=torch.float64) * 0.01

    smoothed_states, smoothed_covariances = urts_smooth(states, covariances, dt, Q, fx=straight_line)

    # Textbook RTS smoother. F is straight_line written as a matrix: x = x + v * dt
    F = torch.eye(6, dtype=torch.float64)
    F[0, 2] = dt

    expected_states = states.clone()
    expected_covariances = covariances.clone()

    for k in range(len(states) - 2, -1, -1):
        predicted_state = F @ states[k]
        predicted_covariance = F @ covariances[k] @ F.T + Q
        gain = covariances[k] @ F.T @ torch.linalg.inv(predicted_covariance)

        expected_states[k] = states[k] + gain @ (expected_states[k + 1] - predicted_state)
        expected_covariances[k] = covariances[k] + gain @ (expected_covariances[k + 1] - predicted_covariance) @ gain.T

    print("URTS smoothed states:")
    print(smoothed_states)

    print("Textbook smoothed states:")
    print(expected_states)

    torch.testing.assert_close(smoothed_states, expected_states)
    torch.testing.assert_close(smoothed_covariances, expected_covariances)
