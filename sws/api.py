# sws/api.py - SWS-Core API Integration
"""
🌐 SWS-Core API - Swarm-to-Swarm Services Platform
==================================================

FastAPI integration for all SWS-Core platform services:
- SWS-100: Graph Agent (topology introspection)
- SWS-110: Perms Agent (A2A access control)  
- SWS-120: Build Agent (agent scaffolding)
- SWS-130: Docs Agent (auto-documentation)

Transforms enterprise swarm into developer platform ecosystem.
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uvicorn

from .graph_agent import graph_agent, GraphAgent
from .perms_agent import perms_agent, PermsAgent, AgentRole
from .build_agent import build_agent, BuildAgent, ScaffoldResult
from .docs_agent import docs_agent, DocsAgent, DocumentationResult

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class TopologyRequest(BaseModel):
    """Request for topology introspection"""
    include_metrics: bool = True
    cache_ttl: Optional[int] = None

class AuthRequest(BaseModel):
    """A2A authorization request"""
    agent_id: str = Field(..., description="Agent requesting access")
    target_stream: str = Field(..., description="Target Redis stream")
    operation: str = Field(..., description="Operation: read, write, admin, create, delete")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class AgentRegistrationRequest(BaseModel):
    """Agent registration request"""
    agent_id: str = Field(..., description="Unique agent identifier")
    role: str = Field(..., description="Agent role: internal_core, internal_service, external_developer, external_premium, system_admin")
    created_by: str = Field(default="api", description="Who created this registration")

class ScaffoldRequest(BaseModel):
    """Agent scaffolding request"""
    intent: str = Field(..., description="What the agent should do", example="Monitor system health and send alerts")
    developer_id: str = Field(default="external", description="Developer requesting scaffolding")

class DocumentationRequest(BaseModel):
    """Documentation generation request"""
    agent_manifest: Dict[str, Any] = Field(..., description="Agent manifest with metadata")

class EcosystemDocRequest(BaseModel):
    """Ecosystem documentation request"""
    agents: List[Dict[str, Any]] = Field(..., description="List of agent manifests")

# Response models
class TopologyResponse(BaseModel):
    """Topology introspection response"""
    topology: Dict[str, Any]
    metrics: Dict[str, Any]
    meta: Dict[str, Any]

class AuthResponse(BaseModel):
    """Authorization response"""
    allowed: bool
    agent_id: str
    operation: str
    target_stream: str
    reason: str
    latency_ms: float
    cached: bool = False

class ScaffoldResponse(BaseModel):
    """Scaffolding response"""
    success: bool
    spec_id: str
    agent_name: str
    pr_url: Optional[str]
    branch_name: Optional[str]
    scaffold_time_seconds: float
    files_created: List[str]
    ci_gates_passed: bool
    error_message: Optional[str] = None

class DocumentationResponse(BaseModel):
    """Documentation generation response"""
    success: bool
    agent_id: str
    documentation: Optional[str]
    diagram: Optional[str]
    api_spec: Optional[Dict[str, Any]]
    quality_score: float
    auto_enhanced: bool
    generation_time_seconds: float
    error_message: Optional[str] = None

# Create FastAPI app
app = FastAPI(
    title="SWS-Core Platform API",
    description="Swarm-to-Swarm Services - Multi-Agent Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize all SWS agents"""
    logger.info("🚀 Starting SWS-Core Platform API")
    
    try:
        # Initialize all agents
        await graph_agent.initialize()
        await perms_agent.initialize()
        
        logger.info("✅ All SWS agents initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize SWS agents: {e}")
        raise

