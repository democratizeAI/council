#!/usr/bin/env python3
"""
🌟 Gemini Streaming Auditor - QA-302
===================================

Real-time policy enforcement through continuous PR meta event streaming.
Transforms Gemini from passive reviewer to live gatekeeper with automatic rollback.

Features:
- Webhook receiver for meta events (/webhook/meta)
- Live policy assertion (coverage, latency, cost)
- Automatic rollback triggers to PatchCtl
- Prometheus metrics for tracking
- Signed webhook comments for violations

Part of Build → Test → Ship hardening rail
"""

import os
import time
import json
import logging
import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, Response
import uvicorn
from pydantic import BaseModel, Field
import redis.asyncio as redis
import aiohttp
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics for QA-302
GEMINI_META_ASSERTIONS_TOTAL = Counter(
    'gemini_meta_assertions_total',
    'Total meta assertions performed by Gemini',
    ['result', 'policy_type']
)

GEMINI_ROLLBACK_TRIGGERED_TOTAL = Counter(
    'gemini_rollback_triggered_total',
    'Total rollbacks triggered by Gemini',
    ['pr_id', 'reason']
)

GEMINI_WEBHOOK_LATENCY = Histogram(
    'gemini_webhook_latency_seconds',
    'Webhook processing latency',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ACTIVE_PR_MONITORS = Gauge(
    'gemini_active_pr_monitors',
    'Number of PRs actively monitored'
)

# Pydantic models for webhook payloads
class MetaWebhookPayload(BaseModel):
    pr_id: str = Field(..., description="PR identifier")
    meta: Dict[str, Any] = Field(..., description="Meta metrics")
    timestamp: Optional[float] = Field(default_factory=time.time)
    source: Optional[str] = Field(default="unknown")

class PolicyAssertion(BaseModel):
    policy_name: str
    value: float
    threshold: float
    operator: str  # ">=", "<=", "=="
    passed: bool
    reason: Optional[str] = None

@dataclass
class PolicyViolation:
    pr_id: str
    policy_name: str
    actual_value: float
    threshold: float
    operator: str
    severity: str  # "warning", "error", "critical"
    timestamp: datetime
    action_taken: str

class GeminiStreamingAuditor:
    """
    Real-time streaming auditor for PR policy enforcement
    Implements QA-302 continuous assertion model
    """
    
    def __init__(self):
        self.redis_client = None
        self.monitored_prs = {}  # pr_id -> monitoring_data
        
        # Policy thresholds from QA-302 spec
        self.policy_thresholds = {
            "unit_coverage": {"threshold": 95.0, "operator": ">="},
            "latency_regression": {"threshold": 1.0, "operator": "<="},
            "cost_delta": {"threshold": 0.01, "operator": "<="}
        }
        
        # Integration endpoints
        self.patchctl_url = os.environ.get("PATCHCTL_URL", "http://localhost:8090")
        self.slack_webhook = os.environ.get("SLACK_WEBHOOK_URL", None)
        
        # Signing secret for webhook validation
        self.webhook_secret = os.environ.get("GEMINI_WEBHOOK_SECRET", "qa302-secret")
        
        logger.info("🌟 Gemini Streaming Auditor initialized (QA-302)")
        
    async def initialize(self):
        """Initialize Redis connection and monitoring"""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379/0")
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
            # Subscribe to relevant streams
            await self._setup_stream_monitoring()
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise
            
    async def _setup_stream_monitoring(self):
        """Setup Redis stream monitoring for PR events"""
        try:
            # Create consumer group for meta events
            await self.redis_client.xgroup_create(
                "ticket-bus", "gemini_auditor", id="0", mkstream=True
            )
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"❌ Stream setup error: {e}")
                
    async def process_meta_webhook(self, payload: MetaWebhookPayload) -> Dict[str, Any]:
        """
        Main webhook processor for PR meta events
        Implements live policy assertion logic
        """
        start_time = time.time()
        
        try:
            logger.info(f"📥 Processing meta webhook for PR {payload.pr_id}")
            
            # Start monitoring this PR
            self._start_pr_monitoring(payload.pr_id)
            
            # Run policy assertions
            assertions = await self._run_policy_assertions(payload)
            
            # Check for violations
            violations = [a for a in assertions if not a.passed]
            
            if violations:
                # Handle policy violations
                await self._handle_policy_violations(payload.pr_id, violations)
                result = "violation_detected"
            else:
                # All policies passed
                await self._handle_policy_success(payload.pr_id, assertions)
                result = "policies_passed"
                
            # Record metrics
            processing_time = time.time() - start_time
            GEMINI_WEBHOOK_LATENCY.observe(processing_time)
            
            for assertion in assertions:
                GEMINI_META_ASSERTIONS_TOTAL.labels(
                    result="pass" if assertion.passed else "fail",
                    policy_type=assertion.policy_name
                ).inc()
                
            logger.info(f"✅ Webhook processed for PR {payload.pr_id} in {processing_time:.2f}s")
            
            return {
                "pr_id": payload.pr_id,
                "result": result,
                "assertions": [a.model_dump() for a in assertions],
                "violations": len(violations),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"❌ Webhook processing error for PR {payload.pr_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
            
    def _start_pr_monitoring(self, pr_id: str):
        """Start monitoring a PR"""
        self.monitored_prs[pr_id] = {
            "started_at": datetime.utcnow(),
            "violations": [],
            "last_check": datetime.utcnow()
        }
        ACTIVE_PR_MONITORS.set(len(self.monitored_prs))
        
    async def _run_policy_assertions(self, payload: MetaWebhookPayload) -> List[PolicyAssertion]:
        """Run all policy assertions against meta data"""
        assertions = []
        meta = payload.meta
        
        # Unit coverage assertion
        unit_coverage = meta.get("unit_coverage", 0.0)
        coverage_assertion = PolicyAssertion(
            policy_name="unit_coverage",
            value=unit_coverage,
            threshold=self.policy_thresholds["unit_coverage"]["threshold"],
            operator=self.policy_thresholds["unit_coverage"]["operator"],
            passed=unit_coverage >= self.policy_thresholds["unit_coverage"]["threshold"],
            reason=f"Coverage {unit_coverage}% vs required {self.policy_thresholds['unit_coverage']['threshold']}%"
        )
        assertions.append(coverage_assertion)
        
        # Latency regression assertion
        latency_regression = meta.get("latency_regression", 0.0)
        latency_assertion = PolicyAssertion(
            policy_name="latency_regression",
            value=latency_regression,
            threshold=self.policy_thresholds["latency_regression"]["threshold"],
            operator=self.policy_thresholds["latency_regression"]["operator"],
            passed=latency_regression <= self.policy_thresholds["latency_regression"]["threshold"],
            reason=f"Latency regression {latency_regression}% vs max {self.policy_thresholds['latency_regression']['threshold']}%"
        )
        assertions.append(latency_assertion)
        
        # Cost delta assertion
        cost_delta = meta.get("cost_delta", 0.0)
        cost_assertion = PolicyAssertion(
            policy_name="cost_delta",
            value=cost_delta,
            threshold=self.policy_thresholds["cost_delta"]["threshold"],
            operator=self.policy_thresholds["cost_delta"]["operator"],
            passed=cost_delta <= self.policy_thresholds["cost_delta"]["threshold"],
            reason=f"Cost delta ${cost_delta:.3f} vs max ${self.policy_thresholds['cost_delta']['threshold']:.3f}"
        )
        assertions.append(cost_assertion)
        
        return assertions
        
    async def _handle_policy_violations(self, pr_id: str, violations: List[PolicyAssertion]):
        """Handle policy violations with rollback and notifications"""
        logger.warning(f"⚠️ Policy violations detected for PR {pr_id}: {len(violations)} issues")
        
        # Record violations
        for violation in violations:
            policy_violation = PolicyViolation(
                pr_id=pr_id,
                policy_name=violation.policy_name,
                actual_value=violation.value,
                threshold=violation.threshold,
                operator=violation.operator,
                severity="error",  # All violations are errors for QA-302
                timestamp=datetime.utcnow(),
                action_taken="rollback_triggered"
            )
            
            # Store violation
            self.monitored_prs[pr_id]["violations"].append(policy_violation)
            
        # Post signed webhook comment
        await self._post_violation_comment(pr_id, violations)
        
        # Trigger PatchCtl rollback
        await self._trigger_patchctl_rollback(pr_id, violations)
        
        # Optional: Send Slack alert
        if self.slack_webhook:
            await self._send_slack_alert(pr_id, violations)
            
    async def _handle_policy_success(self, pr_id: str, assertions: List[PolicyAssertion]):
        """Handle successful policy validation"""
        logger.info(f"✅ All policies passed for PR {pr_id}")
        
        # Update monitoring data
        if pr_id in self.monitored_prs:
            self.monitored_prs[pr_id]["last_check"] = datetime.utcnow()
            
    async def _post_violation_comment(self, pr_id: str, violations: List[PolicyAssertion]):
        """Post signed webhook comment about policy violations"""
        try:
            violation_details = []
            for v in violations:
                violation_details.append(
                    f"- **{v.policy_name}**: {v.value} {v.operator} {v.threshold} ❌"
                )
                
            comment_body = f"""⚠️ **CI Policy Violation Detected** (QA-302)

**PR ID**: `{pr_id}`
**Timestamp**: {datetime.utcnow().isoformat()}Z

**Violations**:
{chr(10).join(violation_details)}

**Action Taken**: Automatic rollback triggered via PatchCtl

---
*Signed by Gemini Streaming Auditor | Hash: {self._generate_signature(pr_id)}*
"""
            
            # In a real implementation, this would post to GitHub/GitLab API
            logger.info(f"📝 Posted violation comment for PR {pr_id}")
            
            # Store comment for testing
            await self.redis_client.hset(
                f"gemini:comments:{pr_id}",
                "violation_comment",
                comment_body
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to post violation comment: {e}")
            
    async def _trigger_patchctl_rollback(self, pr_id: str, violations: List[PolicyAssertion]):
        """Trigger PatchCtl rollback for policy violations"""
        try:
            rollback_payload = {
                "pr_id": pr_id,
                "reason": "gemini_policy_violation",
                "violations": [
                    {
                        "policy": v.policy_name,
                        "actual": v.value,
                        "threshold": v.threshold,
                        "operator": v.operator
                    }
                    for v in violations
                ],
                "triggered_by": "gemini_streaming_auditor",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send rollback request to PatchCtl
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    f"{self.patchctl_url}/rollback",
                    params={"pr_id": pr_id},
                    json=rollback_payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"🔄 PatchCtl rollback triggered for PR {pr_id}")
                        
                        # Record rollback metric
                        for violation in violations:
                            GEMINI_ROLLBACK_TRIGGERED_TOTAL.labels(
                                pr_id=pr_id,
                                reason=violation.policy_name
                            ).inc()
                    else:
                        logger.error(f"❌ PatchCtl rollback failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"❌ PatchCtl rollback trigger error: {e}")
            
    async def _send_slack_alert(self, pr_id: str, violations: List[PolicyAssertion]):
        """Send Slack alert for policy violations"""
        if not self.slack_webhook:
            return
            
        try:
            violation_summary = ", ".join([v.policy_name for v in violations])
            
            slack_payload = {
                "text": f"🚨 Gemini Policy Violation - PR {pr_id}",
                "attachments": [
                    {
                        "color": "danger",
                        "fields": [
                            {
                                "title": "PR ID",
                                "value": pr_id,
                                "short": True
                            },
                            {
                                "title": "Violations",
                                "value": violation_summary,
                                "short": True
                            },
                            {
                                "title": "Action Taken",
                                "value": "Automatic rollback triggered",
                                "short": False
                            }
                        ],
                        "footer": "Gemini Streaming Auditor (QA-302)",
                        "ts": int(time.time())
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook,
                    json=slack_payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.info(f"📲 Slack alert sent for PR {pr_id}")
                    else:
                        logger.warning(f"⚠️ Slack alert failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"❌ Slack alert error: {e}")
            
    def _generate_signature(self, pr_id: str) -> str:
        """Generate signature for webhook comment authenticity"""
        message = f"{pr_id}:{datetime.utcnow().isoformat()}:{time.time_ns()}"
        signature = hmac.new(
            self.webhook_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        return signature
        
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        return {
            "active_prs": len(self.monitored_prs),
            "monitored_prs": list(self.monitored_prs.keys()),
            "policy_thresholds": self.policy_thresholds,
            "uptime": time.time() - start_time if 'start_time' in globals() else 0
        }

# Global auditor instance
auditor = GeminiStreamingAuditor()

# FastAPI application
app = FastAPI(
    title="Gemini Streaming Auditor",
    description="QA-302: Real-time PR policy enforcement",
    version="1.0.0"
)

start_time = time.time()

@app.on_event("startup")
async def startup_event():
    """Initialize auditor on startup"""
    await auditor.initialize()
    logger.info("🌟 Gemini Streaming Auditor started")

@app.post("/webhook/meta")
async def meta_webhook(
    payload: MetaWebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    QA-302: Primary webhook endpoint for PR meta events
    Processes policy assertions and triggers rollbacks on violations
    """
    logger.info(f"📥 Meta webhook received for PR {payload.pr_id}")
    
    # Validate webhook signature (in production)
    # signature_valid = await _validate_webhook_signature(request)
    # if not signature_valid:
    #     raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process webhook in background for faster response
    background_tasks.add_task(auditor.process_meta_webhook, payload)
    
    return {
        "status": "accepted",
        "pr_id": payload.pr_id,
        "timestamp": time.time(),
        "message": "Meta webhook processing started"
    }

@app.get("/webhook/meta/docs")
async def webhook_documentation():
    """API documentation for meta webhook endpoint"""
    return {
        "endpoint": "/webhook/meta",
        "method": "POST",
        "description": "Receives PR meta events for real-time policy enforcement",
        "payload_structure": {
            "pr_id": "String - PR identifier",
            "meta": {
                "unit_coverage": "Float - Test coverage percentage (0-100)",
                "latency_regression": "Float - Latency regression percentage (0-100)",
                "cost_delta": "Float - Cost increase in USD"
            },
            "timestamp": "Float - Unix timestamp (optional)",
            "source": "String - Event source (optional)"
        },
        "policy_thresholds": auditor.policy_thresholds,
        "response_actions": [
            "Post signed webhook comment on violations",
            "Trigger PatchCtl rollback on violations",
            "Send Slack alerts (if configured)",
            "Record Prometheus metrics"
        ]
    }

@app.get("/audit/status")
async def audit_status():
    """Get current auditor status and monitoring information"""
    status = await auditor.get_monitoring_status()
    return status

@app.get("/audit/pr/{pr_id}")
async def get_pr_audit_status(pr_id: str):
    """Get audit status for specific PR"""
    if pr_id not in auditor.monitored_prs:
        raise HTTPException(status_code=404, detail="PR not found in monitoring")
        
    pr_data = auditor.monitored_prs[pr_id]
    return {
        "pr_id": pr_id,
        "monitoring_started": pr_data["started_at"].isoformat(),
        "last_check": pr_data["last_check"].isoformat(),
        "violations": len(pr_data["violations"]),
        "status": "violated" if pr_data["violations"] else "clean"
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Expose Prometheus metrics"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        await auditor.redis_client.ping()
        return {"status": "healthy", "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unhealthy: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8091,
        reload=False,
        log_level="info"
    )