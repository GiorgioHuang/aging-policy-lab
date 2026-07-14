"""Generate figures/intelligence-cycle.svg — the Healthy Aging Policy Intelligence
Cycle (paper §3). Hand-laid geometry for a clean, publication-quality circular
figure: six stages on a ring, clockwise flow, and the four points where the design
hardens trust called out. White background so it embeds cleanly in a PDF.

Run:  python gen_cycle.py   (writes intelligence-cycle.svg next to it)
"""
from __future__ import annotations

import math
import os

W, H = 1120, 680
CX, CY = 560, 344
R = 232                      # node-centre ring radius
NW, NH = 176, 62             # node box

STAGES = [
    ("Observation", "source-linked datum"),
    ("Evidence", "quality-checked body"),
    ("Indicator", "normalized measure (HAPI)"),
    ("Policy", "versioned record"),
    ("Outcome", "analyzed movement"),
    ("Feedback", "cited synthesis"),
]

# Trust-hardening callouts placed by angle (deg). Four carry the design-evaluation
# question they answer (§7); Outcome's causal honesty is a design discipline, not one
# of the four numbered RQs. This makes Theory → Design → Evaluation close visibly.
#   node angles: Observation -90, Evidence -30, Indicator 30, Policy 90,
#                Outcome 150, Feedback 210(=-150)
# Placed in the gaps between nodes (on the transitions) so they never overlap a box.
CALLOUTS = [
    (-60, "RQ1 · traceability", "lineage"),          # Observation → Evidence
    (0,   "RQ2 · reproducibility", "versioned"),     # Evidence → Indicator
    (60,  "RQ4 · robustness", "audited weights"),    # Indicator → (measure stage)
    (120, "causal honesty", "association ≠ cause"),  # Outcome (design discipline)
    (240, "RQ3 · grounding", "cited AI"),            # Feedback
]

ACCENT = "#3f7fd0"
INK = "#0f1726"
MUTED = "#5b6b86"
BAND = "#eaf1fb"
RING = "#d6e2f4"


def pt(angle_deg: float, radius: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return CX + radius * math.cos(a), CY + radius * math.sin(a)


def main() -> None:
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="Helvetica, Arial, sans-serif">'
    )
    parts.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    parts.append(
        '<defs><marker id="arw" viewBox="0 0 10 10" refX="7" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/></marker></defs>'
    )

    # Cycle track (soft band) + clockwise flow.
    parts.append(
        f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" '
        f'stroke="{BAND}" stroke-width="26"/>'
    )
    parts.append(
        f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" '
        f'stroke="{RING}" stroke-width="1.5"/>'
    )

    # Node angles: top, then clockwise every 60 degrees.
    angles = [-90 + 60 * i for i in range(6)]

    # Directional arrowheads at the mid-angle between adjacent nodes.
    for i in range(6):
        mid = angles[i] + 30
        x, y = pt(mid, R)
        tangent = mid + 90  # clockwise tangent
        parts.append(
            f'<g transform="translate({x:.1f},{y:.1f}) rotate({tangent:.1f})">'
            f'<path d="M-9,-7 L9,0 L-9,7 L-4,0 z" fill="{ACCENT}"/></g>'
        )

    # Center label.
    parts.append(
        f'<text x="{CX}" y="{CY-8}" text-anchor="middle" font-size="19" '
        f'font-weight="700" fill="{INK}">Healthy Aging Policy</text>'
        f'<text x="{CX}" y="{CY+16}" text-anchor="middle" font-size="19" '
        f'font-weight="700" fill="{INK}">Intelligence Cycle</text>'
        f'<text x="{CX}" y="{CY+40}" text-anchor="middle" font-size="12.5" '
        f'fill="{MUTED}">a policy-level learning health system</text>'
    )

    # Callout labels (outside the ring): an RQ/discipline tag + its property.
    for ang, label, sub in CALLOUTS:
        lx, ly = pt(ang, R + 74)
        c = math.cos(math.radians(ang))
        anchor = "start" if c > 0.3 else ("end" if c < -0.3 else "middle")
        is_rq = label.startswith("RQ")
        color = ACCENT if is_rq else MUTED
        parts.append(
            f'<text x="{lx:.1f}" y="{ly-3:.1f}" text-anchor="{anchor}" '
            f'font-size="13" font-weight="700" fill="{color}">{label}</text>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{ly+13:.1f}" text-anchor="{anchor}" '
            f'font-size="11" font-style="italic" fill="{MUTED}">{sub}</text>'
        )

    # Nodes. Policy is the observatory's subject, so it is emphasised as the
    # visual anchor: a filled tint and a heavier border.
    for (name, sub), ang in zip(STAGES, angles):
        x, y = pt(ang, R)
        rx, ry = x - NW / 2, y - NH / 2
        focus = name == "Policy"
        fill = "#dcebff" if focus else "#ffffff"
        sw = 2.8 if focus else 1.7
        parts.append(
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{NW}" height="{NH}" rx="13" '
            f'fill="{fill}" stroke="{ACCENT}" stroke-width="{sw}"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y-4:.1f}" text-anchor="middle" font-size="16.5" '
            f'font-weight="700" fill="{INK}">{name}</text>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y+15:.1f}" text-anchor="middle" font-size="11.5" '
            f'fill="{MUTED}">{sub}</text>'
        )

    parts.append("</svg>")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intelligence-cycle.svg")
    with open(out, "w") as fh:
        fh.write("".join(parts))
    print("wrote", out)


if __name__ == "__main__":
    main()
