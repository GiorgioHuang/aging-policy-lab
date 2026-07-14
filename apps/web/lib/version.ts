/**
 * Deployed build identifier shown in the site footer, resolved in priority order:
 *
 *  1. NEXT_PUBLIC_APP_VERSION — the commit SHA, baked at build time when the deploy
 *     passes it (see cloudbuild.yaml / Dockerfile). Most precise, but needs the
 *     Cloud Build trigger to use cloudbuild.yaml.
 *  2. K_REVISION — the Cloud Run revision name (e.g. "aging-policy-lab-00043-abc"), set
 *     automatically at runtime on every deploy. No config needed, so the footer
 *     changes on each deploy out of the box. Read at request time (server-side),
 *     so footer-bearing pages render dynamically.
 *  3. A committed short SHA — the fallback for local / non-Cloud-Run builds.
 *
 * `.git` is excluded from the Docker build context, so the SHA cannot be computed
 * inside the image; hence the build-arg / runtime-revision approach.
 */
const raw =
  (process.env.NEXT_PUBLIC_APP_VERSION || "").trim() ||
  (process.env.K_REVISION || "").trim() ||
  "70a01d0";

// Display cleanup: a full 40-char commit SHA → short 7-char (so passing either
// $SHORT_SHA or $COMMIT_SHA at build works); otherwise strip the Cloud Run service
// prefix from a revision name ("<service>-<nnnnn>-<suffix>").
export const APP_VERSION = /^[0-9a-f]{40}$/i.test(raw)
  ? raw.slice(0, 7)
  : raw.replace(/^aging-policy-lab-/, "");
