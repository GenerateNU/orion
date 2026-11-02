"""Track a time-varying GPS timestamp delay against a reference speed signal.

Problem
-------
TPU/GPS/* rows are stamped when they are saved, not when they are measured, so they
are late. The delay is not constant: it stays at one value for a long stretch, then
jumps (seen in real data: about 1 s, 6 s and 11 s), usually across long GPS outages.
We want the delay at every GPS sample, without assuming it is constant inside a fixed
window.

Method: lag tracking by dynamic programming (Viterbi)
-----------------------------------------------------
Picture a grid. Columns are GPS GroundSpeed samples (time), rows are candidate delays.

  cell cost  E[i, j]  how badly GPS speed g_i matches (scale * VCU speed) at time
                      t_i - lag_j. Squared error in units of the expected spread,
                      capped so one bad sample can't dominate (a robust Gaussian
                      log-likelihood). The spread grows when VCU has to be
                      interpolated across a gap. Zero for every lag (no preference)
                      where the GPS is dead: it reads ~0 for a while although VCU
                      shows no stop that long anywhere in the lag range.

  moving from one sample to the next:
      stay on the same lag     cost 0
      move one grid step       cost drift_penalty   (allows slow drift)
      jump to any other lag    cost jump_penalty    (allows sudden changes, anywhere)
  and, if enforce_order is on, the lag may not grow by more than the time that passed
  between the two samples, so corrected timestamps stay in order (data is saved
  first-in-first-out).

Viterbi finds the cheapest path through the grid exactly. The path is the delay at
every GPS sample. The scale factor (GPS reads a few % low; one run reads ~30% low) is
estimated first from speed quantiles, which don't depend on alignment, then refined
after each pass.

After tracking, the path is split into segments at jumps. Each segment gets a ~95%
interval from its profile cost and a quality flag. Segments without enough
information fall back to the nearest good segment, or to the old fixed default if the
whole run has nothing usable.

Conventions
-----------
lag > 0 means GPS is LATE.  corrected_time = stamped_time - lag.
Times are float seconds (epoch seconds are fine). Speeds are mph: convert GPS m/s with
MS_TO_MPH before calling.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np
import numpy.typing as npt

MS_TO_MPH = 2.23694
# fewest samples to fit the scale or the residual noise from
MIN_FIT_SAMPLES = 30

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int_]
ArrayLike = npt.ArrayLike


@dataclass(frozen=True)
class LagTrackerConfig:
    # candidate delays (s)
    lag_min: float = -5.0
    lag_max: float = 20.0
    lag_step: float = 0.05
    # matching
    noise_mph: float = 1.5  # typical GPS vs VCU mismatch once aligned
    truncate_sigma: float = 3.0  # residuals beyond this many noise units are capped
    # how fast speed can change: sets how unsure VCU interpolation is
    interp_accel_mph_s: float = 4.0
    max_ref_gap_s: float = 10.0  # beyond this VCU gap there is no reference at all
    fit_ref_gap_s: float = 1.5  # stricter gap limit for fitting scale and noise
    # path rules
    jump_penalty: float = 40.0
    drift_penalty: float = 3.0
    enforce_order: bool = True
    # dead GPS detection: a stretch where GPS reads below dead_gps_mph for at least
    # min_dead_s, but VCU has no stop that long anywhere within the candidate lag
    # range -> GPS had no fix
    dead_gps_mph: float = 1.0
    min_dead_s: float = 10.0
    # scale estimation
    scale_iterations: int = 2  # scale refinements between tracking passes
    min_moving_mph: float = 2.0
    # segment quality
    # a sample is informative if its mismatch varies this much across lags
    informative_contrast: float = 1.0
    min_informative: int = 50
    max_ci_width_s: float = 2.0
    ci_delta: float = 4.0  # profile-cost rise that defines the ~95% interval
    # fallback when nothing in the run can be measured (the old GPS_TIME_OFFSET_S)
    default_lag_s: float = 3.0
    # GPS samples closer together than this are back-to-back. A back-to-back sample
    # with exactly the previous value is a duplicate packet, ignored for the estimate.
    back_to_back_s: float = 0.2
    # run sanity: a fitted scale outside this range, or too few informative samples
    # in the whole run, means nothing trustworthy was measured -> all default
    min_scale: float = 0.6
    max_scale: float = 1.1
    min_run_informative: int = 50
    # self-check (logging only, never changes the correction): best lag per window
    # of real driving, found without tracking or penalties, vs the tracker's lag
    check_window_s: float = 60.0
    check_min_samples: int = 30  # GPS samples per window
    check_moving_mph: float = 5.0
    check_min_moving_frac: float = 0.3  # of VCU samples in the window
    check_min_speed_range_mph: float = 6.0
    check_max_gap_s: float = 5.0  # longest VCU or GPS silence allowed in a window
    # the best lag must beat every lag check_rival_min_s..check_rival_max_s away
    # from it by check_margin_mph, or the window can't tell them apart
    check_rival_min_s: float = 1.0
    check_rival_max_s: float = 3.0
    check_margin_mph: float = 0.7
    check_tolerance_s: float = 0.5
    check_min_agree: float = 0.8
    check_max_disagree_s: float = 2.0
    check_min_windows: int = 3


@dataclass
class Segment:
    start_t: float  # stamped time of first GPS sample in the segment
    end_t: float  # stamped time of last GPS sample in the segment
    lag_s: float  # the constant lag that fits the segment best
    ci_lo: float  # ~95% interval (nan if not measurable)
    ci_hi: float
    n_samples: int
    n_informative: int
    quality: str  # "ok" | "unreliable" (internal) | "fallback" | "default"


@dataclass
class LagResult:
    segments: list[Segment]  # sorted by start_t, never empty
    scale: float  # fitted GPS/VCU scale
    noise_mph: float  # estimated residual noise after alignment


@dataclass
class SelfCheck:
    n_windows: int  # usable windows of real driving
    agree_frac: float  # share within check_tolerance_s of the tracker (nan if none)
    worst_s: float  # largest disagreement (nan if none)
    suspicious: bool


# --------------------------------------------------------------------------- main entry
def track_gps_lag(
    vcu_t: ArrayLike,
    vcu_mph: ArrayLike,
    gps_t: ArrayLike,
    gps_mph: ArrayLike,
    cfg: LagTrackerConfig | None = None,
) -> LagResult:
    """Estimate the GPS delay of ONE run as a table of constant-lag segments.

    vcu_t, vcu_mph : VCU/CarState/speed times (s) and values (mph)
    gps_t, gps_mph : TPU/GPS/GroundSpeed stamped times (s) and values converted to mph
    Run this on the whole run at once (not page by page), then use `lag_at`.
    """
    cfg = cfg or LagTrackerConfig()
    vcu_t, vcu_mph = _clean_reference(vcu_t, vcu_mph)
    gps_t, gps_mph = _drop_repeats(*_sorted(gps_t, gps_mph), cfg)

    if len(gps_t) == 0 or len(vcu_t) < 2:
        return _default_result(gps_t, cfg)

    lags = _lag_grid(cfg)
    dead = _dead_mask(vcu_t, vcu_mph, gps_t, gps_mph, cfg)
    scale = _initial_scale(vcu_mph, gps_mph[~dead], cfg)

    # Track, refit the scale on the aligned samples, track again. The last pass's
    # path is the answer.
    for it in range(cfg.scale_iterations + 1):
        E, informative, contrast = _emissions(
            vcu_t, vcu_mph, gps_t, gps_mph, lags, scale, cfg, dead
        )
        path = _viterbi(E, gps_t, lags, cfg)
        ref, width = _reference_at(vcu_t, vcu_mph, gps_t - lags[path])
        use = (width <= cfg.fit_ref_gap_s) & informative & (ref > cfg.min_moving_mph)
        if it < cfg.scale_iterations and use.sum() >= MIN_FIT_SAMPLES:
            scale = float(np.dot(gps_mph[use], ref[use]) / np.dot(ref[use], ref[use]))

    noise = _robust_noise(gps_mph[use] - scale * ref[use], cfg)
    n_informative = int(informative.sum())
    if (
        not cfg.min_scale <= scale <= cfg.max_scale
        or n_informative < cfg.min_run_informative
    ):
        # Parked or barely moving, or GPS and VCU don't really match: report the
        # fitted scale, but don't trust any delay from this run.
        seg = replace(
            _default_result(gps_t, cfg).segments[0], n_informative=n_informative
        )
        return LagResult([seg], scale, noise)
    segments = _segments(path, gps_t, E, contrast, lags, noise, cfg)
    return LagResult(apply_fallbacks(segments, cfg.default_lag_s), scale, noise)


def self_check(
    vcu_t: ArrayLike,
    vcu_mph: ArrayLike,
    gps_t: ArrayLike,
    gps_mph: ArrayLike,
    result: LagResult,
    cfg: LagTrackerConfig | None = None,
) -> SelfCheck:
    """Compare the tracker with an independent, simpler estimate. Logging only.

    The run is split into check_window_s windows. A window of real driving with no
    long data gap gets its own best lag (no tracking, no penalties); that is
    compared with the tracker's lag at the window centre. Same inputs as
    `track_gps_lag`. A run whose scale was rejected has nothing to check.
    """
    cfg = cfg or LagTrackerConfig()
    vcu_t, vcu_mph = _clean_reference(vcu_t, vcu_mph)
    gps_t, gps_mph = _drop_repeats(*_sorted(gps_t, gps_mph), cfg)
    diffs = []
    plausible = cfg.min_scale <= result.scale <= cfg.max_scale
    if len(gps_t) and len(vcu_t) >= 2 and plausible:
        lags = _lag_grid(cfg)
        w = cfg.check_window_s
        for a in np.arange(gps_t[0], gps_t[-1] - w, w):
            g = (gps_t >= a) & (gps_t < a + w)
            in_v = (vcu_t >= a) & (vcu_t < a + w)
            v = vcu_mph[in_v]
            driving = (
                g.sum() >= cfg.check_min_samples
                and len(v) > 0
                and (v > cfg.check_moving_mph).mean() >= cfg.check_min_moving_frac
                and np.ptp(v) >= cfg.check_min_speed_range_mph
                and _max_gap(vcu_t[in_v], a, a + w) <= cfg.check_max_gap_s
                and _max_gap(gps_t[g], a, a + w) <= cfg.check_max_gap_s
            )
            if not driving:
                continue
            best = _window_lag(
                vcu_t, vcu_mph, gps_t[g], gps_mph[g], result.scale, lags, cfg
            )
            if best is not None:
                diffs.append(abs(best - float(lag_at([a + w / 2], result.segments)[0])))
    d = np.array(diffs)
    if len(d) == 0:
        return SelfCheck(0, np.nan, np.nan, False)
    agree, worst = float(np.mean(d <= cfg.check_tolerance_s)), float(d.max())
    suspicious = len(d) >= cfg.check_min_windows and (
        agree < cfg.check_min_agree or worst > cfg.check_max_disagree_s
    )
    return SelfCheck(len(d), agree, worst, suspicious)


def _max_gap(t: FloatArray, start: float, end: float) -> float:
    """Longest stretch of [start, end) with no sample in `t`."""
    return float(np.diff(np.concatenate([[start], t, [end]])).max())


def _window_lag(
    vcu_t: FloatArray,
    vcu_mph: FloatArray,
    gps_t: FloatArray,
    gps_mph: FloatArray,
    scale: float,
    lags: FloatArray,
    cfg: LagTrackerConfig,
) -> float | None:
    """The lag minimising median |GPS - scale * VCU| over one window, or None if it
    doesn't clearly beat its rivals (see check_rival_min_s)."""
    ref = np.interp(gps_t[None, :] - lags[:, None], vcu_t, vcu_mph)
    cost = np.median(np.abs(gps_mph[None, :] - scale * ref), axis=1)
    j = int(np.argmin(cost))
    away = np.abs(lags - lags[j])
    rivals = (away >= cfg.check_rival_min_s) & (away <= cfg.check_rival_max_s)
    if cost[rivals].min() < cost[j] + cfg.check_margin_mph:
        return None
    return float(lags[j])


