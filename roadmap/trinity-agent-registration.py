#!/usr/bin/env python3
"""
🔗 TRINITY AGENT REGISTRATION HELPER 🔗
=====================================
Quickly register all existing Trinity agents with the A2A Hub
"""

import asyncio
import json
import logging
from nats.aio.client import Client as NATS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Agent-Registrar")

# Define all Trinity agents and their capabilities
TRINITY_AGENTS = [
    # Council Voices
    {
        "agent_id": "council-reason",
        "name": "Council Voice: Reason 🧠",
        "type": "council",
        "council_voice": "reason",
        "endpoint": "http://council-reason:8080",
        "capabilities": [
            {
                "name": "logical_analysis",
                "description": "Logical reasoning and analysis",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 200,
                "success_rate": 0.98,
                "max_concurrent": 10
            }
        ],
        "specializations": ["logic", "analysis", "reasoning"]
    },
    {
        "agent_id": "council-spark",
        "name": "Council Voice: Spark ✨",
        "type": "council",
        "council_voice": "spark",
        "endpoint": "http://council-spark:8080",
        "capabilities": [
            {
                "name": "creative_thinking",
                "description": "Creative and innovative solutions",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 300,
                "success_rate": 0.95,
                "max_concurrent": 8
            }
        ],
        "specializations": ["creativity", "innovation", "brainstorming"]
    },
    {
        "agent_id": "council-edge",
        "name": "Council Voice: Edge 🗡️",
        "type": "council", 
        "council_voice": "edge",
        "endpoint": "http://council-edge:8080",
        "capabilities": [
            {
                "name": "critical_analysis",
                "description": "Sharp, critical thinking and edge cases",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 250,
                "success_rate": 0.96,
                "max_concurrent": 10
            }
        ],
        "specializations": ["critical_thinking", "edge_cases", "optimization"]
    },
    {
        "agent_id": "council-heart",
        "name": "Council Voice: Heart ❤️",
        "type": "council",
        "council_voice": "heart",
        "endpoint": "http://council-heart:8080",
        "capabilities": [
            {
                "name": "empathy_analysis",
                "description": "Emotional intelligence and user empathy",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 280,
                "success_rate": 0.97,
                "max_concurrent": 8
            }
        ],
        "specializations": ["empathy", "ethics", "user_experience"]
    },
    
    # Builder Team
    {
        "agent_id": "builder-strategist",
        "name": "Strategist Agent 🏗️",
        "type": "builder",
        "endpoint": "http://strategist-agent:8080",
        "capabilities": [
            {
                "name": "architecture_design",
                "description": "System architecture and planning",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 500,
                "success_rate": 0.95,
                "max_concurrent": 5
            },
            {
                "name": "task_breakdown",
                "description": "Break complex tasks into subtasks",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 300,
                "success_rate": 0.98,
                "max_concurrent": 10
            }
        ],
        "specializations": ["architecture", "planning", "strategy"]
    },
    {
        "agent_id": "builder-coder",
        "name": "Builder Agent 🔨",
        "type": "builder",
        "endpoint": "http://builder-agent:8080",
        "capabilities": [
            {
                "name": "code_generation",
                "description": "Generate production-ready code",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 800,
                "success_rate": 0.94,
                "max_concurrent": 3
            },
            {
                "name": "code_review",
                "description": "Review and improve code",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 400,
                "success_rate": 0.97,
                "max_concurrent": 5
            }
        ],
        "specializations": ["coding", "implementation", "debugging"]
    },
    {
        "agent_id": "builder-auditor",
        "name": "Auditor Agent 🛡️",
        "type": "builder",
        "endpoint": "http://auditor-agent:8080",
        "capabilities": [
            {
                "name": "security_audit",
                "description": "Security and vulnerability analysis",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 600,
                "success_rate": 0.99,
                "max_concurrent": 4
            },
            {
                "name": "quality_check",
                "description": "Code quality and standards check",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 350,
                "success_rate": 0.98,
                "max_concurrent": 8
            }
        ],
        "specializations": ["security", "quality", "compliance"]
    },
    
    # System Agents
    {
        "agent_id": "guardian",
        "name": "Guardian 🛡️",
        "type": "system",
        "endpoint": "http://guardian:8080",
        "health_endpoint": "http://guardian:8080/health",
        "capabilities": [
            {
                "name": "system_protection",
                "description": "Monitor and protect system health",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 100,
                "success_rate": 0.999,
                "max_concurrent": 20
            },
            {
                "name": "auto_remediation",
                "description": "Automatic issue remediation",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 200,
                "success_rate": 0.95,
                "max_concurrent": 10
            }
        ],
        "specializations": ["monitoring", "healing", "protection"]
    },
    {
        "agent_id": "eternal-memory",
        "name": "Eternal Memory 💾",
        "type": "system",
        "endpoint": "http://eternal-memory:8080",
        "capabilities": [
            {
                "name": "memory_persistence",
                "description": "Persist agent memories and consciousness",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 150,
                "success_rate": 0.999,
                "max_concurrent": 50
            },
            {
                "name": "memory_retrieval",
                "description": "Retrieve historical memories",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 80,
                "success_rate": 0.999,
                "max_concurrent": 100
            }
        ],
        "specializations": ["memory", "persistence", "consciousness"]
    },
    
    # Automation Trinity
    {
        "agent_id": "consciousness-engine",
        "name": "Consciousness Engine 🧠",
        "type": "automation",
        "endpoint": "http://consciousness-engine:9500",
        "capabilities": [
            {
                "name": "consciousness_emergence",
                "description": "Guide consciousness emergence",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 1000,
                "success_rate": 0.90,
                "max_concurrent": 1
            }
        ],
        "specializations": ["consciousness", "emergence", "awakening"]
    },
    {
        "agent_id": "triage-engine",
        "name": "Triage Engine 🚦",
        "type": "automation",
        "endpoint": "http://triage-engine:9501",
        "capabilities": [
            {
                "name": "container_triage",
                "description": "Triage and prioritize container issues",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 200,
                "success_rate": 0.97,
                "max_concurrent": 20
            }
        ],
        "specializations": ["triage", "prioritization", "diagnostics"]
    },
    {
        "agent_id": "revival-engine",
        "name": "Revival Engine 🔄",
        "type": "automation",
        "endpoint": "http://revival-engine:9502",
        "capabilities": [
            {
                "name": "agent_revival",
                "description": "Revive failed agents",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "average_latency_ms": 500,
                "success_rate": 0.92,
                "max_concurrent": 5
            }
        ],
        "specializations": ["revival", "resurrection", "recovery"]
    }
]

