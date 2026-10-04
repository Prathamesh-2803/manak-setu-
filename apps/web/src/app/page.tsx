"use client";

import { useEffect, useRef, useState } from "react";

/* ---------------- types (mirror /api/v1/ask) ---------------- */
type Cert = {
  mandatory: boolean;
  scheme: string | null;
  qco_status: string | null;
  implemented_on: string | null;
  ministry: string | null;
  source: string | null;
};
type Card = {
  id: string | null;
  designation: string;
  year: string | null;
  title: string | null;
  aspect: string | null;
  role: string | null;
  score: number | null;
  rerank_score: number | null;
  status: string;
  replaced_by: string | null;
  certification: Cert;
  iso_equivalent: string | null;
  detail_url: string | null;
  evidence: string | null;
  source: string;
};
type AskOut = {
  query: string;
  understood: string;
  language: string;
  decomposer: string;
  results: Card[];
  allied: Card[];
  clause: string;
  confidence: number;
  warnings: string[];
  took_ms: number;
  cached?: boolean;
  stages_ms: Record<string, number>;
};

/* ---------------- static content ---------------- */
const SAMPLES = [
  "Bhawan nirman ke liye 12 mm sariya chahiye, 500 tonne, ISI mark wala",
  "53 grade ordinary portland cement for RCC work",
  "Structural plywood for school furniture, compulsory certification",
];
const STAGES = [
  { id: "detect", label: "Bhasha", sub: "language", msKey: null as string | null },
  { id: "decompose", label: "Decomposer", sub: "AI extract", msKey: "decompose" },
  { id: "retrieve", label: "Khoj", sub: "hybrid", msKey: "retrieve" },
  { id: "rerank", label: "Rerank", sub: "expert", msKey: "rerank" },
  { id: "graph", label: "Graph", sub: "allied", msKey: "graph" },
  { id: "guard", label: "Guard", sub: "verify + QCO", msKey: "enrich_guard" },
];

