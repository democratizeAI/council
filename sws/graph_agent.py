# sws/graph_agent.py - SWS-100: Agent→Agent topology introspection endpoint
"""
🧬 Graph Agent - Swarm-to-Swarm Services Core
==============================================

Provides real-time topology introspection for multi-agent swarms.
- A2A communication pattern discovery via Redis streams
- Performance metrics aggregation across agent mesh
- DAG visualization data for external developer tools
- Sub-200ms response time for /a2a/map endpoint

Part of SWS-Core platform transformation (v0.1-freeze → Developer Ecosystem)
"""

import time
import json
import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import redis.asyncio as redis
from prometheus_client import Histogram, Counter, Gauge
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics for Graph Agent
TOPOLOGY_REQUEST_LATENCY = Histogram(
    "sws_topology_request_latency_seconds",
    "Topology introspection request latency",
    buckets=(0.05, 0.1, 0.15, 0.2, 0.5, 1.0)
)

ACTIVE_AGENTS_GAUGE = Gauge(
    "sws_active_agents_total",
    "Number of active agents in swarm"
)

STREAM_CONNECTIONS_GAUGE = Gauge(
    "sws_stream_connections_total", 
    "Number of active Redis stream connections"
)

@dataclass
class AgentNode:
    """Represents an agent in the topology graph"""
    id: str
    type: str  # "internal" or "external"
    status: str  # "active", "idle", "error"
    last_seen: float
    streams_consumed: List[str]
    streams_produced: List[str]
    performance_metrics: Dict[str, float]
    capabilities: List[str]

@dataclass
class StreamEdge:
    """Represents communication flow between agents"""
    source_agent: str
    target_agent: str
    stream_name: str
    message_rate: float  # messages/second
    latency_p95: float   # milliseconds
    error_rate: float    # percentage
    last_activity: float

@dataclass
class TopologyGraph:
    """Complete swarm topology representation"""
    nodes: List[AgentNode]
    edges: List[StreamEdge]
    metrics: Dict[str, Any]
    generation_time: float
    cache_ttl: int = 30  # seconds

