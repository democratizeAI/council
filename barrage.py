#!/usr/bin/env python3
"""
barrage.py – feeds Council a batch of prompts, throttles to one
request every 12 s, respects $10/day budget guard, and writes ND-JSON.
"""
import json, time, requests, sys
from datetime import datetime

ENDPOINT = "http://localhost:9000/orchestrate"
PAUSE    = 12        # seconds between calls (5 req/min keeps queue depth tiny)
PROMPTS  = [
  "What Grafana panels are still missing for production-grade observability?",
  "List the top three auth or data-privacy vulnerabilities still present.",
  "What CI gates or SBOM steps should be added before auto-merge?",
  "What onboarding docs or front-end screens must exist before GA?"
]

with open("council_barrage.ndjson", "w") as fout:
    for p in PROMPTS:
        body = {"prompt": p, "route": ["gpt-4o-mini"]}
        t0   = time.time()
        resp = requests.post(ENDPOINT, json=body, timeout=60).json()
        latency = time.time() - t0
        record  = {
            "ts": datetime.utcnow().isoformat()+"Z",
            "prompt": p,
            "latency_s": round(latency,2),
            "reply": resp
        }
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"✔ {p[:30]}… ({latency:.1f}s)")
        time.sleep(PAUSE) 