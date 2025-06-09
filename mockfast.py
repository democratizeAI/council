# mockfast.py – ultra-fast mock Council API
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class ChatReq(BaseModel):
    prompt: str | None = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/models")
def models():
    return {
        "models": [
            "tinyllama_1b",
            "mistral_7b_instruct", 
            "phi2_2.7b",
            "math_specialist_0.8b"
        ],
        "status": "mock_loaded"
    }

@app.post("/orchestrate")
@app.post("/vote") 
@app.post("/hybrid/stream")
def mock_chat(_: ChatReq):
    return {
        "content": "💡 mock response (Tiny-LLaMA bypass)",
        "latency_ms": 42,
        "model": "mock-llm"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 