"""Probe the new BIS portal (post 1-Oct-2025 standards) for a JSON API."""

import re

import httpx

UA = {"User-Agent": "ManakSetu research crawler (SIH student project)"}

for url in ("https://standards.bis.gov.in/website/know-your-standards", "https://standards.bis.gov.in/"):
    try:
        r = httpx.get(url, headers=UA, timeout=30, follow_redirects=True)
        print(url, "->", r.status_code, len(r.text), "bytes")
        if r.status_code != 200:
            continue
        text = r.text
        apis = set(re.findall(r"""["']([^"'\s]*(?:api|search|standard)[^"'\s]*)["']""", text, re.I))
        js = re.findall(r"""src=["']([^"']+\.js)["']""", text)
        print("  api-ish:", list(apis)[:10])
        print("  js bundles:", js[:5])
        print("  is SPA:", "<div id=" in text or "__NEXT" in text or "ng-app" in text)
        break
    except Exception as exc:  # noqa: BLE001
        print(url, "ERR", str(exc)[:150])
