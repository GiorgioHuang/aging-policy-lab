/**
 * Brand mark for the Canadian Healthy Aging Policy Observatory.
 *
 * The emblem fuses the three things the platform actually does:
 *   - concentric observatory / radar rings (continuous monitoring) that also
 *     read as tree-growth "age rings" and echo the HAPI radar chart;
 *   - a rising green sprout through them (healthy aging, vitality);
 *   - a bright node at the tip (an observed data point).
 *
 * Dependency-free, inline SVG — scales cleanly from a 16px favicon to a hero.
 * Colors are pulled from the site palette (accent #4f9dff, health #3ecf8e).
 */
export function LogoMark({
  size = 22,
  title = "Healthy Aging Policy Observatory",
}: {
  size?: number;
  title?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label={title}
    >
      <defs>
        <linearGradient
          id="hapiRing"
          x1="10"
          y1="8"
          x2="54"
          y2="58"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#4f9dff" />
          <stop offset="1" stopColor="#7cc4ff" />
        </linearGradient>
        <linearGradient
          id="hapiLeaf"
          x1="24"
          y1="46"
          x2="40"
          y2="16"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#3ecf8e" />
          <stop offset="1" stopColor="#79e9b6" />
        </linearGradient>
      </defs>
      {/* observatory tick ring (dashed = instrument bezel) */}
      <circle
        cx="32"
        cy="32"
        r="29"
        stroke="#4f9dff"
        strokeOpacity="0.32"
        strokeWidth="2.4"
        strokeDasharray="1.6 7"
        strokeLinecap="round"
      />
      {/* concentric radar / age rings */}
      <circle cx="32" cy="32" r="23.5" stroke="url(#hapiRing)" strokeWidth="2" />
      <circle
        cx="32"
        cy="32"
        r="15.5"
        stroke="url(#hapiRing)"
        strokeOpacity="0.45"
        strokeWidth="2"
      />
      {/* rising sprout = healthy aging / growth */}
      <path
        d="M32 45 C 32 38 32 31 32 21"
        stroke="url(#hapiLeaf)"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
      <ellipse
        cx="27.4"
        cy="30"
        rx="3"
        ry="6.2"
        transform="rotate(-42 27.4 30)"
        fill="url(#hapiLeaf)"
        fillOpacity="0.92"
      />
      <ellipse
        cx="36.6"
        cy="27.4"
        rx="3"
        ry="6.2"
        transform="rotate(42 36.6 27.4)"
        fill="url(#hapiLeaf)"
        fillOpacity="0.92"
      />
      {/* bright observed node at the tip */}
      <circle cx="32" cy="20" r="5" fill="#3ecf8e" fillOpacity="0.18" />
      <circle cx="32" cy="20" r="3" fill="#79e9b6" />
    </svg>
  );
}
