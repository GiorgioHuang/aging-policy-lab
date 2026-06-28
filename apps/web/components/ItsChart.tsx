"use client";

// Interactive SVG segmented-regression (ITS) chart.
//
// Draws the canonical interrupted-time-series picture: observed series, a marker
// at the intervention, the fitted pre/post trend segments, and a dashed
// counterfactual (pre-trend projected forward). Hover a point to compare
// observed vs fitted vs counterfactual at that year; click the legend to toggle
// the fitted and counterfactual overlays.

import { useState } from "react";
import type { ChartPoint } from "./TrendChart";
import { useTip, TipLayer, LegendChip } from "./chart-ui";

export type ItsTerm = { coef: number; ci_low: number; ci_high: number; p: number };

export type ItsModel = {
  intercept?: ItsTerm;
  pre_trend: ItsTerm;
  level_change: ItsTerm;
  slope_change: ItsTerm;
  n_pre: number;
  n_post: number;
};

const full = new Intl.NumberFormat("en", { maximumFractionDigits: 1 });
const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

const OBS = "#4f9dff";
const FIT = "#3ecf8e";
const CF = "#e0a23b";

export function ItsChart({
  points,
  model,
  interventionLabel,
}: {
  points: ChartPoint[];
  model: ItsModel;
  interventionLabel?: string | null;
}) {
  const [showFit, setShowFit] = useState(true);
  const [showCf, setShowCf] = useState(true);
  const { ref, tip, move, clear } = useTip();

  const n = points.length;
  const t0 = model.n_pre;
  if (n < 2 || model.intercept == null || t0 < 1 || t0 >= n) return null;

  const b0 = model.intercept.coef;
  const b1 = model.pre_trend.coef;
  const b2 = model.level_change.coef;
  const b3 = model.slope_change.coef;

  const fit = (i: number) => (i < t0 ? b0 + b1 * i : b0 + b1 * i + b2 + b3 * (i - t0 + 1));
  const cf = (i: number) => b0 + b1 * i;

  const W = 560;
  const H = 200;
  const gutterL = 50;
  const padR = 14;
  const padT = 16;
  const padB = 40;
  const plotW = W - gutterL - padR;
  const plotH = H - padT - padB;
  const x0 = gutterL;
  const y0 = padT;

  const ys = [...points.map((p) => p.value), fit(0), fit(n - 1), cf(n - 1)];
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
  const xCut = x0 + ((t0 - 0.5) / (n - 1)) * plotW;

  const observedPath = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const preFit = `M${x(0).toFixed(1)},${y(fit(0)).toFixed(1)} L${x(t0 - 1).toFixed(1)},${y(fit(t0 - 1)).toFixed(1)}`;
  const postFit = `M${x(t0).toFixed(1)},${y(fit(t0)).toFixed(1)} L${x(n - 1).toFixed(1)},${y(fit(n - 1)).toFixed(1)}`;
  const cfPath = `M${x(t0 - 1).toFixed(1)},${y(cf(t0 - 1)).toFixed(1)} L${x(n - 1).toFixed(1)},${y(cf(n - 1)).toFixed(1)}`;

  const yTicks = [max, (max + min) / 2, min];
  const maxLabels = 6;
  const step = Math.max(1, Math.ceil(n / maxLabels));
  const labelIdx: number[] = [];
  for (let i = 0; i < n; i += step) labelIdx.push(i);
  if (labelIdx[labelIdx.length - 1] !== n - 1) labelIdx.push(n - 1);

  return (
    <div className="chart-wrap" ref={ref} onMouseLeave={clear}>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`ITS around ${interventionLabel ?? "the intervention"}`}>
        {yTicks.map((v, i) => (
          <g key={`yt-${i}`}>
            <line x1={x0} y1={y(v)} x2={x0 + plotW} y2={y(v)} stroke="#222b40" strokeWidth="1" />
            <text x={x0 - 8} y={y(v) + 3.5} textAnchor="end" className="chart-axis">
              {compact.format(v)}
            </text>
          </g>
        ))}

        <line x1={xCut} y1={y0} x2={xCut} y2={y0 + plotH} stroke="#8a93a6" strokeWidth="1" strokeDasharray="3 3" />
        <text x={xCut} y={y0 - 4} textAnchor="middle" className="chart-axis" fill="#8a93a6">
          {interventionLabel ?? "intervention"}
        </text>

        {showCf && <path d={cfPath} fill="none" stroke={CF} strokeWidth="1.5" strokeDasharray="4 3" opacity="0.9" />}
        {showFit && <path d={preFit} fill="none" stroke={FIT} strokeWidth="2" />}
        {showFit && <path d={postFit} fill="none" stroke={FIT} strokeWidth="2" />}

        <path d={observedPath} fill="none" stroke={OBS} strokeWidth="1.5" opacity="0.85" />
        {points.map((p, i) => (
          <circle
            key={`${p.label}-${i}`}
            className="hit"
            cx={x(i)}
            cy={y(p.value)}
            r="4.5"
            fill={OBS}
            onMouseMove={(e) =>
              move(
                e,
                <>
                  <div className="tip-title">
                    {p.label}: {full.format(p.value)}
                  </div>
                  <div className="tip-muted">
                    fitted {full.format(fit(i))}
                    {i >= t0 ? <> · counterfactual {full.format(cf(i))}</> : null}
                  </div>
                </>,
              )
            }
          />
        ))}

        {labelIdx.map((i) => {
          const anchor = i === 0 ? "start" : i === n - 1 ? "end" : "middle";
          return (
            <text key={`xl-${i}`} x={x(i)} y={y0 + plotH + 16} textAnchor={anchor} className="chart-axis">
              {points[i].label}
            </text>
          );
        })}
      </svg>

      <div className="chart-legend">
        <LegendChip color={OBS} label="observed" on onClick={() => {}} />
        <LegendChip color={FIT} label="fitted" on={showFit} onClick={() => setShowFit((v) => !v)} />
        <LegendChip color={CF} label="counterfactual" on={showCf} onClick={() => setShowCf((v) => !v)} />
      </div>

      <TipLayer tip={tip} />
    </div>
  );
}
