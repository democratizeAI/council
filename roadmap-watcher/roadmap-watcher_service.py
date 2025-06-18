import asyncio
from fastapi import FastAPI
from nats.aio.client import Client as NATS
import os
import hashlib
from pathlib import Path

app = FastAPI(title="roadmap-watcher")

TRINITY_ROADMAP = Path("/workspace/TRINITY_ROADMAP.md") if os.getenv("DOCKER") else Path("TRINITY_ROADMAP.md")

async def watch_roadmap(nc):
    last_hash = None
    while True:
        try:
            content = TRINITY_ROADMAP.read_bytes()
            current_hash = hashlib.sha256(content).hexdigest()
            if current_hash != last_hash:
                last_hash = current_hash
                await nc.publish("roadmap.updated", content)
        except FileNotFoundError:
            pass
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup():
    app.state.nc = NATS()
    await app.state.nc.connect("nats://nats:4222")
    app.state.watcher_task = asyncio.create_task(watch_roadmap(app.state.nc))

@app.on_event("shutdown")
async def shutdown():
    if app.state.watcher_task:
        app.state.watcher_task.cancel()
    if app.state.nc.is_connected:
        await app.state.nc.close()

@app.get("/health")
async def health():
    return {"service": "roadmap-watcher", "status": "ok"}
