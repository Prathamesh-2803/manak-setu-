# Demo Script — Manak Setu

The exact walkthrough for judges, what's expected on screen at each step, how to recover if something breaks live, and answers to the questions judges always ask.

---

## 1. Pre-demo checklist (run 30 minutes before)

- [ ] `docker compose up` — all 5 containers green (web, api, qdrant, postgres, neo4j)
- [ ] Data loaded: crawl count shows ~23,000 standards; graph node count shows on the dashboard
- [ ] Index warm: hit one known query first so model loading doesn't stall the first request
- [ ] API keys live: Gemini key works (test one call), Groq fallback key present in `.env`
- [ ] Browser: Chrome or Edge (needed for Web Speech API), mic permission granted for `localhost`
- [ ] Language switcher set to English for the intro, Hindi/Hinglish for the wow moment
- [ ] Fallback insurance: 2-minute screen recording + 5 screenshots saved locally (used ONLY if live fails)
- [ ] Linter demo tender already uploaded/ready; foreign-standard example query pre-tested
- [ ] Battery + charger, Wi-Fi confirmed (Gemini/Groq calls need internet)

**Demo length:** aim for **4 minutes live + 2 minutes Q&A prep**. Cut steps, never rush steps.

---

## 2. The main demo: the "sariya" journey (~3 minutes)

**Open with the problem in one line:**
> "A procurement officer must name the right Indian Standard in a tender. There are 23,000 of them, they keep getting revised, and one product needs a family of standards. Let's see an officer who doesn't know any of that."

### Step-by-step with expected screen output

