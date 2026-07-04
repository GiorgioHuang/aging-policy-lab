import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Evaluate per-request so the host reflects the runtime NEXT_PUBLIC_SITE_URL even
// when it wasn't provided at build time.
export const dynamic = "force-dynamic";

// Public content is crawlable; the admin console and API routes are not.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/admin", "/admin/", "/api/"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
