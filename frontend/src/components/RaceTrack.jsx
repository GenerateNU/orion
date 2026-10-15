import PropTypes from "prop-types";
import { useId, useMemo } from "react";

import { useLapPlayback } from "../hooks/useLapPlayback";
import { carAt, formatLapTime, lapTimes, speedKmhAt } from "../utils/lapPlayback";
import { projectPositions } from "../utils/trackProjection";

const WIDTH = 1000;
const HEIGHT = 560;
const PADDING = 80;
const SPEEDS = [1, 2, 5, 10];

const toPath = (points) =>
  points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

// Draws a lap's GPS positions as a race track -- asphalt with red/white kerbs and
// a yellow racing line -- on a stylised background instead of a real map, and
// replays the lap with a car driving it (play/pause, scrub, playback speed).
// Expects positions shaped like the /positions endpoint: [{ timestamp, latitude, longitude }].
export default function RaceTrack({ positions }) {
  // pattern ids must be unique per track on the page; useId's colons aren't safe in url(#...)
  const id = useId().replace(/:/g, "");

  // everything that depends only on the lap is worked out once, not every frame
  const { points, times, d } = useMemo(() => {
    const projected = projectPositions(positions, WIDTH, HEIGHT, PADDING);
    return { points: projected, times: lapTimes(positions), d: toPath(projected) };
  }, [positions]);
  const duration = times[times.length - 1];
  const start = points[0];
  const end = points[points.length - 1];
  // a full lap ends where it started; put END's label underneath so they don't overlap
  const endLabelY = Math.hypot(end.x - start.x, end.y - start.y) < 60 ? 38 : -22;

  const { elapsed, playing, speed, setSpeed, toggle, seek } = useLapPlayback(duration);
  const car = carAt(points, times, elapsed);
  const trail = toPath([...points.slice(0, car.index + 1), car]);
  const kmh = speedKmhAt(positions, times, car.index);

  return (
    <figure className="race-track" style={{ margin: 0 }}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Track drawn from ${positions.length} GPS points`}
      >
        <defs>
          <radialGradient id={`${id}-bg`} cx="50%" cy="45%" r="75%">
            <stop offset="0%" stopColor="#1c1c21" />
            <stop offset="100%" stopColor="#09090a" />
          </radialGradient>
          <pattern id={`${id}-grid`} width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M40 0 H0 V40" fill="none" stroke="#ffffff" strokeOpacity="0.04" />
          </pattern>
          <pattern id={`${id}-stripes`} width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(-35)">
            <rect width="14" height="28" fill="#e10600" fillOpacity="0.07" />
          </pattern>
          <pattern id={`${id}-checker`} width="8" height="8" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="#fff" />
            <rect width="4" height="4" fill="#000" />
            <rect x="4" y="4" width="4" height="4" fill="#000" />
          </pattern>
        </defs>

        {/* background: dark asphalt glow, a faint grid, and speed stripes in two corners */}
        <rect width={WIDTH} height={HEIGHT} fill={`url(#${id}-bg)`} />
        <rect width={WIDTH} height={HEIGHT} fill={`url(#${id}-grid)`} />
        <path d={`M0 0 H260 L0 220 Z`} fill={`url(#${id}-stripes)`} />
        <path d={`M${WIDTH} ${HEIGHT} H${WIDTH - 260} L${WIDTH} ${HEIGHT - 220} Z`} fill={`url(#${id}-stripes)`} />
        <rect x="0" y={HEIGHT - 10} width={WIDTH} height="10" fill={`url(#${id}-checker)`} opacity="0.5" />

        {/* the track itself, built up in layers */}
        <g fill="none" strokeLinecap="round" strokeLinejoin="round">
          <path d={d} stroke="#000" strokeOpacity="0.5" strokeWidth="44" transform="translate(0 6)" />
          <path d={d} stroke="#f4f4f5" strokeWidth="36" />
          <path d={d} stroke="#e10600" strokeWidth="36" strokeDasharray="18 18" strokeLinecap="butt" />
          <path d={d} stroke="#2a2a30" strokeWidth="27" />
          <path
            d={d}
            stroke="#ffd400"
            strokeWidth="3"
            strokeDasharray="16 12"
            data-testid="racing-line"
          />
          {/* where the car has been so far */}
          <path d={trail} stroke="#ffd400" strokeOpacity="0.25" strokeWidth="14" />
          <path d={trail} stroke="#ffd400" strokeWidth="4" data-testid="trail" />
        </g>

        {/* start: a chequered disc */}
        <g transform={`translate(${start.x} ${start.y})`} data-testid="start-marker">
          <circle r="15" fill={`url(#${id}-checker)`} stroke="#ffd400" strokeWidth="4" />
          <text y="-26" className="race-track__label" fill="#ffd400">
            START
          </text>
        </g>

        {/* end: the last recorded position */}
        <g transform={`translate(${end.x} ${end.y})`} data-testid="end-marker">
          <circle r="9" fill="#e10600" stroke="#fff" strokeWidth="3" />
          <text y={endLabelY} className="race-track__label" fill="#fff">
            END
          </text>
        </g>

        {/* the car, drawn pointing right and rotated to its heading */}
        <g
          transform={`translate(${car.x.toFixed(1)} ${car.y.toFixed(1)}) rotate(${car.angle.toFixed(1)})`}
          data-testid="car"
        >
          <circle r="24" fill="#ffd400" opacity="0.18" />
          <g fill="#0b0b0c">
            <rect x="-13" y="-12" width="8" height="5" rx="1.5" />
            <rect x="-13" y="7" width="8" height="5" rx="1.5" />
            <rect x="5" y="-12" width="8" height="5" rx="1.5" />
            <rect x="5" y="7" width="8" height="5" rx="1.5" />
            <rect x="13" y="-10" width="4" height="20" rx="1" />
            <rect x="-18" y="-9" width="4" height="18" rx="1" />
          </g>
          <rect x="-15" y="-7" width="30" height="14" rx="6" fill="#e10600" stroke="#0b0b0c" strokeWidth="1.5" />
          <rect x="-15" y="-1.6" width="30" height="3.2" fill="#ffd400" />
          <circle cx="-2" r="3.6" fill="#0b0b0c" />
        </g>

        {/* heads-up display */}
        <g transform="translate(14 14)" className="race-track__hud">
          <rect width="150" height="58" rx="8" fill="#0b0b0c" fillOpacity="0.8" stroke="#2c2c32" />
          <text x="12" y="26" className="race-track__hud-time" data-testid="lap-time">
            {formatLapTime(elapsed)}
          </text>
          <text x="12" y="46" className="race-track__hud-speed">
            {kmh === null ? "— km/h" : `${Math.round(kmh)} km/h`}
          </text>
        </g>
      </svg>

      <div className="race-track__controls">
        <button
          type="button"
          className="play-button"
          onClick={toggle}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? "❚❚" : "▶"}
        </button>
        <input
          type="range"
          className="scrubber"
          min="0"
          max={duration}
          step="0.1"
          value={elapsed}
          onChange={(e) => seek(Number(e.target.value))}
          aria-label="Lap progress"
          style={{ "--progress": `${duration ? (elapsed / duration) * 100 : 0}%` }}
        />
        <span className="race-track__clock">
          {formatLapTime(elapsed)} / {formatLapTime(duration)}
        </span>
        <div className="speed-picker" role="group" aria-label="Playback speed">
          {SPEEDS.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={speed === s}
              onClick={() => setSpeed(s)}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>

      <figcaption className="race-track__legend">
        <span className="legend-start">Start</span>
        <span className="legend-end">End</span>
        <span className="legend-car">Car</span>
        <span style={{ marginLeft: "auto" }}>{positions.length} GPS points</span>
      </figcaption>
    </figure>
  );
}

RaceTrack.propTypes = {
  positions: PropTypes.arrayOf(
    PropTypes.shape({
      timestamp: PropTypes.string,
      latitude: PropTypes.number.isRequired,
      longitude: PropTypes.number.isRequired,
    })
  ).isRequired,
};
