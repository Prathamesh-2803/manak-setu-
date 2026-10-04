import { NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8001";

export async function GET() {
  try {
    const r = await fetch(`${API_URL}/api/v1/stats`, { next: { revalidate: 60 } });
    const data = await r.json();
    return NextResponse.json(data, { status: r.status });
  } catch (e) {
    return NextResponse.json(
      { error: `API unreachable: ${e instanceof Error ? e.message : e}` },
      { status: 502 }
    );
  }
}
