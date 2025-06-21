import asyncio
from fastapi import FastAPI
from nats.aio.client import Client as NATS

app = FastAPI(title="cloud-auditor")

@app.on_event("startup")
async def startup():
    app.state.nc = NATS()
    await app.state.nc.connect("nats://nats:4222")

@app.on_event("shutdown")
async def shutdown():
    if app.state.nc.is_connected:
        await app.state.nc.close()

@app.get("/health")
async def health():
    return {"service": "cloud-auditor", "status": "ok"}
