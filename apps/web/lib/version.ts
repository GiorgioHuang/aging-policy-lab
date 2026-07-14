/**
 * Deployed build identifier shown in the site footer.
 *
 * The deploy can bake the exact commit by passing the NEXT_PUBLIC_APP_VERSION
 * build-arg (see Dockerfile) — e.g. the Cloud Build `$SHORT_SHA`. When it isn't
 * provided, this committed short SHA identifies the source revision the image was
 * built from (updated when we cut a deploy). `.git` is excluded from the Docker
 * build context, so the value cannot be computed inside the image.
 */
export const APP_VERSION =
  (process.env.NEXT_PUBLIC_APP_VERSION || "").trim() || "d59807b";
