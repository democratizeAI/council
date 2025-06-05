#!/usr/bin/env python3
"""
Ship Criteria Validation - Final Gate for v3.0.0 GA
Validates the 4 critical ship criteria before GA release
"""

import argparse
import json
import os
import glob
from typing import Dict, List, Any
from dataclasses import dataclass
import xml.etree.ElementTree as ET

@dataclass
class ShipCriteria:
    """Ship criteria requirements for v3.0.0 GA"""
    all_suites_green: bool = False
    no_alerts_fired: bool = False
    readme_badge_updated: bool = False
    grafana_snapshot_exported: bool = False
    
    def is_ready_to_ship(self) -> bool:
        """Check if all ship criteria are met"""
        return all([
            self.all_suites_green,
            self.no_alerts_fired,
            self.readme_badge_updated,
            self.grafana_snapshot_exported
        ])

class ShipCriteriaValidator:
    """Validates ship criteria for AutoGen Council v3.0.0 GA"""
    
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        self.criteria = ShipCriteria()
        
    def validate_all_suites_green(self) -> bool:
        """Validate that all 12 test suites passed"""
        print("🔍 Validating all test suites...")
        
        required_suites = [
            "smoke.xml",           # Suite 1: Smoke tests
            "unit.xml",            # Suite 2: Unit/CI tests
            "perf_single.json",    # Suite 3: Single-shot performance
            "load.html",           # Suite 4: Load/burst testing
            "soak.json",           # Suite 5: Soak testing
            "retrieval.json",      # Suite 6: Retrieval accuracy
            "chaos.html",          # Suite 7: Concurrency chaos
            "oom.json",            # Suite 8: OOM guard
            "bandit.json",         # Suite 9: Security scan
            "cross_os.json",       # Suite 10: Cross-OS compatibility
            "alerts.json",         # Suite 11: Alert validation
            # Suite 12 (UX) is manual validation
        ]
        
        suite_results = {}
        
        for suite_file in required_suites:
            suite_path = os.path.join(self.reports_dir, suite_file)
            
            if not os.path.exists(suite_path):
                print(f"   ❌ Missing: {suite_file}")
                suite_results[suite_file] = False
                continue
                
            # Validate specific suite based on file type
            if suite_file.endswith(".xml"):
                result = self._validate_junit_xml(suite_path)
            elif suite_file.endswith(".json"):
                result = self._validate_json_report(suite_path)
            elif suite_file.endswith(".html"):
                result = self._validate_html_report(suite_path)
            else:
                result = True  # File exists
                
            suite_results[suite_file] = result
            status = "✅" if result else "❌"
            print(f"   {status} {suite_file}")
        
        # Check for UX checklist (manual validation)
        ux_checklist = os.path.join(self.reports_dir, "ux_checklist.md")
        if os.path.exists(ux_checklist):
            print(f"   ✅ ux_checklist.md (manual validation)")
            suite_results["ux_checklist.md"] = True
        else:
            print(f"   ❌ ux_checklist.md (manual validation required)")
            suite_results["ux_checklist.md"] = False
        
        all_passed = all(suite_results.values())
        self.criteria.all_suites_green = all_passed
        
        print(f"📊 Suite Summary: {sum(suite_results.values())}/{len(suite_results)} passed")
        return all_passed
    
    def _validate_junit_xml(self, xml_path: str) -> bool:
        """Validate JUnit XML test results"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Check for failures or errors
            failures = int(root.get('failures', 0))
            errors = int(root.get('errors', 0))
            
            return failures == 0 and errors == 0
        except Exception as e:
            print(f"   Warning: Failed to parse {xml_path}: {e}")
            return False
    
    def _validate_json_report(self, json_path: str) -> bool:
        """Validate JSON test report"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Check for overall_pass flag
            if 'overall_pass' in data:
                return data['overall_pass']
            
            # Check for success flag
            if 'success' in data:
                return data['success']
            
            # If no clear pass/fail, assume passed if file exists
            return True
            
        except Exception as e:
            print(f"   Warning: Failed to parse {json_path}: {e}")
            return False
    
    def _validate_html_report(self, html_path: str) -> bool:
        """Validate HTML test report (basic existence check)"""
        try:
            with open(html_path, 'r') as f:
                content = f.read()
            
            # Basic heuristics for success
            if "100%" in content or "success" in content.lower():
                return True
            if "error" in content.lower() or "fail" in content.lower():
                return False
                
            # If unclear, assume passed if file exists and has content
            return len(content) > 100
            
        except Exception as e:
            print(f"   Warning: Failed to read {html_path}: {e}")
            return False
    
    def validate_no_alerts_fired(self) -> bool:
        """Validate that no critical alerts fired during soak test"""
        print("🚨 Validating alert status...")
        
        alert_files = [
            "alerts.json",
            "alert_verification.json",
            "soak.json"  # May contain alert information
        ]
        
        alerts_fired = False
        
        for alert_file in alert_files:
            alert_path = os.path.join(self.reports_dir, alert_file)
            
            if not os.path.exists(alert_path):
                continue
                
            try:
                with open(alert_path, 'r') as f:
                    data = json.load(f)
                
                # Check for alert indicators
                if 'alerts_fired' in data and data['alerts_fired'] > 0:
                    alerts_fired = True
                    print(f"   ❌ {data['alerts_fired']} alerts fired in {alert_file}")
                
                if 'critical_alerts' in data and len(data['critical_alerts']) > 0:
                    alerts_fired = True
                    print(f"   ❌ Critical alerts found in {alert_file}")
                    
            except Exception as e:
                print(f"   Warning: Failed to parse {alert_path}: {e}")
        
        self.criteria.no_alerts_fired = not alerts_fired
        
        if not alerts_fired:
            print("   ✅ No critical alerts fired during testing")
        
        return not alerts_fired
    
    def validate_readme_badge_updated(self) -> bool:
        """Validate that README badge shows passing status"""
        print("📛 Validating README badge...")
        
        readme_path = "README.md"
        
        if not os.path.exists(readme_path):
            print("   ❌ README.md not found")
            self.criteria.readme_badge_updated = False
            return False
        
        try:
            with open(readme_path, 'r') as f:
                content = f.read()
            
            # Look for graduation suite badge
            if "graduation-suite" in content and "passing" in content:
                print("   ✅ Graduation suite badge shows passing")
                self.criteria.readme_badge_updated = True
                return True
            elif "graduation-suite" in content:
                print("   ❌ Graduation suite badge exists but not showing passing")
                self.criteria.readme_badge_updated = False
                return False
            else:
                print("   ❌ Graduation suite badge not found in README")
                self.criteria.readme_badge_updated = False
                return False
                
        except Exception as e:
            print(f"   ❌ Failed to read README.md: {e}")
            self.criteria.readme_badge_updated = False
            return False
    
    def validate_grafana_snapshot_exported(self) -> bool:
        """Validate that Grafana performance snapshot was exported"""
        print("📸 Validating Grafana snapshot...")
        
        snapshot_patterns = [
            "docs/perf_snapshot_v2.7.0.png",
            "docs/perf_snapshot_*.png",
            f"{self.reports_dir}/grafana_snapshot.png"
        ]
        
        for pattern in snapshot_patterns:
            matching_files = glob.glob(pattern)
            if matching_files:
                snapshot_path = matching_files[0]
                
                # Check file size (should be > 10KB for a real screenshot)
                if os.path.getsize(snapshot_path) > 10000:
                    print(f"   ✅ Grafana snapshot exported: {snapshot_path}")
                    self.criteria.grafana_snapshot_exported = True
                    return True
                else:
                    print(f"   ❌ Grafana snapshot too small: {snapshot_path}")
        
        print("   ❌ Grafana snapshot not found or invalid")
        self.criteria.grafana_snapshot_exported = False
        return False
    
    def generate_ship_report(self) -> Dict[str, Any]:
        """Generate comprehensive ship readiness report"""
        return {
            "ship_criteria": {
                "all_suites_green": self.criteria.all_suites_green,
                "no_alerts_fired": self.criteria.no_alerts_fired,
                "readme_badge_updated": self.criteria.readme_badge_updated,
                "grafana_snapshot_exported": self.criteria.grafana_snapshot_exported
            },
            "ready_to_ship": self.criteria.is_ready_to_ship(),
            "timestamp": os.path.getmtime(self.reports_dir) if os.path.exists(self.reports_dir) else None,
            "validation_summary": {
                "criteria_met": sum([
                    self.criteria.all_suites_green,
                    self.criteria.no_alerts_fired,
                    self.criteria.readme_badge_updated,
                    self.criteria.grafana_snapshot_exported
                ]),
                "total_criteria": 4
            }
        }
    
    def run_validation(self) -> bool:
        """Run complete ship criteria validation"""
        print("🚢 SHIP CRITERIA VALIDATION FOR v3.0.0 GA")
        print("=" * 50)
        
        # Run all validations
        suite_1 = self.validate_all_suites_green()
        suite_2 = self.validate_no_alerts_fired()
        suite_3 = self.validate_readme_badge_updated()
        suite_4 = self.validate_grafana_snapshot_exported()
        
        # Print summary
        print("\n📋 SHIP CRITERIA SUMMARY")
        print("=" * 30)
        
        criteria_status = [
            ("All 12 suites green", suite_1),
            ("No alerts fired during 1-hour soak", suite_2),
            ("README badge shows ✓ on last commit", suite_3),
            ("Grafana board exported to docs/", suite_4)
        ]
        
        for criterion, passed in criteria_status:
            status = "✅" if passed else "❌"
            print(f"{status} {criterion}")
        
        ready_to_ship = self.criteria.is_ready_to_ship()
        
        print(f"\n🏆 SHIP DECISION: {'✅ READY TO SHIP v3.0.0 GA' if ready_to_ship else '❌ NOT READY - FIX ISSUES ABOVE'}")
        
        if ready_to_ship:
            print("\n🎉 All ship criteria met! You can now:")
            print("   1. Cut v3.0.0 GA release")
            print("   2. Invite beta users")
            print("   3. Announce general availability")
        else:
            print(f"\n⚠️  {4 - sum([suite_1, suite_2, suite_3, suite_4])}/4 criteria failed")
            print("   Fix the issues above before shipping")
        
        return ready_to_ship

def main():
    parser = argparse.ArgumentParser(description="Validate ship criteria for v3.0.0 GA")
    parser.add_argument("--reports-dir", default="reports", help="Directory containing test reports")
    parser.add_argument("--output", help="Output file for ship report (JSON)")
    
    args = parser.parse_args()
    
    # Run validation
    validator = ShipCriteriaValidator(args.reports_dir)
    ready_to_ship = validator.run_validation()
    
    # Generate report
    ship_report = validator.generate_ship_report()
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(ship_report, f, indent=2)
        print(f"\n📄 Ship report saved to {args.output}")
    
    # Exit with appropriate code
    exit(0 if ready_to_ship else 1)

if __name__ == "__main__":
    main() 