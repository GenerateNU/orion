# Lap detection

**Status: issue #55.** The logic is implemented and unit tested. `LapStep` is
imported in `steps/__init__.py`, so it's registered, but its dependency
`state_step` doesn't exist yet (see section 12).

| Exists | Doesn't exist yet |
| --- | --- |
| This design doc | `state_step`, which `LapStep` depends on |
| `LapStep` (`lap_step.py`) | A pytest job in CI |
| `lap_utils.py`: the `Gate` dataclass and every helper | Tuning the tunables against real runs |
| The `lap_*` tunables on `Settings` and `RunContext` | |
| The `laps` table model and its Alembic migration | |
| Unit tests: `tests/test_lap_utils.py` and `tests/test_lap_step.py` | |

Section 13 lists what's left, in order.

---

## 1. Background and goal

NER wants to compare car and driver performance lap by lap: lap times, speed
through each corner, how one lap differs from another. Every per-lap metric
needs to know where each lap **starts** and **ends**, so this step answers
that first.

The pipeline runs these steps in order:

```
clean_step  ──►  state_step  ──►  lap_step
(Penelope)       (cleaned_data)   (estimated_car_state)
                  NOT built yet    this doc
```

- `clean_step` reads raw readings from Penelope and writes `cleaned_data`.
- `state_step` will read `cleaned_data` and write `estimated_car_state`: where
  the car is at each moment. It isn't built yet.
- `lap_step` reads `estimated_car_state` and writes `laps`.

**Goal:** given the car's position over one run, split the run into laps
without anyone having to configure anything for the track.

## 2. Terms

| Term | Meaning |
| --- | --- |
| **Run** | One Penelope recording session, identified by `run_id`. |
| **Point** | One row of `estimated_car_state`: a time and a position. |
| **Local x/y** | A position in meters east (x) and north (y) of the run's first point. |
| **Heading** | The direction the car is driving at a point, as a unit vector (length 1). (0, 0) when the car isn't moving. |
| **Hitbox** | A small circle (3 m radius by default) around a point. If the car later comes back inside it, it has revisited that spot. |
| **Revisit** | The car coming back to a spot it already drove over. |
| **Gate** | The start/finish line: a 10 m segment across the track, perpendicular to the car's heading, centered on the first revisited point. |
| **Crossing** | The car driving forward through the gate. Each counted crossing ends one lap and starts the next. |

## 3. Input and output

### Input: `estimated_car_state`

| Column | Type | Meaning |
| --- | --- | --- |
| `run_id` | str | Penelope run id |
| `time` | datetime | When the car was at this position |
| `lattitude` | float | Latitude, in degrees |
| `longitude` | float | Longitude, in degrees |

