"""BIS full crawler (Week 1) — three resumable phases.

Phases:
  groups   enumerate group index        -> data/raw/groups.json
  list     fetch every group list page  -> data/raw/list/*.jsonl + data/raw/standards_list.jsonl
  details  fetch per-standard detail    -> data/raw/details/<id>.json  (resumable; run overnight)

Usage:
  python pipeline/crawl_bis.py groups
  python pipeline/crawl_bis.py list
  python pipeline/crawl_bis.py details --limit 5        # sample run
  python pipeline/crawl_bis.py details --delay 1.0      # full overnight run

Politeness: single-threaded, 1 request at a time, configurable delay, honest
User-Agent, retries with backoff, no PDF/document downloads (metadata only).
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "ManakSetu-SIH26108 research crawler (student project; metadata only; "
    "respectful rate limits; no document downloads)"
)
BASE = "https://www.services.bis.gov.in/php/BIS_2.0"
GROUPS_URL = f"{BASE}/dgdashboard/Published/Group_standards"

RAW = Path("data/raw")
DETAILS_DIR = RAW / "details"
LIST_DIR = RAW / "list"

# ---------------------------------------------------------------- helpers


def get(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=60.0, follow_redirects=True)
            r.raise_for_status()
            return r.text
        except Exception as exc:  # noqa: BLE001
            wait = 2**attempt * 2
            print(f"  [retry {attempt + 1}/{retries}] {type(exc).__name__}: {exc} (sleep {wait}s)")
            time.sleep(wait)
    raise RuntimeError(f"giving up: {url}")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def detail_id_from_url(url: str) -> str:
    """.../isdetails_mnd/17568 -> 17568 ; .../isdetails/NTY4MQ== -> 5741"""
    tail = url.rstrip("/").split("/")[-1]
    if tail.isdigit():
        return tail
    try:
        padded = tail + "=" * (-len(tail) % 4)
        decoded = base64.b64decode(padded).decode()
        return decoded if decoded.isdigit() else tail
    except Exception:  # noqa: BLE001
        return tail


DESIGNATION_RE = re.compile(
    r"^(?P<desig>IS(?:/[A-Z]+)*(?:\s+GUIDE)?\s+\d+(?:\s*[:(]\s*Part\s*\d+)?(?:\s*:\s*Sec(?:tion)?\s*\d+)?)\s*[:)]\s*(?P<year>\d{4})",
    re.IGNORECASE,
)
ISO_RE = re.compile(r"/\s*((?:ISO|IEC)(?:\s*/\s*(?:TS|TR))?)\s*([0-9]+(?:-[0-9]+)?)\s*:\s*(\d{4})", re.IGNORECASE)
REVISION_RE = re.compile(r"\((\d+)\s*Revision", re.IGNORECASE)


def parse_row(cells: list[str], hrefs: list[str]) -> dict | None:
    """List-page row: [checkbox, s_no, IS-number, title, amendment, reaffirmation, doc, action]."""
    idx = next((i for i, c in enumerate(cells) if c.startswith("IS")), None)
    if idx is None or idx + 1 >= len(cells):
        return None

    number_cell = cells[idx]
    record: dict = {
        "s_no": cells[idx - 1] if idx >= 1 else "",
        "is_number_raw": clean(number_cell),
        "title": clean(cells[idx + 1]),
        "amendment": clean(cells[idx + 2]) if len(cells) > idx + 2 else "",
        "reaffirmation_year": clean(cells[idx + 3]) if len(cells) > idx + 3 else "",
        "detail_url": hrefs[0] if hrefs else "",
    }
    if record["detail_url"]:
        record["id"] = detail_id_from_url(record["detail_url"])

    m = DESIGNATION_RE.match(record["is_number_raw"])
    iso_parts: list[str] = []
    if m:
        record["designation"] = clean(m.group("desig")).upper()
        record["year"] = m.group("year")
        if record["designation"].startswith("IS/ISO"):
            iso_parts.append(record["designation"].replace("IS/", "") + ":" + record["year"])
    iso = ISO_RE.search(number_cell)
    if iso:
        iso_parts.append(f"{iso.group(1).upper()} {iso.group(2)}:{iso.group(3)}")
    if iso_parts:
        record["iso_equivalent"] = ", ".join(dict.fromkeys(iso_parts))
    rev = REVISION_RE.search(number_cell)
    if rev:
        record["revision_count"] = int(rev.group(1))
    sup = re.search(r"[Ss]uperseding\s+((?:IS|Part)[^,;(]*)", record["title"])
    if sup:
        record["supersedes_raw"] = clean(sup.group(1))[:120]
    return record


# ------------------------------------------------------------- phases


def phase_groups() -> None:
    html = get(GROUPS_URL)
    soup = BeautifulSoup(html, "html.parser")
    groups: list[dict] = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        # Layout: [s_no, group_name(link -> sub groups), count(link -> grp_stn_list/<id>)]
        count_td = next(
            (td for td in tds if td.find("a", href=True) and re.search(r"grp_stn_list/\d+", td.find("a", href=True)["href"])),
            None,
        )
        if count_td is None:
            continue
        m = re.search(r"grp_stn_list/(\d+)", count_td.find("a", href=True)["href"])
        texts = [clean(td.get_text(" ", strip=True)) for td in tds]
        count_txt = clean(count_td.get_text(" ", strip=True))
        name = next((t for t in texts if t and t != count_txt and not t.isdigit() and len(t) > 4), "")
        groups.append(
            {"list_id": int(m.group(1)), "name": name, "count": int(count_txt.replace(",", "")) if count_txt.isdigit() else None}
        )
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "groups.json").write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(g["count"] or 0 for g in groups)
    print(f"[groups] {len(groups)} groups, declared total ~{total} -> {RAW / 'groups.json'}")


def phase_list() -> None:
    groups = json.loads((RAW / "groups.json").read_text(encoding="utf-8"))
    LIST_DIR.mkdir(parents=True, exist_ok=True)
    seen: dict[str, dict] = {}
    for g in groups:
        url = f"{BASE}/dgdashboard/published/grp_stn_list/{g['list_id']}"
        out = LIST_DIR / f"group_{g['list_id']}.jsonl"
        if out.exists():
            rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line]
        else:
            html = get(url)
            soup = BeautifulSoup(html, "html.parser")
            rows = []
            for tr in soup.find_all("tr"):
                cells = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
                hrefs = [a["href"] for a in tr.find_all("a", href=True)]
                rec = parse_row(cells, hrefs)
                if rec:
                    rec["group_list_id"] = g["list_id"]
                    rec["group_name"] = g["name"]
                    rows.append(rec)
            out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
            time.sleep(1.0)
        for r in rows:
            key = r.get("id") or r["is_number_raw"]
            if key not in seen:
                seen[key] = r
        print(f"[list] group {g['list_id']:>3} {g['name'][:40]:40} rows={len(rows)}")

    merged = list(seen.values())
    (RAW / "standards_list.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged), encoding="utf-8"
    )
    print(f"[list] MERGED unique standards: {len(merged)} -> {RAW / 'standards_list.jsonl'}")


# ---------------------------------------------------------- detail page

BASIC_LABELS = [
    "IS Number",
    "IS Title",
    "Superseding IS",
    "Degree of Equivalence",
    "Number of Revisions",
    "Number of Amendments",
    "Aspect",
    "Language",
    "Reaffirmation Year",
    "Technical Department",
    "Technical Committee",
    "Member Secretary",
]
CLASS_LABELS = [
    "Group",
    "Sub Group",
    "Sub Sub Group",
    "Certification",
    "Relevant Ministries",
    "Sustainable development Goals",
    "Short Commom Man's Title",
    "Short Common Man's Title",
    "ITC-HS Code",
    "Identical/Equivalent International Standard(s)",
    "Harmonized with",
]


def _labels_to_fields(text: str, labels: list[str]) -> dict[str, str]:
    hits: list[tuple[int, int, str]] = []
    for lab in labels:
        for m in re.finditer(re.escape(lab) + r"(?:\s*/[^:]{1,60})?\s*:\s*", text, re.IGNORECASE):
            hits.append((m.start(), m.end(), lab))
    hits.sort()
    fields: dict[str, str] = {}
    for i, (start, end, lab) in enumerate(hits):
        stop = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        value = clean(text[end:stop])
        # cut stray section titles that leaked into the value
        value = re.split(r"\b(?:Other Details|Classification Details|Cross Reference Details|Email Ids|Download)\b", value)[0].strip()
        if lab not in fields or not fields[lab]:
            fields[lab] = value
    return fields


def parse_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = clean(soup.get_text(" ", strip=True))

    fields = _labels_to_fields(text, BASIC_LABELS)
    cls_text = text[text.find("Classification Details") :] if "Classification Details" in text else ""
    if cls_text:
        for k, v in _labels_to_fields(cls_text, CLASS_LABELS).items():
            fields.setdefault(k, v)

    # Cross references by document order: anchors before the "referred in" marker
    # are outbound (this IS -> others); after it are inbound (others -> this IS).
    marker = "is Referred in following Indian Standards"
    marker_idx: int | None = None
    anchor_idx: dict[int, int] = {}
    counter = 0
    for el in soup.descendants:
        counter += 1
        if marker_idx is None and isinstance(el, str) and marker in el:
            marker_idx = counter
        elif isinstance(el, str) and marker_idx is None and "is Referred in following" in el:
            marker_idx = counter
        if getattr(el, "name", None) == "a" and el.get("href"):
            href = el["href"]
            if "isdetails" in href and id(el) not in anchor_idx:
                anchor_idx[id(el)] = counter

    cross_out: list[str] = []
    cross_in: list[str] = []
    for a in soup.find_all("a", href=True):
        if "isdetails" not in a["href"]:
            continue
        label = clean(a.get_text(" ", strip=True))
        if not label.upper().startswith("IS"):
            continue
        pos = anchor_idx.get(id(a), 0)
        entry = {"designation": label, "id": detail_id_from_url(a["href"])}
        if marker_idx is None:
            cross_out.append(entry)  # fallback: treat as outbound
        elif pos > marker_idx:
            cross_in.append(entry)
        else:
            cross_out.append(entry)

    return {
        "fields": fields,
        "cross_refs_out": cross_out,
        "cross_refs_in": cross_in,
        "page_text_len": len(text),
    }


def phase_details(limit: int | None, delay: float) -> None:
    DETAILS_DIR.mkdir(parents=True, exist_ok=True)
    rows = [
        json.loads(line)
        for line in (RAW / "standards_list.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    todo = []
    for r in rows:
        rid = r.get("id")
        if not rid or not r.get("detail_url"):
            continue
        if (DETAILS_DIR / f"{rid}.json").exists():
            continue
        todo.append(r)
    if limit:
        todo = todo[:limit]
    already = sum(1 for r in rows if r.get("id") and (DETAILS_DIR / (str(r["id"]) + ".json")).exists())
    print(f"[details] total={len(rows)} already_done={already} todo={len(todo)}")

    done = 0
    errors = 0
    started = time.time()
    for r in todo:
        rid = r["id"]
        try:
            html = get(r["detail_url"])
            detail = parse_detail(html)
            detail["id"] = rid
            detail["list_row"] = r
            (DETAILS_DIR / f"{rid}.json").write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
            done += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"  [error] id={rid}: {exc}")
        if (done + errors) % 25 == 0:
            rate = (done + errors) / max(time.time() - started, 1)
            eta_h = (len(todo) - done - errors) / max(rate, 0.01) / 3600
            print(f"[progress] {done + errors}/{len(todo)} done={done} err={errors} rate={rate:.2f}/s eta={eta_h:.1f}h", flush=True)
        time.sleep(delay)
    print(f"[details] FINISHED done={done} errors={errors}")


def main() -> int:
    ap = argparse.ArgumentParser(description="BIS full crawler")
    ap.add_argument("phase", choices=["groups", "list", "details"])
    ap.add_argument("--limit", type=int, default=None, help="max detail pages this run")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between detail requests")
    args = ap.parse_args()

    if args.phase == "groups":
        phase_groups()
    elif args.phase == "list":
        phase_list()
    else:
        phase_details(args.limit, args.delay)
    return 0


if __name__ == "__main__":
    sys.exit(main())
