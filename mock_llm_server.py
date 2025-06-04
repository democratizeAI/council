#!/usr/bin/env python3
"""
Mock LLM Server for AutoGen Council Testing
Simulates ExLlamaV2 API for development and testing without requiring actual GPU model
"""

import time
import json
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn

app = FastAPI(title="Mock LLM Server", version="1.0.0")

# Mock responses for different query types
MOCK_RESPONSES = {
    "math": [
        "I can help you with that calculation. The answer is {result}.",
        "Let me solve this step by step: {result}",
        "The mathematical result is {result}."
    ],
    "code": [
        """Here's a Python solution:

```python
def hello_world():
    print("Hello, World!")
    return "Hello, World!"

# Call the function
hello_world()
```

This function prints and returns the classic "Hello, World!" message.""",
        """Here's a simple implementation:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Example usage
print(fibonacci(10))
```

This is a recursive implementation of the Fibonacci sequence.""",
        """Here's the factorial function:

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

# Example
print(factorial(5))  # Output: 120
```"""
    ],
    "general": [
        "I understand your question. Let me help you with that.",
        "That's an interesting topic. Here's what I can tell you:",
        "I'd be happy to assist you with this query.",
        "Let me provide you with a comprehensive answer:",
        "Based on my knowledge, I can explain this as follows:"
    ]
}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

class Model(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "mock-llm"

def detect_query_type(content: str) -> str:
    """Detect the type of query for better mock responses"""
    content_lower = content.lower()
    
    # Check for code-related keywords
    if any(word in content_lower for word in ['function', 'code', 'python', 'javascript', 'algorithm', 'implement', 'write']):
        return "code"
    
    # Check for math-related keywords  
    if any(word in content_lower for word in ['calculate', 'solve', 'math', 'equation', '+', '-', '*', '/', 'factorial', 'fibonacci']):
        return "math"
    
    return "general"

def generate_mock_response(content: str, query_type: str) -> str:
    """Generate contextual mock response based on query type"""
    import random
    
    if query_type == "math":
        # Simple math extraction for demo
        if "2+2" in content or "2 + 2" in content:
            return MOCK_RESPONSES["math"][0].format(result="4")
        elif "factorial" in content.lower():
            return "The factorial function computes n! = n × (n-1) × ... × 1. For example, 5! = 120."
        else:
            return random.choice(MOCK_RESPONSES["math"]).format(result="42")
    
    elif query_type == "code":
        return random.choice(MOCK_RESPONSES["code"])
    
    else:
        return random.choice(MOCK_RESPONSES["general"])

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "mistral-13b-gptq",
                "object": "model", 
                "owned_by": "mock-llm",
                "permission": []
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Generate chat completions"""
    
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")
    
    # Get the last user message
    user_message = None
    for message in reversed(request.messages):
        if message.role == "user":
            user_message = message.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    # Detect query type and generate response
    query_type = detect_query_type(user_message)
    response_text = generate_mock_response(user_message, query_type)
    
    # Simulate processing time
    time.sleep(0.1)  # 100ms latency simulation
    
    response = ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(time.time()),
        model=request.model,
        choices=[
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        usage={
            "prompt_tokens": len(user_message.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(user_message.split()) + len(response_text.split())
        }
    )
    
    return response.dict()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "model": "mistral-13b-gptq",
        "backend": "mock-llm",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Mock LLM Server",
        "version": "1.0.0", 
        "description": "OpenAI-compatible API for AutoGen Council testing",
        "endpoints": {
            "models": "/v1/models",
            "chat": "/v1/chat/completions",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Mock LLM Server...")
    print("📡 API Compatible with: ExLlamaV2, OpenAI")
    print("🔗 Endpoints:")
    print("   - Models: http://localhost:8000/v1/models")
    print("   - Chat: http://localhost:8000/v1/chat/completions")
    print("   - Health: http://localhost:8000/health")
    print("\n🧪 This is a MOCK server for testing/demo purposes")
    print("   Replace with real ExLlamaV2 for production use")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    ) 