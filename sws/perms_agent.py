# sws/perms_agent.py - SWS-110: Role-based access for agents (ACL per stream)
"""
🔐 Perms Agent - Swarm-to-Swarm Services Access Control
======================================================

Enterprise-grade authorization for agent-to-agent communication.
- Role-based access control (RBAC) for Redis streams
- Sub-25ms authorization latency for swarm performance
- Integration with existing PatchCtl v2 governance framework
- Audit trail for all A2A permission decisions

Part of SWS-Core platform transformation (v0.1-freeze → Developer Ecosystem)
"""

import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis
from prometheus_client import Histogram, Counter, Gauge
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics for Perms Agent
AUTH_REQUEST_LATENCY = Histogram(
    "sws_auth_request_latency_seconds",
    "A2A authorization request latency",
    buckets=(0.005, 0.01, 0.015, 0.025, 0.05, 0.1)
)

AUTH_REQUESTS_TOTAL = Counter(
    "sws_auth_requests_total",
    "Total A2A authorization requests",
    ["agent_id", "operation", "result"]
)

ACTIVE_PERMISSIONS_GAUGE = Gauge(
    "sws_active_permissions_total",
    "Number of active agent permissions"
)

class Permission(Enum):
    """Stream operation permissions"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    CREATE = "create"
    DELETE = "delete"

class AgentRole(Enum):
    """Predefined agent roles in the swarm"""
    INTERNAL_CORE = "internal_core"      # Opus, Gemini, Sonnet, Router
    INTERNAL_SERVICE = "internal_service" # Builder-Tiny, Guards, etc.
    EXTERNAL_DEVELOPER = "external_developer" # External agents (read-only by default)
    EXTERNAL_PREMIUM = "external_premium"     # Premium external agents (write access)
    SYSTEM_ADMIN = "system_admin"            # Full administrative access

@dataclass
class AuthRequest:
    """Authorization request from agent"""
    agent_id: str
    target_stream: str
    operation: Permission
    context: Dict[str, Any]
    timestamp: float
    request_id: str

@dataclass
class AuthResult:
    """Authorization decision result"""
    allowed: bool
    agent_id: str
    operation: str
    target_stream: str
    reason: str
    latency_ms: float
    cached: bool = False
    ttl_seconds: int = 300

@dataclass
class AgentPermissionSet:
    """Complete permission set for an agent"""
    agent_id: str
    role: AgentRole
    stream_permissions: Dict[str, List[Permission]]
    global_permissions: List[Permission]
    expires_at: Optional[float] = None
    created_by: str = "system"

class ACLEngine:
    """
    Access Control List engine for agent permissions
    
    Implements role-based access control with stream-level granularity.
    Optimized for sub-25ms authorization decisions.
    """
    
    def __init__(self):
        self.role_permissions = self._initialize_role_permissions()
        self.stream_patterns = self._initialize_stream_patterns()
        
    def _initialize_role_permissions(self) -> Dict[AgentRole, Dict[str, List[Permission]]]:
        """Initialize default role-based permissions"""
        return {
            AgentRole.INTERNAL_CORE: {
                "*": [Permission.READ, Permission.WRITE, Permission.CREATE],
                "system:*": [Permission.ADMIN],
                "audit:*": [Permission.READ, Permission.WRITE]
            },
            AgentRole.INTERNAL_SERVICE: {
                "plans": [Permission.READ],
                "implementations": [Permission.READ, Permission.WRITE],
                "audits": [Permission.READ],
                "system:health": [Permission.READ],
                "metrics:*": [Permission.READ]
            },
            AgentRole.EXTERNAL_DEVELOPER: {
                "public:*": [Permission.READ],
                "dev:*": [Permission.READ, Permission.WRITE],
                "sandbox:*": [Permission.READ, Permission.WRITE, Permission.CREATE]
            },
            AgentRole.EXTERNAL_PREMIUM: {
                "public:*": [Permission.READ],
                "dev:*": [Permission.READ, Permission.WRITE, Permission.CREATE],
                "prod:*": [Permission.READ],
                "analytics:*": [Permission.READ]
            },
            AgentRole.SYSTEM_ADMIN: {
                "*": [Permission.READ, Permission.WRITE, Permission.CREATE, Permission.DELETE, Permission.ADMIN]
            }
        }
        
    def _initialize_stream_patterns(self) -> Dict[str, AgentRole]:
        """Map stream patterns to minimum required roles"""
        return {
            "system:*": AgentRole.INTERNAL_CORE,
            "audit:*": AgentRole.INTERNAL_SERVICE,
            "plans": AgentRole.INTERNAL_SERVICE,
            "implementations": AgentRole.INTERNAL_SERVICE,
            "public:*": AgentRole.EXTERNAL_DEVELOPER,
            "dev:*": AgentRole.EXTERNAL_DEVELOPER,
            "prod:*": AgentRole.EXTERNAL_PREMIUM
        }
        
    def check_stream_permission(self, agent_role: AgentRole, stream_name: str, 
                               operation: Permission) -> Tuple[bool, str]:
        """Check if agent role has permission for stream operation"""
        
        role_perms = self.role_permissions.get(agent_role, {})
        
        # Check exact stream match first
        if stream_name in role_perms:
            if operation in role_perms[stream_name]:
                return True, f"Direct permission for {stream_name}"
                
        # Check wildcard patterns
        for pattern, permissions in role_perms.items():
            if "*" in pattern:
                pattern_prefix = pattern.replace("*", "")
                if stream_name.startswith(pattern_prefix):
                    if operation in permissions:
                        return True, f"Wildcard permission via {pattern}"
                        
        # Check global wildcard
        if "*" in role_perms and operation in role_perms["*"]:
            return True, "Global wildcard permission"
            
        return False, f"No permission for {operation.value} on {stream_name}"

class PermsAgent:
    """
    SWS-110: Permissions Agent for A2A access control
    
    Provides role-based access control for agent-to-agent communication
    via Redis streams with enterprise-grade security and audit trails.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client = None
        self.acl_engine = ACLEngine()
        
        # Performance targets
        self.auth_latency_target = 0.025  # 25ms SLA
        self.cache_ttl = 300  # 5 minutes
        
        # Caching for performance
        self.auth_cache = {}
        self.agent_roles_cache = {}
        
        # Default agent roles (from existing enterprise swarm)
        self.default_agent_roles = {
            "opus_strategist": AgentRole.INTERNAL_CORE,
            "gemini_auditor": AgentRole.INTERNAL_CORE,
            "sonnet_builder": AgentRole.INTERNAL_CORE,
            "router_cascade": AgentRole.INTERNAL_CORE,
            "intent_distillation": AgentRole.INTERNAL_SERVICE,
            "builder_tiny": AgentRole.INTERNAL_SERVICE,
            "accuracy_guard": AgentRole.INTERNAL_SERVICE,
            "cost_guard": AgentRole.INTERNAL_SERVICE
        }
        
        logger.info("🔐 Perms Agent initialized (SWS-110)")
        
    async def initialize(self):
        """Initialize Redis connection and load agent roles"""
        self.redis_client = redis.from_url(self.redis_url)
        
        try:
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
            # Load existing agent roles from Redis
            await self._load_agent_roles()
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
            
    async def authorize_a2a_access(self, agent_id: str, target_stream: str, 
                                   operation: str, context: Dict = None) -> AuthResult:
        """
        Main authorization endpoint for A2A communication
        Target: <25ms latency for swarm performance
        """
        start_time = time.perf_counter()
        request_id = hashlib.md5(f"{agent_id}:{target_stream}:{operation}:{time.time()}".encode()).hexdigest()[:8]
        
        try:
            # Convert operation string to Permission enum
            try:
                perm_operation = Permission(operation.lower())
            except ValueError:
                return AuthResult(
                    allowed=False,
                    agent_id=agent_id,
                    operation=operation,
                    target_stream=target_stream,
                    reason=f"Invalid operation: {operation}",
                    latency_ms=(time.perf_counter() - start_time) * 1000
                )
            
            # Check cache first for performance
            cache_key = f"{agent_id}:{target_stream}:{operation}"
            if cache_key in self.auth_cache:
                cached_result, cache_time = self.auth_cache[cache_key]
                if time.time() - cache_time < self.cache_ttl:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    cached_result.latency_ms = latency_ms
                    cached_result.cached = True
                    
                    AUTH_REQUESTS_TOTAL.labels(
                        agent_id=agent_id, 
                        operation=operation, 
                        result="cached_allowed" if cached_result.allowed else "cached_denied"
                    ).inc()
                    
                    return cached_result
            
            # Get agent role
            agent_role = await self._get_agent_role(agent_id)
            
            # Check permission
            allowed, reason = self.acl_engine.check_stream_permission(
                agent_role, target_stream, perm_operation
            )
            
            # Create result
            result = AuthResult(
                allowed=allowed,
                agent_id=agent_id,
                operation=operation,
                target_stream=target_stream,
                reason=reason,
                latency_ms=(time.perf_counter() - start_time) * 1000
            )
            
            # Cache successful result
            if allowed:
                self.auth_cache[cache_key] = (result, time.time())
            
            # Record metrics
            AUTH_REQUEST_LATENCY.observe(result.latency_ms / 1000)
            AUTH_REQUESTS_TOTAL.labels(
                agent_id=agent_id,
                operation=operation,
                result="allowed" if allowed else "denied"
            ).inc()
            
            # Log authorization decision
            log_level = logging.DEBUG if allowed else logging.WARNING
            logger.log(log_level, 
                f"🔐 Auth {request_id}: {agent_id} → {target_stream} ({operation}) = {'✅ ALLOWED' if allowed else '❌ DENIED'} [{result.latency_ms:.1f}ms] - {reason}")
            
            # Alert on SLA violation
            if result.latency_ms > self.auth_latency_target * 1000:
                logger.warning(f"⚠️ Auth SLA violation: {result.latency_ms:.1f}ms > {self.auth_latency_target*1000}ms")
            
            # Audit log for security
            await self._log_auth_decision(request_id, result, context or {})
            
            return result
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"❌ Authorization failed for {agent_id}: {e}")
            
            return AuthResult(
                allowed=False,
                agent_id=agent_id,
                operation=operation,
                target_stream=target_stream,
                reason=f"Authorization error: {str(e)}",
                latency_ms=latency_ms
            )
            
    async def register_agent(self, agent_id: str, role: AgentRole, 
                           created_by: str = "system") -> bool:
        """Register new agent with specific role"""
        try:
            permission_set = AgentPermissionSet(
                agent_id=agent_id,
                role=role,
                stream_permissions=self.acl_engine.role_permissions.get(role, {}),
                global_permissions=[],
                created_by=created_by
            )
            
            # Store in Redis
            await self.redis_client.hset(
                "sws:agent_roles",
                agent_id,
                json.dumps(asdict(permission_set))
            )
            
            # Update cache
            self.agent_roles_cache[agent_id] = role
            
            logger.info(f"🔐 Registered agent {agent_id} with role {role.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register agent {agent_id}: {e}")
            return False
            
    async def revoke_agent_access(self, agent_id: str) -> bool:
        """Revoke all access for an agent"""
        try:
            # Remove from Redis
            await self.redis_client.hdel("sws:agent_roles", agent_id)
            
            # Clear caches
            if agent_id in self.agent_roles_cache:
                del self.agent_roles_cache[agent_id]
                
            # Clear auth cache entries for this agent
            cache_keys_to_remove = [k for k in self.auth_cache.keys() if k.startswith(f"{agent_id}:")]
            for key in cache_keys_to_remove:
                del self.auth_cache[key]
                
            logger.info(f"🔐 Revoked access for agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to revoke access for {agent_id}: {e}")
            return False
            
    async def get_agent_permissions(self, agent_id: str) -> Dict[str, Any]:
        """Get complete permission set for an agent"""
        try:
            role = await self._get_agent_role(agent_id)
            role_permissions = self.acl_engine.role_permissions.get(role, {})
            
            return {
                "agent_id": agent_id,
                "role": role.value,
                "stream_permissions": role_permissions,
                "effective_permissions": await self._calculate_effective_permissions(role)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get permissions for {agent_id}: {e}")
            return {}
            
    async def _get_agent_role(self, agent_id: str) -> AgentRole:
        """Get role for specific agent (with caching)"""
        
        # Check cache first
        if agent_id in self.agent_roles_cache:
            return self.agent_roles_cache[agent_id]
            
        # Check default roles for internal agents
        if agent_id in self.default_agent_roles:
            role = self.default_agent_roles[agent_id]
            self.agent_roles_cache[agent_id] = role
            return role
            
        # Query Redis
        try:
            role_data = await self.redis_client.hget("sws:agent_roles", agent_id)
            if role_data:
                permission_set = json.loads(role_data)
                role = AgentRole(permission_set['role'])
                self.agent_roles_cache[agent_id] = role
                return role
        except Exception as e:
            logger.debug(f"Failed to get role for {agent_id}: {e}")
            
        # Default to external developer for unknown agents
        role = AgentRole.EXTERNAL_DEVELOPER
        self.agent_roles_cache[agent_id] = role
        return role
        
    async def _load_agent_roles(self):
        """Load all agent roles from Redis into cache"""
        try:
            roles_data = await self.redis_client.hgetall("sws:agent_roles")
            for agent_id, role_data in roles_data.items():
                try:
                    permission_set = json.loads(role_data)
                    role = AgentRole(permission_set['role'])
                    self.agent_roles_cache[agent_id.decode()] = role
                except Exception as e:
                    logger.warning(f"Failed to load role for {agent_id}: {e}")
                    
            # Add default roles
            for agent_id, role in self.default_agent_roles.items():
                if agent_id not in self.agent_roles_cache:
                    self.agent_roles_cache[agent_id] = role
                    
            ACTIVE_PERMISSIONS_GAUGE.set(len(self.agent_roles_cache))
            logger.info(f"🔐 Loaded {len(self.agent_roles_cache)} agent roles")
            
        except Exception as e:
            logger.error(f"❌ Failed to load agent roles: {e}")
            
    async def _calculate_effective_permissions(self, role: AgentRole) -> List[str]:
        """Calculate effective permissions for a role"""
        role_perms = self.acl_engine.role_permissions.get(role, {})
        effective = []
        
        for stream_pattern, permissions in role_perms.items():
            for perm in permissions:
                effective.append(f"{stream_pattern}:{perm.value}")
                
        return effective
        
    async def _log_auth_decision(self, request_id: str, result: AuthResult, context: Dict):
        """Log authorization decision for audit trail"""
        try:
            audit_entry = {
                "request_id": request_id,
                "timestamp": time.time(),
                "agent_id": result.agent_id,
                "target_stream": result.target_stream,
                "operation": result.operation,
                "allowed": result.allowed,
                "reason": result.reason,
                "latency_ms": result.latency_ms,
                "context": context
            }
            
            # Store in Redis audit stream
            await self.redis_client.xadd(
                "audit:auth_decisions",
                audit_entry
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to log auth decision: {e}")

# Singleton instance for FastAPI integration
perms_agent = PermsAgent() 