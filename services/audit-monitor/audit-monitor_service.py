import asyncio
from fastapi import FastAPI
import json, time
from nats.aio.client import Client as NATS
from typing import Dict

app = FastAPI(title="audit-monitor")
STATE: Dict[str, int] = {
    "ledger_events": 0,
    "builder_events": 0,
    "council_decisions": 0,
    "guardian_vetos": 0,
    "rollbacks": 0,
    "last_event_ts": None,
}

async def _increment(key: str):
    STATE[key] += 1
    STATE["last_event_ts"] = time.time()

async def _connect_nats():
    nc = NATS()
    await nc.connect("nats://nats:4222")

    async def ledger_cb(msg):
        await _increment("ledger_events")
    async def builder_cb(msg):
        await _increment("builder_events")
    async def council_cb(msg):
        await _increment("council_decisions")
    async def veto_cb(msg):
        await _increment("guardian_vetos")
    async def rollback_cb(msg):
        await _increment("rollbacks")

    await nc.subscribe("ledger.*", cb=ledger_cb)
    await nc.subscribe("builder.events.*", cb=builder_cb)
    await nc.subscribe("council.decision.*", cb=council_cb)
    await nc.subscribe("guardian.veto", cb=veto_cb)
    await nc.subscribe("rollback.*", cb=rollback_cb)

    app.state.nc = nc

@app.on_event("startup")
async def startup():
    asyncio.create_task(_connect_nats())

@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "nc") and app.state.nc.is_connected:
        await app.state.nc.close()

@app.get("/health")
async def health():
    return {"status": "ok", **STATE}

@app.get("/metrics")
async def metrics():
    lines = [
        f"trinity_audit_ledger_total {STATE['ledger_events']}",
        f"trinity_audit_builder_total {STATE['builder_events']}",
        f"trinity_audit_council_decision_total {STATE['council_decisions']}",
        f"trinity_audit_guardian_veto_total {STATE['guardian_vetos']}",
        f"trinity_audit_rollbacks_total {STATE['rollbacks']}",
    ]
    return "\n".join(lines)

@app.post("/trigger_rollback")
async def trigger_rollback():
    if not hasattr(app.state, "nc") or not app.state.nc.is_connected:
        return {"error": "NATS not connected"}
    await app.state.nc.publish("audit.test.rollback", json.dumps({"ts": time.time()}).encode())
    return {"status": "rollback_requested"}
