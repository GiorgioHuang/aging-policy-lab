import type { Metadata } from "next";
import Link from "next/link";
import { LogoMark } from "@/components/Logo";
import { ContactForm } from "@/components/ContactForm";
import {
  GITHUB_PROFILE_URL,
  GITHUB_REPO_URL,
  GITHUB_NEW_ISSUE_URL,
  GITHUB_DISCUSSIONS_URL,
  GITHUB_USER,
} from "@/lib/site";

export const metadata: Metadata = {
  title: "About — Healthy Aging Policy Observatory",
  description:
    "About the Canadian Healthy Aging Policy Observatory: what it is, how it works, its data and methodology, and how to get in touch.",
};

// Glossary of abbreviations, domain terms, and coined names that appear across
// the platform. Grouped so a first-time visitor can decode any label on the site.
type Term = { term: string; expansion?: string; body: string };
const GLOSSARY: Array<{ group: string; terms: Term[] }> = [
  {
    group: "The platform",
    terms: [
      {
        term: "Observatory",
        body: "How we describe this platform: a research instrument that continuously monitors, quantifies, and evaluates aging policy — not a news site or a static report.",
      },
      {
        term: "HAIL",
        expansion: "Healthy Aging Intelligence Lab",
        body: "The long-horizon research lab this Observatory belongs to, building durable, reusable assets for studying how policy shapes healthy aging.",
      },
      {
        term: "HAPI",
        expansion: "Healthy Aging Policy Index",
        body: "Our own composite index (0–100) scoring how well a jurisdiction supports healthy aging, across six domains, with transparent weights and normalization.",
      },
      {
        term: "Evidence pack",
        body: "The exact set of policies, indicators, and literature the AI assistant is given for a topic. Every claim in a generated draft cites an item from this pack — nothing else.",
      },
    ],
  },
  {
    group: "HAPI domains",
    terms: [
      {
        term: "Six domains",
        body: "HAPI is built from Health, Independence, Social Participation, Financial Security, Care Access, and Digital Inclusion — each scored from documented indicators and combined by audited weights.",
      },
      {
        term: "Indicator",
        body: "A single measured signal (e.g. an ADL-limitation rate) with a fixed definition, data source, normalization range, and direction (higher-is-better or lower-is-better).",
      },
      {
        term: "Care Access",
        body: "The v1-priority domain — access to home care and long-term care — chosen because it maps to high-signal CIHI/IRRS and Nova Scotia data.",
      },
    ],
  },
  {
    group: "Methods & analytics",
    terms: [
      {
        term: "Association vs. Causal",
        body: "Two labels we apply strictly. Association = a descriptive trend or correlation. Causal = a claim backed by a quasi-experimental design. The site never upgrades one to the other.",
      },
      {
        term: "ITS",
        expansion: "Interrupted Time Series",
        body: "A quasi-experimental design that models an outcome's trend before vs. after a policy's effective date, used for careful causal claims.",
      },
      {
        term: "DiD",
        expansion: "Difference-in-Differences",
        body: "Compares a jurisdiction that adopted a policy against one that did not, before vs. after — relying on a parallel-trends assumption.",
      },
      {
        term: "Synthetic Control",
        body: "Builds a weighted 'synthetic' comparison jurisdiction from a donor pool to estimate what would have happened without the policy.",
      },
      {
        term: "RAG",
        expansion: "Retrieval-Augmented Generation",
        body: "The assistant retrieves real policies and literature first, then drafts from that grounded material — so output stays traceable rather than invented.",
      },
      {
        term: "KPI",
        expansion: "Key Performance Indicator",
        body: "A target metric attached to a policy record (e.g. a stated wait-time goal).",
      },
    ],
  },
  {
    group: "Data & provenance",
    terms: [
      {
        term: "Lineage",
        body: "The chain that ties any number on the site back to its origin: Observation → DatasetVersion → DataSource. Shown on the Data Hub for reproducibility.",
      },
      {
        term: "Observation",
        body: "One immutable data point — an indicator's value for a jurisdiction at a point in time — stored with a checksum so it can't silently change.",
      },
      {
        term: "DatasetVersion",
        body: "A specific retrieval of an upstream dataset (with its retrieval date and content checksum). Re-running with unchanged upstream is a no-op.",
      },
      {
        term: "ETL",
        expansion: "Extract, Transform, Load",
        body: "The pipeline stages that pull raw data from a source, clean it, and load validated observations into the database.",
      },
    ],
  },
  {
    group: "Sources & institutions",
    terms: [
      {
        term: "StatCan",
        expansion: "Statistics Canada",
        body: "Canada's national statistical agency — a primary source for demography and outcome indicators.",
      },
      {
        term: "WDS",
        expansion: "Web Data Service",
        body: "Statistics Canada's API for programmatically retrieving data tables.",
      },
      {
        term: "CIHI",
        expansion: "Canadian Institute for Health Information",
        body: "National source for health-system data, including home care and long-term care reporting.",
      },
      {
        term: "IRRS",
        expansion: "Integrated interRAI Reporting System",
        body: "CIHI's consolidated home-care/long-term-care reporting system that replaces the legacy HCRS and CCRS. Care Access data follows IRRS going forward.",
      },
      {
        term: "Census",
        body: "Statistics Canada's national census — the backbone for population denominators and internet-use (Digital Inclusion) tables.",
      },
    ],
  },
  {
    group: "Geography & domain",
    terms: [
      {
        term: "NS",
        expansion: "Nova Scotia",
        body: "The first province modelled in depth — chosen as a replicable template that later extends to the rest of Canada.",
      },
      {
        term: "Federal",
        body: "The Government of Canada level, tracked alongside Nova Scotia so provincial and national policy can be compared.",
      },
      {
        term: "LTC",
        expansion: "Long-Term Care",
        body: "Residential care for older adults who can no longer live independently — a core focus of the Care Access domain.",
      },
      {
        term: "ADL",
        expansion: "Activities of Daily Living",
        body: "Basic self-care tasks (bathing, dressing, eating). Limitation rates are a standard measure of functional independence.",
      },
      {
        term: "PIPEDA",
        expansion: "Personal Information Protection and Electronic Documents Act",
        body: "Canada's federal privacy law — the baseline the platform's privacy and data-handling design respects.",
      },
    ],
  },
];

