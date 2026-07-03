import type { Metadata } from "next";
import { revalidatePath } from "next/cache";
import {
  listContactMessages,
  contactStatusCounts,
  updateContactStatus,
  CONTACT_STATUSES,
  type ContactMessage,
} from "@/lib/contact";

// Always read live; never cache or statically render the inbox.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Inbox — Admin",
  robots: { index: false, follow: false },
};

// Server Action: move a message to a new status. Reached by POST to this route,
// which the /admin Basic-Auth middleware already gates.
async function setStatus(formData: FormData): Promise<void> {
  "use server";
  const id = String(formData.get("id") ?? "");
  const status = String(formData.get("status") ?? "");
  await updateContactStatus(id, status);
  revalidatePath("/admin/messages");
}

function fmtDate(iso: string): string {
  // Stored as timestamptz; show a compact, unambiguous UTC stamp.
  return new Date(iso).toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

function Row({ m }: { m: ContactMessage }) {
  return (
    <article className={`msg msg-${m.status}`}>
      <header className="msg-head">
        <span className={`badge status-${m.status}`}>{m.status}</span>
        <strong className="msg-subject">{m.subject || "(no subject)"}</strong>
        <span className="msg-meta">{fmtDate(m.createdAt)}</span>
      </header>

      <div className="msg-from">
        {m.name || "anonymous"}
        {m.email ? (
          <>
            {" · "}
            <a href={`mailto:${m.email}`}>{m.email}</a>
          </>
        ) : null}
        {m.organization ? ` · ${m.organization}` : ""}
      </div>

      <p className="msg-body">{m.message}</p>

      {(m.ip || m.userAgent) && (
        <div className="msg-tech">
          {m.ip ? <span>IP {m.ip}</span> : null}
          {m.userAgent ? <span title={m.userAgent}>UA {m.userAgent}</span> : null}
        </div>
      )}

      <div className="msg-actions">
        {CONTACT_STATUSES.filter((s) => s !== m.status).map((s) => (
          <form key={s} action={setStatus}>
            <input type="hidden" name="id" value={m.id} />
            <input type="hidden" name="status" value={s} />
            <button type="submit" className="msg-btn">
              Mark {s}
            </button>
          </form>
        ))}
      </div>
    </article>
  );
}

export default async function AdminMessagesPage() {
  const [messages, counts] = await Promise.all([
    listContactMessages(300),
    contactStatusCounts(),
  ]);
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <main className="container admin">
      <nav className="admin-nav">
        <span className="admin-nav-here">Contact inbox</span>
        <a href="/admin/assistant-log">Assistant log</a>
      </nav>
      <h1>Contact inbox</h1>
      <p className="admin-summary">
        {total} message{total === 1 ? "" : "s"}
        {" · "}
        {CONTACT_STATUSES.map((s) => `${counts[s] ?? 0} ${s}`).join(" · ")}
      </p>

      {messages.length === 0 ? (
        <div className="panel">No messages yet.</div>
      ) : (
        <div className="msg-list">
          {messages.map((m) => (
            <Row key={m.id} m={m} />
          ))}
        </div>
      )}
    </main>
  );
}
