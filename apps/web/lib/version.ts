/**
 * Deployed build identifier shown in the site footer, resolved in priority order:
 *
 *  1. NEXT_PUBLIC_APP_VERSION — the commit SHA, baked at build time when the deploy
 *     passes it (see cloudbuild.yaml / Dockerfile). Most precise, but needs the
 *     Cloud Build trigger to use cloudbuild.yaml.
 *  2. K_REVISION — the Cloud Run revision name (e.g. "hapi-web-00043-abc"), set
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
  "c47c49a";

// Cloud Run revision names are "<service>-<nnnnn>-<suffix>"; drop the service prefix.
export const APP_VERSION = raw.replace(/^hapi-web-/, "");
