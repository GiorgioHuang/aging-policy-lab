import { NextRequest, NextResponse } from "next/server";
import { getEvidencePack, draftReview, type DraftResult } from "@/lib/assistant";

// The Anthropic SDK needs the Node.js runtime; the route writes nothing statically.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Best-effort per-instance rate limit — the draft calls a paid API from a public
// page, so blunt trivial floods from a single IP.
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 6;
const hits = new Map<string, number[]>();

function rateLimited(key: string): boolean {
  const now = Date.now();
  const recent = (hits.get(key) ?? []).filter((t) => now - t < WINDOW_MS);
  recent.push(now);
  hits.set(key, recent);
  return recent.length > MAX_PER_WINDOW;
}

function clientIp(req: NextRequest): string {
  const xff = req.headers.get("x-forwarded-for");
  return (xff ? xff.split(",")[0] : "").trim() || "unknown";
}

// Cache drafts per topic (per instance) so repeated views don't re-bill the API.
const CACHE_TTL_MS = 60 * 60 * 1000;
const cache = new Map<string, { at: number; result: DraftResult }>();

export async function POST(req: NextRequest) {
  let body: { topic?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "Invalid request." }, { status: 400 });
  }
  const topic = (typeof body.topic === "string" ? body.topic : "").trim().slice(0, 200);
  if (!topic) {
    return NextResponse.json({ ok: false, error: "Missing topic." }, { status: 400 });
  }

  const key = topic.toLowerCase();
  const cached = cache.get(key);
  if (cached && Date.now() - cached.at < CACHE_TTL_MS) {
    return NextResponse.json({ ok: true, ...cached.result });
  }

  if (rateLimited(clientIp(req))) {
    return NextResponse.json(
      { ok: false, error: "Too many requests — please try again in a minute." },
      { status: 429 },
    );
  }

  try {
    const pack = await getEvidencePack(topic);
    const result = await draftReview(pack, { ip: clientIp(req) });
    // Only cache a produced draft — transient failures should be retryable.
    if (result.draft) cache.set(key, { at: Date.now(), result });
    return NextResponse.json({ ok: true, ...result });
  } catch (e) {
    console.error("assistant draft route failed:", e);
    return NextResponse.json(
      { ok: false, error: "Could not generate a draft." },
      { status: 500 },
    );
  }
}
