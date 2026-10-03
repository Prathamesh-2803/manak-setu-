# Project Context — SIH 2026, Problem Statement SIH26108

Everything a new teammate needs to know on day one: what the hackathon is, the deadlines, what we decided and why, who does what, and what hardware we're building on.

---

## 1. The hackathon facts

| Field | Value |
|---|---|
| Event | Smart India Hackathon (SIH) 2026 |
| Problem Statement ID | **SIH26108** |
| Title | *AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications* |
| Ministry | Ministry of Consumer Affairs, Food & Public Distribution |
| Department | Department of Consumer Affairs (DoCA) |
| Theme | Smart Automation |
| Idea submission deadline | **5 October 2026 — 2 days from plan date** |
| Slot status | 338 of 500 idea slots already used (slots fill up — submit early) |
| Grand Finale | 36-hour event, December 2026, only if our idea is shortlisted |
| Team size | Exactly 6 members, at least 1 female member |

**Strategy:** the PPT comes first (deadline-driven), and the full build matters if we're shortlisted for the December finale. Teammates handle the PPT in parallel while we start the build (user's confirmed choice).

---

## 2. What the problem statement demands (acceptance checklist)

The ministry wants a "smart librarian" that reads a product description **in any language** and returns:

1. ✅ The right standard(s)
2. ✅ The allied standards (references, tests, safety, installation)
3. ✅ The latest version and amendments
4. ✅ Whether certification (ISI mark, CRS, Hallmarking) is mandatory
5. ✅ Accepts descriptions, specs, or whole tender documents (text or file upload)
6. ✅ Recommends by **semantic understanding**, not keyword matching
7. ✅ Supports multilingual input (type or speak)

Every feature we build must map back to one of these bullets — that's how we answer "which requirement does this solve?" when judges ask.

---

## 3. Decisions log

All user-confirmed choices. Change history lives here so nobody re-litigates settled decisions.

| # | Decision | Chosen over | Why |
|---|---|---|---|
| D1 | **Gemini API (Flash, free tier) as primary LLM; Groq as fallback** | Claude API | Claude costs money; Gemini Flash + Groq both have generous free tiers with no credit card. Prototype cost stays ₹0. |
| D2 | **Docker (Docker Compose) for deployment** | Government cloud | Cloud costs money and needs approval; Docker runs the whole stack on any laptop and is portable to any server later. |
| D3 | **English + Hindi + Hinglish** for the prototype | All 22 Indian languages | Covers the required multilingual demo ("sariya" = rebar) fastest; more languages deferred. |
| D4 | **All four wow-features**: Tender Linter (basic), Foreign→Indian mapper, Gap analytics (log-only), Voice input | Pick fewer | User selected all four — they're cheap because they reuse the core engine. |
| D5 | **Full ~23,000 standards crawl** | Curated subset | User wants the big number for judges; indexing runs as an overnight batch job. |
| D6 | **Parallel track**: teammates do the PPT, build starts now | PPT first, build later | User has teammates covering the 5 Oct deadline. |
| D7 | **Skip Celery/Redis** for the prototype | Match the PPT stack exactly | Our jobs (PDF parse, retrieval) are fast enough with plain async; fewer containers, simpler code. Postgres caches LLM responses instead. Revisit if we hit slow-job pain. |
| D8 | **Voice via browser Web Speech API** (`hi-IN`) | Bhashini speech API | Free, no government API key/registration needed, works in Chrome/Edge immediately. |
| D9 | **Translation via Gemini API + hand-built glossary** | IndicTrans2 local model / Bhashini API | No heavyweight model install, no API registration; glossary gives the wow-moment ("sariya" → rebar). |
| D10 | **Store metadata + scope summaries + links only** — never full standard PDFs | Crawl complete documents | Copyright safety; also smaller storage. |

---

## 4. Environment (the machine we build on)

| Item | Status |
|---|---|
| OS | Windows 11 (win32), PowerShell |
| CPU / RAM | (fill in: check `Get-CPUInfo` / Task Manager) |
| **GPU** | AMD Radeon RX 6500M (4 GB) + AMD Radeon Graphics (496 MB) — **AMD, not NVIDIA** |
| GPU caveat | PyTorch ROCm on Windows is unreliable → **Plan A:** try ROCm/WSL2 for indexing speed; **Plan B (default schedule):** overnight CPU batch indexing of 23k scope texts. Demo inference never needs the GPU (reranking ~30 candidates runs fine on CPU). |
| Docker | ⏳ **Not installed — blocked on user action.** WSL2 features + Docker Desktop need ONE elevated PowerShell run (see `scripts/install_env.ps1`), then a reboot. |
| Node.js | ✅ v24.21.0 |
| npm | ✅ 11.19.0 |
| Python | ✅ **3.14.7 used for the venv** (`.venv`). Notes: the installed 3.13 launcher entry is broken (points to a missing path), 3.10 also available; 3.14 is the working default and has torch support in 2026. |
| Git | ✅ 2.53.0 (repo initialized) |
| Project folder | `C:\Users\Prathamesh\Documents\Manak Setu` |
| **UI/UX skill** | ✅ **ui-ux-pro-max installed** at `.opencode/skills/` (via `uipro init --ai opencode`). Use it for ALL frontend work (Week 5+). Restart opencode session if the skill doesn't auto-activate. Not committed to git (57 MB, regenerable) — teammates install with: `npm i -g ui-ux-pro-max-cli` then `uipro init --ai opencode`. |

**API keys to create (both free, no card):**
- Gemini: Google AI Studio → `GEMINI_API_KEY`
- Groq: console.groq.com → `GROQ_API_KEY`

---

## 5. Team roles (6 members, ≥1 woman)

| Role | Owns | First-week deliverable |
|---|---|---|
| **Data engineer** | Crawling BIS pages, cleaning, QCO snapshot, glossary | Working crawler → first 100 records in Postgres |
| **Retrieval / NLP engineer** | BGE-M3 embeddings, BM25, hybrid search, reranker, Spec Decomposer prompt | One English query returns ranked results |
| **Graph + rules engineer** | Neo4j schema, role labels, Version Guard, Certification Oracle (QCO table) | Graph loaded; supersession query works |
| **Backend engineer** | FastAPI, file reading (PyMuPDF), LLM adapter (Gemini→Groq), deployment | `/api/recommend` endpoint alive |
| **Frontend + voice engineer** | Next.js UI, badges, clause copy, feedback buttons, mic input | Input box → results screen wired |
| **PM + evaluation + presentation** | Benchmark from QCO pairs, PPT (parallel track), demo script, pitch | Eval dataset extracted from QCOs |

---

## 6. Key facts to keep straight (for PPT and judges)

- ~**23,000** Indian Standards in force (22,689 counted, 10,300 with ISO/IEC equivalents).
- **187 QCOs** covering **769 products** → also our free evaluation answer key.
- Real supersession example: **IS 9637:1980 → withdrawn, superseded by IS 9637:2024**.
- **GFR 2017 Rule 144(iii)**: prefer national standards; foreign specs need written reasons.
- QCO volatility: several withdrawn ~12 Nov 2025, government may reinstate anytime → always show notification date + source.
- Standards published after **1 Oct 2025** live on a newer BIS portal → crawl must cover both.
- Never claim what GeM/BIS use internally — "no public tool we could find" is our honest phrasing.

---

## 7. Related documents

- `README.md` — the full project idea
- `docs/architecture.md` — how the system is put together
- `docs/tech_stack.md` — the tools and why
- `docs/prototype_plan.md` — the 8-week build schedule
- `docs/demo_script.md` — what we show the judges
