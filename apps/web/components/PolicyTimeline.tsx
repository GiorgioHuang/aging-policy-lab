"use client";

// Interactive SVG timeline strip. Plots every policy as a dot on a shared year
// axis, coloured by jurisdiction. Hover a dot for its full title; click a
// jurisdiction in the legend to toggle it.

import { useMemo, useState, type MouseEvent } from "react";
import { useTip, TipLayer, LegendChip } from "./chart-ui";

export type TimelineItem = {
  id: string;
  year: number;
  title: string;
  jurisdiction: string;
  url?: string | null;
};

const JUR_COLORS: Record<string, string> = {
  "CA-FED": "#4f9dff",
  "CA-NS": "#3ecf8e",
};
const fallbackColor = "#e0a23b";

export function PolicyTimeline({ items }: { items: TimelineItem[] }) {
  const all = items.filter((d) => Number.isFinite(d.year));
  const jurs = useMemo(() => [...new Set(all.map((d) => d.jurisdiction))], [all]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const { ref, tip, move, clear } = useTip();

  const pts = all.filter((d) => !hidden.has(d.jurisdiction));
  if (all.length < 2) return null;

  const W = 720;
  const padL = 16;
  const padR = 16;
  const axisY = 150;
  const plotW = W - padL - padR;

  // bounds derive from ALL items so toggling doesn't rescale the axis
  const years = all.map((d) => d.year);
  const minY = Math.floor(Math.min(...years) / 5) * 5;
  const maxY = Math.ceil(Math.max(...years) / 5) * 5;
  const span = maxY - minY || 1;
  const x = (yr: number) => padL + ((yr - minY) / span) * plotW;

  const counts = new Map<number, number>();
  const placed = pts
    .slice()
    .sort((a, b) => a.year - b.year)
    .map((d) => {
      const k = counts.get(d.year) ?? 0;
      counts.set(d.year, k + 1);
      return { ...d, stack: k };
    });

  const firstDecade = Math.ceil(minY / 10) * 10;
  const decades: number[] = [];
  for (let y = firstDecade; y <= maxY; y += 10) decades.push(y);

  const colorFor = (j: string) => JUR_COLORS[j] ?? fallbackColor;
  const toggle = (j: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(j) ? next.delete(j) : next.add(j);
      return next;
    });

  return (
    <div className="chart-wrap" ref={ref} onMouseLeave={clear}>
      <svg className="chart" viewBox={`0 0 ${W} 168`} role="img" aria-label={`Policy timeline ${minY}–${maxY}`}>
        {decades.map((y) => (
          <g key={`dec-${y}`}>
            <line x1={x(y)} y1={20} x2={x(y)} y2={axisY} stroke="#1b2335" strokeWidth="1" />
            <text x={x(y)} y={axisY + 16} textAnchor="middle" className="chart-axis">
              {y}
            </text>
          </g>
        ))}
        <line x1={padL} y1={axisY} x2={W - padR} y2={axisY} stroke="#2c3650" strokeWidth="1.5" />

        {placed.map((d) => {
          const cyDot = axisY - 10 - d.stack * 12;
          const c = colorFor(d.jurisdiction);
          const onMove = (e: MouseEvent) =>
            move(
              e,
              <>
                <div className="tip-title">{d.title}</div>
                <div className="tip-muted">
                  {d.year} · {d.jurisdiction}
                  {d.url ? " · click to open source ↗" : ""}
                </div>
              </>,
            );
          const dot = (
            <circle className="hit" cx={x(d.year)} cy={cyDot} r="5" fill={c} fillOpacity="0.9" onMouseMove={onMove} />
          );
          return (
            <g key={d.id}>
              <line x1={x(d.year)} y1={axisY} x2={x(d.year)} y2={cyDot} stroke={c} strokeWidth="1" opacity="0.35" />
              {d.url ? (
                <a href={d.url} target="_blank" rel="noreferrer">
                  {dot}
                </a>
              ) : (
                dot
              )}
            </g>
          );
        })}
      </svg>

      <div className="chart-legend">
        {jurs.map((j) => (
          <LegendChip key={j} color={colorFor(j)} label={j} on={!hidden.has(j)} onClick={() => toggle(j)} />
        ))}
      </div>

      <TipLayer tip={tip} />
    </div>
  );
}
