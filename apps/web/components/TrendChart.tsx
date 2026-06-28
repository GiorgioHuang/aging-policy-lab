"use client";

// Interactive dependency-free SVG trend chart. Renders on the server and
// hydrates on the client: hovering snaps a crosshair to the nearest point and
// shows a tooltip. Proper left gutter for the y-axis, compact y ticks, and
// evenly-spaced x labels that never overlap.

import { useState, type MouseEvent } from "react";
import { useTip, TipLayer } from "./chart-ui";

export type ChartPoint = { label: string; value: number };
// A dated policy event to overlay as a vertical marker. `t` is a numeric year
// (fractional allowed, e.g. 2022.5 for mid-year); `title` shows on hover.
export type ChartEvent = { t: number; label: string; title?: string };

const EVENT_COLOR = "#a78bfa";

function labelToTime(label: string): number {
  const m = label.match(/^(\d{4})(?:-(\d{2}))?/);
  if (!m) return NaN;
  return Number(m[1]) + (m[2] ? (Number(m[2]) - 1) / 12 : 0);
}

const COLORS: Record<string, string> = {
  higher_is_better: "#3ecf8e",
  lower_is_better: "#e0a23b",
  neutral: "#4f9dff",
};

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const full = new Intl.NumberFormat("en", { maximumFractionDigits: 1 });

export function TrendChart({
  points,
  direction,
  unit,
  yMin,
  yMax,
  events,
}: {
  points: ChartPoint[];
  direction?: string | null;
  unit?: string | null;
  yMin?: number;
  yMax?: number;
  events?: ChartEvent[];
}) {
  const { ref, tip, move, clear } = useTip();
  const [active, setActive] = useState<number | null>(null);
  if (points.length === 0) return null;

  const W = 560;
  const H = 172;
  const gutterL = 50;
  const padR = 14;
  const padT = 14;
  const padB = 26;
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
  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const areaPath =
    `${linePath} L${x(n - 1).toFixed(1)},${(y0 + plotH).toFixed(1)} ` + `L${x(0).toFixed(1)},${(y0 + plotH).toFixed(1)} Z`;
  const gradId = `g${Math.round(min)}-${Math.round(max)}-${n}`;

  const yTicks = [max, (max + min) / 2, min];
  const maxLabels = 6;
  const step = Math.max(1, Math.ceil(n / maxLabels));
  const labelIdx: number[] = [];
  for (let i = 0; i < n; i += step) labelIdx.push(i);
  if (labelIdx[labelIdx.length - 1] !== n - 1) labelIdx.push(n - 1);

  // Position policy events by interpolating their year against the series times,
  // so a marker lands where the data says it should even on irregular cadences.
  const times = points.map((p) => labelToTime(p.label));
  function eventX(t: number): number | null {
    if (n === 0 || Number.isNaN(t) || t < times[0] || t > times[n - 1]) return null;
    for (let i = 0; i < n - 1; i++) {
      const a = times[i];
      const b = times[i + 1];
      if (t >= a && t <= b) return x(b === a ? i : i + (t - a) / (b - a));
    }
    return x(n - 1);
  }
  const evs = (events ?? [])
    .map((e) => ({ ...e, ex: eventX(e.t) }))
    .filter((e): e is ChartEvent & { ex: number } => e.ex != null);

  // Map a pointer x (in viewBox units via ratio) to the nearest data index.
  function onMove(e: MouseEvent<SVGRectElement>) {
    const r = (e.currentTarget as SVGRectElement).getBoundingClientRect();
    const frac = (e.clientX - r.left) / r.width; // 0..1 across the hit rect
    const i = n === 1 ? 0 : Math.max(0, Math.min(n - 1, Math.round(frac * (n - 1))));
    setActive(i);
    const p = points[i];
    move(
      e,
      <>
        <div className="tip-title">
          {full.format(p.value)}
          {unit ? ` ${unit}` : ""}
        </div>
        <div className="tip-muted">{p.label}</div>
      </>,
    );
  }
  function onLeave() {
    setActive(null);
    clear();
  }

  return (
    <div className="chart-wrap" ref={ref}>
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

        {yTicks.map((v, i) => (
          <g key={`yt-${i}`}>
            <line x1={x0} y1={y(v)} x2={x0 + plotW} y2={y(v)} stroke="#222b40" strokeWidth="1" />
            <text x={x0 - 8} y={y(v) + 3.5} textAnchor="end" className="chart-axis">
              {compact.format(v)}
            </text>
          </g>
        ))}

        <path d={areaPath} fill={`url(#${gradId})`} />
        <path d={linePath} fill="none" stroke={color} strokeWidth="2" />

        {/* policy-event markers (dashed vertical lines) */}
        {evs.map((e, i) => (
          <line
            key={`ev-${i}`}
            x1={e.ex}
            y1={y0}
            x2={e.ex}
            y2={y0 + plotH}
            stroke={EVENT_COLOR}
            strokeWidth="1.25"
            strokeDasharray="3 3"
            opacity="0.7"
            pointerEvents="none"
          />
        ))}

        {/* crosshair + highlighted point */}
        {active != null && (
          <g pointerEvents="none">
            <line x1={x(active)} y1={y0} x2={x(active)} y2={y0 + plotH} stroke={color} strokeWidth="1" opacity="0.4" />
            <circle cx={x(active)} cy={y(points[active].value)} r="4.5" fill={color} stroke="var(--panel)" strokeWidth="1.5" />
          </g>
        )}

        {points.map((p, i) => (
          <circle key={`${p.label}-${i}`} cx={x(i)} cy={y(p.value)} r="2.5" fill={color} opacity={active == null ? 1 : 0.5} />
        ))}

        {labelIdx.map((i) => {
          const anchor = i === 0 ? "start" : i === n - 1 ? "end" : "middle";
          return (
            <text key={`xl-${i}`} x={x(i)} y={H - 8} textAnchor={anchor} className="chart-axis">
              {points[i].label}
            </text>
          );
        })}

        {/* transparent hit area for hover snapping */}
        <rect
          x={x0}
          y={y0}
          width={plotW}
          height={plotH}
          fill="transparent"
          onMouseMove={onMove}
          onMouseLeave={onLeave}
        />

        {/* event flags on top of the hit area, so they stay hoverable */}
        {evs.map((e, i) => (
          <path
            key={`evflag-${i}`}
            className="hit"
            d={`M${(e.ex - 4).toFixed(1)},${y0} L${(e.ex + 4).toFixed(1)},${y0} L${e.ex.toFixed(1)},${y0 + 6} Z`}
            fill={EVENT_COLOR}
            onMouseMove={(ev) => {
              setActive(null);
              move(
                ev,
                <>
                  <div className="tip-title">{e.title ?? e.label}</div>
                  <div className="tip-muted">policy · {e.label}</div>
                </>,
              );
            }}
            onMouseLeave={onLeave}
          />
        ))}
      </svg>
      <TipLayer tip={tip} />
    </div>
  );
}
