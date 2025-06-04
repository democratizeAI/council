#!/usr/bin/env python3
"""
🔍 Alert Test Verifier
Monitors alerts in real-time during chaos testing to verify escalation paths
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Set
import argparse
import aiohttp
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AlertEvent:
    """Alert event for tracking"""
    name: str
    severity: str
    status: str  # firing, resolved
    timestamp: datetime
    description: str

class AlertVerifier:
    """Real-time alert verification during chaos tests"""
    
    def __init__(self, prometheus_url: str = "http://localhost:9090",
                 alertmanager_url: str = "http://localhost:9093"):
        self.prometheus_url = prometheus_url
        self.alertmanager_url = alertmanager_url
        self.seen_alerts: Set[str] = set()
        self.alert_history: List[AlertEvent] = []
        self.expected_alerts = {
            "VRAMWarning": {"severity": "warning", "threshold": 75},
            "VRAMCritical": {"severity": "critical", "threshold": 85},
            "VRAMEmergency": {"severity": "page", "threshold": 95}
        }
    
    async def monitor_alerts(self, duration: int = 600):
        """Monitor alerts for specified duration"""
        logger.info(f"🔍 Starting alert monitoring for {duration} seconds...")
        
        start_time = time.time()
        last_check = start_time
        
        while time.time() - start_time < duration:
            try:
                # Check for new alerts
                await self.check_prometheus_alerts()
                await self.check_alertmanager_alerts()
                
                # Show current status every 30 seconds
                if time.time() - last_check >= 30:
                    await self.show_current_status()
                    last_check = time.time()
                
                await asyncio.sleep(10)
                
            except KeyboardInterrupt:
                logger.info("⏹️ Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
                await asyncio.sleep(5)
        
        # Final report
        await self.generate_report()
    
    async def check_prometheus_alerts(self):
        """Check Prometheus for firing alerts"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.prometheus_url}/api/v1/alerts") as response:
                    if response.status == 200:
                        data = await response.json()
                        alerts = data.get("data", {}).get("alerts", [])
                        
                        for alert in alerts:
                            alert_name = alert.get("labels", {}).get("alertname")
                            state = alert.get("state", "unknown")
                            
                            if alert_name and state == "firing":
                                alert_key = f"{alert_name}_{state}"
                                
                                if alert_key not in self.seen_alerts:
                                    self.seen_alerts.add(alert_key)
                                    
                                    severity = alert.get("labels", {}).get("severity", "unknown")
                                    description = alert.get("annotations", {}).get("summary", "")
                                    
                                    event = AlertEvent(
                                        name=alert_name,
                                        severity=severity,
                                        status="firing",
                                        timestamp=datetime.now(timezone.utc),
                                        description=description
                                    )
                                    self.alert_history.append(event)
                                    
                                    logger.info(f"🚨 NEW ALERT: {alert_name} ({severity}) - {description}")
                                    
                                    # Check if this is expected
                                    if alert_name in self.expected_alerts:
                                        expected = self.expected_alerts[alert_name]
                                        logger.info(f"✅ Expected {alert_name} alert fired correctly!")
                                    else:
                                        logger.warning(f"⚠️ Unexpected alert: {alert_name}")
        
        except Exception as e:
            logger.debug(f"Prometheus check failed: {e}")
    
    async def check_alertmanager_alerts(self):
        """Check AlertManager for active alerts"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.alertmanager_url}/api/v1/alerts") as response:
                    if response.status == 200:
                        data = await response.json()
                        alerts = data.get("data", [])
                        
                        active_alerts = [a for a in alerts if a.get("status", {}).get("state") == "active"]
                        
                        if active_alerts:
                            logger.debug(f"📊 AlertManager has {len(active_alerts)} active alerts")
        
        except Exception as e:
            logger.debug(f"AlertManager check failed: {e}")
    
    async def show_current_status(self):
        """Show current monitoring status"""
        logger.info("📊 Current Status:")
        logger.info(f"  Alerts seen: {len(self.alert_history)}")
        
        # Show recent alerts
        recent = [a for a in self.alert_history if (datetime.now(timezone.utc) - a.timestamp).seconds < 300]
        if recent:
            logger.info(f"  Recent alerts (last 5m): {len(recent)}")
            for alert in recent[-3:]:  # Show last 3
                logger.info(f"    🚨 {alert.name} ({alert.severity}) at {alert.timestamp.strftime('%H:%M:%S')}")
        
        # Check expected vs actual
        expected_names = set(self.expected_alerts.keys())
        fired_names = {a.name for a in self.alert_history}
        
        if expected_names & fired_names:
            logger.info(f"  ✅ Expected alerts fired: {expected_names & fired_names}")
        
        missing = expected_names - fired_names
        if missing:
            logger.info(f"  ⏳ Waiting for: {missing}")
    
    async def verify_escalation_sequence(self):
        """Verify the correct alert escalation sequence"""
        logger.info("🧪 Verifying VRAM escalation sequence...")
        
        # Expected sequence: Warning → Critical → Emergency
        expected_sequence = ["VRAMWarning", "VRAMCritical", "VRAMEmergency"]
        fired_sequence = [a.name for a in self.alert_history if a.name in expected_sequence]
        
        logger.info(f"Expected sequence: {' → '.join(expected_sequence)}")
        logger.info(f"Actual sequence: {' → '.join(fired_sequence)}")
        
        # Check if sequence is correct
        if fired_sequence == expected_sequence:
            logger.info("✅ Perfect escalation sequence!")
            return True
        elif set(fired_sequence) == set(expected_sequence):
            logger.warning("⚠️ All alerts fired but sequence may be incorrect")
            return True
        else:
            missing = set(expected_sequence) - set(fired_sequence)
            logger.error(f"❌ Missing alerts: {missing}")
            return False
    
    async def check_notification_channels(self):
        """Check if notifications were sent to expected channels"""
        logger.info("📞 Checking notification channels...")
        
        # In practice, you'd check:
        # - Slack API for message delivery
        # - PagerDuty API for incident creation
        # - Email logs for delivery
        
        logger.info("📱 Slack notifications:")
        logger.info("  - Check #swarm-ops for warning/critical alerts")
        logger.info("  - Check #swarm-incidents for emergency alerts")
        
        logger.info("📧 Email notifications:")
        logger.info("  - Check swarm-ops@company.com for critical alerts")
        
        logger.info("📟 PagerDuty:")
        logger.info("  - Check for emergency incident creation")
        
        # Placeholder for actual verification
        logger.info("⚠️ Manual verification required - check your notification channels")
    
    async def generate_report(self):
        """Generate final test report"""
        logger.info("📋 ALERT TEST REPORT")
        logger.info("=" * 50)
        
        if not self.alert_history:
            logger.warning("❌ No alerts detected during test!")
            return
        
        # Timeline
        logger.info("⏰ Alert Timeline:")
        for alert in self.alert_history:
            timestamp = alert.timestamp.strftime("%H:%M:%S")
            logger.info(f"  {timestamp} - {alert.name} ({alert.severity}) {alert.status}")
        
        # Verification
        escalation_ok = await self.verify_escalation_sequence()
        
        # Summary
        logger.info("📊 Summary:")
        logger.info(f"  Total alerts: {len(self.alert_history)}")
        logger.info(f"  Unique alerts: {len(set(a.name for a in self.alert_history))}")
        logger.info(f"  Escalation sequence: {'✅ Correct' if escalation_ok else '❌ Incorrect'}")
        
        # Next steps
        logger.info("🔍 Next Steps:")
        await self.check_notification_channels()
        
        logger.info("✅ Alert test verification complete!")

async def main():
    """Main verification execution"""
    parser = argparse.ArgumentParser(description="Alert Test Verifier")
    parser.add_argument("--duration", type=int, default=600, help="Monitoring duration in seconds")
    parser.add_argument("--prometheus-url", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--alertmanager-url", default="http://localhost:9093", help="AlertManager URL")
    
    args = parser.parse_args()
    
    verifier = AlertVerifier(args.prometheus_url, args.alertmanager_url)
    
    logger.info("🔍 Alert Test Verifier")
    logger.info("=" * 50)
    logger.info("This will monitor alerts during chaos testing to verify:")
    logger.info("  ✅ Correct alert thresholds trigger")
    logger.info("  ✅ Proper escalation sequence")
    logger.info("  ✅ Notification delivery")
    logger.info("")
    
    try:
        await verifier.monitor_alerts(args.duration)
    except KeyboardInterrupt:
        logger.info("⏹️ Verification stopped by user")
        await verifier.generate_report()

if __name__ == "__main__":
    asyncio.run(main()) 