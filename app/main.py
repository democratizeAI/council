# -*- coding: utf-8 -*-
"""
SwarmAI FastAPI Main Application
🚀 ENHANCED: Integrated with production monitoring and model cache
"""

import os
import time
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse  # 🚀 PHASE A PATCH #4: Add streaming support
from pydantic import BaseModel
from prometheus_client import Histogram, Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from loader.deterministic_loader import boot_models, get_loaded_models
from app.router_intent import route, health_check
from router.voting import vote
from router.cost_tracking import debit, get_budget_status, get_cost_breakdown, downgrade_route
from router.hybrid import hybrid_route, smart_orchestrate
from router.council import council_route  # 🌌 Council integration
from router.traffic_controller import traffic_controller  # 🚦 Traffic controller
from api.whiteboard import wb  # 🗒️ Whiteboard API

# 🚀 NEW: Production monitoring integration
from monitoring.production_metrics import (
    start_production_monitoring, record_agent0_performance, 
    record_cloud_cost, get_production_metrics, get_system_health
)
from common.memory_manager import start_memory_system  # 🧠 Memory persistence

# 🚀 PHASE A PATCH #4: Add streaming imports
import json
import asyncio

# Prometheus metrics
REQUEST_LATENCY = Histogram(
    "swarm_router_request_latency", 
    "Router request latency in seconds",
    buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5)
)

ROUTER_REQUESTS = Counter(
    "swarm_router_requests_total",
    "Total router requests"
)

# Pydantic models for API
class OrchestrateRequest(BaseModel):
    prompt: str
    route: List[str]

class OrchestrateResponse(BaseModel):
    text: str
    model_used: str
    latency_ms: float
    cost_cents: float

class VotingRequest(BaseModel):
    prompt: str
    candidates: List[str]
    top_k: int = 2

class VotingResponse(BaseModel):
    text: str
    winner: Dict[str, Any]
    all_candidates: List[Dict[str, Any]]
    voting_stats: Dict[str, Any]
    total_cost_cents: float
    # 🎭 Council integration
    council_voices: Optional[List[Dict[str, Any]]] = None
    council_consensus: Optional[str] = None
    council_used: Optional[bool] = False

class BudgetResponse(BaseModel):
    budget_status: Dict[str, float]
    cost_breakdown: Dict[str, float]

class HybridRequest(BaseModel):
    prompt: str
    preferred_models: List[str] = []
    enable_council: Optional[bool] = None  # 🌌 Council toggle
    force_council: Optional[bool] = False  # 🌌 Force council deliberation

class HybridResponse(BaseModel):
    text: str
    provider: str
    model_used: str
    confidence: float
    hybrid_latency_ms: float
    cloud_consulted: bool
    cost_cents: float
    council_used: Optional[bool] = False  # 🌌 Council usage indicator
    council_voices: Optional[Dict[str, Any]] = None  # 🌌 Council voice breakdown

class VoteRequest(BaseModel):
    prompt: str
    heads: List[str]
    top_k: Optional[int] = 2

class CouncilRequest(BaseModel):
    prompt: str
    force_council: Optional[bool] = False

class CouncilResponse(BaseModel):
    text: str
    council_used: bool
    voice_responses: Dict[str, Any]
    total_latency_ms: float
    total_cost_dollars: float
    consensus_achieved: bool
    risk_flags: List[str]

class ChatRequest(BaseModel):
    prompt: str
    session_id: str = "default_session"

class ChatResponse(BaseModel):
    text: str
    voices: List[Dict[str, Any]]
    cost_usd: float
    model_chain: List[str]
    session_id: str

