import math
from typing import ClassVar

import pandas as pd
import torch
from pandas import Timestamp
from sqlalchemy import select

from models.vehicle import StateEstimate
from orion.repository import DataPointRepository
from orion.schema import cleaned_data_table
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

    # estimate_state output, matching the estimated_car_state table (lapId is assigned later)
    STATE_TABLE_COLUMNS: ClassVar[list[str]] = ["runId", "time", "latitude", "longitude"]

    # TODO: build from first readings once cleaned data format is settled
    PLACEHOLDER_INITIAL_STATE: ClassVar[torch.Tensor] = torch.zeros(6, dtype=torch.float64)  # [x, y, v, theta, omega, a]
    PLACEHOLDER_INITIAL_COVARIANCE: ClassVar[torch.Tensor] = torch.eye(6, dtype=torch.float64)  # 6x6 identity matrix
    PLACEHOLDER_ORIGIN: ClassVar[tuple[float, float]] = (0.0, 0.0)
    METERS_PER_DEGREE_LAT: ClassVar[float] = 111_320.0
    MPS_PER_MPH: ClassVar[float] = 0.44704  # vcu_speed is in mph; the filter uses m/s

    # Tick length
    tick: ClassVar[str] = "10ms"
    dt_seconds: ClassVar[float] = 0.01

    def __init__(self, orion_db_client: DataPointRepository):
        self.orion_db_client = orion_db_client

    def estimate_state(
        self, start_time: Timestamp, end_time: Timestamp, previous_points: dict[str, dict] | None = None
    ) -> tuple[pd.DataFrame, dict[str, dict]]:
        """
        Estimate positions for every run in [start_time, end_time) and save them to estimated_car_state.

        For paginating: previous_points is the last_points returned by the previous page, keyed by run ID.
        Runs found there continue from where they left off; new runs start fresh.
        Returns (estimated rows, last_points) -- pass last_points into the next page.
        """
        # End is exclusive so back-to-back pages never read (and write) the same reading twice
        last_points = dict(previous_points or {})
        query = (
            select(cleaned_data_table)
            .where(cleaned_data_table.c.time >= start_time, cleaned_data_table.c.time < end_time)
            .order_by(cleaned_data_table.c.time)
        )
        readings = pd.read_sql(query, self.orion_db_client.engine)
        if readings.empty:
            return pd.DataFrame(columns=self.STATE_TABLE_COLUMNS), last_points

        # One value per row: a GPS row with values [lat, lon] becomes two rows
        readings = readings.rename(
            columns={"time": "timestamp", "sensor": "name", "values": "value"}
        ).explode("value")
        readings["timestamp"] = pd.to_datetime(readings["timestamp"], utc=True)
        readings["value"] = readings["value"].astype("float64")
        
        # Each run is estimated on its own -- two sessions aren't one continuous drive
        results = []
        for run_id, run_readings in readings.groupby("runId"):
            positions, last_point = self._estimate_position(run_readings, last_points.get(run_id))
            results.append(positions.assign(runId=run_id))
            last_points[run_id] = {"run_id": run_id, **last_point}

        estimated = pd.concat(results, ignore_index=True).rename(columns={"timestamp": "time"})
        estimated = estimated[self.STATE_TABLE_COLUMNS]

        estimated.to_sql("estimated_car_state", self.orion_db_client.engine, if_exists="append", index=False)
        return estimated, last_points

    def _estimate_position(
        self, cleaned_df: pd.DataFrame, previous_point: dict | None = None
    ) -> tuple[pd.DataFrame, dict]:
        """
        Estimate vehicle position from cleaned sensor data.

        Parameters
        ----------
        cleaned_df : pd.DataFrame
            Cleaned, long-format sensor data (CLEANED_READING_SCHEMA) for one run.
        previous_point : dict, optional
            This run's last point from the previous page; None starts fresh.

        Returns
        -------
        (pd.DataFrame, dict)
            Estimated positions (timestamp, latitude, longitude), and this page's last point.
        """

        # Validatation so nothing breaks because of bad data
        self._validate_input(cleaned_df)

        # 1. Run the UKF forward pass
        forward_estimate, last_point = self._predict_forward(cleaned_df, previous_point)

        # 2. Run the URTS backward pass (it never changes the last tick, so last_point holds for both)
        smoothed_estimate = self._smooth(forward_estimate)

        # 3. Return the smoothed estimate as a DataFrame
        return smoothed_estimate.states[self.OUTPUT_COLUMNS], last_point

    # forward acceleration
    def _calculate_forward_acceleration(self, ax, az):
        return -(0.510 * ax + 0.860 * az) / 1000
    
    def _predict_forward(
        self, cleaned_readings: pd.DataFrame, previous_point: dict | None = None
    ) -> tuple[StateEstimate, dict]:
        """Run the UKF forward, one tick at a time (past-and-current-only).
        Takes CLEANED_READING_SCHEMA rows; noise for R and Q comes from models/noise.py.
        Starts from previous_point if given (continuing the previous page), otherwise from the placeholders.
        Returns the forward StateEstimate (is_smoothed=False) and the last point, for the next page."""
        
        
        if previous_point is None:
            ukf = UKF(self.PLACEHOLDER_INITIAL_STATE.clone(), self.PLACEHOLDER_INITIAL_COVARIANCE.clone())
            previous_tick_time = None
        else:
            # Setting previous_tick_time makes the first tick predict forward from where the last page ended
            ukf = UKF(previous_point["state"].clone(), previous_point["covariance"].clone())
            previous_tick_time = previous_point["time"]

        tick_times, states, covariances = [], [], []

        ticks = cleaned_readings.groupby(cleaned_readings["timestamp"].dt.floor(self.tick))
        for tick_time, tick_readings in ticks:
            acceleration_readings = tick_readings.loc[
                tick_readings["name"] == "vcu_eth_a_accel",
                "value",
            ]

            a_forward = None

            if len(acceleration_readings) >= 3:
                ax, _, az = acceleration_readings.iloc[-3:].tolist()   # latest [x, y, z]; y isn't used
                a_forward = self._calculate_forward_acceleration(ax, az)

            if previous_tick_time is not None:
                dt = (tick_time - previous_tick_time).total_seconds()
                ukf.predict(dt)

            # The temporary UKF.update() takes a full 6-value state as its measurement, so start from
            # the prediction and overwrite the parts this tick's sensors measured.
            # TODO: replace with a sensor-based measurement (z, H, R) once UKF.update() supports it;
            # gyro is skipped until we know which axis is yaw.
            measurement = ukf.state.clone()
            speed = tick_readings.loc[tick_readings["name"] == "vcu_speed", "value"]
            gps = tick_readings.loc[tick_readings["name"] == "gps_location", "value"]

            if not speed.empty:
                measurement[2] = speed.iloc[-1] * self.MPS_PER_MPH
            if len(gps) >= 2:
                # assumes values are [lat, lon]; take the latest fix in this tick
                x, y = self._lat_lon_to_meters(
                    torch.tensor(gps.iloc[-2], dtype=torch.float64),
                    torch.tensor(gps.iloc[-1], dtype=torch.float64),
                )
                measurement[0], measurement[1] = x, y
            if a_forward is not None:
                measurement[5] = a_forward

            # Skip ticks with nothing measured, so the filter doesn't grow falsely confident
            if not speed.empty or len(gps) >= 2 or a_forward is not None:
                ukf.update(measurement)

            tick_times.append(tick_time)
            states.append(ukf.state.clone())
            covariances.append(ukf.covariance.clone())
            previous_tick_time = tick_time

        xs = torch.stack(states)
        Px = torch.stack(covariances)
        forward = self._to_state_estimate(tick_times, xs, Px, is_smoothed=False)

        # Filter needs time/state/covariance/origin to continue; the rest is readable copies for logging/debugging
        last_row = forward.states.iloc[-1]
        last_point = {
            "time": tick_times[-1],
            "state": xs[-1],
            "covariance": Px[-1],
            "origin": self.PLACEHOLDER_ORIGIN,
            "latitude": float(last_row["latitude"]),
            "longitude": float(last_row["longitude"]),
            "speed_mps": float(last_row["speed_mps"]),
            "heading_deg": float(last_row["heading_deg"]),
        }
        return forward, last_point

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