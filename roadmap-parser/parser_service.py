import asyncio
import json
import re
from pathlib import Path
import os

from fastapi import FastAPI
from nats.aio.client import Client as NATS

app = FastAPI(title="roadmap-parser")

ROADMAP_PATH = Path("/workspace/TRINITY_ROADMAP.md")

# Simple markdown parser (clarity + basic lists)

def expand_includes(md: str) -> str:
    """Replace lines like '%% include: path/to/file' with the file's contents"""
    def repl(match):
        inc_path = match.group(1).strip()
        # Allow absolute or relative to repo root
        p = Path(inc_path)
        if not p.is_absolute():
            p = Path.cwd() / inc_path
        try:
            return p.read_text()
        except Exception:
            return f"<!-- include failed: {inc_path} -->"

    return re.sub(r"^%%\s*include:\s*(.+)$", repl, md, flags=re.MULTILINE)

def parse_markdown(md: str):
    md = expand_includes(md)
    data = {
        "clarity": 100.0,
        "sections": [],
        "todos": [],
        "completed": [],
        "planned": [],
        "mermaids": []
    }

    for line in md.splitlines():
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("# ")
            data["sections"].append({"level": level, "title": title})

    for match in re.finditer(r"```mermaid\n(.*?)\n```", md, re.DOTALL):
        data["mermaids"].append(match.group(1))

    unclear = len(re.findall(r"\?\?\?|TBD|TODO", md, re.IGNORECASE))
    lines = max(1, len(md.splitlines()))
    data["clarity"] = max(0, 100 - unclear / lines * 100)
    return data

@app.on_event("startup")
async def startup():
    app.state.nc = NATS()
    await app.state.nc.connect("nats://nats:4222")

    async def message_handler(msg):
        parsed = parse_markdown(msg.data.decode())
        await app.state.nc.publish("roadmap.parsed", json.dumps(parsed).encode())
    await app.state.nc.subscribe("roadmap.updated", cb=message_handler)

@app.on_event("shutdown")
async def shutdown():
    if app.state.nc.is_connected:
        await app.state.nc.close()

@app.get("/health")
async def health():
    return {"status": "ok"} 