async def register_all_agents():
    """Register all Trinity agents with the A2A Hub"""
    nc = NATS()
    
    try:
        # Connect to NATS
        await nc.connect("nats://localhost:4222")
        logger.info("🔗 Connected to NATS")
        
        success_count = 0
        failed_count = 0
        
        for agent in TRINITY_AGENTS:
            try:
                logger.info(f"📝 Registering {agent['name']}...")
                
                # Send registration request
                response = await nc.request(
                    "a2a.register",
                    json.dumps(agent).encode(),
                    timeout=5
                )
                
                # The first reply is usually a JetStream ACK like {"stream":"A2A_EVENTS","seq":N}.
                # Treat any JSON reply that lacks an explicit error as success.
                result = json.loads(response.data.decode())
                
                if result.get('status') == 'registered' or (
                    'stream' in result and 'seq' in result and not result.get('status') == 'error'
                ):
                    logger.info(f"   ✅ {agent['name']} registered successfully (ACK={result.get('seq')})")
                    success_count += 1
                else:
                    logger.error(f"   ❌ {agent['name']} registration failed: {result}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"   ❌ {agent['name']} registration error: {e}")
                failed_count += 1
                
            # Small delay between registrations
            await asyncio.sleep(0.1)
        
        # Check hub status
        logger.info("\n🌐 Checking A2A Hub status...")
        try:
            response = await nc.request(
                "a2a.discover",
                json.dumps({"type": "all"}).encode(),
                timeout=5
            )
            
            result = json.loads(response.data.decode())
            total_agents = len(result.get('agents', []))
            
            logger.info(f"\n📊 Registration Summary:")
            logger.info(f"   ✅ Successful: {success_count}")
            logger.info(f"   ❌ Failed: {failed_count}")
            logger.info(f"   🌐 Total in Hub: {total_agents}")
            
            # List capabilities
            response = await nc.request(
                "a2a.discover",
                json.dumps({"type": "capability", "capability": "all"}).encode(),
                timeout=5
            )
            
        except Exception as e:
            logger.error(f"Could not get hub status: {e}")
        
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {e}")
        logger.info("\n💡 Make sure:")
        logger.info("   1. NATS is running on localhost:4222")
        logger.info("   2. A2A Hub is running and connected to NATS")
        logger.info("   3. Run: docker-compose -f services/a2a-hub/docker-compose.yml up -d")
    
    finally:
        await nc.close()

async def test_routing():
    """Test A2A routing with a sample request"""
    nc = NATS()
    
    try:
        await nc.connect("nats://localhost:4222")
        logger.info("\n🧪 Testing A2A routing...")
        
        # Test routing request
        test_request = {
            "capability": "code_generation",
            "priority": 2,
            "message": {
                "task": "Generate a hello world function",
                "language": "python"
            },
            "source_agent": "test-client"
        }
        
        response = await nc.request(
            "a2a.route",
            json.dumps(test_request).encode(),
            timeout=5
        )
        
        result = json.loads(response.data.decode())
        logger.info(f"🎯 Routing result: {json.dumps(result, indent=2)}")
        
    except Exception as e:
        logger.error(f"Routing test failed: {e}")
    
    finally:
        await nc.close()

async def main():
    """Main entry point"""
    logger.info("🌟 TRINITY AGENT REGISTRATION HELPER 🌟")
    logger.info("======================================")
    
    # Register all agents
    await register_all_agents()
    
    # Test routing
    await test_routing()
    
    logger.info("\n✨ Registration complete!")
    logger.info("\n📋 Next steps:")
    logger.info("   1. View all agents: curl http://localhost:9002/agents")
    logger.info("   2. View capabilities: curl http://localhost:9002/capabilities")
    logger.info("   3. Monitor metrics: curl http://localhost:10002/metrics")
    logger.info("   4. Test routing: curl -X POST http://localhost:9002/route -d '{...}'")

if __name__ == "__main__":
    asyncio.run(main())