# Tech Stack — Manak Setu Prototype

The final tools we use, what each does in plain words, what it costs, and — importantly — what we deliberately dropped (Claude, government cloud) and why.

**Bottom line: the entire prototype costs ₹0.** Free-tier APIs + open-source software running locally in Docker.

---

## 1. The stack at a glance

| # | Layer | Tool | What it does in plain words | Cost |
|---|---|---|---|---|
| 1 | **Frontend** | Next.js + Tailwind CSS + Web Speech API (mic) | The web pages: input box, file upload, results screen with badges, voice button, EN/HI switcher. Browser's built-in speech recognition handles Hindi (`hi-IN`) — no extra service needed. | Free |
| 2 | **Backend** | FastAPI (Python 3.12 venv) | The engine room: receives requests and runs the 7 pipeline stages. Async, so no Celery/Redis needed at prototype scale (decision D7). | Free |
| 3 | **Document reading** | PyMuPDF (Docling if needed) | Pulls text out of uploaded tender PDFs and Word files. Scanned-PDF OCR is deferred. | Free |
| 4 | **Language layer** | Gemini API (translation + Hinglish normalization) + `glossary.yaml` + browser Web Speech API | Detects the language, translates to English, maps local product words ("सरिया / sariya" → steel reinforcement bar). Voice = free browser API. | Free |
| 5 | **Embeddings** | **BGE-M3** (runs locally via Python) | Turns every standard's title+scope and every query into "meaning numbers" (vectors). Handles 100+ languages; one model supports dense retrieval. | Free, local |
| 6 | **Keyword search** | **BM25** (via `bm25s`) | The exact-word half of hybrid search — catches codes like "IS 456" or "12 mm" that meaning-search blurs. | Free, local |
| 7 | **Vector store** | **Qdrant** (Docker container) | Stores dense + sparse vectors and runs hybrid fusion (both searches merged) in a single query. | Free, container |
| 8 | **Reranker** | **bge-reranker-v2-m3** (runs locally, CPU) | The "expert second read": reads the query together with each of the top ~30 candidates and re-sorts them by true relevance. | Free, local |
| 9 | **Graph database** | **Neo4j Community** (Docker; NetworkX fallback) | The standards family tree: edges for *refers-to, superseded-by, equivalent-to ISO/IEC*. Powers "allied standards" with role badges. | Free, container |
| 10 | **Records + rules** | **PostgreSQL** (Docker) | Standards metadata, supersession chains, the QCO/certification rules table, glossary, feedback clicks, eval results, and the LLM response cache. | Free, container |
| 11 | **LLM** | **Gemini Flash (primary) → Groq (fallback)** behind one adapter | Four jobs only: (a) Spec Decomposer JSON extraction, (b) translation/Hinglish normalization, (c) clause writing + explanations, (d) Tender Linter verdicts. Never used to invent standards. | Free tier, no card |
| 12 | **Rules store** | `qco_snapshot.yaml` (dated) loaded into Postgres | The Certification Oracle's data: which products need which certification, per which notification, with its date. Updated by hand/scheduled job for the prototype. | Free |
| 13 | **Evaluation** | Custom benchmark script + JSON logs | Scores Recall@5, MRR, allied recall, EN-vs-HI accuracy, and counts fake-standard outputs (target 0). Langfuse tracing optional later. | Free |
| 14 | **Deployment** | **Docker Compose** | One `docker compose up` starts web + api + qdrant + postgres + neo4j on any laptop. Portable to any server later. | Free |

---

## 2. The LLM setup (this is where Claude was replaced)

### What we chose

```
Primary:  Gemini Flash (Google AI Studio free tier — no credit card)
          model: gemini-3.x-flash / gemini-2.5-flash (whichever the free tier serves)
Fallback: Groq — openai/gpt-oss-120b or qwen3.6-27b (free tier — no credit card)
Both wrapped in ONE adapter class:  llm.generate(prompt, json_mode=...)
```

### Why not Claude

| | Claude API | Gemini + Groq |
|---|---|---|
| Cost | Paid per token — real money for a 6-member student team | Both free tiers, no credit card |
| Fallback | None (one provider) | Two independent free providers |
| Quality for our tasks (JSON extraction, translation, short clause writing) | Excellent | Flash-class models handle these fine |

**The adapter matters more than the provider.** Because everything goes through `services/api/llm/`, we can later swap in an open-weight model (vLLM) for the ministry's on-premise requirement — that's a selling point for judges, not a hack.

### Free-tier realities (know these before demo day)

