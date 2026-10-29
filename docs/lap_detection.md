# Lap detection

**Status: design spike for issue #55.** Nothing here runs yet.

| Exists                                                              | Doesn't exist yet                          |
| ------------------------------------------------------------------- | ------------------------------------------ |
| This design doc                                                     | The lap detection logic (every helper is a stub) |
| `LapStep`, with its two-pass plumbing written out                   | Unit tests                                 |
| `lap_utils.py`: dataclasses, constants, and a documented stub for every helper | Registering `LapStep` in the pipeline |
| The `laps` table model and its Alembic migration                    | `state_step`, which `LapStep` depends on   |

Running `LapStep` today raises `NotImplementedError` from the first stub it
calls. That's expected. Section 15 lists what to do, in order, to finish it.

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
| **Point** | One row of `estimated_car_state`: a time and a position. There are about 100 per second (100 Hz). |
| **Page** | The pipeline never loads a whole run at once. It reads it in pages of up to `PIPELINE_PAGE_SIZE` rows (100,000 by default), in time order. |
| **Pass** | One read of the whole run from start to end, page by page. This step reads the run twice. |
| **Local x/y** | A position in meters east (x) and north (y) of the run's first point. |
| **Hitbox** | A small circle (3 m radius) around a visited point. If the car later comes back inside it, it has revisited that spot. |
| **Revisit** | The car coming back to a spot it already drove over. |
| **Gate** | The start/finish line: a 10 m line segment across the track, perpendicular to the car's direction of travel, placed at the first revisit. |
| **Heading** | The direction the car is driving, as a unit vector (length 1). |
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

The table has no `lap_id` column, and lap detection doesn't add one.

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
  to `estimated_car_state`, and there's no "valid lap" column.

## 4. Approach

### Overview: two passes

The step reads the run twice.

1. **Pass 1, find the gate.** Find the first place the car drives over twice.
   That spot must be on the track's loop. Put a short start/finish line
   there, called the **gate**, perpendicular to the car's direction of
   travel. The gate is worked out from the data. Nothing is configured per
   track.
2. **Pass 2, count crossings.** Read the whole run again from the start and
   record every time the car drives **forward** through the gate. Each counted
   crossing ends one lap and starts the next.

```
 Pass 1                                   Pass 2
 ┌───────────────────────────────┐        ┌───────────────────────────────┐
 │ read pages until the car       │  gate  │ read every page from the start │
 │ revisits a spot; build the     │ ─────► │ and cut a lap at every forward │
 │ gate there, then stop reading  │        │ crossing of the gate           │
 └───────────────────────────────┘        └───────────────────────────────┘
```

Pass 1 usually stops after about one lap of data. Pass 2 always reads
everything.

### Why this method

Alternatives considered:

1. **Configured start/finish coordinates per track.** Someone would have to
   record and maintain coordinates for every track and every cone layout,
   and every run would have to be matched to its track.
2. **Placing it at the first datapoint** We may never revisit this point becuase it may lie off the repeated track.
3. **Analyzing the shape of the whole path** (for example, looking for
   repetition). More complex, and harder to explain and test.

The revisit-and-gate method needs no configuration, works on any closed
loop, and every piece is simple geometry that can be unit tested on its own.

## 5. Converting to meters

Latitude and longitude are **angles**, not distances, so a "3 m" hitbox can't
be measured in degrees:

- One degree of latitude is about **111,195 m** everywhere
  (`6,371,000 × π / 180`).
- One degree of longitude shrinks as you move away from the equator: it's
  `111,195 × cos(latitude)`. At 42° latitude (roughly Boston) that's about
  **82,630 m**.

So every point is converted to flat x/y meters relative to an **origin**: the
run's first point, (`lat0`, `lon0`). Both passes use the same origin, so the
gate from Pass 1 is in the same coordinates as the points in Pass 2.

```
x = EARTH_RADIUS_M * radians(lon - lon0) * cos(radians(lat0))
y = EARTH_RADIUS_M * radians(lat - lat0)

EARTH_RADIUS_M = 6_371_000
```

x points east and y points north, both in meters. This is an
**equirectangular projection**: it treats the Earth as flat near the origin
and uses the origin's latitude to scale longitude. Over an area the size of a
track (a few hundred meters), the error is negligible.

## 6. Pass 1: finding the gate

### Downsampling

Pass 1 only looks at **every 5th point** (`PASS1_SAMPLE_EVERY = 5`). This is a
deliberate speed decision.

