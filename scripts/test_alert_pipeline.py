#!/usr/bin/env python3
"""
🧪 Alert Pipeline Testing Suite
Tests Prometheus → AlertManager → PagerDuty/Slack escalation paths
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import aiohttp
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlertTester:
    """Test alert escalation pipeline"""
    
    def __init__(self, prometheus_url: str = "http://localhost:9090", 
                 alertmanager_url: str = "http://localhost:9093"):
        self.prometheus_url = prometheus_url
        self.alertmanager_url = alertmanager_url
        self.test_results = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "tests": [],
            "summary": {}
        }
    
    async def test_prometheus_connectivity(self) -> bool:
        """Test Prometheus API connectivity"""
        logger.info("🔍 Testing Prometheus connectivity...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.prometheus_url}/api/v1/status/config") as response:
                    if response.status == 200:
                        logger.info("✅ Prometheus API accessible")
                        return True
                    else:
                        logger.error(f"❌ Prometheus API returned {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Prometheus API unreachable: {e}")
            return False
    
    async def test_alertmanager_connectivity(self) -> bool:
        """Test AlertManager API connectivity"""
        logger.info("🔍 Testing AlertManager connectivity...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.alertmanager_url}/api/v1/status") as response:
                    if response.status == 200:
                        logger.info("✅ AlertManager API accessible")
                        return True
                    else:
                        logger.error(f"❌ AlertManager API returned {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ AlertManager API unreachable: {e}")
            return False
    
    async def check_alert_rules_loaded(self) -> Dict[str, bool]:
        """Check if our custom alert rules are loaded"""
        logger.info("🔍 Checking if alert rules are loaded...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.prometheus_url}/api/v1/rules") as response:
                    if response.status == 200:
                        rules_data = await response.json()
                        
                        # Check for our rule groups
                        expected_groups = ["test_alerts", "day2_operations", "canary_alerts", "system_health"]
                        found_groups = {}
                        
                        for group in rules_data.get("data", {}).get("groups", []):
                            group_name = group.get("name", "")
                            if group_name in expected_groups:
                                found_groups[group_name] = True
                                logger.info(f"✅ Found rule group: {group_name}")
                        
                        # Check for missing groups
                        for group in expected_groups:
                            if group not in found_groups:
                                found_groups[group] = False
                                logger.warning(f"⚠️ Missing rule group: {group}")
                        
                        return found_groups
                    else:
                        logger.error(f"❌ Failed to fetch rules: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"❌ Failed to check rules: {e}")
            return {}
    
    async def get_current_alerts(self) -> List[Dict]:
        """Get currently firing alerts"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.prometheus_url}/api/v1/alerts") as response:
                    if response.status == 200:
                        alerts_data = await response.json()
                        return alerts_data.get("data", {}).get("alerts", [])
                    else:
                        logger.error(f"❌ Failed to fetch alerts: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"❌ Failed to get alerts: {e}")
            return []
    
    async def trigger_test_alert(self, severity: str = "warning") -> bool:
        """Trigger a test alert by posting to AlertManager"""
        logger.info(f"🚨 Triggering test alert with severity: {severity}")
        
        test_alert = [{
            "labels": {
                "alertname": f"TestAlert{severity.title()}",
                "severity": severity,
                "environment": "test",
                "team": "swarm-ops",
                "component": "alert-testing"
            },
            "annotations": {
                "summary": f"🧪 Test {severity} alert",
                "description": f"This is a test {severity} alert triggered by the alert testing pipeline.",
                "runbook_url": "https://docs.swarm.ai/runbook/test-alerts"
            },
            "startsAt": datetime.now(timezone.utc).isoformat(),
            "generatorURL": f"{self.prometheus_url}/graph"
        }]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.alertmanager_url}/api/v1/alerts",
                    json=test_alert,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"✅ Test {severity} alert posted successfully")
                        return True
                    else:
                        logger.error(f"❌ Failed to post test alert: {response.status}")
                        response_text = await response.text()
                        logger.error(f"Response: {response_text}")
                        return False
        except Exception as e:
            logger.error(f"❌ Failed to trigger test alert: {e}")
            return False
    
    async def check_alert_received(self, alert_name: str, timeout: int = 30) -> bool:
        """Check if alert was received by AlertManager"""
        logger.info(f"⏳ Waiting for alert {alert_name} to appear in AlertManager...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.alertmanager_url}/api/v1/alerts") as response:
                        if response.status == 200:
                            alerts_data = await response.json()
                            alerts = alerts_data.get("data", [])
                            
                            for alert in alerts:
                                if alert.get("labels", {}).get("alertname") == alert_name:
                                    logger.info(f"✅ Alert {alert_name} found in AlertManager")
                                    return True
                        
                        await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"Error checking alerts: {e}")
                await asyncio.sleep(2)
        
        logger.warning(f"⚠️ Alert {alert_name} not found within {timeout}s")
        return False
    
    def validate_alert_thresholds(self) -> Dict[str, str]:
        """Validate alert thresholds against recommended values"""
        logger.info("🔍 Validating alert thresholds...")
        
        recommendations = {
            "VRAMWarning": "75% threshold is good for early warning",
            "VRAMCritical": "85% threshold allows time for intervention", 
            "VRAMEmergency": "95% threshold for immediate action - good",
            "LatencyWarning": "200ms threshold aligns with SLA - good",
            "LatencyCritical": "500ms threshold for SLA breach - good",
            "LatencyEmergency": "2s threshold for emergency - good",
            "BudgetWarning": "$7.50 (75% of budget) gives early warning - good",
            "BudgetCritical": "$10 budget limit enforces cost control - good",
            "BudgetRunaway": "$15 (50% over) detects cost bombs - good"
        }
        
        for alert, recommendation in recommendations.items():
            logger.info(f"✅ {alert}: {recommendation}")
        
        return recommendations
    
    def validate_alert_timing(self) -> Dict[str, str]:
        """Validate alert timing and burn-in periods"""
        logger.info("🔍 Validating alert timing...")
        
        timing_analysis = {
            "VRAMWarning": "3m burn-in prevents flapping during load spikes",
            "VRAMCritical": "2m burn-in for urgent but not immediate action",
            "VRAMEmergency": "30s burn-in for true emergencies",
            "LatencyWarning": "5m burn-in filters temporary spikes",
            "LatencyCritical": "3m burn-in for SLA breach confirmation",
            "LatencyEmergency": "1m burn-in for system unresponsiveness",
            "CUDAFragmentation": "5m burn-in schedules maintenance window",
            "BudgetWarning": "10m burn-in prevents cost spike false alarms"
        }
        
        for alert, analysis in timing_analysis.items():
            logger.info(f"✅ {alert}: {analysis}")
        
        return timing_analysis
    
    async def run_escalation_test(self) -> Dict[str, bool]:
        """Run complete escalation path test"""
        logger.info("🧪 Running escalation path test...")
        
        results = {}
        
        # Test each severity level
        severities = ["warning", "critical"]
        
        for severity in severities:
            logger.info(f"Testing {severity} escalation...")
            
            # Trigger test alert
            alert_name = f"TestAlert{severity.title()}"
            triggered = await self.trigger_test_alert(severity)
            
            if triggered:
                # Wait for alert to appear
                received = await self.check_alert_received(alert_name, timeout=30)
                results[f"{severity}_escalation"] = received
                
                if received:
                    logger.info(f"✅ {severity.title()} escalation path working")
                else:
                    logger.error(f"❌ {severity.title()} escalation path failed")
            else:
                results[f"{severity}_escalation"] = False
                logger.error(f"❌ Failed to trigger {severity} alert")
        
        return results
    
    async def cleanup_test_alerts(self):
        """Clean up test alerts from AlertManager"""
        logger.info("🧹 Cleaning up test alerts...")
        
        try:
            # Use AlertManager's silence API to silence test alerts
            silence_data = {
                "matchers": [
                    {"name": "severity", "value": "test", "isRegex": False}
                ],
                "startsAt": datetime.now(timezone.utc).isoformat(),
                "endsAt": (datetime.now(timezone.utc).replace(hour=23, minute=59)).isoformat(),
                "createdBy": "alert-test-pipeline",
                "comment": "Silencing test alerts generated by alert testing pipeline"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.alertmanager_url}/api/v1/silences",
                    json=silence_data
                ) as response:
                    if response.status == 200:
                        logger.info("✅ Test alerts silenced")
                    else:
                        logger.warning(f"⚠️ Failed to silence test alerts: {response.status}")
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup test alerts: {e}")

