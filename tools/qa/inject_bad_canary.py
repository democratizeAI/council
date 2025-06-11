#!/usr/bin/env python3
"""
Rollback Drill Script - Builder Hardening Wave
Simulates bad deployments to test automatic rollback systems

Usage:
    python tools/qa/inject_bad_canary.py --pr QA-302-demo
    python tools/qa/inject_bad_canary.py --pr QA-302-demo --shadow
    python tools/qa/inject_bad_canary.py --type accuracy-regression
    python tools/qa/inject_bad_canary.py --type cost-spike
"""

import argparse
import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import requests
from prometheus_client.parser import text_string_to_metric_families

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RollbackDrillSimulator:
    """Simulates various failure scenarios to test rollback mechanisms"""
    
    def __init__(self, patchctl_url: str = "http://patchctl:8080", 
                 prometheus_url: str = "http://prometheus:9090"):
        self.patchctl_url = patchctl_url
        self.prometheus_url = prometheus_url
        self.drill_id = f"drill_{int(time.time())}"
        
    async def simulate_bad_pr(self, pr_id: str, shadow: bool = False) -> Dict:
        """Simulate a bad PR that should trigger rollback"""
        logger.info(f"🧪 Starting rollback drill: {self.drill_id}")
        logger.info(f"📝 Simulating bad PR: {pr_id} (shadow={shadow})")
        
        # Create bad PR payload
        bad_pr = self._generate_bad_pr_payload(pr_id)
        
        # Submit to streaming auditor
        result = await self._submit_to_auditor(bad_pr, shadow)
        
        # Monitor rollback trigger
        rollback_triggered = await self._wait_for_rollback(timeout=120)
        
        if rollback_triggered:
            logger.info("✅ Rollback triggered successfully")
            recovery_time = await self._measure_recovery_time()
            logger.info(f"⏱️ Recovery time: {recovery_time}s")
            return {
                "drill_id": self.drill_id,
                "success": True,
                "recovery_time": recovery_time,
                "pr_id": pr_id
            }
        else:
            logger.error("❌ Rollback NOT triggered - drill failed")
            return {
                "drill_id": self.drill_id,
                "success": False,
                "pr_id": pr_id
            }
    
    def _generate_bad_pr_payload(self, pr_id: str) -> Dict:
        """Generate PR payload that violates policies"""
        scenarios = [
            self._accuracy_regression_scenario(),
            self._cost_spike_scenario(),
            self._coverage_violation_scenario(),
            self._latency_regression_scenario()
        ]
        
        base_payload = {
            "pr_id": pr_id,
            "drill_id": self.drill_id,
            "timestamp": datetime.utcnow().isoformat(),
            "meta": {
                "title": f"[DRILL] Rollback test - {pr_id}",
                "description": "Automated rollback drill - safe to ignore",
                "author": "rollback-drill-bot"
            }
        }
        
        # Pick random violation scenario
        violation = random.choice(scenarios)
        base_payload.update(violation)
        
        logger.info(f"📊 Simulated violation: {violation['violation_type']}")
        return base_payload
    
    def _accuracy_regression_scenario(self) -> Dict:
        """Simulate accuracy regression below 95% baseline"""
        return {
            "violation_type": "accuracy_regression",
            "metrics": {
                "accuracy_score": 0.89,  # Below 95% threshold
                "test_suite_results": {
                    "reasoning_bench": 0.87,
                    "code_generation": 0.91,
                    "natural_language": 0.88
                }
            },
            "policy_violations": ["accuracy_baseline_violated"]
        }
    
    def _cost_spike_scenario(self) -> Dict:
        """Simulate cost spike exceeding daily budget"""
        return {
            "violation_type": "cost_spike",
            "metrics": {
                "cost_per_request": 0.015,  # Above normal
                "projected_daily_cost": 0.75,  # Above $0.50 limit
                "o3_api_calls": 150  # Excessive usage
            },
            "policy_violations": ["daily_cost_exceeded"]
        }
    
    def _coverage_violation_scenario(self) -> Dict:
        """Simulate test coverage below requirements"""
        return {
            "violation_type": "coverage_violation",
            "metrics": {
                "test_coverage": 0.72,  # Below 80% requirement
                "lines_covered": 1440,
                "lines_total": 2000,
                "missing_tests": ["meta_hash_audit.py", "streaming_auditor.py"]
            },
            "policy_violations": ["test_coverage_insufficient"]
        }
    
    def _latency_regression_scenario(self) -> Dict:
        """Simulate latency regression above thresholds"""
        return {
            "violation_type": "latency_regression",
            "metrics": {
                "p95_latency_ms": 450,  # Above 200ms threshold
                "p99_latency_ms": 850,  # Above 500ms threshold
                "response_times": [120, 180, 340, 450, 520, 680, 850]
            },
            "policy_violations": ["latency_threshold_exceeded"]
        }
    
    async def _submit_to_auditor(self, payload: Dict, shadow: bool = False) -> Dict:
        """Submit bad payload to streaming auditor webhook"""
        webhook_url = f"{self.patchctl_url}/webhook/meta"
        if shadow:
            webhook_url += "?shadow=true"
        
        headers = {
            "Content-Type": "application/json",
            "X-Audit-Source": "rollback-drill",
            "X-Drill-ID": self.drill_id
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(webhook_url, json=payload, headers=headers) as response:
                    result = await response.json()
                    logger.info(f"📤 Submitted to auditor: {response.status}")
                    return result
            except Exception as e:
                logger.error(f"❌ Failed to submit to auditor: {e}")
                return {"error": str(e)}
    
    async def _wait_for_rollback(self, timeout: int = 120) -> bool:
        """Wait for rollback to be triggered"""
        logger.info(f"⏳ Waiting for rollback trigger (timeout: {timeout}s)")
        
        start_time = time.time()
        initial_count = await self._get_rollback_count()
        
        while (time.time() - start_time) < timeout:
            current_count = await self._get_rollback_count()
            
            if current_count > initial_count:
                logger.info("🎯 Rollback triggered!")
                return True
            
            await asyncio.sleep(5)
        
        logger.warning(f"⏰ Timeout waiting for rollback ({timeout}s)")
        return False
    
    async def _get_rollback_count(self) -> int:
        """Get current rollback count from Prometheus"""
        query = "gemini_rollback_triggered_total"
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.prometheus_url}/api/v1/query"
                params = {"query": query}
                
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    if data["status"] == "success" and data["data"]["result"]:
                        return int(float(data["data"]["result"][0]["value"][1]))
                    
                    return 0
        except Exception as e:
            logger.warning(f"Failed to query Prometheus: {e}")
            return 0
    
    async def _measure_recovery_time(self) -> float:
        """Measure time for system to recover after rollback"""
        logger.info("📊 Measuring recovery time...")
        
        start_time = time.time()
        
        # Wait for system to become healthy again
        while True:
            healthy = await self._check_system_health()
            if healthy:
                recovery_time = time.time() - start_time
                return round(recovery_time, 1)
            
            await asyncio.sleep(2)
            
            # Safety timeout
            if (time.time() - start_time) > 300:
                logger.warning("Recovery timeout - system may need manual intervention")
                return 300.0
    
    async def _check_system_health(self) -> bool:
        """Check if system is healthy after rollback"""
        health_checks = [
            self._check_patchctl_health(),
            self._check_gemini_audit_health(),
            self._check_prometheus_health()
        ]
        
        results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        # All health checks must pass
        return all(isinstance(r, bool) and r for r in results)
    
    async def _check_patchctl_health(self) -> bool:
        """Check PatchCtl health endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.patchctl_url}/health") as response:
                    return response.status == 200
        except:
            return False
    
    async def _check_gemini_audit_health(self) -> bool:
        """Check Gemini audit service health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://gemini-audit:8080/health") as response:
                    return response.status == 200
        except:
            return False
    
    async def _check_prometheus_health(self) -> bool:
        """Check Prometheus health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.prometheus_url}/-/healthy") as response:
                    return response.status == 200
        except:
            return False

class DrillReporter:
    """Generate reports for rollback drill results"""
    
    def __init__(self):
        self.report_data = []
    
    def add_drill_result(self, result: Dict):
        """Add drill result to report"""
        self.report_data.append({
            **result,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def generate_report(self) -> Dict:
        """Generate comprehensive drill report"""
        if not self.report_data:
            return {"error": "No drill data available"}
        
        total_drills = len(self.report_data)
        successful_drills = sum(1 for r in self.report_data if r.get("success", False))
        
        recovery_times = [r.get("recovery_time", 0) for r in self.report_data if r.get("recovery_time")]
        avg_recovery = sum(recovery_times) / len(recovery_times) if recovery_times else 0
        
        return {
            "drill_summary": {
                "total_drills": total_drills,
                "successful_drills": successful_drills,
                "success_rate": round(successful_drills / total_drills * 100, 1),
                "average_recovery_time": round(avg_recovery, 1)
            },
            "performance_metrics": {
                "fastest_recovery": min(recovery_times) if recovery_times else 0,
                "slowest_recovery": max(recovery_times) if recovery_times else 0,
                "target_recovery_time": 90.0,
                "target_met": all(t <= 90.0 for t in recovery_times)
            },
            "drill_details": self.report_data
        }
    
    def save_report(self, filename: str = None):
        """Save report to file"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"rollback_drill_report_{timestamp}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📋 Report saved: {filename}")
        return filename

