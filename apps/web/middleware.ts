import { NextRequest, NextResponse } from "next/server";

/**
 * HTTP Basic Auth guard for the /admin area (the contact inbox).
 *
 * Deliberately dependency-free and fail-closed: with no ADMIN_PASSWORD set the
 * admin area is locked (503), so it can never be accidentally exposed. Runs on
 * every /admin request, including the Server Action POSTs that update message
 * status. Always deploy behind HTTPS (Cloud Run terminates TLS) — Basic Auth
 * sends credentials on each request.
 */
export const config = { matcher: ["/admin/:path*"] };

// Length-aware constant-time-ish compare. Credentials are high-entropy secrets
// over TLS, so the small length leak here is not a practical concern.
function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export function middleware(req: NextRequest) {
  const expectedUser = process.env.ADMIN_USER || "admin";
  const expectedPass = process.env.ADMIN_PASSWORD;

  // Fail closed — the admin area stays locked until a password is configured.
  if (!expectedPass) {
    return new NextResponse("Admin is not configured (set ADMIN_PASSWORD).", {
      status: 503,
    });
  }

  const challenge = () =>
    new NextResponse("Authentication required.", {
      status: 401,
      headers: { "WWW-Authenticate": 'Basic realm="Observatory admin", charset="UTF-8"' },
    });

  const header = req.headers.get("authorization") ?? "";
  const [scheme, encoded] = header.split(" ");
  if (scheme !== "Basic" || !encoded) return challenge();

  let decoded: string;
  try {
    decoded = atob(encoded);
  } catch {
    return challenge();
  }
  const sep = decoded.indexOf(":");
  if (sep < 0) return challenge();
  const user = decoded.slice(0, sep);
  const pass = decoded.slice(sep + 1);

  // Evaluate both comparisons regardless, so failures don't short-circuit.
  const userOk = safeEqual(user, expectedUser);
  const passOk = safeEqual(pass, expectedPass);
  if (!userOk || !passOk) return challenge();

  return NextResponse.next();
}
