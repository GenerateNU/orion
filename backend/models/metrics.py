from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    """Derived metrics computed over a window (e.g. a lap) of VehicleState rows."""
    window_start: datetime
    window_end: datetime
    avg_speed_mps: float
    max_speed_mps: float
    total_distance_m: float
    battery_drain_rate_v_per_min: Optional[float] = None
    lap_number: Optional[int] = None