The primary key is (`run_id`, `time`). Note the spelling: the column really
is called **`lattitude`** (two t's). The code uses it as spelled and doesn't
rename it.

The step reads it with `select_estimated_positions(run_id)` in
`orion_core/queries/orion_queries.py`: just `time`, `lattitude`, and
`longitude` for the whole run, ordered by time.

### Output: `laps`

| Column | Type | Meaning |
| --- | --- | --- |
| `run_id` | str | Penelope run id |
| `lap_id` | int | Lap number within the run, starting at 1 |
| `start_time` | datetime | When the lap started |
| `end_time` | datetime | When the lap ended |

- The primary key is (`run_id`, `lap_id`). `lap_id` isn't auto-incremented by
  the database. The step assigns it, starting at 1 for every run and
  increasing by 1.
- No foreign keys and no extra indexes. The primary key already covers
  lookups by `run_id`.
- **A point belongs to the lap whose half-open window `[start_time, end_time)`
  contains its time.** Half-open means the start time is included and the
  end time is not. So a point at exactly a lap boundary belongs to the lap
  that starts there.
- Lap membership comes **only** from these windows. Nothing is written back
  to `estimated_car_state`.

## 4. Approach

### Overview

Unlike the other steps, `LapStep` reads the **whole run at once** instead of
paging it. Then `transform` does four things, in order:

1. **Convert to meters.** Turn every latitude/longitude into local x/y
   (section 5).
2. **Find the gate.** Find the first place the car drives back over a spot
   it already drove over. That spot must be on the track's loop. Put a short
   start/finish line there, perpendicular to the car's heading (section 6).
3. **Find crossings.** Record every time the car drives **forward** through
   the gate, and drop crossings that come too soon after the previous one
   (section 7).
4. **Build laps.** Each counted crossing ends one lap and starts the next.
   The last lap ends at the run's last point (section 8).

```
 lat/lon ──► local x/y ──► find_gate ──► find_crossings ──► apply_min_lap_time ──► build_lap_rows
                            (sampled)      (every point)                              ──► laps
```

If there's no gate, step 3 is skipped and the whole run is one lap.

### Why one read instead of pages

The base class's pages exist because runs are too big to hold in memory. But
this step only needs three columns. A 30-minute run at 100 Hz is about
180,000 rows, which is a few MB as three numpy arrays.

Reading it in one go keeps the code simple. With pages, the step had to carry
state between them (the points searched so far, the previous page's last
point, the open lap, the last crossing time) and still missed some crossings
at page boundaries. With the whole run in one frame, every helper is a pure
function of arrays, and there are no page-boundary cases at all.

`pagination_key` is still set, because `PipelineStep` requires it, but
`extract` doesn't use it.

### Why this method

Alternatives considered:

1. **Configured start/finish coordinates per track.** Someone would have to
   record and maintain coordinates for every track and every cone layout,
   and every run would have to be matched to its track.
2. **Placing the gate at the first point.** The car may never come back to
   it, because it may lie off the repeated loop (for example in the pits).
3. **Analyzing the shape of the whole path** (for example, looking for
   repetition). More complex, and harder to explain and test.

The revisit-and-gate method needs no configuration, works on any closed
loop, and every piece is simple geometry that can be unit tested on its own.

## 5. Converting to meters

`to_local_xy(lat, lon)`.

Latitude and longitude are **angles**, not distances, so a "3 m" hitbox can't
be measured in degrees:

- One degree of latitude is about **111,195 m** everywhere
  (`6,371,000 × π / 180`).
- One degree of longitude shrinks as you move away from the equator: it's
  `111,195 × cos(latitude)`. At 42° latitude (roughly Boston) that's about
  **82,630 m**.

So every point is converted to flat x/y meters relative to an **origin**: the
run's first point, (`lat0`, `lon0`).

```
x = EARTH_RADIUS_M * radians(lon - lon0) * cos(radians(lat0))
y = EARTH_RADIUS_M * radians(lat - lat0)

EARTH_RADIUS_M = 6_371_000
```

x points east and y points north, both in meters. This is an
**equirectangular projection**: it treats the Earth as flat near the origin
and uses the origin's latitude to scale longitude. Over an area the size of a
track (a few hundred meters), the error is negligible.

`EARTH_RADIUS_M` lives in `lap_constants.py`. It's a physical constant, not
a tunable.

## 6. Finding the gate

`find_gate` downsamples the run, finds the first revisit with
`find_first_revisit`, and builds a `Gate` there.

### Downsampling

The search only looks at **every 5th point**
(`lap_gate_search_sample_every = 5`). This is a deliberate speed decision.

- Set it to 1 to search every point. Nothing else has to change.
- Finding crossings always uses every point.

At 100 Hz and 10 m/s, every 5th point is still a point every 50 cm, much
finer than the 3 m hitbox.

### Headings

`headings(x, y)` gives the unit heading at every point, from its neighbors
(`np.gradient`):

- At an interior point, the heading points from the point before it to the
  point after it.
- At the first and last points, it uses the point itself and its one
  neighbor.
- It's divided by its own length, so even a crawling car gets a unit
  heading.
- Where the neighbors are at exactly the same position (for example repeated
  GPS fixes while parked), the heading is **(0, 0)**. That point counts as
  **not moving**.

**Example:** neighbors (−1, 0) and (1, 0) give (2, 0) / 2 = (1, 0): driving
in +x (east).

The heading at the gate center comes from the **sampled** points, so its
neighbors are 5 points away.

### Distance driven

`distance_driven(x, y)` is the running total (cumsum) of the straight-line
step between consecutive points, starting at 0.

**Example:** points (0, 0), (3, 4), (6, 8) give 0, 5, 10. (Each step is a
3-4-5 triangle.)

Why it matters: a parked car can sit still for minutes, so the time check
alone would let it "revisit" itself. Its distance driven doesn't grow, so the
distance check stops that.

### The revisit rule

An earlier point P is a **candidate** for a later point Q when all four of
these are true:

1. **Q is inside P's hitbox:** `(xQ - xP)^2 + (yQ - yP)^2 <= lap_hitbox_radius_m^2`.
   Comparing squared distances avoids a square root.
2. **Enough time has passed:** `time_s[Q] - time_s[P] >= lap_min_revisit_time_s`
   (5 s). Consecutive points are always inside each other's hitboxes, and
   this excludes them.
3. **Enough distance was driven:** `distance_m[Q] - distance_m[P] >= lap_min_revisit_distance_m`
   (50 m). This excludes a parked or crawling car.
4. **P is moving:** its heading isn't (0, 0), so the gate has a direction.

**Hitbox example** (radius 3, so radius² = 9), with P = (10, 10):

- Q = (12, 11): `2² + 1² = 5 <= 9`, so Q is **inside**.
- Q = (13, 13): `3² + 3² = 18 > 9`, so Q is **outside**.

### `find_first_revisit`

1. **Cutoffs, all at once.** `time_s` and `distance_m` only ever increase.
   So for each Q, every point before some index is far enough back in both
   time and distance, and every point after it isn't. Binary search
   (`np.searchsorted`) finds that index for every Q in one call:

   ```
   time_cut     = searchsorted(time_s, time_s - lap_min_revisit_time_s, side="right")
   distance_cut = searchsorted(distance_m, distance_m - lap_min_revisit_distance_m, side="right")
   cutoff       = min(time_cut, distance_cut, index of Q)
   ```

   This replaces checking rules 2 and 3 point by point. Capping at Q's own
   index means Q is only ever compared with earlier points.
2. **Hitbox test.** For each Q in time order (skipping those with
   `cutoff == 0`), compute the squared distance from Q to every point
   before its cutoff, in one numpy operation. The candidates are the ones
   inside the hitbox that are moving.
3. **Closest wins.** The first Q with any candidates ends the search, and the
   candidate closest to Q is returned. That candidate is the gate center.
4. Returns None if no Q has a candidate.

The outer loop over Q stays a Python loop. The search needs the *earliest*
revisit, so it can stop as soon as it finds one, and comparing all points
with all points at once would need gigabytes of memory. Each iteration is a
single vectorized comparison, so even the worst case (no revisit on a long
run) takes about a second or two.

### Building the gate

The `Gate` dataclass stores:

| Field | Meaning |
| --- | --- |
| `x`, `y` | The gate center: the revisited point P |
| `heading_x`, `heading_y` | The unit heading at P: the direction the car drives through the gate |
| `half_width_m` | How far the gate reaches on each side of its center (`lap_gate_half_width_m`, 5 m) |

The gate line goes through the center, perpendicular to the heading, and is
`2 × half_width_m` (10 m) long.

```
                         ▲ left = +5
 ════════════════════════╪════════════════════  track edge
                         │
     car ───►         center ──────► heading      (heading, +x)
                         │
 ════════════════════════╪════════════════════  track edge
                         ▼ left = −5

        behind the line: ahead < 0  │  past the line: ahead >= 0
```

**Why the gate is wider than the hitbox.** The revisit point was within 3 m
(the hitbox radius) of the center, so the car's path on later laps goes
within about 3 m of it too. The gate reaches 5 m on each side, so those
passes cross the line comfortably inside it, with room for the driver taking
a slightly different line.

### No gate

If `find_gate` returns None, the car never came back to a spot it had
already driven over. **The whole run is one lap.** No crossings are looked
for, and `build_lap_rows` makes lap 1 from the run's start to its end.

## 7. Finding crossings

`find_crossings(x, y, gate)` looks at every pair of consecutive points,
**A then B**, over the whole run (not downsampled).

### Two coordinates relative to the gate

Every point is measured relative to the gate center, along two directions:

```
ahead = (x - gate.x) * heading_x + (y - gate.y) * heading_y
left  = (y - gate.y) * heading_x - (x - gate.x) * heading_y
```

- `ahead` is how far the point is past the gate line, along the heading.
  Negative means behind the line.
- `left` is how far the point is to the left of the gate center, along the
  line, when facing the heading.

### The two conditions

A move from A to B is counted only if **both** hold.

**1. Forward across the line:** `ahead(A) < 0` and `ahead(B) >= 0`.

A was behind the line and B is on or past it. Driving through backwards
fails, because then A is the point that's past the line. The heading doesn't
need to match exactly: any move from behind to past counts. A point exactly
on the line counts as "past", so the car is counted once, not twice.

**2. Inside the gate:** where the step A → B reaches the line,
`|left| <= half_width_m`.

The step reaches the line a fraction `t = ahead(A) / (ahead(A) − ahead(B))`
of the way from A to B, so `left` there is
`left(A) + t × (left(B) − left(A))`. Condition 1 alone only checks the
gate's line, which is infinitely long in the math. This stops a crossing of
that line elsewhere on the track (for example a parallel straight 40 m
away) from counting.

`find_crossings` returns the index of **B** (the first point past the line)
for every counted step.

### Worked examples

All use center (0, 0), heading (1, 0), and half width 5. Then `ahead = x`
and `left = y`.

**Counts.** A = (−1, −4), B = (1, −6).

- ahead(A) = −1 < 0 and ahead(B) = 1 ≥ 0. Condition 1 holds.
- t = −1 / (−1 − 1) = 0.5, so left at the line = −4 + 0.5 × (−6 − (−4)) = −5.
  |−5| ≤ 5, so it's **counted**.

**Outside the gate.** A = (−1, 20), B = (1, 20).

- Condition 1 holds, but left at the line = 20 > 5, so it's **not counted**.

**Wrong way.** A = (1, 0), B = (−1, 0).

- ahead(A) = 1 ≥ 0, so condition 1 fails and it's **not counted**.

### Minimum lap time

`apply_min_lap_time(start_time, crossing_times, lap_min_lap_time_s)`.

Crossings are processed in order, starting from the run's start time as the
first lap boundary. A crossing is **kept** only if it's at least
`lap_min_lap_time_s` (10 s) after the last boundary. Each kept crossing
becomes the new boundary; dropped ones don't.

This drops:

- **GPS jitter at the line** (forward, back, forward): the second forward
  step is within 10 s of the first.
- **A crossing right after the run starts**, for example when the car starts
  just behind the line. Without the start as the first boundary, that would
  make a lap 1 a few seconds long.

## 8. Laps

`build_lap_rows(run_id, start_time, end_time, crossing_times)`.

### Boundaries

- **The crossing time is t(B)**, the time of the first point past the line.
  The lap ending there gets `end_time = t(B)`, and the next lap gets
  `start_time = t(B)`.
- Under `[start, end)`, A is the last point of the finishing lap and B is the
  first point of the next. There are **no gaps and no overlaps**.
- There's no time interpolation. At 100 Hz, points are 10 ms apart, which is
  precise enough.
- **Lap 1** starts at the run's first point.
- **The final lap** ends at the run's last point. If the run's last point was
  itself a counted crossing, it isn't added again, so there's never an empty
  final lap.

### Timing example

A run from 12:00:00 to 12:02:40, with counted crossings at 12:01:05 and
12:02:10:

| lap_id | start_time | end_time | Window |
| --- | --- | --- | --- |
| 1 | 12:00:00 | 12:01:05 | `[12:00:00, 12:01:05)` |
| 2 | 12:01:05 | 12:02:10 | `[12:01:05, 12:02:10)` |
| 3 | 12:02:10 | 12:02:40 | `[12:02:10, 12:02:40]` (see "The final point") |

### Partial and bad laps

- **Everything before the first crossing is part of lap 1**: time in the
  pits, the out-lap, sitting on the grid.
- **The final lap runs to the end of the run**, even if the car stopped
  halfway round.
- **Bad laps are kept unchanged.** A 15-minute lap 7 (a spin, a red flag) is
  just lap 7. Filtering laps is a decision for whatever uses them later.
- **There's no "time between laps."** Every point belongs to exactly one lap.

### The final point

A known edge: under `[start, end)`, the run's very last point has
`time = end_time` of the final lap, so it's excluded from every lap.
**Whoever later assigns points to laps should treat the final lap's end as
inclusive.** This isn't handled in code now.

## 9. Edge cases

| Case | What happens |
| --- | --- |
| Empty run (no rows) | `extract` yields nothing, so `transform` never runs and nothing is written. The run's old laps are still deleted by `prepare`. |
| No revisit (e.g. a straight acceleration run) | No gate. One lap: (1, first time, last time). |
| Gate at the run's first point | The first point is on the line, not behind it, so it's not a crossing. Lap 1 starts there anyway. |
| Starting just behind the line | The first crossing is within `lap_min_lap_time_s` of the start, so it's dropped. |
| Out-lap from the pits | If the pit lane passes through the gate more than `lap_min_lap_time_s` after the start, that pass ends lap 1 (the out-lap). If sooner, the out-lap joins lap 1. |
| Car parked at the start | Its points are 0 m driven apart, so they can't revisit each other. A parked point with no heading can't be the gate center. |
| Car standing still mid-run | Its distance driven doesn't grow, so it fails the distance check and can't revisit itself. |
| GPS jitter at the line (forward, back, forward) | The backward step isn't counted, and the second forward step is within `lap_min_lap_time_s` of the first, so only one crossing counts. |
| Crossing the gate's extended line elsewhere | `|left|` at the line is more than `half_width_m`, so it isn't counted. |
| Driving through the gate backwards | `ahead(A) >= 0`, so condition 1 fails and it isn't counted. |
| The run's last point is a crossing | It isn't added again as the end time. No empty final lap. |
| The run's final point | Excluded from the final lap by the half-open rule. Consumers should treat the final lap's end as inclusive (section 8). |

## 10. Tunables

The tunables are `lap_*` fields on `Settings` (`orion_core/settings.py`), so
they can be set per environment with `LAP_*` variables (see `.env.example`).
`PipelineRunner` copies them onto `RunContext`, and `LapStep` passes them
into the `lap_utils` functions as arguments, so `lap_utils` stays pure.
Tests can override them per run with `RunContext(run_id=..., lap_...=...)`.

They are **untuned starting guesses**.

| Setting (env var) | Default | Meaning | Tradeoff |
| --- | --- | --- | --- |
| `lap_hitbox_radius_m` (`LAP_HITBOX_RADIUS_M`) | 3.0 | Radius of each point's hitbox, in meters | Bigger finds a revisit more easily (the driver's line varies lap to lap), but risks false revisits where two parts of the track come close. Smaller is stricter but may miss the revisit if the line changes. |
| `lap_min_revisit_time_s` (`LAP_MIN_REVISIT_TIME_S`) | 5.0 | Minimum time between two points for a revisit to count | Too small lets slow driving match itself. Too large could skip a very short loop. |
| `lap_min_revisit_distance_m` (`LAP_MIN_REVISIT_DISTANCE_M`) | 50.0 | Minimum distance driven between two points for a revisit to count | Too small lets a slowly creeping car match itself. Too large misses tracks shorter than it (not realistic for FSAE). |
| `lap_gate_search_sample_every` (`LAP_GATE_SEARCH_SAMPLE_EVERY`) | 5 | The gate search only looks at every Nth point | Bigger is faster but spaces sampled points further apart. Set to 1 to use every point. |
| `lap_gate_half_width_m` (`LAP_GATE_HALF_WIDTH_M`) | 5.0 | The gate reaches this far on each side of its center (10 m total) | Wider tolerates different racing lines, but risks catching a nearby, parallel part of the track. Should stay larger than the hitbox radius. |
| `lap_min_lap_time_s` (`LAP_MIN_LAP_TIME_S`) | 10.0 | Minimum time between two lap boundaries | Bigger suppresses more jitter, but must stay below the fastest real lap. |

