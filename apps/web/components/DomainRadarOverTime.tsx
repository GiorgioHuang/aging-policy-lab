"use client";

// A DomainRadar with a year slider: scrub through the HAPI profile's evolution.
//
// For the selected year we show each domain's most recent score *as of* that
// year (last-observation-carried-forward), so the polygon fills in and shifts
// smoothly as you slide rather than blinking in and out on irregular cadences.

import { useMemo, useState } from "react";
import { DomainRadar, type RadarAxis, type RadarSeries } from "./DomainRadar";

export type RadarTemporalSeries = {
  code: string;
  color: string;
  byYear: Record<string, Record<string, number>>; // year -> domain -> score
};

export function DomainRadarOverTime({
  axes,
  years,
  series,
}: {
  axes: RadarAxis[];
  years: string[]; // sorted ascending
  series: RadarTemporalSeries[];
}) {
  const [idx, setIdx] = useState(Math.max(0, years.length - 1));
  const year = years[idx];

  // LOCF: latest score per domain at or before the selected year.
  const snapshot: RadarSeries[] = useMemo(
    () =>
      series.map((s) => {
        const scores: Record<string, number | null> = {};
        for (const a of axes) {
          let v: number | null = null;
          for (let i = 0; i <= idx; i++) {
            const got = s.byYear[years[i]]?.[a.key];
            if (got != null) v = got;
          }
          scores[a.key] = v;
        }
        return { code: s.code, color: s.color, scores };
      }),
    [series, axes, years, idx],
  );

  if (axes.length < 3 || years.length === 0) return null;

  return (
    <div>
      <DomainRadar axes={axes} series={snapshot} />
      {years.length > 1 && (
        <div className="radar-slider">
          <span className="radar-slider-label">as of</span>
          <input
            type="range"
            min={0}
            max={years.length - 1}
            value={idx}
            step={1}
            onChange={(e) => setIdx(Number(e.target.value))}
            aria-label="Select year"
            list="radar-years"
          />
          <output className="radar-slider-year">{year}</output>
        </div>
      )}
    </div>
  );
}
