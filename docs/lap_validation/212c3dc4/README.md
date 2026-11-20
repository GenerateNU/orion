# Run `212c3dc4-7c56-4836-b451-eb33d824a075`

| | |
|---|---|
| When | 23:12:02 → 23:38:19 (1,577 s) |
| Data | 52,115 estimated positions (33 Hz average) |
| Layout | Small loop, about 60 m × 100 m, ~20 s laps |
| Idle and stops | No positions logged for 1,034 s (from 102 s in). The car was stopped for 151 s inside lap 4. Telemetry dropped out for 3–5 s at a time in the last 30 s. |
| Result | **7 of 14 laps detected before the fix; 14 of 14 after** |

## After: 30 m gate

The gate isn't at the run's first point. The car starts off the loop at (0, 0)
and joins it, so the first revisit, and therefore the gate, is on the loop at
about (9, −3) m. That is correct. The pass 2.4 s into the run is the car joining
the loop. It falls under the 10 s minimum lap time, so it is dropped, as it
should be. Every other pass is counted, and the re-run matches the stored `laps`
table.

The "10 m gate" column below was reconstructed by recounting crossings with a 5 m half-width on the same
positions and the same gate.

## True vs detected laps

| True lap | Start → end | Duration | 10 m gate | 30 m gate |
|---|---|---|---|---|
| 1 | 23:12:02 → 23:31:02 | 1,139.7 s (1,034 s idle, 67 s stopped) | lap 1 | lap 1 ✅ |
| 2 | 23:31:02 → 23:31:23 | 21.5 s | lap 2 | lap 2 ✅ |
| 3 | 23:31:23 → 23:31:45 | 21.5 s | merged into lap 3 | lap 3 ✅ |
| 4 | 23:31:45 → 23:34:51 | 186.0 s (151 s stopped) | merged into lap 3 | lap 4 ✅ |
| 5 | 23:34:51 → 23:35:11 | 20.4 s | merged into lap 3 | lap 5 ✅ |
| 6 | 23:35:11 → 23:35:33 | 22.3 s | merged into lap 4 | lap 6 ✅ |
| 7 | 23:35:33 → 23:35:53 | 19.4 s | merged into lap 4 | lap 7 ✅ |
| 8 | 23:35:53 → 23:36:14 | 21.2 s | merged into lap 4 | lap 8 ✅ |
| 9 | 23:36:14 → 23:36:33 | 18.9 s | merged into lap 4 | lap 9 ✅ |
| 10 | 23:36:33 → 23:36:55 | 22.3 s | merged into lap 5 | lap 10 ✅ |
| 11 | 23:36:55 → 23:37:15 | 20.2 s | merged into lap 5 | lap 11 ✅ |
| 12 | 23:37:15 → 23:37:34 | 18.6 s | merged into lap 6 | lap 12 ✅ |
| 13 | 23:37:34 → 23:37:55 | 21.3 s (3 s dropout) | merged into lap 6 | lap 13 ✅ |
| 14 | 23:37:55 → 23:38:19 | 23.3 s (18 s of dropouts, run ends) | lap 7 | lap 14 ✅ |

## Mismatches and causes

| Mismatch | Cause | Status |
|---|---|---|
| 7 missed boundaries (true laps 3–5, 6–9, 10–11 and 12–13 merged) | Same as run 80a58216: the 10 m gate was shorter than the spread of lines through the start/finish | **Fixed** by the same 5 m → 15 m half-width change |
| Laps 1 and 4 last 1,140 s and 186 s | Idle time (lap 1) and a 151 s stop (lap 4) inside the lap | **Accepted:** the boundaries are correct |
| Lap 14 is mostly dropouts | Telemetry dropped out repeatedly as the run ended. It is the last, partial lap. | **Accepted** |

## Gate width sweep

This run is what confirms 15 m, not just the 12.5 m that was enough for run
80a58216.

Raw crossings include the pass 2.4 s into the run, which is always dropped.

| Half-width | Raw crossings | Laps (of 14) |
|---|---|---|
| 5 m | 7 | 7 |
| 7.5 m | 11 | 11 |
| 10 m – 12.5 m | 13 | 13: true laps 12–13 still merged |
| **15 m – 25 m** | **14** | **14** ✅ |
| 30 m | 15 | 14: one extra pass, dropped by the minimum lap time |

At a 30 m half-width (a 60 m gate), the gate starts catching an extra pass, which
only the minimum lap time removes. That is the first sign of the wide-gate risk
of catching another part of the track. 15 m sits inside the range where the
count is right.
