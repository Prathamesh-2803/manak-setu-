"""Week-0 smoke crawler: fetch ONE BIS standards list page and parse the table.

Proves the data pipe end-to-end (fetch -> parse -> JSONL). The full crawler
(Week 1) enumerates all classification pages with the same parser.

Usage:
    python pipeline/crawl_bis.py                       # default sample page
    python pipeline/crawl_bis.py --url <list-page-url>
    python pipeline/crawl_bis.py --out data/raw/smoke.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# One request, honest user agent, clear identification.
USER_AGENT = "ManakSetu-SIH26108 research crawler (student project; metadata only; contact: via SIH submission)"
DEFAULT_URL = "https://www.services.bis.gov.in/php/BIS_2.0/dgdashboard/published/sub_sub_grp_stn_list/575"

DESIGNATION_RE = re.compile(
    r"^(?P<desig>IS(?:/ISO)?\s+\d+(?:\s*:\s*Part\s*\d+(?:\s*Sec(?:tion)?\s*\d+)?)?)\s*:\s*(?P<year>\d{4})",
    re.IGNORECASE,
)
ISO_RE = re.compile(r"/\s*((?:ISO|IEC)(?:\s*/\s*TS)?)\s*([0-9]+(?:-[0-9]+)?)\s*:\s*(\d{4})", re.IGNORECASE)
REVISION_RE = re.compile(r"\((\d+)\s*Revision", re.IGNORECASE)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def parse_row(cells: list[str], hrefs: list[str]) -> dict | None:
    # Layout: [checkbox, s_no, IS-number, title, amendment, reaffirmation, buy, comment]
    # Auto-detect the IS-number cell so the parser survives layout shifts.
    idx = next((i for i, c in enumerate(cells) if c.startswith("IS")), None)
    if idx is None or idx + 1 >= len(cells):
        return None

    number_cell = cells[idx]
    title = cells[idx + 1]
    record: dict = {
        "s_no": cells[idx - 1] if idx >= 1 else "",
        "is_number_raw": clean(number_cell),
        "title": clean(title),
        "amendment": clean(cells[idx + 2]) if len(cells) > idx + 2 else "",
        "reaffirmation_year": clean(cells[idx + 3]) if len(cells) > idx + 3 else "",
        "detail_url": hrefs[0] if hrefs else "",
    }

    m = DESIGNATION_RE.match(record["is_number_raw"])
    iso_parts: list[str] = []
    if m:
        record["designation"] = re.sub(r"\s+", " ", m.group("desig")).upper().replace(" :", ":")
        record["year"] = m.group("year")
        if record["designation"].startswith("IS/ISO"):
            # Identical adoption: IS/ISO 10012:2003 == ISO 10012:2003
            iso_parts.append(record["designation"].replace("IS/", "") + ":" + record["year"])
    iso = ISO_RE.search(number_cell)
    if iso:
        iso_parts.append(f"{iso.group(1).upper()} {iso.group(2)}:{iso.group(3)}")
    if iso_parts:
        # dedupe while keeping order (designation regex may double-hit)
        record["iso_equivalent"] = ", ".join(dict.fromkeys(iso_parts))
    rev = REVISION_RE.search(number_cell)
    if rev:
        record["revision_count"] = int(rev.group(1))

    # Titles sometimes carry supersession info: "Superseding IS xxx"
    sup = re.search(r"[Ss]uperseding\s+((?:IS|Part)[^,;(]*)", title)
    if sup:
        record["supersedes_raw"] = clean(sup.group(1))[:120]
    return record


def fetch(url: str) -> str:
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    for tr in soup.find_all("tr"):
        cells = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        hrefs = [a.get("href", "") for a in tr.find_all("a", href=True)]
        rec = parse_row(cells, hrefs)
        if rec:
            records.append(rec)
    return records


def main() -> int:
    ap = argparse.ArgumentParser(description="BIS list-page smoke crawler")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", default="data/raw/smoke.jsonl")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    print(f"[crawl] GET {args.url}")
    html = fetch(args.url)
    print(f"[crawl] {len(html)} bytes")

    records = parse_page(html)
    print(f"[parse] {len(records)} standards parsed")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[save]  {out.resolve()}")

    for rec in records[:3]:
        print("  e.g.", json.dumps(rec, ensure_ascii=False)[:200])

    time.sleep(max(args.delay, 0))  # stay polite even for a single request
    return 0 if records else 1


if __name__ == "__main__":
    sys.exit(main())
