// Dependency-free SVG timeline strip, rendered on the server.
//
// Plots every policy as a dot on a shared year axis, coloured by jurisdiction —
// a one-glance view of when aging policy clustered (and where the gaps are)
// across the whole 1952→present span. Dots in the same year stack vertically.

export type TimelineItem = {
  id: string;
  year: number;
  title: string;
  jurisdiction: string;
};

const JUR_COLORS: Record<string, string> = {
  "CA-FED": "#4f9dff",
  "CA-NS": "#3ecf8e",
};
const fallbackColor = "#e0a23b";

export function PolicyTimeline({ items }: { items: TimelineItem[] }) {
  const pts = items.filter((d) => Number.isFinite(d.year));
  if (pts.length < 2) return null;

  const W = 720;
  const padL = 16;
  const padR = 16;
  const axisY = 150;
  const plotW = W - padL - padR;

  const years = pts.map((d) => d.year);
  let minY = Math.min(...years);
  let maxY = Math.max(...years);
  // round outward to tidy decade-ish bounds
  minY = Math.floor(minY / 5) * 5;
  maxY = Math.ceil(maxY / 5) * 5;
  const span = maxY - minY || 1;
  const x = (yr: number) => padL + ((yr - minY) / span) * plotW;

  // stack dots that share a year so they don't overlap
  const counts = new Map<number, number>();
  const placed = pts
    .slice()
    .sort((a, b) => a.year - b.year)
    .map((d) => {
      const k = counts.get(d.year) ?? 0;
      counts.set(d.year, k + 1);
      return { ...d, stack: k };
    });

  // decade gridlines/labels
  const firstDecade = Math.ceil(minY / 10) * 10;
  const decades: number[] = [];
  for (let y = firstDecade; y <= maxY; y += 10) decades.push(y);

  const jurs = [...new Set(pts.map((d) => d.jurisdiction))];
  const colorFor = (j: string) => JUR_COLORS[j] ?? fallbackColor;

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} 196`}
      role="img"
      aria-label={`Policy timeline ${minY}–${maxY}`}
    >
      {/* decade gridlines */}
      {decades.map((y) => (
        <g key={`dec-${y}`}>
          <line x1={x(y)} y1={20} x2={x(y)} y2={axisY} stroke="#1b2335" strokeWidth="1" />
          <text x={x(y)} y={axisY + 16} textAnchor="middle" className="chart-axis">
            {y}
          </text>
        </g>
      ))}

      {/* axis baseline */}
      <line x1={padL} y1={axisY} x2={W - padR} y2={axisY} stroke="#2c3650" strokeWidth="1.5" />

      {/* policy dots (stacked upward from the axis) */}
      {placed.map((d) => {
        const cyDot = axisY - 10 - d.stack * 12;
        const c = colorFor(d.jurisdiction);
        return (
          <g key={d.id}>
            <line x1={x(d.year)} y1={axisY} x2={x(d.year)} y2={cyDot} stroke={c} strokeWidth="1" opacity="0.35" />
            <circle cx={x(d.year)} cy={cyDot} r="4" fill={c} fillOpacity="0.9">
              <title>
                {d.year} · {d.jurisdiction}: {d.title}
              </title>
            </circle>
          </g>
        );
      })}

      {/* legend */}
      <g transform={`translate(${padL}, 184)`} className="chart-axis">
        {jurs.map((j, i) => (
          <g key={j} transform={`translate(${i * 92}, 0)`}>
            <circle cx="4" cy="-3" r="4" fill={colorFor(j)} />
            <text x="14" y="0">{j}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}
