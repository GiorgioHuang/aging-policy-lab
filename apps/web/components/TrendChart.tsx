// Dependency-free SVG trend chart (renders on the server; native <title>
// tooltips on hover). Proper left gutter for the y-axis, compact y ticks, and
// evenly-spaced x labels that never overlap.

export type ChartPoint = { label: string; value: number };

const COLORS: Record<string, string> = {
  higher_is_better: "#3ecf8e",
  lower_is_better: "#e0a23b",
  neutral: "#4f9dff",
};

const compact = new Intl.NumberFormat("en", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const full = new Intl.NumberFormat("en", { maximumFractionDigits: 1 });

export function TrendChart({
  points,
  direction,
  unit,
  yMin,
  yMax,
}: {
  points: ChartPoint[];
  direction?: string | null;
  unit?: string | null;
  yMin?: number;
  yMax?: number;
}) {
  if (points.length === 0) return null;

  const W = 560;
  const H = 172;
  const gutterL = 50; // y-axis labels
  const padR = 14;
  const padT = 14;
  const padB = 26; // x-axis labels
  const plotW = W - gutterL - padR;
  const plotH = H - padT - padB;
  const x0 = gutterL;
  const y0 = padT;

  const values = points.map((p) => p.value);
  let min = yMin ?? Math.min(...values);
  let max = yMax ?? Math.max(...values);
  if (min === max) {
    const d = Math.abs(min) || 1;
    min -= d * 0.05;
    max += d * 0.05;
  }

  const n = points.length;
  const x = (i: number) => x0 + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
  const y = (v: number) => y0 + plotH - ((v - min) / (max - min)) * plotH;

  const color = COLORS[direction ?? "neutral"] ?? COLORS.neutral;
  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`)
    .join(" ");
  const areaPath =
    `${linePath} L${x(n - 1).toFixed(1)},${(y0 + plotH).toFixed(1)} ` +
    `L${x(0).toFixed(1)},${(y0 + plotH).toFixed(1)} Z`;
  const gradId = `g${Math.round(min)}-${Math.round(max)}-${n}`;

  // y ticks: top, middle, bottom
  const yTicks = [max, (max + min) / 2, min];

  // x labels: first, last, and a few evenly spaced in between (max ~6, no overlap)
  const maxLabels = 6;
  const step = Math.max(1, Math.ceil(n / maxLabels));
  const labelIdx: number[] = [];
  for (let i = 0; i < n; i += step) labelIdx.push(i);
  if (labelIdx[labelIdx.length - 1] !== n - 1) labelIdx.push(n - 1);

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Trend from ${points[0].label} to ${points[n - 1].label}`}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.26" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* y gridlines + tick labels */}
      {yTicks.map((v, i) => (
        <g key={`yt-${i}`}>
          <line
            x1={x0}
            y1={y(v)}
            x2={x0 + plotW}
            y2={y(v)}
            stroke="#222b40"
            strokeWidth="1"
          />
          <text x={x0 - 8} y={y(v) + 3.5} textAnchor="end" className="chart-axis">
            {compact.format(v)}
          </text>
        </g>
      ))}

      {/* area + line */}
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="2" />

      {/* points with hover tooltips */}
      {points.map((p, i) => (
        <circle key={`${p.label}-${i}`} cx={x(i)} cy={y(p.value)} r="3" fill={color}>
          <title>
            {p.label}: {full.format(p.value)}
            {unit ? ` ${unit}` : ""}
          </title>
        </circle>
      ))}

      {/* x labels */}
      {labelIdx.map((i) => {
        const anchor = i === 0 ? "start" : i === n - 1 ? "end" : "middle";
        return (
          <text key={`xl-${i}`} x={x(i)} y={H - 8} textAnchor={anchor} className="chart-axis">
            {points[i].label}
          </text>
        );
      })}
    </svg>
  );
}
