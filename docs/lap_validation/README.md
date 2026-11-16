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

## How the validator works

The validator is one script,
[`services/pipeline/scripts/lap_viewer.py`](../../services/pipeline/scripts/lap_viewer.py).
It works on a run the pipeline has already processed.

1. **Load.** It reads two tables from OrionDB:
   - `estimated_car_state`, the run's positions
   - `laps`, the stored laps

   If either is empty, it says so and stops.
2. **Re-run the gate detection.** It calls the same `lap_utils.py` functions the
   lap step uses, with the same settings:
   - `to_local_xy`
   - `find_gate`
   - `find_crossings`
   - `apply_min_lap_time`

   The gate isn't stored in the database, so this is the only way to see it.
3. **Cross-check.** It compares the re-run's crossings with the stored lap
   boundaries. A mismatch means the `laps` table came from older code or other
   settings.
4. **Plot.** The path is drawn so you can step through it and see where each lap
   really starts and ends.

What's on screen, and where each item comes from:

| Item | Source |
|---|---|
| Point colors, black **X** lap ends, black slider lines, stored laps table | `laps` table |
| Pink **gate**, green/orange **circles** (crossings kept/dropped), dashed slider lines | Re-run gate detection |
| Purple slider marks | Gaps of more than 1 s in `estimated_car_state` |
| Info panel (time, speed, current lap, distance to gate) | The point under the slider |

The true laps are read off the path by hand. There are no timing sheets or video.

### Tools

- **matplotlib** draws the map, the slider and the info panel. It is a dev
  dependency.
- **OrionDB:** the local `orion-db` Docker container, read-only.
- **The lap step's own code** (`lap_utils.py`), so the validator can't drift from
  the pipeline.
- **The frontend** re-runs the pipeline on a run after a fix.

## Using it yourself

1. Start the stack with `docker compose up -d --build`, and process the run from
   the frontend at http://localhost:3000. You need the NER VPN for Penelope.
2. From the repo root, run:

   ```
   uv run python services/pipeline/scripts/lap_viewer.py <run_id>
   ```

   - `--every N` plots every Nth point. The default is 10; a bigger N is faster.
   - `--save out.png` saves an image instead of opening a window.
   - The database comes from `ORION_DATABASE_URL`. If that isn't set, the
     script uses the local container at `localhost:5434`.
3. Step through the run. Drag the slider, or click it and use ←/→, with Shift to
   move 50 points at a time. Write down the time each true lap starts and ends.
4. Compare your laps with the stored laps table. For each mismatch, work out the
   cause from the plot: a missed or extra crossing, the gate in the wrong place,
   or a data gap.
5. If you change a setting or the code, rebuild the backend container with
   `docker compose up -d --build backend`. Then re-run the run from the frontend
   and run the viewer again.
6. Add a folder for the run with a `README.md` and its images, in the same format
   as the existing runs, and add a row to the table above.
