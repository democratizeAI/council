#!/usr/bin/env python3
"""
FMC-120 Live Feedback Lifecycle Service
Mission: Close feedback loops end-to-end with PatchCtl, Gemini-Audit integration
Builder 2 Implementation - LIVE MODE
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import redis
import requests
import os

# Prometheus metrics for live tracking
feedback_seen_total = Counter('feedback_seen_total', 'Total feedback events', ['pr', 'source', 'type'])
loop_status = Gauge('loop_status', 'Loop completion status', ['pr', 'status'])
average_confidence = Gauge('average_confidence', 'Average feedback confidence', ['pr'])
loop_closure_status = Gauge('loop_closure_status', 'Loop closure completion', ['pr'])

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FeedbackEvent:
    """Live feedback event structure"""
    pr_id: str
    source: str  # ci, gemini_audit, human, ai_analysis
    confidence: float
    actionable: bool
    type: str  # latency_regression, code_quality, security, performance
    content: str
    timestamp: datetime
    event_id: str

@dataclass
class PRLoopState:
    """PR feedback loop state tracking"""
    pr_id: str
    events: List[FeedbackEvent]
    total_feedback: int
    average_confidence: float
    loop_closed: bool
    status: str  # active, complete, sent_to_audit, safe_to_merge
    created_at: datetime
    closed_at: Optional[datetime]

class LiveFeedbackLoop:
    """Live feedback loop manager with PatchCtl integration"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True, db=1)
        self.active_loops: Dict[str, PRLoopState] = {}
        
        # Integration endpoints
        self.patchctl_url = os.getenv('PATCHCTL_URL', 'http://localhost:8090')
        self.gemini_audit_url = os.getenv('GEMINI_AUDIT_URL', 'http://localhost:8091')
        self.ledger_url = os.getenv('LEDGER_URL', 'http://localhost:8000/ledger')
        
        # Thresholds for live operation
        self.min_feedback_events = 3
        self.confidence_threshold = 0.8
        self.quality_threshold = 0.84
        
        logger.info("🧠 Builder 2 FMC-120 Live Service Initialized")
    
    def start_pr_loop(self, pr_id: str) -> PRLoopState:
        """Initialize feedback loop for a PR"""
        loop_state = PRLoopState(
            pr_id=pr_id,
            events=[],
            total_feedback=0,
            average_confidence=0.0,
            loop_closed=False,
            status="active",
            created_at=datetime.utcnow(),
            closed_at=None
        )
        
        self.active_loops[pr_id] = loop_state
        self._persist_loop_state(loop_state)
        
        # Initialize metrics
        loop_status.labels(pr=pr_id, status="active").set(1)
        
        logger.info(f"🔄 Started feedback loop for PR {pr_id}")
        return loop_state
    
    def process_feedback(self, feedback_data: Dict) -> Dict:
        """Process incoming feedback event - LIVE MODE"""
        try:
            pr_id = feedback_data['pr_id']
            
            # Get or create loop
            if pr_id not in self.active_loops:
                self.start_pr_loop(pr_id)
            
            loop_state = self.active_loops[pr_id]
            
            # Create feedback event
            event = FeedbackEvent(
                pr_id=pr_id,
                source=feedback_data['source'],
                confidence=feedback_data['confidence'],
                actionable=feedback_data.get('actionable', True),
                type=feedback_data['type'],
                content=feedback_data.get('content', ''),
                timestamp=datetime.utcnow(),
                event_id=f"fb-{pr_id}-{int(time.time())}"
            )
            
            # Add to loop state
            loop_state.events.append(event)
            loop_state.total_feedback += 1
            
            # Update average confidence
            loop_state.average_confidence = sum(e.confidence for e in loop_state.events) / len(loop_state.events)
            
            # Update metrics
            feedback_seen_total.labels(pr=pr_id, source=event.source, type=event.type).inc()
            average_confidence.labels(pr=pr_id).set(loop_state.average_confidence)
            
            # Check for loop closure
            result = self._check_loop_closure(loop_state)
            
            # Persist state
            self._persist_loop_state(loop_state)
            
            logger.info(f"✅ Processed feedback: {event.event_id} | PR: {pr_id} | Total: {loop_state.total_feedback}")
            
            return {
                "feedback_processed": True,
                "event_id": event.event_id,
                "pr_id": pr_id,
                "total_feedback": loop_state.total_feedback,
                "average_confidence": loop_state.average_confidence,
                "loop_closed": loop_state.loop_closed,
                "status": loop_state.status,
                "actions_triggered": result.get('actions_triggered', [])
            }
            
        except Exception as e:
            logger.error(f"❌ Feedback processing failed: {e}")
            raise
    
    def _check_loop_closure(self, loop_state: PRLoopState) -> Dict:
        """Check if loop should close and trigger actions"""
        actions_triggered = []
        
        # Check closure criteria
        sufficient_feedback = loop_state.total_feedback >= self.min_feedback_events
        good_confidence = loop_state.average_confidence >= self.confidence_threshold
        
        if sufficient_feedback and good_confidence and not loop_state.loop_closed:
            # Close the loop
            loop_state.loop_closed = True
            loop_state.closed_at = datetime.utcnow()
            
            # Update metrics
            loop_closure_status.labels(pr=loop_state.pr_id).set(1)
            
            # Determine final action
            regression_detected = any(
                'latency' in e.type or 'regression' in e.type 
                for e in loop_state.events
            )
            
            low_quality = any(
                e.confidence < self.quality_threshold 
                for e in loop_state.events
            )
            
            if regression_detected or low_quality:
                # Route to Gemini Audit
                loop_state.status = "sent_to_audit"
                actions_triggered.append(self._trigger_gemini_audit(loop_state))
                loop_status.labels(pr=loop_state.pr_id, status="sent_to_audit").set(1)
                
            else:
                # Safe to merge
                loop_state.status = "safe_to_merge"
                actions_triggered.append(self._trigger_patchctl_approval(loop_state))
                loop_status.labels(pr=loop_state.pr_id, status="safe_to_merge").set(1)
            
            # Update ledger
            actions_triggered.append(self._update_ledger(loop_state))
            
            # Publish A2A event
            actions_triggered.append(self._publish_loop_close_event(loop_state))
            
            logger.info(f"🎯 Loop closed for PR {loop_state.pr_id} - Status: {loop_state.status}")
        
        return {"actions_triggered": actions_triggered}
    
    def _trigger_gemini_audit(self, loop_state: PRLoopState) -> str:
        """Trigger Gemini audit for PR"""
        try:
            audit_payload = {
                "pr_id": loop_state.pr_id,
                "reason": "feedback_loop_quality_concern",
                "feedback_events": len(loop_state.events),
                "average_confidence": loop_state.average_confidence,
                "concerns": [e.type for e in loop_state.events if e.confidence < self.quality_threshold]
            }
            
            # Send to Gemini Audit
            response = requests.post(
                f"{self.gemini_audit_url}/audit-request",
                json=audit_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"🌟 Gemini audit triggered for PR {loop_state.pr_id}")
                return f"gemini_audit_triggered:{loop_state.pr_id}"
            else:
                logger.warning(f"⚠️ Gemini audit trigger failed: {response.status_code}")
                return f"gemini_audit_failed:{response.status_code}"
                
        except Exception as e:
            logger.error(f"❌ Gemini audit trigger error: {e}")
            return f"gemini_audit_error:{str(e)}"
    
    def _trigger_patchctl_approval(self, loop_state: PRLoopState) -> str:
        """Trigger PatchCtl approval for PR"""
        try:
            patch_payload = {
                "pr_id": loop_state.pr_id,
                "action": "approve_merge",
                "feedback_loop_complete": True,
                "feedback_events": loop_state.total_feedback,
                "quality_score": loop_state.average_confidence,
                "autonomous": True
            }
            
            # Send to PatchCtl
            response = requests.post(
                f"{self.patchctl_url}/patch-approve",
                json=patch_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"💡 PatchCtl approval triggered for PR {loop_state.pr_id}")
                return f"patchctl_approved:{loop_state.pr_id}"
            else:
                logger.warning(f"⚠️ PatchCtl approval failed: {response.status_code}")
                return f"patchctl_failed:{response.status_code}"
                
        except Exception as e:
            logger.error(f"❌ PatchCtl approval error: {e}")
            return f"patchctl_error:{str(e)}"
    
    def _update_ledger(self, loop_state: PRLoopState) -> str:
        """Update Trinity Ledger with feedback status"""
        try:
            ledger_update = {
                "pr_id": loop_state.pr_id,
                "fmc_loop_closure": True,
                "feedback_seen_total": loop_state.total_feedback,
                "average_confidence": loop_state.average_confidence,
                "status": loop_state.status,
                "closed_at": loop_state.closed_at.isoformat() if loop_state.closed_at else None
            }
            
            # Update ledger
            response = requests.patch(
                f"{self.ledger_url}/update-feedback-status",
                json=ledger_update,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"📋 Ledger updated for PR {loop_state.pr_id}")
                return f"ledger_updated:{loop_state.pr_id}"
            else:
                logger.warning(f"⚠️ Ledger update failed: {response.status_code}")
                return f"ledger_failed:{response.status_code}"
                
        except Exception as e:
            logger.error(f"❌ Ledger update error: {e}")
            return f"ledger_error:{str(e)}"
    
    def _publish_loop_close_event(self, loop_state: PRLoopState) -> str:
        """Publish LOOP_CLOSE A2A event"""
        try:
            event_payload = {
                "event_type": "LOOP_CLOSE",
                "pr_id": loop_state.pr_id,
                "status": loop_state.status,
                "feedback_count": loop_state.total_feedback,
                "quality_score": loop_state.average_confidence,
                "timestamp": datetime.utcnow().isoformat(),
                "builder": "builder2"
            }
            
            # Publish to event bus (Redis pub/sub)
            self.redis_client.publish("a2a_events", json.dumps(event_payload))
            
            logger.info(f"📡 A2A LOOP_CLOSE event published for PR {loop_state.pr_id}")
            return f"a2a_published:{loop_state.pr_id}"
            
        except Exception as e:
            logger.error(f"❌ A2A event publish error: {e}")
            return f"a2a_error:{str(e)}"
    
    def _persist_loop_state(self, loop_state: PRLoopState):
        """Persist loop state to Redis"""
        try:
            state_data = {
                "pr_id": loop_state.pr_id,
                "total_feedback": loop_state.total_feedback,
                "average_confidence": loop_state.average_confidence,
                "loop_closed": loop_state.loop_closed,
                "status": loop_state.status,
                "events": [asdict(e) for e in loop_state.events],
                "created_at": loop_state.created_at.isoformat(),
                "closed_at": loop_state.closed_at.isoformat() if loop_state.closed_at else None
            }
            
            self.redis_client.setex(
                f"fmc120:loop:{loop_state.pr_id}", 
                86400,  # 24 hour TTL
                json.dumps(state_data, default=str)
            )
            
        except Exception as e:
            logger.error(f"❌ State persistence error: {e}")

