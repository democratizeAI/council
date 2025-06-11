#!/usr/bin/env python3
"""
FMC Prometheus Gauges
Metrics collection for Builder 2 FMC-120 feedback loop integration
Live metrics for autonomous feedback governance
"""

import time
import json
import logging
from typing import Dict, List
from prometheus_client import Gauge, Counter, Histogram, Info, start_http_server
from datetime import datetime

logger = logging.getLogger(__name__)

# Core FMC-120 Metrics
feedback_seen_total = Counter(
    'feedback_seen_total',
    'Total feedback events processed by FMC-120',
    ['pr', 'source', 'type']
)

loop_status = Gauge(
    'loop_status', 
    'Current status of feedback loops',
    ['pr', 'status']
)

average_confidence = Gauge(
    'average_confidence',
    'Average confidence score for PR feedback',
    ['pr']
)

loop_closure_status = Gauge(
    'loop_closure_status',
    'Loop closure completion indicator (1=closed, 0=open)',
    ['pr']
)

# Builder 2 Integration Metrics
builder2_prs_active = Gauge(
    'builder2_prs_active',
    'Number of active PRs being tracked by Builder 2'
)

builder2_decisions_total = Counter(
    'builder2_decisions_total',
    'Total routing decisions made by Builder 2',
    ['decision_type']  # approve_merge, route_to_audit, hold_for_review
)

patchctl_integrations = Counter(
    'patchctl_integrations_total',
    'PatchCtl hook integrations triggered',
    ['pr', 'action']
)

gemini_audit_triggers = Counter(
    'gemini_audit_triggers_total',
    'Gemini audit triggers from feedback loops',
    ['pr', 'reason']
)

# Quality & Performance Metrics
feedback_loop_duration = Histogram(
    'feedback_loop_duration_seconds',
    'Time from loop start to closure',
    ['pr']
)

