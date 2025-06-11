#!/usr/bin/env python3
"""
EXT-24C Guardian Monitor
Monitors autoscaler performance and writes pass/fail results
"""

import time
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [GUARDIAN] %(message)s')
logger = logging.getLogger('guardian')

class EXT24CGuardian:
    """Guardian monitoring for EXT-24C autoscaler drill"""
    
    def __init__(self):
        self.prometheus_url = "http://localhost:9090"
        self.autoscaler_url = "http://localhost:8090"
        
        # Pass conditions
        self.target_util_min = 65.0
        self.target_util_max = 80.0
        self.max_scale_decisions = 3
        self.max_latency_spike = 0.020  # 20ms
        self.monitor_duration = 600  # 10 minutes
        
        # Monitoring state
        self.start_time = None
        self.util_violations = []
        self.latency_spikes = []
        self.scale_decisions = 0
        self.monitoring = False
        
        logger.info("🛡️ EXT-24C Guardian Monitor Initialized")
        logger.info(f"   Target utilization: {self.target_util_min}-{self.target_util_max}%")
        logger.info(f"   Max scale decisions: {self.max_scale_decisions}")
        logger.info(f"   Max latency spike: {self.max_latency_spike*1000:.0f}ms")
    
    def query_prometheus(self, query: str) -> Optional[float]:
        """Query Prometheus for metrics"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={'query': query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']['result']:
                    return float(data['data']['result'][0]['value'][1])
            
            return None
            
        except Exception as e:
            logger.debug(f"Prometheus query failed: {e}")
            return None
    
    def get_gpu_utilization(self) -> Optional[float]:
        """Get current GPU utilization"""
        return self.query_prometheus('gpu_util_percent')
    
    def get_vram_usage_gb(self) -> Optional[float]:
        """Get current VRAM usage in GB"""
        vram_bytes = self.query_prometheus('gpu_vram_max_bytes')
        if vram_bytes is not None:
            return vram_bytes / (1024 * 1024 * 1024)
        return None
    
    def get_scale_decisions_count(self) -> int:
        """Get total scale decisions in monitoring window"""
        try:
            # Query for total decisions across all actions
            decisions = self.query_prometheus('increase(autoscaler_decisions_total[10m])')
            return int(decisions) if decisions is not None else 0
        except:
            return 0
    
    def get_p95_latency(self) -> Optional[float]:
        """Get current P95 latency"""
        # Try to get from existing metrics
        queries = [
            'histogram_quantile(0.95, rate(council_router_latency_seconds_bucket[1m]))',
            'ext24b_council_latency_p95_seconds',
            'council_latency_p95_5m'
        ]
        
        for query in queries:
            result = self.query_prometheus(query)
            if result is not None:
                return result
        
        return None
    
    def check_autoscaler_status(self) -> Dict:
        """Check autoscaler service status"""
        try:
            response = requests.get(f"{self.autoscaler_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'error': str(e)}
    
    def record_violation(self, violation_type: str, value: float, threshold: float):
        """Record a pass condition violation"""
        violation = {
            'timestamp': time.time(),
            'type': violation_type,
            'value': value,
            'threshold': threshold,
            'elapsed': time.time() - self.start_time if self.start_time else 0
        }
        
        if violation_type == 'utilization':
            self.util_violations.append(violation)
            logger.warning(f"⚠️ Utilization violation: {value:.1f}% (target: {self.target_util_min}-{self.target_util_max}%)")
        elif violation_type == 'latency':
            self.latency_spikes.append(violation)
            logger.warning(f"⚠️ Latency spike: {value*1000:.1f}ms (max: {threshold*1000:.0f}ms)")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info(f"👀 Starting {self.monitor_duration}s monitoring window")
        
        self.start_time = time.time()
        self.monitoring = True
        
        while self.monitoring and (time.time() - self.start_time) < self.monitor_duration:
            try:
                elapsed = time.time() - self.start_time
                
                # Get current metrics
                gpu_util = self.get_gpu_utilization()
                vram_gb = self.get_vram_usage_gb()
                scale_decisions = self.get_scale_decisions_count()
                p95_latency = self.get_p95_latency()
                autoscaler_status = self.check_autoscaler_status()
                
                # Check GPU utilization bounds
                if gpu_util is not None:
                    if gpu_util < self.target_util_min:
                        self.record_violation('utilization', gpu_util, self.target_util_min)
                    elif gpu_util > self.target_util_max:
                        self.record_violation('utilization', gpu_util, self.target_util_max)
                
                # Check latency spikes
                if p95_latency is not None and p95_latency > self.max_latency_spike:
                    self.record_violation('latency', p95_latency, self.max_latency_spike)
                
                # Update scale decisions count
                self.scale_decisions = scale_decisions
                
                # Log status every 60 seconds
                if int(elapsed) % 60 == 0:
                    logger.info(f"📊 T+{elapsed:.0f}s: GPU={gpu_util:.1f}% VRAM={vram_gb:.1f}GB "
                               f"Decisions={scale_decisions} P95={p95_latency*1000:.1f}ms" 
                               if p95_latency else f"Decisions={scale_decisions}")
                
                # Check for early failure conditions
                if scale_decisions > self.max_scale_decisions:
                    logger.error(f"❌ EARLY FAIL: Too many scale decisions ({scale_decisions} > {self.max_scale_decisions})")
                    self.monitoring = False
                    break
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"❌ Monitor loop error: {e}")
                time.sleep(10)
        
        logger.info("✅ Monitoring window completed")
    
    def evaluate_results(self) -> Dict:
        """Evaluate drill results and determine pass/fail"""
        total_duration = time.time() - self.start_time if self.start_time else 0
        
        results = {
            'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            'duration': total_duration,
            'target_duration': self.monitor_duration,
            'gpu_util_violations': len(self.util_violations),
            'latency_spikes': len(self.latency_spikes),
            'scale_decisions': self.scale_decisions,
            'max_scale_decisions': self.max_scale_decisions,
            'pass_conditions': {},
            'overall_pass': False
        }
        
        # Evaluate pass conditions
        conditions = {
            'utilization_in_band': len(self.util_violations) == 0,
            'scale_decisions_ok': self.scale_decisions <= self.max_scale_decisions,
            'no_latency_spikes': len(self.latency_spikes) == 0,
            'full_duration': total_duration >= (self.monitor_duration * 0.95)  # Allow 5% tolerance
        }
        
        results['pass_conditions'] = conditions
        results['overall_pass'] = all(conditions.values())
        
        # Log results
        logger.info("📊 EXT-24C Drill Results:")
        for condition, passed in conditions.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"   {condition}: {status}")
        
        if results['overall_pass']:
            logger.info("🎉 EXT-24C Drill PASSED")
        else:
            logger.warning("⚠️ EXT-24C Drill FAILED")
        
        return results
    
    def write_pass_file(self, results: Dict):
        """Write pass/fail result to /tmp/EXT24C_PASS"""
        try:
            pass_data = {
                'drill': 'EXT-24C',
                'timestamp': datetime.now().isoformat(),
                'passed': results['overall_pass'],
                'results': results
            }
            
            with open('/tmp/EXT24C_PASS', 'w') as f:
                json.dump(pass_data, f, indent=2)
            
            status = "PASS" if results['overall_pass'] else "FAIL"
            logger.info(f"📝 Guardian wrote /tmp/EXT24C_PASS - {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to write pass file: {e}")
    
    def run_drill_monitor(self):
        """Run the complete drill monitoring"""
        logger.info("🚀 Starting EXT-24C Guardian monitoring")
        
        try:
            # Monitor the drill
            self.monitor_loop()
            
            # Evaluate results
            results = self.evaluate_results()
            
            # Write pass file
            self.write_pass_file(results)
            
            return results['overall_pass']
            
        except Exception as e:
            logger.error(f"❌ Guardian monitoring failed: {e}")
            return False

def main():
    """Run Guardian monitoring"""
    guardian = EXT24CGuardian()
    
    try:
        success = guardian.run_drill_monitor()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("🛑 Guardian monitoring interrupted")
        return 1
    except Exception as e:
        logger.error(f"❌ Guardian failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 