import { describe, expect, it } from "vitest";

import { carAt, formatLapTime, lapTimes, locate, speedKmhAt } from "./lapPlayback";

describe("lapTimes", () => {
  it("counts seconds from the first timestamp", () => {
    const times = lapTimes([
      { timestamp: "2026-05-14T12:00:00Z" },
      { timestamp: "2026-05-14T12:00:00.5Z" },
      { timestamp: "2026-05-14T12:00:02Z" },
    ]);
    expect(times).toEqual([0, 0.5, 2]);
  });

  it("falls back to 0.1 s apart without timestamps", () => {
    expect(lapTimes([{}, {}, {}])).toEqual([0, 0.1, 0.2]);
  });

  it("never goes backwards", () => {
    const times = lapTimes([
      { timestamp: "2026-05-14T12:00:01Z" },
      { timestamp: "2026-05-14T12:00:00Z" },
      { timestamp: "2026-05-14T12:00:03Z" },
    ]);
    expect(times).toEqual([0, 0, 2]);
  });
});

describe("locate / carAt", () => {
  const times = [0, 10, 20];
  const points = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }];

  it("finds the segment and how far along it the car is", () => {
    expect(locate(times, 15)).toEqual({ index: 1, frac: 0.5 });
  });

  it("clamps before the start and after the end", () => {
    expect(locate(times, -5)).toEqual({ index: 0, frac: 0 });
    expect(locate(times, 99)).toEqual({ index: 2, frac: 0 });
  });

  it("interpolates the position and points the car along the track", () => {
    expect(carAt(points, times, 5)).toMatchObject({ x: 50, y: 0, angle: 0 });
    expect(carAt(points, times, 15)).toMatchObject({ x: 100, y: 50, angle: 90 });
  });

  it("keeps the last heading at the finish", () => {
    expect(carAt(points, times, 20)).toMatchObject({ x: 100, y: 100, angle: 90 });
  });
});

describe("speedKmhAt", () => {
  it("works out speed from distance over time", () => {
    // 0.001 deg of latitude is ~111 m; covering it in 10 s is ~40 km/h
    const positions = [{ latitude: 42, longitude: -71 }, { latitude: 42.001, longitude: -71 }];
    expect(speedKmhAt(positions, [0, 10], 0)).toBeCloseTo(40, 0);
  });

  it("is null when no time passes", () => {
    expect(speedKmhAt([{ latitude: 1, longitude: 1 }], [0], 0)).toBeNull();
  });
});

describe("formatLapTime", () => {
  it("formats as m:ss.s", () => {
    expect(formatLapTime(0)).toBe("0:00.0");
    expect(formatLapTime(83.46)).toBe("1:23.4");
    expect(formatLapTime(9.95)).toBe("0:09.9");
  });
});

describe("formatLapTime with bad input", () => {
  it("never shows a negative time", () => {
    expect(formatLapTime(-0.05)).toBe("0:00.0");
  });
});