def lag_at(stamped_t: ArrayLike, segments: Sequence[Segment]) -> FloatArray:
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


# --------------------------------------------------------------------------- pieces
def _lag_grid(cfg: LagTrackerConfig) -> FloatArray:
    return np.arange(cfg.lag_min, cfg.lag_max + cfg.lag_step / 2, cfg.lag_step)


def _drop_repeats(
    t: FloatArray, v: FloatArray, cfg: LagTrackerConfig
) -> tuple[FloatArray, FloatArray]:
    """Drop duplicate packets: a sample with exactly the previous sample's value,
    less than back_to_back_s after it. Only for the estimate; no rows are removed
    from the data."""
    repeat = np.zeros(len(t), dtype=bool)
    repeat[1:] = (np.diff(v) == 0) & (np.diff(t) < cfg.back_to_back_s)
    return t[~repeat], v[~repeat]


def _sorted(t: ArrayLike, v: ArrayLike) -> tuple[FloatArray, FloatArray]:
    t = np.asarray(t, dtype=float)
    v = np.asarray(v, dtype=float)
    keep = np.isfinite(t) & np.isfinite(v)
    t, v = t[keep], v[keep]
    order = np.argsort(t, kind="stable")
    return t[order], v[order]


def _clean_reference(t: ArrayLike, v: ArrayLike) -> tuple[FloatArray, FloatArray]:
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
    vcu_mph: FloatArray, gps_mph: FloatArray, cfg: LagTrackerConfig
) -> float:
    """Ratio of high speed quantiles while moving. Doesn't depend on time alignment."""
    g = gps_mph[gps_mph > cfg.min_moving_mph]
    v = vcu_mph[vcu_mph > cfg.min_moving_mph]
    if len(g) < MIN_FIT_SAMPLES or len(v) < MIN_FIT_SAMPLES:
        return 1.0
    return float(np.quantile(g, 0.9) / np.quantile(v, 0.9))


