"""Ready-to-paste tender clause generator (template, instant, no LLM cost)."""

from __future__ import annotations


def build_clause(main: dict, cert: dict, version: dict) -> str:
    des = main.get("designation") or "IS"
    year = main.get("year") or "latest"
    title = (main.get("title") or "the applicable Indian Standard").strip()
    clause = (
        f"The goods shall conform to {des}:{year} ({title}), "
        "latest revision including all amendments thereto."
    )
    if cert.get("mandatory"):
        clause += (
            f" The goods shall bear the {cert.get('scheme', 'Standard Mark')} "
            "as required under the applicable Quality Control Order"
        )
        if cert.get("implemented_on") and str(cert["implemented_on"]).lower() != "none":
            clause += f" (implemented {cert['implemented_on']})"
        clause += "."
    if version.get("status") != "current" and version.get("replaced_by"):
        clause += (f" Note: {des} stands {version['status']}; "
                   f"use {version['replaced_by']} instead.")
    return clause
