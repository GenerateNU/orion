import PropTypes from "prop-types";

// The team husky in a yellow badge with a red ring. Drawn here (not a copy of
// any official logo) so it scales cleanly and needs no image file.
// With no title it's decorative and hidden from screen readers.
export default function Husky({ className, title }) {
  const a11y = title ? { role: "img", "aria-label": title } : { "aria-hidden": true };
  return (
    <svg className={className} viewBox="0 0 64 64" {...a11y}>
      <circle cx="32" cy="32" r="30" fill="var(--yellow, #ffd400)" />
      <circle cx="32" cy="32" r="30" fill="none" stroke="var(--red, #e10600)" strokeWidth="3" />

      {/* ears */}
      <path d="M13 29 L19 6 L30 20 Z" fill="#2b2b31" />
      <path d="M51 29 L45 6 L34 20 Z" fill="#2b2b31" />
      <path d="M17 24 L20 12 L26 20 Z" fill="var(--red, #e10600)" />
      <path d="M47 24 L44 12 L38 20 Z" fill="var(--red, #e10600)" />

      {/* head */}
      <path
        d="M32 15 C46 15 53 26 53 38 C53 50 44 57 32 59 C20 57 11 50 11 38 C11 26 18 15 32 15 Z"
        fill="#2b2b31"
      />
      {/* white mask: forehead stripe, cheeks and muzzle */}
      <path
        d="M32 21 C30.5 27 27 29.5 22.5 31.5 C16.5 34 14.5 40 16.5 46 C19 53.5 26 57.5 32 57.5
           C38 57.5 45 53.5 47.5 46 C49.5 40 47.5 34 41.5 31.5 C37 29.5 33.5 27 32 21 Z"
        fill="#f4f4f5"
      />

      {/* eyes */}
      <ellipse cx="24.5" cy="38" rx="3.4" ry="3" fill="#2b2b31" />
      <ellipse cx="39.5" cy="38" rx="3.4" ry="3" fill="#2b2b31" />
      <circle cx="24.5" cy="38" r="2" fill="#5ab4ff" />
      <circle cx="39.5" cy="38" r="2" fill="#5ab4ff" />
      <circle cx="24.5" cy="38" r="0.9" fill="#0b0b0c" />
      <circle cx="39.5" cy="38" r="0.9" fill="#0b0b0c" />

      {/* nose and mouth */}
      <path d="M28 46 Q32 44 36 46 Q34.5 50 32 50 Q29.5 50 28 46 Z" fill="#0b0b0c" />
      <path
        d="M32 50 V53 M32 53 Q29.5 55.5 27 53.5 M32 53 Q34.5 55.5 37 53.5"
        fill="none"
        stroke="#0b0b0c"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

Husky.propTypes = {
  className: PropTypes.string,
  title: PropTypes.string,
};