const MODULES: Array<{ title: string; href: string; body: string }> = [
  {
    title: "Policy Library",
    href: "/policies",
    body: "A structured, timestamped record of aging-related policies across Canadian governments — department, budget, target population, KPIs, lifecycle, and AI-assisted summaries.",
  },
  {
    title: "Data Hub",
    href: "/data",
    body: "Versioned indicators drawn from Statistics Canada, CIHI, and Nova Scotia open data — each observation carries full lineage (source, dataset version, checksum) for reproducibility.",
  },
  {
    title: "HAPI",
    href: "/hapi",
    body: "The Healthy Aging Policy Index — a transparent, weight-audited composite across six domains (Health, Independence, Social Participation, Financial Security, Care Access, Digital Inclusion).",
  },
  {
    title: "Policy Analytics",
    href: "/analytics",
    body: "Quasi-experimental analysis — interrupted time series around real policy interventions — that is careful to separate association from causation.",
  },
  {
    title: "AI Research Assistant",
    href: "/assistant",
    body: "Retrieval over the policy library and literature to accelerate literature reviews, always with citations back to the underlying source.",
  },
];

export default function AboutPage() {
  return (
    <main className="container about">
      <header className="about-hero">
        <LogoMark size={56} />
        <div>
          <h1>Canadian Healthy Aging Policy Observatory</h1>
          <p className="about-lede">
            A research-infrastructure platform that monitors, quantifies, and evaluates the effect
            of aging policy across Canadian governments — starting with Nova Scotia and the federal
            level as a replicable template.
          </p>
        </div>
      </header>

      <section>
        <h2>What this is</h2>
        <p>
          The Observatory is a research instrument, not a news site. It is part of the{" "}
          <strong>Healthy Aging Intelligence Lab (HAIL)</strong> — a long-horizon effort to build
          durable, reusable assets for studying how policy shapes healthy aging: a versioned policy
          knowledge base, a defensible indicator system, reproducible data pipelines, and a
          literature knowledge base. The goal is to support rigorous research and, over time, to
          grow into shared infrastructure that others can build on.
        </p>
      </section>

      <section>
        <h2>What it does</h2>
        <div className="about-modules">
          {MODULES.map((m) => (
            <Link key={m.href} href={m.href} className="panel about-module">
              <h3>{m.title}</h3>
              <p>{m.body}</p>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h2>Data &amp; methodology</h2>
        <ul className="about-list">
          <li>
            <strong>Provenance first.</strong> Every indicator value is stored with its source,
            dataset version, and content checksum, so any number on the site can be traced back to
            the exact upstream table it came from.
          </li>
          <li>
            <strong>Transparent index.</strong> HAPI&rsquo;s normalization ranges and domain weights
            are documented method choices, sensitivity-tested against equal / expert / empirical
            weighting schemes rather than asserted.
          </li>
          <li>
            <strong>Honest about causation.</strong> Descriptive trends are labelled as association;
            causal claims are reserved for quasi-experimental designs (interrupted time series, with
            their assumptions and limits stated). Association is never dressed up as cause.
          </li>
          <li>
            <strong>Open by default.</strong> The methodology, data catalog, and code are public on
            GitHub for scrutiny and replication.
          </li>
        </ul>
      </section>

      <section id="glossary">
        <h2>Glossary</h2>
        <p className="about-glossary-lede">
          The abbreviations, domain terms, and coined names used across the platform.
        </p>
        <div className="about-glossary">
          {GLOSSARY.map((g) => (
            <div key={g.group} className="glossary-group">
              <h3 className="glossary-group-title">{g.group}</h3>
              <dl className="glossary-list">
                {g.terms.map((t) => (
                  <div key={t.term} className="glossary-item">
                    <dt>
                      <span className="glossary-term">{t.term}</span>
                      {t.expansion ? (
                        <span className="glossary-expansion">{t.expansion}</span>
                      ) : null}
                    </dt>
                    <dd>{t.body}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      </section>

      <section id="contact" className="about-contact">
        <h2>Contact</h2>
        <p>
          The fastest and most transparent way to reach me is on <strong>GitHub</strong> — issues
          and discussions are public, get notified instantly, and keep a durable record. For
          anything not suited to a public thread (collaborations, data requests, sensitive matters),
          use the private form below.
        </p>

        <div className="about-links">
          <a className="btn" href={GITHUB_NEW_ISSUE_URL} target="_blank" rel="noopener noreferrer">
            Open an issue
          </a>
          <a
            className="btn btn-ghost"
            href={GITHUB_DISCUSSIONS_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Start a discussion
          </a>
          <a
            className="btn btn-ghost"
            href={GITHUB_PROFILE_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            @{GITHUB_USER} on GitHub
          </a>
        </div>

        <p className="about-repo">
          Source &amp; methodology:{" "}
          <a href={GITHUB_REPO_URL} target="_blank" rel="noopener noreferrer">
            {GITHUB_REPO_URL.replace("https://", "")}
          </a>
        </p>

        <h3 className="about-form-heading">Send a private message</h3>
        <ContactForm />
      </section>
    </main>
  );
}
