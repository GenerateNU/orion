import { describe, expect, it } from "vitest";
import type { Track } from "@features/dashboard/utils/trackmap";
import { clampHalf, lapHalfM, selectionWindow } from "./useTrackSelection";

// 10 s of driving at 10 m/s: 100 m, a sample every second.
const track: Track = {
  time: Float64Array.from({ length: 11 }, (_, i) => i * 1000),
  startMs: 0,
  xs: new Float32Array(11),
  ys: new Float32Array(11),
  dist: Float64Array.from({ length: 11 }, (_, i) => i * 10),
  totalM: 100,
  firstTime: 0,
  lastTime: 10_000,
  viewSize: { width: 100, height: 100 },
};

// A 40 m lap, then a 60 m one.
const laps = [
  { id: 1, window: [0, 4000] as const },
  { id: 2, window: [4000, 10_000] as const },
];

describe("track window length", () => {
  it("is capped at one lap: half a typical (median) lap each side of the car", () => {
    const maxHalfM = lapHalfM(track, laps);
    expect(maxHalfM).toBe(30);
    expect(clampHalf(track, 45, maxHalfM)).toBe(30);
    expect(clampHalf(track, 20, maxHalfM)).toBe(20);
  });

  it("stays inside the car's lap: an end that would cross START is cut off there", () => {
    // Car at 30 m (3 s) on lap 1, 20 m each side: 10 m to 50 m, but lap 1 ends at 40 m.
    expect(selectionWindow(track, { center: 3000, halfM: 20 }, laps)).toEqual([1000, 4000]);
    // Without laps, only the run's ends limit it.
    expect(selectionWindow(track, { center: 3000, halfM: 20 })).toEqual([1000, 5000]);
  });

  it("falls back to half the run when there are no laps", () => {
    expect(lapHalfM(track, [])).toBe(Infinity);
    expect(lapHalfM(track, undefined)).toBe(Infinity);
    expect(clampHalf(track, 80, lapHalfM(track, undefined))).toBe(50);
  });
});