def _reference_at(
    vcu_t: FloatArray, vcu_mph: FloatArray, tq: FloatArray
) -> tuple[FloatArray, FloatArray]:
    """VCU speed interpolated at times tq, and the width of the VCU gap it was
    interpolated across (inf outside the VCU time range)."""
    inside = (tq >= vcu_t[0]) & (tq <= vcu_t[-1])
    ic = np.clip(np.searchsorted(vcu_t, tq), 1, len(vcu_t) - 1)
    width = np.where(inside, vcu_t[ic] - vcu_t[ic - 1], np.inf)
    return np.interp(tq, vcu_t, vcu_mph), width


def _runs(mask: npt.NDArray[np.bool_]) -> list[tuple[int, int]]:
    """(start, end) index pairs (end exclusive) of consecutive True values."""
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return [
        (int(a), int(b))
        for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1), strict=True)
    ]


def _dead_mask(
    vcu_t: FloatArray,
    vcu_mph: FloatArray,
    gps_t: FloatArray,
    gps_mph: FloatArray,
    cfg: LagTrackerConfig,
) -> npt.NDArray[np.bool_]:
    """GPS samples that read ~0 because the GPS had no fix, not because the car stopped.

    A GPS zero-stretch lasting D seconds is a real stop only if VCU shows a stop of
    similar length somewhere within [start - lag_max, end - lag_min]. If VCU's longest
    stop there is shorter than half of D, the GPS was dead and those samples carry no
    timing information.
    """
    dead = np.zeros(len(gps_t), dtype=bool)
    stopped = vcu_mph < cfg.min_moving_mph
    for a, b in _runs(gps_mph < cfg.dead_gps_mph):
        duration = gps_t[b - 1] - gps_t[a]
        if duration < cfg.min_dead_s:
            continue
        lo, hi = gps_t[a] - cfg.lag_max, gps_t[b - 1] - cfg.lag_min
        i0, i1 = np.searchsorted(vcu_t, [lo, hi])
        longest = 0.0
        for c, e in _runs(stopped[i0:i1]):
            longest = max(longest, vcu_t[i0 + e - 1] - vcu_t[i0 + c])
        if longest < 0.5 * duration:
            dead[a:b] = True
    return dead