- The count runs across the whole run, not per page. The step keeps a running
  **global row index**, and a row is sampled when
  `global_index % PASS1_SAMPLE_EVERY == 0`. This keeps the spacing even across
  page boundaries.
- **To undo it**, set `PASS1_SAMPLE_EVERY = 1`. Pass 1 then uses every point,
  and nothing else has to change.
- Pass 2 always uses every point.

Why: a 30-minute run at 100 Hz has about **180,000 points**. In the worst case
(no revisit is ever found), every point is compared with every earlier point.
That comparison is vectorized (see "Why vectorized" below), so even the worst
case takes a second or two rather than minutes.

Usually Pass 1 stops after the first lap, so in practice it's much cheaper.
At 100 Hz and 10 m/s, every 5th point is still a point every 50 cm, much
finer than the 3 m hitbox. The visited points take only a few MB.

### Visited points

Every sampled point is stored in a `VisitedPoints`: four parallel numpy
arrays, where index i of each array is the same point.

| Field | Meaning |
| --- | --- |
| `x`, `y` | Position in local meters |
| `time_s` | Seconds since the run's first point |
| `distance_m` | Total distance driven up to this point |

These are the candidates a later point can revisit, not revisits themselves.
`VisitedPoints` persists across pages, and is extended **once per page** (by
concatenating the whole page onto each array), not once per point.

### Why vectorized

Pass 1 previously compared each new point against every remembered point in a
Python loop. That's about 650 million iterations in the worst case (a long run
with no revisit), which takes minutes. Storing points in a growing DataFrame
would be worse, because adding a row copies the whole frame.

The plan instead:

- store points as numpy arrays,
- extend them once per page instead of once per point,
- compare each point against all earlier points in a single vectorized step.

Same result, but the worst case drops to a second or two. The math uses numpy
arrays rather than pandas Series because the loop runs tens of thousands of
times, and pandas adds a fixed overhead to every operation.

The outer loop over points stays a loop. Each point may only be compared with
earlier points, the search needs the earliest revisit, and comparing all
points with all points at once would need gigabytes of memory.

### Distance driven

Distance driven is worked out for a whole page at once. The step length
between consecutive sampled points is the straight-line distance:

```
step = sqrt(dx^2 + dy^2)
```

The page's first step is measured from the last point already in
`VisitedPoints`, if there is one. `distance_m` is then the running total
(cumsum) of the steps, starting from the last `distance_m` in
`VisitedPoints`, or 0 for the run's first point. The distance driven between
two visited points P and Q is simply `distance_m[Q] - distance_m[P]`, which
costs only one extra number per point.

**Example:** sampled points (0, 0), (3, 4), (6, 8) have `distance_m` 0, 5, 10.
(Each step is a 3-4-5 triangle.)

Why it matters: a parked car can sit still for minutes, so the time check
alone would let it "revisit" itself. Its distance driven doesn't grow, so the
distance check stops that.

### The hitbox test

Q is inside P's hitbox when the distance between them is at most
`HITBOX_RADIUS_M`. By Pythagoras:

```
(xQ - xP)^2 + (yQ - yP)^2 <= HITBOX_RADIUS_M^2
```

Comparing squared distances avoids a square root. `squared_distances`
computes the left-hand side from Q to many points P at once, as one numpy
operation.

**Example** (radius 3, so radius² = 9), with P = (10, 10):

- Q = (12, 11): `2² + 1² = 4 + 1 = 5 <= 9`, so Q is **inside**.
- Q = (13, 13): `3² + 3² = 9 + 9 = 18 > 9`, so Q is **outside**.

### The revisit rule

An earlier visited point P is a **candidate** for a later point Q when all
three of these are true:

1. **Q is inside P's hitbox:** `(xQ - xP)^2 + (yQ - yP)^2 <= HITBOX_RADIUS_M^2`.
2. **Enough time has passed:** `time_s[Q] - time_s[P] >= MIN_REVISIT_TIME_S`
   (5 s). Consecutive points are always inside each other's hitboxes, and this
   excludes them.
3. **Enough distance was driven:** `distance_m[Q] - distance_m[P] >= MIN_REVISIT_DISTANCE_M`
   (50 m). This excludes a parked or crawling car.

For each page, `find_revisit`:

1. Works out the page's `distance_m` (above) and extends `VisitedPoints` with
   the whole page. This happens first, so every index below refers to
   `VisitedPoints` itself.
