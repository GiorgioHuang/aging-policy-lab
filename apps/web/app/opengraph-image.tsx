import { ImageResponse } from "next/og";
import { SITE_NAME, SITE_TAGLINE } from "@/lib/site";

// Branded 1200×630 social-share card, generated at build time. Applies to every
// route as the default OG/Twitter image (pages may override with their own).
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = SITE_NAME;

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "linear-gradient(135deg, #0f1420 0%, #161d2e 100%)",
          color: "#e6eaf2",
          padding: "72px 80px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          {/* Observatory mark: radar rings + green sprout node. */}
          <svg width="88" height="88" viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="none" stroke="#4f9dff" strokeWidth="2.5" opacity="0.55" />
            <circle cx="32" cy="32" r="18" fill="none" stroke="#7cc4ff" strokeWidth="2.5" opacity="0.7" />
            <circle cx="32" cy="32" r="6" fill="#3ecf8e" />
          </svg>
          <div style={{ display: "flex", fontSize: 30, letterSpacing: 4, color: "#9aa6bf" }}>
            HEALTHY AGING INTELLIGENCE LAB
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", fontSize: 68, fontWeight: 700, lineHeight: 1.05 }}>
            {SITE_NAME}
          </div>
          <div style={{ display: "flex", fontSize: 34, color: "#9aa6bf", maxWidth: 900 }}>
            {SITE_TAGLINE}
          </div>
        </div>

        <div style={{ display: "flex", gap: 16 }}>
          {["Policy Library", "Data Hub", "HAPI", "Analytics", "AI Assistant"].map((t) => (
            <div
              key={t}
              style={{
                display: "flex",
                fontSize: 24,
                color: "#4f9dff",
                border: "1px solid #27314a",
                borderRadius: 10,
                padding: "8px 18px",
              }}
            >
              {t}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size },
  );
}