def _emissions(
    vcu_t: FloatArray,
    vcu_mph: FloatArray,
    gps_t: FloatArray,
    gps_mph: FloatArray,
    lags: FloatArray,
    scale: float,
    cfg: LagTrackerConfig,
    dead: npt.NDArray[np.bool_],
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.bool_], FloatArray]:
    """Cost grid E[sample, lag] and a mask of informative samples."""
    n, m = len(gps_t), len(lags)
    E = np.zeros((n, m), dtype=np.float32)
    valid = np.zeros((n, m), dtype=bool)
    # range of the mismatch part only, to judge informativeness
    r_lo = np.full(n, np.inf)
    r_hi = np.full(n, -np.inf)
    cap = cfg.truncate_sigma**2
    for j, lag in enumerate(lags):
        ref, width = _reference_at(vcu_t, vcu_mph, gps_t - lag)
        ok = width <= cfg.max_ref_gap_s
        # interpolating across a wider VCU gap is less certain: widen the expected
        # spread (sigma) and pay log(sigma^2) for it, as in a Gaussian likelihood.
        # This keeps lags that land in VCU gaps from being unfairly favoured or
        # punished.
        w = np.where(ok, width, 0.0)
        var = cfg.noise_mph**2 + (cfg.interp_accel_mph_s * w / 2) ** 2
        r2 = (gps_mph - scale * ref) ** 2 / var
        mismatch = np.minimum(r2, cap)
        cost = mismatch + np.log(var / cfg.noise_mph**2)
        E[:, j] = np.where(ok, cost, 0.0)
        valid[:, j] = ok
        r_lo = np.where(ok, np.minimum(r_lo, mismatch), r_lo)
        r_hi = np.where(ok, np.maximum(r_hi, mismatch), r_hi)

    # cells with no reference at all (outside the VCU range) get the sample's average cost
    n_valid = valid.sum(axis=1)
    row_mean = np.where(
        n_valid > 0, (E * valid).sum(axis=1) / np.maximum(n_valid, 1), 0.0
    )
    E = np.where(valid, E, row_mean[:, None]).astype(np.float32)

    # dead GPS and samples with no usable VCU carry no information about the lag
    uninformative = dead | (n_valid == 0)
    E[uninformative] = 0.0

    # a sample is informative only if the mismatch itself changes with the lag
    # (a parked car matches every lag equally well, so it tells us nothing)
    contrast = np.where(n_valid > 0, r_hi - r_lo, 0.0)
    contrast[uninformative] = 0.0
    informative = contrast >= cfg.informative_contrast
    return E, informative, contrast


