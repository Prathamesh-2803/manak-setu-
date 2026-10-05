"use client";

import { useEffect, useRef, useState } from "react";

/* ---------------- types (mirror /api/v1/*) ---------------- */
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
type LintFinding = {
  kind: string;
  severity: string;
  title: string;
  detail: string;
  suggestion: string | null;
};
type LintOut = {
  score: number;
  verdict: string;
  findings: LintFinding[];
  checked_is: string[];
  took_ms: number;
};
type MapHit = {
  designation: string;
  year: string | null;
  title: string | null;
  iso_equivalent: string | null;
  certification: string | null;
};
type MapOut = {
  query: string;
  matches: MapHit[];
  note: string | null;
};
type StatsOut = {
  standards: number;
  qco_tracked: number;
  graph_nodes: number;
  graph_edges: number;
};

/* ---------------- static content ---------------- */
const SAMPLES = [
  "Bhawan nirman ke liye 12 mm sariya chahiye, 500 tonne, ISI mark wala",
  "53 grade ordinary portland cement for RCC work",
  "Structural plywood for school furniture, compulsory certification",
];
const SAMPLE_TENDER = `Supply of 500 tonnes of 12mm steel reinforcement bars for building construction. The goods shall conform to IS 1139:1966 and shall be ISI marked. All site electrical panels shall comply with IEC 60335. Delivery within 60 days.`;
const STAGES = [
  { id: "detect", label: "Language", msKey: null as string | null },
  { id: "decompose", label: "Requirements", msKey: "decompose" },
  { id: "retrieve", label: "Search", msKey: "retrieve" },
  { id: "rerank", label: "Ranking", msKey: "rerank" },
  { id: "graph", label: "Related", msKey: "graph" },
  { id: "guard", label: "Verification", msKey: "enrich_guard" },
];
const LANG_NAMES: Record<string, string> = { "hi-IN": "Hindi", "mr-IN": "Marathi", "en-IN": "English" };