/* ---------------- inline SVG icons (no emoji) ---------------- */
const I = {
  mic: (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>),
  go: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>),
  shield: (<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 3l7 3v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6z" /><path d="M9.5 12l2 2 3.5-4" /></svg>),
  link: (<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="12" cy="18" r="2.5" /><path d="M8 7.5l3 8M16 7.5l-3 8M8.5 6h7" /></svg>),
  copy: (<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a1 1 0 0 1 1-1h9" /></svg>),
  check: (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M4 12.5l5 5L20 6.5" /></svg>),
  warn: (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 3L2 20h20zM12 10v4M12 17.5v.5" /></svg>),
  spark: (<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.2 6.6L21 11l-6.8 2.4L12 20l-2.2-6.6L3 11l6.8-2.4z" /></svg>),
};

function aspectClass(a: string | null): string {
  const s = (a || "").toLowerCase();
  if (s.includes("product")) return "b-product";
  if (s.includes("test")) return "b-test";
  if (s.includes("code") || s.includes("practice")) return "b-code";
  if (s.includes("terminology")) return "b-term";
  if (s.includes("safety")) return "b-safe";
  return "b-other";
}

/* ---------------- small components ---------------- */
function Badges({ c }: { c: Card }) {
  return (
    <div className="badges">
      <span className={`badge ${aspectClass(c.aspect)}`}>{c.role || c.aspect || "Standard"}</span>
      {c.status === "current"
        ? <span className="badge ok">{I.shield} current</span>
        : <span className="badge bad">{I.warn} {c.status}{c.replaced_by ? ` → ${c.replaced_by}` : ""}</span>}
      {c.certification.mandatory
        ? <span className="badge warnb">{I.shield} {c.certification.scheme ?? "compulsory certification"}{c.certification.qco_status ? ` · QCO ${c.certification.qco_status}` : ""}{c.certification.implemented_on && String(c.certification.implemented_on).toLowerCase() !== "none" ? ` · ${c.certification.implemented_on}` : ""}</span>
        : <span className="badge dim">no compulsory certification</span>}
      <span className="src">{c.source === "graph" ? "graph" : "retrieval"}</span>
    </div>
  );
}

function StdCard({ c, i }: { c: Card; i: number }) {
  return (
    <div className="std" style={{ animationDelay: `${Math.min(i * 70, 420)}ms` }}>
      <div className="top">
        <span className="des">{c.designation}{c.year ? `:${c.year}` : ""}</span>
      </div>
      <div className="title">{c.title}</div>
      <Badges c={c} />
      <div className="scores">
        {c.rerank_score != null ? `relevance ${c.rerank_score.toFixed(3)}` : ""}
        {c.detail_url ? (<> · <a href={c.detail_url} target="_blank" rel="noreferrer">BIS record</a></>) : null}
      </div>
    </div>
  );
}

function Ring({ v }: { v: number }) {
  const r = 50, circ = 2 * Math.PI * r;
  return (
    <div className="ring">
      <svg width="118" height="118" viewBox="0 0 118 118">
        <circle cx="59" cy="59" r={r} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth="10" />
        <circle cx="59" cy="59" r={r} fill="none" stroke="url(#g1)" strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={circ * (1 - v)} style={{ transition: "stroke-dashoffset 1s cubic-bezier(.2,.8,.2,1)" }} />
        <defs><linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ff9933" /><stop offset="100%" stopColor="#34c77b" />
        </linearGradient></defs>
      </svg>
      <div className="pct"><b>{Math.round(v * 100)}%</b><span>match</span></div>
    </div>
  );
}

function Chakra() {
  const spokes = Array.from({ length: 12 }, (_, i) => (i * 30 * Math.PI) / 180);
  return (
    <svg className="brandmark" viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <circle cx="24" cy="24" r="20" stroke="#ff9933" strokeWidth="3" />
      <circle cx="24" cy="24" r="4.5" fill="#f2b705" />
      {spokes.map((a, i) => (
        <line key={i} x1="24" y1="24" x2={24 + 16 * Math.cos(a)} y2={24 + 16 * Math.sin(a)} stroke="#9dbcff" strokeWidth="1.6" />
      ))}
    </svg>
  );
}

/* ---------------- main page ---------------- */
export default function Home() {
  const [q, setQ] = useState(SAMPLES[0]);
  const [out, setOut] = useState<AskOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);
  const [listening, setListening] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const recRef = useRef<{ stop: () => void } | null>(null);
  const t0Ref = useRef(0);

  useEffect(() => {
    if (!loading) return;
    t0Ref.current = Date.now();
    const t = setInterval(() => setElapsed((Date.now() - t0Ref.current) / 1000), 500);
    return () => clearInterval(t);
  }, [loading]);

  async function run(query: string) {
    if (!query.trim() || loading) return;
    setLoading(true); setErr(""); setOut(null); setCopied(false); setElapsed(0);
    try {
      const r = await fetch("/api/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || `request failed (${r.status})`);
      setOut(data);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function toggleMic() {
    const SR = (window as unknown as { webkitSpeechRecognition?: new () => any; SpeechRecognition?: new () => any });
    const Impl = SR.webkitSpeechRecognition || SR.SpeechRecognition;
    if (!Impl) { setErr("Voice input needs Chrome — please type instead."); return; }
    if (listening) { recRef.current?.stop(); setListening(false); return; }
    const rec = new Impl();
    rec.lang = "hi-IN"; rec.interimResults = false; rec.maxAlternatives = 1;
    rec.onresult = (e: { results: { transcript: string }[][] }) => setQ(e.results[0][0].transcript);
    rec.onend = () => setListening(false);
    rec.onerror = () => { setListening(false); setErr("Mic failed — please type instead."); };
    recRef.current = rec; setListening(true);
    try { (rec as { start: () => void }).start(); } catch { setListening(false); }
  }

  function copyClause() {
    if (!out?.clause) return;
    navigator.clipboard.writeText(out.clause).then(
      () => { setCopied(true); setTimeout(() => setCopied(false), 2200); },
      () => setErr("Copy blocked by browser — select the text manually.")
    );
  }

  const activeStage = Math.min(STAGES.length - 1, Math.floor(elapsed / 6));
  const top = out?.results?.[0];

  return (
    <div className="wrap">
      <div className="aurora" aria-hidden="true"><span className="a1" /><span className="a2" /><span className="a3" /></div>

      <header className="topbar">
        <Chakra />
        <div className="brand">
          <h1>Manak Setu <span className="hi">मानक सेतु</span></h1>
          <small>Standards Bridge · SIH 2026</small>
        </div>
        <div className="pills">
          <span className="pill hot">SIH26108 · LIVE PROTOTYPE</span>
          <span className="pill">BIS · GeM ready</span>
        </div>
      </header>

      <section className="hero">
        <span className="kicker">AI recommendation engine for Indian Standards</span>
        <h2><span className="hi">टेंडर लिखो,</span> <span className="grad">standards auto-find.</span></h2>
        <p>Type or speak any procurement need — in English, Hindi or Hinglish — and get a verified bundle of standards, versions and certification duties. Every IS number validated against the live database.</p>
        <div className="stats">
          <div className="stat"><b className="saff">17,135</b><span>standards indexed</span></div>
          <div className="stat"><b className="grn">526</b><span>QCO tracked</span></div>
          <div className="stat"><b className="blu">84,274</b><span>graph links</span></div>
          <div className="stat"><b className="gld">0</b><span>fake IS numbers</span></div>
        </div>
      </section>

      <section className="console">
        <div className="cbox">
          <textarea value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. 12 mm steel bars for building construction, 500 tonnes, ISI-marked…" aria-label="Describe what you want to procure" />
          <button className={`iconbtn${listening ? " live" : ""}`} onClick={toggleMic} title="Voice input (Hindi/English)" aria-label="Voice input">{I.mic}</button>
          <button className="cta" disabled={loading} onClick={() => run(q)}>{loading ? "Khoj…" : <>Find {I.go}</>}</button>
        </div>
        <div className="chips">
          {SAMPLES.map((s) => (
            <button key={s} className="chip" onClick={() => { setQ(s); run(s); }}>
              {s.length > 56 ? s.slice(0, 56) + "…" : s}
            </button>
          ))}
        </div>
        {err && <div className="err">{err}</div>}
      </section>

      {(loading || out) && (
        <div className="pipe" role="status" aria-label="AI pipeline progress">
          {STAGES.map((s, i) => {
            const done = !!out;
            const cls = done ? "done" : i < activeStage ? "done" : i === activeStage ? "active" : "";
            const ms = out?.stages_ms?.[s.msKey ?? ""];
            return (
              <div className={`pstage ${cls}`} key={s.id}>
                <div className="dot">{done ? I.check : <span style={{ fontSize: 15, fontWeight: 800 }}>{i + 1}</span>}</div>
                <div className="lbl">{s.label}</div>
                <div className="ms">{s.sub}{ms != null ? ` · ${ms}ms` : ""}</div>
              </div>
            );
          })}
        </div>
      )}

      {loading && !out && (
        <div className="spin">AI pipeline running — decomposer → hybrid search → reranker → knowledge graph → guard → oracle…<br />
          <span style={{ fontSize: 12.5 }}>first query warms the models ({Math.round(elapsed)}s)</span>
          <div className="bar"><div /></div>
        </div>
      )}

      {out && (
        <>
          <div className="uread">
            <span className="ai">{I.spark} AI interpretation · {out.language} · via {out.decomposer}</span>
            <p>{out.understood}</p>
            <div className="confrow">
              <div className="confbar"><div style={{ width: `${out.confidence * 100}%` }} /></div>
              <span className="confnum">{Math.round(out.confidence * 100)}%</span>
            </div>
            <div className="meta">
              {out.took_ms} ms end-to-end · {out.cached ? "served from cache" : "computed live"} · every IS number verified in DB
            </div>
            {out.warnings.map((w, i) => <div className="warn" key={i}>{w}</div>)}
          </div>

          {top && (
            <>
              <div className="sect"><h3>Top recommendation</h3><div className="rule" /><span className="count">rank 1 of {out.results.length}</span></div>
              <div className="hero-pick">
                <Ring v={out.confidence} />
                <div>
                  <span className="crown">Best match · ISI track</span>
                  <div className="des">{top.designation}{top.year ? `:${top.year}` : ""}</div>
                  <div className="title">{top.title}</div>
                  <Badges c={top} />
                  {top.certification.ministry && <div className="meta">Ministry: {top.certification.ministry}</div>}
                  {top.iso_equivalent && <div className="meta">ISO/IEC equivalent: {top.iso_equivalent}</div>}
                </div>
              </div>
            </>
          )}

          {out.results.length > 1 && (
            <>
              <div className="sect"><h3>Also recommended</h3><div className="rule" /><span className="count">{out.results.length - 1} more</span></div>
              <div className="grid">
                {out.results.slice(1).map((c, i) => <StdCard key={c.designation} c={c} i={i} />)}
              </div>
            </>
          )}

          {out.allied.length > 0 && (
            <>
              <div className="sect"><h3>Allied standards · knowledge graph</h3><div className="rule" /><span className="count">{out.allied.length} linked</span></div>
              <div className="grid">
                {out.allied.map((c, i) => <StdCard key={c.designation} c={c} i={i} />)}
              </div>
            </>
          )}

          {out.clause && (
            <div className="clause">
              <span className="ai" style={{ color: "#8fe6d7" }}>{I.spark} Ready-to-paste tender clause</span>
              <p>“{out.clause}”</p>
              <button className="copy" onClick={copyClause}>{copied ? <>{I.check} Copied!</> : <>{I.copy} Copy clause</>}</button>
            </div>
          )}
        </>
      )}

      <footer className="foot">
        Manak Setu prototype · Smart India Hackathon 2026 · Problem SIH26108<br />
        <span className="zero">Zero hallucinated standard numbers — guaranteed by design.</span>
      </footer>
    </div>
  );
}