## 11. Known limitations

These are deliberately not handled in this design.

- **False revisits mid-lap.** Separate parts of the track that pass within the
  hitbox radius of each other (a crossover, a tight hairpin next to a
  straight) can create a revisit partway round the lap. Out-and-back roads do
  the same. The gate would then be in the wrong place.
- **Noisy heading.** The heading comes from the nearest *sampled* neighbors
  only, so a nearly stopped car at the gate center can give a noisy heading.
- **Parked jitter adds distance.** If the position jitters while the car is
  parked, each jitter step adds to the distance driven, so a long enough stop
  could pass the distance check.
- **Figure-eights.** A layout like skidpad, where the car loops in both
  directions through the same center, gives odd laps.
- **Worst-case search time.** With no revisit on a very long run, every
  sampled point is compared with every earlier one. That's vectorized, so it
  takes about a second or two. If that's ever too slow, a spatial grid (only
  comparing against points in nearby cells) is an option.
- **The whole run is in memory.** Fine for three columns of a normal run
  (a few MB). A very long run would need paging again.
- **Untuned defaults.** None of the tunables have been checked against real
  runs.

## 12. Code layout

| File | What it is |
| --- | --- |
| `services/pipeline/src/orion_pipeline/steps/lap_step/lap_step.py` | `LapStep`: `extract` (one query for the whole run) and `transform` (the four stages in section 4). |
| `services/pipeline/src/orion_pipeline/steps/lap_step/lap_utils.py` | The `Gate` dataclass and the pure geometry helpers. |
| `services/pipeline/src/orion_pipeline/steps/lap_step/lap_constants.py` | `EARTH_RADIUS_M`. |
| `packages/orion_core/src/orion_core/settings.py` | The `lap_*` tunables (section 10). |
| `services/pipeline/src/orion_pipeline/runner/run_context.py` | `RunContext`, which carries the `lap_*` tunables to the step. |
| `packages/orion_core/src/orion_core/queries/orion_queries.py` | `select_estimated_positions`, the step's query. |
| `packages/orion_core/src/orion_core/models/orion/laps_model.py` | The `Lap` model (`laps` table). |
| `packages/orion_core/alembic/versions/20261026_466a05a95692_add_laps_table.py` | Migration that creates (and on downgrade drops) `laps`. |
| `services/pipeline/tests/test_lap_utils.py` | Unit tests for each `lap_utils` helper, plus `find_gate` on synthetic ovals (clean, started mid-turn, noisy, with a pit lane). |
| `services/pipeline/tests/test_lap_step.py` | End-to-end tests that run `LapStep` on synthetic circles, with mocked clients. |