/* ---------------- inline SVG icons ---------------- */
const I = {
  mic: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>),
  go: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>),
  shield: (<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M12 3l7 3v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6z" /><path d="M9.5 12l2 2 3.5-4" /></svg>),
  copy: (<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a1 1 0 0 1 1-1h9" /></svg>),
  check: (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"><path d="M4 12.5l5 5L20 6.5" /></svg>),
  warn: (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M12 3L2 20h20zM12 10v4M12 17.5v.5" /></svg>),
};

function Stamps({ c }: { c: Card }) {
  return (
    <div className="stamps">
      {c.status === "current"
        ? <span className="stamp ok">{I.shield} Current</span>
        : <span className="stamp bad">{I.warn} Withdrawn{c.replaced_by ? ` — use ${c.replaced_by}` : ""}</span>}
      {c.certification.mandatory
        ? <span className="stamp warnb">{I.shield} ISI mandatory{c.certification.qco_status ? ` · QCO ${c.certification.qco_status}` : ""}</span>
        : <span className="stamp dim">No compulsory certification</span>}
      <span className="src">{c.role || c.aspect || "Standard"}</span>
    </div>
  );
}

function Entry({ c, main }: { c: Card; main?: boolean }) {
  const cls = main ? "heroentry" : "entry";
  return (
    <div className={cls}>
      {main && <div className="rank">Main specification</div>}
      <div className="des">{c.designation}{c.year ? `:${c.year}` : ""}</div>
      <div className="title">{c.title}</div>
      <Stamps c={c} />
      {c.certification.ministry && <div className="meta">Ministry: {c.certification.ministry}</div>}
      {c.certification.mandatory && c.certification.source && <div className="meta">Source: {c.certification.source}</div>}
      {c.iso_equivalent && <div className="meta">ISO/IEC equivalent: {c.iso_equivalent}</div>}
      <div className="scores">
        {c.rerank_score != null ? `Relevance score ${c.rerank_score.toFixed(3)}` : ""}
        {c.detail_url ? (<> · <a href={c.detail_url} target="_blank" rel="noreferrer">Open BIS record</a></>) : null}
      </div>
      {main && c.evidence && <div className="evidence">Why this matches: {c.evidence}</div>}
    </div>
  );
}

function Mark() {
  return (
    <svg className="brandmark" viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <circle cx="24" cy="24" r="19" stroke="#c2410c" strokeWidth="3.5" />
      <circle cx="24" cy="24" r="4" fill="#1b2432" />
      {Array.from({ length: 12 }, (_, i) => {
        const a = (i * 30 * Math.PI) / 180;
        return <line key={i} x1="24" y1="24" x2={24 + 14 * Math.cos(a)} y2={24 + 14 * Math.sin(a)} stroke="#1b2432" strokeWidth="1.6" />;
      })}
    </svg>
  );
}

/* ---------------- main page ---------------- */
export default function Home() {
  const [q, setQ] = useState("");
  const [voiced, setVoiced] = useState<string | null>(null);
  const [out, setOut] = useState<AskOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);
  const [listening, setListening] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [mode, setMode] = useState<"find" | "audit">("find");
  const [tender, setTender] = useState(SAMPLE_TENDER);
  const [lintOut, setLintOut] = useState<LintOut | null>(null);
  const [lintLoading, setLintLoading] = useState(false);
  const [lintErr, setLintErr] = useState("");
  const [stats, setStats] = useState<StatsOut | null>(null);
  const [mapQ, setMapQ] = useState("IEC 60335");
  const [mapOut, setMapOut] = useState<MapOut | null>(null);
  const [mapLoading, setMapLoading] = useState(false);
  const [copiedReport, setCopiedReport] = useState(false);
  const [micLang, setMicLang] = useState<"hi-IN" | "mr-IN" | "en-IN">("hi-IN");
  const fileRef = useRef<HTMLInputElement | null>(null);
  const recRef = useRef<{ stop: () => void } | null>(null);
  const t0Ref = useRef(0);

  useEffect(() => {
    if (!loading) return;
    t0Ref.current = Date.now();
    const t = setInterval(() => setElapsed((Date.now() - t0Ref.current) / 1000), 500);
    return () => clearInterval(t);
  }, [loading]);

  useEffect(() => {
    fetch("/api/stats").then((r) => r.json()).then((d) => {
      if (d && typeof d.standards === "number") setStats(d);
    }).catch(() => {});
  }, []);

  async function run(query: string) {
    if (!query.trim() || loading) return;
    setLoading(true); setErr(""); setOut(null); setCopied(false); setElapsed(0);
    try {
      const r = await fetch("/api/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, language_hint: voiced }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || `Search failed (error ${r.status}). Please try again.`);
      setOut(data);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function toggleMic() {
    const SR = (window as unknown as { webkitSpeechRecognition?: new () => any; SpeechRecognition?: new () => any });
    const Impl = SR.webkitSpeechRecognition || SR.SpeechRecognition;
    if (!Impl) { setErr("Voice input needs the Chrome browser. Please type instead."); return; }
    if (listening) { recRef.current?.stop(); setListening(false); return; }
    const rec = new Impl();
    rec.lang = micLang; rec.interimResults = false; rec.maxAlternatives = 1;
    rec.onresult = (e: { results: { transcript: string }[][] }) => { setQ(e.results[0][0].transcript); setVoiced(micLang); };
    rec.onend = () => setListening(false);
    rec.onerror = () => { setListening(false); setErr("Microphone did not hear anything. Please try again or type instead."); };
    recRef.current = rec; setListening(true);
    try { (rec as { start: () => void }).start(); } catch { setListening(false); }
  }

  function copyClause() {
    if (!out?.clause) return;
    navigator.clipboard.writeText(out.clause).then(
      () => { setCopied(true); setTimeout(() => setCopied(false), 2200); },
      () => setErr("Copying is blocked by the browser. Please select the text by hand.")
    );
  }

  async function runLint(text: string) {
    if (text.trim().length < 10 || lintLoading) return;
    setLintLoading(true); setLintErr(""); setLintOut(null);
    try {
      const r = await fetch("/api/lint", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || `Check failed (error ${r.status}). Please try again.`);
      setLintOut(data);
    } catch (e) {
      setLintErr(e instanceof Error ? e.message : "Check failed. Please try again.");
    } finally {
      setLintLoading(false);
    }
  }

  async function runLintFile(f: File) {
    if (lintLoading) return;
    setLintLoading(true); setLintErr(""); setLintOut(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const r = await fetch("/api/lint-file", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || data.error || `Check failed (error ${r.status}). Please try again.`);
      setLintOut(data);
    } catch (e) {
      setLintErr(e instanceof Error ? e.message : "Check failed. Please try again.");
    } finally {
      setLintLoading(false);
    }
  }

  async function runMap(code: string) {
    if (code.trim().length < 3 || mapLoading) return;
    setMapLoading(true); setMapOut(null);
    try {
      const r = await fetch(`/api/map?foreign=${encodeURIComponent(code)}`);
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || `Lookup failed (error ${r.status}). Please try again.`);
      setMapOut(data);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Lookup failed. Please try again.");
    } finally {
      setMapLoading(false);
    }
  }

  function reportText(): string {
    if (!lintOut) return "";
    const lines = [
      "MANAK SETU — TENDER HEALTH REPORT",
      `Score: ${lintOut.score}/100 — ${lintOut.verdict}`,
      `IS references checked: ${lintOut.checked_is.join(", ") || "none"}`,
      "",
    ];
    for (const f of lintOut.findings) {
      lines.push(`[${f.severity.toUpperCase()}] ${f.title}`);
      lines.push(`  ${f.detail}`);
      if (f.suggestion) lines.push(`  Fix: ${f.suggestion}`);
      lines.push("");
    }
    lines.push("Generated by Manak Setu (SIH26108) — every IS number checked against the live BIS database.");
    return lines.join("\n");
  }

  function copyReport() {
    navigator.clipboard.writeText(reportText()).then(
      () => { setCopiedReport(true); setTimeout(() => setCopiedReport(false), 2200); },
      () => setLintErr("Copying is blocked by the browser. Please select the text by hand.")
    );
  }

  function downloadReport() {
    const blob = new Blob([reportText()], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "manak-setu-audit-report.txt";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function downloadPDF() {
    if (!lintOut) return;
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const W = 595, M = 48;
    let y = 60;
    const line = (t: string, size: number, bold: boolean, color: [number, number, number], gap = 14) => {
      doc.setFont("helvetica", bold ? "bold" : "normal");
      doc.setFontSize(size);
      doc.setTextColor(...color);
      const split = doc.splitTextToSize(t, W - 2 * M);
      for (const s of split) {
        if (y > 800) { doc.addPage(); y = 60; }
        doc.text(s, M, y);
        y += size * 1.25;
      }
      y += gap;
    };
    doc.setFillColor(194, 65, 12); doc.rect(0, 0, W, 7, "F");
    line("MANAK SETU — Tender Health Report", 17, true, [27, 36, 50], 4);
    line("Smart India Hackathon 2026 · Problem SIH26108", 10, false, [100, 110, 130], 10);
    line(`Health score: ${lintOut.score}/100 — ${lintOut.verdict}`, 13, true,
      lintOut.score >= 85 ? [22, 101, 52] : lintOut.score >= 60 ? [146, 64, 14] : [185, 28, 28], 6);
    line(`IS references checked: ${lintOut.checked_is.join(", ") || "none"}`, 10, false, [100, 110, 130], 10);
    const sevColor = (s: string): [number, number, number] =>
      s === "high" ? [185, 28, 28] : s === "medium" ? [146, 64, 14] : [22, 101, 52];
    lintOut.findings.forEach((f, i) => {
      line(`${i + 1}. [${f.severity.toUpperCase()}] ${f.title}`, 11, true, sevColor(f.severity), 2);
      line(`   ${f.detail}`, 10, false, [60, 65, 80], 1);
      if (f.suggestion) line(`   Fix: ${f.suggestion}`, 10, true, [40, 45, 60], 8);
    });
    line("Generated by Manak Setu — every IS number checked against the live BIS database.", 9, false, [140, 145, 160], 0);
    doc.save("manak-setu-audit-report.pdf");
  }

  function downloadDOC() {
    if (!lintOut) return;
    const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const sevColor = (s: string) => (s === "high" ? "#B42828" : s === "medium" ? "#92400E" : "#166534");
    const items = lintOut.findings.map((f, i) =>
      `<p><b style="color:${sevColor(f.severity)}">${i + 1}. [${esc(f.severity.toUpperCase())}] ${esc(f.title)}</b><br/>` +
      `<span>${esc(f.detail)}</span>` +
      (f.suggestion ? `<br/><b>Fix: ${esc(f.suggestion)}</b>` : "") + `</p>`
    ).join("");
    const html =
      `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word">` +
      `<head><meta charset="utf-8"><title>Manak Setu Audit Report</title></head><body>` +
      `<h1>MANAK SETU — Tender Health Report</h1>` +
      `<p>Smart India Hackathon 2026 · Problem SIH26108</p>` +
      `<h2>Health score: ${lintOut.score}/100 — ${esc(lintOut.verdict)}</h2>` +
      `<p>IS references checked: ${esc(lintOut.checked_is.join(", ") || "none")}</p>` +
      items +
      `<p><i>Generated by Manak Setu — every IS number checked against the live BIS database.</i></p>` +
      `</body></html>`;
    const blob = new Blob(["\ufeff", html], { type: "application/msword;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "manak-setu-audit-report.doc";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const stepIdx = Math.min(STAGES.length - 1, Math.floor(elapsed / 6));
  const top = out?.results?.[0];

  return (
    <div className="wrap">
      <header className="topbar">
        <Mark />
        <div className="brand">
          <h1>Manak Setu <span className="hi">मानक सेतु</span></h1>
          <small>For Indian government procurement · SIH 2026</small>
        </div>
        <div className="headmeta">
          <b>{(stats?.standards ?? 17135).toLocaleString("en-IN")}</b> standards ·
          {" "}<b>{(stats?.qco_tracked ?? 511).toLocaleString("en-IN")}</b> under quality control
          <br />Problem statement SIH26108
        </div>
      </header>

      <section className="intro">
        <h2>Which standard does your purchase need?</h2>
        <p>Describe what you want to buy, in your own words and language. Manak Setu finds the correct Indian Standards, checks they are current, tells you if ISI certification is compulsory, and writes the tender clause.</p>
      </section>

      <section className="panel">
        <div className="tabs" role="tablist" aria-label="Choose a task">
          <button role="tab" aria-selected={mode === "find"} className={`tab${mode === "find" ? " on" : ""}`} onClick={() => setMode("find")}>Search standards</button>
          <button role="tab" aria-selected={mode === "audit"} className={`tab${mode === "audit" ? " on" : ""}`} onClick={() => setMode("audit")}>Check a tender</button>
        </div>

        {mode === "find" && (
          <div className="tabbody">
            <label className="fieldlabel" htmlFor="need">Describe what you want to buy</label>
            <div className="cbox">
              <textarea id="need" value={q} onChange={(e) => { setQ(e.target.value); setVoiced(null); }}
                placeholder="Example: 12 mm steel bars for building construction, 500 tonnes, ISI-marked" />
              <button className={`iconbtn${listening ? " live" : ""}`} onClick={toggleMic}
                title={listening ? "Stop listening" : `Speak instead of typing (${LANG_NAMES[micLang]})`} aria-label="Speak instead of typing">{I.mic}</button>
              <button className="primary" disabled={loading} onClick={() => run(q)}>{loading ? "Searching…" : <>Search {I.go}</>}</button>
            </div>
            <div className="langrow">
              <label htmlFor="miclang">Voice language:</label>
              <select id="miclang" className="langselect" value={micLang} onChange={(e) => setMicLang(e.target.value as "hi-IN" | "mr-IN" | "en-IN")}>
                <option value="hi-IN">Hindi (हिंदी)</option>
                <option value="mr-IN">Marathi (मराठी)</option>
                <option value="en-IN">English</option>
              </select>
              <span className="hint">Spoken input is labelled automatically. Typed Hindi or Hinglish works too.</span>
            </div>
            <div className="samples">
              <span>Try an example:</span>
              {SAMPLES.map((s, i) => (
                <button key={s} className="sample" onClick={() => { setQ(s); setVoiced(null); run(s); }}>
                  Example {i + 1}: {s.length > 46 ? s.slice(0, 46) + "…" : s}
                </button>
              ))}
            </div>
            {err && <div className="err">{err}</div>}
          </div>
        )}

        {mode === "audit" && (
          <div className="tabbody">
            <label className="fieldlabel" htmlFor="tender">Paste your draft tender text, or upload the file</label>
            <div className="cbox" style={{ flexDirection: "column" }}>
              <textarea id="tender" value={tender} onChange={(e) => setTender(e.target.value)} rows={5}
                placeholder="Paste the technical specification section of your tender here…" style={{ minHeight: 110 }} />
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button className="primary" disabled={lintLoading} onClick={() => runLint(tender)} style={{ minHeight: 54 }}>
                  {lintLoading ? "Checking…" : <>Check this tender {I.go}</>}
                </button>
                <button className="btnplain" disabled={lintLoading} onClick={() => fileRef.current?.click()}>Upload a file (.pdf, .docx, .txt)</button>
                <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" hidden
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) runLintFile(f); e.target.value = ""; }} />
              </div>
            </div>
            <div className="samples">
              <span>Try an example:</span>
              <button className="sample" onClick={() => { setTender(SAMPLE_TENDER); runLint(SAMPLE_TENDER); }}>
                Tender with an outdated standard in it
              </button>
            </div>
            {lintErr && <div className="err">{lintErr}</div>}
          </div>
        )}
      </section>

      {mode === "find" && (
        <div className="mapper">
          <span className="mlabel">Have a foreign standard number, like IEC 60335?</span>
          <input value={mapQ} onChange={(e) => setMapQ(e.target.value)} placeholder="Type it here, e.g. IEC 60335"
            aria-label="Foreign standard number" onKeyDown={(e) => { if (e.key === "Enter") runMap(mapQ); }} />
          <button className="btnplain" disabled={mapLoading} onClick={() => runMap(mapQ)}>
            {mapLoading ? "Looking up…" : "Find Indian equivalent"}
          </button>
        </div>
      )}
      {mode === "find" && mapOut && (
        <div className="mapres">
          {mapOut.matches.length === 0 && <div className="warn">{mapOut.note ?? "No Indian equivalent recorded."}</div>}
          {mapOut.matches.map((m) => (
            <div className="std entry" key={m.designation}>
              <div className="des">{m.designation}{m.year ? `:${m.year}` : ""}</div>
              <div className="title">{m.title}</div>
              <div className="stamps">
                <span className="stamp info">Indian equivalent</span>
                {m.certification === "Mandatory Certification"
                  ? <span className="stamp warnb">{I.shield} ISI mandatory</span>
                  : <span className="stamp dim">No compulsory certification</span>}
              </div>
              <div className="scores">BIS records list {m.iso_equivalent} as identical or equivalent. Unofficial mappings are never shown.</div>
            </div>
          ))}
        </div>
      )}

      {mode === "find" && (loading || out) && (
        <div className="stepper" role="status" aria-label="Search progress">
          <div className="stepbar"><div style={{ width: `${out ? 100 : Math.min(96, ((stepIdx + 1) / STAGES.length) * 100)}%` }} /></div>
          <div className="steptext">
            {out
              ? <>Finished in {(out.took_ms / 1000).toFixed(1)} seconds{out.cached ? " (instant answer from memory)" : ""}.</>
              : <><b>Step {stepIdx + 1} of {STAGES.length}: {STAGES[stepIdx].label}…</b> ({Math.round(elapsed)}s, first search warms the system)</>}
          </div>
        </div>
      )}

      {mode === "find" && out && (
        <>
          <div className="sect">
            <h3>What the system understood</h3>
            <p className="sub">Written by the AI in plain English. If it misread you, rephrase and search again.</p>
          </div>
          <div className="uread">
            <div className="who">AI reading · language: {out.language}</div>
            <p>{out.understood}</p>
            <div className="confrow">
              <div className="confbar"><div style={{ width: `${out.confidence * 100}%` }} /></div>
              <span className="confnum">{Math.round(out.confidence * 100)}% match</span>
            </div>
            <div className="meta">Below this score the system refuses to guess and asks a BIS expert instead.</div>
            {out.warnings.map((w, i) => <div className="warn" key={i}>{w}</div>)}
          </div>

          {top && (
            <>
              <div className="sect">
                <h3>Recommended standards</h3>
                <p className="sub">One purchase usually needs a family of rulebooks: the main specification first, then test methods, codes and sampling. Every number below was verified in the live database.</p>
              </div>
              <Entry c={top} main />
            </>
          )}

          {out.results.length > 1 && (
            <div className="ledger">
              {out.results.slice(1).map((c) => <Entry key={c.designation} c={c} />)}
            </div>
          )}

          {out.allied.length > 0 && (
            <>
              <div className="sect">
                <h3>Related standards you may also need</h3>
                <p className="sub">Found by following references between standards — these are the allied rulebooks officers most often forget.</p>
              </div>
              <div className="ledger">
                {out.allied.map((c) => <Entry key={c.designation} c={c} />)}
              </div>
            </>
          )}

          {out.clause && (
            <div className="clause">
              <h4>Tender clause — ready to paste into your document</h4>
              <p>“{out.clause}”</p>
              <button className="copy" onClick={copyClause}>{copied ? <>{I.check} Copied</> : <>{I.copy} Copy clause</>}</button>
            </div>
          )}
        </>
      )}

      {mode === "audit" && lintLoading && !lintOut && (
        <div className="stepper" role="status" aria-label="Checking progress">
          <div className="stepbar"><div style={{ width: "60%" }} /></div>
          <div className="steptext"><b>Checking your tender…</b> reading version records, quality-control orders and related standards.</div>
        </div>
      )}

      {mode === "audit" && lintOut && (
        <>
          <div className="sect">
            <h3>Tender health report</h3>
            <p className="sub">Checked {lintOut.checked_is.length} standard reference(s) in {((lintOut.took_ms || 0) / 1000).toFixed(1)} seconds. Outdated references −25 points, foreign specifications −15, missing allied standards −10 each.</p>
          </div>
          <div className="scorebox">
            <div className="scorebig">{lintOut.score}<small>/100</small></div>
            <div>
              <div style={{ fontSize: 17, color: "var(--ink)", fontWeight: 700 }}>{lintOut.verdict}</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
                <button className="btnplain" onClick={copyReport}>{copiedReport ? "Copied" : "Copy report"}</button>
                <button className="btnplain" onClick={downloadReport}>Save as .txt</button>
                <button className="btnplain" onClick={downloadPDF}>Save as PDF</button>
                <button className="btnplain" onClick={downloadDOC}>Save as Word</button>
              </div>
            </div>
          </div>
          {lintOut.findings.map((f, i) => (
            <div className={`finding sev-${f.severity}`} key={i}>
              <div className="fhead">
                {f.severity === "high" ? I.warn : f.kind === "ok" ? I.check : I.shield}
                <b>{f.title}</b>
              </div>
              <div className="fdetail">{f.detail}</div>
              {f.suggestion && <div className="fsugg">Suggested fix: {f.suggestion}</div>}
            </div>
          ))}
        </>
      )}

      <footer className="foot">
        Manak Setu · Smart India Hackathon 2026 · Problem statement SIH26108.<br />
        Every standard number shown is verified against the live BIS database — the system cannot invent one. Certification statuses come from the BIS quality-control snapshot dated 4 October 2026.
      </footer>
    </div>
  );
}
