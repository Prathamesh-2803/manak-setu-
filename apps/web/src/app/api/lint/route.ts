import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8001";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const text = String(body.text ?? "").slice(0, 12000);
  if (text.trim().length < 10) {
    return NextResponse.json({ error: "tender text too short (min 10 chars)" }, { status: 400 });
  }
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 240_000);
  try {
    const r = await fetch(`${API_URL}/api/v1/lint`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      signal: ctl.signal,
    });
    const data = await r.json();
    return NextResponse.json(data, { status: r.status });
  } catch (e) {
    return NextResponse.json(
      { error: `API unreachable: ${e instanceof Error ? e.message : e}` },
      { status: 502 }
    );
  } finally {
    clearTimeout(timer);
  }
}
