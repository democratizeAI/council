# sws/__init__.py - SWS-Core Package
"""
🌐 SWS-Core: Swarm-to-Swarm Services Platform
==============================================

Multi-agent platform ecosystem for external developers.
Transforms enterprise swarm into developer-friendly platform.

Components:
- SWS-100: Graph Agent (topology introspection)
- SWS-110: Perms Agent (A2A access control) 
- SWS-120: Build Agent (agent scaffolding)
- SWS-130: Docs Agent (auto-documentation)

Part of v0.1-freeze → Developer Ecosystem transformation.
"""

__version__ = "1.0.0"
__author__ = "SWS-Core Team"
__description__ = "Swarm-to-Swarm Services Platform"

# Core agents
from .graph_agent import GraphAgent, graph_agent
from .perms_agent import PermsAgent, perms_agent, AgentRole
from .build_agent import BuildAgent, build_agent
from .docs_agent import DocsAgent, docs_agent

# API integration
from .api import app as sws_api

# Export main components
__all__ = [
    # Agents
    "GraphAgent",
    "graph_agent", 
    "PermsAgent",
    "perms_agent",
    "AgentRole",
    "BuildAgent", 
    "build_agent",
    "DocsAgent",
    "docs_agent",
    
    # API
    "sws_api",
    
    # Version info
    "__version__",
    "__author__",
    "__description__"
]

# Platform capabilities
PLATFORM_CAPABILITIES = [
    "topology_introspection",    # SWS-100
    "a2a_authorization",         # SWS-110
    "agent_scaffolding",         # SWS-120
    "auto_documentation"         # SWS-130
]

# Performance targets
PERFORMANCE_TARGETS = {
    "topology_latency_ms": 200,      # SWS-100 target
    "auth_latency_ms": 25,           # SWS-110 target  
    "scaffold_time_seconds": 90,     # SWS-120 target
    "doc_quality_score": 0.98        # SWS-130 target
}

# Package metadata
PACKAGE_INFO = {
    "name": "sws-core",
    "version": __version__,
    "description": __description__,
    "capabilities": PLATFORM_CAPABILITIES,
    "performance_targets": PERFORMANCE_TARGETS,
    "agents": {
        "graph_agent": "Agent topology introspection and visualization",
        "perms_agent": "Role-based access control for A2A communication", 
        "build_agent": "Automated agent scaffolding and deployment",
        "docs_agent": "Intelligent documentation generation"
    }
} 