"use client";

// A DomainRadar with a year slider: scrub through the HAPI profile's evolution.
//
// For the selected year we show each domain's most recent score *as of* that
// year (last-observation-carried-forward), so the polygon fills in and shifts
// smoothly as you slide rather than blinking in and out on irregular cadences.

import { useEffect, useMemo, useState } from "react";
import { DomainRadar, type RadarAxis, type RadarSeries } from "./DomainRadar";

const STEP_MS = 850; // dwell per year while playing

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
  const [playing, setPlaying] = useState(false);
  const year = years[idx];

  // Auto-advance one year per tick while playing; stop at the last year.
  useEffect(() => {
    if (!playing) return;
    if (idx >= years.length - 1) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => setIdx((i) => Math.min(years.length - 1, i + 1)), STEP_MS);
    return () => clearTimeout(t);
  }, [playing, idx, years.length]);

  // Play from the start if we're already at the end; otherwise resume.
  const togglePlay = () => {
    if (!playing && idx >= years.length - 1) setIdx(0);
    setPlaying((p) => !p);
  };

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
          <button
            type="button"
            className="radar-play"
            onClick={togglePlay}
            aria-label={playing ? "Pause" : "Play year animation"}
            aria-pressed={playing}
          >
            {playing ? "❚❚" : "▶"}
          </button>
          <span className="radar-slider-label">as of</span>
          <input
            type="range"
            min={0}
            max={years.length - 1}
            value={idx}
            step={1}
            onChange={(e) => {
              setPlaying(false);
              setIdx(Number(e.target.value));
            }}
            aria-label="Select year"
          />
          <output className="radar-slider-year">{year}</output>
        </div>
      )}
    </div>
  );
}
