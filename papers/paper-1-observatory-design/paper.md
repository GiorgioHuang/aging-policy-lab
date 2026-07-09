# Design of a Healthy Aging Policy Observatory: A Reproducible Research Instrument for Evaluating Aging Policy in Canada

**Giorgio Huang**¹ *(and collaborators — [TODO: finalize author list & affiliations])*

¹ Healthy Aging Intelligence Lab (HAIL). Correspondence via
https://github.com/GiorgioHuang/aging-policy-lab

*Preprint. Draft — not peer reviewed.*

---

## Abstract

Population aging is reshaping public policy across every Canadian jurisdiction,
yet the evidence base for *whether and how* specific aging policies improve older
adults' lives remains fragmented, hard to reproduce, and rarely traceable to
primary sources. We present the design of the **Canadian Healthy Aging Policy
Observatory**, a research-infrastructure platform that treats policy evaluation as
a reproducible computational discipline rather than a reporting exercise. The
Observatory is organized as five interoperating modules — a versioned **Policy
Library**, a lineage-tracked **Data Hub**, a documented composite index
(**HAPI**, the Healthy Aging Policy Index), a **Policy Analytics** layer built
around an explicit association-versus-causation discipline, and a citation-grounded
**AI Research Assistant**. We describe (i) a data model whose immutable
observations and versioned dataset snapshots make every published number auditable
to the exact upstream table it came from; (ii) the HAPI methodology — six
theory-anchored domains, transparent min-max normalization, per-capita rules, and
three named weighting schemes (equal, expert, empirical) reported side by side as
a sensitivity analysis following OECD/JRC guidance; and (iii) an analytics layer
that tags every result `Association` or `Causal`, reserving causal language for
quasi-experimental designs such as interrupted time series with stated
assumptions and autocorrelation-robust inference. We instantiate the design on a
deliberately narrow slice — Nova Scotia and the federal level, with an initial
focus on Care Access — as a replicable template for national extension. We argue
that the *design itself* is a contribution: an aging-policy observatory built for
reproducibility, provenance, and honest causal reasoning is a durable research
instrument that compounds across a multi-paper program and can mature into shared
public infrastructure.

**Keywords:** healthy aging, policy evaluation, composite indicators, reproducible
research infrastructure, interrupted time series, retrieval-augmented generation,
Nova Scotia, long-term care.

---

## 1. Introduction

Canada, like most high-income countries, is aging quickly: the share of the
population aged 65 and over has risen steadily and is projected to keep climbing
for decades. Governments at every level respond with policy — home-care
investment, long-term-care (LTC) capacity, dementia strategies, seniors' income
supports, digital-inclusion programs. But the machinery for *evaluating* those
policies lags behind the machinery for *announcing* them. Three gaps recur:

1. **Fragmentation.** Policy text, budgets, and target populations live in press
   releases and PDFs; outcome data live in separate statistical agencies (Statistics
   Canada, the Canadian Institute for Health Information, provincial open-data
   portals). Nothing links a policy to the indicators it was meant to move.
2. **Irreproducibility.** Published dashboards and reports rarely let a reader trace
   a headline number back to the specific upstream table, vintage, and transformation
   that produced it. Re-running an analysis a year later often yields a different
   number for unstated reasons.