### `lap_utils` functions

| Function | Purpose |
| --- | --- |
| `to_local_xy` | Latitude/longitude → local x/y meters (section 5). |
| `headings` | Unit heading at every point from its neighbors, (0, 0) where not moving. |
| `distance_driven` | Total distance driven up to every point. |
| `find_first_revisit` | Index of the first earlier point the car drives back over while moving, or None. |
| `find_gate` | Downsample, find the first revisit, and build the `Gate` there, or None. |
| `find_crossings` | Index of the first point past the gate for every forward pass through it. |
| `apply_min_lap_time` | Drop crossings too soon after the previous lap boundary, starting from the run's start. |
| `build_lap_rows` | Turn the crossings into `laps` rows. |

### How the base class's `run` drives `LapStep`

`LapStep` doesn't override `run` or `prepare`. The base class:

1. Calls `prepare`, which deletes the run's old laps so a re-run replaces
   them.
2. Calls `extract`, which reads the whole run with one query and yields it
   as a single frame, or yields nothing for an empty run.
3. Calls `transform` on that frame and `write`s the laps in one append.

`transform` is pure: no I/O and no state on `self` or `ctx`.

### Registration

`LapStep` has the `@register_step` decorator and is imported in
`steps/__init__.py`, so it's registered. **But its dependency `state_step`
isn't registered, so `ordered_steps()` raises `KeyError: 'state_step'`, and
every pipeline job fails.** Until `state_step` exists, either remove the
`lap_step` import from `steps/__init__.py`, or point `depends_on` at the step
that does write `estimated_car_state`.

### Running the tests

From the repo root:

```
uv run --project services/pipeline pytest services/pipeline/tests/test_lap_utils.py services/pipeline/tests/test_lap_step.py
```

`RunContext` reads `Settings` at import time, which needs
`ORION_DATABASE_URL` set in the environment or in `.env` (see
`.env.example`). `.env` is read from the current directory, which is why the
tests run from the repo root. The tests never connect to a database, so any
valid URL works.

## 13. Next steps

In order:

1. **Fix the registration** (section 12) so pipeline jobs don't fail before
   `state_step` exists.
2. **Add a pytest job to `BackendCI.yml`.** The pipeline has tests (these and
   the Kalman filter's), but CI doesn't run them yet.
3. **Build `state_step`**, so `estimated_car_state` has data.
4. **Tune the `lap_*` defaults against real runs.**
5. **Update the pipeline tables in `README.md` and `DevREADME.md`** with the
   `laps` output table and the step's status.
