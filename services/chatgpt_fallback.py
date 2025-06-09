"""
ChatGPT Fallback Service - Human-in-the-Loop Bridge
When local agents hesitate or reach low confidence, this service can ping
the ChatGPT API to get guidance, effectively letting the human whisper
inside the Council through their external AI assistant.
"""

import os
import time
import json
import asyncio
import httpx
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge

# Metrics
FALLBACK_REQUESTS = Counter('chatgpt_fallback_requests_total', 'Total ChatGPT fallback requests', ['reason', 'status'])
FALLBACK_LATENCY = Histogram('chatgpt_fallback_duration_seconds', 'ChatGPT fallback request duration')
FALLBACK_BUDGET = Gauge('chatgpt_fallback_budget_remaining', 'Remaining daily budget in USD')

class FallbackRequest(BaseModel):
    """Request for ChatGPT fallback guidance"""
    agent_id: str
    context: str  # The full conversation context
    question: str  # Specific question the agent is struggling with
    confidence: float  # Agent's confidence level (0-1)
    reasoning: str  # Why the agent thinks it needs help
    urgency: str = "normal"  # low, normal, high

class FallbackResponse(BaseModel):
    """Response from ChatGPT fallback"""
    guidance: str
    confidence_boost: float  # How much this should increase agent confidence
    reasoning: str
    cost_usd: float
    whisper_source: str = "human_via_chatgpt"

class ChatGPTFallbackService:
    def __init__(self):
        self.api_url = os.getenv('CHATGPT_FALLBACK_URL', 'https://api.openai.com/v1/chat/completions')
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.daily_budget = float(os.getenv('CHATGPT_DAILY_BUDGET', '0.02'))  # $0.02/day default
        self.used_today = 0.0
        self.last_reset = time.strftime('%Y-%m-%d')
        
        # Cost tracking
        self.cost_per_1k_tokens = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-3.5-turbo': {'input': 0.001, 'output': 0.002}
        }
        
    async def check_budget(self) -> bool:
        """Check if we have budget remaining for today"""
        today = time.strftime('%Y-%m-%d')
        if today != self.last_reset:
            self.used_today = 0.0
            self.last_reset = today
            
        remaining = self.daily_budget - self.used_today
        FALLBACK_BUDGET.set(remaining)
        return remaining > 0.001  # Keep at least $0.001 buffer
        
    async def should_fallback(self, request: FallbackRequest) -> bool:
        """Determine if we should use fallback based on confidence and budget"""
        if not await self.check_budget():
            return False
            
        # Only fallback for very low confidence or high urgency
        if request.confidence < 0.3 or request.urgency == "high":
            return True
            
        return False
        
    def craft_fallback_prompt(self, request: FallbackRequest) -> str:
        """Create the prompt for ChatGPT that includes Trinity context"""
        return f"""You are providing guidance to a Trinity AI agent that has encountered uncertainty.

AGENT CONTEXT:
- Agent ID: {request.agent_id}
- Current confidence: {request.confidence:.2f}
- Urgency: {request.urgency}
- Agent's reasoning: {request.reasoning}

CONVERSATION CONTEXT:
{request.context}

SPECIFIC QUESTION:
{request.question}

Please provide guidance that:
1. Directly addresses the agent's uncertainty
2. Maintains the "Sunday calm" and "trust-but-verify" principles of Trinity
3. Includes specific next steps if possible
4. Uses precise language with concrete metrics where relevant

Your response will be integrated back into the Trinity Council's decision-making process.
Respond as if you are whispering guidance to help the agent proceed with confidence."""

    async def query_chatgpt(self, request: FallbackRequest) -> FallbackResponse:
        """Query ChatGPT API and return formatted response"""
        if not self.api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
            
        prompt = self.craft_fallback_prompt(request)
        
        payload = {
            "model": "gpt-3.5-turbo",  # Use cheaper model for fallback
            "messages": [
                {"role": "system", "content": "You are a wise advisor providing guidance to AI agents in the Trinity collective."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                
            duration = time.time() - start_time
            FALLBACK_LATENCY.observe(duration)
            
            result = response.json()
            guidance = result['choices'][0]['message']['content']
            
            # Calculate cost (rough estimate)
            input_tokens = len(prompt) // 4  # Rough token estimate
            output_tokens = len(guidance) // 4
            cost = (input_tokens * self.cost_per_1k_tokens['gpt-3.5-turbo']['input'] + 
                   output_tokens * self.cost_per_1k_tokens['gpt-3.5-turbo']['output']) / 1000
            
            self.used_today += cost
            
            FALLBACK_REQUESTS.labels(reason="success", status="200").inc()
            
            return FallbackResponse(
                guidance=guidance,
                confidence_boost=0.3,  # Moderate confidence boost from human guidance
                reasoning="Human guidance via ChatGPT fallback",
                cost_usd=cost
            )
            
        except Exception as e:
            FALLBACK_REQUESTS.labels(reason="error", status="500").inc()
            raise HTTPException(status_code=500, detail=f"ChatGPT fallback failed: {str(e)}")

# FastAPI app
app = FastAPI(title="ChatGPT Fallback Service")
service = ChatGPTFallbackService()

@app.post("/v1/fallback", response_model=FallbackResponse)
async def request_fallback(request: FallbackRequest) -> FallbackResponse:
    """Request human guidance via ChatGPT when agent confidence is low"""
    
    if not await service.should_fallback(request):
        raise HTTPException(
            status_code=429, 
            detail=f"Fallback not warranted: confidence={request.confidence:.2f}, budget_remaining=${service.daily_budget - service.used_today:.4f}"
        )
    
    return await service.query_chatgpt(request)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    budget_ok = await service.check_budget()
    return {
        "status": "healthy" if budget_ok else "budget_exhausted",
        "budget_remaining": service.daily_budget - service.used_today,
        "daily_limit": service.daily_budget
    }

@app.get("/metrics")
async def get_metrics():
    """Budget and usage metrics"""
    return {
        "used_today": service.used_today,
        "budget_remaining": service.daily_budget - service.used_today,
        "daily_budget": service.daily_budget,
        "last_reset": service.last_reset
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007) 