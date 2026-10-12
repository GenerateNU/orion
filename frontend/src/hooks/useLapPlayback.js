import { useCallback, useEffect, useRef, useState } from "react";

// A play/pause clock for replaying a lap that lasts `duration` seconds.
// `elapsed` advances in real time multiplied by `speed`, and stops at the end.
export function useLapPlayback(duration, initialSpeed = 5) {
  const [elapsed, setElapsed] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(initialSpeed);
  // the animation loop reads the latest elapsed from here, not from a stale closure
  const elapsedRef = useRef(0);

  const seek = useCallback(
    (seconds) => {
      const clamped = Math.min(Math.max(seconds, 0), duration);
      elapsedRef.current = clamped;
      setElapsed(clamped);
    },
    [duration]
  );

  // a different lap starts from the beginning, paused
  useEffect(() => {
    seek(0);
    setPlaying(false);
  }, [seek]);

  useEffect(() => {
    if (!playing) return undefined;

    let frame;
    let last = performance.now();
    // timed with performance.now() rather than the frame's own timestamp, which
    // can be earlier than `last` and would step the clock backwards
    const tick = () => {
      const now = performance.now();
      const dt = Math.max(0, now - last) / 1000;
      const next = Math.min(elapsedRef.current + dt * speed, duration);
      last = now;
      elapsedRef.current = next;
      setElapsed(next);
      if (next >= duration) setPlaying(false);
      else frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, speed, duration]);

  const toggle = useCallback(() => {
    // pressing play at the finish restarts the lap
    if (!playing && elapsedRef.current >= duration) seek(0);
    setPlaying((p) => !p);
  }, [playing, duration, seek]);

  return { elapsed, playing, speed, setSpeed, toggle, seek };
}