class GraphAgent:
    """
    SWS-100: Graph Agent for A2A topology introspection
    
    Discovers and maps agent communication patterns across Redis streams.
    Provides real-time topology data for external developer tools.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client = None
        self.topology_cache = {}
        self.cache_ttl = 30  # seconds
        self.discovery_timeout = 10  # seconds
        
        # Performance tracking
        self.response_time_target = 0.2  # 200ms SLA
        
        # Known internal agents from existing swarm
        self.internal_agents = {
            "opus_strategist",
            "gemini_auditor", 
            "sonnet_builder",
            "router_cascade",
            "intent_distillation",
            "builder_tiny",
            "accuracy_guard",
            "cost_guard"
        }
        
        logger.info("🧬 Graph Agent initialized (SWS-100)")
        
    async def initialize(self):
        """Initialize Redis connection and background tasks"""
        self.redis_client = redis.from_url(self.redis_url)
        
        # Test connection
        try:
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
            
    async def get_topology_map(self) -> Dict[str, Any]:
        """
        Main endpoint: /a2a/map
        Returns complete topology with DAG + metrics in <200ms
        """
        start_time = time.perf_counter()
        
        try:
            # Check cache first
            cache_key = "topology_map"
            if cache_key in self.topology_cache:
                cached_data, cache_time = self.topology_cache[cache_key]
                if time.time() - cache_time < self.cache_ttl:
                    logger.debug("📋 Returning cached topology")
                    return cached_data
            
            # Discover active agents
            active_agents = await self.discover_active_agents()
            ACTIVE_AGENTS_GAUGE.set(len(active_agents))
            
            # Build topology graph
            topology = await self.build_topology_graph(active_agents)
            
            # Generate response
            response = {
                "topology": {
                    "nodes": [asdict(node) for node in topology.nodes],
                    "edges": [asdict(edge) for edge in topology.edges],
                    "agent_count": len(topology.nodes),
                    "connection_count": len(topology.edges)
                },
                "metrics": topology.metrics,
                "meta": {
                    "generation_time_ms": (time.perf_counter() - start_time) * 1000,
                    "cache_ttl": self.cache_ttl,
                    "discovery_timeout": self.discovery_timeout,
                    "sws_version": "1.0.0"
                }
            }
            
            # Cache result
            self.topology_cache[cache_key] = (response, time.time())
            
            # Record metrics
            response_time = time.perf_counter() - start_time
            TOPOLOGY_REQUEST_LATENCY.observe(response_time)
            
            if response_time > self.response_time_target:
                logger.warning(f"⚠️ Topology request exceeded SLA: {response_time*1000:.1f}ms > {self.response_time_target*1000}ms")
            
            logger.info(f"🧬 Topology map generated: {len(topology.nodes)} agents, {len(topology.edges)} connections, {response_time*1000:.1f}ms")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Topology map generation failed: {e}")
            raise
            
    async def discover_active_agents(self) -> List[Dict[str, Any]]:
        """Discover active agents via Redis streams and heartbeats"""
        active_agents = []
        
        try:
            # Method 1: Check for agent heartbeats in Redis
            heartbeat_keys = await self.redis_client.keys("agent:*:heartbeat")
            
            for key in heartbeat_keys:
                agent_id = key.decode().split(':')[1]
                heartbeat_data = await self.redis_client.get(key)
                
                if heartbeat_data:
                    heartbeat = json.loads(heartbeat_data)
                    last_seen = heartbeat.get('timestamp', 0)
                    
                    # Consider agent active if seen in last 60 seconds
                    if time.time() - last_seen < 60:
                        agent_info = {
                            "id": agent_id,
                            "type": "internal" if agent_id in self.internal_agents else "external",
                            "status": "active",
                            "last_seen": last_seen,
                            "capabilities": heartbeat.get('capabilities', []),
                            "streams": heartbeat.get('streams', {})
                        }
                        active_agents.append(agent_info)
            
            # Method 2: Check Redis streams for recent activity
            stream_agents = await self.discover_agents_from_streams()
            
            # Merge discoveries (avoid duplicates)
            agent_ids = {agent['id'] for agent in active_agents}
            for stream_agent in stream_agents:
                if stream_agent['id'] not in agent_ids:
                    active_agents.append(stream_agent)
                    
            logger.debug(f"🔍 Discovered {len(active_agents)} active agents")
            return active_agents
            
        except Exception as e:
            logger.error(f"❌ Agent discovery failed: {e}")
            return []
            
    async def discover_agents_from_streams(self) -> List[Dict[str, Any]]:
        """Discover agents by scanning Redis streams for recent activity"""
        stream_agents = []
        
        try:
            # Get all Redis streams
            all_keys = await self.redis_client.keys("*")
            stream_keys = []
            
            for key in all_keys:
                key_str = key.decode()
                # Look for stream-like patterns
                if any(pattern in key_str for pattern in ['plans', 'implementations', 'audits', 'tickets', 'events']):
                    try:
                        stream_info = await self.redis_client.xinfo_stream(key_str)
                        if stream_info.get('length', 0) > 0:
                            stream_keys.append(key_str)
                    except:
                        continue  # Not a stream
                        
            # Analyze recent messages in streams
            for stream_key in stream_keys:
                try:
                    # Get last 10 messages from stream
                    messages = await self.redis_client.xrevrange(
                        stream_key, count=10
                    )
                    
                    for msg_id, fields in messages:
                        # Extract agent info from message fields
                        agent_id = fields.get(b'agent_id', b'unknown').decode()
                        if agent_id != 'unknown':
                            agent_info = {
                                "id": agent_id,
                                "type": "internal" if agent_id in self.internal_agents else "external",
                                "status": "active",
                                "last_seen": time.time(),  # Approximate
                                "capabilities": [],
                                "streams": {"produced": [stream_key]}
                            }
                            stream_agents.append(agent_info)
                            
                except Exception as e:
                    logger.debug(f"Failed to read stream {stream_key}: {e}")
                    continue
                    
            return stream_agents
            
        except Exception as e:
            logger.error(f"❌ Stream discovery failed: {e}")
            return []
            
    async def build_topology_graph(self, active_agents: List[Dict]) -> TopologyGraph:
        """Build complete topology graph with nodes and edges"""
        
        # Build agent nodes
        nodes = []
        for agent_data in active_agents:
            # Get performance metrics for agent
            perf_metrics = await self.get_agent_performance_metrics(agent_data['id'])
            
            node = AgentNode(
                id=agent_data['id'],
                type=agent_data['type'],
                status=agent_data['status'],
                last_seen=agent_data['last_seen'],
                streams_consumed=agent_data.get('streams', {}).get('consumed', []),
                streams_produced=agent_data.get('streams', {}).get('produced', []),
                performance_metrics=perf_metrics,
                capabilities=agent_data.get('capabilities', [])
            )
            nodes.append(node)
            
        # Build communication edges
        edges = await self.discover_communication_edges(nodes)
        
        # Calculate swarm-level metrics
        swarm_metrics = await self.calculate_swarm_metrics(nodes, edges)
        
        STREAM_CONNECTIONS_GAUGE.set(len(edges))
        
        return TopologyGraph(
            nodes=nodes,
            edges=edges,
            metrics=swarm_metrics,
            generation_time=time.time()
        )
        
    async def get_agent_performance_metrics(self, agent_id: str) -> Dict[str, float]:
        """Get performance metrics for specific agent"""
        try:
            # Try to get metrics from Redis
            metrics_key = f"agent:{agent_id}:metrics"
            metrics_data = await self.redis_client.get(metrics_key)
            
            if metrics_data:
                return json.loads(metrics_data)
            else:
                # Default metrics
                return {
                    "latency_p95": 0.0,
                    "request_rate": 0.0,
                    "error_rate": 0.0,
                    "cpu_usage": 0.0,
                    "memory_usage": 0.0
                }
                
        except Exception as e:
            logger.debug(f"Failed to get metrics for {agent_id}: {e}")
            return {}
            
    async def discover_communication_edges(self, nodes: List[AgentNode]) -> List[StreamEdge]:
        """Discover communication patterns between agents"""
        edges = []
        
        # Build mapping of streams to producers/consumers
        stream_producers = defaultdict(list)
        stream_consumers = defaultdict(list)
        
        for node in nodes:
            for stream in node.streams_produced:
                stream_producers[stream].append(node.id)
            for stream in node.streams_consumed:
                stream_consumers[stream].append(node.id)
                
        # Create edges for each stream
        for stream_name in set(list(stream_producers.keys()) + list(stream_consumers.keys())):
            producers = stream_producers.get(stream_name, [])
            consumers = stream_consumers.get(stream_name, [])
            
            # Create edges from each producer to each consumer
            for producer in producers:
                for consumer in consumers:
                    if producer != consumer:  # No self-loops
                        # Get stream performance metrics
                        stream_metrics = await self.get_stream_metrics(stream_name)
                        
                        edge = StreamEdge(
                            source_agent=producer,
                            target_agent=consumer,
                            stream_name=stream_name,
                            message_rate=stream_metrics.get('message_rate', 0.0),
                            latency_p95=stream_metrics.get('latency_p95', 0.0),
                            error_rate=stream_metrics.get('error_rate', 0.0),
                            last_activity=stream_metrics.get('last_activity', time.time())
                        )
                        edges.append(edge)
                        
        return edges
        
    async def get_stream_metrics(self, stream_name: str) -> Dict[str, float]:
        """Get performance metrics for Redis stream"""
        try:
            # Get stream info
            stream_info = await self.redis_client.xinfo_stream(stream_name)
            
            # Calculate message rate (approximate)
            message_count = stream_info.get('length', 0)
            first_entry = stream_info.get('first-entry')
            last_entry = stream_info.get('last-entry')
            
            message_rate = 0.0
            if first_entry and last_entry and message_count > 1:
                # Parse timestamps from Redis stream IDs
                first_ts = int(first_entry[0].decode().split('-')[0]) / 1000
                last_ts = int(last_entry[0].decode().split('-')[0]) / 1000
                time_span = last_ts - first_ts
                
                if time_span > 0:
                    message_rate = message_count / time_span
                    
            return {
                'message_rate': message_rate,
                'latency_p95': 50.0,  # Placeholder - would need instrumentation
                'error_rate': 0.0,    # Placeholder - would need error tracking
                'last_activity': time.time(),
                'message_count': message_count
            }
            
        except Exception as e:
            logger.debug(f"Failed to get stream metrics for {stream_name}: {e}")
            return {}
            
    async def calculate_swarm_metrics(self, nodes: List[AgentNode], edges: List[StreamEdge]) -> Dict[str, Any]:
        """Calculate swarm-level performance metrics"""
        
        if not nodes:
            return {}
            
        # Agent type breakdown
        internal_agents = sum(1 for node in nodes if node.type == "internal")
        external_agents = sum(1 for node in nodes if node.type == "external")
        
        # Performance aggregations
        total_latency = sum(node.performance_metrics.get('latency_p95', 0) for node in nodes)
        avg_latency = total_latency / len(nodes) if nodes else 0
        
        total_request_rate = sum(node.performance_metrics.get('request_rate', 0) for node in nodes)
        
        total_error_rate = sum(node.performance_metrics.get('error_rate', 0) for node in nodes)
        avg_error_rate = total_error_rate / len(nodes) if nodes else 0
        
        # Stream metrics
        total_message_rate = sum(edge.message_rate for edge in edges)
        active_streams = len(set(edge.stream_name for edge in edges))
        
        return {
            "swarm_health": "healthy" if avg_error_rate < 0.05 else "degraded",
            "agent_breakdown": {
                "internal": internal_agents,
                "external": external_agents,
                "total": len(nodes)
            },
            "performance": {
                "avg_latency_ms": avg_latency,
                "total_request_rate": total_request_rate,
                "avg_error_rate": avg_error_rate
            },
            "communication": {
                "active_streams": active_streams,
                "total_message_rate": total_message_rate,
                "connection_count": len(edges)
            },
            "timestamp": time.time()
        }

# Singleton instance for FastAPI integration
graph_agent = GraphAgent() 