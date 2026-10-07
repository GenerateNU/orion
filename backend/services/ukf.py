import torch

from models.noise import PROCESS_NOISE_STDDEV
from services.ctra import ctra

# Process noise matrix Q, built once from models/noise.py. Shared with URTS so both use identical values.
PROCESS_NOISE = torch.diag(torch.tensor(
    [stddev**2 for stddev in PROCESS_NOISE_STDDEV.values()], dtype=torch.float64
))


class UKF:
    """
    UKF for vehicle state estimation.

    State:
        [x, y, velocity, heading, turn_rate, acceleration]
    """
 
    def __init__(
        self,
        initial_state: torch.Tensor,
        initial_covariance: torch.Tensor,
        process_noise: torch.Tensor = PROCESS_NOISE,
    ):
        self.state = initial_state.to(torch.float64)
        self.covariance = initial_covariance.to(torch.float64)
        self.process_noise = process_noise.to(torch.float64)

        # Number of variables in our state
        self.state_dimension = 6

        # UKF tuning parameters (hard coded but will have todo to calculate these)
        self.alpha = 0.001
        self.beta = 2.0
        self.kappa = 0.0

    def generate_sigma_points(self) -> torch.Tensor:
        """
        Generate sigma points around the current state.

        For a 6-variable state, the UKF generates
        2 * 6 + 1 = 13 sigma points.
        """

        n = self.state_dimension

        # Calculate UKF scaling parameter
        lambda_ = (
            self.alpha**2 * (n + self.kappa) - n
        )

        # Calculate square root of covariance matrix
        covariance_sqrt = torch.linalg.cholesky(
            (n + lambda_) * self.covariance
        )

        # First sigma point is the current state
        sigma_points = [self.state]

        # Add positive and negative variations
        for i in range(n):
            sigma_points.append(
                self.state + covariance_sqrt[:, i]
            )

            sigma_points.append(
                self.state - covariance_sqrt[:, i]
            )

        return torch.stack(sigma_points)

    def calculate_weights(self) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Calculate the weights used for the sigma points.

        Returns:
            Mean weights and covariance weights.
        """

        n = self.state_dimension

        lambda_ = (
            self.alpha**2 * (n + self.kappa)
            - n
        )

        mean_weights = torch.full(
            (2 * n + 1,),
            1 / (2 * (n + lambda_)),
            dtype=self.state.dtype,
        )

        covariance_weights = mean_weights.clone()

        mean_weights[0] = lambda_ / (n + lambda_)

        covariance_weights[0] = (
            mean_weights[0]
            + (1 - self.alpha**2 + self.beta)
        )

        return mean_weights, covariance_weights

    def predict(self, dt: float) -> torch.Tensor:
        """
        Predict the next vehicle state using CTRA.
        """

        sigma_points = self.generate_sigma_points()

        # Run every sigma point through CTRA
        predicted_sigma_points = torch.stack(
            [
                ctra(sigma_point, dt)
                for sigma_point in sigma_points
            ]
        )

        mean_weights, covariance_weights = (
            self.calculate_weights()
        )

        # Calculate predicted state
        predicted_state = torch.sum(
            predicted_sigma_points
            * mean_weights.unsqueeze(1),
            dim=0,
        )

        self.state = predicted_state

        # Calculate predicted covariance
        predicted_covariance = torch.zeros_like(
            self.covariance
        )

        for i in range(predicted_sigma_points.shape[0]):
            difference = (
                predicted_sigma_points[i]
                - predicted_state
            )

            predicted_covariance += (
                covariance_weights[i]
                * torch.outer(difference, difference)
            )

        # Add process noise: the real car drifts from CTRA's physics a little every tick
        self.covariance = predicted_covariance + self.process_noise

        return self.state

    def update(self, measurement: torch.Tensor) -> torch.Tensor:
        """
        Update the predicted state using sensor measurements.

        The measurement format will be added once the
        sensor inputs are finalized.
        """

        # TODO: Define measurement model
        # TODO: Predict what the sensors should measure
        # TODO: Calculate measurement covariance -- build R for this sensor from SENSOR_STDDEV in models/noise.py
        # TODO: Calculate Kalman gain
        # TODO: Update state and covariance

        raise NotImplementedError