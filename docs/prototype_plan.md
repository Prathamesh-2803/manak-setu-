# Prototype Plan — Manak Setu

Scope (what's in / what's out), the week-by-week build schedule with owners, how we measure success, and the risk register.

---

## 1. Scope

### In scope (the prototype must do all of this)

| Area | Included |
|---|---|
| **Core pipeline** | Language layer → Spec Decomposer → Hybrid retrieval (BGE-M3 + BM25) → Reranker → Graph expansion with role badges → Version Guard → Certification Oracle → Guardrail + clause generator |
| **Input types** | Typed text (EN/HI/Hinglish), uploaded tender PDF (text-based), voice via browser mic |
| **Languages** | English, Hindi, Hinglish (glossary-normalized) |
| **Wow-feature 1** | **Tender Linter (basic)** — upload draft tender → flags outdated / missing / foreign-only standards |
| **Wow-feature 2** | **Foreign→Indian mapper** — "IEC 60335" → IS equivalent (from BIS equivalence field; unofficial matches labelled "suggested") |
| **Wow-feature 3** | **Gap analytics (log-only)** — below-threshold queries logged → simple count dashboard |
| **Wow-feature 4** | **Voice input** — Web Speech API (`hi-IN`) mic button |
| **Data** | Full crawl: ~23,000 IS records (number, title, scope, status, supersession, ISO equivalence, category/role) + QCO snapshot |
| **Evaluation** | Benchmark from QCO pairs; Recall@5, MRR, allied recall, EN vs HI, fake-IS = 0 |

### Out of scope (deferred — say "roadmap", don't build)

- All 22 scheduled languages; Bhashini API; IndicTrans2 local model
- OCR for scanned PDFs (text PDFs only)
- Celery/Redis job queue
- Live QCO auto-scraper (we ship a **dated snapshot** with source shown; manual updates)
- Word/PDF add-in, GeM/CPPP embeddable widget (REST API is in-scope so these are easy later)
- On-prem vLLM open-weight model (adapter keeps the door open; pitch it as deployment fit)
- Full-text standard documents (copyright — metadata + scope summaries + links only)

---

## 2. Eight-week build schedule (parallel track: teammates do the PPT, due 5 Oct)

### Week 0 status — COMPLETE (2026-10-04)

| Task | Status |
|---|---|
| Git repo initialized | ✅ |
| Repo scaffold (compose, .env.example, .gitignore, folder tree) | ✅ |
| Python 3.14 venv + FastAPI skeleton | ✅ `/health` responds |
| UI/UX Pro Max skill installed (`.opencode/skills/`) | ✅ |
| BIS smoke crawl: fetch → parse → JSONL | ✅ 51 standards from 1 list page (designation, ISO equivalent, revision count, detail URLs) |
| WSL2 + Docker Desktop install + reboot | ✅ Docker 29.8.1, Compose v5.5.1, WSL2 Ubuntu |
| Full stack up: `docker compose up -d` | ✅ 4/4 verified: api `:8000` 200, qdrant `:6333` 200, neo4j `:7474` 200, postgres healthy |
| Gemini + Groq API keys (user) | ⏳ user has keys, will paste into `.env` (needed Week 3) |
| Next.js app scaffold | ⬜ deferred to frontend phase (Week 5, uses ui-ux-pro-max skill) |

**→ Next: Week 1 — full BIS crawl (~23k standards) → Postgres, graph loader → Neo4j, QCO snapshot + glossary.**

| Week | Dates (approx.) | Milestone | Demo moment it unlocks | Owner(s) |
|---|---|---|---|---|
| **0** | Oct 3–5 | **Infra day:** install Docker Desktop + WSL2, create Python 3.12 venv, scaffold repo (compose file, folder structure), smoke-test crawling 1 BIS list page, create Gemini + Groq keys | "The pipe works — 1 page crawled, containers up" | Backend + Data |
| **1** | Oct 6–12 | Full crawl → ~23k records in Postgres; graph loader → Neo4j; QCO snapshot + `glossary.yaml` | "23,000 standards loaded" shown on screen | Data + Graph |
| **2** | Oct 13–20 | Indexer (BGE-M3 dense + BM25 sparse → Qdrant, overnight batch); hybrid retrieval endpoint; reranker | First end-to-end English query returns ranked standards | Retrieval/NLP |
| **3** | Oct 21–27 | Spec Decomposer + LLM adapter (Gemini→Groq with caching) + guardrail (IS validation + confidence gate) + clause generator | **First full English answer with a ready-to-paste clause** | Retrieval/NLP + Backend |
| **4** | Oct 28–Nov 3 | Version Guard + Certification Oracle + role badges from graph | Red/green version status + certification panel with notification source | Graph/Rules |
| **5** | Nov 4–10 | Next.js UI: input box, file upload, results with badges, clause copy button, feedback 👍/👎 | Looks like a real product | Frontend/Voice |
| **6** | Nov 11–17 | Hindi/Hinglish + glossary + voice mic + Foreign mapper + Tender Linter (basic) + gap-analytics logging | **The full "sariya" demo works** | Frontend + NLP |
| **7** | Nov 18–24 | Evaluation run on QCO benchmark + results table + simple gap dashboard | Numbers for the PPT/finale | PM/Eval |
| **8** | Nov 25–Dec | Hardening: 50 real tender snippets, LLM caching, load test, live-demo rehearsal, fallback screenshots | Survives judge questions | Everyone |

