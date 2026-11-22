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
lap_progress_step   1. pick the laps the ideal lap can come from
   │                2. pick the ideal lap from them
   │                3. measure every point along the ideal lap
   ▼
lap_progress        run_id, time, lap_id, lap_percent (0-100, never NULL)
   │
backend             GET /runs/{id}/laps/sensors/data?lap_ids=3&lap_ids=5
                    gives every sensor reading its lap_percent
```

The step trusts its input: it doesn't filter out points it thinks are bad. Every
position gets a percentage, and odd input gives odd percentages.

## 1. Pick the laps

The ideal lap is picked from every lap except:

| Left out | Why |
| --- | --- |
| The first lap | It includes the drive before the first crossing (the pits). |
| The last lap | It stops wherever the run stops. |
| A lap longer than 1.5 × the median lap | Two laps merged by a missed crossing. It would win the medoid (it covers the track twice) and double the ideal lap's length. |

A run with 1 or 2 laps has no lap left, so it gets no `lap_progress` rows: there's
no complete loop from the line back to the line to measure along.

## 2. Pick the ideal lap

The ideal lap is the ruler every lap is measured with. Each lap is redrawn with a
point every 1 m from the start/finish line, so every meter of track counts equally,
however fast the car went. The ideal lap is the **medoid**: the lap the other laps'
points are closest to, on average. It is then **lightly smoothed** (a closed spline
that may move it about 0.25 m RMS), which irons out GPS jitter.

We compared rulers on three runs, by how much the percentage at the same corner
differs between laps (lower is better):

| Run | Median-time lap | Medoid | Smoothed medoid (used) |
| --- | --- | --- | --- |
| 80a58216 | 0.30% | 0.61% | **0.25%** |
| 212c3dc4 | 5.30% | 2.04% | **1.31%** |
| 3adaad41 | 0.77% | 0.62% | **0.47%** |

## 3. Measure every point

- **Matching.** Each point is matched to its nearest ideal lap point, where heading
  counts too (each unit of heading difference counts as 10 m), so the far side of a
  hairpin, driven the other way, never matches. The point is then placed along the
  ideal lap's direction there, so the distance changes smoothly.
- **Never backwards.** Within a lap the percentage only goes up. A lap's first point
  more than half a lap "ahead" is really just before the line, so it reads 0%. The
  percentage is capped at 100, so a merged lap reads 100% for its second loop.
- **Impossible jumps don't count.** A match further ahead than the car could have
  driven since the lap's last progress (40 m/s × the time, plus 10 m) is a bad match,
  so that point keeps the previous percentage.

## 4. Where it is stored

The step's own table, `lap_progress`: one row per `estimated_car_state` row (same
`run_id` and `time`), with the `lap_id` the point falls in and its `lap_percent`.
The step uses the default step flow (`prepare` deletes the run's rows, `transform`
computes them, `write` appends them), so a re-run replaces them. The ideal lap is
rebuilt each run and not stored.

## 5. Backend

The percentages are on positions (OrionDB), but graphs need them on sensor readings
(Penelope), which have their own timestamps. The backend only matches the two by
time; it computes and stores nothing.

`GET /runs/{run_id}/laps/sensors/data?sensors=...&lap_ids=3&lap_ids=5&start_percent=40&end_percent=80`
returns one response per lap, in the order given (the percents default to the whole
lap). It reads `lap_progress` once for all the laps. Each lap's window is its first
and last position in the range; the readings in it are read from Penelope as usual,
and each reading gets the `lap_percent` of the position nearest in time (after the
GPS time offset). A lap with no position in the range is a 404.

The time-based `GET /runs/{run_id}/sensors/data` is unchanged.

## Constants

At the top of `lap_progress_utils.py`. They are starting values, checked on a
handful of runs.

| Constant | Value | What it does |
| --- | --- | --- |
| `SPACING_M` | 1.0 | Distance between the ideal lap's points |
| `SMOOTHING_M` | 0.25 | How far smoothing may move the ideal lap (RMS) |
| `MAX_LAP_LENGTH_RATIO` | 1.5 | Longest lap that may be the ideal lap, × the median |
| `HEADING_WEIGHT_M` | 10.0 | How much heading counts when matching |
| `MAX_SPEED_MPS` | 40.0 | Fastest the car can go, for the jump check |
| `JUMP_MARGIN_M` | 10.0 | Slack in the jump check |

## Limitations

- Runs with fewer than 3 laps get no percentages.
- Pit, pre-lap and stopped points still get a percentage (from the nearest track
  position), so they look odd in % charts.
- Backend readings after a data gap take the nearest position's percentage, however
  far away in time.
- If lap detection merges most laps of a run, the median lap is itself a merged lap
  and merged laps can be chosen.
- With one usable lap, that lap is the ideal lap, however unusual it is.
- Laps on very different lines (for example cutting across the infield) match less
  well.

## Code

| Where | What |
| --- | --- |
| `services/pipeline/src/orion_pipeline/steps/lap_progress_step/` | The step (`lap_progress_step.py`) and its helpers (`lap_progress_utils.py`) |
| `packages/orion_core/src/orion_core/models/orion/lap_progress_model.py` | The `lap_progress` table |
| `services/backend/src/orion_backend/services/sensor_service.py` | `get_lap_sensor_data` |
| `services/pipeline/tests/test_lap_progress_utils.py`, `test_lap_progress_step.py`, `services/backend/tests/test_sensor_lap_percent.py` | Tests |
