import { describe, expect, it } from "vitest";
import { makeTrack, startLineLaps } from "./trackmap";

// A car driving 3.5 laps of a circle (~700 m around), one fix a second, 60 s a lap.
const SECONDS_PER_LAP = 60;
const samples = SECONDS_PER_LAP * 3.5;
const latLon = Array.from({ length: samples }, (_, i): [number, number] => {
  const angle = (2 * Math.PI * i) / SECONDS_PER_LAP;
  return [42.34 + 0.001 * Math.cos(angle), -71.09 + 0.0013 * Math.sin(angle)];
});
const time = Float64Array.from({ length: samples }, (_, i) => i * 1000);

describe("laps from the START line", () => {
  it("finds one lap per crossing, leaving out the unfinished one", () => {
    const track = makeTrack(latLon, time, 0)!;
    const laps = startLineLaps(track);
    expect(laps.map((lap) => lap.id)).toEqual([1, 2, 3]);
    for (const lap of laps) {
      expect((lap.window[1] - lap.window[0]) / 1000).toBeCloseTo(SECONDS_PER_LAP, 0);
    }
    expect(laps[0].window[0]).toBe(0);
  });

  it("finds none when the car never comes back to START", () => {
    const track = makeTrack(latLon.slice(0, 40), time.slice(0, 40), 0)!;
    expect(startLineLaps(track)).toEqual([]);
  });
});
