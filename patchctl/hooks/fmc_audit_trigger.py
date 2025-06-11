#!/usr/bin/env python3
"""
PatchCtl FMC Audit Trigger Hook
Integrates with FMC-120 feedback loops for autonomous routing decisions
Builder 2 Integration Component
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PatchDecision:
    """PatchCtl routing decision"""
    action: str  # approve_merge, route_to_audit, hold_for_review
    pr_id: str
    reason: str
    confidence: float
    auto_merge: bool
    audit_required: bool

class FMCAuditTrigger:
    """PatchCtl hook for FMC-120 feedback loop integration"""
    
    def __init__(self):
        self.gemini_audit_url = "http://localhost:8091"
        self.fmc120_url = "http://localhost:8088"
        self.ledger_url = "http://localhost:8000"
        
        # Routing thresholds
        self.auto_merge_threshold = 0.85
        self.audit_trigger_threshold = 0.80
        self.hold_threshold = 0.60
        
    def process_feedback_completion(self, pr_id: str, feedback_data: Dict) -> PatchDecision:
        """Process completed feedback loop and make routing decision"""
        try:
            # Extract feedback metrics
            total_feedback = feedback_data.get('total_feedback', 0)
            average_confidence = feedback_data.get('average_confidence', 0.0)
            loop_closed = feedback_data.get('loop_closed', False)
            events = feedback_data.get('events', [])
            
            # Analyze feedback for decision factors
            decision_factors = self._analyze_feedback_factors(events)
            
            # Make routing decision
            decision = self._make_routing_decision(
                pr_id, 
                total_feedback, 
                average_confidence, 
                decision_factors
            )
            
            # Execute decision
            self._execute_decision(decision, feedback_data)
            
            logger.info(f"🎯 PatchCtl decision for PR {pr_id}: {decision.action} (confidence: {decision.confidence:.3f})")
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ PatchCtl decision error for PR {pr_id}: {e}")
            # Default to audit for safety
            return PatchDecision(
                action="route_to_audit",
                pr_id=pr_id,
                reason=f"Error in decision process: {str(e)}",
                confidence=0.0,
                auto_merge=False,
                audit_required=True
            )
    
    def _analyze_feedback_factors(self, events: List[Dict]) -> Dict:
        """Analyze feedback events for decision factors"""
        factors = {
            'regression_detected': False,
            'security_concerns': False,
            'performance_impact': False,
            'test_failures': False,
            'human_approval': False,
            'ai_confidence': 0.0,
            'ci_status': 'unknown'
        }
        
        for event in events:
            event_type = event.get('type', '')
            source = event.get('source', '')
            confidence = event.get('confidence', 0.0)
            content = event.get('content', '').lower()
            
            # Check for regressions
            if 'regression' in event_type or 'latency' in event_type:
                factors['regression_detected'] = True
            
            # Security concerns
            if 'security' in event_type or 'vulnerability' in content:
                factors['security_concerns'] = True
            
            # Performance impact
            if 'performance' in event_type or 'slow' in content:
                factors['performance_impact'] = True
            
            # Test failures
            if source == 'ci' and ('failed' in content or 'error' in content):
                factors['test_failures'] = True
            
            # Human approval
            if source == 'human' and ('lgtm' in content or 'approve' in content):
                factors['human_approval'] = True
            
            # AI confidence tracking
            if source in ['ai_analysis', 'gemini_audit']:
                factors['ai_confidence'] = max(factors['ai_confidence'], confidence)
            
            # CI status
            if source == 'ci':
                if 'passed' in content:
                    factors['ci_status'] = 'passed'
                elif 'failed' in content:
                    factors['ci_status'] = 'failed'
        
        return factors
    
    def _make_routing_decision(self, pr_id: str, total_feedback: int, 
                             average_confidence: float, factors: Dict) -> PatchDecision:
        """Make autonomous routing decision based on feedback analysis"""
        
        # Safety checks - route to audit if any concerns
        if (factors['security_concerns'] or 
            factors['test_failures'] or 
            factors['ci_status'] == 'failed'):
            
            return PatchDecision(
                action="route_to_audit",
                pr_id=pr_id,
                reason="Safety concerns detected - security/test failures",
                confidence=average_confidence,
                auto_merge=False,
                audit_required=True
            )
        
        # Regression detection - require audit
        if factors['regression_detected'] or factors['performance_impact']:
            return PatchDecision(
                action="route_to_audit", 
                pr_id=pr_id,
                reason="Performance regression detected",
                confidence=average_confidence,
                auto_merge=False,
                audit_required=True
            )
        
        # High confidence with good indicators - auto merge
        if (average_confidence >= self.auto_merge_threshold and
            total_feedback >= 3 and
            factors['ci_status'] == 'passed' and
            factors['ai_confidence'] >= 0.80):
            
            return PatchDecision(
                action="approve_merge",
                pr_id=pr_id,
                reason="High confidence, all checks passed",
                confidence=average_confidence,
                auto_merge=True,
                audit_required=False
            )
        
        # Medium confidence - route to audit for review
        if average_confidence >= self.audit_trigger_threshold:
            return PatchDecision(
                action="route_to_audit",
                pr_id=pr_id,
                reason="Medium confidence - requires human review",
                confidence=average_confidence,
                auto_merge=False,
                audit_required=True
            )
        
        # Low confidence - hold for manual review
        return PatchDecision(
            action="hold_for_review",
            pr_id=pr_id,
            reason="Low confidence - manual intervention required",
            confidence=average_confidence,
            auto_merge=False,
            audit_required=True
        )
    
    def _execute_decision(self, decision: PatchDecision, feedback_data: Dict):
        """Execute the routing decision"""
        try:
            if decision.action == "approve_merge":
                self._trigger_auto_merge(decision, feedback_data)
                
            elif decision.action == "route_to_audit":
                self._trigger_gemini_audit(decision, feedback_data)
                
            elif decision.action == "hold_for_review":
                self._trigger_manual_review(decision, feedback_data)
            
            # Update PatchCtl status
            self._update_patchctl_status(decision)
            
        except Exception as e:
            logger.error(f"❌ Decision execution error: {e}")
    
    def _trigger_auto_merge(self, decision: PatchDecision, feedback_data: Dict):
        """Trigger autonomous merge approval"""
        try:
            merge_payload = {
                "pr_id": decision.pr_id,
                "action": "auto_merge_approved",
                "reason": decision.reason,
                "confidence": decision.confidence,
                "feedback_loop_complete": True,
                "timestamp": datetime.utcnow().isoformat(),
                "builder": "builder2"
            }
            
            # Send to merge queue (simulated)
            logger.info(f"🚀 Auto-merge approved for PR {decision.pr_id}")
            
            # Notify FMC-120 of approval
            requests.patch(
                f"{self.fmc120_url}/update-status/{decision.pr_id}",
                json={"status": "approved_for_merge", "auto_merge": True},
                timeout=5
            )
            
        except Exception as e:
            logger.error(f"❌ Auto-merge trigger error: {e}")
    
    def _trigger_gemini_audit(self, decision: PatchDecision, feedback_data: Dict):
        """Trigger Gemini audit review"""
        try:
            audit_payload = {
                "pr_id": decision.pr_id,
                "audit_type": "feedback_loop_review",
                "reason": decision.reason,
                "priority": "high" if "security" in decision.reason else "medium",
                "feedback_summary": {
                    "total_events": feedback_data.get('total_feedback', 0),
                    "average_confidence": feedback_data.get('average_confidence', 0.0),
                    "events": feedback_data.get('events', [])
                },
                "requested_by": "patchctl_fmc_hook",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to Gemini Audit (simulated)
            logger.info(f"🌟 Gemini audit triggered for PR {decision.pr_id}")
            
            # Notify FMC-120 of audit routing
            requests.patch(
                f"{self.fmc120_url}/update-status/{decision.pr_id}",
                json={"status": "sent_to_audit", "audit_triggered": True},
                timeout=5
            )
            
        except Exception as e:
            logger.error(f"❌ Gemini audit trigger error: {e}")
    
    def _trigger_manual_review(self, decision: PatchDecision, feedback_data: Dict):
        """Trigger manual review process"""
        try:
            review_payload = {
                "pr_id": decision.pr_id,
                "review_type": "manual_intervention_required",
                "reason": decision.reason,
                "confidence": decision.confidence,
                "feedback_data": feedback_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"👤 Manual review required for PR {decision.pr_id}")
            
            # Notify FMC-120 of hold status
            requests.patch(
                f"{self.fmc120_url}/update-status/{decision.pr_id}",
                json={"status": "held_for_review", "manual_review": True},
                timeout=5
            )
            
        except Exception as e:
            logger.error(f"❌ Manual review trigger error: {e}")
    
    def _update_patchctl_status(self, decision: PatchDecision):
        """Update PatchCtl internal status"""
        try:
            status_update = {
                "pr_id": decision.pr_id,
                "patchctl_decision": decision.action,
                "confidence": decision.confidence,
                "auto_merge_eligible": decision.auto_merge,
                "audit_required": decision.audit_required,
                "decision_timestamp": datetime.utcnow().isoformat(),
                "fmc_integration": True
            }
            
            # Store in PatchCtl state (simulated)
            logger.info(f"💡 PatchCtl status updated for PR {decision.pr_id}")
            
        except Exception as e:
            logger.error(f"❌ PatchCtl status update error: {e}")

# Global hook instance
fmc_audit_trigger = FMCAuditTrigger()

def handle_feedback_completion(pr_id: str, feedback_data: Dict) -> Dict:
    """Main hook entry point for FMC-120 integration"""
    try:
        decision = fmc_audit_trigger.process_feedback_completion(pr_id, feedback_data)
        
        return {
            "success": True,
            "decision": {
                "action": decision.action,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "auto_merge": decision.auto_merge,
                "audit_required": decision.audit_required
            },
            "pr_id": pr_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Feedback completion hook error: {e}")
        return {
            "success": False,
            "error": str(e),
            "pr_id": pr_id,
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == '__main__':
    # Test the hook with sample data
    test_feedback = {
        "total_feedback": 3,
        "average_confidence": 0.87,
        "loop_closed": True,
        "events": [
            {"source": "ci", "type": "latency_regression", "confidence": 0.8, "content": "latency increased by 1.4%"},
            {"source": "ai_analysis", "type": "code_quality", "confidence": 0.9, "content": "good code quality"},
            {"source": "human", "type": "approval", "confidence": 0.9, "content": "lgtm, ship it"}
        ]
    }
    
    result = handle_feedback_completion("builder2-trial-pr-01", test_feedback)
    print(json.dumps(result, indent=2)) 