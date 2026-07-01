/**
 * Contact-form persistence + validation (server-only).
 *
 * Writes inbound inquiries to the `contact_message` table (migration 0005) with
 * parameterized SQL. Validation is server-side and authoritative — the client
 * mirror in components/ContactForm.tsx is only for UX.
 *
 * Privacy/security posture:
 *   - No maintainer email anywhere; replies happen out-of-band or via GitHub.
 *   - The client IP is never stored raw — only an optional salted SHA-256 prefix
 *     (needs CONTACT_IP_SALT), for abuse triage.
 *   - If CONTACT_WEBHOOK_URL is set, a best-effort notification is POSTed to a
 *     channel the maintainer controls (Slack/Discord-compatible) so inquiries are
 *     *timely* without exposing a personal inbox. Never blocks the response.
 */
import { createHash } from "crypto";
import { pool } from "./db";

export class ContactValidationError extends Error {}

const LIMITS = {
  name: 120,
  email: 200,
  organization: 200,
  subject: 200,
  message: 5000,
} as const;

export type ContactInput = {
  name?: unknown;
  email?: unknown;
  organization?: unknown;
  subject?: unknown;
  message?: unknown;
};

function str(v: unknown): string {
  return typeof v === "string" ? v.trim() : "";
}

// Deliberately permissive — reject only obvious non-emails so valid
// international addresses aren't bounced.
function looksLikeEmail(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

export async function saveContactMessage(
  input: ContactInput,
  meta: { ip?: string; userAgent?: string | null },
): Promise<void> {
  const fields = {
    name: str(input.name),
    email: str(input.email),
    organization: str(input.organization),
    subject: str(input.subject),
    message: str(input.message),
  };

  if (fields.message.length < 10) {
    throw new ContactValidationError("Please write a message of at least 10 characters.");
  }
  for (const key of Object.keys(LIMITS) as (keyof typeof LIMITS)[]) {
    if (fields[key].length > LIMITS[key]) {
      throw new ContactValidationError(`Your ${key} is too long (max ${LIMITS[key]} characters).`);
    }
  }
  if (fields.email && !looksLikeEmail(fields.email)) {
    throw new ContactValidationError("That email address doesn't look valid.");
  }

  const salt = process.env.CONTACT_IP_SALT;
  const ipHash =
    salt && meta.ip
      ? createHash("sha256").update(`${salt}|${meta.ip}`).digest("hex").slice(0, 32)
      : null;
  const userAgent = (meta.userAgent ?? "").slice(0, 400) || null;

  await pool.query(
    `INSERT INTO contact_message
       (name, email, organization, subject, message, source, user_agent, ip_hash)
     VALUES ($1, $2, $3, $4, $5, 'about-form', $6, $7)`,
    [
      fields.name || null,
      fields.email || null,
      fields.organization || null,
      fields.subject || null,
      fields.message,
      userAgent,
      ipHash,
    ],
  );

  notifyWebhook(fields);
}

// Best-effort, fire-and-forget. Slack expects {text}, Discord expects {content};
// sending both keys satisfies either (each ignores the extra). A failure here
// must never surface to the sender, so all errors are swallowed.
function notifyWebhook(f: {
  name: string;
  email: string;
  organization: string;
  subject: string;
  message: string;
}): void {
  const hook = process.env.CONTACT_WEBHOOK_URL;
  if (!hook) return;
  const from =
    (f.name || "anonymous") +
    (f.email ? ` <${f.email}>` : "") +
    (f.organization ? ` (${f.organization})` : "");
  const text =
    `📬 New Observatory contact\n` +
    (f.subject ? `Subject: ${f.subject}\n` : "") +
    `From: ${from}\n\n${f.message}`;
  void fetch(hook, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, content: text }),
  }).catch(() => {});
}