async def run_comprehensive_drill():
    """Run comprehensive rollback drill with multiple scenarios"""
    logger.info("🚀 Starting comprehensive rollback drill")
    
    simulator = RollbackDrillSimulator()
    reporter = DrillReporter()
    
    # Test scenarios
    scenarios = [
        {"pr": "QA-302-accuracy", "type": "accuracy_regression"},
        {"pr": "QA-302-cost", "type": "cost_spike"},
        {"pr": "QA-302-coverage", "type": "coverage_violation"},
        {"pr": "QA-302-latency", "type": "latency_regression"}
    ]
    
    for scenario in scenarios:
        logger.info(f"🧪 Running scenario: {scenario['type']}")
        
        result = await simulator.simulate_bad_pr(scenario["pr"], shadow=True)
        result["scenario_type"] = scenario["type"]
        
        reporter.add_drill_result(result)
        
        # Brief pause between scenarios
        await asyncio.sleep(10)
    
    # Generate final report
    report_file = reporter.save_report()
    final_report = reporter.generate_report()
    
    logger.info("📊 Comprehensive drill complete!")
    logger.info(f"Success rate: {final_report['drill_summary']['success_rate']}%")
    logger.info(f"Average recovery: {final_report['drill_summary']['average_recovery_time']}s")
    
    return final_report

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Builder Hardening Rollback Drill")
    parser.add_argument("--pr", default="QA-302-demo", help="PR ID for drill")
    parser.add_argument("--shadow", action="store_true", help="Run in shadow mode")
    parser.add_argument("--type", choices=["accuracy-regression", "cost-spike", "coverage-violation", "latency-regression"], 
                        help="Specific violation type to test")
    parser.add_argument("--comprehensive", action="store_true", help="Run all scenarios")
    parser.add_argument("--patchctl-url", default="http://patchctl:8080", help="PatchCtl URL")
    parser.add_argument("--prometheus-url", default="http://prometheus:9090", help="Prometheus URL")
    
    args = parser.parse_args()
    
    if args.comprehensive:
        # Run comprehensive drill
        result = asyncio.run(run_comprehensive_drill())
        print(json.dumps(result, indent=2))
    else:
        # Run single drill
        simulator = RollbackDrillSimulator(args.patchctl_url, args.prometheus_url)
        result = asyncio.run(simulator.simulate_bad_pr(args.pr, args.shadow))
        
        if result["success"]:
            print(f"✅ Rollback drill PASSED")
            print(f"📊 Recovery time: {result['recovery_time']}s")
            print(f"🎯 Target: <90s (Met: {result['recovery_time'] <= 90})")
        else:
            print(f"❌ Rollback drill FAILED")
            print(f"🔍 Check logs for details")
            exit(1)

if __name__ == "__main__":
    main() 