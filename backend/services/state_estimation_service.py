import pandas as pd


class StateEstimationService:
    """
    Scaffold for estimating vehicle position from cleaned sensor data.
    """

    # Signals that the state estimation would need to get (based on the R&D doc)
    REQUIRED_COLUMNS = [
        "timestamp",
        "latitude",
        "longitude",
        "longitudinal_acceleration",
        "lateral_acceleration",
        "yaw_rate",
        "vehicle_speed",
    ]

    # Bare minimum output (need to go back and add more)
    OUTPUT_COLUMNS = [
        "timestamp",
        "latitude",
        "longitude",
    ]

    def estimate_position(self, cleaned_df: pd.DataFrame) -> pd.DataFrame:
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


        return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

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