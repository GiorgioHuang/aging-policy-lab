import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Evaluate per-request so absolute URLs reflect the runtime NEXT_PUBLIC_SITE_URL
// even when it wasn't provided at build time.
export const dynamic = "force-dynamic";

// Public, indexable routes only — /admin and /api are excluded (see robots.ts).
// Kept as an explicit list so priorities/cadence are intentional rather than
// inferred; add a route here when a new public page ships.
const ROUTES: Array<{
  path: string;
  changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"];
  priority: number;
}> = [
  { path: "/", changeFrequency: "daily", priority: 1.0 },
  { path: "/policies", changeFrequency: "weekly", priority: 0.9 },
  { path: "/hapi", changeFrequency: "weekly", priority: 0.9 },
  { path: "/data", changeFrequency: "weekly", priority: 0.8 },
  { path: "/analytics", changeFrequency: "weekly", priority: 0.8 },
  { path: "/assistant", changeFrequency: "monthly", priority: 0.7 },
  { path: "/research", changeFrequency: "monthly", priority: 0.8 },
  { path: "/about", changeFrequency: "monthly", priority: 0.6 },
  { path: "/contact", changeFrequency: "monthly", priority: 0.5 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return ROUTES.map((r) => ({
    url: `${SITE_URL}${r.path}`,
    lastModified,
    changeFrequency: r.changeFrequency,
    priority: r.priority,
  }));
}
