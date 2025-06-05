#!/usr/bin/env python3
"""
💰 Cost Guardrail for CI/CD
Prevents cost regression in automated testing - fails PR if cost drifts
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

def load_latest_titanic_report(reports_dir: str = "reports") -> Dict[str, Any]:
    """Load the most recent Titanic report"""
    
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        raise FileNotFoundError(f"Reports directory not found: {reports_dir}")
    
    # Find the latest Titanic report, excluding complete gauntlet files
    titanic_files = [
        f for f in reports_path.glob("autogen_titanic*.json") 
        if "complete" not in f.name and "gauntlet_complete" not in f.name
    ]
    
    # Fallback to any titanic files if no autogen ones found
    if not titanic_files:
        titanic_files = [
            f for f in reports_path.glob("*titanic*.json") 
            if "complete" not in f.name and "gauntlet_complete" not in f.name
        ]
    
    if not titanic_files:
        raise FileNotFoundError("No Titanic reports found")
    
    # Sort by modification time, get latest
    latest_file = max(titanic_files, key=lambda f: f.stat().st_mtime)
    print(f"📁 Loading: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        return json.load(f)

def extract_cost_metrics(report: Dict[str, Any]) -> Dict[str, float]:
    """Extract cost metrics from report"""
    
    metrics = {
        'avg_cost_usd': None,
        'total_cost_usd': None,
        'cost_per_request': None
    }
    
    print(f"🔍 DEBUG: Report keys: {list(report.keys())}")
    
    # Handle nested report structure (gauntlet format)
    if 'report' in report and isinstance(report['report'], dict):
        print("🔍 DEBUG: Found nested report structure")
        report = report['report']
        print(f"🔍 DEBUG: Nested report keys: {list(report.keys())}")
    
    # Performance section (newer format)
    if 'performance' in report:
        perf = report['performance']
        print(f"🔍 DEBUG: Performance section found: {perf}")
        metrics['total_cost_usd'] = perf.get('total_cost_usd', 0.0)
        metrics['avg_cost_usd'] = metrics['total_cost_usd']  # Same thing for runs
        
        # Calculate per-request cost
        completed = report.get('metadata', {}).get('completed_requests', 1)
        print(f"🔍 DEBUG: Completed requests: {completed}")
        if completed > 0:
            metrics['cost_per_request'] = metrics['total_cost_usd'] / completed
    
    # Metadata format
    if 'metadata' in report and metrics['total_cost_usd'] is None:
        meta = report['metadata']
        print(f"🔍 DEBUG: Metadata section found: {meta}")
        metrics['total_cost_usd'] = meta.get('total_cost_usd', 0.0)
        completed = meta.get('completed_requests', meta.get('total_requests', 1))
        if completed > 0:
            metrics['cost_per_request'] = metrics['total_cost_usd'] / completed
            metrics['avg_cost_usd'] = metrics['total_cost_usd']
    
    # Gauntlet format
    if 'statistical_analysis' in report and metrics['total_cost_usd'] is None:
        swarm_data = report['statistical_analysis'].get('swarm_council', {})
        print(f"🔍 DEBUG: Gauntlet format found: {swarm_data}")
        metrics['total_cost_usd'] = swarm_data.get('cost_total_usd', 0.0)
        total_requests = swarm_data.get('total_requests', 1)
        if total_requests > 0:
            metrics['cost_per_request'] = metrics['total_cost_usd'] / total_requests
            metrics['avg_cost_usd'] = metrics['total_cost_usd']
    
    # Direct benchmark format (older reports)
    if 'total_cost_usd' in report and 'total_prompts' in report and metrics['total_cost_usd'] is None:
        print(f"🔍 DEBUG: Direct benchmark format found")
        metrics['total_cost_usd'] = report.get('total_cost_usd', 0.0)
        total_prompts = report.get('total_prompts', 1)
        metrics['avg_cost_usd'] = metrics['total_cost_usd']
        if total_prompts > 0:
            metrics['cost_per_request'] = metrics['total_cost_usd'] / total_prompts
        print(f"🔍 DEBUG: Total cost: ${metrics['total_cost_usd']}, Prompts: {total_prompts}")
    
    print(f"🔍 DEBUG: Extracted metrics: {metrics}")
    return metrics

def check_cost_guardrails(metrics: Dict[str, float], thresholds: Dict[str, float]) -> Dict[str, Any]:
    """Check cost metrics against guardrails"""
    
    results = {
        'passed': True,
        'violations': [],
        'metrics': metrics,
        'thresholds': thresholds
    }
    
    for metric_name, threshold in thresholds.items():
        if metric_name in metrics and metrics[metric_name] is not None:
            value = metrics[metric_name]
            
            if value > threshold:
                results['passed'] = False
                results['violations'].append({
                    'metric': metric_name,
                    'value': value,
                    'threshold': threshold,
                    'excess_percent': ((value - threshold) / threshold) * 100
                })
    
    return results

def main():
    """Main guardrail execution"""
    
    parser = argparse.ArgumentParser(description="Cost Guardrail for CI/CD")
    parser.add_argument("--cost-threshold", type=float, default=0.03, help="Maximum average cost per run (USD)")
    parser.add_argument("--per-request-threshold", type=float, default=0.02, help="Maximum cost per request (USD)")
    parser.add_argument("--reports-dir", default="reports", help="Reports directory")
    parser.add_argument("--strict", action="store_true", help="Fail on any threshold violation")
    
    args = parser.parse_args()
    
    print("💰 COST GUARDRAIL - CI/CD Protection")
    print("=" * 40)
    
    try:
        # Load latest report
        report = load_latest_titanic_report(args.reports_dir)
        print(f"📊 Loaded report: {report.get('metadata', {}).get('timestamp', 'Unknown time')}")
        
        # Extract cost metrics
        metrics = extract_cost_metrics(report)
        
        # Set thresholds
        thresholds = {
            'avg_cost_usd': args.cost_threshold,
            'cost_per_request': args.per_request_threshold
        }
        
        # Check guardrails
        results = check_cost_guardrails(metrics, thresholds)
        
        # Print results
        print(f"\n📈 COST METRICS:")
        for metric_name, value in metrics.items():
            if value is not None:
                threshold = thresholds.get(metric_name)
                status = "✅" if threshold is None or value <= threshold else "❌"
                threshold_str = f" (limit: ${threshold:.3f})" if threshold else ""
                print(f"  {status} {metric_name}: ${value:.4f}{threshold_str}")
        
        print(f"\n🛡️ GUARDRAIL RESULTS:")
        
        if results['passed']:
            print("✅ ALL GUARDRAILS PASSED - Cost within acceptable limits")
            print("   Ready for deployment")
            sys.exit(0)
        else:
            print("❌ COST REGRESSION DETECTED - Guardrails violated")
            print("\n🚨 VIOLATIONS:")
            
            for violation in results['violations']:
                metric = violation['metric']
                value = violation['value']
                threshold = violation['threshold']
                excess = violation['excess_percent']
                
                print(f"  ❌ {metric}: ${value:.4f} > ${threshold:.3f} (+{excess:.1f}% over limit)")
            
            print(f"\n🔧 RECOMMENDED ACTIONS:")
            print(f"  1. Review recent changes that might increase costs")
            print(f"  2. Check if more expensive models are being used")
            print(f"  3. Verify confidence gates are properly configured")
            print(f"  4. Consider implementing token diet or caching")
            
            if args.strict:
                print(f"\n💥 STRICT MODE: Failing CI due to cost regression")
                sys.exit(1)
            else:
                print(f"\n⚠️ NON-STRICT MODE: Warning only, allowing CI to continue")
                sys.exit(0)
    
    except Exception as e:
        print(f"❌ Guardrail check failed: {e}")
        if args.strict:
            sys.exit(1)
        else:
            print("⚠️ Non-strict mode: Continuing despite error")
            sys.exit(0)

if __name__ == "__main__":
    main() 