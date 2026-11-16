# Lap progress

Every point the car drove gets a **lap percentage**: how far round the lap it was,
from 0% at the start/finish line to 100% back at it. The same spot on track reads
the same percentage on every lap, so laps can be compared side by side ("lap 4 was
slower than lap 6 at 40%") no matter how long each one took.

## The whole flow

```
state_step          estimated_car_state: where the car was, 100 times a second
   │
lap_step            laps: when each lap starts and ends (docs/lap_detection.md)
   │
lap_progress_step   1. pick the good laps
   │                2. pick the ideal lap from them
   │                3. measure every point along the ideal lap
   ▼
estimated_car_state.lap_percent   (0-100, or NULL)
   │
backend             GET /runs/{id}/sensors/data?with_lap_percent=true
                    gives every sensor reading its lap_id and lap_percent
```

## 1. Pick the good laps

The ideal lap is picked from complete, normal laps only. A lap is left out if it is:

| Left out | Why |
| --- | --- |
| The first lap | It includes the drive before the first crossing (the pits). |
| The last lap | It stops wherever the run stops. |
| A lap with a hole in its data over 1 s | Its path has a gap in it. |
| A lap over 1.5 × the median lap time | Long stops, or two laps merged by a missed crossing. |

A run with fewer than 3 laps has no lap left, so it gets no percentages (every
`lap_percent` stays NULL).

## 2. Pick the ideal lap

The ideal lap is the ruler every lap is measured with. It is the **medoid**: the
chosen lap whose line the other laps are closest to, on average. Each lap is redrawn
with a point every 1 m from the start/finish line, then for each lap we measure how
far the other laps' points are from it. The lap with the smallest average wins.

Then it is **lightly smoothed** (a closed spline that may move it about 0.25 m), which
irons out GPS jitter and small hooks without moving the line.

### Why this one

We compared three rulers on three runs. "Corner spread" is how much the percentage
at the same corner differs between laps: lower is better.

| Run | Median lap time (old) | Medoid | Smoothed medoid (used) | Average of all laps |
| --- | --- | --- | --- | --- |
| 80a58216 | 0.30% | 0.61% | **0.25%** | 0.56% |
| 212c3dc4 | 5.30% | 2.04% | **1.31%** | 25.9% |
| 3adaad41 | 0.77% | 0.62% | **0.47%** | 1.30% |

- The **median-time lap** looks only at time, so it can pick a lap with an odd line
  (on 212c3dc4 it has a hook at the hairpin).
- The **average** sounds best but fell apart on real data: laps 1 m apart averaged in
  1 m bins mixed different laps in neighboring bins, and on tight tracks points got
  matched to the wrong part of the track. Each round made the path longer and
  wigglier (up to 2.5× the real lap).
- The **smoothed medoid** is a real lap the car drove, keeps a typical line, and
  had the lowest corner spread on every run.

## 3. Measure every point

Each point of the run is matched to the ideal lap and gets the distance along it,
turned into a percentage of its length.

- **Matching.** The nearest ideal lap point, where "nearest" counts the direction
  the car is heading too, so the far side of a hairpin never matches. The point is
  then placed between that ideal lap point and its neighbor, so percentages change
  smoothly instead of in 1 m steps.
- **Never backwards.** Within a lap the percentage only goes up. A lap starts at 0%
  and ends at 100% near the line, even if the car crosses it slightly early or late.
- **Impossible jumps are dropped.** A match further ahead than the car could have
  driven since its furthest progress (40 m/s × the time, plus 10 m) is a bad match,
  so that point gets NULL instead of skipping the rest of the lap ahead.

A point gets **NULL** (no percentage) when it is:

- more than 15 m from the ideal lap (pits, off track),
- heading more than 60° away from the ideal lap's direction (spins, wrong way),
- slower than 1 m/s (stopped on track),
- an impossible jump (above).

## 4. Where it is stored

One nullable column, `estimated_car_state.lap_percent`. No extra tables: a point's
lap always comes from the `laps` table by time, and the ideal lap is rebuilt each
run and thrown away.

The step follows the normal step flow: `prepare` sets the run's column back to NULL,
`transform` computes `(time, lap_percent)`, and `write` fills it in with one bulk
update. So a re-run replaces the values. When `state_step` re-runs it rewrites the
rows (back to NULL), and this step fills them in again in the same job.

## 5. Backend

`GET /runs/{run_id}/sensors/data?...&with_lap_percent=true` adds two lists to every
sensor series, one entry per reading:

- `lap_percent`: the `lap_percent` of the nearest point in `estimated_car_state`
  within 50 ms of the reading (after the GPS time offset), or null.
- `lap_id`: the lap whose `[start_time, end_time)` contains the reading (the last
  lap includes its end), or null.

Without the flag the response is exactly as before.

## Settings

All in `Settings` (`orion_core/settings.py`), each settable from `.env`:

| Setting | Default | What it does |
| --- | --- | --- |
| `lap_progress_max_gap_s` | 1.0 | Longest data hole a lap may have to be chosen |
| `lap_progress_max_lap_time_ratio` | 1.5 | Slowest lap that may be chosen, × the median |
| `lap_progress_spacing_m` | 1.0 | Distance between the ideal lap's points |
| `lap_progress_smoothing_m` | 0.25 | How far smoothing may move the ideal lap |
| `lap_progress_max_offtrack_m` | 15.0 | Further than this from the ideal lap: NULL |
| `lap_progress_max_heading_diff_deg` | 60.0 | Turned further than this: NULL |
| `lap_progress_min_speed_mps` | 1.0 | Slower than this: NULL |
| `lap_progress_heading_weight_m` | 10.0 | How much heading counts when matching (a full turnaround = 2 × this, in meters) |
| `lap_progress_gate_margin_m` | 20.0 | Near the line, a lap's first points read 0% and its last read 100% |
| `lap_progress_max_speed_mps` | 40.0 | Fastest the car can go, for the jump check |
| `lap_progress_jump_margin_m` | 10.0 | Slack in the jump check |
| `lap_percent_match_tolerance_s` | 0.05 | Backend: furthest a reading may be from its nearest point |

## Checking it by eye

Both scripts read the local OrionDB (or `ORION_DATABASE_URL`):

```bash
# Every lap with a dot where it reached the slider's percentage; dots that sit
# together (across the track from each other) mean the percentages line up.
uv run python services/pipeline/scripts/lap_percent_viewer.py <run id>

# The candidate ideal laps from the table above, drawn over the run's laps.
uv run python services/pipeline/scripts/ideal_lap_viewer.py <run id>
```

## Limitations

- Runs with fewer than 3 laps get no percentages.
- If lap detection merges most laps of a run (missed crossings), the median lap
  time is itself a merged lap and merged laps can be chosen. Widening the lap gate
  (`lap_gate_half_width_m`) fixed this on the runs we checked.
- With one usable lap, that lap is the ideal lap, however unusual it is.
- Laps on very different lines (for example cutting across the infield) match less
  of their points.
- The numbers above are starting values, checked on a handful of runs.

## Code

| Where | What |
| --- | --- |
| `services/pipeline/src/orion_pipeline/steps/lap_progress_step/` | The step (`lap_progress_step.py`), lap choice and medoid (`ideal_lap.py`), matching and percentages (`lap_progress_utils.py`) |
| `services/pipeline/src/orion_pipeline/clients/oriondb_client.py` | `set_null_for_run` and `update_for_run` (the bulk update) |
| `services/backend/src/orion_backend/services/sensor_service.py` | `attach_lap_progress` |
| `services/pipeline/tests/test_ideal_lap.py`, `test_lap_progress_step.py`, `test_oriondb_client.py`, `services/backend/tests/test_sensor_lap_percent.py` | Tests |
