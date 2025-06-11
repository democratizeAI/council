#!/usr/bin/env python3
"""
EXT-24B Anomaly-Burst Drill - 20-Minute Runbook
Purpose: Prove M-310 latency-anomaly alert & dashboard flip red→green in <30s
Success Gate: CouncilLatencyAnomaly alert fires, auto-resolves, and p95 spike returns to baseline

🧠 Builder 2 Implementation
"""

import os
import sys
import time
import json
import requests
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [EXT-24B] %(message)s'
)
logger = logging.getLogger('ext24b-drill')

class EXT24BDrill:
    """EXT-24B Anomaly-Burst Drill Executor"""
    
    def __init__(self):
        self.prom_url = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
        self.pushgateway_url = os.getenv('PUSHGATEWAY_URL', 'http://localhost:9091')
        self.council_url = os.getenv('COUNCIL_URL', 'http://localhost:8080')
        
        # Drill parameters
        self.spike_duration = 180  # 3 minutes
        self.spike_latency_ms = 200  # 200ms extra
        self.alert_timeout = 45  # seconds to wait for alert
        self.resolution_timeout = 30  # seconds for alert to clear
        
        # Metrics tracking
        self.baseline_p95 = None
        self.spike_p95 = None
        self.alert_fired = False
        self.alert_resolved = False
        self.alert_fire_time = None
        self.alert_resolve_time = None
        
        logger.info("🎯 EXT-24B Anomaly-Burst Drill Initialized")
        logger.info(f"   Prometheus: {self.prom_url}")
        logger.info(f"   Spike duration: {self.spike_duration}s")
        logger.info(f"   Spike latency: +{self.spike_latency_ms}ms")
    
    def query_prometheus(self, query: str) -> Optional[float]:
        """Query Prometheus and return single value"""
        try:
            response = requests.get(
                f"{self.prom_url}/api/v1/query",
                params={'query': query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']['result']:
                    return float(data['data']['result'][0]['value'][1])
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Prometheus query failed: {e}")
            return None
    
    def get_p95_latency(self) -> Optional[float]:
        """Get current p95 latency from Prometheus"""
        query = 'histogram_quantile(0.95, rate(council_router_latency_seconds_bucket[5m]))'
        return self.query_prometheus(query)
    
    def check_alerts(self) -> List[Dict]:
        """Get current active alerts"""
        try:
            response = requests.get(f"{self.prom_url}/api/v1/alerts", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data['data']['alerts']
            return []
        except Exception as e:
            logger.error(f"❌ Failed to check alerts: {e}")
            return []
    
    def check_targets(self) -> bool:
        """Verify Prometheus targets are UP"""
        try:
            response = requests.get(f"{self.prom_url}/api/v1/targets", timeout=10)
            if response.status_code == 200:
                data = response.json()
                active_targets = data['data']['activeTargets']
                
                up_count = sum(1 for target in active_targets if target['health'] == 'up')
                total_count = len(active_targets)
                
                logger.info(f"📊 Targets: {up_count}/{total_count} UP")
                return up_count == total_count
            
            return False
        except Exception as e:
            logger.error(f"❌ Failed to check targets: {e}")
            return False
    
    def get_gpu_utilization(self) -> Optional[float]:
        """Get current GPU utilization"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                util = float(result.stdout.strip())
                logger.info(f"🎮 GPU utilization: {util}%")
                return util
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get GPU utilization: {e}")
            return None
    
    def preflight_checks(self) -> bool:
        """Execute preflight checks (5 min before 06:30)"""
        logger.info("🚁 Starting preflight checks...")
        
        checks = {
            "board_green": False,
            "targets_up": False,
            "gpu_headroom": False,
            "anomaly_rule_loaded": False
        }
        
        # Check 1: Board green (no active alerts)
        alerts = self.check_alerts()
        checks["board_green"] = len(alerts) == 0
        if checks["board_green"]:
            logger.info("✅ Board green - No active alerts")
        else:
            logger.warning(f"⚠️ {len(alerts)} active alerts found")
        
        # Check 2: Targets UP
        checks["targets_up"] = self.check_targets()
        if checks["targets_up"]:
            logger.info("✅ All Prometheus targets UP")
        else:
            logger.warning("⚠️ Some Prometheus targets DOWN")
        
        # Check 3: GPU headroom (<80%)
        gpu_util = self.get_gpu_utilization()
        if gpu_util is not None:
            checks["gpu_headroom"] = gpu_util < 80
            if checks["gpu_headroom"]:
                logger.info(f"✅ GPU headroom available: {gpu_util}%")
            else:
                logger.warning(f"⚠️ High GPU utilization: {gpu_util}%")
        
        # Check 4: Anomaly rule loaded
        try:
            response = requests.get(f"{self.prom_url}/api/v1/rules", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Look for CouncilLatencyAnomaly rule
                for group in data['data']['groups']:
                    for rule in group['rules']:
                        if rule.get('name') == 'CouncilLatencyAnomaly':
                            checks["anomaly_rule_loaded"] = True
                            logger.info("✅ CouncilLatencyAnomaly rule loaded")
                            break
                    if checks["anomaly_rule_loaded"]:
                        break
                
                if not checks["anomaly_rule_loaded"]:
                    logger.warning("⚠️ CouncilLatencyAnomaly rule not found")
        except Exception as e:
            logger.error(f"❌ Failed to check rules: {e}")
        
        # Summary
        passed = sum(checks.values())
        total = len(checks)
        
        logger.info(f"🚁 Preflight complete: {passed}/{total} checks passed")
        
        if passed == total:
            logger.info("✅ All preflight checks PASSED - Ready for drill")
            return True
        else:
            logger.warning("⚠️ Some preflight checks FAILED - Drill may not work correctly")
            return False
    
    def execute_latency_spike(self) -> bool:
        """Execute the latency spike using latency_spike.py"""
        logger.info("🔥 Starting latency spike...")
        
        try:
            # Get baseline p95 before spike
            self.baseline_p95 = self.get_p95_latency()
            if self.baseline_p95:
                logger.info(f"📊 Baseline p95: {self.baseline_p95:.3f}s")
            
            # Execute latency spike script with correct arguments
            cmd = [
                'python', 'scripts/latency_spike.py',
                '--duration', str(self.spike_duration),
                '--latency', str(self.spike_latency_ms / 1000),  # Convert ms to seconds
                '--wait', '--verbose'
            ]
            
            logger.info(f"🚀 Executing: {' '.join(cmd)}")
            
            # Start spike in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment for spike to start
            time.sleep(5)
            
            # Monitor for alert firing
            self.monitor_alert_lifecycle()
            
            # Wait for process completion
            stdout, stderr = process.communicate(timeout=self.spike_duration + 60)
            
            if process.returncode == 0:
                logger.info("✅ Latency spike completed successfully")
                logger.info(f"Output: {stdout}")
                return True
            else:
                logger.error(f"❌ Latency spike failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to execute latency spike: {e}")
            return False
    
    def monitor_alert_lifecycle(self):
        """Monitor alert firing and resolution in background thread"""
        def monitor():
            start_time = time.time()
            
            # Phase 1: Wait for alert to fire
            while time.time() - start_time < self.alert_timeout:
                alerts = self.check_alerts()
                
                for alert in alerts:
                    if alert.get('labels', {}).get('alertname') == 'CouncilLatencyAnomaly':
                        if not self.alert_fired:
                            self.alert_fired = True
                            self.alert_fire_time = time.time()
                            fire_delay = self.alert_fire_time - start_time
                            logger.info(f"🚨 CouncilLatencyAnomaly FIRED after {fire_delay:.1f}s")
                        break
                
                if self.alert_fired:
                    break
                    
                time.sleep(2)
            
            if not self.alert_fired:
                logger.warning(f"⚠️ Alert did not fire within {self.alert_timeout}s")
                return
            
            # Phase 2: Wait for alert to resolve
            resolution_start = time.time()
            
            while time.time() - resolution_start < self.resolution_timeout:
                alerts = self.check_alerts()
                
                council_alert_active = False
                for alert in alerts:
                    if alert.get('labels', {}).get('alertname') == 'CouncilLatencyAnomaly':
                        council_alert_active = True
                        break
                
                if not council_alert_active and not self.alert_resolved:
                    self.alert_resolved = True
                    self.alert_resolve_time = time.time()
                    resolve_delay = self.alert_resolve_time - self.alert_fire_time
                    logger.info(f"✅ CouncilLatencyAnomaly RESOLVED after {resolve_delay:.1f}s")
                    break
                
                time.sleep(2)
            
            if not self.alert_resolved:
                logger.warning(f"⚠️ Alert did not resolve within {self.resolution_timeout}s")
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def verify_success(self) -> Dict:
        """Verify drill success criteria"""
        logger.info("🔍 Verifying success criteria...")
        
        # Get post-spike p95
        time.sleep(10)  # Wait for metrics to stabilize
        self.spike_p95 = self.get_p95_latency()
        
        results = {
            "baseline_p95": self.baseline_p95,
            "spike_p95": self.spike_p95,
            "alert_fired": self.alert_fired,
            "alert_resolved": self.alert_resolved,
            "fire_time": self.alert_fire_time,
            "resolve_time": self.alert_resolve_time,
            "success": False
        }
        
        # Calculate metrics
        if self.baseline_p95 and self.spike_p95:
            spike_delta = self.spike_p95 - self.baseline_p95
            results["spike_delta"] = spike_delta
            logger.info(f"📊 P95 delta: {spike_delta:.3f}s ({spike_delta*1000:.0f}ms)")
        
        if self.alert_fire_time and self.alert_resolve_time:
            alert_duration = self.alert_resolve_time - self.alert_fire_time
            results["alert_duration"] = alert_duration
            logger.info(f"⏱️ Alert duration: {alert_duration:.1f}s")
        
        # Success criteria
        success_criteria = []
        
        # 1. Alert fired and resolved
        if self.alert_fired and self.alert_resolved:
            success_criteria.append("Alert lifecycle ✅")
        else:
            success_criteria.append("Alert lifecycle ❌")
        
        # 2. Alert resolved within 30s
        if self.alert_resolved and results.get("alert_duration", 999) <= 30:
            success_criteria.append("Quick resolution ✅")
        else:
            success_criteria.append("Quick resolution ❌")
        
        # 3. Spike was significant (>150ms)
        if results.get("spike_delta", 0) > 0.150:
            success_criteria.append("Significant spike ✅")
        else:
            success_criteria.append("Significant spike ❌")
        
        # Overall success
        results["success"] = all("✅" in criterion for criterion in success_criteria)
        results["success_criteria"] = success_criteria
        
        logger.info("📋 Success criteria:")
        for criterion in success_criteria:
            logger.info(f"   {criterion}")
        
        return results
    
    def push_metrics(self, results: Dict):
        """Push drill results to Pushgateway"""
        try:
            success_value = 1 if results["success"] else 0
            
            metrics = f"""ext24b_pass_total {success_value}
ext24b_spike_delta_seconds {results.get('spike_delta', 0)}
ext24b_alert_duration_seconds {results.get('alert_duration', 0)}
ext24b_baseline_p95_seconds {results.get('baseline_p95', 0)}
ext24b_spike_p95_seconds {results.get('spike_p95', 0)}
"""
            
            response = requests.post(
                f"{self.pushgateway_url}/metrics/job/ext24b_drill",
                data=metrics,
                headers={'Content-Type': 'text/plain'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("📤 Metrics pushed to Pushgateway")
            else:
                logger.warning(f"⚠️ Failed to push metrics: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Failed to push metrics: {e}")
    
    def update_ledger(self, results: Dict):
        """Update Trinity Ledger with drill results"""
        try:
            if results["success"]:
                status = "🟢"
                spike_ms = results.get('spike_delta', 0) * 1000
                alert_duration = results.get('alert_duration', 0)
                notes = f"Anomaly drill PASS, p95 spike {spike_ms:.0f}ms, cleared in {alert_duration:.0f}s"
            else:
                status = "🟠"
                notes = "Anomaly drill PARTIAL - see logs for details"
            
            # Update command (simulated)
            logger.info(f"📋 Ledger update: EXT-24B {status} - {notes}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update ledger: {e}")
    
    def execute_drill(self) -> Dict:
        """Execute the complete EXT-24B drill"""
        logger.info("🚀 Starting EXT-24B Anomaly-Burst Drill")
        logger.info(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S ET')}")
        
        # Step 0: Preflight checks
        if not self.preflight_checks():
            logger.warning("⚠️ Preflight checks failed - continuing anyway")
        
        # Step 1: Execute latency spike
        spike_success = self.execute_latency_spike()
        
        # Step 2: Verify success
        results = self.verify_success()
        
        # Step 3: Push metrics
        self.push_metrics(results)
        
        # Step 4: Update ledger
        self.update_ledger(results)
        
        # Final report
        if results["success"]:
            logger.info("🎉 EXT-24B Drill PASSED")
        else:
            logger.warning("⚠️ EXT-24B Drill FAILED or PARTIAL")
        
        return results

def main():
    """Main drill execution"""
    drill = EXT24BDrill()
    
    try:
        results = drill.execute_drill()
        
        # Print final summary
        print("\n" + "="*50)
        print("EXT-24B ANOMALY-BURST DRILL SUMMARY")
        print("="*50)
        print(f"Success: {'✅ PASS' if results['success'] else '❌ FAIL'}")
        
        if results.get('spike_delta'):
            print(f"P95 spike: {results['spike_delta']*1000:.0f}ms")
        
        if results.get('alert_duration'):
            print(f"Alert duration: {results['alert_duration']:.1f}s")
        
        print("\nSuccess criteria:")
        for criterion in results.get('success_criteria', []):
            print(f"  {criterion}")
        
        print("="*50)
        
        return 0 if results["success"] else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Drill interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Drill failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 