def _suffix_min(x: FloatArray) -> tuple[FloatArray, IntArray]:
    """sm[j] = min(x[j:]), sa[j] = index of that minimum."""
    n = len(x)
    rev = x[::-1]
    acc = np.minimum.accumulate(rev)
    pos = np.maximum.accumulate(np.where(rev <= acc, np.arange(n), 0))
    return acc[::-1], (n - 1 - pos)[::-1]


def _viterbi(
    E: npt.NDArray[np.float32],
    gps_t: FloatArray,
    lags: FloatArray,
    cfg: LagTrackerConfig,
) -> npt.NDArray[np.int64]:
    """Cheapest path through the cost grid. Returns the lag index at every sample."""
    n, m = E.shape
    step = lags[1] - lags[0] if m > 1 else 1.0
    ar = np.arange(m)
    back = np.empty((n, m), dtype=np.int32)
    D = E[0].astype(np.float64)
    back[0] = ar
    for i in range(1, n):
        dt = gps_t[i] - gps_t[i - 1]
        max_up = m if not cfg.enforce_order else int(np.floor(dt / step + 1e-9))

        best = D.copy()  # stay
        arg = ar.copy()

        cand = np.full(m, np.inf)  # drift down: from j+1
        cand[:-1] = D[1:] + cfg.drift_penalty
        better = cand < best
        best[better], arg[better] = cand[better], ar[better] + 1

        if max_up >= 1:  # drift up: from j-1
            cand = np.full(m, np.inf)
            cand[1:] = D[:-1] + cfg.drift_penalty
            better = cand < best
            best[better], arg[better] = cand[better], ar[better] - 1

        if max_up >= m:  # jump from anywhere
            jmin = int(np.argmin(D))
            cand = np.full(m, D[jmin] + cfg.jump_penalty)
            carg = np.full(m, jmin)
        else:  # jump from j' >= j - max_up (keeps order)
            sm, sa = _suffix_min(D)
            src = np.clip(ar - max_up, 0, m - 1)
            cand = sm[src] + cfg.jump_penalty
            carg = sa[src]
        better = cand < best
        best[better], arg[better] = cand[better], carg[better]

        D = best + E[i]
        D -= D.min()  # keep numbers small; doesn't change the argmin
        back[i] = arg

    path = np.empty(n, dtype=np.int64)
    path[-1] = int(np.argmin(D))
    for i in range(n - 1, 0, -1):
        path[i - 1] = back[i, path[i]]
    return path


