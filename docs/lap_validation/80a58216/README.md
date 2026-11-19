# Run `80a58216-3dae-4c3d-ac69-f4afff3f928f`

| | |
|---|---|
| When | 2026-08-15, 17:13:43 → 17:48:15 (2,072 s) |
| Data | 72,305 estimated positions |
| Layout | Single loop, about 140 m × 185 m, ~45 s laps |
| Idle | Car idle with no positions logged for 469 s (from 73 s in) and 880 s (from 881 s in) |
| Result | **4 of 9 laps detected before the fix; 9 of 9 after** |

## Before: 10 m gate

The gate was placed correctly, at the run's first point on the start/finish
straight, but it was only 10 m long. The car's line through the start/finish
spread across about 20 m of track from lap to lap, roughly 5 m west to 15 m east
of the gate center. Most passes went beside the gate, so only 3 of 8 crossings
were counted and neighboring laps were merged.

## After: 30 m gate

With the wider gate, every pass is counted. The re-run gate's boundaries match
the stored `laps` table exactly.

## True vs detected laps

| True lap | Start → end | Duration | 10 m gate | 30 m gate |
|---|---|---|---|---|
| 1 | 17:13:43 → 17:22:46 | 543.0 s (469 s idle) | lap 1 | lap 1 ✅ |
| 2 | 17:22:46 → 17:23:33 | 46.8 s | merged into lap 2 | lap 2 ✅ |
| 3 | 17:23:33 → 17:43:05 | 1,172.5 s (880 s idle) | merged into lap 2 | lap 3 ✅ |
| 4 | 17:43:05 → 17:43:51 | 45.4 s | merged into lap 3 | lap 4 ✅ |
| 5 | 17:43:51 → 17:44:35 | 44.4 s | merged into lap 3 | lap 5 ✅ |
| 6 | 17:44:35 → 17:45:52 | 77.0 s | merged into lap 3 | lap 6 ✅ |
| 7 | 17:45:52 → 17:46:39 | 46.6 s | merged into lap 4 | lap 7 ✅ |
| 8 | 17:46:39 → 17:47:23 | 44.5 s | merged into lap 4 | lap 8 ✅ |
| 9 | 17:47:23 → 17:48:15 | 51.8 s (run ends) | merged into lap 4 | lap 9 ✅ |

## Mismatches and causes

| Mismatch | Cause | Status |
|---|---|---|
| 5 missed boundaries (true laps 2–3, 4–6 and 7–9 merged) | The 10 m gate covered only part of the ~20 m spread of lines | **Fixed:** the gate half-width went from 5 m to 15 m |
| Laps 1 and 3 last 543 s and 1,172 s | The car sat idle for 469 s and 880 s inside them | **Accepted:** the boundaries are correct |

No extra laps were detected, and the gate was in the right place.

- **Gate width sweep** (crossings counted out of 8):

  | Half-width | Crossings counted |
  |---|---|
  | 5 m | 3 |
  | 7.5 m | 5 |
  | 10 m | 6 |
  | 12.5 m – 30 m | 8 |

- **Lap 6** (77 s) is about 30 s slower than the other full laps. Its boundaries
  were checked on the path, so it is a slow lap, not a merged one.
