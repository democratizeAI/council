#!/usr/bin/env python3
"""
SciWave Swarm Coordinator - Triple Agent Synergy
🌊 Orchestrates Fetch → Review → Peer pipeline with Redis streams

Coordinates SCI-100, SCI-110, SCI-120 in distributed swarm architecture
"""

import asyncio
import redis.asyncio as redis
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import uuid

from .fetch_agent import FetchAgent
from .review_agent import ReviewAgent  
from .peer_agent import PeerAgent

logger = logging.getLogger(__name__)

@dataclass
class SwarmTicket:
    """Ticket for inter-agent communication"""
    id: str
    agent_type: str
    status: str
    payload: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class SciWaveCoordinator:
    """Orchestrates the SciWave triple agent synergy"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", config: Dict[str, Any] = None):
        self.redis_url = redis_url
        self.config = config or {}
        
        # Initialize agents
        self.fetch_agent = FetchAgent(config.get('fetch', {}))
        self.review_agent = ReviewAgent(config.get('review', {}))
        self.peer_agent = PeerAgent(config.get('peer', {}))
        
        # Redis streams for coordination
        self.streams = {
            'papers_fetched': 'sciwave:papers',
            'summaries_ready': 'sciwave:summaries', 
            'reviews_completed': 'sciwave:reviews'
        }
        
        # Coordination state
        self.running = False
        self.redis_client = None
        
        # Metrics
        self.swarm_metrics = {
            'cycles_completed': 0,
            'total_papers_processed': 0,
            'avg_cycle_time': 0.0,
            'success_rate': 0.0,
            'last_cycle': None,
            'agent_health': {
                'fetch': True,
                'review': True,
                'peer': True
            }
        }

    async def initialize(self):
        """Initialize Redis connection and streams"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            
            # Test connection
            await self.redis_client.ping()
            
            # Create consumer groups for each stream
            for stream_name in self.streams.values():
                try:
                    await self.redis_client.xgroup_create(
                        stream_name, 'sciwave_processors', id='0', mkstream=True
                    )
                except redis.RedisError:
                    # Group might already exist
                    pass
            
            logger.info("SciWave coordinator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize coordinator: {e}")
            raise

    async def cleanup(self):
        """Cleanup Redis connections"""
        if self.redis_client:
            await self.redis_client.close()

    async def create_ticket(self, agent_type: str, payload: Dict[str, Any]) -> SwarmTicket:
        """Create a new swarm ticket"""
        ticket = SwarmTicket(
            id=str(uuid.uuid4()),
            agent_type=agent_type,
            status='pending',
            payload=payload,
            created_at=datetime.now()
        )
        return ticket

    async def publish_ticket(self, stream: str, ticket: SwarmTicket) -> str:
        """Publish ticket to Redis stream"""
        try:
            ticket_data = {
                'id': ticket.id,
                'agent_type': ticket.agent_type,
                'status': ticket.status,
                'payload': json.dumps(ticket.payload),
                'created_at': ticket.created_at.isoformat(),
                'completed_at': ticket.completed_at.isoformat() if ticket.completed_at else '',
                'error': ticket.error or ''
            }
            
            message_id = await self.redis_client.xadd(stream, ticket_data)
            logger.debug(f"Published ticket {ticket.id} to stream {stream}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish ticket: {e}")
            raise

    async def consume_stream(self, stream: str, consumer_group: str, consumer_name: str, 
                           timeout: int = 1000) -> List[Dict[str, Any]]:
        """Consume messages from Redis stream"""
        try:
            messages = await self.redis_client.xreadgroup(
                consumer_group, consumer_name, {stream: '>'}, count=10, block=timeout
            )
            
            parsed_messages = []
            for stream_name, stream_messages in messages:
                for message_id, fields in stream_messages:
                    message_data = {
                        'message_id': message_id,
                        'stream': stream_name.decode(),
                        'fields': {k.decode(): v.decode() for k, v in fields.items()}
                    }
                    parsed_messages.append(message_data)
            
            return parsed_messages
            
        except Exception as e:
            logger.error(f"Failed to consume from stream {stream}: {e}")
            return []

    async def ack_message(self, stream: str, consumer_group: str, message_id: str):
        """Acknowledge processed message"""
        try:
            await self.redis_client.xack(stream, consumer_group, message_id)
        except Exception as e:
            logger.error(f"Failed to ack message {message_id}: {e}")

    async def daily_fetch_cycle(self) -> Dict[str, Any]:
        """Execute SCI-100 daily fetch cycle"""
        try:
            logger.info("🔬 Starting daily fetch cycle...")
            
            # Execute fetch
            fetch_result = await self.fetch_agent.daily_fetch_cycle()
            
            # Create tickets for each paper
            papers = fetch_result.get('papers', [])
            tickets_created = []
            
            for paper in papers:
                ticket = await self.create_ticket('review', paper)
                message_id = await self.publish_ticket(self.streams['papers_fetched'], ticket)
                tickets_created.append(ticket.id)
            
            # Update health status
            self.swarm_metrics['agent_health']['fetch'] = fetch_result.get('kpi_gate_passed', False)
            
            result = {
                'fetch_result': fetch_result,
                'tickets_created': len(tickets_created),
                'ticket_ids': tickets_created,
                'status': 'success' if fetch_result.get('kpi_gate_passed') else 'kpi_failure'
            }
            
            logger.info(f"Fetch cycle completed: {len(papers)} papers, {len(tickets_created)} tickets")
            return result
            
        except Exception as e:
            logger.error(f"Daily fetch cycle failed: {e}")
            self.swarm_metrics['agent_health']['fetch'] = False
            return {'status': 'error', 'error': str(e)}

    async def review_processing_cycle(self) -> Dict[str, Any]:
        """Execute SCI-110 review processing cycle"""
        try:
            logger.info("🧠 Starting review processing cycle...")
            
            # Consume papers from fetch stream
            messages = await self.consume_stream(
                self.streams['papers_fetched'], 
                'sciwave_processors', 
                'review_worker'
            )
            
            summaries_created = []
            processed_count = 0
            
            for message in messages:
                try:
                    # Parse ticket
                    fields = message['fields']
                    paper_data = json.loads(fields['payload'])
                    
                    # Generate review/summary
                    summary = await self.review_agent.review_paper(paper_data)
                    
                    # Create summary ticket
                    summary_data = asdict(summary)
                    summary_data['timestamp'] = summary_data['timestamp'].isoformat()
                    
                    ticket = await self.create_ticket('peer', summary_data)
                    message_id = await self.publish_ticket(self.streams['summaries_ready'], ticket)
                    
                    summaries_created.append(ticket.id)
                    processed_count += 1
                    
                    # Acknowledge original message
                    await self.ack_message(
                        self.streams['papers_fetched'],
                        'sciwave_processors',
                        message['message_id']
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to process review message: {e}")
                    continue
            
            # Update health status
            kpi_passed = self.review_agent.check_kpi_gate()
            self.swarm_metrics['agent_health']['review'] = kpi_passed
            
            result = {
                'messages_processed': processed_count,
                'summaries_created': len(summaries_created),
                'summary_ids': summaries_created,
                'kpi_gate_passed': kpi_passed,
                'avg_bleu_score': self.review_agent.get_metrics().get('avg_bleu_score', 0.0),
                'status': 'success' if kpi_passed else 'kpi_failure'
            }
            
            logger.info(f"Review cycle completed: {processed_count} papers reviewed")
            return result
            
        except Exception as e:
            logger.error(f"Review processing cycle failed: {e}")
            self.swarm_metrics['agent_health']['review'] = False
            return {'status': 'error', 'error': str(e)}

    async def peer_review_cycle(self) -> Dict[str, Any]:
        """Execute SCI-120 peer review cycle"""
        try:
            logger.info("👥 Starting peer review cycle...")
            
            # Consume summaries from review stream
            messages = await self.consume_stream(
                self.streams['summaries_ready'],
                'sciwave_processors', 
                'peer_worker'
            )
            
            summaries = []
            processed_count = 0
            
            # Collect summaries for batch processing
            for message in messages:
                try:
                    fields = message['fields']
                    summary_data = json.loads(fields['payload'])
                    summaries.append(summary_data)
                    processed_count += 1
                    
                    # Acknowledge message
                    await self.ack_message(
                        self.streams['summaries_ready'],
                        'sciwave_processors',
                        message['message_id']
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to process peer message: {e}")
                    continue
            
            # Execute peer review cycle
            if summaries:
                peer_result = await self.peer_agent.peer_review_cycle(summaries)
                
                # Publish final results
                final_ticket = await self.create_ticket('complete', peer_result)
                await self.publish_ticket(self.streams['reviews_completed'], final_ticket)
            else:
                peer_result = {'reviews': [], 'comparisons': [], 'kpi_gate_passed': False}
            
            # Update health status
            kpi_passed = peer_result.get('kpi_gate_passed', False)
            self.swarm_metrics['agent_health']['peer'] = kpi_passed
            
            result = {
                'summaries_processed': processed_count,
                'peer_result': peer_result,
                'kpi_gate_passed': kpi_passed,
                'avg_delta_confidence': peer_result.get('avg_delta_confidence', 0.0),
                'status': 'success' if kpi_passed else 'kpi_failure'
            }
            
            logger.info(f"Peer review cycle completed: {processed_count} summaries reviewed")
            return result
            
        except Exception as e:
            logger.error(f"Peer review cycle failed: {e}")
            self.swarm_metrics['agent_health']['peer'] = False
            return {'status': 'error', 'error': str(e)}

    async def full_swarm_cycle(self) -> Dict[str, Any]:
        """Execute complete fetch → review → peer cycle"""
        cycle_start = datetime.now()
        
        try:
            logger.info("🌊 Starting full SciWave swarm cycle...")
            
            # Phase 1: Fetch papers
            fetch_result = await self.daily_fetch_cycle()
            
            # Wait for papers to be available for processing
            await asyncio.sleep(2)
            
            # Phase 2: Review papers
            review_result = await self.review_processing_cycle()
            
            # Wait for summaries to be available
            await asyncio.sleep(2)
            
            # Phase 3: Peer review
            peer_result = await self.peer_review_cycle()
            
            # Calculate cycle metrics
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            
            # Overall success criteria
            all_kpi_passed = (
                fetch_result.get('status') == 'success' and
                review_result.get('kpi_gate_passed', False) and
                peer_result.get('kpi_gate_passed', False)
            )
            
            # Update swarm metrics
            self.swarm_metrics['cycles_completed'] += 1
            self.swarm_metrics['last_cycle'] = datetime.now().isoformat()
            
            if 'papers' in fetch_result.get('fetch_result', {}):
                papers_count = len(fetch_result['fetch_result']['papers'])
                self.swarm_metrics['total_papers_processed'] += papers_count
            
            # Update average cycle time
            if self.swarm_metrics['avg_cycle_time'] == 0:
                self.swarm_metrics['avg_cycle_time'] = cycle_time
            else:
                self.swarm_metrics['avg_cycle_time'] = (
                    self.swarm_metrics['avg_cycle_time'] * 0.7 + cycle_time * 0.3
                )
            
            # Update success rate
            total_cycles = self.swarm_metrics['cycles_completed']
            if all_kpi_passed:
                success_count = int(self.swarm_metrics['success_rate'] * (total_cycles - 1)) + 1
            else:
                success_count = int(self.swarm_metrics['success_rate'] * (total_cycles - 1))
            
            self.swarm_metrics['success_rate'] = success_count / total_cycles
            
            result = {
                'cycle_id': str(uuid.uuid4()),
                'phases': {
                    'fetch': fetch_result,
                    'review': review_result,
                    'peer': peer_result
                },
                'overall_success': all_kpi_passed,
                'cycle_time_seconds': cycle_time,
                'swarm_metrics': self.swarm_metrics.copy(),
                'timestamp': datetime.now().isoformat(),
                'agent_health': self.swarm_metrics['agent_health'].copy()
            }
            
            logger.info(f"Full swarm cycle completed in {cycle_time:.2f}s, success: {all_kpi_passed}")
            return result
            
        except Exception as e:
            logger.error(f"Full swarm cycle failed: {e}")
            return {
                'cycle_id': str(uuid.uuid4()),
                'overall_success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def start_continuous_processing(self, cycle_interval: int = 3600):
        """Start continuous processing with specified interval (seconds)"""
        self.running = True
        
        logger.info(f"Starting continuous SciWave processing (interval: {cycle_interval}s)")
        
        while self.running:
            try:
                # Execute full cycle
                result = await self.full_swarm_cycle()
                
                # Log results
                if result.get('overall_success'):
                    logger.info("✅ Swarm cycle completed successfully")
                else:
                    logger.warning("⚠️ Swarm cycle completed with issues")
                
                # Wait for next cycle
                await asyncio.sleep(cycle_interval)
                
            except Exception as e:
                logger.error(f"Continuous processing error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

    def stop_continuous_processing(self):
        """Stop continuous processing"""
        self.running = False
        logger.info("Stopping continuous SciWave processing")

    def get_swarm_metrics(self) -> Dict[str, Any]:
        """Get comprehensive swarm metrics"""
        return {
            'swarm_metrics': self.swarm_metrics.copy(),
            'agent_metrics': {
                'fetch': self.fetch_agent.get_metrics(),
                'review': self.review_agent.get_metrics(), 
                'peer': self.peer_agent.get_metrics()
            },
            'timestamp': datetime.now().isoformat()
        }

# Test function
async def test_sciwave_coordinator():
    """Test the SciWave coordinator"""
    coordinator = SciWaveCoordinator()
    
    try:
        await coordinator.initialize()
        
        print("🌊 Testing SciWave Coordinator...")
        
        # Test full cycle
        result = await coordinator.full_swarm_cycle()
        
        print(f"Cycle completed: {result.get('overall_success')}")
        print(f"Cycle time: {result.get('cycle_time_seconds', 0):.2f}s")
        print(f"Agent health: {result.get('agent_health', {})}")
        
        # Get metrics
        metrics = coordinator.get_swarm_metrics()
        print(f"Swarm metrics: {metrics['swarm_metrics']}")
        
        return result
        
    finally:
        await coordinator.cleanup()

if __name__ == "__main__":
    asyncio.run(test_sciwave_coordinator()) 