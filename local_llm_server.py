#!/usr/bin/env python3
"""
Local LLM Server Mock for AutoGen Council Development
=====================================================

Provides a simple OpenAI-compatible API for local development when no real LLM server is available.
Runs on port 8001 by default.
"""

import json
import time
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Local LLM Server Mock", version="1.0.0")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "local-llm"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]
    usage: dict

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "local-llm",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local"
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "local"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Handle chat completion requests"""
    
    # Get the last user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    # Generate a simple response based on the input
    if "math" in user_message.lower() or any(op in user_message for op in ["+", "-", "*", "/", "="]):
        response_text = "I can help with math! For complex calculations, please use the specialized math endpoint."
    elif "code" in user_message.lower() or "python" in user_message.lower():
        response_text = "I can help with code! For code execution, please use the secure sandbox environment."
    elif "memory" in user_message.lower() or "remember" in user_message.lower():
        response_text = "I can help with memory! Information will be stored in the FAISS vector database."
    else:
        response_text = f"This is a mock response to: {user_message[:50]}... Please configure a real LLM server for full functionality."
    
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_message.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(user_message.split()) + len(response_text.split())
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "local-llm-server", "version": "1.0.0"}

if __name__ == "__main__":
    print("[LLM] Starting Local LLM Server Mock on port 8001")
    print("[LLM] OpenAI-compatible API available at http://localhost:8001/v1")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info") 