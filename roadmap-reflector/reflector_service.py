import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any

import docker
from fastapi import FastAPI
from prometheus_client import Gauge, Counter, start_http_server
from nats.aio.client import Client as NATS

app = FastAPI(title="roadmap-reflector")

nc: NATS

docker_client = docker.from_env()

# Prometheus metrics
alignment_gauge = Gauge("trinity_roadmap_alignment_percent", "Roadmap completion alignment")
clarity_gauge = Gauge("trinity_roadmap_clarity_percent", "Roadmap clarity %")
missing_services = Gauge("trinity_missing_services_total", "Number of services referenced in roadmap but not running")
gap_counter = Counter("trinity_roadmap_gaps_total", "Total gaps detected", ["type"])


@app.on_event("startup")
async def startup():
    global nc
    nc = NATS()
    await nc.connect("nats://nats:4222")

    async def process(msg):
        parsed = json.loads(msg.data.decode())
        gaps = compute_gaps(parsed)
        # Update metrics
        clarity_gauge.set(parsed.get("clarity", 0))
        alignment_gauge.set(100 - len(gaps) * 5)  # crude placeholder
        for g in gaps:
            gap_counter.labels(g["type"]).inc()
        missing_services.set(len([g for g in gaps if g["type"] == "missing_service"]))
        await nc.publish("roadmap.gaps", json.dumps(gaps).encode())

    await nc.subscribe("roadmap.parsed", cb=process)
    # expose metrics
    start_http_server(9902)


def compute_gaps(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []
    # clarity gap
    if parsed.get("clarity", 100) < 90:
        gaps.append({"type": "low_clarity", "score": parsed["clarity"]})
    # missing services: look for section titles ending with "service"
    roadmap_services = {
        s["title"].split()[0].lower()
        for s in parsed.get("sections", [])
        if "service" in s["title"].lower()
    }
    running = {c.name.split("-")[1] if "-" in c.name else c.name for c in docker_client.containers.list()}
    for svc in roadmap_services - running:
        gaps.append({"type": "missing_service", "name": svc})
    return gaps


@app.get("/health")
async def health():
    return {"status": "ok"} 