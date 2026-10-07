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