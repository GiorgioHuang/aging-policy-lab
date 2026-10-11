/**
 * The HAPI composite over a jurisdiction's full domain profile.
 *
 * Domains come from different survey vintages, so a single period often holds only
 * the newest domain (e.g. Care Access): a per-period composite there is that one
 * domain, not the index. The headline therefore combines each domain's *latest
 * available* score (the same profile the radar shows), with the weights the scoring
 * engine stored on its 'overall' rows (`inputs.domain_weights`, expert tiers in v1).
 */

export type ByPeriod = Record<string, Record<string, number>>; // period → domain → score

export type ProfileComposite = {
  score: number;
  nDomains: number;
  fromYear: string; // oldest data year in the profile
  toYear: string; // newest data year in the profile
};

/** Merge the per-row weight maps (each lists only the domains present in its period). */
export function mergeWeights(maps: Array<Record<string, number> | null | undefined>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const m of maps) if (m) for (const [d, w] of Object.entries(m)) out[d] ??= Number(w);
  return out;
}

function weighted(profile: Record<string, number>, weights: Record<string, number>): number | null {
  let num = 0;
  let den = 0;
  for (const [d, s] of Object.entries(profile)) {
    const w = weights[d] ?? 1;
    num += s * w;
    den += w;
  }
  return den > 0 ? num / den : null;
}

/** Latest score per domain up to (and including) `untilYear`, with each one's year. */
function profileAsOf(byPeriod: ByPeriod, untilYear?: string) {
  const scores: Record<string, number> = {};
  const years: Record<string, string> = {};
  for (const period of Object.keys(byPeriod).sort()) {
    const yr = period.slice(0, 4);
    if (untilYear && yr > untilYear) break;
    for (const [d, s] of Object.entries(byPeriod[period])) {
      scores[d] = s;
      years[d] = yr;
    }
  }
  return { scores, years };
}

/** Composite of each domain's latest available score. */
export function profileComposite(byPeriod: ByPeriod, weights: Record<string, number>): ProfileComposite | null {
  const { scores, years } = profileAsOf(byPeriod);
  const score = weighted(scores, weights);
  if (score === null) return null;
  const ys = Object.values(years).sort();
  return { score, nDomains: ys.length, fromYear: ys[0], toYear: ys[ys.length - 1] };
}

/** The composite as of each year (each domain's latest score up to that year), from
 * the first year in which every domain the jurisdiction has ever been measured on
 * has a value — earlier years would be a partial index. The last point equals
 * `profileComposite`. */
export function compositeTrend(
  byPeriod: ByPeriod,
  weights: Record<string, number>,
): { label: string; value: number }[] {
  const all = new Set(Object.values(byPeriod).flatMap((p) => Object.keys(p)));
  const years = [...new Set(Object.keys(byPeriod).map((p) => p.slice(0, 4)))].sort();
  const out: { label: string; value: number }[] = [];
  for (const yr of years) {
    const { scores } = profileAsOf(byPeriod, yr);
    if (Object.keys(scores).length < all.size) continue;
    const v = weighted(scores, weights);
    if (v !== null) out.push({ label: yr, value: v });
  }
  return out;
}
