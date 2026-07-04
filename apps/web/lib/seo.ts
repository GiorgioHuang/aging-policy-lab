import type { Metadata } from "next";
import { SITE_NAME, SITE_SHORT } from "./site";

/**
 * Build per-page Metadata with a canonical URL and matching Open Graph / Twitter
 * fields, so every public page is self-describing and non-duplicative. The root
 * layout supplies metadataBase, the title template, and the default OG image;
 * here we only set what is page-specific.
 *
 * @param title        Short page title (the layout template appends "· HAPI Observatory").
 * @param description  1–2 sentence, keyword-aware summary (~150–160 chars ideal).
 * @param path         Absolute path from the site root, e.g. "/hapi".
 */
export function pageMetadata({
  title,
  description,
  path,
}: {
  title: string;
  description: string;
  path: string;
}): Metadata {
  const canonical = path === "/" ? "/" : path.replace(/\/+$/, "");
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      title: `${title} · ${SITE_SHORT}`,
      description,
      url: canonical,
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} · ${SITE_SHORT}`,
      description,
    },
  };
}
