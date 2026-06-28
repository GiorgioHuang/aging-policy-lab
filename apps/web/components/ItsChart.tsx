// Dependency-free SVG segmented-regression (ITS) chart, rendered on the server.
//
// Draws the canonical interrupted-time-series picture: the observed series, a
// vertical marker at the intervention, the fitted pre- and post-intervention
// trend segments, and a dashed counterfactual — the pre-trend projected forward
// as if the intervention had never happened. The gap between the post-segment
// and the counterfactual IS the estimated effect (level change + slope change).

import type { ChartPoint } from "./TrendChart";

export type ItsTerm = { coef: number; ci_low: number; ci_high: number; p: number };

export type ItsModel = {
  intercept?: ItsTerm;
  pre_trend: ItsTerm;
  level_change: ItsTerm;
  slope_change: ItsTerm;
  n_pre: number;
  n_post: number;
};

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const full = new Intl.NumberFormat("en", { maximumFractionDigits: 1 });

export function ItsChart({
  points,
  model,
  interventionLabel,
}: {
  points: ChartPoint[];
  model: ItsModel;
  interventionLabel?: string | null;
}) {
  const n = points.length;
  const t0 = model.n_pre; // index of the first post-intervention point
  // Need the intercept to reconstruct the fitted lines; without it (older
  // findings computed before we stored it) fall back gracefully.
  if (n < 2 || model.intercept == null || t0 < 1 || t0 >= n) return null;

  const b0 = model.intercept.coef;
  const b1 = model.pre_trend.coef;
  const b2 = model.level_change.coef;
  const b3 = model.slope_change.coef;

  // Fitted value of the segmented model at integer index i.
  const fit = (i: number) =>
    i < t0 ? b0 + b1 * i : b0 + b1 * i + b2 + b3 * (i - t0 + 1);
  // Counterfactual: pre-trend projected across the whole horizon.
  const cf = (i: number) => b0 + b1 * i;

  const W = 560;
  const H = 200;
  const gutterL = 50;
  const padR = 14;
  const padT = 16;
  const padB = 40; // x labels + legend room
  const plotW = W - gutterL - padR;
  const plotH = H - padT - padB;
  const x0 = gutterL;
  const y0 = padT;

  // y-domain spans observed values AND the fitted/counterfactual extremes.
  const ys = [
    ...points.map((p) => p.value),
    fit(0),
    fit(n - 1),
    cf(n - 1),
  ];
  let min = Math.min(...ys);
  let max = Math.max(...ys);
  if (min === max) {
    const d = Math.abs(min) || 1;
    min -= d * 0.05;
    max += d * 0.05;
  } else {
    const pad = (max - min) * 0.08;
    min -= pad;
    max += pad;
  }

  const x = (i: number) => x0 + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
  const y = (v: number) => y0 + plotH - ((v - min) / (max - min)) * plotH;

  // Intervention boundary sits between the last pre and first post point.
  const xCut = x0 + ((t0 - 0.5) / (n - 1)) * plotW;

  const observedPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`)
    .join(" ");
  const preFit = `M${x(0).toFixed(1)},${y(fit(0)).toFixed(1)} L${x(t0 - 1).toFixed(1)},${y(fit(t0 - 1)).toFixed(1)}`;
  const postFit = `M${x(t0).toFixed(1)},${y(fit(t0)).toFixed(1)} L${x(n - 1).toFixed(1)},${y(fit(n - 1)).toFixed(1)}`;
  // Counterfactual continues the pre-trend from the last pre point onward.
  const cfPath = `M${x(t0 - 1).toFixed(1)},${y(cf(t0 - 1)).toFixed(1)} L${x(n - 1).toFixed(1)},${y(cf(n - 1)).toFixed(1)}`;

  const yTicks = [max, (max + min) / 2, min];
  const maxLabels = 6;
  const step = Math.max(1, Math.ceil(n / maxLabels));
  const labelIdx: number[] = [];
  for (let i = 0; i < n; i += step) labelIdx.push(i);
  if (labelIdx[labelIdx.length - 1] !== n - 1) labelIdx.push(n - 1);

  const OBS = "#4f9dff";
  const FIT = "#3ecf8e";
  const CF = "#e0a23b";

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Interrupted time series around ${interventionLabel ?? "the intervention"}`}
    >
      {/* y gridlines + ticks */}
      {yTicks.map((v, i) => (
        <g key={`yt-${i}`}>
          <line x1={x0} y1={y(v)} x2={x0 + plotW} y2={y(v)} stroke="#222b40" strokeWidth="1" />
          <text x={x0 - 8} y={y(v) + 3.5} textAnchor="end" className="chart-axis">
            {compact.format(v)}
          </text>
        </g>
      ))}

      {/* intervention marker */}
      <line x1={xCut} y1={y0} x2={xCut} y2={y0 + plotH} stroke="#8a93a6" strokeWidth="1" strokeDasharray="3 3" />
      <text x={xCut} y={y0 - 4} textAnchor="middle" className="chart-axis" fill="#8a93a6">
        {interventionLabel ?? "intervention"}
      </text>

      {/* counterfactual (pre-trend projected) */}
      <path d={cfPath} fill="none" stroke={CF} strokeWidth="1.5" strokeDasharray="4 3" opacity="0.9" />
      {/* fitted segments */}
      <path d={preFit} fill="none" stroke={FIT} strokeWidth="2" />
      <path d={postFit} fill="none" stroke={FIT} strokeWidth="2" />
      {/* observed */}
      <path d={observedPath} fill="none" stroke={OBS} strokeWidth="1.5" opacity="0.85" />
      {points.map((p, i) => (
        <circle key={`${p.label}-${i}`} cx={x(i)} cy={y(p.value)} r="2.6" fill={OBS}>
          <title>
            {p.label}: {full.format(p.value)}
          </title>
        </circle>
      ))}

      {/* x labels */}
      {labelIdx.map((i) => {
        const anchor = i === 0 ? "start" : i === n - 1 ? "end" : "middle";
        return (
          <text key={`xl-${i}`} x={x(i)} y={y0 + plotH + 16} textAnchor={anchor} className="chart-axis">
            {points[i].label}
          </text>
        );
      })}

      {/* legend */}
      <g transform={`translate(${x0}, ${H - 8})`} className="chart-axis">
        <line x1="0" y1="-3" x2="16" y2="-3" stroke={OBS} strokeWidth="1.5" />
        <text x="20" y="0">observed</text>
        <line x1="86" y1="-3" x2="102" y2="-3" stroke={FIT} strokeWidth="2" />
        <text x="106" y="0">fitted</text>
        <line x1="150" y1="-3" x2="166" y2="-3" stroke={CF} strokeWidth="1.5" strokeDasharray="4 3" />
        <text x="170" y="0">counterfactual</text>
      </g>
    </svg>
  );
}
