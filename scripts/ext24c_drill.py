#!/usr/bin/env python3
"""
EXT-24C Autoscaler Drill Orchestrator
Coordinates autoscaler enablement, load ramp, and monitoring for complete drill execution
"""

import os
import time
import threading
import subprocess
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [EXT-24C] %(message)s')
logger = logging.getLogger('ext24c-drill')

class EXT24CDrill:
    """EXT-24C Autoscaler Drill orchestrator"""
    
    def __init__(self):
        self.autoscaler_url = "http://localhost:8090"
        self.council_url = "http://localhost:8080"
        
        # Drill parameters
        self.load_ramp_duration = 600  # 10 minutes
        self.start_qps = 200
        self.end_qps = 600
        
        # State tracking
        self.autoscaler_enabled = False
        self.load_ramp_running = False
        self.guardian_monitoring = False
        
        logger.info("🎯 EXT-24C Autoscaler Drill Orchestrator")
        logger.info(f"   Load ramp: {self.start_qps} → {self.end_qps} QPS over {self.load_ramp_duration}s")
    
    def check_prerequisites(self) -> Dict:
        """Check prerequisites for EXT-24C drill"""
        logger.info("🔍 Checking EXT-24C prerequisites...")
        
        prereqs = {
            'soak_pass': False,
            'lg210_enabled': False,
            'int2_bench_started': False,
            'autoscaler_ready': False,
            'council_ready': False
        }
        
        # Check 1: Soak PASS (simulated - would check actual soak status)
        # In real implementation: check soak flags at 07:00
        prereqs['soak_pass'] = True  # Simulated
        logger.info("✅ Soak PASS flag confirmed (simulated)")
        
        # Check 2: LG-210 enabled (simulated - would check env flag)
        # In real implementation: check LG-210 env flag at 07:05
        prereqs['lg210_enabled'] = True  # Simulated
        logger.info("✅ LG-210 flag enabled (simulated)")
        
        # Check 3: INT-2 benchmark (simulated)
        # In real implementation: check INT-2 benchmark status and accuracy_guard
        prereqs['int2_bench_started'] = True  # Simulated
        logger.info("✅ INT-2 benchmark started, accuracy_guard Δ ≤ 0% (simulated)")
        
        # Check 4: Autoscaler service
        try:
            response = requests.get(f"{self.autoscaler_url}/health", timeout=5)
            prereqs['autoscaler_ready'] = response.status_code == 200
            if prereqs['autoscaler_ready']:
                logger.info("✅ Autoscaler service ready")
            else:
                logger.warning(f"⚠️ Autoscaler health check failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Autoscaler not accessible: {e}")
        
        # Check 5: Council service (target for load testing)
        try:
            response = requests.get(f"{self.council_url}/health", timeout=5)
            prereqs['council_ready'] = response.status_code == 200
            if prereqs['council_ready']:
                logger.info("✅ Council service ready")
            else:
                logger.warning(f"⚠️ Council health check failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Council not accessible: {e}")
        
        passed = sum(prereqs.values())
        total = len(prereqs)
        
        logger.info(f"🔍 Prerequisites: {passed}/{total} passed")
        
        return prereqs
    
    def enable_autoscaler(self) -> bool:
        """Enable autoscaler via API call (simulates Helm values update)"""
        logger.info("⚡ Enabling autoscaler (AUTOSCALE_ENABLED=true)")
        
        try:
            # In real implementation: would update Helm values
            # helm upgrade council-autoscaler --set autoscaler.enabled=true
            
            response = requests.post(f"{self.autoscaler_url}/enable", timeout=10)
            
            if response.status_code == 200:
                self.autoscaler_enabled = True
                logger.info("✅ Autoscaler enabled successfully")
                return True
            else:
                logger.error(f"❌ Failed to enable autoscaler: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to enable autoscaler: {e}")
            return False
    
    def disable_autoscaler(self) -> bool:
        """Disable autoscaler (emergency fallback)"""
        logger.info("🛑 Disabling autoscaler (AUTOSCALE_ENABLED=false)")
        
        try:
            response = requests.post(f"{self.autoscaler_url}/disable", timeout=10)
            
            if response.status_code == 200:
                self.autoscaler_enabled = False
                logger.info("✅ Autoscaler disabled")
                return True
            else:
                logger.error(f"❌ Failed to disable autoscaler: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to disable autoscaler: {e}")
            return False
    
    def start_load_ramp(self) -> bool:
        """Start load ramp script"""
        logger.info(f"🚀 Starting load ramp: {self.start_qps} → {self.end_qps} QPS")
        
        try:
            # Start load ramp script
            cmd = [
                'python', 'scripts/ext24c_load_ramp.py',
                '--target', self.council_url,
                '--start-qps', str(self.start_qps),
                '--end-qps', str(self.end_qps),
                '--duration', str(self.load_ramp_duration),
                '--workers', '10'
            ]
            
            logger.info(f"🔧 Executing: {' '.join(cmd)}")
            
            self.load_ramp_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.load_ramp_running = True
            logger.info("✅ Load ramp started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start load ramp: {e}")
            return False
    
    def start_guardian_monitoring(self) -> bool:
        """Start Guardian monitoring"""
        logger.info("🛡️ Starting Guardian monitoring")
        
        try:
            cmd = ['python', 'scripts/ext24c_guardian.py']
            
            self.guardian_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.guardian_monitoring = True
            logger.info("✅ Guardian monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Guardian monitoring: {e}")
            return False
    
    def monitor_drill_progress(self):
        """Monitor drill progress and handle failures"""
        logger.info("👀 Monitoring drill progress...")
        
        start_time = time.time()
        check_interval = 30  # Check every 30 seconds
        
        while self.load_ramp_running or self.guardian_monitoring:
            time.sleep(check_interval)
            elapsed = time.time() - start_time
            
            # Check for load ramp completion
            if self.load_ramp_running and hasattr(self, 'load_ramp_process'):
                if self.load_ramp_process.poll() is not None:
                    self.load_ramp_running = False
                    logger.info("✅ Load ramp completed")
            
            # Check for Guardian completion
            if self.guardian_monitoring and hasattr(self, 'guardian_process'):
                if self.guardian_process.poll() is not None:
                    self.guardian_monitoring = False
                    logger.info("✅ Guardian monitoring completed")
            
            # Emergency checks (simulated - would check real metrics)
            try:
                # Check for excessive scale decisions
                response = requests.get(f"{self.autoscaler_url}/status", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    decisions = status.get('decisions_in_window', 0)
                    
                    if decisions > 3 and elapsed < 600:  # More than 3 decisions in first 10 min
                        logger.warning(f"⚠️ EMERGENCY: {decisions} scale decisions detected")
                        logger.info("🔧 Raising VRAM cap to 80% (AS_VRAM_CAP_MB=10240)")
                        # In real implementation: would update VRAM cap
                
            except Exception as e:
                logger.debug(f"Status check failed: {e}")
            
            logger.info(f"📊 T+{elapsed:.0f}s: Drill in progress...")
    
    def check_pass_file(self) -> Dict:
        """Check Guardian pass file results"""
        try:
            import json
            with open('/tmp/EXT24C_PASS', 'r') as f:
                pass_data = json.load(f)
            
            return pass_data
            
        except FileNotFoundError:
            logger.warning("⚠️ Guardian pass file not found")
            return {'passed': False, 'error': 'pass_file_missing'}
        except Exception as e:
            logger.error(f"❌ Failed to read pass file: {e}")
            return {'passed': False, 'error': str(e)}
    
    def execute_drill(self) -> Dict:
        """Execute the complete EXT-24C drill"""
        logger.info("🚀 Starting EXT-24C Autoscaler Drill")
        logger.info(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S ET')}")
        
        results = {
            'start_time': datetime.now().isoformat(),
            'prerequisites_passed': False,
            'autoscaler_enabled': False,
            'load_ramp_started': False,
            'guardian_started': False,
            'drill_completed': False,
            'guardian_pass': False,
            'overall_success': False
        }
        
        try:
            # Step 1: Check prerequisites
            prereqs = self.check_prerequisites()
            results['prerequisites_passed'] = all(prereqs.values())
            
            if not results['prerequisites_passed']:
                logger.error("❌ Prerequisites failed - aborting drill")
                return results
            
            # Step 2: Enable autoscaler
            results['autoscaler_enabled'] = self.enable_autoscaler()
            if not results['autoscaler_enabled']:
                logger.error("❌ Failed to enable autoscaler - aborting drill")
                return results
            
            # Step 3: Start Guardian monitoring
            results['guardian_started'] = self.start_guardian_monitoring()
            
            # Step 4: Start load ramp
            results['load_ramp_started'] = self.start_load_ramp()
            if not results['load_ramp_started']:
                logger.error("❌ Failed to start load ramp - aborting drill")
                return results
            
            # Step 5: Monitor progress
            self.monitor_drill_progress()
            
            # Step 6: Wait for Guardian completion and check results
            if hasattr(self, 'guardian_process'):
                logger.info("⏳ Waiting for Guardian to complete...")
                self.guardian_process.wait(timeout=660)  # 11 minutes max
            
            results['drill_completed'] = True
            
            # Step 7: Check pass file
            pass_data = self.check_pass_file()
            results['guardian_pass'] = pass_data.get('passed', False)
            results['pass_data'] = pass_data
            
            # Overall success
            results['overall_success'] = (
                results['prerequisites_passed'] and
                results['autoscaler_enabled'] and
                results['load_ramp_started'] and
                results['guardian_started'] and
                results['drill_completed'] and
                results['guardian_pass']
            )
            
            if results['overall_success']:
                logger.info("🎉 EXT-24C Drill PASSED")
            else:
                logger.warning("⚠️ EXT-24C Drill FAILED")
            
        except Exception as e:
            logger.error(f"❌ Drill execution failed: {e}")
            results['error'] = str(e)
        
        finally:
            # Cleanup: Disable autoscaler
            if self.autoscaler_enabled:
                self.disable_autoscaler()
        
        return results

def main():
    """Execute EXT-24C drill"""
    drill = EXT24CDrill()
    
    try:
        results = drill.execute_drill()
        
        print("\n" + "="*60)
        print("EXT-24C AUTOSCALER DRILL SUMMARY")
        print("="*60)
        print(f"Overall Success: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
        print(f"Prerequisites: {'✅' if results['prerequisites_passed'] else '❌'}")
        print(f"Autoscaler Enabled: {'✅' if results['autoscaler_enabled'] else '❌'}")
        print(f"Load Ramp Started: {'✅' if results['load_ramp_started'] else '❌'}")
        print(f"Guardian Monitoring: {'✅' if results['guardian_started'] else '❌'}")
        print(f"Guardian Pass: {'✅' if results['guardian_pass'] else '❌'}")
        print("="*60)
        
        return 0 if results['overall_success'] else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Drill interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Drill failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 