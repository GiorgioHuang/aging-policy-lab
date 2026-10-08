import { pool } from "./db";
import { getAccessContext, orgScope } from "./access";

// Policy Watch (docs/04 §9): newly published items from official feeds that
// matched aging-policy terms, queued for human review in `policy_candidate`.
// These are leads, not Policy Library records — only accepted candidates are
// drafted into the curated seed.

export type Candidate = {
  id: string;
  source: string;
  url: string;
  title: string;
  summary: string | null;
  publishedAt: string | null;
  firstSeenAt: string;
  jurisdictionCode: string | null;
  department: string | null;
  matchedTerms: string[];
  aiCategory: string | null;
  aiRationale: string | null;
  status: "new" | "accepted" | "rejected" | "auto_rejected";
};

export type WatchOverview = {
  candidates: Candidate[]; // awaiting review + accepted, newest first
  counts: Record<Candidate["status"], number>;
  bySource: Record<string, number>;
  latestFind: string | null;
};

/** The watched sources, in the order shown on the page (mirrors watch/sources.py). */
export const WATCH_SOURCES: Array<{
  key: string[];
  label: string;
  jurisdiction: string;
  stage: string;
  href: string;
}> = [
  {
    key: ["gc_news", "gc_news_esdc", "gc_news_phac"],
    label: "Government of Canada news releases",
    jurisdiction: "Federal",
    stage: "announcements, funding",
    href: "https://www.canada.ca/en/news.html",
  },
  {
    key: ["gazette_p1", "gazette_p2"],
    label: "Canada Gazette Parts I & II",
    jurisdiction: "Federal",
    stage: "proposed and enacted regulations",
    href: "https://gazette.gc.ca/",
  },
  {
    key: ["legisinfo_bills"],
    label: "LEGISinfo — bills before Parliament",
    jurisdiction: "Federal",
    stage: "legislation",
    href: "https://www.parl.ca/legisinfo/en/bills",
  },
  {
    key: ["ns_bills"],
    label: "Nova Scotia Legislature — bills",
    jurisdiction: "Nova Scotia",
    stage: "legislation",
    href: "https://nslegislature.ca/legislative-business/bills-statutes/bills",
  },
  {
    key: ["ns_news"],
    label: "Nova Scotia government news releases",
    jurisdiction: "Nova Scotia",
    stage: "announcements, funding",
    href: "https://news.novascotia.ca/",
  },
];

export async function getWatchOverview(limit = 100): Promise<WatchOverview> {
  const ctx = await getAccessContext();
  const scope = orgScope(ctx, "c.org_id", 2);

  const list = await pool.query<{
    id: string;
    source: string;
    url: string;
    title: string;
    summary: string | null;
    published_at: string | null;
    first_seen_at: string;
    jurisdiction_code: string | null;
    department: string | null;
    matched_terms: string[] | null;
    ai_category: string | null;
    ai_rationale: string | null;
    status: Candidate["status"];
  }>(
    `SELECT c.id::text, c.source, c.url, c.title, c.summary,
            c.published_at::text, c.first_seen_at::text, c.jurisdiction_code,
            c.department, c.matched_terms, c.ai_category, c.ai_rationale, c.status
       FROM policy_candidate c
      WHERE c.status IN ('new', 'accepted')${scope.clause}
      ORDER BY COALESCE(c.published_at, c.first_seen_at) DESC
      LIMIT $1`,
    [limit, ...scope.params],
  );

  const stats = await pool.query<{ status: Candidate["status"]; source: string; n: string; latest: string | null }>(
    `SELECT c.status, c.source, count(*)::text AS n, max(c.first_seen_at)::text AS latest
       FROM policy_candidate c
      WHERE true${orgScope(ctx, "c.org_id", 1).clause}
      GROUP BY c.status, c.source`,
    orgScope(ctx, "c.org_id", 1).params,
  );

  const counts: WatchOverview["counts"] = { new: 0, accepted: 0, rejected: 0, auto_rejected: 0 };
  const bySource: Record<string, number> = {};
  let latestFind: string | null = null;
  for (const r of stats.rows) {
    const n = Number(r.n);
    counts[r.status] = (counts[r.status] ?? 0) + n;
    bySource[r.source] = (bySource[r.source] ?? 0) + n;
    if (r.latest && (!latestFind || r.latest > latestFind)) latestFind = r.latest;
  }

  return {
    candidates: list.rows.map((r) => ({
      id: r.id,
      source: r.source,
      url: r.url,
      title: r.title,
      summary: r.summary,
      publishedAt: r.published_at,
      firstSeenAt: r.first_seen_at,
      jurisdictionCode: r.jurisdiction_code,
      department: r.department,
      matchedTerms: r.matched_terms ?? [],
      aiCategory: r.ai_category,
      aiRationale: r.ai_rationale,
      status: r.status,
    })),
    counts,
    bySource,
    latestFind,
  };
}
