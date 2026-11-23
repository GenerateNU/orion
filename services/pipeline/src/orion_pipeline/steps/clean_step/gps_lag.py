"""Estimate the time-varying GPS timestamp delay with a sliding window."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from orion_pipeline.steps.clean_step.gps_lag_config import (
    MIN_FIT_SAMPLES,
    LagTrackerConfig,
)


@dataclass
class Segment:
    start_t: float  # stamped time the lag starts to apply
    end_t: float
    lag_s: float
    n_samples: int  # GPS samples inside the segment
    quality: str  # "ok" | "fallback" | "default"


@dataclass
class LagResult:
    segments: list[Segment]  # sorted by start_t, never empty
    scale: float  # fitted GPS/VCU scale


def track_gps_lag(
    vcu_t: npt.ArrayLike,
    vcu_mph: npt.ArrayLike,
    gps_t: npt.ArrayLike,
    gps_mph: npt.ArrayLike,
    cfg: LagTrackerConfig | None = None,
) -> LagResult:
    """Estimate the GPS delay of ONE run as a table of constant-lag segments.

    vcu_t, vcu_mph : VCU/CarState/speed times (s) and values (mph)
    gps_t, gps_mph : TPU/GPS/GroundSpeed stamped times (s) and values converted to mph
    Run this on the whole run at once (not page by page), then use `lag_at`.
    """
    cfg = cfg or LagTrackerConfig()
    vcu_t, vcu_mph = _clean_reference(vcu_t, vcu_mph)
    gps_t, gps_mph = _sorted(gps_t, gps_mph)

    if len(gps_t) == 0 or len(vcu_t) < 2:
        return _default_result(gps_t, 1.0, cfg)

    lags = np.arange(cfg.lag_min, cfg.lag_max + cfg.lag_step / 2, cfg.lag_step)
    scale = _initial_scale(vcu_mph, gps_mph, cfg)
    starts = np.arange(gps_t[0], gps_t[-1] - cfg.window_s, cfg.hop_s)

    def measure(scale: float) -> npt.NDArray[np.float64]:
        return np.array(
            [
                _window_lag(vcu_t, vcu_mph, gps_t, gps_mph, a, scale, lags, cfg)
                for a in starts
            ]
        )

    # Measure every window, refit the scale on the aligned windows, measure again.
    window_lags = measure(scale)
    for _ in range(cfg.scale_iterations):
        scale = _refit_scale(
            vcu_t, vcu_mph, gps_t, gps_mph, starts, window_lags, scale, cfg
        )
        window_lags = measure(scale)

    measured = np.isfinite(window_lags)
    if not cfg.min_scale <= scale <= cfg.max_scale or measured.sum() < cfg.min_windows:
        # Parked or barely moving, or GPS and VCU don't really match: report the
        # fitted scale, but don't trust any delay from this run.
        return _default_result(gps_t, scale, cfg)
    return LagResult(_segments(starts, window_lags, gps_t, cfg), scale)


def lag_at(
    stamped_t: npt.ArrayLike, segments: Sequence[Segment]
) -> npt.NDArray[np.float64]:
    """Lag for arbitrary stamped times of any TPU/GPS/* sensor.

    Each time gets the lag of the last segment starting at or before it; times
    before the first segment get the first segment's lag. Rows sharing a packet
    timestamp with a GroundSpeed sample get exactly that sample's lag. A pure
    function of the row's own time, so paging can't change the answer.
    """
    starts = np.array([seg.start_t for seg in segments], dtype=float)
    lags = np.array([seg.lag_s for seg in segments], dtype=float)
    i = np.searchsorted(starts, np.asarray(stamped_t, dtype=float), side="right") - 1
    return lags[np.clip(i, 0, len(lags) - 1)]


def _sorted(
    t: npt.ArrayLike, v: npt.ArrayLike
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    t = np.asarray(t, dtype=float)
    v = np.asarray(v, dtype=float)
    keep = np.isfinite(t) & np.isfinite(v)
    t, v = t[keep], v[keep]
    order = np.argsort(t, kind="stable")
    return t[order], v[order]


def _clean_reference(
    t: npt.ArrayLike, v: npt.ArrayLike
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Sort VCU and average duplicate timestamps (interpolation needs strictly
    increasing times)."""
    t, v = _sorted(t, v)
    if len(t) == 0:
        return t, v
    uniq, inv = np.unique(t, return_inverse=True)
    sums = np.bincount(inv, weights=v)
    counts = np.bincount(inv)
    return uniq, sums / counts


def _initial_scale(
    vcu_mph: npt.NDArray[np.float64],
    gps_mph: npt.NDArray[np.float64],
    cfg: LagTrackerConfig,
) -> float:
    """Ratio of high speed quantiles while moving. Doesn't depend on time alignment."""
    g = gps_mph[gps_mph > cfg.min_moving_scale_mph]
    v = vcu_mph[vcu_mph > cfg.min_moving_scale_mph]
    if len(g) < MIN_FIT_SAMPLES or len(v) < MIN_FIT_SAMPLES:
        return 1.0
    return float(np.quantile(g, 0.9) / np.quantile(v, 0.9))


def _max_gap(t: npt.NDArray[np.float64], start: float, end: float) -> float:
    """Longest stretch of [start, end) with no sample in `t`."""
    return float(np.diff(np.concatenate([[start], t, [end]])).max())


def _window_lag(
    vcu_t: npt.NDArray[np.float64],
    vcu_mph: npt.NDArray[np.float64],
    gps_t: npt.NDArray[np.float64],
    gps_mph: npt.NDArray[np.float64],
    start: float,
    scale: float,
    lags: npt.NDArray[np.float64],
    cfg: LagTrackerConfig,
) -> float:
    """The lag minimising mean capped |GPS - scale * VCU| over the window starting at
    `start`, or nan if the window can't be trusted: too few or gappy samples, not
    really driving, no clear winner over nearby lags, or a VCU gap at that lag."""
    end = start + cfg.window_s
    i0, i1 = np.searchsorted(gps_t, [start, end])
    g_t, g_mph = gps_t[i0:i1], gps_mph[i0:i1]
    if (
        len(g_t) < cfg.min_samples
        or _max_gap(g_t, start, end) > cfg.max_gap_s
        or (g_mph > cfg.moving_mph).mean() < cfg.min_moving_frac
        or np.ptp(g_mph) < cfg.min_speed_range_mph
    ):
        return np.nan

    ref = np.interp(g_t[None, :] - lags[:, None], vcu_t, vcu_mph)
    cost = np.minimum(np.abs(g_mph[None, :] - scale * ref), cfg.trunc_mph).mean(axis=1)
    # lags that reach outside the VCU data have no reference
    cost[(g_t[0] - lags < vcu_t[0]) | (g_t[-1] - lags > vcu_t[-1])] = np.inf
    j = int(np.argmin(cost))
    if not np.isfinite(cost[j]):
        return np.nan
    away = np.abs(lags - lags[j])
    rivals = (away >= cfg.rival_min_s) & (away <= cfg.rival_max_s)
    if cost[rivals].min() < cost[j] + cfg.margin_mph:
        return np.nan

    # VCU must cover the matching stretch of time without a long silence
    lag = float(lags[j])
    v = vcu_t[(vcu_t >= start - lag) & (vcu_t < end - lag)]
    if _max_gap(v, start - lag, end - lag) > cfg.max_gap_s:
        return np.nan
    return lag


def _refit_scale(
    vcu_t: npt.NDArray[np.float64],
    vcu_mph: npt.NDArray[np.float64],
    gps_t: npt.NDArray[np.float64],
    gps_mph: npt.NDArray[np.float64],
    starts: npt.NDArray[np.float64],
    window_lags: npt.NDArray[np.float64],
    scale: float,
    cfg: LagTrackerConfig,
) -> float:
    """Least-squares GPS/VCU ratio over the samples of the measured windows, each
    aligned by its own lag. Keeps `scale` if there are too few."""
    gg = rr = 0.0
    n = 0
    for a, lag in zip(starts, window_lags, strict=True):
        if not np.isfinite(lag):
            continue
        i0, i1 = np.searchsorted(gps_t, [a, a + cfg.window_s])
        g = gps_mph[i0:i1]
        ref = np.interp(gps_t[i0:i1] - lag, vcu_t, vcu_mph)
        use = ref > cfg.min_moving_scale_mph
        gg += float(np.dot(g[use], ref[use]))
        rr += float(np.dot(ref[use], ref[use]))
        n += int(use.sum())
    return gg / rr if n >= MIN_FIT_SAMPLES and rr > 0 else scale


def _segments(
    starts: npt.NDArray[np.float64],
    window_lags: npt.NDArray[np.float64],
    gps_t: npt.NDArray[np.float64],
    cfg: LagTrackerConfig,
) -> list[Segment]:
    """One lag per hop, centred on its window, then runs of equal lag merged. Hops
    with no measurement take the nearest measured hop's lag."""
    ok = np.isfinite(window_lags)
    measured = np.flatnonzero(ok)
    hops = np.arange(len(starts))
    nearest = measured[np.abs(hops[:, None] - measured).argmin(axis=1)]
    hop_lag = window_lags[nearest]

    # hop k covers the middle hop_s of window k; the ends reach out to the run's edges
    lo = starts + (cfg.window_s - cfg.hop_s) / 2
    lo[0] = gps_t[0]
    hi = np.append(lo[1:], gps_t[-1])
    counts = np.searchsorted(gps_t, hi) - np.searchsorted(gps_t, lo)

    segments: list[Segment] = []
    for k in hops:
        quality = "ok" if ok[k] else "fallback"
        last = segments[-1] if segments else None
        if last and last.lag_s == hop_lag[k] and last.quality == quality:
            last.end_t = float(hi[k])
            last.n_samples += int(counts[k])
        else:
            segments.append(
                Segment(
                    float(lo[k]), float(hi[k]), float(hop_lag[k]), int(counts[k]), quality
                )
            )
    return segments


def _default_result(
    gps_t: npt.NDArray[np.float64], scale: float, cfg: LagTrackerConfig
) -> LagResult:
    n = len(gps_t)
    seg = Segment(
        start_t=float(gps_t[0]) if n else np.nan,
        end_t=float(gps_t[-1]) if n else np.nan,
        lag_s=float(cfg.default_lag_s),
        n_samples=n,
        quality="default",
    )
    return LagResult([seg], scale)
