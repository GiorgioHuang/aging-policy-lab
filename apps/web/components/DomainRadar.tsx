// Dependency-free SVG radar ("profile") chart, rendered on the server.
//
// Compares one or more jurisdictions across the HAPI domains for the latest
// period: each axis is a domain (0 at centre, 100 at the rim), each jurisdiction
// a coloured polygon. Makes strengths/gaps legible at a glance in a way a stack
// of separate trend charts cannot.

export type RadarAxis = { key: string; label: string };
export type RadarSeries = { code: string; color: string; scores: Record<string, number | null> };

const RINGS = [25, 50, 75, 100];

export function DomainRadar({
  axes,
  series,
}: {
  axes: RadarAxis[];
  series: RadarSeries[];
}) {
  const n = axes.length;
  if (n < 3) return null; // a radar needs >= 3 axes to read as an area

  const W = 460;
  const H = 360;
  const cx = W / 2;
  const cy = H / 2 + 6;
  const R = 118;

  // axis i points at angle starting from straight up, clockwise
  const ang = (i: number) => -Math.PI / 2 + (i / n) * 2 * Math.PI;
  const at = (i: number, r: number) => ({
    x: cx + Math.cos(ang(i)) * r,
    y: cy + Math.sin(ang(i)) * r,
  });
  const poly = (pts: { x: number; y: number }[]) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ") + " Z";

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="HAPI domain profile by jurisdiction"
    >
      {/* grid rings */}
      {RINGS.map((ring) => (
        <path
          key={`ring-${ring}`}
          d={poly(axes.map((_, i) => at(i, (ring / 100) * R)))}
          fill="none"
          stroke="#222b40"
          strokeWidth="1"
        />
      ))}
      {/* spokes + axis labels */}
      {axes.map((a, i) => {
        const tip = at(i, R);
        const lab = at(i, R + 20);
        const anchor = Math.abs(lab.x - cx) < 8 ? "middle" : lab.x > cx ? "start" : "end";
        return (
          <g key={a.key}>
            <line x1={cx} y1={cy} x2={tip.x} y2={tip.y} stroke="#222b40" strokeWidth="1" />
            <text x={lab.x} y={lab.y + 3} textAnchor={anchor} className="chart-axis">
              {a.label}
            </text>
          </g>
        );
      })}
      {/* "100" rim tick on the top spoke */}
      <text x={cx} y={cy - R - 6} textAnchor="middle" className="chart-axis" opacity="0.6">
        100
      </text>

      {/* series polygons */}
      {series.map((s) => {
        const pts = axes.map((a, i) => at(i, ((s.scores[a.key] ?? 0) / 100) * R));
        return (
          <g key={s.code}>
            <path d={poly(pts)} fill={s.color} fillOpacity="0.14" stroke={s.color} strokeWidth="2" />
            {pts.map((p, i) => {
              const v = series.length && axes[i] ? s.scores[axes[i].key] : null;
              return (
                <circle key={`${s.code}-${i}`} cx={p.x} cy={p.y} r="2.8" fill={s.color}>
                  <title>
                    {s.code} · {axes[i].label}: {v == null ? "no score" : v.toFixed(1)}
                  </title>
                </circle>
              );
            })}
          </g>
        );
      })}

      {/* legend */}
      <g transform={`translate(${cx}, ${H - 6})`} className="chart-axis">
        {series.map((s, i) => {
          const span = 120;
          const x = (i - (series.length - 1) / 2) * span;
          return (
            <g key={`lg-${s.code}`} transform={`translate(${x}, 0)`}>
              <line x1="-30" y1="-3" x2="-14" y2="-3" stroke={s.color} strokeWidth="2" />
              <text x="-10" y="0">{s.code}</text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
