import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useLapPlayback } from "./useLapPlayback";

describe("useLapPlayback", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
  });
  afterEach(() => vi.useRealTimers());

  it("advances at the chosen speed while playing", () => {
    const { result } = renderHook(() => useLapPlayback(100, 5));
    act(() => result.current.toggle());
    act(() => vi.advanceTimersByTime(1000));
    // 1 real second at 5x is ~5 seconds of lap
    expect(result.current.elapsed).toBeGreaterThan(4.5);
    expect(result.current.elapsed).toBeLessThan(5.5);
  });

  it("stops at the end of the lap", () => {
    const { result } = renderHook(() => useLapPlayback(2, 10));
    act(() => result.current.toggle());
    act(() => vi.advanceTimersByTime(1000));
    expect(result.current.elapsed).toBe(2);
    expect(result.current.playing).toBe(false);
  });

  it("restarts from the beginning when played at the finish", () => {
    const { result } = renderHook(() => useLapPlayback(2, 10));
    act(() => result.current.seek(2));
    act(() => result.current.toggle());
    expect(result.current.elapsed).toBe(0);
    expect(result.current.playing).toBe(true);
  });

  it("doesn't move while paused", () => {
    const { result } = renderHook(() => useLapPlayback(100, 5));
    act(() => vi.advanceTimersByTime(1000));
    expect(result.current.elapsed).toBe(0);
  });
});