2. For each of the page's points Q, at position q, in time order:
   1. **Cutoff.** `time_s` and `distance_m` only ever increase. So every point
      before some position is at least 5 s and 50 m of driving earlier than
      Q, and every point after that position isn't. Binary search finds it:

      ```
      time_cut = searchsorted(time_s[:q], time_s[q] - MIN_REVISIT_TIME_S, side="right")
      dist_cut = searchsorted(distance_m[:q], distance_m[q] - MIN_REVISIT_DISTANCE_M, side="right")
      cutoff   = min(time_cut, dist_cut)
      ```

      Only points before `cutoff` can be candidates, so this replaces checking
      rules 2 and 3 point by point.
   2. **Hitbox test.** `d2 = squared_distances(Q, x[:cutoff], y[:cutoff])`.
      The candidates are the indices where `d2 <= HITBOX_RADIUS_M^2`.
   3. **Closest first.** Q may be inside several visited points' hitboxes.
      The candidates are tried in order of smallest `d2`. The first candidate
      with a **valid heading** (below) becomes the gate center, and Pass 1
      stops reading pages. If no candidate has a valid heading, Pass 1 moves
      on to the next Q.

`VisitedPoints` keeps the whole page either way. That's fine, because Pass 1
stops reading pages as soon as a gate is found.

### Heading at P

The car's direction at P comes from P's neighbors in `VisitedPoints`:

- `before` is the visited point at P's index − 1, or P itself if P is
  index 0.
- `after` is the visited point at P's index + 1, or P itself if there
  isn't one.
- `h = after − before`.
- If `|h| < MIN_HEADING_SPAN_M` (0.1 m), the heading is **invalid**: the car
  was essentially standing still at P, for example parked on the line before
  driving.
- Otherwise the unit heading is `ĥ = h / |h|`.

**Example:** before = (−1, 0), after = (1, 0) gives h = (2, 0), |h| = 2, and
ĥ = (1, 0): driving in +x (east).

### No gate

If no gate is found after all pages, the car never came back to a spot it
had already driven over. **The whole run is one lap.**

## 7. Building the gate

Given the gate center P and the heading ĥ at P:

- **Center:** `C = (xP, yP)`.
- **Normal:** `n̂ = (−ĥy, ĥx)`. This is the heading rotated 90° to the left,
  and it points along the gate line.
- **Endpoints:** `G1 = C + w·n̂` is the gate's **left** end and
  `G2 = C − w·n̂` its **right** end, when facing the driving direction.
  `w = GATE_HALF_WIDTH_M` (5 m), so the gate is 10 m long in total.

The `Gate` dataclass stores just G1 and G2.

**Why the order matters.** The side test in section 8 measures which side of
the arrow G1 → G2 a point is on. Because G1 is on the left and G2 on the
right, that arrow points to the car's right, so "ahead of the line" always
comes out positive and "behind" negative. Swap them and every sign flips,
which would count laps driven backwards instead.

**Example:** C = (0, 0), ĥ = (1, 0) (driving +x) gives n̂ = (0, 1),
G1 = (0, 5), and G2 = (0, −5).

```
                        G1 = C + w·n̂   (0, 5)    left end
                         │
 ════════════════════════╪════════════════════  track edge
                         │
                         │
     car ───►            C ──────► ĥ            (heading, +x)
                         │
                         │
 ════════════════════════╪════════════════════  track edge
                         │
                        G2 = C − w·n̂   (0, −5)   right end

   behind the line: side < 0  │  past the line: side >= 0
```

**Why the gate is wider than the hitbox.** The revisit point was within 3 m
(the hitbox radius) of C, so the car's path on later laps goes through within
about 3 m of C too. The gate reaches 5 m on each side, so those passes cross
the line comfortably inside it, with room for the driver taking a slightly
different line.

## 8. Pass 2: detecting crossings

Pass 2 looks at every pair of consecutive points, **A then B**.

### The cross product

For two arrows u and v:

```
cross(u, v) = ux·vy − uy·vx
```

It's a single number, and only its sign matters here. Stand at the tail of u
and look along it: if v points to your **left**, the result is positive; to
your **right**, negative; along the same line, zero.

### The side test

```
side(P) = cross(G2 − G1, P − G1)
```

This asks which side of the arrow G1 → G2 the point P lies on. Since that
arrow points to the driver's right (section 7), points ahead of the line come
out positive.

