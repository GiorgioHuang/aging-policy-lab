// Dependency-free SVG trend chart (renders on the server; native <title>
// tooltips on hover). Kept simple on purpose — the data series are short.

export type ChartPoint = { label: string; value: number };

const COLORS: Record<string, string> = {
  higher_is_better: "#3ecf8e",
  lower_is_better: "#e0a23b",
  neutral: "#4f9dff",
};

function fmtVal(v: number): string {
  return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function TrendChart({
  points,
  direction,
  unit,
}: {
  points: ChartPoint[];
  direction?: string | null;
  unit?: string | null;
}) {
  if (points.length === 0) return null;

  const W = 560;
  const H = 150;
  const padL = 10;
  const padR = 48; // room for the trailing value label
  const padT = 14;
  const padB = 22;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const values = points.map((p) => p.value);
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    // flat series: pad so the line sits mid-height
    const d = Math.abs(min) || 1;
    min -= d * 0.05;
    max += d * 0.05;
  }

  const x = (i: number) =>
    padL + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW);
  const y = (v: number) => padT + innerH - ((v - min) / (max - min)) * innerH;

  const color = COLORS[direction ?? "neutral"] ?? COLORS.neutral;
  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`)
    .join(" ");
  const areaPath =
    `${linePath} L${x(points.length - 1).toFixed(1)},${(padT + innerH).toFixed(1)} ` +
    `L${x(0).toFixed(1)},${(padT + innerH).toFixed(1)} Z`;

  const last = points[points.length - 1];
  const gradId = `g-${Math.round(min)}-${Math.round(max)}-${points.length}`;

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Trend from ${points[0].label} to ${last.label}`}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* baseline */}
      <line
        x1={padL}
        y1={padT + innerH}
        x2={padL + innerW}
        y2={padT + innerH}
        stroke="#27314a"
        strokeWidth="1"
      />

      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="2" />

      {points.map((p, i) => (
        <circle key={`${p.label}-${i}`} cx={x(i)} cy={y(p.value)} r="3" fill={color}>
          <title>
            {p.label}: {fmtVal(p.value)}
            {unit ? ` ${unit}` : ""}
          </title>
        </circle>
      ))}

      {/* y-axis min/max */}
      <text x={padL} y={padT - 3} className="chart-axis">
        {fmtVal(max)}
      </text>
      <text x={padL} y={padT + innerH + 14} className="chart-axis">
        {fmtVal(min)}
      </text>

      {/* x-axis first/last labels */}
      <text x={padL} y={H - 4} className="chart-axis">
        {points[0].label}
      </text>
      {points.length > 1 && (
        <text x={padL + innerW} y={H - 4} textAnchor="end" className="chart-axis">
          {last.label}
        </text>
      )}

      {/* trailing value */}
      <text
        x={x(points.length - 1) + 6}
        y={y(last.value) + 4}
        className="chart-last"
        fill={color}
      >
        {fmtVal(last.value)}
      </text>
    </svg>
  );
}
