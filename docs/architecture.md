# Architecture — Manak Setu

How the system is put together: the live request path (what happens when an officer asks something), the offline data pipeline (how the data gets in), the data stores, and the repo layout.

---

## 1. The big picture (hospital metaphor)

| Hospital step | Manak Setu stage |
|---|---|
| Patient arrives with a complaint | Officer submits tender text (typed, spoken, or uploaded) |
| Triage nurse breaks the complaint into parts | **Spec Decomposer** extracts structured facts + sub-queries |
| Specialists are searched | **Hybrid retrieval** (BGE-M3 meaning + BM25 keywords) |
| Referral map shows which other specialists are needed | **Knowledge Graph** expansion with role labels |
| Pharmacy checks medicines aren't expired | **Version Guard** (withdrawn → successor) |
| Permits are verified | **Certification Oracle** (QCO status + scheme + source) |
| Doctor writes an evidenced report | **Guardrail + explainable output** (validated IS numbers, confidence, clause) |

---

## 2. Live request path (7-stage pipeline)

What happens the moment an officer submits a query. This is the diagram for the PPT.

```mermaid
flowchart LR
    subgraph INPUT["Officer"]
        U1["Type EN/HI/Hinglish"]
        U2["Mic - Web Speech API"]
        U3["Upload tender PDF"]
    end

    subgraph WEB["Next.js Frontend"]
        UI["Results UI:<br/>role badges, red/green status,<br/>clause copy, feedback buttons"]
    end

    subgraph API["FastAPI - the 7 stages"]
        S1["1. Language Layer<br/>detect language + translate (Gemini)<br/>glossary: sariya = rebar"]
        S2["2. Spec Decomposer<br/>Gemini -> JSON facts:<br/>product, grade, size, tests<br/>+ sub-queries"]
        S3["3. Hybrid Retrieval<br/>Qdrant: dense BGE-M3<br/>+ sparse BM25"]
        S4["4. Reranker<br/>bge-reranker-v2-m3<br/>re-sorts top 30"]
        S5["5. Graph Expansion<br/>Neo4j: allies + role badges"]
        S6["6. Version Guard<br/>withdrawn -> successor,<br/>amendments listed"]
        S7["7. Certification Oracle<br/>QCO status + scheme<br/>+ source notification"]
        G["Guardrail + Clause Gen<br/>every IS number validated<br/>confidence gate + clause text"]
        L["Tender Linter<br/>regex + Gemini find IS/foreign refs<br/>-> health report"]
        M["Foreign Mapper<br/>IEC/EN/ISO -> IS equivalent"]
    end

    subgraph STORES["Data stores"]
        Q[("Qdrant<br/>dense + sparse vectors")]
        N[("Neo4j<br/>standards family tree")]
        P[("Postgres<br/>IS records, QCO rules,<br/>feedback, eval, LLM cache")]
    end

    subgraph LLM["LLM adapter"]
        GEM["Gemini Flash - primary"]
        GRQ["Groq gpt-oss-120b - fallback"]
    end

    UI --> S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> G --> UI
    U1 --> WEB
    U2 --> WEB
    U3 --> WEB
    U3 --> L --> UI
    S1 --> GEM
    S2 --> GEM
    GEM -. "rate limit / error" .-> GRQ
    S2 -. "cache decomposition" .-> P
    S3 <--> Q
    S5 <--> N
    S6 <--> P
    S7 <--> P
    M <--> P
    G -. "IS must exist in DB" .-> P
```

### Stage-by-stage walkthrough

