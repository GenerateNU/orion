import torch

from services.ukf import UKF


def test_ukf_generates_13_sigma_points():
    state = torch.tensor([
        0.0, 0.0, 10.0, 0.0, 0.0, 0.0
    ])

    covariance = torch.eye(6)

    ukf = UKF(state, covariance)

    sigma_points = ukf.generate_sigma_points()

    print("Sigma points:")
    print(sigma_points)

    print("Shape:")
    print(sigma_points.shape)

    assert sigma_points.shape == (13, 6)


def test_ukf_predicts_without_sensors():
    state = torch.tensor([
        0.0, 0.0, 10.0, 0.0, 0.0, 0.0
    ])

    covariance = torch.eye(6)

    ukf = UKF(state, covariance)

    result = ukf.predict(0.1)

    print("Predicted state:")
    print(result)

    print("Predicted covariance:")
    print(ukf.covariance)

    assert result.shape == (6,)
    assert torch.isfinite(result).all()
    assert torch.isfinite(ukf.covariance).all()

def make_ukf() -> UKF:
    initial_state = torch.tensor(
        [0, 0, 2, 0.3, 0.1, 0.5],
        dtype=torch.float64,
    )
    initial_covariance = torch.eye(6, dtype=torch.float64)

    return UKF(initial_state, initial_covariance)


def test_update_corrects_state_and_reduces_uncertainty():
    ukf = make_ukf()

    # Simulate a prediction first
    ukf.predict(0.1)

    predicted_state = ukf.state.clone()
    predicted_covariance = ukf.covariance.clone()

    # Simulate a measurement that differs from the prediction
    measurement = predicted_state + torch.tensor(
        [1, 1, 1, 0.1, 0.1, 0.1],
        dtype=torch.float64,
    )

    # Run the update
    updated_state = ukf.update(measurement)

    # Check that the update returns a six-variable state
    assert updated_state.shape == (6,)

    # Check that the updated state contains valid numbers
    assert torch.isfinite(updated_state).all()

    # Check that the state moved toward the measurement
    assert torch.linalg.norm(
        measurement - updated_state
    ) < torch.linalg.norm(
        measurement - predicted_state
    )

    # Check that uncertainty did not increase
    assert torch.allclose(
        ukf.covariance,
        ukf.covariance.T,
        atol=1e-10,
    )

    assert torch.trace(ukf.covariance) < torch.trace(
        predicted_covariance
    )
