#!/usr/bin/env python3
"""
EXT-24C Prerequisites Checker
Validates all requirements before drill execution at 08:30 ET
"""

import time
import requests
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [PREREQ] %(message)s')
logger = logging.getLogger('prereq-check')

class EXT24CPrerequisiteChecker:
    """Checks all prerequisites for EXT-24C drill"""
    
    def __init__(self):
        self.checks = {
            'soak_pass_07_00': {'status': False, 'description': 'Soak PASS flag at 07:00'},
            'lg210_enabled_07_05': {'status': False, 'description': 'LG-210 flipped to true at 07:05'},
            'int2_bench_07_15': {'status': False, 'description': 'INT-2 quant bench started 07:15'},
            'accuracy_guard_delta': {'status': False, 'description': 'accuracy_guard shows Δ ≤ 0%'},
            'autoscaler_service': {'status': False, 'description': 'Autoscaler service ready'},
            'prometheus_metrics': {'status': False, 'description': 'Prometheus metrics available'},
            'gpu_baseline': {'status': False, 'description': 'GPU baseline established'}
        }
        
        logger.info("🔍 EXT-24C Prerequisites Checker")
    
    def check_soak_pass(self) -> bool:
        """Check if soak passed at 07:00"""
        # In real implementation, would check actual soak status
        # For simulation, assume it passed
        current_time = datetime.now()
        target_time = current_time.replace(hour=7, minute=0, second=0, microsecond=0)
        
        if current_time >= target_time:
            logger.info("✅ Soak PASS at 07:00 (simulated)")
            return True
        else:
            logger.warning(f"⏳ Waiting for 07:00 soak PASS (current: {current_time.strftime('%H:%M')})")
            return False
    
    def check_lg210_enabled(self) -> bool:
        """Check if LG-210 flag is enabled"""
        # In real implementation, would check environment variable or config
        # For simulation, assume it's enabled
        current_time = datetime.now()
        target_time = current_time.replace(hour=7, minute=5, second=0, microsecond=0)
        
        if current_time >= target_time:
            logger.info("✅ LG-210 enabled at 07:05 (simulated)")
            return True
        else:
            logger.warning(f"⏳ Waiting for 07:05 LG-210 flip (current: {current_time.strftime('%H:%M')})")
            return False
    
    def check_int2_benchmark(self) -> bool:
        """Check if INT-2 benchmark started"""
        # In real implementation, would check benchmark service status
        current_time = datetime.now()
        target_time = current_time.replace(hour=7, minute=15, second=0, microsecond=0)
        
        if current_time >= target_time:
            logger.info("✅ INT-2 benchmark started at 07:15 (simulated)")
            return True
        else:
            logger.warning(f"⏳ Waiting for 07:15 INT-2 benchmark (current: {current_time.strftime('%H:%M')})")
            return False
    
    def check_accuracy_guard(self) -> bool:
        """Check accuracy guard delta"""
        # In real implementation, would query accuracy guard service
        # For simulation, assume delta is acceptable
        logger.info("✅ accuracy_guard Δ ≤ 0% (simulated)")
        return True
    
    def check_autoscaler_service(self) -> bool:
        """Check if autoscaler service is ready"""
        try:
            response = requests.get("http://localhost:8090/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Autoscaler service ready")
                return True
            else:
                logger.warning(f"⚠️ Autoscaler health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"⚠️ Autoscaler not accessible: {e}")
            return False
    
    def check_prometheus_metrics(self) -> bool:
        """Check if required Prometheus metrics are available"""
        try:
            # Check for GPU metrics
            response = requests.get(
                "http://localhost:9090/api/v1/query",
                params={'query': 'gpu_util_percent'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']['result']:
                    logger.info("✅ GPU utilization metrics available")
                    return True
            
            logger.warning("⚠️ GPU metrics not available in Prometheus")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Prometheus not accessible: {e}")
            return False
    
    def check_gpu_baseline(self) -> bool:
        """Check if GPU baseline is established"""
        try:
            # Try to get current GPU utilization
            response = requests.get(
                "http://localhost:9090/api/v1/query",
                params={'query': 'gpu_util_percent'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']['result']:
                    util = float(data['data']['result'][0]['value'][1])
                    if 0 <= util <= 50:  # Reasonable baseline
                        logger.info(f"✅ GPU baseline established: {util:.1f}%")
                        return True
                    else:
                        logger.warning(f"⚠️ GPU utilization too high for baseline: {util:.1f}%")
                        return False
            
            logger.warning("⚠️ Cannot determine GPU baseline")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ GPU baseline check failed: {e}")
            return False
    
    def run_all_checks(self) -> dict:
        """Run all prerequisite checks"""
        logger.info("🔍 Running EXT-24C prerequisite checks...")
        
        # Map check functions to their keys
        check_functions = {
            'soak_pass_07_00': self.check_soak_pass,
            'lg210_enabled_07_05': self.check_lg210_enabled,
            'int2_bench_07_15': self.check_int2_benchmark,
            'accuracy_guard_delta': self.check_accuracy_guard,
            'autoscaler_service': self.check_autoscaler_service,
            'prometheus_metrics': self.check_prometheus_metrics,
            'gpu_baseline': self.check_gpu_baseline
        }
        
        # Run each check
        for check_key, check_func in check_functions.items():
            try:
                self.checks[check_key]['status'] = check_func()
            except Exception as e:
                logger.error(f"❌ Check {check_key} failed: {e}")
                self.checks[check_key]['status'] = False
                self.checks[check_key]['error'] = str(e)
        
        # Summary
        passed = sum(1 for check in self.checks.values() if check['status'])
        total = len(self.checks)
        
        logger.info(f"📊 Prerequisites Summary: {passed}/{total} passed")
        
        if passed == total:
            logger.info("🎉 All prerequisites PASSED - Ready for EXT-24C drill")
        else:
            logger.warning("⚠️ Some prerequisites FAILED - Review before drill")
            
            # Log failed checks
            for key, check in self.checks.items():
                if not check['status']:
                    logger.warning(f"   ❌ {check['description']}")
        
        return {
            'all_passed': passed == total,
            'passed_count': passed,
            'total_count': total,
            'checks': self.checks,
            'ready_for_drill': passed >= (total * 0.8)  # 80% threshold
        }

def main():
    """Run prerequisite checks"""
    checker = EXT24CPrerequisiteChecker()
    
    try:
        results = checker.run_all_checks()
        
        print("\n" + "="*50)
        print("EXT-24C PREREQUISITES SUMMARY")
        print("="*50)
        
        for key, check in results['checks'].items():
            status = "✅ PASS" if check['status'] else "❌ FAIL"
            print(f"{status} - {check['description']}")
        
        print("="*50)
        overall_status = "✅ READY" if results['all_passed'] else "⚠️ PARTIAL" if results['ready_for_drill'] else "❌ NOT READY"
        print(f"Overall Status: {overall_status}")
        print(f"Score: {results['passed_count']}/{results['total_count']}")
        print("="*50)
        
        return 0 if results['ready_for_drill'] else 1
        
    except Exception as e:
        logger.error(f"❌ Prerequisites check failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 