| # | Stage | Input | Output | Tool(s) |
|---|---|---|---|---|
| 1 | **Language layer** | Raw text/speech in any supported language | Normalized English query + detected language | Gemini (translate/normalize), vernacular glossary (`glossary.yaml`), browser Web Speech API |
| 2 | **Spec decomposer** | Normalized tender text | Structured JSON: product, material, grade, size, quantity, use-case, tests + 3–5 sub-queries | Gemini with JSON-mode prompt (cached in Postgres) |
| 3 | **Hybrid retrieval** | Sub-queries | Top ~50 candidates (fusion of dense + sparse) | Qdrant, BGE-M3 dense vectors, BM25 sparse vectors |
| 4 | **Reranker** | Query + top 30 candidates | Ordered top 5–10 | bge-reranker-v2-m3 (local, CPU) |
| 5 | **Graph expansion** | Top hits | Allied standards + role badges (Main / Test method / Sampling / Terminology / Safety / Installation / Raw material / Marking & packaging) | Neo4j traversal; roles pre-labelled offline |
| 6 | **Version guard** | Each candidate IS | Current-version status; withdrawn → red flag + successor; amendment list | Postgres records (supersession chain) |
| 7 | **Certification oracle** | Product / IS | Mandatory? scheme (ISI/CRS/Hallmarking) + notification date + source | Postgres QCO table (dated snapshot) |
| 8 | **Guardrail + output** | Everything above | Validated results (only IS numbers that exist in DB), confidence score, evidence text ("matched because…"), ready-to-paste clause | Postgres validation + Gemini clause writing; below confidence threshold → "ask a BIS expert" |

**Side modules (reuse the same engine):**
- **Tender Linter** — regex + LLM detect every IS/foreign-standard mention in an uploaded tender, then check each against Version Guard + Certification Oracle → health report (missing / outdated / foreign-only / contradiction).
- **Foreign mapper** — look up IEC/EN/ISO reference → IS equivalent from BIS equivalence field; unofficial matches labelled "suggested, needs expert review".
- **Gap analytics** — every query below the confidence threshold is logged; simple dashboard counts them per product category.

---

## 3. Offline data pipeline (Week 1–2, then re-runs)

```mermaid
flowchart LR
    B["BIS public pages<br/>(Know Your Standard +<br/>classification lists,<br/>old + post-2025 portals)"] --> C["Crawler<br/>httpx + BeautifulSoup,<br/>rate-limited, robots-respectful"]
    C --> DB[("Postgres<br/>~23,000 IS records<br/>QCO snapshot<br/>glossary.yaml")]
    DB --> IDX["Indexer<br/>scope text -> BGE-M3 dense<br/>+ BM25 sparse<br/>(overnight CPU batch)"]
    IDX --> QD[("Qdrant")]
    DB --> GL["Graph loader<br/>edges: refers-to, superseded-by,<br/>equivalent-to ISO/IEC"]
    GL --> NEO[("Neo4j")]
    DB --> RL["Role labeler<br/>BIS category field -><br/>Product/Test/Sampling/Safety badge"]
    RL --> NEO
    DB --> EV["Eval builder<br/>QCO product-standard pairs<br/>= free answer key"]
    EV --> SC["Scorer<br/>Recall@5, MRR, allied recall,<br/>EN vs HI, fake-IS count = 0"]
```

**Key insight:** the BIS classification lists expose a category field (*Product Specification / Code of Practice / Methods of tests / Terminology / Dimensions / System Standard / Safety Standard*) — that is our role-badge source of truth, no LLM guessing required.

---

## 4. Data stores — who owns what

| Store | Holds | Why this one |
|---|---|---|
| **Qdrant** (Docker) | Dense vectors (BGE-M3) + sparse vectors (BM25) for every standard's title + scope | Native hybrid search (dense + sparse fusion) in one query |
| **Neo4j** (Docker) | Nodes = IS records; edges = *refers-to, referred-in, supersedes/superseded-by, equivalent-to ISO/IEC, committee-of* | Multi-hop traversal for "allied standards" — the exact thing plain vector search can't do. Fallback: NetworkX in-process graph if Neo4j is too heavy. |
| **Postgres** (Docker) | Standards metadata (number, title, status, revision, supersession chain), QCO/certification rules table, glossary, user feedback, eval results, **LLM response cache** | Relational facts + audit trail; one row per IS keeps guardrail validation trivial (`SELECT EXISTS`) |
| File system (`data/`) | Raw crawl JSONL, `qco_snapshot.yaml`, `glossary.yaml` | Version-controllable source of truth, reloadable into Postgres |

