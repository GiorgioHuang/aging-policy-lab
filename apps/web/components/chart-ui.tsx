"use client";

// Shared client-side interactivity for the SVG charts: a cursor-following
// tooltip and a tiny hook that converts pointer events into wrapper-relative
// pixel coordinates. Keeping this in one place lets every chart share the same
// tooltip look and behaviour.

import { useRef, useState, type ReactNode, type MouseEvent } from "react";

export type Tip = { x: number; y: number; w: number; content: ReactNode } | null;

export function useTip() {
  const ref = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<Tip>(null);

  function move(e: MouseEvent, content: ReactNode) {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    setTip({ x: e.clientX - r.left, y: e.clientY - r.top, w: r.width, content });
  }
  const clear = () => setTip(null);
  return { ref, tip, move, clear };
}

/** Absolutely-positioned tooltip; flips to the left near the right edge.
 * Anchors with `right` when flipped so the tooltip's width isn't squeezed by
 * the space remaining to the cursor's right. */
export function TipLayer({ tip }: { tip: Tip }) {
  if (!tip) return null;
  const flip = tip.x > tip.w * 0.62;
  const style = flip
    ? { right: tip.w - tip.x + 12, top: tip.y, transform: "translateY(-50%)" }
    : { left: tip.x + 12, top: tip.y, transform: "translateY(-50%)" };
  return (
    <div className="chart-tip" style={style}>
      {tip.content}
    </div>
  );
}

/** Click-to-toggle legend chip. */
export function LegendChip({
  color,
  label,
  on,
  onClick,
}: {
  color: string;
  label: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" className={`legend-chip${on ? "" : " off"}`} onClick={onClick}>
      <span className="legend-swatch" style={{ background: color }} />
      {label}
    </button>
  );
}