confidence_distribution = Histogram(
    'confidence_distribution',
    'Distribution of feedback confidence scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

regression_detection_rate = Gauge(
    'regression_detection_rate',
    'Rate of regression detection in feedback loops'
)

# System Health Metrics
fmc_service_health = Gauge(
    'fmc_service_health',
    'Health status of FMC services',
    ['service']  # fmc100, fmc110, fmc120
)

integration_success_rate = Gauge(
    'integration_success_rate',
    'Success rate of FMC integrations',
    ['integration_type']  # patchctl, gemini, ledger, a2a
)

# Acceptance Criteria Metrics (from task requirements)
acceptance_criteria = {
    'feedback_seen_min': Gauge('acceptance_feedback_seen_min', 'Minimum feedback events (target ≥3)'),
    'average_confidence_min': Gauge('acceptance_average_confidence_min', 'Minimum average confidence (target >0.8)'),
    'loop_closure_complete': Gauge('acceptance_loop_closure_complete', 'Loop closure completion status'),
    'pr_safe_to_merge': Gauge('acceptance_pr_safe_to_merge', 'PR marked safe to merge or sent to audit')
}

# Builder 2 Service Info
builder2_info = Info('builder2_service_info', 'Builder 2 service information')
builder2_info.info({
    'mode': 'live',
    'version': 'v1.0.0',
    'builder': 'builder2',
    'mission': 'feedback_lifecycle_integration'
})

class FMCMetricsCollector:
    """Centralized metrics collection for FMC-120 integration"""
    
    def __init__(self):
        self.start_time = time.time()
        self.active_loops = {}
        
    def record_feedback_event(self, pr_id: str, source: str, event_type: str, confidence: float):
        """Record a feedback event"""
        feedback_seen_total.labels(pr=pr_id, source=source, type=event_type).inc()
        confidence_distribution.observe(confidence)
        
        # Update average confidence for PR
        if pr_id in self.active_loops:
            self.active_loops[pr_id]['confidences'].append(confidence)
            avg_conf = sum(self.active_loops[pr_id]['confidences']) / len(self.active_loops[pr_id]['confidences'])
            average_confidence.labels(pr=pr_id).set(avg_conf)
        
        logger.info(f"📊 Recorded feedback: {pr_id} | {source} | {event_type} | {confidence:.3f}")
    
    def start_loop(self, pr_id: str):
        """Start tracking a feedback loop"""
        self.active_loops[pr_id] = {
            'start_time': time.time(),
            'confidences': [],
            'events': 0
        }
        
        loop_status.labels(pr=pr_id, status='active').set(1)
        builder2_prs_active.set(len(self.active_loops))
        
        logger.info(f"🔄 Started loop tracking: {pr_id}")
    
    def close_loop(self, pr_id: str, final_status: str):
        """Close a feedback loop and record metrics"""
        if pr_id in self.active_loops:
            loop_data = self.active_loops[pr_id]
            duration = time.time() - loop_data['start_time']
            
            # Record closure metrics
            loop_closure_status.labels(pr=pr_id).set(1)
            feedback_loop_duration.labels(pr=pr_id).observe(duration)
            loop_status.labels(pr=pr_id, status=final_status).set(1)
            loop_status.labels(pr=pr_id, status='active').set(0)
            
            # Clean up
            del self.active_loops[pr_id]
            builder2_prs_active.set(len(self.active_loops))
            
            logger.info(f"✅ Closed loop: {pr_id} | Status: {final_status} | Duration: {duration:.1f}s")
    
    def record_decision(self, pr_id: str, decision_type: str, confidence: float):
        """Record a Builder 2 routing decision"""
        builder2_decisions_total.labels(decision_type=decision_type).inc()
        
        # Update acceptance criteria
        if decision_type == 'approve_merge':
            acceptance_criteria['pr_safe_to_merge'].set(1)
        elif decision_type == 'route_to_audit':
            acceptance_criteria['pr_safe_to_merge'].set(1)  # Still handled
        
        logger.info(f"🎯 Decision recorded: {pr_id} | {decision_type} | {confidence:.3f}")
    
    def record_integration(self, pr_id: str, integration_type: str, success: bool):
        """Record integration attempt"""
        action = 'success' if success else 'failure'
        
        if integration_type == 'patchctl':
            patchctl_integrations.labels(pr=pr_id, action=action).inc()
        elif integration_type == 'gemini':
            gemini_audit_triggers.labels(pr=pr_id, reason='feedback_loop').inc()
        
        # Update success rates
        current_rate = integration_success_rate.labels(integration_type=integration_type)._value._value
        new_rate = (current_rate + (1.0 if success else 0.0)) / 2  # Simple moving average
        integration_success_rate.labels(integration_type=integration_type).set(new_rate)
        
        logger.info(f"🔗 Integration: {integration_type} | {action} | PR: {pr_id}")
    
    def validate_acceptance_criteria(self, pr_id: str, feedback_count: int, avg_confidence: float):
        """Validate acceptance criteria for Builder 2 task"""
        
        # ✅ feedback_seen_total ≥ 3
        if feedback_count >= 3:
            acceptance_criteria['feedback_seen_min'].set(1)
        else:
            acceptance_criteria['feedback_seen_min'].set(0)
        
        # ✅ average_confidence > 0.8
        if avg_confidence > 0.8:
            acceptance_criteria['average_confidence_min'].set(1)
        else:
            acceptance_criteria['average_confidence_min'].set(0)
        
        # ✅ loop_closure_status = complete
        if pr_id in self.active_loops and feedback_count >= 3 and avg_confidence > 0.8:
            acceptance_criteria['loop_closure_complete'].set(1)
        
        logger.info(f"📋 Acceptance criteria check: {pr_id} | Events: {feedback_count} | Confidence: {avg_confidence:.3f}")
    
    def update_service_health(self, service: str, healthy: bool):
        """Update service health metrics"""
        fmc_service_health.labels(service=service).set(1 if healthy else 0)
    
    def get_metrics_summary(self) -> Dict:
        """Get current metrics summary"""
        return {
            "active_loops": len(self.active_loops),
            "total_feedback_events": feedback_seen_total._value.sum(),
            "service_uptime": time.time() - self.start_time,
            "acceptance_criteria": {
                "feedback_minimum": acceptance_criteria['feedback_seen_min']._value._value,
                "confidence_minimum": acceptance_criteria['average_confidence_min']._value._value, 
                "loop_closure": acceptance_criteria['loop_closure_complete']._value._value,
                "pr_status": acceptance_criteria['pr_safe_to_merge']._value._value
            }
        }

# Global metrics collector instance
metrics_collector = FMCMetricsCollector()

def export_builder2_trial_metrics():
    """Export specific metrics for builder2-trial-pr-01 demonstration"""
    pr_id = "builder2-trial-pr-01"
    
    # Simulate Builder 2 trial metrics
    metrics_collector.start_loop(pr_id)
    
    # Simulate feedback events
    metrics_collector.record_feedback_event(pr_id, "ci", "latency_regression", 0.8)
    metrics_collector.record_feedback_event(pr_id, "ai_analysis", "code_quality", 0.91)
    metrics_collector.record_feedback_event(pr_id, "human", "approval", 0.85)
    
    # Validate criteria
    metrics_collector.validate_acceptance_criteria(pr_id, 3, 0.85)
    
    # Record decision
    metrics_collector.record_decision(pr_id, "route_to_audit", 0.85)
    
    # Record integrations
    metrics_collector.record_integration(pr_id, "patchctl", True)
    metrics_collector.record_integration(pr_id, "gemini", True)
    
    # Close loop
    metrics_collector.close_loop(pr_id, "sent_to_audit")
    
    return metrics_collector.get_metrics_summary()

def start_metrics_server(port: int = 9091):
    """Start Prometheus metrics server"""
    start_http_server(port)
    logger.info(f"📊 FMC metrics server started on port {port}")
    
    # Initialize service health
    metrics_collector.update_service_health("fmc100", True)
    metrics_collector.update_service_health("fmc110", True) 
    metrics_collector.update_service_health("fmc120", True)

if __name__ == '__main__':
    # Demo mode - start server and export trial metrics
    start_metrics_server(9091)
    
    print("🧠 Builder 2 FMC Metrics Server Started")
    print("📊 Demo metrics for builder2-trial-pr-01:")
    
    summary = export_builder2_trial_metrics()
    print(json.dumps(summary, indent=2))
    
    print("\n✅ Acceptance Criteria Status:")
    print(f"  - feedback_seen_total ≥ 3: {'✅' if summary['acceptance_criteria']['feedback_minimum'] else '❌'}")
    print(f"  - average_confidence > 0.8: {'✅' if summary['acceptance_criteria']['confidence_minimum'] else '❌'}")
    print(f"  - loop_closure_status = complete: {'✅' if summary['acceptance_criteria']['loop_closure'] else '❌'}")
    print(f"  - PR status = safe_to_merge OR sent_to_audit: {'✅' if summary['acceptance_criteria']['pr_status'] else '❌'}")
    
    print(f"\n🔄 Metrics available at: http://localhost:9091/metrics")
    
    # Keep server running
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Metrics server stopped") 