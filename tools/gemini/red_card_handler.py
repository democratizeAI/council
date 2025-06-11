#!/usr/bin/env python3
"""
QA-302 Red Card Handler
🚫 Automated policy violation enforcement for Gemini audit failures

Handles red card issuance, rollback triggering, and notification management
when property-based tests detect policy violations in PR meta bundles.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RedCardViolation:
    """Individual policy violation details"""
    field_name: str
    actual_value: Any
    expected_range: str
    violation_type: str
    severity: str  # "low", "medium", "high", "critical"
    reproduction_seed: Optional[int] = None

@dataclass
class RedCardEvent:
    """Complete red card event with all context"""
    event_id: str
    pr_number: str
    pr_title: str
    pr_author: str
    timestamp: str
    violations: List[RedCardViolation]
    audit_source: str  # "qa-300-routing", "direct-audit", "property-fuzz"
    rollback_triggered: bool
    comment_posted: bool
    metrics_pushed: bool
    notification_sent: bool

class RedCardHandler:
    """Handles red card issuance and enforcement for Gemini audit violations"""
    
    def __init__(self, github_token: str = None, slack_webhook: str = None):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.slack_webhook = slack_webhook or os.getenv('SLACK_GEMINI_WEBHOOK')
        self.audit_api = os.getenv('AUDIT_LOG_API')
        self.audit_token = os.getenv('AUDIT_TOKEN')
        self.prometheus_gateway = os.getenv('PROMETHEUS_GATEWAY', 'http://prometheus-pushgateway:9091')
        
        self.red_card_history = []
        self.violation_patterns = {}
        
    def classify_violation_severity(self, violation: Dict[str, Any]) -> str:
        """Classify violation severity based on field and impact"""
        field_name = violation.get('field_name', '')
        actual_value = violation.get('actual_value', 0)
        violation_type = violation.get('violation_type', '')
        
        # Coverage violations
        if field_name == 'unit_coverage':
            if actual_value < 50:
                return "critical"  # Very low coverage
            elif actual_value < 80:
                return "high"     # Below acceptable
            elif actual_value < 95:
                return "medium"   # Below target
            else:
                return "low"      # Minor deviation
        
        # Latency violations
        elif field_name == 'latency_regression':
            if actual_value > 5.0:
                return "critical"  # Severe regression
            elif actual_value > 2.0:
                return "high"     # Significant regression
            elif actual_value > 1.0:
                return "medium"   # Above threshold
            else:
                return "low"      # Minor regression
        
        # Cost violations
        elif field_name == 'cost_delta':
            abs_value = abs(actual_value)
            if abs_value > 0.1:
                return "critical"  # Major cost impact
            elif abs_value > 0.05:
                return "high"     # Significant cost increase
            elif abs_value > 0.01:
                return "medium"   # Above threshold
            else:
                return "low"      # Minor cost change
        
        return "medium"  # Default severity

    def create_red_card_violations(self, audit_result: Dict[str, Any]) -> List[RedCardViolation]:
        """Convert audit result assertions into red card violations"""
        violations = []
        
        for assertion in audit_result.get('assertions', []):
            if not assertion.get('assertion_result', True):
                violation = RedCardViolation(
                    field_name=assertion['field_name'],
                    actual_value=assertion['value'],
                    expected_range=assertion['expected_range'],
                    violation_type=assertion['violation_type'],
                    severity=self.classify_violation_severity(assertion),
                    reproduction_seed=assertion.get('reproduction_seed')
                )
                violations.append(violation)
        
        return violations

    def generate_red_card_comment(self, event: RedCardEvent) -> str:
        """Generate comprehensive red card comment for GitHub PR"""
        comment = f"""🚫 **Gemini Policy Violation (property-fuzzed)**

**Event ID**: `{event.event_id}`
**PR**: #{event.pr_number} - {event.pr_title}
**Author**: @{event.pr_author}
**Audit Source**: {event.audit_source}
**Timestamp**: {event.timestamp}

---

## 🚨 Policy Violations Detected

