#!/usr/bin/env python3
"""
🌐 TRINITY A2A HUB - STANDALONE RUNNER 🌐
=======================================
Run A2A Hub directly without Docker complications
"""

import os
import sys
import asyncio
import subprocess
import time

def check_dependencies():
    """Check and install required dependencies"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        'nats-py',
        'aiohttp',
        'aioredis',
        'asyncpg',
        'prometheus-client'
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_').split('=')[0])
            print(f"✅ {package} installed")
        except ImportError:
            print(f"📥 Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def create_simplified_a2a_hub():
    """Create a simplified A2A Hub that works with your setup"""
    
    hub_code = '''#!/usr/bin/env python3
"""
🌐 TRINITY A2A HUB - SIMPLIFIED VERSION 🌐
========================================
Streamlined for immediate deployment
"""

import os
import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime

from nats.aio.client import Client as NATS
from aiohttp import web
from prometheus_client import Counter, Histogram, Gauge, start_http_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("A2A-Hub")

# Metrics
message_counter = Counter('a2a_messages_total', 'Total messages routed')
active_agents = Gauge('a2a_active_agents', 'Number of active agents')

@dataclass
class Agent:
    id: str
    name: str
    capabilities: List[str]
    endpoint: str
    status: str = "online"
    last_heartbeat: float = 0

class SimplifiedA2AHub:
    """Simplified A2A Hub for immediate deployment"""
    
    def __init__(self):
        self.nc = None
        self.agents: Dict[str, Agent] = {}
        self.running = False
        self.app = web.Application()
        
        # Use environment or defaults
        self.nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        self.hub_port = int(os.getenv("A2A_HUB_PORT", "9002"))
        
        logger.info(f"🌐 A2A Hub starting on port {self.hub_port}")
        logger.info(f"   NATS: {self.nats_url}")
    
    async def start(self):
        """Start the hub"""
        try:
            # Connect to NATS
            await self._connect_nats()
            
            # Setup routes
            self._setup_routes()
            
            # Start web server
            runner = web.AppRunner(self.app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', self.hub_port)
            await site.start()
            
            logger.info(f"✅ A2A Hub running on http://0.0.0.0:{self.hub_port}")
            
            # Start metrics
            start_http_server(self.hub_port + 1000)
            
            self.running = True
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Failed to start: {e}")
            raise
    
    async def _connect_nats(self):
        """Connect to NATS"""
        self.nc = NATS()
        
        for attempt in range(5):
            try:
                await self.nc.connect(self.nats_url)
                logger.info("✅ Connected to NATS")
                
                # Subscribe to core topics
                await self.nc.subscribe("a2a.register", cb=self._handle_register)
                await self.nc.subscribe("a2a.discover", cb=self._handle_discover)
                await self.nc.subscribe("a2a.route", cb=self._handle_route)
                await self.nc.subscribe("a2a.heartbeat", cb=self._handle_heartbeat)
                
                return
            except Exception as e:
                logger.warning(f"NATS connection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2)
        
        raise Exception("Could not connect to NATS after 5 attempts")
    
    async def _handle_register(self, msg):
        """Handle agent registration"""
        try:
            data = json.loads(msg.data.decode())
            
            agent = Agent(
                id=data.get('agent_id', data.get('name', 'unknown')),
                name=data.get('name', 'Unknown'),
                capabilities=[
                    cap.get('name', 'unknown') 
                    for cap in data.get('capabilities', [])
                ],
                endpoint=data.get('endpoint', ''),
                last_heartbeat=time.time()
            )
            
            self.agents[agent.id] = agent
            active_agents.set(len(self.agents))
            
            logger.info(f"✅ Registered: {agent.name} with {len(agent.capabilities)} capabilities")
            
            # Send confirmation
            if msg.reply:
                await self.nc.publish(msg.reply, json.dumps({
                    'status': 'registered',
                    'agent_id': agent.id
                }).encode())
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            if msg.reply:
                await self.nc.publish(msg.reply, json.dumps({
                    'status': 'error',
                    'error': str(e)
                }).encode())
    
    async def _handle_discover(self, msg):
        """Handle discovery requests"""
        try:
            response = {
                'agents': [
                    {
                        'id': agent.id,
                        'name': agent.name,
                        'capabilities': agent.capabilities,
                        'status': agent.status
                    }
                    for agent in self.agents.values()
                ]
            }
            
            if msg.reply:
                await self.nc.publish(msg.reply, json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"Discovery error: {e}")
    
    async def _handle_route(self, msg):
        """Handle routing requests"""
        try:
            data = json.loads(msg.data.decode())
            capability = data.get('capability')
            
            # Find agents with capability
            capable_agents = [
                agent for agent in self.agents.values()
                if capability in agent.capabilities and agent.status == 'online'
            ]
            
            if capable_agents:
                # Simple round-robin selection
                agent = capable_agents[0]
                
                message_counter.inc()
                
                response = {
                    'status': 'routed',
                    'agent_id': agent.id,
                    'agent_name': agent.name,
                    'endpoint': agent.endpoint
                }
                
                logger.info(f"🎯 Routed {capability} to {agent.name}")
            else:
                response = {
                    'status': 'no_agent_available',
                    'capability': capability
                }
                logger.warning(f"No agent available for {capability}")
            
            if msg.reply:
                await self.nc.publish(msg.reply, json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"Routing error: {e}")
    
    async def _handle_heartbeat(self, msg):
        """Handle heartbeats"""
        try:
            data = json.loads(msg.data.decode())
            agent_id = data.get('agent_id')
            
            if agent_id in self.agents:
                self.agents[agent_id].last_heartbeat = time.time()
                self.agents[agent_id].status = 'online'
                
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/health', self._handle_health)
        self.app.router.add_get('/agents', self._handle_agents)
        self.app.router.add_get('/capabilities', self._handle_capabilities)
    
    async def _handle_health(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'agents': len(self.agents),
            'uptime': int(time.time())
        })
    
    async def _handle_agents(self, request):
        """List agents endpoint"""
        return web.json_response({
            'agents': [asdict(agent) for agent in self.agents.values()]
        })
    
    async def _handle_capabilities(self, request):
        """List capabilities endpoint"""
        capabilities = {}
        for agent in self.agents.values():
            for cap in agent.capabilities:
                if cap not in capabilities:
                    capabilities[cap] = []
                capabilities[cap].append(agent.id)
        
        return web.json_response({'capabilities': capabilities})

async def main():
    """Run the simplified A2A Hub"""
    hub = SimplifiedA2AHub()
    
    try:
        await hub.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if hub.nc:
            await hub.nc.close()

if __name__ == "__main__":
    print("🌟 TRINITY A2A HUB - SIMPLIFIED VERSION 🌟")
    print("========================================")
    asyncio.run(main())
'''
    
    # Write the hub file
    with open('a2a_hub_simple.py', 'w') as f:
        f.write(hub_code)
    
    print("✅ Created simplified A2A Hub: a2a_hub_simple.py")

def main():
    """Main runner"""
    print("🌐 TRINITY A2A HUB STANDALONE RUNNER")
    print("====================================")
    
    # Check dependencies
    check_dependencies()
    
    # Create simplified hub
    create_simplified_a2a_hub()
    
    print("\n📋 Starting A2A Hub...")
    print("This will run in the foreground. Press Ctrl+C to stop.")
    print("")
    
    # Run the hub
    try:
        subprocess.run([sys.executable, 'a2a_hub_simple.py'])
    except KeyboardInterrupt:
        print("\n👋 A2A Hub stopped")

if __name__ == "__main__":
    main()
