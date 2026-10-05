---
title: Manak Setu API
sdk: docker
app_port: 8000
---
# Manak Setu (मानक सेतु) — Standards Bridge

**AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications**

| | |
|---|---|
| **Hackathon** | Smart India Hackathon (SIH) 2026 |
| **Problem Statement** | SIH26108 |
| **Ministry** | Ministry of Consumer Affairs, Food & Public Distribution |
| **Department** | Department of Consumer Affairs (DoCA) |
| **Theme** | Smart Automation |
| **Idea submission deadline** | **5 October 2026** (338 of 500 slots used at time of writing) |
| **Grand Finale** | 36-hour event, December 2026 (if shortlisted) |
| **Team** | Exactly 6 members, at least 1 woman |

> **One-line pitch:** Manak Setu is a Standards Knowledge Graph plus hybrid AI that turns any tender description — typed or spoken in any Indian language — into a **verified bundle of standards, versions, and certification duties**, with a guardrail that makes fake standard numbers impossible.

---

## Table of contents

1. [The problem](#1-the-problem)
2. [What already exists, and the gap](#2-what-already-exists-and-the-gap)
3. [The solution: how Manak Setu works](#3-the-solution-how-manak-setu-works)
4. [The 14 features](#4-the-14-features)
5. [Worked example (the demo)](#5-worked-example-the-demo)
6. [Technology stack (summary)](#6-technology-stack-summary)
7. [Build plan (summary)](#7-build-plan-summary)
8. [How we prove it works](#8-how-we-prove-it-works)
9. [Team roles and PPT checklist](#9-team-roles-and-ppt-checklist)
10. [Honest caveats and risks](#10-honest-caveats-and-risks)
11. [Glossary](#11-glossary)
12. [Documentation map](#12-documentation-map)

---

## 1. The problem

### What an Indian Standard is

An **Indian Standard (IS)** is an official rulebook for a product or process, written by the **Bureau of Indian Standards (BIS)**. It says how strong the product must be, what materials it may use, how it is tested, and how it is labelled. About **23,000 Indian Standards are in force** (22,689 counted in a 2025 Parliament reply, of which 10,300 have a matching ISO/IEC standard). **187 Quality Control Orders (QCOs)** cover **769 products** with compulsory certification.

### What goes wrong today

A government clerk has to buy 500 ceiling fans, steel bars, or school furniture. The tender must say "the product shall conform to IS xxxx". Finding the right IS is painful because:

| Pain point | What it means in daily life |
|---|---|
| **Too many standards** | ~23,000 rulebooks. Keyword search requires you to already know the right words. |
| **Overlapping scopes** | Two or three standards seem to cover the same thing. Which one is right for this purchase? |
| **Frequent revisions** | Standards get withdrawn or replaced. Real BIS example: **IS 9637:1980 is withdrawn, superseded by IS 9637:2024**. Quoting the old one is a mistake. |
| **Allied standards missed** | One product needs a *family* of rulebooks: product spec, test method, sampling, safety, installation, terminology, marking/packaging. Officers often name only one. |
| **Certification keeps changing** | Whether ISI/CRS/Hallmarking certification is compulsory depends on QCOs. Several QCOs were withdrawn in late 2025 (e.g., notification dated 12 November 2025), and the government reserves the right to reinstate them at any time. |

**Result:** incomplete tenders, outdated references, unclear quality, and disputes between buyers and suppliers.

### The legal angle

**GFR 2017 Rule 144(iii)**: specifications should, as far as practicable, be based on national standards where they exist — and if an officer prefers a foreign specification, the reasons must be **recorded in writing**. Using the right IS is procurement policy, not politeness.

### What the ministry is asking for (the PS's five requirements)

| PS asks for | In plain words | Our answer |
|---|---|---|
| Accept descriptions, specs, or whole tender documents | Paste text or upload a file | Smart file reader + Spec Decomposer |
| Recommend by meaning, not keyword matching | Understand "what I need" even if my words differ | Semantic + hybrid search |
| Find allied standards | Show the related rulebooks I forgot | Standards Knowledge Graph |
| Show latest version and amendments | Never give me an outdated rulebook | Version Guard |
| Suggest mandatory certification | Tell me if ISI mark / CRS / Hallmarking is compulsory | Certification Oracle |
| Support multilingual input | Let me type or speak in my own language | Indic language layer |

---

## 2. What already exists, and the gap

| Existing thing | What it does | Gap |
|---|---|---|
| **BIS "Know Your Standard" / Manak Online** | Search by IS number or keyword; shows PDFs, amendments, licences, labs, committee. | Keyword-based; you must already know what to look for. No meaning understanding, no "what else do I need" advice. |
| **Standard Wizard (private)** | AI semantic search over 28,000+ standards from various organisations. | Not India-specific, no QCO/certification logic, not built for procurement, paid. |
| **GeM + BIS integration** | The Consumer Affairs Secretary says BIS standards are integrated into GeM. | No public sign of semantic recommendation or allied-standard discovery. |
| **GeMAI** | GeM's CTO presented a vision of asking an AI to help create a tender. | A vision, not a standards engine. |
| **Research (Frontiers in AI, 2025)** | Knowledge-graph RAG for engineering standards; plain RAG struggles with linked technical information. | Not for BIS, not for procurement, no certification layer. |

**The gap in one line:** nobody (publicly) combines meaning-based search + a standards relationship map + version checking + live certification rules + multilingual input + tender auditing for Indian procurement. That is our space. *(In the pitch, say "no public tool we could find" — we cannot prove no internal government system exists.)*

---

## 3. The solution: how Manak Setu works

**Think of it as a super-librarian, a quality inspector, and a compliance checker rolled into one.** It does not just search words: it understands the meaning of the request, follows a map of how standards connect to each other, double-checks that nothing is outdated, looks up certification rules, and can even audit an existing tender for mistakes.

### The hospital metaphor

The patient arrives (the tender text). A triage nurse breaks the complaint into parts (Decomposer). Specialists are searched (Retrieval). A referral map shows which other specialists are also needed (Knowledge Graph). The pharmacy checks the medicines are not expired (Version Guard) and that the right permits are in place (Certification Oracle). Finally, the doctor writes a report with evidence (Explainable Output).

### The 7-stage pipeline

```
1. Input & Language Layer   → type / paste / upload / speak, any Indian language
2. Spec Decomposer          → AI extracts facts (product, material, size, tests) + writes sub-questions
3. Hybrid Retrieval         → search by meaning (BGE-M3) AND exact words (BM25)
4. Reranker                 → a second, smarter model re-sorts candidates by true relevance
5. Knowledge Graph Expansion→ follow connections to allied standards, label each one's role
6. Version Guard            → resolve to latest version; flag withdrawn standards in red
7. Certification Oracle     → QCO status, scheme (ISI/CRS/Hallmarking), source notification
+ Guardrail & Output        → validate every IS number, confidence score, evidence text, ready-to-paste clause
```

Two side products reuse the same engine: the **Tender Linter** (audits an existing tender) and the **Gap Analytics Dashboard** (shows BIS which products lack a good standard).

Full diagrams: [`docs/architecture.md`](docs/architecture.md).

---

## 4. The 14 features

### Part A — Core features (directly answer the PS)

1. **Standards Knowledge Graph** — every standard is a dot, every relationship ("refers to", "replaced by", "equals ISO xxx") is a line. Recommending the main standard lets us automatically suggest its relatives. Graphs answer connection questions far better than plain search.
2. **Semantic search using embeddings** — text becomes a list of numbers that captures meaning, so "strong rods used in building slabs" finds the steel reinforcement bar standard even though the word "rods" never appears in its title.
3. **Hybrid retrieval + cross-encoder reranking** — meaning-search misses exact codes, keyword-search misses meaning. Run both, merge, then let an expert model (the reranker) read the query and each candidate together and pick the best 5 out of 50.
4. **Spec Decomposer (LLM structured extraction)** — the AI reads messy tender text and pulls out clean facts (product, material, grade, use, tests), then writes smaller questions: product spec, tests, safety, packaging. One long paragraph is a bad search query; breaking it apart finds the whole family.
5. **Allied standard expansion with role labelling** — walk the graph, collect relatives, and label each: *Product Spec / Test Method / Sampling / Terminology / Safety / Installation / Raw Material / Marking & Packaging* — shown as colour-coded badges.
6. **Version Guard** — always show the newest valid version, list amendments, and warn in red on outdated references (e.g., "IS 9637:1980 — WITHDRAWN, use IS 9637:2024").
7. **Certification Oracle** — a rules table mapping each product/standard to QCO status (active/withdrawn/deferred), scheme (ISI mark, CRS, Hallmarking, Eco Mark), and the source notification with its date. A watcher program checks for updates.
8. **Multilingual NLP and voice** — type or speak in Hindi, Marathi, Tamil, Bengali, or Hinglish. Detects the language, translates, and understands local product words via a vernacular glossary ("सरिया / sariya" = steel reinforcement bar).

### Part B — Unique extras (what makes us stand out)

9. **Hallucination guardrail + explainability** — the AI may only choose from standards that exist in our database; every IS number is validated before display. Each answer shows the matching scope text, a confidence score, and a link to the official record. Low confidence → "ask a BIS expert" instead of guessing. Target: **zero fake standard numbers, guaranteed by design**.
10. **Tender Linter (compliance audit engine)** — upload a draft tender, get a health report: missing standards, outdated versions quoted, foreign certifications with no Indian equivalent, contradictions. Spell-check for standards. (GeM's own corrigendum boilerplate lists mandating foreign certification despite existing Indian Standards as a problem clause — we catch it before the bid goes live.)
11. **Foreign-to-Indian standard mapper** — type "IEC 60335" or "EN 12150", get the Indian equivalent. Of 22,689 standards in force, 10,300 have a corresponding ISO/IEC standard, so many mappings come straight from BIS data. Unofficial mappings are labelled "suggested, needs expert review".
12. **Ready-to-paste clause generator** — writes the actual tender sentence: *"The goods shall conform to IS [number]:[year] (latest revision including amendments) and shall bear the Standard Mark as required under the applicable Quality Control Order."*
13. **Gap-analytics dashboard** — every query with no good match is logged as a possible "standards gap". BIS sees which products people ask about that have no standard (BIS's own training material lists formulating standards where none exist as one of its goals). Turns the tool into a demand signal for new standards.
14. **Feedback loop + deployment-ready integration** — officers click correct/wrong, feeding evaluation. Delivered as a REST API, an embeddable widget for GeM/CPPP, and a Word/PDF add-in; for confidential tenders it runs fully on-premise with open-weight models.

---

## 5. Worked example (the demo)

> *Standard numbers below are illustrative — in the real system every number comes from the live database and is verified before display. See [`docs/demo_script.md`](docs/demo_script.md).*

**The officer's request (typed/spoken in Hinglish):**
*"Bhawan nirman ke liye 12 mm sariya chahiye, 500 tonne, ISI mark wala."*
("I need 12 mm steel bars for building construction, 500 tonnes, ISI-marked.")

| Step | What the system does | What the officer sees |
|---|---|---|
| 1. Language layer | Detects Hinglish, converts to English, maps "sariya" → steel reinforcement bar | "Understood as: 12 mm steel reinforcement bars, 500 tonnes, construction use." |
| 2. Spec Decomposer | Extracts product, size, quantity, use, ISI intent; creates sub-questions (product spec, tests, sampling, marking, construction code) | A "What I understood" card the officer can correct |
| 3. Retrieval + rerank | Hybrid search finds candidates; reranker picks the best | Top match: the high-strength deformed steel bars standard (IS 1786 — verify in DB) |
| 4. Graph expansion | Follows connections: tensile test method, sampling method, concrete construction code, terminology | Colour-coded badges: Main / Test method / Sampling / Code of practice |
| 5. Version Guard | Checks each standard is current, lists amendments | Green tick "current" or red "withdrawn, use this instead" |
| 6. Certification Oracle | Looks up certification status and scheme | "Compulsory certification: Yes/No (as per notification, date). Scheme: ISI mark." |
| 7. Guardrail + output | Validates every number, adds confidence and "matched because…" text, writes the clause | Copy-paste tender clause + a PDF summary |

---

## 6. Technology stack (summary)

| Layer | Tool | In plain words |
|---|---|---|
| Frontend | Next.js + Tailwind, mic button, language switcher | The web pages: input box, file upload, results screen, voice button |
| Backend | FastAPI (Python) | The server that receives requests and runs the 7 stages (Celery/Redis deferred — not needed at prototype speed) |
| Document reading | PyMuPDF / Docling | Reads text out of uploaded tender PDFs/Word files |
| Language tools | Gemini API (translation) + vernacular glossary; browser Web Speech API for voice | Detects the language, translates, understands local product words |
| Embeddings | BGE-M3 (runs locally) | Turns text into meaning-numbers; 100+ languages |
| Reranker | bge-reranker-v2-m3 (runs locally) | The second expert that re-sorts results by true relevance |
| Search store | Qdrant (Docker) | Stores meaning-numbers + keyword index for fast lookup |
| Graph database | Neo4j (Docker); NetworkX fallback | Stores the map of standards and their connections |
| Records/rules store | PostgreSQL (Docker) | Standards metadata, QCO rules, feedback, evaluation results |
| **LLM** | **Gemini Flash (primary) → Groq (fallback)** — *substituted for Claude to keep cost at ₹0* | Does structured extraction, translation, and clause writing; adapter swaps providers on rate-limit |
| Rules store | YAML/JSON table + scheduled updates | The Certification Oracle's QCO list with dates and sources |
| Evaluation | Custom benchmark (Recall@5, MRR), JSON logs | Measures accuracy; target zero fake standards |
| Deployment | **Docker Compose** — *substituted for government cloud* | One command runs the whole stack on any laptop; portable to any server later |

**Full details, free-tier limits, and the Claude→Gemini / cloud→Docker rationale: [`docs/tech_stack.md`](docs/tech_stack.md).**

---

## 7. Build plan (summary)

| # | Step | You end up with |
|---|---|---|
| 1 | **Data ingestion (crawling)** — collect public IS records: number, title, scope, supersession, cross-references, amendments, ISO equivalent, committee. Cover both the old and post-1-Oct-2025 BIS portals. The PS provides no dataset, so we build our own. | A clean table of ~23,000 standards |
| 2 | **Knowledge graph construction** — load standards as dots, references/replacements/equivalents as lines; add QCO records | A working map in Neo4j |
| 3 | **Indexing** — chunk scopes, create dense (BGE-M3) and sparse (BM25) vectors | A searchable hybrid index |
| 4 | **Retrieval pipeline** — hybrid search → reranker → top-K | Working English search |
| 5 | **Spec Decomposer** — prompt the LLM for structured facts and sub-questions | Messy text in, clean facts out |
| 6 | **Graph expansion + roles** — follow connections, label roles (pre-labelled offline and cached) | Allied standards with badges |
| 7 | **Version Guard + Certification Oracle** — resolve to latest versions; rules table + update watcher | Status and certification panel |
| 8 | **Multilingual layer + voice** — language detection, translation, Hinglish handling, glossary, speech input | Hindi + Hinglish working |
| 9 | **Tender Linter** — detect IS/foreign mentions, check against the graph, produce a health report | Upload tender, get audit |
| 10 | **UI + API** — input screen, results with badges, clause copy, feedback buttons, portal API | Demo-ready interface |
| 11 | **Evaluation** — test on real product→standard pairs, record scores | Numbers for the PPT |
| 12 | **Hardening + demo prep** — 50 real tender snippets, caching, live (never hard-coded) demo | A demo that survives judges' questions |

**Week-by-week schedule with owners: [`docs/prototype_plan.md`](docs/prototype_plan.md).**

---

## 8. How we prove it works

- **Free answer key:** QCOs already list products together with their standards (187 orders, 769 products). Product name in → expected standard out.
- **Recall@5:** how often is the correct standard inside our top 5?
- **MRR (Mean Reciprocal Rank):** how high up does the correct answer appear on average?
- **Allied-standard recall:** how many truly related standards did we also find?
- **Language fairness:** accuracy in English vs Hindi vs Hinglish; show the gap and how we reduce it.
- **Safety check:** count of non-existent standard numbers output — target is **zero**, guaranteed by the guardrail.

*A modest honest number beats a big vague claim — put a small results table in the PPT.*

---

## 9. Team roles and PPT checklist

### Six roles (SIH requires exactly 6, at least 1 woman)

| Role | Owns |
|---|---|
| Data engineer | Crawling, cleaning, QCO records, graph data |
| Retrieval / NLP engineer | Embeddings, hybrid search, reranker, Spec Decomposer |
| Graph + rules engineer | Knowledge graph, role labels, Version Guard, Certification Oracle |
| Backend engineer | API, file reading, integrations, deployment |
| Frontend + voice engineer | UI, language switcher, voice input, results design |
| PM + evaluation + presentation | Benchmark, PPT, demo script, pitch, risk answers |

### PPT checklist (deadline: 5 October 2026)

| PPT section | What to write |
|---|---|
| Idea title | *Manak Setu: a Standards Knowledge Graph plus hybrid AI that turns any tender description into a verified bundle of standards, versions, and certification duties.* |
| Problem | 23,000 standards, constant revisions, allied standards missed, certification rules changing → disputes |
| Solution & uniqueness | The 7-stage pipeline plus Knowledge Graph, Version Guard, Certification Oracle, Tender Linter, no-fake-standards guardrail, gap analytics |
| Technical approach | Stack table + pipeline diagram |
| Feasibility & viability | Public data, open-source/free models, measurable evaluation, on-premise option, API integration |
| Risks & fixes | Data access → request official BIS feed. Certification volatility → live watcher with sources. Wrong answers → confidence gating + expert review |
| Impact | Better quality procurement, fewer disputes, support for GFR 2017 Rule 144(iii), faster tender writing, standards-gap insights for BIS |

---

## 10. Honest caveats and risks

- **No prototype fully ends a ministry's search by itself.** Position this as a working prototype, measured accuracy, and a clear pilot plan with BIS and GeM.
- **Data access.** We did not verify whether BIS offers an official API or bulk download. Plan: crawl public pages respectfully, and ask BIS for an official feed. Respect robots rules and site terms.
- **Copyright.** Store metadata, scope summaries, and links to official pages — never copy full standard documents.
- **Certification data is the riskiest part** — it changes often. Always show the source notification and date next to each status.
- **Foreign mappings** not officially matched by BIS must be labelled "suggested, needs expert review".
- **Unverified claims.** What GeM or BIS use internally is not public — avoid stating it as fact.

**Full risk register with mitigations: [`docs/prototype_plan.md`](docs/prototype_plan.md).**

---

## 11. Glossary

| Term | Simple meaning |
|---|---|
| **BIS** | Bureau of Indian Standards: the national body that writes product standards and certifies products |
| **IS (Indian Standard)** | An official rulebook for a product, process, or service |
| **QCO (Quality Control Order)** | A government order making a standard compulsory for certain products — no certificate, no sale |
| **ISI mark / Standard Mark** | The logo on products certified to an Indian Standard |
| **CRS** | Compulsory Registration Scheme: mandatory registration for notified electronics and IT products |
| **Hallmarking** | Certification of purity for precious metals like gold |
| **GFR** | General Financial Rules: the government's buying and spending rulebook (Rule 144(iii) = prefer national standards) |
| **GeM** | Government e-Marketplace: the main government online buying platform |
| **Tender / Bid** | The public document inviting suppliers to sell under stated conditions |
| **Technical Specification** | The part of a tender describing exactly what is wanted |
| **Normative / allied standard** | A related standard the main one depends on, or one that should be used alongside it |
| **Semantic search** | Search by meaning rather than exact words |
| **Embedding** | A list of numbers representing the meaning of a text |
| **Hybrid retrieval** | Meaning-search and keyword-search run together |
| **Reranker** | A second, smarter model that re-sorts search results |
| **LLM** | Large Language Model: the kind of AI that reads and writes text |
| **RAG** | Retrieval-Augmented Generation: the AI looks up real documents first, then answers using them |
| **Knowledge Graph** | A map of things (dots) and how they are connected (lines) |
| **Hallucination** | When an AI confidently states something untrue |
| **Recall@5 / MRR** | Scores measuring how often, and how high, the right answer appears |
| **On-premise** | Running software on your own servers instead of the public internet |

---

## 12. Documentation map

| File | What it holds |
|---|---|
| `README.md` (this file) | The entire project idea: problem, solution, features, example, plan |
| `docs/project_context.md` | SIH facts, deadlines, decisions log, team, environment |
| `docs/architecture.md` | Pipeline diagrams, stage-by-stage walkthrough, repo layout |
| `docs/tech_stack.md` | Final stack, Gemini/Groq details, cost, dropped items |
| `docs/prototype_plan.md` | Scope, 8-week schedule, evaluation, risk register |
| `docs/demo_script.md` | Judge demo walkthrough + fallback plan |

### Sources for the facts used above

Lok Sabha unstarred question 2111 (12 March 2025) and Rajya Sabha question 1325 (Department of Consumer Affairs) for standard/QCO counts; BIS Know Your Standard and Manak Online pages for record fields and the IS 9637 example; GFR 2017 Rule 144(iii); GeM bid corrigendum boilerplate; law-firm updates on QCO withdrawals (Oct–Nov 2025); Frontiers in AI paper (DOI 10.3389/frai.2025.1697169) on knowledge-graph RAG; model pages for BGE-M3, bge-reranker-v2-m3, IndicTrans2, and Bhashini; Standard Wizard listings; CII release on BIS-GeM integration. *Standard numbers in examples are illustrative and must be verified against the live database before the demo.*