# Global variable to track model loading status
model_loading_summary = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    global model_loading_summary
    
    # Startup
    echo("[STARTUP] SwarmAI FastAPI starting up...")
    profile = os.environ.get("SWARM_GPU_PROFILE", "rtx_4070")
    echo(f"[PROFILE] Using GPU profile: {profile}")
    
    # 🚀 NEW: Start production monitoring first
    start_production_monitoring()
    echo("📊 Production monitoring started")
    
    # 🧠 NEW: Start memory system
    try:
        await start_memory_system()
        echo("🧠 Memory persistence system started")
    except Exception as e:
        echo(f"⚠️ Memory system startup warning: {e}")
    
    try:
        model_loading_summary = boot_models(profile=profile)
        echo(f"[OK] Model loading complete: {model_loading_summary}")
    except Exception as e:
        echo(f"[ERROR] Model loading failed: {e}")
        model_loading_summary = {"error": str(e)}
    
    print("🌌 Council-in-the-Loop: Initialized")
    print("🎯 Router 2.0 ready for requests")
    print("📊 Production monitoring active")
    
    yield
    
    # Shutdown
    echo("[SHUTDOWN] SwarmAI FastAPI shutting down...")
    
    # 🚀 NEW: Stop monitoring gracefully
    from monitoring.production_metrics import stop_production_monitoring
    stop_production_monitoring()
    
    # 🧠 NEW: Stop memory system gracefully
    try:
        from common.memory_manager import MEMORY_MANAGER
        await MEMORY_MANAGER.shutdown()
        echo("🧠 Memory system shutdown complete")
    except Exception as e:
        echo(f"⚠️ Memory shutdown warning: {e}")

# Create FastAPI app with lifespan management
app = FastAPI(
    title="SwarmAI Router 2.0",
    description="Intelligent AI model routing, orchestration, and confidence-weighted voting with cost tracking",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware to handle browser preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
)

# Register whiteboard API router
app.include_router(wb)

def echo(msg: str):
    """Safe logging function with ASCII-only output"""
    # Replace problematic emojis with ASCII equivalents
    safe_msg = msg.replace('🗳️', '[VOTE]').replace('🏆', '[WIN]').replace('💰', '[COST]').replace('❌', '[ERROR]').replace('⚠️', '[WARN]').replace('🎯', '[ROUTE]').replace('🌌', '[COUNCIL]').replace('📊', '[MONITOR]').replace('🧠', '[MEMORY]')
    print(time.strftime('%H:%M:%S'), safe_msg, flush=True)

# Register additional API routers after echo function is defined
# Memory API router for graduation suite compatibility
try:
    from api.memory_routes import router as memory_router
    app.include_router(memory_router)
    echo("[MEMORY] Memory API routes registered successfully")
except ImportError as e:
    echo(f"[MEMORY] Memory routes not available: {e}")

# OpenAI-compatible API router for graduation suite compatibility
try:
    from api.openai_compat import router as openai_router
    app.include_router(openai_router)
    echo("[OPENAI] OpenAI-compatible API routes registered successfully")
except ImportError as e:
    echo(f"[OPENAI] OpenAI-compat routes not available: {e}")