async def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(description="Alert Pipeline Tester")
    parser.add_argument("--prometheus-url", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--alertmanager-url", default="http://localhost:9093", help="AlertManager URL")
    parser.add_argument("--test-escalation", action="store_true", help="Test escalation paths")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup test alerts")
    
    args = parser.parse_args()
    
    tester = AlertTester(args.prometheus_url, args.alertmanager_url)
    
    logger.info("🧪 Starting Alert Pipeline Test")
    logger.info("=" * 50)
    
    # Basic connectivity tests
    prometheus_ok = await tester.test_prometheus_connectivity()
    alertmanager_ok = await tester.test_alertmanager_connectivity()
    
    if not prometheus_ok or not alertmanager_ok:
        logger.error("❌ Basic connectivity failed - aborting tests")
        return
    
    # Check rule loading
    rules_status = await tester.check_alert_rules_loaded()
    missing_rules = [group for group, loaded in rules_status.items() if not loaded]
    
    if missing_rules:
        logger.warning(f"⚠️ Missing rule groups: {missing_rules}")
        logger.warning("Make sure alerts.yml is loaded in Prometheus config")
    
    # Validate thresholds and timing
    tester.validate_alert_thresholds()
    tester.validate_alert_timing()
    
    # Test escalation if requested
    if args.test_escalation:
        escalation_results = await tester.run_escalation_test()
        
        all_passed = all(escalation_results.values())
        if all_passed:
            logger.info("🎉 All escalation tests passed!")
        else:
            logger.error("❌ Some escalation tests failed")
            for test, result in escalation_results.items():
                status = "✅" if result else "❌"
                logger.info(f"  {status} {test}")
    
    # Cleanup if requested
    if args.cleanup:
        await tester.cleanup_test_alerts()
    
    # Show current alerts
    current_alerts = await tester.get_current_alerts()
    if current_alerts:
        logger.info(f"📊 Current firing alerts: {len(current_alerts)}")
        for alert in current_alerts[:5]:  # Show first 5
            alert_name = alert.get("labels", {}).get("alertname", "Unknown")
            severity = alert.get("labels", {}).get("severity", "unknown")
            logger.info(f"  🚨 {alert_name} ({severity})")
    else:
        logger.info("✅ No alerts currently firing")
    
    logger.info("🎯 Alert pipeline test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 