*Adjust to the actual finale date once announced. Week 0 is non-negotiable: nothing else works without Docker + data access proven.*

### Definition of done (per milestone)

A milestone is "done" only when: (a) it works through the **UI**, not just a script; (b) at least one teammate other than the owner has run it; (c) it's committed to git with a one-line demo note.

---

## 3. Evaluation strategy

### The free answer key

**QCOs already pair products with their standards** (official figures: 187 orders covering 769 products). That gives us test questions for free: *product name in → expected standard out.* Build this into `eval/benchmark.jsonl` via `pipeline/build_eval.py`.

### Metrics (all reported in the PPT, even if modest)

| Metric | Question it answers | Target mindset |
|---|---|---|
| **Recall@5** | Is the correct standard in our top 5? | Report honestly; compare EN vs HI |
| **MRR** | How high up does it appear? | Higher = officer sees it sooner |
| **Allied-standard recall** | Did we also find the true test/safety/sampling standards? | The graph's whole point |
| **Language fairness** | Accuracy: English vs Hindi vs Hinglish | Show the gap and what we did about it (glossary, translation) |
| **Fake-standard count** | How often did we output a non-existent IS number? | **Must be 0 — guaranteed by the guardrail by design** |
| **Linter precision** (sample) | Of flagged clauses, how many were real problems? | Hand-check 20 flagged clauses |

*A modest, honest number beats a big vague claim. Put the results table in the PPT even if small.*

---

## 4. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **BIS blocks the crawl** (robots/limits/structure change; two portals to cover) | Medium | High | Respectful crawler: rate-limit, identify honestly, cover both portals; **fallback = curated seed dataset** of demo categories; in the pitch: "we'd request an official BIS feed" |
| R2 | **Gemini free tier throttles during demo** | Medium | High | Groq auto-fallback (second free provider); every decomposition **cached** in Postgres; demo queries pre-warmed; keep prompts short |
| R3 | **AMD GPU/ROCm doesn't work on Windows** | High | Low | Plan B is the *default*: overnight CPU batch indexing. GPU treated as a bonus, never on the critical path |
| R4 | **QCO/certification data changes** | High | Medium | Always display notification date + source; label snapshot "as of <date>"; never show a bare yes/no |
| R5 | **Wrong recommendation erodes trust** | Medium | High | Confidence gating below threshold → "no confident match, ask a BIS expert"; show matching scope text as evidence |
| R6 | **Python 3.14 breaks ML wheels** | Medium | Medium | Python 3.12 venv from day 1 |
| R7 | **Docker not installed / WSL2 issues** | Certain → resolved | High | Day-1 task; if Docker fails, native-run fallback documented (Postgres/Qdrant as plain processes) |
| R8 | **Copyright infringement** | Low | High | Store metadata + scope summaries + links only — never full standard PDFs |
| R9 | **LLM invents an IS number** | Medium | Critical | Guardrail: every output IS validated against Postgres; LLM only ever *selects from retrieved rows*; design makes fake output impossible, not just unlikely |
| R10 | **Slots fill / deadline miss (5 Oct)** | — | Critical | PPT on parallel track (user's confirmed choice); check slot count daily |
| R11 | **Hardcoded-demo accusation from judges** | Medium | High | Always demo live; keep fallback screenshots + a 2-min recorded video as insurance only |

---

## 5. Working agreements

1. **Git:** everyone works on branches; commit messages start with the module (`crawler:`, `retrieval:`, `ui:`). No secrets in git (`.env` is ignored; `.env.example` is committed).
2. **Everything through Docker:** if it doesn't run with `docker compose up`, it isn't done.
3. **No hard-coded answers:** results must come from the live pipeline — judges notice.
4. **Decisions get logged** in `docs/project_context.md` (decisions table) — don't re-litigate settled choices in meetings.
5. **Data honesty:** every certification status shows its source + date; every unofficial mapping shows "suggested, needs expert review".

---

## 6. Team-of-6 workload mapping

| Role | Weeks 0–2 | Weeks 3–5 | Weeks 6–8 |
|---|---|---|---|
| Data engineer | Crawler + QCO snapshot + glossary | Data QA + re-crawl automation | 50 tender snippets dataset |
| Retrieval/NLP | Index design + BGE-M3/BM25 setup | Decomposer prompts + guardrail | Eval run + language-fairness tests |
| Graph/rules | Neo4j schema + loader + role labels | Version Guard + Certification Oracle | Linter rules + mapper data |
| Backend | FastAPI skeleton + compose file | LLM adapter + caching + endpoints | Load test + hardening |
| Frontend/voice | UI scaffolding | Results screen + badges + copy button | Hindi UI + mic + linter screen |
| PM/eval/PPT | PPT (parallel, due Oct 5) | Demo script + benchmark build | Scores table + pitch rehearsals |
