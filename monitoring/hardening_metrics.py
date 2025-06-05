#!/usr/bin/env python3
"""
📊 Hardening Monitoring Metrics
===============================

Prometheus metrics to monitor the hardening measures:
1. Docker restart tracking
2. FAISS memory QPS monitoring  
3. GPU driver health
4. Intent classification accuracy

Used by Grafana dashboards and alerting.
"""

import time
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, Summary, Info, CollectorRegistry, REGISTRY
import threading

logger = logging.getLogger(__name__)

# 🚀 HARDENING: Check if metrics already exist to prevent duplication
def get_or_create_counter(name, description, labelnames=None):
    """Get existing counter or create new one"""
    try:
        # Check if metric already exists
        for collector in REGISTRY._collector_to_names.keys():
            if hasattr(collector, '_name') and collector._name == name:
                return collector
        # Create new metric
        return Counter(name, description, labelnames or [])
    except Exception:
        return Counter(name, description, labelnames or [])

def get_or_create_histogram(name, description, labelnames=None, buckets=None):
    """Get existing histogram or create new one"""
    try:
        for collector in REGISTRY._collector_to_names.keys():
            if hasattr(collector, '_name') and collector._name == name:
                return collector
        return Histogram(name, description, labelnames or [], buckets=buckets)
    except Exception:
        return Histogram(name, description, labelnames or [], buckets=buckets)

def get_or_create_gauge(name, description, labelnames=None):
    """Get existing gauge or create new one"""
    try:
        for collector in REGISTRY._collector_to_names.keys():
            if hasattr(collector, '_name') and collector._name == name:
                return collector
        return Gauge(name, description, labelnames or [])
    except Exception:
        return Gauge(name, description, labelnames or [])

# 🚀 HARDENING METRICS - Protected against duplication

# Docker restart tracking
swarm_docker_restart_total = get_or_create_counter(
    "swarm_docker_restart_total",
    "Total number of Docker container restarts",
    ["container_name", "restart_reason"]
)

# FAISS memory monitoring
swarm_memory_qps = get_or_create_counter(
    "swarm_memory_qps_total", 
    "Total FAISS memory query operations"
)

