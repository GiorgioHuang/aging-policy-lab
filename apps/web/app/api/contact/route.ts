import { NextRequest, NextResponse } from "next/server";
import { saveContactMessage, ContactValidationError } from "@/lib/contact";

// pg needs the Node.js runtime (not Edge); this handler must not be statically
// optimized since it writes to the database.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Best-effort, per-instance rate limit (resets on cold start). Not a WAF — just
// enough to blunt a trivial flood from a single IP. A real deployment should sit
// behind a proper rate limiter / bot filter.
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 5;
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

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "Invalid request." }, { status: 400 });
  }

  // Honeypot: a hidden field real users never see. If it's filled, a bot did it —
  // return ok so the bot believes it succeeded, but drop the message.
  if (typeof body.website === "string" && body.website.trim() !== "") {
    return NextResponse.json({ ok: true });
  }

  const ip = clientIp(req);
  if (rateLimited(ip)) {
    return NextResponse.json(
      { ok: false, error: "Too many messages — please try again in a minute." },
      { status: 429 },
    );
  }

  try {
    await saveContactMessage(body, { ip, userAgent: req.headers.get("user-agent") });
    return NextResponse.json({ ok: true });
  } catch (e) {
    if (e instanceof ContactValidationError) {
      return NextResponse.json({ ok: false, error: e.message }, { status: 400 });
    }
    console.error("contact save failed:", e);
    return NextResponse.json(
      { ok: false, error: "Something went wrong saving your message. Please try GitHub instead." },
      { status: 500 },
    );
  }
}
