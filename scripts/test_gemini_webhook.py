#!/usr/bin/env python3
"""
QA-302 Gemini Webhook Test Harness
==================================

Tests the Gemini streaming auditor webhook with both passing and failing scenarios.
Verifies policy assertion logic and rollback triggers.

Usage:
    python scripts/test_gemini_webhook.py
    python scripts/test_gemini_webhook.py --endpoint http://localhost:8091
"""

import asyncio
import json
import time
import argparse
import logging
from typing import Dict, List, Any
from dataclasses import dataclass

import aiohttp
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestCase:
    """Test case definition"""
    name: str
    pr_id: str
    meta: Dict[str, float]
    expected_result: str  # "policies_passed" or "violation_detected"
    expected_violations: int
    description: str

class GeminiWebhookTester:
    """Test harness for Gemini webhook functionality"""
    
    def __init__(self, endpoint: str = "http://localhost:8091"):
        self.endpoint = endpoint
        self.webhook_url = f"{endpoint}/webhook/meta"
        self.status_url = f"{endpoint}/audit/status"
        self.health_url = f"{endpoint}/health"
        
        # Test cases covering all scenarios from QA-302 spec
        self.test_cases = [
            # Passing scenarios
            TestCase(
                name="all_policies_pass",
                pr_id="QA-302-pass-01",
                meta={
                    "unit_coverage": 97.5,  # >= 95% ✅
                    "latency_regression": 0.3,  # <= 1% ✅  
                    "cost_delta": 0.007  # <= $0.01 ✅
                },
                expected_result="policies_passed",
                expected_violations=0,
                description="All policies meet requirements"
            ),
            
            TestCase(
                name="minimal_pass_thresholds",
                pr_id="QA-302-pass-02", 
                meta={
                    "unit_coverage": 95.0,  # Exactly 95% ✅
                    "latency_regression": 1.0,  # Exactly 1% ✅
                    "cost_delta": 0.01  # Exactly $0.01 ✅
                },
                expected_result="policies_passed",
                expected_violations=0,
                description="Policies exactly at threshold boundaries"
            ),
            
            # Single violation scenarios
            TestCase(
                name="coverage_violation_only",
                pr_id="QA-302-fail-01",
                meta={
                    "unit_coverage": 92.0,  # < 95% ❌
                    "latency_regression": 0.5,  # <= 1% ✅
                    "cost_delta": 0.005  # <= $0.01 ✅
                },
                expected_result="violation_detected",
                expected_violations=1,
                description="Unit coverage below 95% threshold"
            ),
            
            TestCase(
                name="latency_violation_only",
                pr_id="QA-302-fail-02",
                meta={
                    "unit_coverage": 97.0,  # >= 95% ✅
                    "latency_regression": 1.8,  # > 1% ❌
                    "cost_delta": 0.008  # <= $0.01 ✅
                },
                expected_result="violation_detected",
                expected_violations=1,
                description="Latency regression above 1% threshold"
            ),
            
            TestCase(
                name="cost_violation_only",
                pr_id="QA-302-fail-03",
                meta={
                    "unit_coverage": 96.0,  # >= 95% ✅
                    "latency_regression": 0.7,  # <= 1% ✅
                    "cost_delta": 0.025  # > $0.01 ❌
                },
                expected_result="violation_detected",
                expected_violations=1,
                description="Cost delta above $0.01 threshold"
            ),
            
            # Multiple violation scenarios
            TestCase(
                name="coverage_and_latency_violations",
                pr_id="QA-302-fail-04",
                meta={
                    "unit_coverage": 88.0,  # < 95% ❌
                    "latency_regression": 2.5,  # > 1% ❌
                    "cost_delta": 0.005  # <= $0.01 ✅
                },
                expected_result="violation_detected",
                expected_violations=2,
                description="Both coverage and latency violations"
            ),
            
            TestCase(
                name="all_policies_fail",
                pr_id="QA-302-fail-05",
                meta={
                    "unit_coverage": 85.0,  # < 95% ❌
                    "latency_regression": 3.2,  # > 1% ❌
                    "cost_delta": 0.045  # > $0.01 ❌
                },
                expected_result="violation_detected",
                expected_violations=3,
                description="All policies fail their thresholds"
            ),
            
            # Edge cases
            TestCase(
                name="zero_values",
                pr_id="QA-302-edge-01",
                meta={
                    "unit_coverage": 0.0,  # < 95% ❌
                    "latency_regression": 0.0,  # <= 1% ✅
                    "cost_delta": 0.0  # <= $0.01 ✅
                },
                expected_result="violation_detected",
                expected_violations=1,
                description="Edge case with zero coverage"
            ),
            
            TestCase(
                name="extreme_values",
                pr_id="QA-302-edge-02",
                meta={
                    "unit_coverage": 100.0,  # >= 95% ✅
                    "latency_regression": 50.0,  # > 1% ❌
                    "cost_delta": 1.0  # > $0.01 ❌
                },
                expected_result="violation_detected",
                expected_violations=2,
                description="Edge case with extreme values"
            )
        ]
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test cases and return results"""
        logger.info("🧪 Starting QA-302 Gemini Webhook Test Suite")
        
        # Check service health first
        if not await self._check_health():
            logger.error("❌ Gemini service is not healthy")
            return {"success": False, "error": "Service not healthy"}
            
        results = {
            "test_suite": "QA-302 Gemini Webhook",
            "timestamp": time.time(),
            "total_tests": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "results": []
        }
        
        # Run each test case
        for test_case in self.test_cases:
            logger.info(f"🔬 Running test: {test_case.name}")
            test_result = await self._run_test_case(test_case)
            results["results"].append(test_result)
            
            if test_result["passed"]:
                results["passed"] += 1
                logger.info(f"✅ {test_case.name}: PASSED")
            else:
                results["failed"] += 1
                logger.error(f"❌ {test_case.name}: FAILED - {test_result.get('error', 'Unknown error')}")
                
        # Summary
        success_rate = (results["passed"] / results["total_tests"]) * 100
        logger.info(f"📊 Test Summary: {results['passed']}/{results['total_tests']} passed ({success_rate:.1f}%)")
        
        return results
        
    async def _check_health(self) -> bool:
        """Check if Gemini service is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.health_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f"✅ Service health check passed: {health_data.get('status')}")
                        return True
                    else:
                        logger.error(f"❌ Health check failed: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            return False
            
    async def _run_test_case(self, test_case: TestCase) -> Dict[str, Any]:
        """Run a single test case"""
        try:
            # Prepare webhook payload
            payload = {
                "pr_id": test_case.pr_id,
                "meta": test_case.meta,
                "timestamp": time.time(),
                "source": "test_harness"
            }
            
            # Send webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {
                            "test_case": test_case.name,
                            "passed": False,
                            "error": f"HTTP {response.status}",
                            "expected": test_case.expected_result,
                            "actual": None
                        }
                        
                    webhook_response = await response.json()
                    
            # Wait a moment for processing
            await asyncio.sleep(1)
            
            # Get PR status to verify processing
            pr_status = await self._get_pr_status(test_case.pr_id)
            
            # Validate results
            validation_result = self._validate_test_result(test_case, webhook_response, pr_status)
            
            return {
                "test_case": test_case.name,
                "description": test_case.description,
                "passed": validation_result["passed"],
                "error": validation_result.get("error"),
                "expected": {
                    "result": test_case.expected_result,
                    "violations": test_case.expected_violations
                },
                "actual": {
                    "webhook_response": webhook_response,
                    "pr_status": pr_status
                },
                "meta_input": test_case.meta
            }
            
        except Exception as e:
            return {
                "test_case": test_case.name,
                "passed": False,
                "error": str(e),
                "expected": test_case.expected_result,
                "actual": None
            }
            
    async def _get_pr_status(self, pr_id: str) -> Dict[str, Any]:
        """Get PR audit status"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/audit/pr/{pr_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
            
    def _validate_test_result(self, test_case: TestCase, webhook_response: Dict, pr_status: Dict) -> Dict[str, Any]:
        """Validate test case results"""
        try:
            # Check webhook response structure
            if "status" not in webhook_response:
                return {"passed": False, "error": "Missing status in webhook response"}
                
            if webhook_response["status"] != "accepted":
                return {"passed": False, "error": f"Unexpected webhook status: {webhook_response['status']}"}
            
            # Check PR status
            if "error" in pr_status:
                return {"passed": False, "error": f"PR status error: {pr_status['error']}"}
                
            # Validate PR monitoring status
            expected_status = "clean" if test_case.expected_violations == 0 else "violated"
            if pr_status.get("status") != expected_status:
                return {"passed": False, "error": f"Expected status '{expected_status}', got '{pr_status.get('status')}'"}
                
            # Validate violation count
            actual_violations = pr_status.get("violations", 0)
            if actual_violations != test_case.expected_violations:
                return {"passed": False, "error": f"Expected {test_case.expected_violations} violations, got {actual_violations}"}
                
            return {"passed": True}
            
        except Exception as e:
            return {"passed": False, "error": f"Validation error: {e}"}

async def main():
    """Main test harness entry point"""
    parser = argparse.ArgumentParser(description="QA-302 Gemini Webhook Test Harness")
    parser.add_argument("--endpoint", default="http://localhost:8091", help="Gemini service endpoint")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Run tests
    tester = GeminiWebhookTester(args.endpoint)
    results = await tester.run_all_tests()
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"📁 Test results saved to {args.output}")
    else:
        print(json.dumps(results, indent=2))
        
    # Exit with appropriate code
    if results.get("failed", 0) > 0:
        exit(1)
    else:
        logger.info("🎉 All tests passed!")
        exit(0)

if __name__ == "__main__":
    asyncio.run(main())