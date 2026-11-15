# Ideal lap

## What it is

Lap comparison graphs should use "% of lap completed" on the X axis instead of
time. For that, every lap needs to be measured with the same ruler: one lap
that defines 0% to 100%. Then 40% is the same spot on the track on every lap,
no matter how fast the lap was.

That ruler is the **ideal lap**. Each run gets its own, picked from that run's
laps.

## How it's picked

1. Skip the **first and last laps**. They start or end wherever the run does
   (like the pits), not at the start/finish line.
2. Skip laps with **missing data** (a gap longer than 1 s).
3. Skip laps that are really **two or more laps stuck together**: anything
   longer than 1.25× the shortest lap. This happens when lap detection misses
   a crossing of the start/finish line.
4. Of what's left, take the lap with the **middle lap time** (the median).

The chosen lap is redrawn with a point every 1 m, from 0% at the start/finish
line to just under 100% back at it.

## Runs with only 1 or 2 laps

Every lap is a first or last lap, so step 1 leaves nothing. Instead:

1. Draw a wide finish line across the track (15 m each side) at the
   start/finish.
2. Each time the car crosses it, that's one trip around the track.
3. Pick a trip with the same rules: no missing data, not doubled up, middle
   lap time.

This doesn't change the laps list. It's only used to pick the ruler.

## Why the median lap

- It's a real lap the car actually drove.
- It's simple to explain and check, and needs no new libraries.
- Averaging laps together was ruled out: laps take different lines and speeds,
  so averaging blurs the corners.

The ruler doesn't need to be perfect, just the same for every lap.

## Example

Run `3adaad41` has 15 laps. After skipping the end laps, the gappy laps and
the doubled-up laps, laps 3, 6, 10 and 14 are left. The middle lap time is
lap 10's (42 s), so lap 10 is the ideal lap.

## Limitations

- The median looks at lap time, not the path. A lap with a normal time but an
  odd line could be picked.
- If the car never crosses the start/finish line twice, there's no ideal lap.
- The numbers (1 s, 1.25×, 1 m, 15 m) are starting guesses, not tuned yet.

## Code

`services/pipeline/src/orion_pipeline/steps/lap_progress_step/ideal_lap.py`,
tested in `services/pipeline/tests/test_ideal_lap.py`.