- `side(P) < 0`: P is **behind** the line (the car hasn't reached it yet).
- `side(P) >= 0`: P is **on or past** the line.

### The two conditions

A move from A to B is counted only if **both** hold.

**1. Forward across the line:** `side(A) < 0` and `side(B) >= 0`.

A was behind the line and B is on or past it. Driving through backwards fails,
because then A is the point that's past the line. The heading doesn't need to
match exactly: any move from behind to past counts. A point exactly on the line
counts as "past", so the car is counted once, not twice.

**2. Inside the gate:** G1 and G2 are on opposite sides of the line through A
and B.

```
d1 = cross(B − A, G1 − A)
d2 = cross(B − A, G2 − A)
```

d1 and d2 say which side of the car's path each gate end is on. If
`d1 · d2 <= 0` they're on opposite sides (or one is exactly on the path), so
the path went between the ends. Condition 1 alone only checks the gate's line,
which is infinitely long in the math; this stops a crossing of that line
elsewhere on the track (for example a parallel straight 40 m away) from
counting.

### Worked examples

All use C = (0, 0), ĥ = (1, 0), n̂ = (0, 1), and w = 5, so G1 = (0, 5),
G2 = (0, −5), and G2 − G1 = (0, −10).

**Counts.** A = (−2, 2), B = (1.5, 2).

- side(A) = cross((0, −10), (−2, −3)) = −20: behind.
- side(B) = cross((0, −10), (1.5, −3)) = 15: past. Condition 1 holds.
- B − A = (3.5, 0). d1 = cross((3.5, 0), (2, 3)) = 10.5 and
  d2 = cross((3.5, 0), (2, −7)) = −24.5. Opposite signs, so it's **counted**.

**Outside the gate.** A = (−1, 40), B = (1, 40).

- Condition 1 holds (A is behind, B is past).
- B − A = (2, 0). d1 = cross((2, 0), (1, −35)) = −70 and
  d2 = cross((2, 0), (1, −45)) = −90. Same sign, so it's **not counted**.

**Wrong way.** A = (1.5, −3), B = (−1.5, −3).

- side(A) = cross((0, −10), (1.5, −8)) = 15, which is ≥ 0. Condition 1 fails,
  so it's **not counted**.

### Minimum lap time

Crossings are processed in order. A crossing is **kept** only if `t − last_counted >= MIN_LAP_TIME_S` (10 s).

## 9. Laps

### Boundaries

- **The crossing time is t(B)**, the time of the first point past the line.
  The lap ending there gets `end_time = t(B)`, and the next lap gets
  `start_time = t(B)`.
- Under `[start, end)`, A is the last point of the finishing lap and B is the
  first point of the next. There are **no gaps and no overlaps**.
- There's no time interpolation. At 100 Hz, points are 10 ms apart, which is
  precise enough.
- **Lap 1** starts at the run's first point.
- **Each counted crossing** closes the current lap and opens the next.
  `lap_id` starts at 1 and increases by 1.
- **The final lap** ends at the time of the run's last point.

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
- **No gate** gives one lap: (1, first time, last time).
- **An empty run** (no rows) writes nothing.

### Gate at the first point

If the gate center is the run's first point, there's no point before it on
the car's first pass, so that pass isn't a crossing. That's fine: lap 1
starts at the run's first point, which is the gate anyway.

### The final point

A known edge: under `[start, end)`, the run's very last point has
`time = end_time` of the final lap, so it's excluded from every lap.
**Whoever later assigns points to laps should treat the final lap's end as
inclusive.** This isn't handled in code now.

## 10. Pagination

Neither pass ever holds the whole run in memory. Each reads pages in time
order, and keeps a small amount of state between pages. Empty pages are
skipped in both passes.

**Pass 1** stops reading as soon as a gate is found.

| Carried across pages | Why |
| --- | --- |
| The `VisitedPoints` | A revisit is usually of a point on an earlier page. The running distance driven continues from the last `distance_m` in `VisitedPoints`. |
| The global row index | So downsampling keeps every 5th row of the *run*, not of each page. |
| The origin (`lat0`, `lon0`) and run start time | Recorded from the first row of the first page. Every later x/y and `time_s` is relative to them. |

**Pass 2** restarts from the first page (by calling `extract` again).

| Carried across pages | Why |
| --- | --- |
| `previous`: the last point (x, y, time) of the previous page | Paired with the new page's first point, so a crossing between two pages isn't missed. |
| The current `lap_id` | Lap numbers continue across pages. |
| The current lap's `start_time` | A lap usually spans several pages. |
| The last counted crossing time | The minimum lap time check needs it, even across pages. |
| The last time seen | The end of the run, for the final lap. |

**Why the carried point matters.** If the car crosses the gate between the
last point of page 4 and the first point of page 5, neither page contains
both A and B. Without carrying the last point over, that lap would silently
merge with the next one.

```
 page 4                        │  page 5
 ... ●     ●     ●     A ──────┼──► B     ●     ●  ...
                    side < 0   │ gate     side >= 0
           previous = A ───────┘ checked against B
```

## 11. Edge cases

| Case | What happens |
| --- | --- |
| Empty run (no rows) | Nothing is written. |
| No revisit (e.g. a straight acceleration run) | No gate. One lap: (1, first time, last time). |
| Gate at the run's first point | The first pass isn't a crossing (there's no point before it). Lap 1 still starts at the gate. |
| Car parked on the line at the start | Its heading span is below `MIN_HEADING_SPAN_M`, so that point can't be the gate center. The next candidate is tried. |
| Car standing still mid-run | Its distance driven doesn't grow, so it fails the `MIN_REVISIT_DISTANCE_M` check and can't revisit itself. |
| GPS jitter at the line (forward, back, forward) | The backward step isn't counted, and the second forward step is within `MIN_LAP_TIME_S` of the first, so only one crossing counts. |
| Crossing the gate's extended line elsewhere | G1 and G2 are on the same side of the path (`d1 · d2 > 0`), so it isn't counted. |
| Driving through the gate backwards | `side(A) >= 0`, so condition 1 fails and it isn't counted. |
| A crossing on a page boundary | The previous page's last point is paired with this page's first point, so it's found. |
| The run's final point | Excluded from the final lap by the half-open rule. Consumers should treat the final lap's end as inclusive (section 9). |

## 12. Tunable constants

These live in `lap_constants.py` and are passed into the `lap_utils`
functions as arguments so `lap_utils` stays pure. They are
**untuned starting guesses** and should potentially move to `Settings` later.

| Name | Value | Meaning | Tradeoff |
| --- | --- | --- | --- |
| `HITBOX_RADIUS_M` | 3.0 | Radius of each visited point's hitbox | Bigger finds a revisit more easily (the driver's line varies lap to lap), but risks false revisits where two parts of the track come close. Smaller is stricter but may miss the revisit if the line changes. |
| `MIN_REVISIT_TIME_S` | 5.0 | Minimum time between two points for a hit to count | Too small lets slow driving match itself. Too large could skip a very short loop. |
| `MIN_REVISIT_DISTANCE_M` | 50.0 | Minimum distance driven between two points for a hit to count | Too small lets a slowly creeping car match itself. Too large misses tracks shorter than it (not realistic for FSAE). |
| `PASS1_SAMPLE_EVERY` | 5 | Pass 1 only looks at every Nth point | Bigger is faster but spaces sampled points further apart. Set to 1 to use every point. |
| `MIN_HEADING_SPAN_M` | 0.1 | Minimum distance between the two neighbors used for heading | Too small accepts noisy headings from a nearly stopped car. Too large rejects valid slow points. |
| `GATE_HALF_WIDTH_M` | 5.0 | The gate reaches this far on each side of its center (10 m total) | Wider tolerates different racing lines, but risks catching a nearby, parallel part of the track. Should stay larger than `HITBOX_RADIUS_M`. |
| `MIN_LAP_TIME_S` | 10.0 | Minimum time between two counted crossings | Bigger suppresses more jitter, but must stay below the fastest real lap. |

## 13. Known limitations

These are deliberately not handled in this design.

- **False revisits mid-lap.** Separate parts of the track that pass within the
  hitbox radius of each other (a crossover, a tight hairpin next to a
  straight) can create a revisit partway round the lap. Out-and-back roads do
  the same. The gate would then be in the wrong place.
- **Noisy heading.** The heading comes from the nearest *sampled* neighbors
  only
- **Parked jitter adds distance.** If the position jitters while the car is
  parked, each jitter step adds to the distance driven, so a long enough stop
  could pass the distance check.
- **Figure-eights.** A layout like skidpad, where the car loops in both
  directions through the same center, gives odd laps.
- **Worst-case search time.** Pass 1's worst case (no revisit on a very long
  run) compares every point with every earlier point. The comparisons are
  vectorized (section 6), so this takes about a second or two. If that's ever
  too slow, a spatial grid (only comparing against points in nearby cells) is
  still an option.
