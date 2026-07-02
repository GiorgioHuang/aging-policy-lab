"use client";

import { useEffect, useState } from "react";

type State =
  | { kind: "loading" }
  | { kind: "draft"; text: string }
  | { kind: "unconfigured" }
  | { kind: "message"; text: string };

// Human-readable copy for the non-draft outcomes returned by the API.
function reasonMessage(reason: string | null): State {
  switch (reason) {
    case "no_api_key":
      return { kind: "unconfigured" };
    case "empty_pack":
      return { kind: "message", text: "No matching evidence to synthesize for this topic." };
    case "refusal":
      return { kind: "message", text: "The assistant declined to draft on this topic." };
    default:
      return { kind: "message", text: "Couldn’t generate a draft just now — please try again." };
  }
}

export function AssistantDraft({ topic }: { topic: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    fetch("/api/assistant/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    })
      .then(async (res) => {
        const json = await res.json().catch(() => ({}));
        if (cancelled) return;
        if (res.ok && json.ok && json.draft) {
          setState({ kind: "draft", text: json.draft as string });
        } else if (res.ok && json.ok) {
          setState(reasonMessage(json.reason ?? null));
        } else {
          setState({ kind: "message", text: json.error || "Couldn’t generate a draft." });
        }
      })
      .catch(() => {
        if (!cancelled) setState({ kind: "message", text: "Couldn’t reach the assistant." });
      });
    return () => {
      cancelled = true;
    };
  }, [topic]);

  if (state.kind === "loading") {
    return (
      <div className="panel draft-panel">
        <h2>Cited draft review</h2>
        <p className="draft-status">
          <span className="draft-spinner" aria-hidden="true" /> Drafting from the evidence
          pack above… every claim is cited to a [P]/[L]/[F] id; nothing is invented.
        </p>
      </div>
    );
  }

  if (state.kind === "draft") {
    return (
      <div className="panel draft-panel">
        <h2>Cited draft review</h2>
        <p className="draft-note">
          AI-generated from the evidence pack above — a starting point for a human
          researcher, not a verdict. Every claim carries a citation id; Association vs
          Causal tags are preserved.
        </p>
        <div className="draft-body">{state.text}</div>
      </div>
    );
  }

  if (state.kind === "unconfigured") {
    return (
      <div className="panel draft-panel">
        <h2>Cited draft review</h2>
        <p className="draft-note">
          Live draft generation is off (no <code className="code">ANTHROPIC_API_KEY</code> on
          the server). The retrieval above is complete; you can generate the cited draft from
          the same pack via the CLI:
        </p>
        <pre className="draft-cli">
          python -m hapi_pipeline.cli assistant &quot;{topic}&quot;
        </pre>
      </div>
    );
  }

  return (
    <div className="panel draft-panel">
      <h2>Cited draft review</h2>
      <p className="draft-status">{state.text}</p>
    </div>
  );
}
