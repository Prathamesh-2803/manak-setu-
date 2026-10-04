"use client";

import { useState } from "react";

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
  stages_ms: Record<string, number>;
};

const SAMPLES = [
  "Bhawan nirman ke liye 12 mm sariya chahiye, 500 tonne, ISI mark wala",
  "53 grade ordinary portland cement for RCC work",
  "Structural plywood for school furniture, compulsory certification",
];

function aspectClass(a: string | null): string {
  const s = (a || "").toLowerCase();
  if (s.includes("product")) return "b-product";
  if (s.includes("test")) return "b-test";
  if (s.includes("code") || s.includes("practice")) return "b-code";
  if (s.includes("terminology")) return "b-term";
  if (s.includes("safety")) return "b-safe";
  return "b-other";
}

function StdCard({ c, main }: { c: Card; main?: boolean }) {
  const st = c.status === "current" ? (
    <span className="badge ok">● current</span>
  ) : (
    <span className="badge bad">● {c.status}{c.replaced_by ? ` → ${c.replaced_by}` : ""}</span>
  );
  const cert = c.certification.mandatory ? (
    <span className="badge warnb">
      ■ {c.certification.scheme ?? "compulsory certification"}
      {c.certification.qco_status ? ` · QCO ${c.certification.qco_status}` : ""}
      {c.certification.implemented_on ? ` · since ${c.certification.implemented_on}` : ""}
    </span>
  ) : (
    <span className="badge b-other">○ no compulsory certification</span>
  );
  return (
    <div className="card std">
      <div className="top">
        <span className="des">{c.designation}{c.year ? `:${c.year}` : ""}</span>
        <span className={`badge ${aspectClass(c.aspect)}`}>{c.role || c.aspect || "Standard"}</span>
        {st}
        {cert}
        <span className="src">{c.source}</span>
      </div>
      <div className="title">{c.title}</div>
      {c.certification.ministry && (
        <div className="meta">Ministry: {c.certification.ministry}</div>
      )}
      {c.iso_equivalent && (
        <div className="meta">ISO/IEC equivalent: {c.iso_equivalent}</div>
      )}
      <div className="scores">
        {c.rerank_score != null ? `relevance ${c.rerank_score.toFixed(2)}` : ""}
        {c.detail_url ? <> · <a href={c.detail_url} target="_blank" rel="noreferrer">BIS record</a></> : null}
      </div>
      {main && c.evidence && <div className="evidence">Matched: {c.evidence}</div>}
    </div>
  );
}

export default function Home() {
  const [q, setQ] = useState(SAMPLES[0]);
  const [out, setOut] = useState<AskOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);

  async function run(query: string) {
    if (!query.trim() || loading) return;
    setLoading(true);
    setErr("");
    setOut(null);
    setCopied(false);
    try {
      const r = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

  function copyClause() {
    if (!out?.clause) return;
    navigator.clipboard.writeText(out.clause).then(
      () => { setCopied(true); setTimeout(() => setCopied(false), 2000); },
      () => setCopied(false)
    );
  }

  return (
    <div className="wrap">
      <div className="hero">
        <h1>Manak Setu <span className="dev">(मानक सेतु)</span></h1>
        <p>AI-powered recommendation engine for applicable Indian Standards — type or paste any tender description, in English, Hindi or Hinglish.</p>
      </div>

      <div className="card">
        <div className="searchrow">
          <textarea value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. 12 mm steel bars for building construction, 500 tonnes, ISI-marked…" />
          <button className="btn" disabled={loading} onClick={() => run(q)}>
            {loading ? "Searching…" : "Find standards"}
          </button>
        </div>
        <div className="chips">
          {SAMPLES.map((s) => (
            <button key={s} className="btn-ghost" onClick={() => { setQ(s); run(s); }}>
              {s.length > 52 ? s.slice(0, 52) + "…" : s}
            </button>
          ))}
        </div>
      </div>

      {loading && <div className="spin">Running decomposer → hybrid search → reranker → knowledge graph → version guard → certification oracle…<br />(first query warms the models, ~1–2 min)</div>}
      {err && <div className="err">Error: {err}</div>}

      {out && (
        <>
          <div className="card understood">
            <div className="lbl">What I understood ({out.language}, via {out.decomposer})</div>
            <p>{out.understood}</p>
            <div className="meta">
              Confidence {(out.confidence * 100).toFixed(0)}% · {out.took_ms} ms
              {Object.entries(out.stages_ms).map(([k, v]) => ` · ${k} ${v}ms`).join("")}
            </div>
            <div className="confbar"><div style={{ width: `${out.confidence * 100}%` }} /></div>
            {out.warnings.map((w, i) => <div className="warn" key={i}>⚠ {w}</div>)}
          </div>

          <div className="sect">Recommended standards ({out.results.length})</div>
          {out.results.map((c) => <StdCard key={c.designation} c={c} main />)}

          {out.allied.length > 0 && (
            <>
              <div className="sect">Allied standards from the knowledge graph ({out.allied.length})</div>
              <div className="grid2">
                {out.allied.map((c) => <StdCard key={c.designation} c={c} />)}
              </div>
            </>
          )}

          {out.clause && (
            <div className="clause">
              <div className="lbl" style={{ color: "#9db9ff" }}>Ready-to-paste tender clause</div>
              <p>{out.clause}</p>
              <button className="copy" onClick={copyClause}>{copied ? "✓ Copied!" : "Copy clause"}</button>
            </div>
          )}
        </>
      )}

      <div className="foot">
        Manak Setu prototype · SIH26108 · every IS number validated against the live database — zero hallucinated standards by design.
      </div>
    </div>
  );
}
