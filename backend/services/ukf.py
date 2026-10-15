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
        self.alpha = 1.0
        self.beta = 2.0
        self.kappa = 0.0

    def generate_sigma_points(self) -> torch.Tensor:
        """
        Generate sigma points around the current state.

        For a 6-variable state, the UKF generates 13 sigma points.
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

        # Add positive/negative variations
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
        Calculate the weights used for the sigma points. (how much significance each has)

        Returns:
            Mean weights and covariance weights.
        """

        n = self.state_dimension

        lambda_ = (
            self.alpha**2 * (n + self.kappa) - n
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
        The UKF estimates six physical variables.
        Timestamp is added only when calling CTRA.
        """
        # Generate 13 sigma points, each containing 6 state variables
        sigma_points = self.generate_sigma_points()

        mean_weights, covariance_weights = self.calculate_weights()

        # Temporary timestamp for the CTRA input.
        # CTRA calculates its own dt from the timestamps, so we
        # provide a start time and an end time separated by dt.
        start_time = torch.tensor(0.0, dtype=torch.float64)
        end_time = torch.tensor(dt, dtype=torch.float64)

        predicted_sigma_points_list = []

        # Predict every sigma point separately
        for sigma_point in sigma_points:
            # Add timestamp to make a 7-value row:
            # [time, x, y, velocity, heading, turn_rate, acceleration]
            state_with_time = torch.cat(
                (start_time.unsqueeze(0), sigma_point)
            )

            # CTRA expects two rows to calculate dt from their timestamps.
            next_state_with_time = torch.cat(
                (end_time.unsqueeze(0), sigma_point)
            )

            ctra_input = torch.stack(
                [state_with_time, next_state_with_time]
            )

            # CTRA predicts from the first row over the time interval.
            predicted_state_with_time = ctra(ctra_input)

            # Remove timestamp; the UKF tracks only the 6 physical variables.
            predicted_sigma_points_list.append(
                predicted_state_with_time[1:]
            )

        predicted_sigma_points = torch.stack(
            predicted_sigma_points_list
        )

        # Calculate the weighted average of the predicted sigma points
        predicted_state = torch.sum(
            predicted_sigma_points * mean_weights.unsqueeze(1),
            dim=0,
        )

        self.state = predicted_state

        # Calculate the predicted covariance
        predicted_covariance = torch.zeros_like(self.covariance)

        for i in range(predicted_sigma_points.shape[0]):
            difference = predicted_sigma_points[i] - predicted_state

            predicted_covariance += (
                covariance_weights[i]
                * torch.outer(difference, difference)
            )

        # Add process noise
        self.covariance = predicted_covariance + self.process_noise

        return self.state
    
    def update(self, measurement: torch.Tensor) -> torch.Tensor:
        """
        Correct the predicted state using the next input row.

        Currently, all six state variables are treated as directly observed.

        TODO: Replace this temporary state-based update with a sensor-based
        measurement model once the sensor inputs and data format are finalized. Currently 
        has updates based on x,y data that is given not anything else. 
        """
        measurement = measurement.to(torch.float64)

        # Difference between the supplied state and our prediction
        innovation = measurement - self.state

        # TODO: Replace this placeholder with measurement noise (R) based on
        # the actual sensors and their expected measurement uncertainty.
        measurement_noise = torch.eye(
            self.state_dimension,
            dtype=torch.float64,
        )

        # Calculate the uncertainty in the difference between prediction and observation
        innovation_covariance = (
            self.covariance + measurement_noise
        )

        # Calculate the Kalman gain without explicitly inverting a matrix
        kalman_gain = torch.linalg.solve(
            innovation_covariance,
            self.covariance.T,
        ).T

        # Correct the predicted state toward the supplied observation
        self.state = self.state + kalman_gain @ innovation

        # Reduce uncertainty after using the observation
        identity = torch.eye(
            self.state_dimension,
            dtype=torch.float64,
        )

        self.covariance = (
            identity - kalman_gain
        ) @ self.covariance

        # Keep the covariance symmetric against small numerical errors
        self.covariance = (
            self.covariance + self.covariance.T
        ) / 2

        return self.state