def _robust_noise(resid: FloatArray, cfg: LagTrackerConfig) -> float:
    if len(resid) < MIN_FIT_SAMPLES:
        return cfg.noise_mph
    mad = np.median(np.abs(resid - np.median(resid)))
    return float(max(1.4826 * mad, 0.3))


def _segments(
    path: npt.NDArray[np.int64],
    gps_t: FloatArray,
    E: npt.NDArray[np.float32],
    contrast: FloatArray,
    lags: FloatArray,
    noise: float,
    cfg: LagTrackerConfig,
) -> list[Segment]:
    """Split the path at jumps (> 1 grid step) and score each piece. Each segment
    gets one constant lag: the one that fits its samples best (lowest summed cost).
    The path's median is only used to check the path agrees with that fit."""
    n = len(path)
    cuts = np.flatnonzero(np.abs(np.diff(path)) > 1) + 1
    bounds = np.concatenate([[0], cuts, [n]])
    rescale = (cfg.noise_mph / noise) ** 2
    segments: list[Segment] = []
    for a, b in zip(bounds[:-1], bounds[1:], strict=True):
        n_inf = int((contrast[a:b] >= cfg.informative_contrast).sum())
        profile = E[a:b].sum(axis=0) * rescale
        jmin = int(np.argmin(profile))
        lo = hi = jmin
        limit = profile[jmin] + cfg.ci_delta
        while lo > 0 and profile[lo - 1] <= limit:
            lo -= 1
        while hi < len(lags) - 1 and profile[hi + 1] <= limit:
            hi += 1
        ci_lo, ci_hi = float(lags[lo]), float(lags[hi])
        best_lag = float(lags[jmin])
        median_lag = float(np.median(lags[path[a:b]]))
        good = (
            n_inf >= cfg.min_informative
            and (ci_hi - ci_lo) <= cfg.max_ci_width_s
            and ci_lo - 0.5 <= median_lag <= ci_hi + 0.5
        )
        segments.append(
            Segment(
                start_t=float(gps_t[a]),
                end_t=float(gps_t[b - 1]),
                lag_s=best_lag,
                ci_lo=ci_lo if good else np.nan,
                ci_hi=ci_hi if good else np.nan,
                n_samples=int(b - a),
                n_informative=n_inf,
                quality="ok" if good else "unreliable",
            )
        )
    return segments


def apply_fallbacks(segments: list[Segment], default_lag_s: float) -> list[Segment]:
    """Replace unreliable segments: nearest "ok" segment in time -> "fallback";
    none -> "default"."""
    good = [seg for seg in segments if seg.quality == "ok"]

    def gap(a: Segment, b: Segment) -> float:
        return max(a.start_t - b.end_t, b.start_t - a.end_t, 0.0)

    out = []
    for seg in segments:
        if seg.quality == "ok":
            out.append(seg)
            continue
        if good:
            new_lag, quality = min(good, key=lambda g: gap(g, seg)).lag_s, "fallback"
        else:
            new_lag, quality = float(default_lag_s), "default"
        out.append(
            replace(seg, lag_s=new_lag, quality=quality, ci_lo=np.nan, ci_hi=np.nan)
        )
    return out


def _default_result(gps_t: FloatArray, cfg: LagTrackerConfig) -> LagResult:
    n = len(gps_t)
    seg = Segment(
        start_t=float(gps_t[0]) if n else np.nan,
        end_t=float(gps_t[-1]) if n else np.nan,
        lag_s=float(cfg.default_lag_s),
        ci_lo=np.nan,
        ci_hi=np.nan,
        n_samples=n,
        n_informative=0,
        quality="default",
    )
    return LagResult([seg], 1.0, cfg.noise_mph)
