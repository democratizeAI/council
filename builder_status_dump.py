#!/usr/bin/env python3
"""
builder_status_dump.py
➡  Prints one JSON object per line (ND-JSON) with the latest info
    for every builder card it can discover in the ledger or builder API.
"""

import json, os, re, sys
from pathlib import Path
import requests

# --- CONFIG ------------------------------------------------------------------
BUILDER_API        = os.getenv("BUILDER_API", "http://localhost:8005")   # tiny-svc mock or real
LEDGER_FILES       = list(Path("docs/ledger").glob("Trinity Ledger *.pdf")) \
                  + list(Path("docs/ledger").glob("*.md"))
CARD_REGEX         = re.compile(r"\b([BEIS]-\d{2,3})\b")
TIMEOUT            = 4  # seconds
# -----------------------------------------------------------------------------


def discover_ids_from_ledger() -> set[str]:
    ids = set()
    for f in LEDGER_FILES:
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        ids.update(CARD_REGEX.findall(text))
    return ids


def query_builder_api(card_id: str) -> dict | None:
    try:
        r = requests.get(f"{BUILDER_API}/tickets/{card_id}", timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except requests.exceptions.RequestException:
        pass
    return None


def main():
    ids = sorted(discover_ids_from_ledger())
    if not ids:
        sys.stderr.write("No card IDs found in ledger; aborting.\n")
        sys.exit(1)

    for cid in ids:
        obj = query_builder_api(cid) or {
            "id": cid,
            "status": "unknown / not in Builder API yet",
            "title": "",
            "owner": "",
            "last_update": "",
            "ci_status": "",
        }
        print(json.dumps(obj, ensure_ascii=False))

if __name__ == "__main__":
    main() 