- **Untuned constants.** None of the constants have been checked against real
  runs.

## 14. Code layout

| File | What it is |
| --- | --- |
| `services/pipeline/src/orion_pipeline/steps/lap_step/lap_step.py` | `LapStep`: attributes, `extract`, and the two-pass plumbing. Real code. |
| `services/pipeline/src/orion_pipeline/steps/lap_step/lap_constants.py` | `EARTH_RADIUS_M` and the tunable constants from section 12. |
| `services/pipeline/src/orion_pipeline/steps/lap_step/lap_utils.py` | Pure geometry helpers. The dataclasses are real; every function is a documented stub. |
| `packages/orion_core/src/orion_core/models/orion/laps_model.py` | The `Lap` model (`laps` table). It replaced the unused `Metrics` draft that was in this file. |
| `packages/orion_core/alembic/versions/20261026_466a05a95692_add_laps_table.py` | Migration that creates (and on downgrade drops) `laps`. |

### `lap_utils` functions

| Function | Purpose |
| --- | --- |
| `to_local_xy` | Latitude/longitude → local x/y meters (equirectangular, section 5). |
| `seconds_since` | Seconds from the run's start to each time. |
| `downsample` | Keep rows whose global index is divisible by `every_n`. |
| `squared_distances` | Squared distance from one point to many points at once, for the hitbox test. |
| `heading_at` | Unit heading at a visited point from its neighbors, or None. |
| `find_revisit` | Extend `VisitedPoints` with one page's sampled points, then search them in order and return the first valid revisit. |
| `build_gate` | Build a `Gate` (G1 left, G2 right) from a center, heading, and half width. |
| `cross_2d` | The 2D cross product `ux·vy − uy·vx`. |
| `side_of_gate` | side(P): negative behind the gate line, zero or positive on or past it. |
| `crosses_gate` | Both crossing conditions for one pair A → B. |
| `find_crossings` | t(B) for every counted pair in a page, including (previous, first point). |
| `apply_min_lap_time` | Drop crossings too soon after the last counted one. |
| `build_lap_rows` | Turn crossings into finished-lap rows, and return the next lap_id and lap start. |
| `make_lap_row` | A one-row DataFrame for a single lap. |

