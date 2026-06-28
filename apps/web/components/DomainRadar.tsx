"use client";

// Interactive SVG radar ("profile") chart. Each axis is a HAPI domain (0 at the
// centre, 100 at the rim), each jurisdiction a coloured polygon. Hover a vertex
// for the exact score; click a jurisdiction in the legend to toggle it.

import { useState } from "react";
import { useTip, TipLayer, LegendChip } from "./chart-ui";

export type RadarAxis = { key: string; label: string };
export type RadarSeries = { code: string; color: string; scores: Record<string, number | null> };

const RINGS = [25, 50, 75, 100];

export function DomainRadar({ axes, series }: { axes: RadarAxis[]; series: RadarSeries[] }) {
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const { ref, tip, move, clear } = useTip();
  const n = axes.length;
  if (n < 3) return null;

  const W = 460;
  const H = 360;
  const cx = W / 2;
  const cy = H / 2 + 6;
  const R = 118;

  const ang = (i: number) => -Math.PI / 2 + (i / n) * 2 * Math.PI;
  const at = (i: number, r: number) => ({ x: cx + Math.cos(ang(i)) * r, y: cy + Math.sin(ang(i)) * r });
  const poly = (pts: { x: number; y: number }[]) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ") + " Z";

  const shown = series.filter((s) => !hidden.has(s.code));
  const toggle = (code: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });

  return (
    <div className="chart-wrap" ref={ref} onMouseLeave={clear}>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="HAPI domain profile by jurisdiction">
        {RINGS.map((ring) => (
          <path key={`ring-${ring}`} d={poly(axes.map((_, i) => at(i, (ring / 100) * R)))} fill="none" stroke="#222b40" strokeWidth="1" />
        ))}
        {axes.map((a, i) => {
          const tip2 = at(i, R);
          const lab = at(i, R + 20);
          const anchor = Math.abs(lab.x - cx) < 8 ? "middle" : lab.x > cx ? "start" : "end";
          return (
            <g key={a.key}>
              <line x1={cx} y1={cy} x2={tip2.x} y2={tip2.y} stroke="#222b40" strokeWidth="1" />
              <text x={lab.x} y={lab.y + 3} textAnchor={anchor} className="chart-axis">
                {a.label}
              </text>
            </g>
          );
        })}
        <text x={cx} y={cy - R - 6} textAnchor="middle" className="chart-axis" opacity="0.6">
          100
        </text>

        {shown.map((s) => {
          const pts = axes.map((a, i) => at(i, ((s.scores[a.key] ?? 0) / 100) * R));
          return (
            <g key={s.code}>
              <path d={poly(pts)} fill={s.color} fillOpacity="0.14" stroke={s.color} strokeWidth="2" />
              {pts.map((p, i) => {
                const v = s.scores[axes[i].key];
                return (
                  <circle
                    key={`${s.code}-${i}`}
                    className="hit"
                    cx={p.x}
                    cy={p.y}
                    r="4"
                    fill={s.color}
                    onMouseMove={(e) =>
                      move(
                        e,
                        <>
                          <div className="tip-title">
                            {axes[i].label}: {v == null ? "no score" : v.toFixed(1)}
                          </div>
                          <div className="tip-muted">{s.code} · 0–100</div>
                        </>,
                      )
                    }
                  />
                );
              })}
            </g>
          );
        })}
      </svg>

      <div className="chart-legend" style={{ justifyContent: "center" }}>
        {series.map((s) => (
          <LegendChip key={s.code} color={s.color} label={s.code} on={!hidden.has(s.code)} onClick={() => toggle(s.code)} />
        ))}
      </div>

      <TipLayer tip={tip} />
    </div>
  );
}