"""
        
        # Group violations by severity
        violations_by_severity = {}
        for violation in event.violations:
            severity = violation.severity
            if severity not in violations_by_severity:
                violations_by_severity[severity] = []
            violations_by_severity[severity].append(violation)
        
        # Display violations by severity (critical first)
        severity_order = ['critical', 'high', 'medium', 'low']
        severity_emojis = {
            'critical': '🔴',
            'high': '🟠', 
            'medium': '🟡',
            'low': '⚪'
        }
        
        for severity in severity_order:
            if severity in violations_by_severity:
                violations = violations_by_severity[severity]
                comment += f"### {severity_emojis[severity]} {severity.upper()} Severity\n\n"
                
                for violation in violations:
                    comment += f"- **{violation.field_name}**: `{violation.actual_value}` (expected: {violation.expected_range})\n"
                    comment += f"  - **Violation**: {violation.violation_type}\n"
                    if violation.reproduction_seed:
                        comment += f"  - **Reproduction Seed**: `{violation.reproduction_seed}`\n"
                    comment += "\n"
        
        # Reproduction instructions
        comment += "---\n\n## 🔍 Reproduction Instructions\n\n"
        
        seeds = [v.reproduction_seed for v in event.violations if v.reproduction_seed]
        if seeds:
            comment += "```bash\n"
            comment += "# Reproduce these specific failures:\n"
            for seed in seeds:
                comment += f"hypothesis reproduce {seed}\n"
            comment += "\n# Run full property test suite:\n"
            comment += "python -m pytest tests/test_meta_assertions_property.py -v --hypothesis-show-statistics\n"
            comment += "```\n\n"
        
        # Required actions
        comment += "---\n\n## ⚠️ Required Actions\n\n"
        comment += "1. 🛑 **ROLLBACK TRIGGERED** - PR is blocked from merge\n"
        comment += "2. 🔍 **Review Violations** - Address each policy violation above\n"
        comment += "3. 🧪 **Test Locally** - Reproduce and fix issues using seeds provided\n"
        comment += "4. 📊 **Verify Meta** - Ensure PR meta fields are within policy bounds\n"
        comment += "5. 🔄 **Re-submit** - Push fixes and re-trigger audit\n\n"
        
        # Emergency rollback instructions
        comment += "---\n\n## 🚨 Emergency Rollback\n\n"
        comment += "If this is urgent and violations are acceptable:\n\n"
        comment += "```bash\n"
        comment += "# Apply emergency bypass label:\n"
        comment += f'gh pr edit {event.pr_number} --add-label "rollback: gemini-skip"\n'
        comment += "\n# Or revert to last known good state:\n"
        comment += "git checkout HEAD~1\n"
        comment += "```\n\n"
        
        # Audit metadata
        comment += "---\n\n## 📋 Audit Metadata\n\n"
        comment += f"- **Event ID**: `{event.event_id}`\n"
        comment += f"- **Audit Timestamp**: {event.timestamp}\n"
        comment += f"- **Source**: {event.audit_source}\n"
        comment += f"- **Violations Count**: {len(event.violations)}\n"
        comment += f"- **Highest Severity**: {max([v.severity for v in event.violations], key=lambda x: severity_order.index(x))}\n"
        comment += f"\n*Generated by QA-302 Streaming Auditor*\n"
        
        return comment

    def post_github_comment(self, pr_number: str, comment: str) -> bool:
        """Post red card comment to GitHub PR"""
        if not self.github_token:
            logger.warning("No GitHub token available, skipping comment")
            return False
        
        try:
            # Get repository info from environment
            repo = os.getenv('GITHUB_REPOSITORY', 'autogencouncil/enterprise-swarm')
            
            url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            data = {
                'body': comment
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            logger.info(f"Red card comment posted to PR #{pr_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post GitHub comment: {e}")
            return False

    def trigger_rollback(self, pr_number: str, event_id: str) -> bool:
        """Trigger rollback enforcement for the PR"""
        try:
            # Block PR from merge using GitHub API
            repo = os.getenv('GITHUB_REPOSITORY', 'autogencouncil/enterprise-swarm')
            
            # Convert PR to draft to prevent merge
            url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            data = {'draft': True}
            response = requests.patch(url, headers=headers, json=data)
            
            if response.status_code == 200:
                logger.info(f"PR #{pr_number} converted to draft (rollback triggered)")
                return True
            else:
                logger.warning(f"Failed to convert PR to draft: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to trigger rollback: {e}")
            return False

    def push_metrics(self, event: RedCardEvent) -> bool:
        """Push red card metrics to Prometheus"""
        try:
            metrics = []
            
            # Red card event counter
            metrics.append(f'gemini_red_card_events_total{{pr="{event.pr_number}",source="{event.audit_source}"}} 1')
            
            # Violation counts by field and severity
            for violation in event.violations:
                metrics.append(f'gemini_violations_total{{field="{violation.field_name}",severity="{violation.severity}"}} 1')
            
            # Rollback events
            if event.rollback_triggered:
                metrics.append(f'gemini_rollbacks_total{{pr="{event.pr_number}"}} 1')
            
            # Timestamp
            metrics.append(f'gemini_red_card_timestamp {int(datetime.now().timestamp())}')
            
            # Push to Prometheus pushgateway
            url = f"{self.prometheus_gateway}/metrics/job/gemini-red-card/instance/{event.event_id}"
            
            metrics_text = '\n'.join(metrics) + '\n'
            
            response = requests.post(
                url,
                data=metrics_text,
                headers={'Content-Type': 'text/plain'}
            )
            response.raise_for_status()
            
            logger.info(f"Red card metrics pushed for event {event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to push metrics: {e}")
            return False

    def send_slack_notification(self, event: RedCardEvent) -> bool:
        """Send Slack notification for red card event"""
        if not self.slack_webhook:
            logger.warning("No Slack webhook configured, skipping notification")
            return False
        
        try:
            # Determine color based on highest severity
            severity_colors = {
                'critical': '#FF0000',  # Red
                'high': '#FF8000',      # Orange
                'medium': '#FFFF00',    # Yellow
                'low': '#FFFFFF'        # White
            }
            
            highest_severity = max([v.severity for v in event.violations], 
                                 key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
            color = severity_colors.get(highest_severity, '#FFFF00')
            
            # Create Slack message
            message = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚫 Gemini Red Card Issued - PR #{event.pr_number}",
                        "title_link": f"https://github.com/autogencouncil/enterprise-swarm/pull/{event.pr_number}",
                        "text": f"Policy violations detected in {event.pr_title}",
                        "fields": [
                            {
                                "title": "Author",
                                "value": event.pr_author,
                                "short": True
                            },
                            {
                                "title": "Violations",
                                "value": str(len(event.violations)),
                                "short": True
                            },
                            {
                                "title": "Highest Severity",
                                "value": highest_severity.upper(),
                                "short": True
                            },
                            {
                                "title": "Audit Source",
                                "value": event.audit_source,
                                "short": True
                            }
                        ],
                        "footer": "QA-302 Streaming Auditor",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook, json=message)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent for red card {event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def log_audit_event(self, event: RedCardEvent) -> bool:
        """Log red card event to audit system"""
        if not self.audit_api or not self.audit_token:
            logger.warning("No audit API configured, skipping audit log")
            return False
        
        try:
            audit_data = {
                "event_type": "gemini_red_card_issued",
                "event_id": event.event_id,
                "pr_number": event.pr_number,
                "pr_author": event.pr_author,
                "timestamp": event.timestamp,
                "violations": [asdict(v) for v in event.violations],
                "audit_source": event.audit_source,
                "rollback_triggered": event.rollback_triggered,
                "security_classification": "audit_enforcement"
            }
            
            headers = {
                'Authorization': f'Bearer {self.audit_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.audit_api}/gemini-red-card",
                json=audit_data,
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"Audit event logged for red card {event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    def issue_red_card(self, audit_result: Dict[str, Any], pr_info: Dict[str, Any]) -> RedCardEvent:
        """Issue a complete red card for audit violations"""
        # Create event ID
        event_id = f"RC-{datetime.now().strftime('%Y%m%d')}-{int(time.time() * 1000) % 100000:05d}"
        
        # Create violations
        violations = self.create_red_card_violations(audit_result)
        
        # Create red card event
        event = RedCardEvent(
            event_id=event_id,
            pr_number=pr_info.get('number', 'unknown'),
            pr_title=pr_info.get('title', 'Unknown PR'),
            pr_author=pr_info.get('author', 'unknown'),
            timestamp=datetime.now().isoformat(),
            violations=violations,
            audit_source=audit_result.get('audit_source', 'property-fuzz'),
            rollback_triggered=audit_result.get('rollback_triggered', True),
            comment_posted=False,
            metrics_pushed=False,
            notification_sent=False
        )
        
        logger.info(f"Issuing red card {event_id} for PR #{event.pr_number}")
        
        # Execute red card actions
        try:
            # 1. Generate and post GitHub comment
            comment = self.generate_red_card_comment(event)
            event.comment_posted = self.post_github_comment(event.pr_number, comment)
            
            # 2. Trigger rollback enforcement
            if event.rollback_triggered:
                self.trigger_rollback(event.pr_number, event_id)
            
            # 3. Push metrics
            event.metrics_pushed = self.push_metrics(event)
            
            # 4. Send notifications
            event.notification_sent = self.send_slack_notification(event)
            
            # 5. Log audit event
            self.log_audit_event(event)
            
            # 6. Add to history
            self.red_card_history.append(event)
            
            logger.info(f"Red card {event_id} fully processed")
            
        except Exception as e:
            logger.error(f"Error processing red card {event_id}: {e}")
        
        return event

    def get_red_card_stats(self) -> Dict[str, Any]:
        """Get red card statistics"""
        total_cards = len(self.red_card_history)
        
        if total_cards == 0:
            return {
                'total_red_cards': 0,
                'successful_posts': 0,
                'rollbacks_triggered': 0,
                'most_common_violation': None
            }
        
        successful_posts = len([e for e in self.red_card_history if e.comment_posted])
        rollbacks = len([e for e in self.red_card_history if e.rollback_triggered])
        
        # Find most common violation type
        violation_counts = {}
        for event in self.red_card_history:
            for violation in event.violations:
                violation_type = violation.violation_type
                violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1
        
        most_common = max(violation_counts.items(), key=lambda x: x[1])[0] if violation_counts else None
        
        return {
            'total_red_cards': total_cards,
            'successful_posts': successful_posts,
            'rollbacks_triggered': rollbacks,
            'most_common_violation': most_common,
            'violation_distribution': violation_counts
        }

def main():
    """CLI interface for red card handler testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QA-302 Red Card Handler")
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode')
    parser.add_argument('--pr-number', help='PR number for testing')
    parser.add_argument('--audit-result', help='JSON file with audit result')
    
    args = parser.parse_args()
    
    handler = RedCardHandler()
    
    if args.test_mode:
        # Test mode - create sample red card
        sample_audit = {
            'audit_source': 'test-mode',
            'rollback_triggered': True,
            'assertions': [
                {
                    'field_name': 'unit_coverage',
                    'value': 75,
                    'expected_range': '[95, 100]',
                    'assertion_result': False,
                    'violation_type': 'coverage_below_threshold',
                    'reproduction_seed': 12345
                }
            ]
        }
        
        sample_pr = {
            'number': args.pr_number or 'TEST-123',
            'title': 'Test PR for Red Card Handler',
            'author': 'test-user'
        }
        
        event = handler.issue_red_card(sample_audit, sample_pr)
        
        print(f"🚫 Red card issued: {event.event_id}")
        print(f"Comment posted: {event.comment_posted}")
        print(f"Metrics pushed: {event.metrics_pushed}")
        print(f"Notification sent: {event.notification_sent}")
        
    else:
        print("🛡️ Red Card Handler ready for production use")
        stats = handler.get_red_card_stats()
        print(f"Stats: {stats}")

if __name__ == "__main__":
    main() 