import math
from typing import ClassVar

import pandas as pd
import torch
from pandas import Timestamp

from models.vehicle import StateEstimate
from orion.repository import DataPointRepository
from services.ukf import UKF
from services.urts import urts_smooth


class StateEstimationService:
    """
    Scaffold for estimating vehicle position from cleaned sensor data.
    """

    # Inputs based on cleaned data in Penelope
    REQUIRED_COLUMNS: ClassVar[list[str]] = ["timestamp", "name", "value"]

    # Bare minimum output (need to go back and add more)
    OUTPUT_COLUMNS: ClassVar[list[str]] = [
        "timestamp",
        "latitude",
        "longitude",
    ]

    # TODO: build from first readings once cleaned data format is settled
    PLACEHOLDER_INITIAL_STATE: ClassVar[torch.Tensor] = torch.zeros(6, dtype=torch.float64)  # [x, y, v, theta, omega, a]
    PLACEHOLDER_INITIAL_COVARIANCE: ClassVar[torch.Tensor] = torch.eye(6, dtype=torch.float64)  # 6x6 identity matrix
    PLACEHOLDER_ORIGIN: ClassVar[tuple[float, float]] = (0.0, 0.0)
    METERS_PER_DEGREE_LAT: ClassVar[float] = 111_320.0

    # Tick length
    tick: ClassVar[str] = "10ms"
    dt_seconds: ClassVar[float] = 0.01

    def __init__(self, orion_db_client: DataPointRepository):
        self.orion_db_client = orion_db_client

    def estimate_state(self, start_time: Timestamp, end_time: Timestamp) -> pd.DataFrame:
        """ use private method helper functions"""
        
        
    def _estimate_position(self, cleaned_df: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate vehicle position from cleaned sensor data.

        Parameters
        ----------
        cleaned_df : pd.DataFrame
            Cleaned, wide-format sensor data from the clean service.

        Returns
        -------
        pd.DataFrame
            Estimated vehicle positions with timestamp, latitude,
            and longitude.
        """

        # Validatation so nothing breaks because of bad data
        self._validate_input(cleaned_df)

        # Implement the state estimation pipeline.
        # 1. Run the UKF forward pass
        forward_estimate = self._predict_forward(cleaned_df)

        # 2. Run the URTS backward pass
        smoothed_estimate = self._smooth(forward_estimate)

        # 3. Return the smoothed estimate as a DataFrame
        return smoothed_estimate.states[self.OUTPUT_COLUMNS]

    def _predict_forward(self, cleaned_readings: pd.DataFrame) -> StateEstimate:
        """Run the UKF forward, one tick at a time (past-and-current-only).
        Takes CLEANED_READING_SCHEMA rows; noise for R and Q comes from models/noise.py.
        Output has is_smoothed=False."""
        ukf = UKF(self.PLACEHOLDER_INITIAL_STATE.clone(), self.PLACEHOLDER_INITIAL_COVARIANCE.clone())

        # get tick times
        tick_times, states, covariances = [], [], []
        previous_tick_time = None
        
        ticks = cleaned_readings.groupby(cleaned_readings["timestamp"].dt.floor(self.tick))

        for tick_time, tick_readings in ticks:
            if previous_tick_time is not None:
                dt = (tick_time - previous_tick_time).total_seconds()
                ukf.predict(dt)

            # update the UKF with the readings for this tick
            # TODO: implement UKF update
            # ukf.update(tick_readings)

            tick_times.append(tick_time)
            states.append(ukf.state.clone())
            covariances.append(ukf.covariance.clone())
            previous_tick_time = tick_time

        xs = torch.stack(states)
        Px = torch.stack(covariances)
        return self._to_state_estimate(tick_times, xs, Px, is_smoothed=False)
        

    def _smooth(self, forward: StateEstimate) -> StateEstimate:
        """Run the URTS backward pass over a completed forward run.
        Output has is_smoothed=True."""
        states = forward.states

        x, y = self._lat_lon_to_meters(
            torch.tensor(states["latitude"].to_numpy(), dtype=torch.float64),
            torch.tensor(states["longitude"].to_numpy(), dtype=torch.float64),
        )
        xs = torch.stack([
            x,
            y,
            torch.tensor(states["speed_mps"].to_numpy(), dtype=torch.float64),
            torch.deg2rad(torch.tensor(states["heading_deg"].to_numpy(), dtype=torch.float64)),
            torch.deg2rad(torch.tensor(states["yaw_rate_dps"].to_numpy(), dtype=torch.float64)),
            torch.tensor(states["accel_mps2"].to_numpy(), dtype=torch.float64),
        ], dim=1)
        Ps = torch.tensor(forward.covariance, dtype=torch.float64)

        x_smooth, P_smooth = urts_smooth(xs, Ps, self.dt_seconds)

        return self._to_state_estimate(list(states["timestamp"]), x_smooth, P_smooth, is_smoothed=True)
        
    def _to_state_estimate(self, tick_times, xs: torch.Tensor, Ps: torch.Tensor, is_smoothed: bool) -> StateEstimate:
        """Convert filter tensors ([x, y, v, theta, omega, a] in meters/radians) into a StateEstimate."""
        latitude, longitude = self._meters_to_lat_lon(xs[:, 0], xs[:, 1])
        states = pd.DataFrame({
            "timestamp": tick_times,
            "speed_mps": xs[:, 2].numpy(),
            "heading_deg": torch.rad2deg(xs[:, 3]).numpy(),
            "yaw_rate_dps": torch.rad2deg(xs[:, 4]).numpy(),
            "accel_mps2": xs[:, 5].numpy(),                
            "latitude": latitude.numpy(),
            "longitude": longitude.numpy(),
        })
        return StateEstimate(states=states, covariance=Ps.numpy(), is_smoothed=is_smoothed)

    def _meters_to_lat_lon(self, x: torch.Tensor, y: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Local x (east) / y (north) meters from the origin -> latitude / longitude. Fine at track scale."""
        origin_lat, origin_lon = self.PLACEHOLDER_ORIGIN
        latitude = origin_lat + y / self.METERS_PER_DEGREE_LAT
        longitude = origin_lon + x / (self.METERS_PER_DEGREE_LAT * math.cos(math.radians(origin_lat)))
        return latitude, longitude

    def _lat_lon_to_meters(self, latitude: torch.Tensor, longitude: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Inverse of _meters_to_lat_lon."""
        origin_lat, origin_lon = self.PLACEHOLDER_ORIGIN
        y = (latitude - origin_lat) * self.METERS_PER_DEGREE_LAT
        x = (longitude - origin_lon) * self.METERS_PER_DEGREE_LAT * math.cos(math.radians(origin_lat))
        return x, y

    def _validate_input(self, cleaned_df: pd.DataFrame) -> None:
        """
        Validate the input DataFrame from the clean service.
            
        """
            
        # Make sure the clean service actually provided a DataFrame.
        if not isinstance(cleaned_df, pd.DataFrame):
            raise TypeError("cleaned_df must be a pandas DataFrame")
            
        # The estimation model cannot produce a position from no data.
        if cleaned_df.empty:
            raise ValueError("cleaned_df cannot be empty")
            
        # Check that every signal required by the state estimation model is there 
        missing_columns = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in cleaned_df.columns
        ]
 
        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )
        
        # Cleaned so that the data must be in chronological order.
        if not cleaned_df["timestamp"].is_monotonic_increasing:
            raise ValueError(
                "cleaned_df must be sorted by timestamp"
            )