3. **Causal overreach.** Descriptive co-movement ("spending rose and ED visits
   fell") is routinely presented in language that implies causation, without the
   design or assumptions that would justify it.

We argue these are *infrastructure* problems, not analysis problems, and that they
call for an **observatory**: a standing, reproducible instrument that continuously
ingests policies and outcomes, quantifies them with a documented and versioned
method, and supports honest inference — as opposed to a website that presents
pre-computed conclusions. The distinction is the same one astronomy draws between
a telescope and a press photo: the value is in the instrument's reliability and in
the fact that others can point it themselves.

This paper presents the **design** of such an instrument, the Canadian Healthy
Aging Policy Observatory, part of the long-horizon Healthy Aging Intelligence Lab
(HAIL). Our contributions are:

- **An architecture for reproducible policy evaluation** (§3–§4): a five-module
  platform over a data model in which every indicator value is an *immutable
  observation* bound to a *versioned dataset snapshot* and a *data source*, so
  provenance is a structural property rather than a convention.
- **A defensible composite-index methodology, HAPI** (§5): six theory-anchored
  domains of healthy aging, transparent normalization and per-capita rules, and —
  crucially — three weighting schemes reported side by side as a built-in
  sensitivity analysis, with a version stamp so historical scores stay
  interpretable when the method evolves.
- **A causal-discipline layer** (§6): a two-tier analytics model that separates
  description from quasi-experimental inference, with a worked interrupted-time-series
  (ITS) design whose assumptions and limitations are first-class, machine-attached
  metadata rather than footnotes.
- **A grounded AI research assistant** (§7): retrieval over the platform's own
  stores that drafts cited literature reviews in which every claim maps to a
  visible evidence item and no source is fabricated.

We instantiate the design on Nova Scotia (NS) and the federal level, with an
initial emphasis on Care Access — a slice chosen because it maps to high-signal
CIHI/interRAI and NS open data and to real long-term-care policy questions. The
narrow scope is a methodological choice: get the model, the lineage, and the index
*method* right on a small, well-understood slice, then widen additively (§8). We
discuss reproducibility, limitations, and ethics candidly (§9), and close by
situating Paper 1 as the foundation of a four-paper program that reuses and extends
the same platform assets (§10).

## 2. Related work

**Composite indices of aging.** Several frameworks quantify aspects of aging at the
population level: the WHO *World Report on Ageing and Health* (2015) and the
*Decade of Healthy Ageing 2021–2030* articulate "intrinsic capacity" and
"functional ability" as organizing constructs; the European **Active Ageing
Index** and HelpAge International's **Global AgeWatch Index** operationalize
domains such as income security, health, and enabling environments into composite
scores. HAPI is in this tradition but differs in three design commitments: it is
(a) *policy-facing* — indicators are chosen for their link to actionable policy and
are explicitly connected to policy records; (b) *reproducible by construction* —
every sub-indicator value carries source lineage; and (c) *honest about its own
weighting* — it ships equal/expert/empirical weightings side by side rather than
asserting one. Methodologically we follow the OECD/JRC *Handbook on Constructing
Composite Indicators* (2008), particularly its insistence on transparency and
sensitivity analysis.

**Policy monitors and trackers.** Government and NGO "trackers" catalog policies but
seldom integrate outcome data or support inference; academic evaluations produce
rigorous single-policy studies but rarely as standing, reusable infrastructure. The
Observatory aims at the middle ground: a durable platform that is both a catalog and
an analysis instrument.

**Reproducible data infrastructure.** Our data model borrows the data-warehousing and
scientific-workflow ideas of immutable facts, dataset versioning, and content
addressing (checksums) so that analyses are reproducible and idempotent — re-ingesting
unchanged upstream data is a no-op. These ideas are standard in data engineering; our
contribution is applying them rigorously to *policy* evaluation, where provenance is
usually weakest.

**LLMs for policy analysis.** Retrieval-augmented generation (RAG) [10] has made it feasible
to draft literature reviews and summaries grounded in a fixed corpus. The risk —
fabricated citations and unsupported claims — is well documented. Our assistant is
designed so that the model may cite *only* items in a pre-assembled evidence pack, and
every generated claim carries a citation tag mapping to a visible source, making
fabrication structurally detectable (§7).

The frameworks and methods named in this section are cited in full in §11: the WHO
aging reports [1, 2], the OECD/JRC composite-indicator handbook [3], the AgeWatch [4]
and Active Ageing [5] indices, the interrupted-time-series literature [6, 7, 8], the
FAIR data-stewardship principles [9], and retrieval-augmented generation [10].

## 3. System design

### 3.1 Five modules

The Observatory is organized as five modules that share one database and one
provenance discipline (Figure 1):

1. **Policy Library** — a jurisdiction-aware, time-stamped record of aging-related
   policies: department, budget, target population, lifecycle status, themes, and
   AI-assisted summaries, with human review. Policies are versioned.
2. **Data Hub** — connectors that ingest open data (Statistics Canada, CIHI, NS
   open data) into immutable observations with full lineage and automated quality
   checks.
3. **Indicators (HAPI)** — the Healthy Aging Policy Index: a documented composite
   over six domains, computed from Data Hub observations and stored with a method
   version (§5).
4. **Policy Analytics** — descriptive trends and quasi-experimental designs that
   connect policies to outcomes under an explicit association/causation tagging
   discipline (§6).
5. **AI Research Assistant** — retrieval over the Policy Library, indicators, and a
   literature knowledge base that produces cited evidence packs and draft reviews
   (§7).

> **Figure 1 (system context).** Reproduce from
> [`docs/01-platform-overview.md`](../../docs/01-platform-overview.md) — the
> Mermaid system-context diagram showing the five modules, the shared database,
> and the three user roles (researcher, policymaker, public).

### 3.2 Architecture

The platform is a monorepo (Figure 2): a **Next.js/TypeScript** web application
(`apps/web`) for the researcher-facing surfaces; a **Python** data/indicator/analytics
pipeline (`pipeline/hapi_pipeline`) for ingestion, scoring, and analysis; a **PostgreSQL**
schema with forward-only SQL migrations (`db/`); and a shared contracts package. Local
development uses Docker Compose for Postgres; the web app deploys as a container to a
managed runtime. The AI layer wraps a hosted large-language-model API behind narrow,
auditable entry points (summarization, assistant), and every AI generation is logged.

This separation matters for a *research* instrument: the pipeline is the reproducible
core (deterministic transforms, versioned method), while the web app is a read-mostly
view over what the pipeline produced. A number shown in the UI is never computed in the
browser; it is a rendering of a stored, lineage-bearing record.

> **Figure 2 (architecture / monorepo).** Reproduce from
> [`docs/02-architecture.md`](../../docs/02-architecture.md).

### 3.3 Design principles

- **Foundation before breadth.** Get the data model, lineage, and HAPI *method*
  right on a narrow slice (NS + federal, Care Access first), then widen additively.
- **Every artifact is demonstrable and reproducible.** No result is "done" until it
  re-runs to the same value and traces to sources.
- **Researcher-first.** Public dashboards and any future software-as-a-service
  surface come *after* a credible research core.

## 4. Data model

The schema (Figure 3) centers on a small set of entities that make provenance and
reproducibility structural:

- **Jurisdiction** — a hierarchical tree (Canada → Federal / Nova Scotia → …),
  so adding a province is a row, not a schema change.
- **Policy** (and **policy_version**) — a versioned policy record linked to a
  jurisdiction, with lifecycle status and themes.
- **Indicator** — the definition of a measured signal: its meaning, unit, and the
  normalization/per-capita rules that turn raw values into HAPI inputs.
- **DataSource** — metadata about an upstream provider (agency, licence, update
  cadence, access method).
- **DatasetVersion** — a specific *retrieval* of a source: retrieval timestamp and
  a content **checksum**. This is the unit of idempotency.
- **Observation** — an immutable (jurisdiction × indicator × time) value bound to
  the DatasetVersion it came from. Observations are never mutated; a new upstream
  vintage produces a new DatasetVersion and new observations.
- **hapi_score** — a computed domain or composite score for a jurisdiction × period
  at a given `method_version`.
- **policy_indicator** and **indicator_source** — the many-to-many links
  (policies ↔ indicators, indicators ↔ sources) that make the platform a small
  knowledge graph.
- **analysis_finding**, **literature** — analytic results (with a tier tag) and the
  literature knowledge base the assistant draws on.

The key property is the **lineage chain**: every value a reader sees resolves as
`Observation → DatasetVersion → DataSource`. Because observations are immutable and
dataset versions are content-addressed by checksum, an analysis is reproducible
(the same inputs yield the same outputs) and ingestion is idempotent (re-ingesting
unchanged upstream data changes nothing). This is what lets the platform claim that
*any number on the site can be audited to the exact upstream table it came from*.

> **Figure 3 (entity–relationship).** Reproduce from
> [`docs/03-data-model.md`](../../docs/03-data-model.md).

## 5. The Healthy Aging Policy Index (HAPI)

HAPI is a composite index (0–100, higher is better) scoring how well a jurisdiction
supports healthy aging, computed from Data Hub observations. It is deliberately *not*
a re-badging of any single government indicator; it is an independent, documented
construction whose every choice is auditable.

### 5.1 Domains

HAPI v1 spans six domains, grounded in the WHO healthy-ageing framework and the
HelpAge/AgeWatch tradition:

Health, Independence, Social Participation, Financial Security, Care Access, and
Digital Inclusion.

In v1 all six are data-backed for at least one jurisdiction — e.g. Health from
Statistics Canada life expectancy and health-adjusted life expectancy at 65 and
CCHS self-rated measures; Independence from functional-health, disability, and
activities-of-daily-living (ADL) series; Care Access from CCHS regular-provider and
influenza-immunization rates plus the live NS long-term-care waitlist, LTC workforce,
and bed-capacity signals; Financial Security from the seniors' low-income rate and
gap; Digital Inclusion from seniors' internet use; and Social Participation from
community belonging and life satisfaction among those 65+.

### 5.2 Indicator normalization and per-capita rules

Each indicator specifies four things that make its contribution transparent:

- a **domain**;
- a **direction** (`higher_is_better` or `lower_is_better`), aligning "higher HAPI
  score = better outcome";
- a **normalization** rule — v1 uses **min-max** to [0, 100] against a documented
  reference range that brackets the observed Canada + NS span so the score
  discriminates rather than saturating; and
- where the raw datum is a count, a **per-capita** rule (e.g. the NS LTC waitlist is
  expressed as *people waiting per 1,000 population aged 65+*, using a Statistics
  Canada denominator).

Reference ranges are explicit method choices, documented per indicator. For example,
the NS LTC waitlist is normalized over a 2–16 per-1,000 range that brackets its live
~8–13 per-1,000 values, and the nursing/residential-care workforce over 40–100 per
1,000 seniors, bracketing its observed ~60 (Canada) to ~87 (NS) span. Publishing the
ranges — rather than hiding them inside a black-box rescaling — is what lets a
reviewer contest a specific choice.

### 5.3 Weighting and sensitivity analysis

Domain weighting is the most contestable step in any composite index, so HAPI treats
it as a first-class, auditable object rather than a hidden constant. The composite is
a **weighted mean over the domains present** for a given jurisdiction × year — the
engine renormalizes by the weights of the domains actually available, so a cell
missing a domain is scored fairly on the rest. Within a domain, indicators are
averaged by their per-indicator weight.

Following OECD/JRC guidance [3], HAPI defines and *reports side by side* three
weighting schemes (`hapi weights`):

- **equal** — every domain 1.0 (the neutral default);
- **expert** — theory/literature-anchored tiers (the v1 default): Tier 1 (weight 4)
  Health and Care Access, as the intrinsic-capacity core and the most
  policy-actionable health-system pillar; Tier 2 (weight 3) Financial Security and
  Independence; Tier 3 (weight 2) Social Participation and Digital Inclusion —
  grounded in the WHO *World Report on Ageing and Health* and the HelpAge *Global
  AgeWatch Index*;
- **empirical** — data-driven weights proportional to each domain's coefficient of
  variation across jurisdiction × year cells (domains that discriminate more carry
  more weight); indicative while coverage is NS + federal, firming up as the
  jurisdiction set grows.

Because only weight *ratios* matter (the engine renormalizes), the sensitivity report
shows whether the headline ordering of jurisdictions is robust to the weighting choice
— the central robustness question for any composite index.

The three schemes place the following normalized weight on each domain:

| Domain | equal | expert | empirical |
|---|---:|---:|---:|
| Health | 16.7 | 22.2 | 13.5 |
| Independence | 16.7 | 16.7 | 18.1 |
| Social Participation | 16.7 | 11.1 | 8.4 |
| Financial Security | 16.7 | 16.7 | 25.2 |
| Care Access | 16.7 | 22.2 | 18.4 |
| Digital Inclusion | 16.7 | 11.1 | 16.4 |

and imply these composites at each jurisdiction's latest period:

| Jurisdiction | Period | equal | expert | empirical |
|---|---|---:|---:|---:|
| CA (federal) | 2024 | 43.2 | 41.7 | 44.6 |
| CA-NS (Nova Scotia) | 2026 | 50.1 | 50.1 | 50.1 |

The **maximum composite spread across schemes is 2.9 points**, and the NS-above-federal
ordering holds under all three weightings. In other words, the headline comparison is
robust to the weighting choice — the central robustness question for a composite index
— even though the *level* shifts by a couple of points. (The empirical scheme is
indicative while coverage is two jurisdictions and firms up as the set grows.)

### 5.4 Method versioning

Every stored score carries a `method_version` (v1). Changing the indicator set,
normalization, or weighting bumps the version so historical scores remain
interpretable and comparisons are never silently mixed across method definitions.
This is the index analogue of the data model's dataset versioning: reproducibility
across *time* as well as across *inputs*.

The computed v1 domain profiles (latest available score per domain, matching the
platform's radar) and latest composites are:

| Jurisdiction | Overall | As of | Health | Independence | Social Participation | Financial Security | Care Access | Digital Inclusion |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| CA (federal) | 42 | 2024 | 48 | 46 | 50 | 56 | 28 | 72 |
| CA-NS (Nova Scotia) | 50 | 2026 | 38 | 44 | 69 | 21 | 50 | 59 |

*HAPI v1; 0–100, higher is better; each domain shows its latest available score, as
domains draw on different survey vintages.* The two jurisdictions differ in
instructive ways — e.g. Nova Scotia scores higher on Social Participation but lower on
Financial Security — illustrating that the composite is a profile, not a single
ranking. These are demonstration-scale figures over two jurisdictions and should be
read as evidence that the *method* runs end-to-end and reproduces, not as a definitive
provincial assessment (§9).

> **Figure 4 (HAPI domain profile).** The radar/temporal profile at the platform's
> `/hapi` view renders the same domain scores over time.

## 6. Policy analytics and causal discipline

The analytics layer exists to connect policies to outcomes *without* overclaiming.
Its organizing principle is a strict, machine-enforced separation between
description and causal inference.

### 6.1 Two tiers, always labelled

- **Tier 1 — descriptive (Association).** Trends, policy-event overlays, and
  correlations. A Tier-1 card may say a decline is *associated* with a policy's
  effective date; it may not say the policy *caused* it.
- **Tier 2 — quasi-experimental (Causal).** Designs that support a causal reading
  under stated assumptions: interrupted time series (ITS), difference-in-differences
  (DiD), and synthetic control (SC). Each carries its assumptions and limitations as
  attached metadata.

Every result is tagged `Association` or `Causal` in both the UI and data exports, so
a reader can never mistake one for the other. The tag is not cosmetic: it is a field
on the finding, and causal tags are only ever produced *together with* the design's
named assumptions.

### 6.2 Worked example: interrupted time series

The platform ships a worked ITS design as the reference Tier-2 pattern: around a
policy's effective date `t0`, model an outcome series by **segmented regression**
[7, 8] —
a pre-intervention level and trend, plus a post-intervention **level change** and
**slope change**:

```
y_t = β0 + β1·t + β2·1[t ≥ t0] + β3·(t − t0)^+ + ε_t
```

where `β2` estimates the immediate level shift at the intervention and `β3` the change
in trend afterward. Inference uses **Newey-West (HAC) standard errors** [6] to handle
autocorrelation in the residuals. The estimated effect is the gap between the observed
post-intervention segment and the **counterfactual** — the pre-intervention trend
projected forward.

The implementation makes its guardrails explicit: it requires at least three points
on each side of the intervention before reporting coefficients (otherwise it returns
an `insufficient_data` status that *demonstrates the method without asserting an
effect*), and it attaches a fixed statement of the four ITS assumptions to every
result: (1) the pre-trend would have continued absent the intervention; (2) no other
event coincides with `t0`; (3) the linear-segment functional form is adequate; (4)
autocorrelation is handled. A finding is tagged `causal` only in the presence of
these assumptions — never upgraded silently from an association.

> **Figure 5 (ITS).** Reproduce the segmented-regression figure (observed series,
> fitted segments, dashed counterfactual) from the platform's `/analytics` view.

The v1 build carries three ITS designs, and their outcomes illustrate the discipline
directly. Two are attached to real Nova Scotia policies but have too few points on one
side of the intervention, so the platform **refuses to estimate coefficients** and
returns an `insufficient_data` status:

- *NS long-term-care waitlist* around the 2022 LTC capital plan (`care_access.ltc_waitlist_ns`,
  intervention 2022-09): 1 pre / 3 post — below the ≥3-per-segment threshold.
- *NS nursing & residential-care workforce* around the 2022 Continuing Care Assistant
  strategy (`care_access.ltc_workforce_per_1k_65plus`, intervention 2022-10): 5 pre / 2
  post — post-segment too short.

That the platform *demonstrates the design without asserting an effect* on thin data is
the honesty property, not a failure. The third design, an illustrative series with
adequate coverage (5 pre / 5 post), exercises the full segmented regression:

| Term | Coef | 95% CI | p |
|---|---:|---|---:|
| Pre-trend | 1477.0 | 1188.9 .. 1765.1 | <0.001 |
| Level change | −1009.9 | −2075.4 .. 55.6 | 0.063 |
| Slope change | −715.7 | −1125.1 .. −306.3 | <0.001 |

*R² = 0.934; Newey–West (HAC) standard errors.* Here the intervention is associated
with a significant **downward change in trend** (slope change −716, p < 0.001) on top
of a rising pre-trend, with the immediate level change not significant at 0.05
(p = 0.063). Reported as **Causal(ITS)** *only* alongside the four assumptions above —
and even then the platform's convention is that this is a design result for a human to
interpret, not a verdict.

### 6.3 Why enforce discipline in software

Causal overreach is usually a *communication* failure, not a statistical one. By
making the association/causation distinction a data field, attaching assumptions to
causal results by construction, and refusing to emit coefficients on thin data, the
platform turns methodological honesty into a default that survives busy authors and
enthusiastic readers.

## 7. AI research assistant

The assistant accelerates literature review without sacrificing traceability. Its
design goal is that *every* factual claim in a generated draft maps to a visible
source and that no source is fabricated.

### 7.1 Evidence pack, then draft

Given a topic, the assistant first retrieves an **evidence pack** from the platform's
own stores: relevant policies (with citation ids `P#`), literature (`L#`), and
analytic findings (`F#`). The draft is then generated *from that exact pack*, under a
system contract that requires: (1) every factual claim ends with a citation tag
referencing a pack item; (2) the model uses only the pack — no invented sources,
numbers, or references; (3) analytic findings are reported at their exact tier
(`Association` or `Causal`), never upgraded; (4) the output is framed as a draft plus
evidence for a human researcher, not a verdict. Because the pack is fixed and visible,
a fabricated citation is *detectable* — its id will not resolve to a pack item.

### 7.2 Auditability

Every generation is logged (topic, model, evidence-pack sizes, token usage, latency,
status) so the assistant's behavior is itself a research record. The same
retrieve-then-ground contract runs in both the web app and the command-line pipeline,
so the two produce the same grounded, cited output.

> **Figure 6 (assistant flow).** Reproduce from
> [`docs/08-module-ai-research-assistant.md`](../../docs/08-module-ai-research-assistant.md).

## 8. Instantiation: Nova Scotia + federal, Care Access first

We build the design on a narrow slice by intent. Nova Scotia is a tractable,
policy-rich province with acute aging pressures and accessible open data; the federal
level anchors national comparison. Care Access is the lead domain because it maps to
the author's long-term-care focus and to high-signal CIHI/interRAI and NS sources
(the live NS LTC waitlist, LTC workforce, and bed-capacity series). Adding a province
or a source is additive — new rows and one connector — not a schema change, so the
slice is a genuine template for national extension rather than a special case.

A note on source continuity, recorded in the platform: CIHI decommissioned the legacy
home-care and continuing-care reporting systems (HCRS/CCRS) in favor of the Integrated
interRAI Reporting System (IRRS); Care Access connectors therefore treat IRRS as the
forward source and use legacy systems only for historical continuity, handling the
series break explicitly. That such an operational detail is captured in the data
model's source metadata — rather than lost — is exactly the reproducibility property
the design is for.

The v1 build, reproduced from the committed fixture dataset with the pipeline
commands in the paper's repository README, comprises:

| Asset | Count |
|---|---:|
| Policies | 26 |
| Indicators (distinct, observed) | 34 |
| Observations | 231 |
| Dataset versions | 17 |
| Data sources | 17 |
| HAPI scores | 100 |
| Analytic findings | 3 |
| Literature references | 7 |
| Jurisdictions | 3 |

These counts reproduce deterministically from committed fixtures (captured from the
real upstream tables) via `ingest → score → analyze`; the production deployment runs
the same connectors against live sources. That the headline numbers regenerate from
one command is the reproducibility claim of §9 made concrete.

## 9. Reproducibility, limitations, and ethics

**Reproducibility.** Re-runs yield identical results or show exactly what changed;
every number traces to a source; every AI claim carries a citation. Ingestion is
idempotent and dataset versions are content-addressed, in keeping with FAIR
data-stewardship principles [9].

**Limitations.** (1) *Coverage.* With two jurisdictions, the empirical weighting and
any cross-jurisdiction inference are indicative, not definitive; the design's value is
in the method and its extensibility. (2) *Normalization ranges are choices.* Min-max
reference ranges are documented and contestable; a different range shifts scores. We
mitigate by publishing them and by the weighting sensitivity analysis, but a composite
index is a lens, not a measurement. (3) *Causal identification.* ITS and related
designs rest on assumptions (no coincident shocks, correct functional form) that real
policy timelines often strain; thin pre/post data may permit only *demonstrating* a
design, not estimating an effect — which the platform reports honestly. (4) *Indicator
validity.* Domains are proxied by available series; a proxy is not the construct.

**Ethics and privacy.** The platform uses aggregate, published statistics, not
individual records, and its privacy design respects Canada's federal privacy law
(PIPEDA) as a baseline. Most importantly, the design encodes an ethic of *epistemic
honesty*: association is never dressed as causation, index choices are exposed for
scrutiny, and AI output is grounded and cited by construction. For a platform that may
inform decisions about a vulnerable population, that honesty is a safety property, not
a nicety.

## 10. Conclusion and future work

We have described the design of a Healthy Aging Policy Observatory as a reproducible
research instrument: a five-module platform over a provenance-first data model, a
transparent and version-stamped composite index, an analytics layer that enforces the
association/causation distinction in software, and a citation-grounded AI assistant.
The claim of the paper is that this *design* — reproducibility, provenance, and honest
causal reasoning built into the infrastructure — is itself a contribution, because it
yields a durable instrument rather than a one-off study.

The Observatory is the foundation of a four-paper program that reuses and deposits
back into the same assets: Paper 2 hardens the AI-assisted analysis framework; Paper 3
adds agent-based simulation of LTC policy calibrated against HAPI; Paper 4 produces
rigorous quasi-experimental evaluations of real policies. Near-term platform work
widens jurisdiction and source coverage, matures the empirical weighting as coverage
grows, and accumulates worked Tier-2 evaluations — each of which both publishes
findings and stress-tests the analytics guardrails described here.

## Acknowledgements

This work uses publicly available data from Statistics Canada, the Canadian
Institute for Health Information (CIHI), and the Nova Scotia Open Data portal; we
thank these providers for open access to the underlying tables. *[TODO: add funding
sources and named collaborators.]*

## Data and code availability

The platform — schema, pipeline, methodology, and web application — is developed in
the open at https://github.com/GiorgioHuang/aging-policy-lab. Figures and quantitative
results in this paper reproduce from the pipeline commands listed in the paper's
repository README.

## 11. References

*Aging frameworks and composite indices.*

1. World Health Organization. *World Report on Ageing and Health.* Geneva: WHO,
   2015. ISBN 978-92-4-156504-2.
2. World Health Organization. *Decade of Healthy Ageing 2021–2030.* Geneva: WHO,
   2020.
3. Nardo, M., Saisana, M., Saltelli, A., Tarantola, S., Hoffmann, A., & Giovannini,
   E. *Handbook on Constructing Composite Indicators: Methodology and User Guide.*
   Paris: OECD Publishing, 2008. doi:10.1787/9789264043466-en.
4. HelpAge International. *Global AgeWatch Index 2015: Insight Report.* London:
   HelpAge International, 2015.
5. Zaidi, A., Gasior, K., Hofmarcher, M. M., Lelkes, O., Marin, B., Rodrigues, R.,
   Schmidt, A., Vanhuysse, P., & Zolyomi, E. *Active Ageing Index 2012: Concept,
   Methodology and Final Results.* Vienna: European Centre for Social Welfare Policy
   and Research, 2013.

*Quasi-experimental methods (interrupted time series).*

6. Newey, W. K., & West, K. D. "A Simple, Positive Semi-Definite, Heteroskedasticity
   and Autocorrelation Consistent Covariance Matrix." *Econometrica*, 55(3),
   703–708, 1987. doi:10.2307/1913610.
7. Wagner, A. K., Soumerai, S. B., Zhang, F., & Ross-Degnan, D. "Segmented
   regression analysis of interrupted time series studies in medication use
   research." *Journal of Clinical Pharmacy and Therapeutics*, 27(4), 299–309, 2002.
   doi:10.1046/j.1365-2710.2002.00430.x.
8. Lopez Bernal, J., Cummins, S., & Gasparrini, A. "Interrupted time series
   regression for the evaluation of public health interventions: a tutorial."
   *International Journal of Epidemiology*, 46(1), 348–355, 2017.
   doi:10.1093/ije/dyw098.

*Reproducible data infrastructure and grounded generation.*

9. Wilkinson, M. D., Dumontier, M., Aalbersberg, Ij. J., et al. "The FAIR Guiding
   Principles for scientific data management and stewardship." *Scientific Data*, 3,
   160018, 2016. doi:10.1038/sdata.2016.18.
10. Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N.,
    Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D.
    "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *Advances in
    Neural Information Processing Systems (NeurIPS)* 33, 2020. arXiv:2005.11401.

*Primary data sources.*

11. Statistics Canada. Data accessed via the Web Data Service (WDS). Tables used
    include: 13-10-0971-01 (health-adjusted life expectancy at birth and at age 65),
    13-10-0096-01 (Canadian Community Health Survey — health characteristics, annual),
    13-10-0374-01 (Canadian Survey on Disability), 13-10-0789-01 (Canadian Health
    Survey on Seniors — activities of daily living), 11-10-0135-01 (low-income
    statistics by age and sex), and 14-10-0202-01 (employment by industry, Survey of
    Employment, Payrolls and Hours). *[TODO: confirm each table's exact vintage as
    cited in the Data Hub.]*
12. Canadian Institute for Health Information (CIHI). Integrated interRAI Reporting
    System (IRRS) and long-term-care data holdings. Ottawa: CIHI.
13. Government of Nova Scotia. Nova Scotia Open Data Portal — including the
    long-term-care placement waitlist (dataset c39g-gsdd) and the long-term-care
    facilities directory (dataset x76a-axw2). data.novascotia.ca.
