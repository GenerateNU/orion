# Unit conversions
METERS_PER_DEGREE_LAT = 111_320.0
MPS_PER_MPH = 0.44704
from typing import Any

class PhysicsModelConfig:
    def __init__(
        self,
        model_name: str,
        model_params: dict[str, Any],
        straight_threshold: float = 1e-6,
    ) -> None:
        self.model_name = model_name
        self.model_params = model_params
        # rad/s, below this |turn rate| the car is treated as driving straight
        self.straight_threshold = straight_threshold

    def __repr__(self) -> str:
        return (
            f"PhysicsModelConfig(model_name={self.model_name}, "
            f"model_params={self.model_params})"
        )
