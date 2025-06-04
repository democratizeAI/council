#!/usr/bin/env python3
"""
Simple FastAPI Test
"""
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "message": "Simple API working"}

@app.post("/hybrid")
def hybrid(req: dict):
    return {
        "text": f"Echo: {req.get('prompt', 'no prompt')}",
        "model": "test",
        "latency_ms": 1.0,
        "skill_type": "test",
        "confidence": 1.0,
        "timestamp": "2024-01-01T00:00:00"
    }

if __name__ == "__main__":
    print("🧪 Starting simple FastAPI test on :8001")
    uvicorn.run(app, host="0.0.0.0", port=8001) 