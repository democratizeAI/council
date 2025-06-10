#!/usr/bin/env python3
"""
Day-1 Event Injector (BC-140)
Posts Bug A, Bug B, Feature F rows via /ledger/new for BC-140
"""

import os
import sys
import json
import time
import requests
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Add project root to path
sys.path.append('.')

try:
    from common.a2a_bus import A2ABus
except ImportError:
    A2ABus = None
    print("Warning: A2A bus not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('day1-injector')

# Configuration
COUNCIL_API_URL = os.getenv('COUNCIL_API_URL', 'http://council-api:8080')
LEDGER_ENDPOINT = f"{COUNCIL_API_URL}/ledger/new"

# Predefined ticket templates
TICKET_TEMPLATES = {
    "A": {
        "type": "bug",
        "priority": "high",
        "title": "Memory leak in council-router connection pooling",
        "description": """
# Bug Report: Memory leak in council-router connection pooling

## Summary
Connection pooling in council-router exhibits gradual memory growth over 24+ hour periods.

## Symptoms
- RSS memory grows from ~200MB to ~800MB over 24h
- No corresponding increase in active connections
- GC pressure increases linearly with uptime

## Impact
- Service restarts required every 24-48h
- Increased latency during high memory periods
- Risk of OOM kills in production

## Reproduction
1. Start council-router with default config
2. Generate sustained load (1000 req/min)
3. Monitor RSS memory every hour
4. Observe linear growth pattern

## Expected Fix
Implement proper connection cleanup in pool manager.

## Related Metrics
- `council_router_memory_rss_bytes`
- `council_router_connections_active`
- `council_router_gc_duration_seconds`
        """.strip(),
        "labels": ["bug", "memory", "council-router", "high-priority"],
        "assignee": "platform-team",
        "estimated_hours": 16,
        "components": ["council-router", "connection-pool"]
    },
    "B": {
        "type": "bug", 
        "priority": "medium",
        "title": "Inconsistent Redis connection retry backoff",
        "description": """
# Bug Report: Inconsistent Redis connection retry backoff

## Summary
Redis connection retry logic uses inconsistent backoff strategies across services.

## Symptoms
- Some services retry immediately on Redis disconnect
- Others use exponential backoff starting at 1s
- Inconsistent behavior during Redis maintenance
- Thundering herd during Redis cluster failover

## Impact
- Service instability during Redis maintenance
- Increased load on Redis during recovery
- Inconsistent user experience across services

## Services Affected
- council-api: immediate retry
- ledger-service: 1s fixed backoff
- a2a-bus: exponential backoff (correct)

## Expected Fix
Standardize retry backoff across all Redis clients:
- Initial delay: 100ms
- Max delay: 30s
- Backoff factor: 2.0
- Max retries: 10

## Test Cases
- Redis cluster failover scenarios
- Network partition recovery
- Redis planned maintenance windows
        """.strip(),
        "labels": ["bug", "redis", "consistency", "infrastructure"],
        "assignee": "platform-team",
        "estimated_hours": 8,
        "components": ["redis-client", "council-api", "ledger-service"]
    },
    "F": {
        "type": "feature",
        "priority": "medium",
        "title": "A2A message compression for large payloads",
        "description": """
# Feature Request: A2A message compression for large payloads

## Summary
Implement optional compression for A2A messages exceeding configurable size threshold.

## Business Case
- Large deployment manifests (>10KB) cause A2A performance degradation
- Network bandwidth optimization for distributed environments
- Reduced Redis memory usage for message queues

## Acceptance Criteria
1. **Compression Threshold**: Configurable size limit (default: 1KB)
2. **Compression Algorithm**: LZ4 for speed, optional GZIP for ratio
3. **Transparent Operation**: No API changes for existing consumers
4. **Performance**: <5ms compression overhead for 10KB payloads
5. **Metrics**: Track compression ratios and performance impact

## Implementation Plan
- [ ] Add compression layer to A2A bus publish path
- [ ] Implement auto-detection on consume path
- [ ] Add configuration options to common/a2a_bus.py
- [ ] Add metrics for compression performance
- [ ] Update documentation and examples

## Success Metrics
- 50%+ size reduction for large deployment manifests
- <10ms latency increase for compressed messages
- Zero backward compatibility issues

## Configuration
```yaml
a2a:
  compression:
    enabled: true
    threshold_bytes: 1024
    algorithm: "lz4"  # or "gzip"
    level: 1  # compression level
```

## Testing Strategy
- Unit tests for compression/decompression
- Performance benchmarks with various payload sizes
- Backward compatibility tests with existing consumers
        """.strip(),
        "labels": ["feature", "a2a", "performance", "compression"],
        "assignee": "platform-team", 
        "estimated_hours": 24,
        "components": ["a2a-bus", "compression", "performance"]
    }
}


class Day1Injector:
    """Injects Day-1 development tickets via Council API"""
    
    def __init__(self, council_url: str = COUNCIL_API_URL):
        self.council_url = council_url
        self.ledger_endpoint = f"{council_url}/ledger/new"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "day1-injector/BC-140",
            "Content-Type": "application/json"
        })
        
        # A2A integration
        self.a2a_bus = None
        if A2ABus:
            try:
                self.a2a_bus = A2ABus('day1-injector')
                logger.info("🔌 A2A bus initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize A2A bus: {e}")
        
        logger.info(f"🏗️ Day-1 Injector initialized")
        logger.info(f"   Council API: {council_url}")
        logger.info(f"   Ledger endpoint: {self.ledger_endpoint}")
    
    def publish_injection_event(self, event_type: str, details: dict = None):
        """Publish injection events to A2A bus"""
        if not self.a2a_bus:
            return
        
        try:
            payload = {
                "event_type": event_type,
                "timestamp": time.time(),
                "injector_version": "BC-140",
                **(details or {})
            }
            
            stream_id = self.a2a_bus.pub(
                row_id=f"DAY1_INJECT_{event_type}",
                payload=payload,
                event_type=event_type
            )
            
            logger.info(f"📤 Published {event_type} event: {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish {event_type} event: {e}")
    
    def create_ticket_payload(self, ticket_id: str, custom_fields: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create ledger payload for a ticket"""
        if ticket_id not in TICKET_TEMPLATES:
            raise ValueError(f"Unknown ticket ID: {ticket_id}. Available: {list(TICKET_TEMPLATES.keys())}")
        
        template = TICKET_TEMPLATES[ticket_id].copy()
        
        # Merge custom fields
        if custom_fields:
            template.update(custom_fields)
        
        # Generate unique row ID
        timestamp = int(time.time())
        row_id = f"DAY1_{ticket_id}_{timestamp}"
        
        # Create ledger payload
        payload = {
            "row_id": row_id,
            "row_type": "ticket",
            "created_at": datetime.now().isoformat(),
            "created_by": "day1-injector",
            "ticket_data": {
                "id": ticket_id,
                "status": "open",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                **template
            },
            "metadata": {
                "source": "day1-injector",
                "version": "BC-140",
                "injected_at": datetime.now().isoformat()
            }
        }
        
        return payload
    
    def inject_ticket(self, ticket_id: str, custom_fields: Dict[str, Any] = None) -> Dict[str, Any]:
        """Inject a single ticket via Council API"""
        logger.info(f"📝 Injecting ticket {ticket_id}")
        
        try:
            # Create payload
            payload = self.create_ticket_payload(ticket_id, custom_fields)
            
            # Log ticket details
            ticket_data = payload["ticket_data"]
            logger.info(f"   Type: {ticket_data['type']}")
            logger.info(f"   Priority: {ticket_data['priority']}")
            logger.info(f"   Title: {ticket_data['title']}")
            logger.info(f"   Estimated hours: {ticket_data.get('estimated_hours', 'N/A')}")
            
            # Make API request
            logger.debug(f"POST {self.ledger_endpoint}")
            response = self.session.post(
                self.ledger_endpoint,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            logger.info(f"✅ Ticket {ticket_id} injected successfully")
            logger.info(f"   Row ID: {payload['row_id']}")
            logger.info(f"   Response: {response_data.get('status', 'unknown')}")
            
            # Publish success event
            self.publish_injection_event("TICKET_INJECTED", {
                "ticket_id": ticket_id,
                "row_id": payload["row_id"],
                "ticket_type": ticket_data["type"],
                "priority": ticket_data["priority"],
                "response_status": response_data.get("status")
            })
            
            return {
                "success": True,
                "ticket_id": ticket_id,
                "row_id": payload["row_id"],
                "response": response_data,
                "payload": payload
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API request failed for ticket {ticket_id}: {e}")
            
            # Publish failure event
            self.publish_injection_event("TICKET_INJECTION_FAILED", {
                "ticket_id": ticket_id,
                "error": str(e),
                "error_type": "api_request"
            })
            
            return {
                "success": False,
                "ticket_id": ticket_id,
                "error": str(e),
                "error_type": "api_request"
            }
            
        except Exception as e:
            logger.error(f"❌ Unexpected error injecting ticket {ticket_id}: {e}")
            
            self.publish_injection_event("TICKET_INJECTION_FAILED", {
                "ticket_id": ticket_id,
                "error": str(e),
                "error_type": "unexpected"
            })
            
            return {
                "success": False,
                "ticket_id": ticket_id,
                "error": str(e),
                "error_type": "unexpected"
            }
    
    def inject_multiple_tickets(self, ticket_ids: List[str], 
                               custom_fields: Dict[str, Dict[str, Any]] = None) -> Dict[str, Any]:
        """Inject multiple tickets"""
        logger.info(f"🚀 Starting Day-1 injection for {len(ticket_ids)} tickets")
        
        results = []
        success_count = 0
        failure_count = 0
        
        # Publish batch start event
        self.publish_injection_event("INJECTION_BATCH_START", {
            "ticket_ids": ticket_ids,
            "total_count": len(ticket_ids)
        })
        
        for ticket_id in ticket_ids:
            # Get custom fields for this ticket
            ticket_custom_fields = custom_fields.get(ticket_id, {}) if custom_fields else {}
            
            # Inject ticket
            result = self.inject_ticket(ticket_id, ticket_custom_fields)
            results.append(result)
            
            if result["success"]:
                success_count += 1
            else:
                failure_count += 1
            
            # Short delay between injections
            time.sleep(0.5)
        
        # Calculate summary
        summary = {
            "total_tickets": len(ticket_ids),
            "successful": success_count,
            "failed": failure_count,
            "success_rate": (success_count / len(ticket_ids)) * 100 if ticket_ids else 0,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"📊 Injection batch completed:")
        logger.info(f"   Total: {summary['total_tickets']}")
        logger.info(f"   Successful: {summary['successful']}")
        logger.info(f"   Failed: {summary['failed']}")
        logger.info(f"   Success rate: {summary['success_rate']:.1f}%")
        
        # Publish batch completion event
        self.publish_injection_event("INJECTION_BATCH_COMPLETE", {
            "summary": summary,
            "ticket_ids": ticket_ids
        })
        
        return summary
    
    def check_council_api_health(self) -> bool:
        """Check if Council API is available"""
        try:
            health_url = f"{self.council_url}/health"
            response = self.session.get(health_url, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Council API health check passed")
                return True
            else:
                logger.warning(f"⚠️ Council API health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Council API health check failed: {e}")
            return False
    
    def check_builder_ack_metric(self) -> Optional[float]:
        """Check Builder ACK metric to verify scaffold PRs are opening"""
        try:
            # This would typically query Prometheus for builder metrics
            # For now, simulate the check
            logger.info("📊 Checking Builder ACK metric...")
            
            # Mock metric check - in real implementation would query Prometheus
            # builder_ack_total = prometheus_query("sum(builder_ack_total)")
            
            logger.info("✅ Builder ACK metric check simulated")
            return 1.0  # Mock value
            
        except Exception as e:
            logger.error(f"❌ Failed to check Builder ACK metric: {e}")
            return None
    
    def verify_injection_success(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify that injection was successful"""
        logger.info("🔍 Verifying injection success...")
        
        verification = {
            "api_health": self.check_council_api_health(),
            "builder_ack_metric": self.check_builder_ack_metric(),
            "successful_injections": len([r for r in results if r["success"]]),
            "total_injections": len(results),
            "row_ids": [r["row_id"] for r in results if r["success"]],
            "timestamp": datetime.now().isoformat()
        }
        
        if verification["api_health"] and verification["successful_injections"] > 0:
            logger.info("✅ Injection verification passed")
        else:
            logger.warning("⚠️ Injection verification concerns detected")
        
        return verification


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Day-1 Event Injector (BC-140)")
    parser.add_argument("--bugs", nargs="*", default=["A", "B"],
                        help="Bug tickets to inject (default: A B)")
    parser.add_argument("--features", nargs="*", default=["F"],
                        help="Feature tickets to inject (default: F)")
    parser.add_argument("--council-url", default=COUNCIL_API_URL,
                        help=f"Council API URL (default: {COUNCIL_API_URL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry run mode (don't actually inject)")
    parser.add_argument("--verify", action="store_true",
                        help="Verify injection success after completion")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Combine all tickets to inject
    all_tickets = (args.bugs or []) + (args.features or [])
    
    if not all_tickets:
        logger.error("❌ No tickets specified for injection")
        exit(1)
    
    logger.info("📝 Day-1 Event Injector Starting (BC-140)")
    logger.info(f"   Bugs: {args.bugs or 'none'}")
    logger.info(f"   Features: {args.features or 'none'}")
    logger.info(f"   Council URL: {args.council_url}")
    logger.info(f"   Dry run: {args.dry_run}")
    
    try:
        # Initialize injector
        injector = Day1Injector(council_url=args.council_url)
        
        if args.dry_run:
            logger.info("🧪 DRY RUN: Would inject the following tickets:")
            for ticket_id in all_tickets:
                if ticket_id in TICKET_TEMPLATES:
                    template = TICKET_TEMPLATES[ticket_id]
                    logger.info(f"   {ticket_id}: {template['type']} - {template['title']}")
                else:
                    logger.warning(f"   {ticket_id}: UNKNOWN TICKET")
            
            logger.info("✅ Dry run completed")
            exit(0)
        
        # Check API health first
        if not injector.check_council_api_health():
            logger.error("❌ Council API health check failed")
            exit(1)
        
        # Inject tickets
        summary = injector.inject_multiple_tickets(all_tickets)
        
        # Verify if requested
        if args.verify:
            verification = injector.verify_injection_success(summary["results"])
            summary["verification"] = verification
        
        # Final status
        if summary["failed"] == 0:
            logger.info(f"🎉 SUCCESS: All {summary['successful']} tickets injected")
            exit(0)
        else:
            logger.error(f"❌ PARTIAL FAILURE: {summary['successful']}/{summary['total_tickets']} succeeded")
            exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Injection interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main() 