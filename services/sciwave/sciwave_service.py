#!/usr/bin/env python3
"""
SciWave Service - Production Triple Agent Swarm
🌊 Production-ready service wrapper for SCI-100, SCI-110, SCI-120

Provides:
- Health checks and readiness probes
- Prometheus metrics export
- Graceful shutdown
- Error recovery
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import redis.asyncio as redis

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.sciwave import SciWaveCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
CYCLES_TOTAL = Counter('sciwave_cycles_total', 'Total SciWave cycles executed')
CYCLE_DURATION = Histogram('sciwave_cycle_duration_seconds', 'SciWave cycle duration')
PAPERS_PROCESSED = Counter('sciwave_papers_processed_total', 'Total papers processed')
KPI_GATES_PASSED = Counter('sciwave_kpi_gates_passed_total', 'KPI gates passed', ['agent'])
AGENT_HEALTH = Gauge('sciwave_agent_health', 'Agent health status', ['agent'])
SWARM_SUCCESS_RATE = Gauge('sciwave_success_rate', 'Overall swarm success rate')

class SciWaveService:
    """Production SciWave service"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.coordinator = None
        self.running = False
        self.background_task = None
        
        # Service state
        self.startup_time = datetime.now()
        self.last_cycle_time = None
        self.error_count = 0
        self.max_errors = 10

    async def initialize(self):
        """Initialize the SciWave coordinator"""
        try:
            redis_url = self.config.get('redis_url', 'redis://redis:6379')
            
            self.coordinator = SciWaveCoordinator(
                redis_url=redis_url,
                config=self.config.get('agents', {})
            )
            
            await self.coordinator.initialize()
            
            logger.info("SciWave service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SciWave service: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            if not self.coordinator:
                return {'status': 'unhealthy', 'reason': 'coordinator_not_initialized'}
            
            # Test Redis connection
            try:
                await self.coordinator.redis_client.ping()
                redis_healthy = True
            except:
                redis_healthy = False
            
            # Check agent health
            agent_health = self.coordinator.swarm_metrics['agent_health']
            all_agents_healthy = all(agent_health.values())
            
            # Overall health
            healthy = redis_healthy and all_agents_healthy and self.error_count < self.max_errors
            
            return {
                'status': 'healthy' if healthy else 'unhealthy',
                'redis': redis_healthy,
                'agents': agent_health,
                'error_count': self.error_count,
                'uptime_seconds': (datetime.now() - self.startup_time).total_seconds(),
                'last_cycle': self.last_cycle_time,
                'running': self.running
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'status': 'unhealthy', 'reason': str(e)}

    async def readiness_check(self) -> Dict[str, Any]:
        """Readiness check for Kubernetes"""
        try:
            health = await self.health_check()
            
            ready = (
                health['status'] == 'healthy' and
                health['redis'] and
                self.coordinator is not None
            )
            
            return {
                'status': 'ready' if ready else 'not_ready',
                'details': health
            }
            
        except Exception as e:
            return {'status': 'not_ready', 'reason': str(e)}

    async def execute_cycle(self) -> Dict[str, Any]:
        """Execute single SciWave cycle with metrics"""
        try:
            with CYCLE_DURATION.time():
                result = await self.coordinator.full_swarm_cycle()
            
            # Update metrics
            CYCLES_TOTAL.inc()
            self.last_cycle_time = datetime.now().isoformat()
            
            if result.get('overall_success'):
                self.error_count = max(0, self.error_count - 1)  # Reduce error count on success
            else:
                self.error_count += 1
            
            # Update agent-specific metrics
            for agent_name, health in result.get('agent_health', {}).items():
                AGENT_HEALTH.labels(agent=agent_name).set(1 if health else 0)
                if health:
                    KPI_GATES_PASSED.labels(agent=agent_name).inc()
            
            # Update papers processed
            phases = result.get('phases', {})
            if 'fetch' in phases and 'fetch_result' in phases['fetch']:
                papers_count = len(phases['fetch']['fetch_result'].get('papers', []))
                PAPERS_PROCESSED.inc(papers_count)
            
            # Update success rate
            swarm_metrics = self.coordinator.get_swarm_metrics()
            success_rate = swarm_metrics['swarm_metrics'].get('success_rate', 0.0)
            SWARM_SUCCESS_RATE.set(success_rate)
            
            return result
            
        except Exception as e:
            logger.error(f"Cycle execution failed: {e}")
            self.error_count += 1
            return {'overall_success': False, 'error': str(e)}

    async def start_background_processing(self, interval: int = 3600):
        """Start background processing task"""
        self.running = True
        
        async def background_worker():
            while self.running:
                try:
                    await self.execute_cycle()
                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"Background processing error: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute on error
        
        self.background_task = asyncio.create_task(background_worker())
        logger.info(f"Started background processing with {interval}s interval")

    async def stop_background_processing(self):
        """Stop background processing"""
        self.running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped background processing")

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_background_processing()
        if self.coordinator:
            await self.coordinator.cleanup()

# FastAPI application
app = FastAPI(
    title="SciWave Triple Agent Swarm",
    description="Long-term science planning & literature summarization",
    version="0.1.0"
)

# Global service instance
service = None

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    global service
    
    # Load configuration
    config = {
        'redis_url': os.getenv('REDIS_URL', 'redis://redis:6379'),
        'agents': {
            'fetch': {},
            'review': {},
            'peer': {}
        }
    }
    
    service = SciWaveService(config)
    await service.initialize()
    
    # Start background processing if enabled
    if os.getenv('SCIWAVE_BACKGROUND_ENABLED', 'true').lower() == 'true':
        interval = int(os.getenv('SCIWAVE_CYCLE_INTERVAL', '3600'))
        await service.start_background_processing(interval)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global service
    if service:
        await service.cleanup()

@app.get("/health")
async def health():
    """Health check endpoint"""
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    health_status = await service.health_check()
    
    if health_status['status'] == 'healthy':
        return JSONResponse(content=health_status)
    else:
        raise HTTPException(status_code=503, detail=health_status)

@app.get("/ready") 
async def ready():
    """Readiness check endpoint"""
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    readiness = await service.readiness_check()
    
    if readiness['status'] == 'ready':
        return JSONResponse(content=readiness)
    else:
        raise HTTPException(status_code=503, detail=readiness)

@app.post("/cycle")
async def trigger_cycle(background_tasks: BackgroundTasks):
    """Manually trigger a SciWave cycle"""
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    background_tasks.add_task(service.execute_cycle)
    
    return {"message": "Cycle triggered", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest().decode('utf-8')

@app.get("/status")
async def status():
    """Detailed status information"""
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    health = await service.health_check()
    swarm_metrics = service.coordinator.get_swarm_metrics() if service.coordinator else {}
    
    return {
        'service': health,
        'swarm': swarm_metrics,
        'timestamp': datetime.now().isoformat()
    }

@app.get("/agents/{agent_name}/metrics")
async def agent_metrics(agent_name: str):
    """Get metrics for specific agent"""
    if not service or not service.coordinator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    valid_agents = ['fetch', 'review', 'peer']
    if agent_name not in valid_agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    swarm_metrics = service.coordinator.get_swarm_metrics()
    agent_metrics = swarm_metrics['agent_metrics'].get(agent_name, {})
    
    return {
        'agent': agent_name,
        'metrics': agent_metrics,
        'timestamp': datetime.now().isoformat()
    }

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    
    # Create event loop if none exists
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run cleanup
    if service:
        loop.run_until_complete(service.cleanup())
    
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "sciwave_service:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=False,
        log_level="info"
    ) 