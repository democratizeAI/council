#!/usr/bin/env python3
"""
EXT-24C Autoscaler Service
Maintains GPU utilization between 65-80% with controlled scaling decisions
"""

import os
import time
import threading
import subprocess
from flask import Flask, jsonify, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('autoscaler')

# Prometheus metrics
SCALE_DECISIONS_TOTAL = Counter('autoscaler_decisions_total', 'Total scaling decisions', ['action'])
GPU_UTILIZATION = Gauge('gpu_util_percent', 'GPU utilization percentage')
GPU_VRAM_USAGE = Gauge('gpu_vram_max_bytes', 'GPU VRAM usage in bytes')
AUTOSCALER_ENABLED = Gauge('autoscaler_enabled', 'Autoscaler enabled status')
SCALE_COOLDOWN = Gauge('autoscaler_cooldown_seconds', 'Seconds until next scale decision allowed')
TARGET_UTILIZATION = Gauge('autoscaler_target_util_percent', 'Target GPU utilization')

app = Flask(__name__)

class AutoscalerEngine:
    """GPU utilization autoscaler for EXT-24C"""
    
    def __init__(self):
        self.enabled = False
        self.target_min = 65.0  # 65% minimum
        self.target_max = 80.0  # 80% maximum
        self.vram_limit_gb = 10.5  # 10.5GB VRAM limit
        self.cooldown_seconds = 120  # 2 minutes between decisions
        self.last_decision_time = 0
        self.decision_window = 600  # 10 minutes
        self.max_decisions_per_window = 3
        self.decision_history = []
        
        # Set initial metrics
        TARGET_UTILIZATION.set(self.target_min)
        AUTOSCALER_ENABLED.set(0)
        
        logger.info("🎯 EXT-24C Autoscaler Engine Initialized")
        logger.info(f"   Target range: {self.target_min}%-{self.target_max}%")
        logger.info(f"   VRAM limit: {self.vram_limit_gb}GB")
        logger.info(f"   Max decisions: {self.max_decisions_per_window}/10min")
    
    def get_gpu_metrics(self) -> dict:
        """Get current GPU metrics"""
        try:
            # Get GPU utilization
            util_result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=10
            )
            
            # Get VRAM usage
            vram_result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=10
            )
            
            if util_result.returncode == 0 and vram_result.returncode == 0:
                util_percent = float(util_result.stdout.strip())
                vram_mb = float(vram_result.stdout.strip())
                vram_bytes = vram_mb * 1024 * 1024
                
                # Update Prometheus metrics
                GPU_UTILIZATION.set(util_percent)
                GPU_VRAM_USAGE.set(vram_bytes)
                
                return {
                    'utilization_percent': util_percent,
                    'vram_usage_bytes': vram_bytes,
                    'vram_usage_gb': vram_mb / 1024,
                    'success': True
                }
            
            return {'success': False, 'error': 'nvidia-smi failed'}
            
        except Exception as e:
            logger.error(f"❌ Failed to get GPU metrics: {e}")
            return {'success': False, 'error': str(e)}
    
    def should_scale(self, current_util: float, current_vram_gb: float) -> dict:
        """Determine if scaling action is needed"""
        now = time.time()
        
        # Check cooldown
        time_since_last = now - self.last_decision_time
        if time_since_last < self.cooldown_seconds:
            remaining_cooldown = self.cooldown_seconds - time_since_last
            SCALE_COOLDOWN.set(remaining_cooldown)
            return {
                'action': 'none',
                'reason': f'cooldown_active_{remaining_cooldown:.0f}s'
            }
        
        SCALE_COOLDOWN.set(0)
        
        # Check decision rate limit
        recent_decisions = [d for d in self.decision_history if now - d['timestamp'] < self.decision_window]
        if len(recent_decisions) >= self.max_decisions_per_window:
            return {
                'action': 'none',
                'reason': f'rate_limited_{len(recent_decisions)}_decisions_in_10min'
            }
        
        # Check VRAM limit
        if current_vram_gb > self.vram_limit_gb:
            return {
                'action': 'scale_down',
                'reason': f'vram_limit_exceeded_{current_vram_gb:.1f}GB_>{self.vram_limit_gb}GB'
            }
        
        # Check utilization bounds
        if current_util < self.target_min:
            return {
                'action': 'scale_up',
                'reason': f'util_low_{current_util:.1f}%_<_{self.target_min}%'
            }
        elif current_util > self.target_max:
            return {
                'action': 'scale_down',
                'reason': f'util_high_{current_util:.1f}%_>_{self.target_max}%'
            }
        
        return {
            'action': 'none',
            'reason': f'in_target_range_{current_util:.1f}%'
        }
    
    def execute_scale_action(self, action: str, reason: str) -> bool:
        """Execute scaling action"""
        try:
            logger.info(f"🎛️ Executing scale action: {action} - {reason}")
            
            # Record decision
            decision = {
                'timestamp': time.time(),
                'action': action,
                'reason': reason
            }
            
            self.decision_history.append(decision)
            self.last_decision_time = time.time()
            
            # Update metrics
            SCALE_DECISIONS_TOTAL.labels(action=action).inc()
            
            # Simulate scaling actions (in real implementation, would call Kubernetes/Docker APIs)
            if action == 'scale_up':
                logger.info("📈 SCALE UP: Adding worker instances")
                # kubectl scale deployment council-workers --replicas=+1
                
            elif action == 'scale_down':
                logger.info("📉 SCALE DOWN: Removing worker instances")
                # kubectl scale deployment council-workers --replicas=-1
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Scale action failed: {e}")
            return False
    
    def enable(self):
        """Enable autoscaler"""
        self.enabled = True
        AUTOSCALER_ENABLED.set(1)
        logger.info("✅ Autoscaler ENABLED")
    
    def disable(self):
        """Disable autoscaler"""
        self.enabled = False
        AUTOSCALER_ENABLED.set(0)
        logger.info("🛑 Autoscaler DISABLED")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("👀 Starting autoscaler monitoring loop")
        
        while True:
            try:
                if not self.enabled:
                    time.sleep(10)
                    continue
                
                # Get current metrics
                metrics = self.get_gpu_metrics()
                
                if not metrics['success']:
                    logger.warning(f"⚠️ Failed to get metrics: {metrics.get('error')}")
                    time.sleep(5)
                    continue
                
                util = metrics['utilization_percent']
                vram_gb = metrics['vram_usage_gb']
                
                # Determine scaling action
                decision = self.should_scale(util, vram_gb)
                
                if decision['action'] != 'none':
                    success = self.execute_scale_action(decision['action'], decision['reason'])
                    if success:
                        logger.info(f"✅ Scale action completed: {decision['action']}")
                    else:
                        logger.error(f"❌ Scale action failed: {decision['action']}")
                else:
                    logger.debug(f"📊 No action: {decision['reason']}")
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"❌ Monitor loop error: {e}")
                time.sleep(10)

