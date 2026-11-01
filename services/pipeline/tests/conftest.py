import os

import numpy as np
import pytest

# RunContext reads settings at import time; tests never touch a real database.
os.environ.setdefault("ORION_DATABASE_URL", "postgresql://test@localhost/test")


def _make_run(
    seed,
    lag_schedule,
    outages=(),
    dead=(),
    duration=1800.0,
    gps_scale=0.94,
    parked=False,
):
    """Build one fake run with a KNOWN, changing GPS delay.

    lag_schedule : [(measured_time_from, lag_s), ...]  true delay as a function of measurement time
    outages      : [(t0, t1), ...]  no GPS rows measured in these intervals (connection lost)
    dead         : [(t0, t1), ...]  GPS rows exist but read ~0 (no fix)
    Returns vcu_t, vcu_mph, gps_t (stamped), gps_mph, true_lag (per GPS row), measured_t (per GPS row)
    """
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, duration, 0.05)
    speed = np.zeros_like(t)
    if not parked:
        target, next_change = 0.0, 0.0
        for i in range(1, len(t)):
            if t[i] >= next_change:
                target = float(rng.choice([0.0, rng.uniform(10, 50)], p=[0.25, 0.75]))
                next_change = t[i] + rng.uniform(6, 18)
            rate = 6.0 if target > speed[i - 1] else 12.0
            speed[i] = speed[i - 1] + np.clip(
                target - speed[i - 1], -rate * 0.05, rate * 0.05
            )

    vcu_t = np.cumsum(rng.exponential(0.35, int(duration / 0.3)))
    vcu_t = vcu_t[vcu_t < duration]
    vcu_mph = np.interp(vcu_t, t, speed) + rng.normal(0, 0.3, len(vcu_t))

    tm = np.cumsum(rng.exponential(0.25, int(duration / 0.2)))
    tm = tm[tm < duration]
    for a, b in outages:
        tm = tm[(tm < a) | (tm >= b)]
    gps_mph = gps_scale * np.interp(tm, t, speed) + rng.normal(0, 0.4, len(tm))
    for a, b in dead:
        inside = (tm >= a) & (tm < b)
        gps_mph[inside] = np.abs(rng.normal(0, 0.05, inside.sum()))
    gps_mph = np.clip(gps_mph, 0, None)

    starts = np.array([s for s, _ in lag_schedule])
    values = np.array([v for _, v in lag_schedule])
    true_lag = values[np.searchsorted(starts, tm, side="right") - 1]
    stamped = tm + true_lag + rng.normal(0, 0.1, len(tm))
    order = np.argsort(stamped)
    return (
        vcu_t,
        np.clip(vcu_mph, 0, None),
        stamped[order],
        gps_mph[order],
        true_lag[order],
        tm[order],
    )


@pytest.fixture
def make_run():
    return _make_run