| # | Action | What the officer says / does | Expected on screen | Time |
|---|---|---|---|---|
| 1 | Click the **mic** (or paste Hinglish text) | *"Bhawan nirman ke liye 12 mm sariya chahiye, 500 tonne, ISI mark wala."* | Speech-to-text captures the line; language badge shows **Hinglish** | 15s |
| 2 | **"What I understood" card** appears | Officer glances at it (optionally edits) | Card: `Product: steel reinforcement bars · Size: 12 mm · Qty: 500 t · Use: construction · ISI mark: required` + sub-queries: `product spec / tensile test / sampling / marking & packaging / construction code` | 20s |
| 3 | **Results load** (badge colors) | Officer points at the bundle | Top result = steel bar standard with green **Main** badge; below it: blue **Test method**, gray **Sampling**, orange **Code of practice** — each with a one-line "why included" | 30s |
| 4 | **Version column** | "What if someone quotes an old one?" | Green ticks = *current*; if we demo an outdated example (e.g., IS 9637:1980): red flag **WITHDRAWN → use IS 9637:2024** with link | 20s |
| 5 | **Certification panel** | "Is the ISI mark actually compulsory?" | `Compulsory certification: Yes — per QCO notification dated <date> · Scheme: ISI mark · [source link]` — date and source always visible | 20s |
| 6 | **Clause generator** | "Now give me the tender line" | Officer clicks **Copy clause** → clipboard gets: *"The goods shall conform to IS 1786 (latest revision including amendments) and shall bear the Standard Mark as required under the applicable Quality Control Order."* | 20s |
| 7 | **Guardrail beat** (say it, don't just show it) | "Could this AI invent a standard number?" | Point at the confidence score + "Matched because: scope says…" evidence line. One sentence: *"Every IS number you saw was validated against our database — the LLM can only pick from real rows. Zero fake numbers by design."* | 20s |

### The Hindi check (proves multilingualism)
Switch the language selector to **हिंदी** and re-run a short query → the same bundle renders with Hindi labels. One line: *"Same accuracy, officer's own language."*

---

## 3. The three quick extras (~90 seconds total)

| Feature | One-liner to say | Show this |
|---|---|---|
| **Tender Linter** | "Before publishing, audit the whole tender." | Upload a draft → health report: `2 outdated versions ⚠️ · 1 missing test-method standard · 1 foreign certification without Indian equivalent (GFR risk)` — each clickable |
| **Foreign→Indian mapper** | "GeM's own corrigenda say don't demand foreign standards when Indian ones exist." | Type `IEC 60335` → `IS/IEC 60335 (identical, per BIS equivalence data) · Use for GFR compliance` |
| **Gap analytics** | "This also tells BIS where standards are missing." | Dashboard: `solar water pump controller — 47 searches, no confident match → standards gap` |

---

## 4. If the live demo breaks (recovery ladder)

| Failure | Recovery |
|---|---|
| Gemini rate-limited | Adapter auto-falls back to Groq — *mention it proudly*: "We run on two independent free providers; watch it switch." |
| First query is slow (model load) | Warm-up query was already run in the pre-demo checklist; if cold anyway: "First call loads the model — that's the one-time warm-up you just saw." |
| Mic/speech fails | Paste the Hinglish text instead — same pipeline from step 2 |
| Whole API down | **Do not apologize and stop.** Switch to the 2-minute recorded video, then resume live for Q&A. Say: "Here's a recording of the same flow; I'll show you the parts that don't depend on the network." |
| A standard number looks wrong | The guardrail only shows DB-validated numbers — if a number seems off, open the evidence line ("matched because…") and the official BIS link; if genuinely wrong, say "that's exactly why we show confidence and evidence — below threshold we refuse to answer" |
| Crawl data incomplete | Honest line: "We've indexed ~23k public records; we're requesting an official BIS feed for production" — turns a gap into a roadmap |

**Rule: never fake a result, never hard-code an answer. Judges catch that instantly.**

---

## 5. Anticipated judge questions + answers

| Question | Answer |
|---|---|
| *"How is this different from just asking ChatGPT?"* | ChatGPT can invent an IS number that doesn't exist. We run a **retrieval pipeline over a real database**: knowledge-graph allied standards, version guard, live certification rules, and a guardrail that validates every number. Try asking us for `IS 99999` — we refuse. |
| *"Where did your data come from?"* | Public BIS records — number, title, scope, supersession, ISO equivalence — crawled respectfully (metadata + links only, no copyrighted full texts). For production we'd request an official BIS feed; that's in our pitch. |
| *"What if the certification rule changed yesterday?"* | Every status shows the **notification date and source** beside it, and we label the snapshot "as of <date>". Our QCO watcher is designed to re-check on a schedule. |
| *"What accuracy do you actually have?"* | We evaluate against QCO product→standard pairs — free ground truth — reporting Recall@5, MRR, allied recall, and English-vs-Hindi fairness. *(Fill in real numbers from `eval/results/` before demo day.)* |
| *"Hallucinations?"* | The LLM never chooses what exists — it only structures text and formats output. Every IS number is checked against Postgres; below confidence threshold we say "ask a BIS expert" instead of guessing. Target: **zero fake numbers**. |
| *"Why not Claude / expensive models?"* | Provider-agnostic adapter: Gemini primary, Groq fallback, both free. For a ministry we'd swap in an **open-weight model on-prem** — same interface, data never leaves government servers. |
| *"Won't BIS block your crawling?"* | We crawl public metadata politely and would request an official feed — that's an explicit ask in our pilot plan with BIS. |
| *"Which requirement does this solve?"* | Map to the PS checklist: semantic recommendation, allied standards, latest versions + amendments, mandatory certification, multilingual input — all shown live. |
| *"What's the deployment story?"* | `docker compose up` runs the whole stack anywhere; delivered as REST API + embeddable widget for GeM/CPPP; on-prem option via open-weight LLM. |
| *"Is this actually useful or a hackathon toy?"* | Position honestly: a working prototype with measured accuracy and a pilot plan with BIS/GeM — not a claim to replace the ministry's search on day one. |

---

## 6. Closing line (memorize this)

> "Manak Setu doesn't just search standards — it **understands the tender, walks the standards family tree, checks every version and certification rule, and refuses to show a number that doesn't exist**. From Hinglish speech to a copy-paste tender clause in ten seconds — that's the bridge between what officers say and what the rulebook requires."

---

## 7. Post-demo (if shortlisted)

1. Log the questions we fumbled → add to `prototype_plan.md` risk/answer table
2. Capture evaluator contacts → pilot-plan slide (BIS + GeM)
3. If any number was quoted loosely, correct it in the next round — credibility compounds
