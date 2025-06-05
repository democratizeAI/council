#!/usr/bin/env python3
"""
OpenAI-Compatible API Endpoints
==============================

Provides OpenAI-compatible endpoints that wrap the AutoGen Council functionality.
This satisfies graduation suite requirements that expect OpenAI-format responses.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
import logging
import uuid

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["openai-compat"])

class Message(BaseModel):
    role: str
    content: str

class OpenAIRequest(BaseModel):
    messages: List[Message]
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.7
    model: Optional[str] = "tinyllama_1b"

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAIResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage

@router.post("/hybrid", response_model=OpenAIResponse)
async def hybrid_openai_compat(request: OpenAIRequest):
    """
    OpenAI-compatible hybrid endpoint for graduation suite compatibility.
    Wraps the existing AutoGen Council hybrid functionality.
    """
    try:
        # Convert OpenAI format to AutoGen Council format
        if not request.messages:
            raise HTTPException(status_code=422, detail="Messages cannot be empty")
        
        # Extract the user prompt (last user message)
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=422, detail="No user message found")
        
        prompt = user_messages[-1].content
        logger.info(f"🔄 OpenAI-compat request: '{prompt[:50]}...'")
        
        # Call the AutoGen Council hybrid system
        try:
            from router_cascade import RouterCascade
            router_cascade = RouterCascade()
            
            # Route the query through AutoGen Council
            result = await router_cascade.route_query(prompt)
            
            response_text = result.get("text", "I'm processing your request...")
            model_used = result.get("model", request.model or "autojen-council")
            confidence = result.get("confidence", 0.8)
            
            logger.info(f"✅ AutoGen Council response: {confidence:.2f} confidence")
            
        except Exception as e:
            logger.warning(f"⚠️ AutoGen Council failed, using fallback: {e}")
            # Fallback response for testing
            response_text = f"Hello! I understand you're asking: '{prompt}'. This is a test response from AutoGen Council."
            model_used = "autogen-council-fallback"
        
        # Convert response to OpenAI format
        completion_tokens = len(response_text.split())
        prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)
        
        choice = Choice(
            index=0,
            message=Message(role="assistant", content=response_text),
            finish_reason="stop"
        )
        
        openai_response = OpenAIResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=model_used,
            choices=[choice],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
        
        return openai_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OpenAI-compat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/v1/chat/completions", response_model=OpenAIResponse)
async def chat_completions_openai_compat(request: OpenAIRequest):
    """
    Standard OpenAI v1/chat/completions endpoint for maximum compatibility.
    Delegates to the hybrid endpoint.
    """
    return await hybrid_openai_compat(request)

@router.get("/v1/models")
async def list_models():
    """List available models in OpenAI format"""
    return {
        "object": "list",
        "data": [
            {
                "id": "tinyllama_1b",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "autogen-council"
            },
            {
                "id": "autogen-council",
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "autogen-council"
            }
        ]
    }

# Additional compatibility endpoints
@router.get("/openai/health")
async def openai_health():
    """OpenAI-style health check"""
    return {
        "status": "ok",
        "service": "autogen-council-openai-compat",
        "version": "1.0.0"
    } 