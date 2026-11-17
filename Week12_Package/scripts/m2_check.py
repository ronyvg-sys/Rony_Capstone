#!/usr/bin/env python3
"""scripts/m2_check.py — is your M2 deliverable in shape?

M2 has five items. Two of them (the running API, the passing eval suite) are your
own capstone code and are checked with the commands this script prints. The other
three are documents this script verifies directly: the KPI snapshot, the ADR
consolidation, and the DR #2 one-pager. Runs offline.

    python3 scripts/m2_check.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GREEN, RED, YEL, NC = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def _read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text() if p.exists() else ""


def check(label: str, ok: bool, hint: str = "") -> bool:
    mark = f"{GREEN}✓{NC}" if ok else f"{RED}✗{NC}"
    print(f"  {mark} {label}" + (f"  — {hint}" if not ok and hint else ""))
    return ok


def main() -> int:
    print("M2 deliverable — document checks (items 3–5):\n")
    ok = True

    snap = _read("docs/kpi/wk12-snapshot.md")
    kpi_rows = all(re.search(rf"^\|\s*{n}\s*\|", snap, re.M) for n in range(1, 9))
    ok &= check("KPI snapshot: docs/kpi/wk12-snapshot.md exists", bool(snap),
                "write the 8-KPI dashboard")
    ok &= check("KPI snapshot: all 8 KPI rows present", kpi_rows)
    ok &= check("KPI snapshot: wk6→wk12 trajectory + commentary",
                "trajectory" in snap.lower() and "commentary" in snap.lower())

    adr = _read("docs/adr/0001-capstone-framing.md")
    ok &= check("ADR: docs/adr/0001-capstone-framing.md exists", bool(adr))
    ok &= check("ADR: marked v2 (M2)", "v2 (m2)" in adr.lower() or "v2 (M2)" in adr)
    ok &= check("ADR: consolidates Phase 2 (retrieval + lifecycle + eval)",
                all(k in adr.lower() for k in ("rerank", "tombstone", "ragas")))

    dr = _read("docs/dr/dr2-summary-EXAMPLE.md") or _read("docs/dr/dr2-summary-template.md")
    ok &= check("DR #2 one-pager: docs/dr/dr2-summary-*.md exists", bool(dr))
    ok &= check("DR #2 one-pager: covers retrieval + KB lifecycle + KPIs",
                all(k in dr.lower() for k in ("retriev", "lifecycle", "kpi")))

    rb = _read("docs/runbooks/rag_debugging.md")
    tax = _read("docs/debugging/rag_failure_taxonomy.md")
    ok &= check("Debugging runbook present", bool(rb))
    ok &= check("Failure taxonomy present", bool(tax))

    print(f"\nItems 1–2 are your capstone code — verify them with:\n"
          f"  {YEL}# 1. Production API (run your service, then):{NC}\n"
          f"  curl -s localhost:8000/health | python3 -m json.tool\n"
          f"  curl -s -XPOST localhost:8000/ask -d '{{\"question\":\"What is the leave policy?\"}}'\n"
          f"  {YEL}# 2. Eval suite (your W11 eval/ folder):{NC}\n"
          f"  python3 -m pytest eval/ -q\n")

    if ok:
        print(f"{GREEN}M2 documents complete.{NC} Finish items 1–2 above, then you're ready for DR #2.")
        return 0
    print(f"{RED}Some M2 documents are missing or incomplete (see ✗ above).{NC}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