swarm_memory_query_latency = get_or_create_histogram(
    "swarm_memory_query_latency_seconds",
    "FAISS memory query latency",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

swarm_memory_size = get_or_create_gauge(
    "swarm_memory_size_entries",
    "Number of entries in FAISS memory"
)

swarm_memory_singleton_violations = get_or_create_counter(
    "swarm_memory_singleton_violations_total",
    "Number of times FAISS was re-instantiated instead of using singleton"
)

# GPU health monitoring  
swarm_gpu_health = get_or_create_gauge(
    "swarm_gpu_health_status",
    "GPU health status (1=healthy, 0=unhealthy)",
    ["gpu_id", "gpu_name"]
)

swarm_gpu_memory_utilization = get_or_create_gauge(
    "swarm_gpu_memory_utilization_percent", 
    "GPU memory utilization percentage",
    ["gpu_id"]
)

swarm_gpu_falloff_events = get_or_create_counter(
    "swarm_gpu_falloff_events_total",
    "Number of times GPU fell off the bus (driver reset)"
)

# Intent classification monitoring
swarm_intent_classification_latency = Histogram(
    "swarm_intent_classification_latency_seconds",
    "Intent classification latency",
    ["classifier_type"],  # regex, miniLM
    buckets=[0.001, 0.003, 0.005, 0.01, 0.025, 0.05, 0.1]
)

swarm_intent_accuracy = Gauge(
    "swarm_intent_accuracy_percent",
    "Intent classification accuracy based on user feedback",
    ["intent_type"]
)

swarm_fallback_penalty_applied = Counter(
    "swarm_fallback_penalty_applied_total",
    "Number of times fallback penalty was applied",
    ["intent_type"]
)

# Routing improvements
swarm_wrong_head_selections = Counter(
    "swarm_wrong_head_selections_total", 
    "Number of times wrong specialist head was chosen"
)

swarm_confidence_delta = Histogram(
    "swarm_confidence_delta",
    "Confidence score deltas between specialists",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
)

# 🎯 LENGTH PENALTY METRICS - Track math head rebalancing
swarm_length_penalty_applied = get_or_create_counter(
    "swarm_length_penalty_applied_total",
    "Number of times length penalty was applied",
    ["specialist", "penalty_tier"]  # penalty_tier: severe, moderate, mild, none
)

swarm_math_head_win_ratio = get_or_create_gauge(
    "swarm_math_head_win_ratio",
    "Ratio of votes won by math head (should be ~0.2-0.3 after fix)"
)

swarm_original_vs_penalized_confidence = get_or_create_histogram(
    "swarm_original_vs_penalized_confidence_delta",
    "Delta between original and penalized confidence scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

swarm_specialist_win_counts = get_or_create_counter(
    "swarm_specialist_win_counts_total",
    "Win counts by specialist (track rebalancing)",
    ["specialist"]
)

# Performance metrics
swarm_fast_local_hits = Counter(
    "swarm_fast_local_hits_total",
    "Number of queries handled by fast local path"
)

swarm_cloud_escalations = Counter(
    "swarm_cloud_escalations_total",
    "Number of queries escalated to cloud",
    ["reason"]  # low_confidence, complexity, safety
)

# System info
swarm_system_info = Info(
    "swarm_system_info",
    "System information for hardening monitoring"
)

class HardeningMonitor:
    """Monitor for hardening measures"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_memory_check = 0
        self.memory_check_interval = 30  # Check every 30 seconds
        
    def track_docker_restart(self, container_name: str, reason: str = "unknown"):
        """Track Docker container restart"""
        swarm_docker_restart_total.labels(
            container_name=container_name,
            restart_reason=reason
        ).inc()
        logger.info(f"🔄 Docker restart tracked: {container_name} ({reason})")
    
    def track_memory_query(self, query_time: float, result_count: int = 0):
        """Track FAISS memory query"""
        swarm_memory_qps.inc()
        swarm_memory_query_latency.observe(query_time)
        
        # Update memory size periodically
        current_time = time.time()
        if current_time - self.last_memory_check > self.memory_check_interval:
            self._update_memory_size()
            self.last_memory_check = current_time
    
    def _update_memory_size(self):
        """Update FAISS memory size metric"""
        try:
            from bootstrap import MEMORY
            memory_size = len(getattr(MEMORY, 'data', []))
            swarm_memory_size.set(memory_size)
        except Exception as e:
            logger.warning(f"Failed to update memory size metric: {e}")
    
    def track_singleton_violation(self):
        """Track FAISS singleton violation"""
        swarm_memory_singleton_violations.inc()
        logger.warning("🚨 FAISS singleton violation detected!")
    
    def track_gpu_health(self, gpu_id: int, is_healthy: bool, gpu_name: str = "unknown", memory_util: float = 0.0):
        """Track GPU health status"""
        swarm_gpu_health.labels(gpu_id=str(gpu_id), gpu_name=gpu_name).set(1 if is_healthy else 0)
        swarm_gpu_memory_utilization.labels(gpu_id=str(gpu_id)).set(memory_util)
    
    def track_gpu_falloff(self):
        """Track GPU driver falloff event"""
        swarm_gpu_falloff_events.inc()
        logger.error("🚨 GPU fell off the bus - driver reset event!")
    
    def track_intent_classification(self, classifier_type: str, latency: float, intent: str, confidence: float):
        """Track intent classification performance"""
        swarm_intent_classification_latency.labels(classifier_type=classifier_type).observe(latency)
        
        # Update accuracy if we have feedback
        swarm_intent_accuracy.labels(intent_type=intent).set(confidence * 100)
    
    def track_fallback_penalty(self, intent_type: str):
        """Track fallback penalty application"""
        swarm_fallback_penalty_applied.labels(intent_type=intent_type).inc()
    
    def track_wrong_head_selection(self):
        """Track wrong specialist head selection"""
        swarm_wrong_head_selections.inc()
        logger.warning("🎯 Wrong specialist head was chosen")
    
    def track_confidence_delta(self, delta: float):
        """Track confidence score deltas"""
        swarm_confidence_delta.observe(delta)
    
    def track_length_penalty(self, specialist: str, original_confidence: float, penalized_confidence: float):
        """Track length penalty application"""
        delta = original_confidence - penalized_confidence
        penalty_ratio = delta / original_confidence if original_confidence > 0 else 0
        
        # Categorize penalty severity
        if penalty_ratio >= 0.5:
            penalty_tier = "severe"
        elif penalty_ratio >= 0.3:
            penalty_tier = "moderate"
        elif penalty_ratio >= 0.1:
            penalty_tier = "mild"
        else:
            penalty_tier = "none"
        
        swarm_length_penalty_applied.labels(
            specialist=specialist,
            penalty_tier=penalty_tier
        ).inc()
        
        swarm_original_vs_penalized_confidence.observe(delta)
        
        logger.debug(f"📏 Length penalty tracked: {specialist} {penalty_tier} ({delta:.3f} delta)")
    
    def track_specialist_win(self, specialist: str):
        """Track specialist win for rebalancing monitoring"""
        swarm_specialist_win_counts.labels(specialist=specialist).inc()
        
        # Update math head win ratio if it's math specialist
        if "math" in specialist.lower():
            # This would need to be calculated over a rolling window
            # For now, just log the event
            logger.debug(f"🧮 Math head won: {specialist}")
    
    def track_fast_local_hit(self):
        """Track fast local path usage"""
        swarm_fast_local_hits.inc()
    
    def track_cloud_escalation(self, reason: str):
        """Track cloud escalation"""
        swarm_cloud_escalations.labels(reason=reason).inc()
    
    def update_system_info(self):
        """Update system information metrics"""
        try:
            import torch
            import sys
            import platform
            
            info_dict = {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": platform.platform(),
                "cuda_available": str(torch.cuda.is_available()),
                "cuda_version": torch.version.cuda or "not_available",
                "pytorch_version": torch.__version__,
                "uptime_seconds": str(int(time.time() - self.start_time))
            }
            
            if torch.cuda.is_available():
                info_dict["gpu_count"] = str(torch.cuda.device_count())
                info_dict["gpu_name"] = torch.cuda.get_device_name(0)
            
            swarm_system_info.info(info_dict)
            
        except Exception as e:
            logger.warning(f"Failed to update system info: {e}")

# Global monitor instance
_monitor = None

def get_hardening_monitor() -> HardeningMonitor:
    """Get global hardening monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = HardeningMonitor()
        _monitor.update_system_info()
    return _monitor

# Convenience functions for easy integration
def track_memory_query(query_time: float, result_count: int = 0):
    """Track FAISS memory query"""
    get_hardening_monitor().track_memory_query(query_time, result_count)

def track_intent_classification(classifier_type: str, latency: float, intent: str, confidence: float):
    """Track intent classification"""
    get_hardening_monitor().track_intent_classification(classifier_type, latency, intent, confidence)

def track_length_penalty(specialist: str, original_confidence: float, penalized_confidence: float):
    """Track length penalty application"""
    get_hardening_monitor().track_length_penalty(specialist, original_confidence, penalized_confidence)

def track_specialist_win(specialist: str):
    """Track specialist win"""
    get_hardening_monitor().track_specialist_win(specialist)

def track_fast_local_hit():
    """Track fast local path usage"""
    get_hardening_monitor().track_fast_local_hit()

def track_cloud_escalation(reason: str):
    """Track cloud escalation"""
    get_hardening_monitor().track_cloud_escalation(reason)

# Context managers for easy timing
class memory_query_timer:
    """Context manager for timing memory queries"""
    def __init__(self):
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            query_time = time.time() - self.start_time
            track_memory_query(query_time)

class intent_classification_timer:
    """Context manager for timing intent classification"""
    def __init__(self, classifier_type: str):
        self.classifier_type = classifier_type
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time and not exc_type:
            latency = time.time() - self.start_time
            # Note: intent and confidence would need to be set externally
            track_intent_classification(self.classifier_type, latency, "unknown", 0.5)

if __name__ == "__main__":
    # Test the monitoring system
    monitor = get_hardening_monitor()
    
    print("📊 Testing hardening metrics...")
    
    # Test metrics
    monitor.track_docker_restart("council-api", "health_check_failed")
    monitor.track_memory_query(0.015, 3)
    monitor.track_fast_local_hit()
    monitor.track_cloud_escalation("low_confidence")
    monitor.track_intent_classification("regex", 0.002, "math", 0.95)
    
    print("✅ Metrics tracking test completed")
    print("🔗 View metrics at: http://localhost:9090/metrics") 