# Initialize live feedback loop manager
feedback_loop = LiveFeedbackLoop()

@app.route('/start-loop', methods=['POST'])
def start_loop():
    """Start feedback loop for PR"""
    try:
        data = request.get_json()
        pr_id = data.get('pr_id')
        
        if not pr_id:
            return jsonify({"error": "Missing pr_id"}), 400
        
        loop_state = feedback_loop.start_pr_loop(pr_id)
        
        return jsonify({
            "loop_started": True,
            "pr_id": pr_id,
            "status": loop_state.status,
            "created_at": loop_state.created_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Start loop failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/feedback', methods=['POST'])
def process_feedback():
    """Process feedback event - LIVE ENDPOINT"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['pr_id', 'source', 'confidence', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        result = feedback_loop.process_feedback(data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Process feedback failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/loop-status/<pr_id>', methods=['GET'])
def get_loop_status(pr_id: str):
    """Get current loop status"""
    try:
        if pr_id in feedback_loop.active_loops:
            loop_state = feedback_loop.active_loops[pr_id]
            
            return jsonify({
                "pr_id": pr_id,
                "total_feedback": loop_state.total_feedback,
                "average_confidence": loop_state.average_confidence,
                "loop_closed": loop_state.loop_closed,
                "status": loop_state.status,
                "created_at": loop_state.created_at.isoformat(),
                "closed_at": loop_state.closed_at.isoformat() if loop_state.closed_at else None,
                "events": [
                    {
                        "source": e.source,
                        "type": e.type,
                        "confidence": e.confidence,
                        "timestamp": e.timestamp.isoformat()
                    }
                    for e in loop_state.events
                ]
            })
        else:
            return jsonify({"error": "Loop not found"}), 404
            
    except Exception as e:
        logger.error(f"❌ Get loop status failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "service": "fmc120-live",
        "mode": "LIVE",
        "builder": "builder2",
        "active_loops": len(feedback_loop.active_loops),
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    logger.info("🧠 Builder 2 FMC-120 Live Service Starting...")
    logger.info("🔄 Feedback lifecycle integration ACTIVE")
    app.run(host='0.0.0.0', port=8088, debug=False) 