# Global autoscaler instance
autoscaler = AutoscalerEngine()

@app.route('/health')
def health():
    """Health check"""
    metrics = autoscaler.get_gpu_metrics()
    return jsonify({
        'status': 'healthy',
        'autoscaler_enabled': autoscaler.enabled,
        'gpu_metrics': metrics,
        'target_range': f"{autoscaler.target_min}-{autoscaler.target_max}%",
        'decisions_in_window': len([d for d in autoscaler.decision_history 
                                  if time.time() - d['timestamp'] < autoscaler.decision_window])
    })

@app.route('/enable', methods=['POST'])
def enable_autoscaler():
    """Enable autoscaler"""
    autoscaler.enable()
    return jsonify({'status': 'enabled'})

@app.route('/disable', methods=['POST'])
def disable_autoscaler():
    """Disable autoscaler"""
    autoscaler.disable()
    return jsonify({'status': 'disabled'})

@app.route('/status')
def status():
    """Get autoscaler status"""
    recent_decisions = [d for d in autoscaler.decision_history 
                       if time.time() - d['timestamp'] < autoscaler.decision_window]
    
    return jsonify({
        'enabled': autoscaler.enabled,
        'target_range': f"{autoscaler.target_min}-{autoscaler.target_max}%",
        'vram_limit_gb': autoscaler.vram_limit_gb,
        'decisions_in_window': len(recent_decisions),
        'max_decisions': autoscaler.max_decisions_per_window,
        'recent_decisions': recent_decisions[-5:],  # Last 5 decisions
        'cooldown_remaining': max(0, autoscaler.cooldown_seconds - (time.time() - autoscaler.last_decision_time))
    })

@app.route('/metrics')
def metrics():
    """Prometheus metrics"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    logger.info("🚀 EXT-24C Autoscaler Service Starting...")
    
    # Start monitoring loop in background
    monitor_thread = threading.Thread(target=autoscaler.monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Start Flask app
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8090)),
        debug=False,
        threaded=True
    ) 