The dataclasses are `Gate` (left end G1 and right end G2), `VisitedPoints`
(parallel numpy float arrays `x`, `y`, `time_s`, `distance_m`), and `TrackPoint` (x, y,
time: the point Pass 2 carries between pages).

### How `LapStep.run` drives the two passes

Every other step uses the base class's `run`: prepare, then
extract → transform → write once per page. `LapStep` needs two reads of the
run, so it overrides `run`:

1. Reset the carry-over state.
2. `prepare`: the base class default, which deletes the run's old laps so a
   re-run replaces them.
3. **Pass 1:** `_find_gate` reads pages until `find_revisit` finds a revisit,
   and records the origin and the run's start and end times along the way.
4. If no row was read, stop (empty run).
5. If there's no gate, write one lap covering the whole run and stop.
6. **Pass 2:** open lap 1 at the run start, then call `extract` again and, for
   each page, `transform` (which updates the carry-over state) and `write` the
   laps it finished.
7. Write the final lap, from the open lap's start to the run's last time.

`transform` is still pure in that it does no I/O, but unlike other steps it
reads and updates carry-over state on `self`.

### Why `LapStep` isn't registered yet

Steps are registered by importing them in `steps/__init__.py`. `LapStep`
isn't imported there, so the pipeline never runs it. Registering it now would
make **every** pipeline job fail: its dependency `state_step` doesn't exist,
and every helper raises `NotImplementedError`.

## 15. Next steps

In order:

1. **Implement the `lap_utils` functions.** Each stub's docstring states
   exactly what it does, with the formula from this doc.
2. **Write unit tests on synthetic data**, under `services/pipeline/tests/`:
   - a circle driven 3 times gives 3 laps;
   - a straight line gives 1 lap;
   - a crossing exactly on a page boundary is found;
   - crossing the extended line outside the gate isn't counted;
   - laps have no gaps and cover every point.
3. **Add a pytest job to `BackendCI.yml`**, since these will be the first
   tests in the repo.
4. **Once `state_step` exists, import `LapStep` in `steps/__init__.py`** to
   register it.
5. **Move the constants to `Settings`.**
6. **Update the pipeline tables in `README.md` and `DevREADME.md`** with the
   `laps` output table and the step's status.
