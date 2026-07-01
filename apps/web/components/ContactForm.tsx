"use client";

import { useState } from "react";
import { GITHUB_PROFILE_URL } from "@/lib/site";

type State = "idle" | "sending" | "sent" | "error";

export function ContactForm() {
  const [state, setState] = useState<State>("idle");
  const [error, setError] = useState("");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setState("sending");
    setError("");
    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok || !json.ok) {
        throw new Error(json.error || "Could not send your message.");
      }
      form.reset();
      setState("sent");
    } catch (err) {
      setState("error");
      setError(err instanceof Error ? err.message : "Could not send your message.");
    }
  }

  if (state === "sent") {
    return (
      <div className="panel contact-sent" role="status">
        <strong>✓ Thanks — your message was received.</strong>
        <p>
          If you left an email, I&rsquo;ll reply from there. For the fastest response you can also
          reach me on{" "}
          <a href={GITHUB_PROFILE_URL} target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
          .
        </p>
      </div>
    );
  }

  return (
    <form className="contact-form" onSubmit={onSubmit} noValidate>
      {/* Honeypot — hidden from humans, tempting to bots. Leave it empty. */}
      <input
        type="text"
        name="website"
        className="hp"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
      />

      <div className="contact-row">
        <label>
          Name
          <input name="name" maxLength={120} autoComplete="name" />
        </label>
        <label>
          <span className="contact-cap">
            Email <span className="contact-opt">(optional)</span>
          </span>
          <input
            name="email"
            type="email"
            maxLength={200}
            autoComplete="email"
            placeholder="so I can reply"
          />
        </label>
      </div>

      <label>
        <span className="contact-cap">
          Organization <span className="contact-opt">(optional)</span>
        </span>
        <input name="organization" maxLength={200} />
      </label>

      <label>
        Subject
        <input name="subject" maxLength={200} />
      </label>

      <label>
        Message
        <textarea
          name="message"
          rows={5}
          maxLength={5000}
          required
          placeholder="Research collaboration, data question, feedback…"
        />
      </label>

      {state === "error" && (
        <p className="contact-error" role="alert">
          {error}
        </p>
      )}

      <div className="contact-actions">
        <button type="submit" disabled={state === "sending"}>
          {state === "sending" ? "Sending…" : "Send message"}
        </button>
        <span className="contact-note">
          Private inbox — stored securely, reviewed out-of-band. No third-party trackers.
        </span>
      </div>
    </form>
  );
}
