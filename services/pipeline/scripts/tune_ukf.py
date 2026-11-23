import argparse
import itertools
from dataclasses import replace

import numpy as np
import pandas as pd

from orion_pipeline.steps.state_estimation.state import PX, PY
from orion_pipeline.steps.state_estimation.state_model_config import (
    GPS_STD_M,
    GYRO_STD_RADPS,
    SPEED_STD_MPS,
    UKFConfig,
)
from orion_pipeline.steps.state_estimation.ukf_step import UKFStep
from orion_pipeline.steps.state_estimation.urts_smoother import URTS

# Noise std per sensor, in the filter's units. Defaults: 1.5 m, 0.5 m/s, 0.05 rad/s
GRID = {
    "gps_std_m": [0.3, 0.5, 0.75, 1.0, 1.5],
    "speed_std_mps": [2.0, 3.0, 4.0, 6.0, 8.0],
    "gyro_std_radps": [0.2, 0.3, 0.5, 0.75, 1.0],
}

# Seconds added to every GPS timestamp, relative to the cleaned data
LAG_SHIFTS_S = [round(x, 2) for x in np.arange(-2.0, 2.01, 0.25)]


def load_readings(args: argparse.Namespace) -> pd.DataFrame:
    if args.file:
        return pd.read_parquet(args.file).sort_values(["time", "sensor"])

    from orion_core.db.engines import make_sync_engine
    from orion_core.queries.orion_queries import select_cleaned_readings
    from orion_core.settings import get_settings
    from orion_pipeline.clients.oriondb_client import OrionDBClient

    settings = get_settings()
    client = OrionDBClient(
        make_sync_engine(settings.orion_database_url), settings.pipeline_page_size
    )
    query = select_cleaned_readings(args.run_id, UKFConfig().sensors.keys())
    return client.read_frame(query.order_by(None).order_by("time", "sensor"))


def shift_gps(readings: pd.DataFrame, shift_s: float) -> pd.DataFrame:
    """Readings with GPS timestamps moved by the shift, re-sorted into time order."""
    if shift_s == 0:
        return readings
    out = readings.copy()
    is_gps = out["sensor"] == "gps_location"
    # Whole microseconds, so the shifted times fit the column's datetime64[us]
    delta = pd.Timedelta(seconds=shift_s).round("us")
    out["time"] = out["time"].where(~is_gps, out["time"] + delta)
    return out.sort_values(["time", "sensor"], kind="stable")


def split_holdout(
    readings: pd.DataFrame, every: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(readings without every Nth GPS fix, the withheld fixes). The first fix
    is always kept, since it sets the filter's origin."""
    is_gps = (readings["sensor"] == "gps_location").to_numpy()
    gps_index = np.cumsum(is_gps) - 1
    held = is_gps & (gps_index % every == every - 1)
    return readings[~held], readings[held]


def score(train: pd.DataFrame, held: pd.DataFrame, cfg: UKFConfig) -> float:
    ukf = UKFStep(cfg)
    ticks = ukf.push(train) + ukf.flush()
    if not ticks:
        return float("nan")
    smoothed = URTS.smooth_ticks(ticks)
    est = pd.DataFrame(
        [s.state[[PX, PY]] for s in smoothed],
        index=pd.DatetimeIndex([s.time for s in smoothed]),
        columns=["x", "y"],
    )
    est = est[~est.index.duplicated()]

    truth = pd.DataFrame(
        [ukf._to_xy(*v) for v in held["values"]],
        index=pd.DatetimeIndex(held["time"].dt.floor(cfg.tick)),
        columns=["x", "y"],
    )
    # Only fixes the filter was running at (not before startup or in a gap)
    truth = truth[truth.index.isin(est.index)]
    if truth.empty:
        return float("nan")
    diff = est.loc[truth.index].to_numpy() - truth.to_numpy()
    return float(np.sqrt(np.mean(np.sum(diff**2, axis=1))))


def make_config(
    gps_std_m: float = GPS_STD_M,
    speed_std_mps: float = SPEED_STD_MPS,
    gyro_std_radps: float = GYRO_STD_RADPS,
) -> UKFConfig:
    """The default config with new noise stds. Gating settings are kept."""
    base = UKFConfig()
    stds = {
        "gps_location": gps_std_m,
        "vcu_speed": speed_std_mps,
        "vcu_imu_gyro": gyro_std_radps,
    }
    return replace(
        base,
        sensors={
            name: replace(cfg, noise_std=stds.get(name, cfg.noise_std))
            for name, cfg in base.sensors.items()
        },
    )


def safe_score(train: pd.DataFrame, held: pd.DataFrame, cfg: UKFConfig) -> float:
    try:
        return score(train, held, cfg)
    except (np.linalg.LinAlgError, ValueError) as e:
        print(f"  failed: {e}")
        return float("nan")


def best_lag(readings: pd.DataFrame, every: int, center: float = 0.0) -> float:
    """Sweep LAG_SHIFTS_S (around center) with the default filter settings,
    return the best."""
    rows = []
    shifts = [round(center + d, 2) for d in LAG_SHIFTS_S]
    for shift in shifts:
        train, held = split_holdout(shift_gps(readings, shift), every)
        rmse = safe_score(train, held, make_config())
        rows.append((shift, rmse))
        print(f"  gps shift {shift:+.2f}s -> {rmse:.3f}")
    valid = [r for r in rows if not np.isnan(r[1])]
    if not valid:
        raise SystemExit("No lag shift produced a usable score.")
    shift = min(valid, key=lambda r: r[1])[0]
    if shift in (shifts[0], shifts[-1]):
        print("  WARNING: best shift is at the edge of the sweep; widen LAG_SHIFTS_S")
    print(f"best gps shift: {shift:+.2f}s")
    return shift


def main() -> None:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--run-id")
    src.add_argument("--file")
    ap.add_argument("--holdout-every", type=int, default=5)
    ap.add_argument("--gps-shift-s", type=float, help="skip the lag sweep, use this")
    ap.add_argument(
        "--lag-center", type=float, default=0.0, help="center of the lag sweep"
    )
    ap.add_argument("--out")
    args = ap.parse_args()

    readings = load_readings(args)
    if readings.empty:
        raise SystemExit(
            "No cleaned readings found. Is the run id right, and has "
            "clean_step run for it? (Only runs in cleaned_data work.)"
        )
    counts = readings["sensor"].value_counts()
    print("readings per sensor:", counts.to_dict())
    if counts.get("gps_location", 0) < 2:
        raise SystemExit("Need at least two gps_location readings.")

    print("Lag sweep:" if args.gps_shift_s is None else "Using given GPS shift")
    shift = (
        args.gps_shift_s
        if args.gps_shift_s is not None
        else best_lag(readings, args.holdout_every, args.lag_center)
    )
    train, held = split_holdout(shift_gps(readings, shift), args.holdout_every)
    print(f"{len(train)} readings, {len(held)} withheld GPS fixes")

    rows = []
    combos = list(itertools.product(*GRID.values()))
    for i, combo in enumerate(combos, 1):
        params = dict(zip(GRID, combo, strict=True))
        rmse = safe_score(train, held, make_config(**params))
        rows.append({**params, "gps_shift_s": shift, "rmse_m": rmse})
        print(f"[{i}/{len(combos)}] {params} -> {rmse:.3f}")

    results = pd.DataFrame(rows).sort_values("holdout_rmse_m")
    print("\nBest 10:\n", results.head(10).to_string(index=False))
    if args.out:
        results.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