---

## 5. Request lifecycle — the "sariya" example, end to end

1. Mic captures → Web Speech API (`hi-IN`) returns Hinglish text: *"Bhawan nirman ke liye 12 mm sariya chahiye…"*
2. Language layer: language-ID says Hinglish → Gemini normalizes → English + glossary hits `sariya → steel reinforcement bar`
3. Decomposer returns: `{product: "reinforcement bar", size: "12 mm", qty: "500 t", use: "construction", needs_isi: true}` + sub-queries: `[product spec, tensile test method, sampling, marking & packaging, construction code]`
4. Qdrant returns 50 fused candidates → reranker orders them → top hit = steel bar standard
5. Neo4j walks edges → 4 allies, each with a role badge
6. Version Guard: all 5 = current (or red flag with successor)
7. Certification Oracle: QCO row → "ISI mark mandatory, per notification dated YYYY-MM-DD"
8. Guardrail: all 5 IS numbers exist in Postgres ✓, confidence 0.91 → Gemini writes the clause → UI shows bundle + copy button
9. User clicks 👍/👎 → feedback row in Postgres; below-threshold queries → gap-analytics log

---

## 6. Repo layout

```
Manak Setu/
├── README.md                     # the entire project idea
├── docs/
│   ├── project_context.md        # SIH facts, decisions, team, environment
│   ├── architecture.md           # this file
│   ├── tech_stack.md             # tools + cost + rationale
│   ├── prototype_plan.md         # scope + schedule + risks
│   └── demo_script.md            # judge walkthrough
├── docker-compose.yml            # web + api + qdrant + postgres + neo4j
├── .env.example                  # GEMINI_API_KEY, GROQ_API_KEY, DB URLs
├── apps/
│   └── web/                      # Next.js frontend
│       ├── app/                  # pages (home, results, linter, dashboard)
│       ├── components/           # InputBox, ResultCard, Badge, ClauseCopy…
│       └── lib/                  # API client, i18n strings (en/hi)
├── services/
│   └── api/                      # FastAPI backend
│       ├── main.py               # app entry
│       ├── routers/              # recommend, linter, feedback, eval
│       ├── stages/               # language, decompose, retrieve, rerank,
│       │                         # graph, version, certification, guardrail
│       ├── llm/                  # adapter: gemini.py, groq.py, prompts/
│       └── db/                   # Postgres access, Neo4j client, Qdrant client
├── pipeline/                     # offline jobs (Python scripts)
│   ├── crawl_bis.py              # crawler
│   ├── load_graph.py             # Postgres -> Neo4j
│   ├── index_vectors.py          # BGE-M3 + BM25 -> Qdrant (batch)
│   ├── label_roles.py            # category -> role badges
│   └── build_eval.py             # QCO pairs -> benchmark
├── data/
│   ├── raw/                      # crawl JSONL
│   ├── qco_snapshot.yaml         # certification rules (dated)
│   └── glossary.yaml             # vernacular product words
├── eval/
│   ├── benchmark.jsonl           # product -> expected IS pairs
│   └── results/                  # score reports (numbers for PPT)
└── scripts/
    └── dev.sh / dev.ps1          # docker compose up helpers
```

---

## 7. Deployment

- **Prototype:** `docker compose up` starts five containers — `web` (Next.js), `api` (FastAPI), `qdrant`, `postgres`, `neo4j` — on any laptop. Embedding/reranking run inside `api` (local Python models, no external calls).
- **LLM calls** are the only external dependency (Gemini primary, Groq fallback) — both behind one adapter interface so an open-weight model (vLLM) can replace them later for on-premise deployment, as the ministry would require.
- **Future (not in prototype):** embeddable widget for GeM/CPPP, Word/PDF add-in, official BIS data feed, live QCO watcher.
