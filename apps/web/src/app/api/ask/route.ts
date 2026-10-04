import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8001";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const query = String(body.query ?? "").slice(0, 4000);
  if (!query.trim()) {
    return NextResponse.json({ error: "query is required" }, { status: 400 });
  }
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 180_000);
  try {
    const r = await fetch(`${API_URL}/api/v1/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: 6, expand: 6 }),
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
