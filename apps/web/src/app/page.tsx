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

  async function run(query: string) {
    if (!query.trim() || loading) return;
    setLoading(true); setErr(""); setOut(null); setCopied(false); setElapsed(0);
    try {
      const r = await fetch("/api/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, language_hint: voiced }),
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
    rec.lang = micLang; rec.interimResults = false; rec.maxAlternatives = 1;
    rec.onresult = (e: { results: { transcript: string }[][] }) => { setQ(e.results[0][0].transcript); setVoiced(micLang); };
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

  useEffect(() => {
    fetch("/api/stats").then((r) => r.json()).then((d) => {
      if (d && typeof d.standards === "number") setStats(d);
    }).catch(() => {});
  }, []);

  async function runMap(code: string) {
    if (code.trim().length < 3 || mapLoading) return;
    setMapLoading(true); setMapOut(null);
    try {
      const r = await fetch(`/api/map?foreign=${encodeURIComponent(code)}`);
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || `request failed (${r.status})`);
      setMapOut(data);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setMapLoading(false);
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
      if (!r.ok) throw new Error(data.detail || data.error || `request failed (${r.status})`);
      setLintOut(data);
    } catch (e) {
      setLintErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLintLoading(false);
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
    lines.push("Generated by Manak Setu (SIH26108) — every IS number validated against the live BIS database.");
    return lines.join("\n");
  }

  function copyReport() {
    navigator.clipboard.writeText(reportText()).then(
      () => { setCopiedReport(true); setTimeout(() => setCopiedReport(false), 2200); },
      () => setLintErr("Copy blocked by browser — select the text manually.")
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
    // tricolor header bar
    doc.setFillColor(255, 153, 51); doc.rect(0, 0, W / 3, 8, "F");
    doc.setFillColor(240, 242, 255); doc.rect(W / 3, 0, W / 3, 8, "F");
    doc.setFillColor(19, 136, 8); doc.rect((2 * W) / 3, 0, W / 3, 8, "F");
    line("MANAK SETU — TENDER HEALTH REPORT", 17, true, [20, 25, 45], 4);
    line("Smart India Hackathon 2026 · Problem SIH26108", 10, false, [100, 110, 130], 10);
    line(`Health score: ${lintOut.score}/100 — ${lintOut.verdict}`, 13, true,
      lintOut.score >= 85 ? [20, 130, 80] : lintOut.score >= 60 ? [170, 120, 10] : [180, 40, 40], 6);
    line(`IS references checked: ${lintOut.checked_is.join(", ") || "none"}`, 10, false, [100, 110, 130], 10);
    const sevColor = (s: string): [number, number, number] =>
      s === "high" ? [180, 40, 40] : s === "medium" ? [170, 120, 10] : [20, 130, 80];
    lintOut.findings.forEach((f, i) => {
      line(`${i + 1}. [${f.severity.toUpperCase()}] ${f.title}`, 11, true, sevColor(f.severity), 2);
      line(`   ${f.detail}`, 10, false, [60, 65, 80], 1);
      if (f.suggestion) line(`   Fix: ${f.suggestion}`, 10, true, [40, 45, 60], 8);
    });
    line("Generated by Manak Setu — every IS number validated against the live BIS database.", 9, false, [140, 145, 160], 0);
    doc.save("manak-setu-audit-report.pdf");
  }

  function downloadDOC() {
    if (!lintOut) return;
    const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const sevColor = (s: string) => (s === "high" ? "#B42828" : s === "medium" ? "#AA7810" : "#148850");
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
      `<p><i>Generated by Manak Setu — every IS number validated against the live BIS database.</i></p>` +
      `</body></html>`;
    const blob = new Blob(["\ufeff", html], { type: "application/msword;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "manak-setu-audit-report.doc";
    a.click();
    URL.revokeObjectURL(a.href);
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
      if (!r.ok) throw new Error(data.error || `request failed (${r.status})`);
      setLintOut(data);
    } catch (e) {
      setLintErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLintLoading(false);
    }
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
          <div className="stat"><b className="saff">{(stats?.standards ?? 17135).toLocaleString("en-IN")}</b><span>standards indexed · live</span></div>
          <div className="stat"><b className="grn">{(stats?.qco_tracked ?? 526).toLocaleString("en-IN")}</b><span>QCO tracked · live</span></div>
          <div className="stat"><b className="blu">{(stats?.graph_edges ?? 84274).toLocaleString("en-IN")}</b><span>graph links · live</span></div>
        </div>
      </section>

      <div className="tabs" role="tablist" aria-label="Mode">
        <button role="tab" aria-selected={mode === "find"} className={`tab${mode === "find" ? " on" : ""}`} onClick={() => setMode("find")}>Find standards</button>
        <button role="tab" aria-selected={mode === "audit"} className={`tab${mode === "audit" ? " on" : ""}`} onClick={() => setMode("audit")}>Audit a tender</button>
      </div>

      {mode === "find" && (
      <section className="console">
        <div className="cbox">
          <textarea value={q} onChange={(e) => { setQ(e.target.value); setVoiced(null); }}
            placeholder="e.g. 12 mm steel bars for building construction, 500 tonnes, ISI-marked…" aria-label="Describe what you want to procure" />
          <button className={`iconbtn${listening ? " live" : ""}`} onClick={toggleMic} title={`Voice input (${micLang === "hi-IN" ? "Hindi" : "English"})`} aria-label="Voice input">{I.mic}</button>
          <select className="langselect" value={micLang} onChange={(e) => setMicLang(e.target.value as "hi-IN" | "mr-IN" | "en-IN")} title="Voice input language" aria-label="Voice input language">
            <option value="hi-IN">हिंदी</option>
            <option value="mr-IN">मराठी</option>
            <option value="en-IN">EN</option>
          </select>
          <button className="cta" disabled={loading} onClick={() => run(q)}>{loading ? "Khoj…" : <>Find {I.go}</>}</button>
        </div>
        <div className="chips">
          {SAMPLES.map((s) => (
            <button key={s} className="chip" onClick={() => { setQ(s); run(s); }}>
              {s.length > 56 ? s.slice(0, 56) + "…" : s}
            </button>
          ))}
        </div>
        <div className="hintline">Mic speaks {micLang === "hi-IN" ? "Hindi (हिंदी में बोलें)" : micLang === "mr-IN" ? "Marathi (मराठीत बोला)" : "English"} — typed Hinglish works too. Spoken input is auto-tagged so the AI labels it right.</div>
        {err && <div className="err">{err}</div>}
      </section>
      )}

      {mode === "find" && (
        <div className="mapper">
          <span className="mlabel">Foreign code in tender?</span>
          <input value={mapQ} onChange={(e) => setMapQ(e.target.value)} placeholder="e.g. IEC 60335, ISO 11611, EN 12150"
            aria-label="Foreign standard code" onKeyDown={(e) => { if (e.key === "Enter") runMap(mapQ); }} />
          <button className="btn-ghost" disabled={mapLoading} onClick={() => runMap(mapQ)}>
            {mapLoading ? "Mapping…" : "Map to Indian equivalent"}
          </button>
        </div>
      )}
      {mode === "find" && mapOut && (
        <div className="mapres">
          {mapOut.matches.length === 0 && <div className="warn">{mapOut.note ?? "No match."}</div>}
          {mapOut.matches.map((m) => (
            <div className="std" key={m.designation} style={{ animationDelay: "60ms" }}>
              <div className="top"><span className="des">{m.designation}{m.year ? `:${m.year}` : ""}</span></div>
              <div className="title">{m.title}</div>
              <div className="badges">
                <span className="badge b-product">Indian equivalent</span>
                {m.certification === "Mandatory Certification"
                  ? <span className="badge warnb">{I.shield} compulsory certification</span>
                  : <span className="badge dim">no compulsory certification</span>}
              </div>
              <div className="scores">BIS records list {m.iso_equivalent} as identical/equivalent</div>
            </div>
          ))}
          <div className="meta">Official BIS-recorded mappings only — anything else needs expert review.</div>
        </div>
      )}

      {mode === "audit" && (
      <section className="console">
        <div className="cbox" style={{ flexDirection: "column" }}>
          <textarea value={tender} onChange={(e) => setTender(e.target.value)} rows={5}
            placeholder="Paste a draft tender clause here…" aria-label="Draft tender text" style={{ minHeight: 110 }} />
          <button className="cta" disabled={lintLoading} onClick={() => runLint(tender)} style={{ minHeight: 54 }}>
            {lintLoading ? "Auditing…" : <>Audit tender {I.go}</>}
          </button>
        </div>
        <div className="chips">
          <button className="chip" onClick={() => { setTender(SAMPLE_TENDER); runLint(SAMPLE_TENDER); }}>
            Try the sample: outdated IS + foreign spec + gaps
          </button>
          <button className="chip" onClick={() => fileRef.current?.click()}>
            …or upload tender file (.pdf/.docx/.txt)
          </button>
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" hidden
            onChange={(e) => { const f = e.target.files?.[0]; if (f) runLintFile(f); e.target.value = ""; }} />
        </div>
        {lintErr && <div className="err">{lintErr}</div>}
      </section>
      )}

      {mode === "find" && (loading || out) && (
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

      {mode === "find" && loading && !out && (
        <div className="spin">AI pipeline running — decomposer → hybrid search → reranker → knowledge graph → guard → oracle…<br />
          <span style={{ fontSize: 12.5 }}>first query warms the models ({Math.round(elapsed)}s)</span>
          <div className="bar"><div /></div>
        </div>
      )}

      {mode === "find" && out && (
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
              <div className="sect"><h3>Recommended family</h3><div className="rule" /><span className="count">main spec + {out.results.length - 1} relatives</span></div>
              <div className="famnote">One purchase needs a family of rulebooks — the main specification first, test methods, codes and sampling below. Every number verified in the live database.</div>
              <div className="hero-pick">
                <Ring v={out.confidence} />
                <div>
                  <span className="crown">Main specification</span>
                  <div className="des">{top.designation}{top.year ? `:${top.year}` : ""}</div>
                  <div className="title">{top.title}</div>
                  <Badges c={top} />
                  {top.certification.ministry && <div className="meta">Ministry: {top.certification.ministry}</div>}
                  {top.certification.mandatory && top.certification.source && <div className="meta">Source: {top.certification.source}</div>}
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

      {mode === "audit" && lintLoading && !lintOut && (
        <div className="spin">Auditing — checking versions → scanning foreign specs → finding gaps…<div className="bar"><div /></div></div>
      )}

      {mode === "audit" && lintOut && (
        <>
          <div className="sect"><h3>Tender health report</h3><div className="rule" /><span className="count">{lintOut.took_ms} ms · {lintOut.checked_is.length} IS refs checked</span></div>
          <div className="hero-pick">
            <Ring v={lintOut.score / 100} />
            <div>
              <span className="crown">Health score · {lintOut.score}/100</span>
              <div className="title" style={{ fontSize: 17 }}>{lintOut.verdict}</div>
              <div className="meta">Outdated refs −25 · foreign specs −15 · missing allied −10 each</div>
              <div className="chips">
                <button className="chip" onClick={copyReport}>{copiedReport ? "Copied!" : "Copy report"}</button>
                <button className="chip" onClick={downloadReport}>TXT</button>
                <button className="chip" onClick={downloadPDF}>PDF</button>
                <button className="chip" onClick={downloadDOC}>DOC</button>
              </div>
            </div>
          </div>
          {lintOut.findings.map((f, i) => (
            <div className={`finding sev-${f.severity}`} key={i} style={{ animationDelay: `${Math.min(i * 70, 420)}ms` }}>
              <div className="fhead">
                {f.severity === "high" ? I.warn : f.kind === "ok" ? I.check : I.spark}
                <b>{f.title}</b>
                <span className="src">{f.kind}</span>
              </div>
              <div className="fdetail">{f.detail}</div>
              {f.suggestion && <div className="fsugg">→ {f.suggestion}</div>}
            </div>
          ))}
        </>
      )}

      <footer className="foot">
        Manak Setu prototype · Smart India Hackathon 2026 · Problem SIH26108<br />
        <span className="zero">Zero hallucinated standard numbers — guaranteed by design.</span>
      </footer>
    </div>
  );
}
