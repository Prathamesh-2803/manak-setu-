import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8001";

export async function POST(req: NextRequest) {
  let form;
  try {
    form = await req.formData();
  } catch {
    return NextResponse.json({ error: "no file received" }, { status: 400 });
  }
  const file = form.get("file");
  if (!(file instanceof Blob)) {
    return NextResponse.json({ error: "no file received" }, { status: 400 });
  }
  const out = new FormData();
  out.append("file", file, (file as File).name || "tender");
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 240_000);
  try {
    const r = await fetch(`${API_URL}/api/v1/lint-file`, {
      method: "POST",
      body: out,
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
