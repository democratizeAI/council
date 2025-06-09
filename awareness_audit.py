#!/usr/bin/env python3
"""
awareness_audit.py – snapshots Council reply + key Prom metrics + builder status
emits ND-JSON (one object per line)
"""
import json, requests, subprocess, os, time
from datetime import datetime

def prom(q):  # tiny helper
    try:
        url = "http://localhost:9090/api/v1/query"
        r = requests.get(url, params={"query": q}, timeout=4)
        r.raise_for_status()
        return float(r.json()["data"]["result"][0]["value"][1])
    except Exception as e:
        print(f"Warning: Could not query Prometheus for {q}: {e}", file=os.sys.stderr)
        return 0.0

def safe_prom(q, default=0.0):
    """Safe prometheus query with fallback"""
    try:
        return prom(q)
    except:
        return default

metrics = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "cloud_est_usd_total": safe_prom("cloud_est_usd_total"),
    "queue_depth": safe_prom("avg_over_time(http_queue_depth[30s])"),
    "gpu_util": safe_prom("avg_over_time(nvidia_gpu_utilization[30s])"),
    "guardian_escalations_total": safe_prom("guardian_escalations_total")
}

# Load council response
try:
    with open("council_reply.json", "r") as f:
        council = json.load(f)
except Exception as e:
    council = {"error": f"Could not load council reply: {e}"}

# run the builder-status dump (assumes script is in PATH / repo root)
try:
    builder_lines = subprocess.check_output(
        ["python", "builder_status_dump.py"], text=True).strip().splitlines()
    builder_objs = [json.loads(line) for line in builder_lines if line.strip()]
except Exception as e:
    builder_objs = [{"error": f"Could not run builder status dump: {e}"}]

report = {
    "metrics": metrics,
    "council_audit": council,
    "builder_status": builder_objs
}

print(json.dumps(report, ensure_ascii=False, indent=2)) 