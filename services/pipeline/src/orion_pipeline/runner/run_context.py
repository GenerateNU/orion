from pydantic import BaseModel

from orion_core.settings import get_settings


class RunContext(BaseModel):
    """What a step knows about the job it's running in.

    Steps take this instead of a bare run_id, so later we can add fields
    (time range, config, progress reporting) without changing every step.
    """

    run_id: str
    # Seconds added to gps_location timestamps in the clean step.
    gps_time_offset_s: float = get_settings().gps_time_offset_s

    # Lap step tunables. See the matching `lap_*` fields on Settings.
    lap_hitbox_radius_m: float = get_settings().lap_hitbox_radius_m
    lap_min_revisit_time_s: float = get_settings().lap_min_revisit_time_s
    lap_min_revisit_distance_m: float = get_settings().lap_min_revisit_distance_m
    lap_gate_search_sample_every: int = get_settings().lap_gate_search_sample_every
    lap_gate_half_width_m: float = get_settings().lap_gate_half_width_m
    lap_min_lap_time_s: float = get_settings().lap_min_lap_time_s

    # Lap progress step tunables. See the matching `lap_progress_*` fields on Settings.
    lap_progress_max_gap_s: float = get_settings().lap_progress_max_gap_s
    lap_progress_max_lap_time_ratio: float = (
        get_settings().lap_progress_max_lap_time_ratio
    )
    lap_progress_spacing_m: float = get_settings().lap_progress_spacing_m
    lap_progress_smoothing_m: float = get_settings().lap_progress_smoothing_m
    lap_progress_max_offtrack_m: float = get_settings().lap_progress_max_offtrack_m
    lap_progress_max_heading_diff_deg: float = (
        get_settings().lap_progress_max_heading_diff_deg
    )
    lap_progress_min_speed_mps: float = get_settings().lap_progress_min_speed_mps
    lap_progress_heading_weight_m: float = get_settings().lap_progress_heading_weight_m
    lap_progress_gate_margin_m: float = get_settings().lap_progress_gate_margin_m
    lap_progress_max_speed_mps: float = get_settings().lap_progress_max_speed_mps
    lap_progress_jump_margin_m: float = get_settings().lap_progress_jump_margin_m
