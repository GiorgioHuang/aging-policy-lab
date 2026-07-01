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
 *   - Best-effort notifications go to whatever channels are configured — a
 *     Telegram bot (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID) and/or a generic
 *     Slack/Discord webhook (CONTACT_WEBHOOK_URL) — so inquiries are *timely*
 *     without exposing a personal inbox. Notifications never block the response.
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

// The lifecycle states a message can be in (mirrors the CHECK in migration 0005).
export const CONTACT_STATUSES = ["new", "read", "archived", "spam"] as const;
export type ContactStatus = (typeof CONTACT_STATUSES)[number];

export type ContactMessage = {
  id: string;
  createdAt: string;
  name: string | null;
  email: string | null;
  organization: string | null;
  subject: string | null;
  message: string;
  status: ContactStatus;
};

/** Read the inbox for the protected /admin/messages page (newest first). */
export async function listContactMessages(limit = 200): Promise<ContactMessage[]> {
  const { rows } = await pool.query<{
    id: string;
    created_at: string;
    name: string | null;
    email: string | null;
    organization: string | null;
    subject: string | null;
    message: string;
    status: ContactStatus;
  }>(
    `SELECT id, created_at::text AS created_at, name, email, organization,
            subject, message, status
       FROM contact_message
   ORDER BY created_at DESC
      LIMIT $1`,
    [limit],
  );
  return rows.map((r) => ({
    id: r.id,
    createdAt: r.created_at,
    name: r.name,
    email: r.email,
    organization: r.organization,
    subject: r.subject,
    message: r.message,
    status: r.status,
  }));
}

/** Per-status counts for the inbox header (e.g. how many are unread). */
export async function contactStatusCounts(): Promise<Record<string, number>> {
  const { rows } = await pool.query<{ status: string; n: string }>(
    `SELECT status, count(*)::text AS n FROM contact_message GROUP BY status`,
  );
  const out: Record<string, number> = {};
  for (const r of rows) out[r.status] = Number(r.n);
  return out;
}

/** Move a message to a new lifecycle state. Status is whitelisted; id is bound. */
export async function updateContactStatus(id: string, status: string): Promise<void> {
  if (!(CONTACT_STATUSES as readonly string[]).includes(status)) {
    throw new Error(`invalid status: ${status}`);
  }
  if (!/^\d+$/.test(id)) {
    throw new Error(`invalid id: ${id}`);
  }
  await pool.query(`UPDATE contact_message SET status = $2 WHERE id = $1`, [id, status]);
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

  notify(fields);
}

// Fan out a single plain-text summary to every configured channel. Best-effort
// and fire-and-forget: a notification failure must never surface to the sender,
// so all errors are swallowed. Plain text (no Markdown/HTML) is used deliberately
// so arbitrary user content can't break formatting or inject markup.
function notify(f: {
  name: string;
  email: string;
  organization: string;
  subject: string;
  message: string;
}): void {
  const from =
    (f.name || "anonymous") +
    (f.email ? ` <${f.email}>` : "") +
    (f.organization ? ` (${f.organization})` : "");
  const text =
    `📬 New Observatory contact\n` +
    (f.subject ? `Subject: ${f.subject}\n` : "") +
    `From: ${from}\n\n${f.message}`;
  sendTelegram(text);
  sendWebhook(text);
}

// Telegram bot: instant push straight from the server to Telegram's API — no
// third-party relay. Set TELEGRAM_BOT_TOKEN (from @BotFather) and TELEGRAM_CHAT_ID
// (your chat with the bot). Telegram caps a message at 4096 chars.
function sendTelegram(text: string): void {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) return;
  void fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: text.slice(0, 3900),
      disable_web_page_preview: true,
    }),
  }).catch(() => {});
}

// Generic incoming webhook. Slack expects {text}, Discord expects {content};
// sending both keys satisfies either (each ignores the extra).
function sendWebhook(text: string): void {
  const hook = process.env.CONTACT_WEBHOOK_URL;
  if (!hook) return;
  void fetch(hook, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, content: text }),
  }).catch(() => {});
}