# Health check endpoint
@app.get("/health")
async def health_check():
    """Platform health check"""
    try:
        # Quick health checks for all agents
        redis_status = "healthy"
        try:
            await graph_agent.redis_client.ping()
        except:
            redis_status = "unhealthy"
            
        return {
            "status": "healthy" if redis_status == "healthy" else "degraded",
            "timestamp": time.time(),
            "version": "1.0.0",
            "components": {
                "graph_agent": "ready",
                "perms_agent": "ready", 
                "build_agent": "ready",
                "docs_agent": "ready",
                "redis": redis_status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ============================================================================
# SWS-100: Graph Agent Endpoints (Topology Introspection)
# ============================================================================

@app.get("/a2a/map", response_model=TopologyResponse)
async def get_topology_map(request: TopologyRequest = Depends()):
    """
    SWS-100: Agent→Agent topology introspection endpoint
    Returns DAG + metrics for swarm visualization
    """
    try:
        topology_data = await graph_agent.get_topology_map()
        
        return TopologyResponse(
            topology=topology_data["topology"],
            metrics=topology_data["metrics"],
            meta=topology_data["meta"]
        )
        
    except Exception as e:
        logger.error(f"❌ Topology introspection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Topology introspection failed: {str(e)}")

@app.get("/a2a/agents")
async def list_active_agents():
    """List all active agents in the swarm"""
    try:
        agents = await graph_agent.discover_active_agents()
        return {
            "agents": agents,
            "count": len(agents),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")

@app.get("/a2a/streams")
async def list_active_streams():
    """List all active Redis streams"""
    try:
        # This would need implementation in graph_agent
        return {
            "streams": [],
            "count": 0,
            "timestamp": time.time(),
            "note": "Stream discovery implementation pending"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list streams: {str(e)}")

# ============================================================================
# SWS-110: Perms Agent Endpoints (A2A Access Control)
# ============================================================================

@app.post("/a2a/auth", response_model=AuthResponse)
async def authorize_a2a_access(auth_request: AuthRequest):
    """
    SWS-110: A2A-auth endpoint with <25ms latency target
    Role-based access control for agent stream operations
    """
    try:
        auth_result = await perms_agent.authorize_a2a_access(
            agent_id=auth_request.agent_id,
            target_stream=auth_request.target_stream,
            operation=auth_request.operation,
            context=auth_request.context
        )
        
        return AuthResponse(
            allowed=auth_result.allowed,
            agent_id=auth_result.agent_id,
            operation=auth_result.operation,
            target_stream=auth_result.target_stream,
            reason=auth_result.reason,
            latency_ms=auth_result.latency_ms,
            cached=auth_result.cached
        )
        
    except Exception as e:
        logger.error(f"❌ A2A authorization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Authorization failed: {str(e)}")

@app.post("/a2a/register")
async def register_agent(registration: AgentRegistrationRequest):
    """Register new agent with role-based permissions"""
    try:
        # Convert role string to enum
        try:
            role = AgentRole(registration.role.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {registration.role}")
            
        success = await perms_agent.register_agent(
            agent_id=registration.agent_id,
            role=role,
            created_by=registration.created_by
        )
        
        if success:
            return {"success": True, "message": f"Agent {registration.agent_id} registered with role {registration.role}"}
        else:
            raise HTTPException(status_code=500, detail="Registration failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Agent registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.delete("/a2a/revoke/{agent_id}")
async def revoke_agent_access(agent_id: str):
    """Revoke all access for an agent"""
    try:
        success = await perms_agent.revoke_agent_access(agent_id)
        
        if success:
            return {"success": True, "message": f"Access revoked for agent {agent_id}"}
        else:
            raise HTTPException(status_code=500, detail="Revocation failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Agent revocation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Revocation failed: {str(e)}")

@app.get("/a2a/permissions/{agent_id}")
async def get_agent_permissions(agent_id: str):
    """Get complete permission set for an agent"""
    try:
        permissions = await perms_agent.get_agent_permissions(agent_id)
        return permissions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get permissions: {str(e)}")

# ============================================================================
# SWS-120: Build Agent Endpoints (Agent Scaffolding)
# ============================================================================

@app.post("/agent/create", response_model=ScaffoldResponse)
async def scaffold_agent(scaffold_request: ScaffoldRequest, background_tasks: BackgroundTasks):
    """
    SWS-120: Agent scaffold CLI endpoint
    Create agent from intent with PR merge in <90s
    """
    try:
        # Run scaffolding in background for better performance
        scaffold_result = await build_agent.scaffold_agent(
            intent=scaffold_request.intent,
            developer_id=scaffold_request.developer_id
        )
        
        return ScaffoldResponse(
            success=scaffold_result.success,
            spec_id=scaffold_result.spec_id,
            agent_name=scaffold_result.agent_name,
            pr_url=scaffold_result.pr_url,
            branch_name=scaffold_result.branch_name,
            scaffold_time_seconds=scaffold_result.scaffold_time_seconds,
            files_created=scaffold_result.files_created,
            ci_gates_passed=scaffold_result.ci_gates_passed,
            error_message=scaffold_result.error_message
        )
        
    except Exception as e:
        logger.error(f"❌ Agent scaffolding failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scaffolding failed: {str(e)}")

@app.get("/agent/templates")
async def list_agent_templates():
    """List available agent templates"""
    try:
        templates = list(build_agent.template_engine.templates.keys())
        template_details = []
        
        for template_name in templates:
            template = build_agent.template_engine.templates[template_name]
            template_details.append({
                "name": template.name,
                "description": template.description,
                "capabilities": template.required_capabilities,
                "files": template.base_files
            })
            
        return {
            "templates": template_details,
            "count": len(templates)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")

@app.get("/agent/scaffold/status")
async def get_scaffold_metrics():
    """Get agent scaffolding metrics and status"""
    return {
        "active_scaffolds": 0,  # Would need implementation in build_agent
        "target_latency_seconds": build_agent.pr_merge_target,
        "supported_agent_types": list(build_agent.template_engine.templates.keys()),
        "timestamp": time.time()
    }

# ============================================================================
# SWS-130: Docs Agent Endpoints (Auto-Documentation)
# ============================================================================

@app.post("/docs/generate", response_model=DocumentationResponse)
async def generate_agent_documentation(doc_request: DocumentationRequest):
    """
    SWS-130: Auto-doc + diagram from agent manifest
    Target: ≥98% documentation quality pass rate
    """
    try:
        doc_result = await docs_agent.auto_document_agent(doc_request.agent_manifest)
        
        return DocumentationResponse(
            success=doc_result.success,
            agent_id=doc_result.agent_id,
            documentation=doc_result.documentation,
            diagram=doc_result.diagram,
            api_spec=doc_result.api_spec,
            quality_score=doc_result.quality_score,
            auto_enhanced=doc_result.auto_enhanced,
            generation_time_seconds=doc_result.generation_time_seconds,
            error_message=doc_result.error_message
        )
        
    except Exception as e:
        logger.error(f"❌ Documentation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Documentation generation failed: {str(e)}")

@app.post("/docs/ecosystem")
async def generate_ecosystem_documentation(ecosystem_request: EcosystemDocRequest):
    """Generate documentation for entire agent ecosystem"""
    try:
        ecosystem_docs = await docs_agent.generate_ecosystem_documentation(ecosystem_request.agents)
        return ecosystem_docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ecosystem documentation failed: {str(e)}")

@app.get("/docs/quality/standards")
async def get_documentation_standards():
    """Get documentation quality standards and rules"""
    try:
        return {
            "quality_target": docs_agent.quality_pass_rate_target,
            "quality_rules": [
                {
                    "name": rule["name"],
                    "description": rule["description"],
                    "weight": rule["weight"]
                }
                for rule in docs_agent.quality_checker.quality_rules
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get standards: {str(e)}")

# ============================================================================
# Platform Management Endpoints
# ============================================================================

@app.get("/platform/status")
async def get_platform_status():
    """Get overall platform status and metrics"""
    try:
        # Collect status from all agents
        topology_health = await graph_agent.redis_client.ping() if graph_agent.redis_client else False
        
        return {
            "platform": "SWS-Core",
            "version": "1.0.0",
            "status": "healthy",
            "uptime_seconds": time.time(),  # Simplified
            "components": {
                "graph_agent": {
                    "status": "healthy" if topology_health else "unhealthy",
                    "description": "Agent topology introspection"
                },
                "perms_agent": {
                    "status": "healthy",
                    "description": "A2A access control"
                },
                "build_agent": {
                    "status": "healthy", 
                    "description": "Agent scaffolding pipeline"
                },
                "docs_agent": {
                    "status": "healthy",
                    "description": "Auto-documentation generation"
                }
            },
            "capabilities": [
                "topology_introspection",
                "a2a_authorization", 
                "agent_scaffolding",
                "auto_documentation"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Platform status check failed: {str(e)}")

@app.get("/platform/metrics/summary")
async def get_platform_metrics():
    """Get platform-wide metrics summary"""
    return {
        "metrics": {
            "active_agents": 0,  # Would integrate with graph_agent
            "total_streams": 0,   # Would integrate with graph_agent
            "auth_requests_24h": 0,  # Would integrate with perms_agent
            "scaffolds_today": 0,    # Would integrate with build_agent
            "docs_generated_today": 0  # Would integrate with docs_agent
        },
        "performance": {
            "avg_topology_latency_ms": 0,
            "avg_auth_latency_ms": 0,
            "avg_scaffold_time_seconds": 0,
            "avg_doc_quality_score": 0
        },
        "timestamp": time.time()
    }

# CLI simulation endpoint for development
@app.post("/cli/agent/create")
async def cli_agent_create(intent: str, developer_id: str = "cli_user"):
    """
    CLI simulation endpoint
    Equivalent to: `agent create --intent="X"`
    """
    scaffold_request = ScaffoldRequest(intent=intent, developer_id=developer_id)
    return await scaffold_agent(scaffold_request, BackgroundTasks())

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for better error responses"""
    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": time.time(),
            "path": str(request.url)
        }
    )

# Development server runner
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "sws.api:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        access_log=True
    ) 