| Provider | Free tier facts | Our mitigation |
|---|---|---|
| **Gemini** | Flash models are free but Google **no longer publishes the exact daily limits** (they're shown per-project in AI Studio). Rate limits hit unpredictably under load. | Keep prompts short; **cache every decomposition in Postgres** (same tender text → never re-call); auto-fallback on 429/error. |
| **Groq** | 30 requests/min, ~1,000 requests/day, **8,000 tokens/min, 200,000 tokens/day per model** on free tier. Long prompts can eat a whole minute's budget. Llama models are no longer free (Aug 2026) — use `gpt-oss-120b` or Qwen. | Use only for short fallback calls (decomposition, one-line translations); never bulk jobs. |

### The four jobs the LLM is allowed to do

1. **Spec Decomposer** — tender text in → strict JSON out (product, material, grade, size, use, tests) + 3–5 sub-queries. Validated with Pydantic; retry once on malformed JSON.
2. **Language normalization** — Hinglish/Devanagari → English query (plus glossary lookup).
3. **Clause + explanation writing** — formats the final tender sentence and the "matched because…" line from *retrieved* facts only.
4. **Tender Linter verdicts** — classifies each detected clause (OK / outdated / missing / foreign-without-Indian-equivalent).

**The LLM never chooses which standards exist.** That's the guardrail: every IS number shown is validated against Postgres before display.

---

## 3. Retrieval internals (why "hybrid")

```
Query ──┬── BGE-M3 dense vector ──────► Qdrant ──┐
        └── BM25 sparse (keyword) ────► Qdrant ──┴─► fusion (top 50)
                                                        │
                              bge-reranker-v2-m3 ◄──────┘
                                        │
                                        ▼
                              ordered top 5–10 ──► graph expansion
```

- **Dense only** misses exact codes ("IS 456", "IP65").
- **BM25 only** misses meaning ("strong rods" ≠ "deformed bars").
- **Reranker** is the expert that actually *reads* query + candidate together — cheap on CPU because it only scores ~30 pairs per request.
- Index **scope clause + title** of each standard (scope is what a standard actually covers), chunked for precision.

---

## 4. What we dropped, and why

| Dropped | Original plan | Why dropped (prototype) | When it returns |
|---|---|---|---|
| **Claude API** | LLM brain | Costs money → **Gemini primary + Groq fallback** (decision D1) | Never for prototype; on-prem vLLM is the finale story |
| **Government cloud** | Deployment target | Cost + approval delays → **Docker Compose** (decision D2) | Pitch as "containerized, cloud-ready" |
| **Celery + Redis** | Async job queue | Jobs are fast enough with plain async; 2 fewer containers (decision D7) | If PDF parsing/Linter gets slow |
| **Bhashini API** | Translation/speech | Needs government API registration → **Gemini + Web Speech API** (decisions D8, D9) | Adding more languages later |
| **IndicTrans2** | Local translation model | Heavy install, CPU cost → Gemini covers EN↔HI | If we must run offline/no-API |
| **OCR (Tesseract/PaddleOCR)** | Scanned PDFs | Time sink → text PDFs only | Post-prototype |
| **vLLM open models** | On-prem LLM option | No GPU headroom now → adapter keeps the door open | Finale "deployment fit" slide |
| **Langfuse** | Tracing/observability | Nice-to-have → JSON logs first | If debugging needs it |
| **Milvus** | Vector DB alternative | Qdrant does hybrid just as easily with lighter footprint | Never (unless scale demands) |

---

## 5. Hardware notes (this machine)

- **GPU: AMD Radeon RX 6500M (4 GB)** — AMD GPUs lack reliable PyTorch support on Windows (ROCm is Linux-first, 4 GB is tight anyway).
  - **Plan A:** try ROCm under WSL2 to speed up indexing.
  - **Plan B (the schedule we plan around):** index all ~23,000 scopes as an **overnight CPU batch job**. Short scope texts on CPU: a few hours — perfectly fine.
  - **The demo never needs the GPU:** embedding one query + reranking 30 pairs on CPU ≈ 1–2 seconds.
- **Python 3.14 is installed, but use Python 3.12 for the venv** — torch/sentence-transformers wheels may not exist for 3.14 yet.
- **Docker Desktop must be installed first** (with WSL2 backend) — it's a Day-1 task.

---

## 6. Environment variables (`.env`)

```bash
GEMINI_API_KEY=...        # Google AI Studio, free
GROQ_API_KEY=...          # console.groq.com, free
DATABASE_URL=postgresql://manak:manak@postgres:5432/manak_setu
QDRANT_URL=http://qdrant:6333
NEO4J_URL=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...        # generated, not committed
CONFIDENCE_THRESHOLD=0.65 # below this -> "ask a BIS expert"
```

---

## 7. Cost summary

| Item | Cost |
|---|---|
| Gemini API (free tier) | ₹0 |
| Groq API (free tier) | ₹0 |
| BGE-M3, bge-reranker-v2-m3, Qdrant, Neo4j, Postgres, FastAPI, Next.js | ₹0 (open source) |
| Docker Desktop | ₹0 (personal use) |
| Government cloud | ₹0 (not used — decision D2) |
| **Total** | **₹0** |
