/**
 * Shared, non-secret site constants. The maintainer's *personal email is
 * deliberately never stored here or shipped to the client* — contact goes
 * through GitHub (public, timely) or the private DB-backed form (see
 * lib/contact.ts). Only the public GitHub profile / repo links are exposed.
 */
export const GITHUB_USER = "GiorgioHuang";
export const GITHUB_REPO = "aging-policy-lab";

export const GITHUB_PROFILE_URL = `https://github.com/${GITHUB_USER}`;
export const GITHUB_REPO_URL = `https://github.com/${GITHUB_USER}/${GITHUB_REPO}`;
export const GITHUB_NEW_ISSUE_URL = `${GITHUB_REPO_URL}/issues/new`;
export const GITHUB_DISCUSSIONS_URL = `${GITHUB_REPO_URL}/discussions`;

// ── SEO / site identity ──────────────────────────────────────────────────────
// The canonical origin used for metadataBase, canonical URLs, Open Graph, the
// sitemap, and structured data. Configure via either:
//   • SITE_URL             — plain server env, read at RUNTIME (not inlined), so a
//                            value set only on the running container is honoured
//                            everywhere (including robots.txt / sitemap.xml).
//   • NEXT_PUBLIC_SITE_URL — inlined at BUILD time (pass as a Docker build-arg) so
//                            statically rendered pages bake the real domain.
// Set at least one; the fallback keeps builds valid until then. Trailing slash
// stripped.
export const SITE_URL = (
  process.env.SITE_URL ||
  process.env.NEXT_PUBLIC_SITE_URL ||
  "https://hapi-observatory.ca"
).replace(/\/+$/, "");

export const SITE_NAME = "Canadian Healthy Aging Policy Observatory";
export const SITE_SHORT = "HAPI Observatory";
export const SITE_TAGLINE =
  "Monitor, quantify, and evaluate the effect of aging policy across Canadian governments.";
export const SITE_DESCRIPTION =
  "A research-infrastructure platform that monitors, quantifies, and evaluates healthy-aging " +
  "policy across Canadian governments — starting with Nova Scotia and the federal level. " +
  "Versioned policy library, an audited Healthy Aging Policy Index (HAPI), reproducible open-data " +
  "pipelines, quasi-experimental analytics, and a cited AI research assistant.";
export const SITE_KEYWORDS = [
  "healthy aging policy",
  "Canadian aging policy",
  "Nova Scotia long-term care",
  "Healthy Aging Policy Index",
  "HAPI",
  "policy observatory",
  "aging indicators",
  "home care policy",
  "policy analytics",
  "interrupted time series",
  "quasi-experimental policy evaluation",
  "Healthy Aging Intelligence Lab",
];