@app.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest):
    """Route a prompt to specified model heads with cost tracking"""
    
    start_time = time.time()
    
    try:
        ROUTER_REQUESTS.inc()
        
        # Apply budget-aware routing
        cost_optimized_route = downgrade_route(request.route)
        if cost_optimized_route != request.route:
            echo(f"💰 Budget-aware routing: {request.route} -> {cost_optimized_route}")
        
        with REQUEST_LATENCY.time():
            result = await route(request.prompt, cost_optimized_route)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Determine which model was actually used (simplified)
        loaded_models = get_loaded_models()
        available_heads = [h for h in cost_optimized_route if h in loaded_models]
        model_used = available_heads[0] if available_heads else "unknown"
        
        # Track cost
        tokens = len(result.split())  # Simple token estimate
        cost_cents = debit(model_used, tokens)
        
        return OrchestrateResponse(
            text=result,
            model_used=model_used,
            latency_ms=latency_ms,
            cost_cents=cost_cents
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vote", response_model=VotingResponse)
async def vote_endpoint(request: VotingRequest):
    """🎭 Enhanced Router 2.0: Confidence-weighted voting + Council deliberation"""
    
    start_time = time.time()
    
    try:
        ROUTER_REQUESTS.inc()
        
        echo(f"🗳️ Vote request: '{request.prompt[:50]}...' with {len(request.candidates)} candidates")
        
        # 🎭 COUNCIL DELIBERATION: Run Council first for additional perspective
        council_result = None
        council_voices = None
        council_consensus = None
        council_used = False
        
        try:
            from router.council import council_router
            
            echo(f"🎭 Running Council deliberation alongside voting...")
            deliberation = await council_router.council_deliberate(request.prompt)
            
            # Format Council voices for response
            council_voices = []
            for voice_enum, voice_response in deliberation.voice_responses.items():
                voice_dict = {
                    "voice": voice_enum.value.title(),  # reason -> Reason
                    "reply": voice_response.response,
                    "tokens": len(voice_response.response.split()),
                    "cost": voice_response.cost_dollars,
                    "confidence": voice_response.confidence,
                    "model": voice_response.model_used
                }
                council_voices.append(voice_dict)
            
            council_consensus = deliberation.final_response
            council_used = True
            echo(f"🎭 Council deliberation complete: {len(council_voices)} voices")
            
        except Exception as e:
            echo(f"🎭 Council deliberation failed: {e}, continuing with traditional voting")
        
        # TRADITIONAL VOTING: Run the original voting system
        # Apply budget-aware candidate selection
        cost_optimized_candidates = downgrade_route(request.candidates)
        if cost_optimized_candidates != request.candidates:
            echo(f"💰 Budget-aware voting: {request.candidates} -> {cost_optimized_candidates}")
        
        with REQUEST_LATENCY.time():
            result = await vote(request.prompt, cost_optimized_candidates, request.top_k)
        
        # 📊 NEW: Record Agent-0 performance if this was an Agent-0 response
        if result.get("winner", {}).get("specialist") == "mistral_general":
            latency_ms = (time.time() - start_time) * 1000
            confidence = result.get("winner", {}).get("confidence", 0.0)
            record_agent0_performance(latency_ms, confidence)
        
        # Track costs for all candidates that responded
        total_cost_cents = 0.0
        all_candidates = result.get("all_candidates", result.get("candidates", []))
        
        for candidate in all_candidates:
            # Safely estimate tokens from response snippet
            response_text = candidate.get("response_snippet", candidate.get("text", ""))
            if isinstance(response_text, str):
                tokens = len(response_text.split())
                model_name = candidate.get("model", candidate.get("specialist", "unknown"))
                cost = debit(model_name, tokens)
                total_cost_cents += cost
        
        # Add Council cost if used
        if council_used and deliberation:
            total_cost_cents += deliberation.total_cost_dollars * 100  # Convert dollars to cents
        
        # 🎭 ENHANCED RESPONSE: Include both voting results + Council deliberation
        return VotingResponse(
            text=result["text"],
            winner=result["winner"],
            all_candidates=all_candidates,  # Use the candidates we found
            voting_stats=result.get("voting_stats", {}),
            total_cost_cents=total_cost_cents,
            # 🎭 Council integration
            council_voices=council_voices,
            council_consensus=council_consensus,
            council_used=council_used
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/budget", response_model=BudgetResponse)
async def budget():
    """Get current budget status and cost breakdown"""
    try:
        return BudgetResponse(
            budget_status=get_budget_status(),
            cost_breakdown=get_cost_breakdown()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Budget check failed: {e}")

@app.get("/health")
async def health():
    """Health check endpoint with production monitoring"""
    try:
        result = await health_check()
        
        # Add council-specific health info
        council_status = traffic_controller.get_status()
        
        # 📊 NEW: Add production monitoring health
        monitoring_health = get_system_health()
        
        return {
            **result,
            "council": {
                "enabled": council_status["council_enabled"],
                "traffic_percent": council_status["traffic_percent"],
                "controller_active": council_status["controller_active"]
            },
            "monitoring": monitoring_health,
            "production_ready": (
                monitoring_health.get("system_health", 0) > 0.5 and
                monitoring_health.get("monitoring_active", False)
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

@app.get("/healthz")
async def healthz():
    """Load balancer health check with QPS metrics and production monitoring"""
    try:
        # Get basic health
        health_result = await health_check()
        
        # 📊 NEW: Get production monitoring status
        monitoring_health = get_system_health()
        
        # Add QPS metrics for load balancer
        return {
            "status": "healthy" if health_result.get("status") == "healthy" else "unhealthy",
            "local_qps": REQUEST_LATENCY._total._value if hasattr(REQUEST_LATENCY, '_total') else 0,
            "council_qps": COUNCIL_REQUESTS_TOTAL._value._value if 'COUNCIL_REQUESTS_TOTAL' in globals() else 0,
            "council_traffic_percent": traffic_controller.traffic_percent,
            "gpu_utilization": monitoring_health.get("gpu_utilization", 0),
            "system_health": monitoring_health.get("system_health", 0.5),
            "memory_queue": monitoring_health.get("scratchpad_queue", 0),
            "production_alerts_active": monitoring_health.get("monitoring_active", False),
            "timestamp": time.time()
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/models")
async def models():
    """Get currently loaded models with cache statistics"""
    try:
        loaded_models = get_loaded_models()
        
        models_info = {}
        for name, info in loaded_models.items():
            models_info[name] = {
                "backend": info.get("backend", "unknown"),
                "type": info.get("type", "unknown"),
                "vram_mb": info.get("vram_mb", 0),
                "loaded_at": info.get("loaded_at", 0)
            }
        
        # 🚀 NEW: Add model cache statistics
        try:
            from router.model_cache import get_model_stats
            cache_stats = get_model_stats()
        except Exception as e:
            cache_stats = {"error": str(e)}
        
        return {
            "total_models": len(loaded_models),
            "loaded_models": models_info,  # Include this field for test compatibility
            "models": models_info,  # Keep this too for new API
            "loading_summary": model_loading_summary,
            "cache_stats": cache_stats  # 🚀 NEW: Model cache information
        }
    except Exception as e:
        echo(f"❌ Models endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {e}")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint with production monitoring"""
    try:
        # Get standard metrics
        standard_metrics = generate_latest()
        
        # 📊 NEW: Get production monitoring metrics
        production_metrics = get_production_metrics()
        
        # Combine metrics
        combined_metrics = standard_metrics.decode() + "\n" + production_metrics
        
        return Response(combined_metrics.encode(), media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        # Fallback to standard metrics
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/metrics/production")
async def production_metrics_endpoint():
    """Production-only metrics endpoint"""
    try:
        metrics_text = get_production_metrics()
        return Response(metrics_text, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Production metrics failed: {e}")

@app.get("/status/production")
async def production_status():
    """Production status dashboard endpoint"""
    try:
        health_summary = get_system_health()
        
        # 🧠 NEW: Add memory system status
        try:
            from common.memory_manager import get_memory_stats
            memory_stats = get_memory_stats()
        except Exception as e:
            memory_stats = {"error": str(e)}
        
        return {
            "timestamp": time.time(),
            "system_health": health_summary,
            "memory_system": memory_stats,
            "uptime_seconds": time.time() - (health_summary.get("start_time", time.time())),
            "alerts_configured": [
                "gpu_utilization < 20% for 3min",
                "agent0_latency_p95 > 400ms", 
                "cloud_spend > $0.50/day",
                "scratchpad_queue > 1,000 entries"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Production status failed: {e}")

@app.post("/hybrid", response_model=HybridResponse)
async def hybrid_endpoint(request: HybridRequest):
    """Enhanced hybrid local+cloud+council routing endpoint with monitoring"""
    
    start_time = time.time()
    
    try:
        ROUTER_REQUESTS.inc()
        
        # 🌌 Council integration logic
        council_result = None
        council_used = False
        
        # Check if council should be used
        if request.force_council or request.enable_council:
            echo(f"🌌 Council requested for: '{request.prompt[:50]}...'")
            
            # Temporarily enable council if requested
            original_enabled = os.environ.get("SWARM_COUNCIL_ENABLED", "false")
            if request.enable_council or request.force_council:
                os.environ["SWARM_COUNCIL_ENABLED"] = "true"
            
            try:
                with REQUEST_LATENCY.time():
                    council_result = await council_route(request.prompt)
                
                if council_result.get("council_used", False):
                    council_used = True
                    echo(f"🌌 Council deliberation completed")
                
                # Restore original setting
                os.environ["SWARM_COUNCIL_ENABLED"] = original_enabled
                
            except Exception as e:
                echo(f"🌌 Council failed, falling back to hybrid: {e}")
                os.environ["SWARM_COUNCIL_ENABLED"] = original_enabled
                council_result = None
        
        # If council succeeded, use its result
        if council_used and council_result:
            cost_cents = council_result.get("total_cost_cents", 0.0)
            
            return HybridResponse(
                text=council_result["text"],
                provider="council",
                model_used="five_voice_council",
                confidence=council_result.get("consensus_confidence", 0.9),
                hybrid_latency_ms=council_result.get("total_latency_ms", 0.0),
                cloud_consulted=council_result.get("cloud_consulted", False),
                cost_cents=cost_cents,
                council_used=True,
                council_voices=council_result.get("voice_summary", {})
            )
        
        # Fall back to standard hybrid routing
        with REQUEST_LATENCY.time():
            result = await hybrid_route(request.prompt, request.preferred_models or None)
        
        # 📊 NEW: Record performance metrics
        latency_ms = result.get("hybrid_latency_ms", 0.0)
        confidence = result.get("confidence", 0.0)
        
        # Record Agent-0 performance if it was used
        if result.get("provider") == "local_smart" and "agent" in result.get("model_used", "").lower():
            record_agent0_performance(latency_ms, confidence)
        
        # Record cloud costs if cloud was used
        if result.get("cloud_consulted", False):
            provider = result.get("provider", "unknown")
            cost_usd = result.get("cost_cents", 0) / 100.0
            if cost_usd > 0:
                record_cloud_cost(provider, cost_usd, result.get("model_used", "unknown"))
        
        return HybridResponse(
            text=result["text"],
            provider=result.get("provider", "unknown"),
            model_used=result.get("model_used", "unknown"),
            confidence=result.get("confidence", 0.0),
            hybrid_latency_ms=result.get("hybrid_latency_ms", 0.0),
            cloud_consulted=result.get("cloud_consulted", False),
            cost_cents=result.get("cost_cents", 0.0),
            council_used=False,
            council_voices=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/council", response_model=CouncilResponse)
async def council_endpoint(request: CouncilRequest):
    """🌌 Dedicated Council-in-the-Loop deliberation endpoint"""
    
    start_time = time.time()
    
    try:
        echo(f"🌌 Council deliberation: '{request.prompt[:50]}...'")
        
        # Force council if requested
        if request.force_council:
            original_enabled = os.environ.get("SWARM_COUNCIL_ENABLED", "false")
            os.environ["SWARM_COUNCIL_ENABLED"] = "true"
            
            # Lower token threshold for forced council
            original_tokens = os.environ.get("COUNCIL_MIN_TOKENS", "20")
            os.environ["COUNCIL_MIN_TOKENS"] = "1"
            
            try:
                result = await council_route(request.prompt)
                
                # Restore settings
                os.environ["SWARM_COUNCIL_ENABLED"] = original_enabled
                os.environ["COUNCIL_MIN_TOKENS"] = original_tokens
                
            except Exception as e:
                # Restore settings on error
                os.environ["SWARM_COUNCIL_ENABLED"] = original_enabled
                os.environ["COUNCIL_MIN_TOKENS"] = original_tokens
                raise e
        else:
            result = await council_route(request.prompt)
        
        return CouncilResponse(
            text=result["text"],
            council_used=result.get("council_used", False),
            voice_responses=result.get("voice_responses", {}),
            total_latency_ms=result.get("total_latency_ms", 0.0),
            total_cost_dollars=result.get("total_cost_dollars", 0.0),
            consensus_achieved=result.get("consensus_achieved", False),
            risk_flags=result.get("risk_flags", [])
        )
        
    except Exception as e:
        echo(f"❌ Council error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/council/status")
async def council_status():
    """🌌 Get council configuration and status"""
    try:
        from router.council import council_router
        
        return {
            "council_enabled": council_router.council_enabled,
            "voice_models": {voice.value: model for voice, model in council_router.voice_models.items()},
            "budget_limits": {
                "max_cost_per_request": council_router.max_council_cost_per_request,
                "daily_budget": council_router.daily_council_budget
            },
            "trigger_config": {
                "min_tokens": council_router.min_tokens_for_council,
                "keywords": council_router.council_trigger_keywords
            },
            "performance_targets": {
                "p95_latency_ms": council_router.target_p95_latency_ms
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """🚀 FRONT-SPEAKER AGENT-0: Agent-0 always speaks first for instant responses"""
    
    try:
        # Import the updated router with Agent-0 first logic
        from router_cascade import RouterCascade
        
        echo(f"🚀 Agent-0 first chat: '{request.prompt[:50]}...' (session: {request.session_id})")
        
        # Initialize router with session context
        router = RouterCascade()
        router.current_session_id = request.session_id
        
        # Use the new Agent-0 first routing
        result = await router.route_query(request.prompt)
        
        # Extract response details
        response_text = result.get("text", "")
        confidence = result.get("confidence", 0.0)
        cost_usd = result.get("cost_usd", 0.0)
        model_used = result.get("model", "agent0")
        specialists_used = result.get("specialists_used", [])
        refinement_available = result.get("refinement_available", False)
        
        # Format voices for frontend compatibility
        voices_list = []
        
        # Always include Agent-0 as primary voice
        voices_list.append({
            "voice": "Agent-0",
            "reply": response_text,
            "tokens": len(response_text.split()),
            "cost": 0.0,  # Agent-0 is free
            "confidence": confidence,
            "model": model_used
        })
        
        # Add specialist voices if they were used
        for specialist in specialists_used:
            voices_list.append({
                "voice": specialist.title(),
                "reply": f"[Enhanced by {specialist}]",
                "tokens": 0,
                "cost": cost_usd / len(specialists_used) if specialists_used else 0.0,
                "confidence": 0.8,  # Estimated
                "model": f"{specialist}_specialist"
            })
        
        # Build model chain
        model_chain = [model_used]
        model_chain.extend(specialists_used)
        
        echo(f"✅ Agent-0 response: {confidence:.2f} confidence, {len(specialists_used)} specialists")
        
        return ChatResponse(
            text=response_text,
            voices=voices_list,
            cost_usd=cost_usd,
            model_chain=model_chain,
            session_id=request.session_id
        )
        
    except Exception as e:
        echo(f"❌ Agent-0 first chat error: {e}")
        # Fallback to simple Agent-0 response
        return ChatResponse(
            text=f"Hi! I understand you're asking: {request.prompt}. Let me help you with that.",
            voices=[{
                "voice": "Agent-0",
                "reply": "Fallback response",
                "tokens": 10,
                "cost": 0.0,
                "confidence": 0.5,
                "model": "agent0-fallback"
            }],
            cost_usd=0.0,
            model_chain=["agent0-fallback"],
            session_id=request.session_id
        )

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """🚀 FRONT-SPEAKER AGENT-0: Streaming with immediate Agent-0 draft + background refinement"""
    
    async def generate_stream():
        try:
            # Send immediate start signal
            yield f"data: {json.dumps({'type': 'start', 'text': '', 'session_id': request.session_id})}\n\n"
            await asyncio.sleep(0.01)
            
            echo(f"🚀 Agent-0 streaming: '{request.prompt[:50]}...'")
            
            # Import the updated router
            from router_cascade import RouterCascade
            
            # Initialize router with session context
            router = RouterCascade()
            router.current_session_id = request.session_id
            
            # Get Agent-0 response (which may trigger background refinement)
            agent0_start = time.time()
            result = await router.route_query(request.prompt)
            
            # Extract Agent-0 draft
            agent0_text = result.get("text", "")
            confidence = result.get("confidence", 0.0)
            refinement_available = result.get("refinement_available", False)
            refinement_task = result.get("refinement_task")
            
            agent0_latency = (time.time() - agent0_start) * 1000
            
            # 1️⃣ Stream Agent-0 draft immediately (word by word)
            words = agent0_text.split()
            streamed_text = ""
            
            for i, word in enumerate(words):
                if i > 0:
                    streamed_text += " "
                streamed_text += word
                
                # Send progressive Agent-0 draft
                chunk_data = {
                    'type': 'agent0_token',
                    'text': streamed_text,
                    'partial': True,
                    'progress': (i + 1) / len(words),
                    'confidence': confidence,
                    'refinement_pending': refinement_available
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
                await asyncio.sleep(0.03)  # Fast streaming for Agent-0
            
            # 2️⃣ Send Agent-0 completion
            agent0_complete = {
                'type': 'agent0_complete',
                'text': agent0_text,
                'partial': False,
                'meta': {
                    'voice': 'Agent-0',
                    'confidence': confidence,
                    'latency_ms': agent0_latency,
                    'total_tokens': len(words),
                    'refinement_pending': refinement_available
                },
                'session_id': request.session_id
            }
            yield f"data: {json.dumps(agent0_complete)}\n\n"
            
            # 3️⃣ If refinement is running, show status and wait for completion
            if refinement_available and refinement_task:
                # Show refinement status
                refine_status = {
                    'type': 'refinement_status',
                    'text': '⚙️ Specialists are refining the answer...',
                    'status': 'refining'
                }
                yield f"data: {json.dumps(refine_status)}\n\n"
                
                try:
                    # Wait for background refinement with timeout
                    refined_result = await asyncio.wait_for(refinement_task, timeout=10.0)
                    
                    # Check if refinement improved the answer
                    refined_text = refined_result.get("text", "")
                    refinement_type = refined_result.get("refinement_type", "none")
                    specialists_used = refined_result.get("specialists_used", [])
                    
                    if refined_text != agent0_text and refinement_type != "none":
                        # Refinement improved the answer - send update
                        refinement_update = {
                            'type': 'refinement_complete',
                            'text': refined_text,
                            'original_text': agent0_text,
                            'meta': {
                                'refinement_type': refinement_type,
                                'specialists_used': specialists_used,
                                'improvement': True
                            }
                        }
                        yield f"data: {json.dumps(refinement_update)}\n\n"
                    else:
                        # No improvement - Agent-0 answer stands
                        no_improvement = {
                            'type': 'refinement_complete',
                            'text': agent0_text,
                            'meta': {
                                'improvement': False,
                                'message': 'Agent-0 answer was already optimal'
                            }
                        }
                        yield f"data: {json.dumps(no_improvement)}\n\n"
                        
                except asyncio.TimeoutError:
                    # Refinement timed out
                    timeout_msg = {
                        'type': 'refinement_timeout',
                        'text': agent0_text,
                        'meta': {
                            'message': 'Refinement timed out - using Agent-0 answer'
                        }
                    }
                    yield f"data: {json.dumps(timeout_msg)}\n\n"
                except Exception as e:
                    # Refinement failed
                    error_msg = {
                        'type': 'refinement_error',
                        'text': agent0_text,
                        'meta': {
                            'message': f'Refinement failed: {str(e)}'
                        }
                    }
                    yield f"data: {json.dumps(error_msg)}\n\n"
            
            # 4️⃣ Send final completion
            final_data = {
                'type': 'stream_complete',
                'session_id': request.session_id,
                'meta': {
                    'total_latency_ms': (time.time() - agent0_start) * 1000,
                    'agent0_latency_ms': agent0_latency,
                    'refinement_used': refinement_available
                }
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            error_data = {
                'type': 'error', 
                'text': f"Streaming error: {str(e)}",
                'error': str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 