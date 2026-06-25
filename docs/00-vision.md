# 00 — Vision

## 中文概览

本文确立平台的长期定位与使命。核心论点:我们要建的**不是政策网站,而是研究基础设施(Research Infrastructure)**。

- **实验室愿景**:**Healthy Aging Intelligence Lab(HAIL)** —— 利用人工智能、数据科学与政策分析,帮助加拿大建立更公平、高效、可持续的老龄化支持体系。这一定位与"优雅地老去(aging with dignity)"的初衷高度一致,并把 AI 产品、健康信息学研究与老龄化政策研究整合到同一条十年主线上。
- **平台定位**:**Canadian Healthy Aging Policy Observatory** —— 持续监测、量化评估、预测各级政府老龄化政策的效果。
- **三重价值**:研究平台(持续产出成果)/ 创业项目(未来 SaaS 或研究服务)/ 研究资产库(数据库、指标体系、AI Agent、文献库、政策知识图谱、可视化)。
- **为什么值得长期投入**:它把四个原本零散的论文课题,变成围绕**同一平台**不断深化的研究主线;与作者在长期照护(LTC)领域的工作直接相关;可扎根 Nova Scotia 并向全加拿大扩展。

---

## 1. The lab: Healthy Aging Intelligence Lab (HAIL)

**Mission.** To use artificial intelligence, data science, and policy analysis to help Canada build a fairer, more efficient, and more sustainable system of support for an aging population.

HAIL is the ten-year umbrella under which three threads the author cares about converge:

1. **AI products** for health and aging,
2. **Health informatics** research, and
3. **Aging-policy** research.

Historically these would be three separate efforts. HAIL treats them as one program with a shared spine — the observatory described here — so that every paper, dataset, and tool compounds rather than starting over.

The animating idea is **aging with dignity**: that growing older in Canada should be supported by systems that are fair, well-evidenced, and continuously improving. The observatory is the instrument that lets us *measure* whether they are.

## 2. The platform: an observatory, not a website

The platform is the **Canadian Healthy Aging Policy Observatory**. Its purpose is not to *collect* policies but to **continuously monitor, quantify, and forecast the effects** of aging-related policy across Canadian governments.

The word "observatory" is deliberate. An astronomical observatory does not merely store images of the sky; it observes a system over time, measures it against consistent instruments, and reports change. This platform does the same for aging policy:

- it **observes** policy as it is announced, funded, implemented, and retired;
- it **measures** outcomes against an independent, transparent index (HAPI);
- it **reports** change — and is honest about what can and cannot be inferred.

This is what separates the project from an ordinary policy portal. (See [`01-platform-overview.md`](01-platform-overview.md) for the "website vs. observatory" contrast table.)

## 3. Three roles, one system

The observatory is intentionally designed to serve three purposes at once:

| Role | What it means | What it accumulates |
|------|---------------|---------------------|
| **Research platform** | Continuously produces research outputs, not a one-off thesis topic | Papers, datasets, reproducible analyses |
| **Venture** | Can grow into a SaaS product or research service | Users, dashboards, recurring value |
| **Research-asset base** | Every cycle deposits reusable assets | Database, indicator system (HAPI), AI agents, literature knowledge base, policy knowledge graph, visualizations |

A few years of operation should leave behind a compounding stack of **research assets** that simultaneously support *publication* and *practical application*. See [`09-research-roadmap.md`](09-research-roadmap.md) for the research-asset ledger.

## 4. Why this is worth investing in

- **One spine, not four disconnected projects.** Instead of four unrelated theses, the research arc deepens a *single* platform. (Paper 1: *Design of a Healthy Aging Policy Observatory*; Paper 2: *AI-assisted Policy Analysis Framework*; Paper 3: *Agent-based Simulation for Long-term Care Policy*; Paper 4: *Evidence-based Evaluation of Healthy Aging Policies*.)
- **Directly tied to the author's LTC work.** Long-term care is both a domain of expertise and a high-impact policy area for an aging population.
- **Rooted in Nova Scotia, extensible to Canada.** NS + Federal is the v1 template; the data model and HAPI methodology are designed to generalize to other provinces.
- **A durable competitive moat.** The hard, valuable parts — a curated longitudinal policy corpus, a defensible indicator methodology, a working analytics + AI layer — take years to build and are hard to copy. That is exactly why they make a good foundation for both research and a venture.

## 5. Design principles

These principles recur throughout the rest of the documentation:

1. **Reproducibility first.** Every number is traceable to a versioned source. Analyses are re-runnable. (See [`03-data-model.md`](03-data-model.md), [`05-module-data-hub.md`](05-module-data-hub.md).)
2. **Honest inference.** Association is reported as association. Causal claims demand quasi-experimental designs with stated assumptions. Over-claiming is treated as a defect. (See [`07-module-policy-analytics.md`](07-module-policy-analytics.md).)
3. **Independent measurement.** HAPI does not simply re-publish government metrics; it defines its own transparent index. (See [`06-module-indicators-hapi.md`](06-module-indicators-hapi.md).)
4. **AI as an accelerator, not an authority.** AI drafts summaries, retrieves evidence, and proposes analyses — always with citations and human review. (See [`08-module-ai-research-assistant.md`](08-module-ai-research-assistant.md).)
5. **Build for both paper and product.** Every component is designed to be citable *and* shippable.

## 6. What success looks like (5-year horizon)

- A continuously updated, longitudinal corpus of NS + Federal aging policy, expanding to other provinces.
- A published, defensible HAPI methodology used in peer-reviewed work.
- A working analytics + AI layer that turns "I want to study NS dementia policy" into a sourced, cited starting point in minutes.
- A stack of research assets supporting a steady publication stream *and* a credible path to a SaaS/research-service venture.
