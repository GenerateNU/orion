# Lap validation

This folder checks the lap step ([lap_detection.md](../lap_detection.md)) against
real runs. For each run it compares the laps the step detected with the laps the
car actually drove, and records every mismatch, its cause and the fix.

## Runs

| Run | Layout | True laps | Before fix | After fix | Write-up |
|---|---|---|---|---|---|
| `80a58216-3dae-4c3d-ac69-f4afff3f928f` | Loop, ~140 × 185 m, ~45 s laps | 9 | 4 | 9 ✅ | [80a58216/](80a58216/README.md) |
| `212c3dc4-7c56-4836-b451-eb33d824a075` | Small loop, ~60 × 100 m, ~20 s laps | 14 | 7 | 14 ✅ | [212c3dc4/](212c3dc4/README.md) |

**Fix so far:** the gate was too short.
- Real drivers don't take the same line through the start/finish every lap.
- The default gate half-width went from 5 m (a 10 m gate) to 15 m (a 30 m
  gate), in `lap_gate_half_width_m` in
  [settings.py](../../packages/orion_core/src/orion_core/settings.py).
- It is covered by `test_default_gate_counts_laps_on_different_lines` in
  [test_lap_utils.py](../../services/pipeline/tests/test_lap_utils.py).

**Known and accepted:** a lap with idle time, a stop or a data gap in it still
counts that time in its duration. The boundaries are correct, but those laps
shouldn't be compared directly with driven laps.

## Method

Each run was one the pipeline had already processed.

1. Its positions (`estimated_car_state`) and stored laps (`laps`) were read from
   OrionDB.
2. The gate detection was re-run with the lap step's own `lap_utils.py`
   functions and settings (`to_local_xy`, `find_gate`, `find_crossings`,
   `apply_min_lap_time`), since the gate isn't stored in the database. The
   re-run's crossings were checked against the stored lap boundaries.
3. The true laps were read off the plotted path by hand. There are no timing
   sheets or video.
4. After a fix, the run was re-processed from the frontend and checked again.

To add a run, add a folder for it with a `README.md` in the same format as the
existing runs, and add a row to the table above.
