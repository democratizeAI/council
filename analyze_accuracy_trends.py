#!/usr/bin/env python3
"""
📈 Accuracy Trend Analysis
Analyzes historical Titanic reports to detect accuracy regression
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics

def load_titanic_reports(reports_dir: str = "reports") -> List[Dict[str, Any]]:
    """Load all Titanic reports from the reports directory"""
    
    reports = []
    reports_path = Path(reports_dir)
    
    if not reports_path.exists():
        print(f"❌ Reports directory not found: {reports_dir}")
        return []
    
    # Find all JSON files with Titanic-related names
    titanic_files = list(reports_path.glob("*titanic*.json")) + list(reports_path.glob("autogen_titanic*.json"))
    
    print(f"📁 Found {len(titanic_files)} Titanic report files")
    
    for file_path in titanic_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Add file metadata
            data['_file_name'] = file_path.name
            data['_file_path'] = str(file_path)
            data['_file_size'] = file_path.stat().st_size
            
            # Parse timestamp from filename or metadata
            timestamp = extract_timestamp(file_path.name, data)
            if timestamp:
                data['_parsed_timestamp'] = timestamp
                reports.append(data)
            else:
                print(f"⚠️ Skipping {file_path.name} - no valid timestamp")
                
        except Exception as e:
            print(f"❌ Failed to load {file_path.name}: {e}")
            continue
    
    # Sort by timestamp
    reports.sort(key=lambda x: x.get('_parsed_timestamp', datetime.min))
    
    print(f"✅ Loaded {len(reports)} valid reports")
    return reports

def extract_timestamp(filename: str, data: Dict[str, Any]) -> Optional[datetime]:
    """Extract timestamp from filename or report data"""
    
    # Try filename patterns
    if "_20250" in filename:
        try:
            # Pattern: autogen_titanic_20250604_002439.json
            parts = filename.split("_")
            for i, part in enumerate(parts):
                if part.startswith("20250") and len(part) == 8:
                    date_str = part
                    if i + 1 < len(parts):
                        time_str = parts[i + 1].split(".")[0]  # Remove .json
                        datetime_str = f"{date_str}_{time_str}"
                        return datetime.strptime(datetime_str, "%Y%m%d_%H%M%S")
        except:
            pass
    
    # Try metadata timestamp
    metadata = data.get('metadata', {})
    if 'timestamp' in metadata:
        try:
            timestamp_str = metadata['timestamp']
            # Handle ISO format
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            pass
    
    # Try top-level timestamp
    if 'timestamp' in data:
        try:
            timestamp_str = data['timestamp']
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            pass
    
    return None

def extract_accuracy_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    """Extract accuracy metrics from a report"""
    
    metrics = {
        'timestamp': report.get('_parsed_timestamp'),
        'file_name': report.get('_file_name'),
        'success_rate': None,
        'accuracy': None,
        'content_pass_rate': None,
        'total_requests': None,
        'avg_latency_ms': None,
        'cost_usd': None,
        'errors': 0,
        'cloudretry': 0
    }
    
    # Performance section (newer format)
    if 'performance' in report:
        perf = report['performance']
        metrics['success_rate'] = perf.get('success_rate')
        metrics['content_pass_rate'] = perf.get('content_pass_rate')
        metrics['avg_latency_ms'] = perf.get('avg_latency_ms')
        metrics['cost_usd'] = perf.get('total_cost_usd')
        
        # Count from detailed results
        if 'detailed_results' in report:
            results = report['detailed_results']
            metrics['total_requests'] = len(results)
            metrics['errors'] = sum(1 for r in results if r.get('status') == 'error')
            metrics['cloudretry'] = sum(1 for r in results if r.get('status') == 'cloudretry')
    
    # Metadata section
    elif 'metadata' in report:
        meta = report['metadata']
        metrics['total_requests'] = meta.get('completed_requests', meta.get('total_requests'))
        metrics['cost_usd'] = meta.get('total_cost_usd')
        
        # Check if this is the gauntlet format
        if 'statistical_analysis' in report:
            swarm_data = report['statistical_analysis'].get('swarm_council', {})
            metrics['success_rate'] = swarm_data.get('success_rate')
            metrics['accuracy'] = swarm_data.get('composite_accuracy')
            metrics['avg_latency_ms'] = swarm_data.get('latency_mean_ms')
            metrics['cost_usd'] = swarm_data.get('cost_total_usd')
            metrics['total_requests'] = swarm_data.get('total_requests')
    
    # Overall metrics (Docker format)
    elif 'overall_metrics' in report:
        overall = report['overall_metrics']
        metrics['success_rate'] = overall.get('success_rate')
        metrics['accuracy'] = overall.get('average_accuracy')
        metrics['avg_latency_ms'] = overall.get('average_latency_ms')
        metrics['total_requests'] = overall.get('total_questions')
    
    return metrics

def analyze_accuracy_trends(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze accuracy trends across reports"""
    
    print("\n📊 ACCURACY TREND ANALYSIS")
    print("=" * 50)
    
    all_metrics = []
    
    for report in reports:
        metrics = extract_accuracy_metrics(report)
        if metrics['success_rate'] is not None or metrics['accuracy'] is not None:
            all_metrics.append(metrics)
    
    if not all_metrics:
        return {"error": "No valid metrics found in reports"}
    
    print(f"📈 Analyzing {len(all_metrics)} reports with valid metrics")
    print()
    
    # Sort by timestamp
    all_metrics.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min)
    
    # Calculate trends
    success_rates = [m['success_rate'] for m in all_metrics if m['success_rate'] is not None]
    accuracies = [m['accuracy'] for m in all_metrics if m['accuracy'] is not None]
    latencies = [m['avg_latency_ms'] for m in all_metrics if m['avg_latency_ms'] is not None]
    costs = [m['cost_usd'] for m in all_metrics if m['cost_usd'] is not None]
    
    # Recent vs Historical comparison
    recent_cutoff = len(all_metrics) // 2  # Last 50% of reports
    recent_metrics = all_metrics[recent_cutoff:]
    historical_metrics = all_metrics[:recent_cutoff]
    
    def calculate_stats(metrics_list, key):
        values = [m[key] for m in metrics_list if m[key] is not None]
        if not values:
            return None
        return {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'count': len(values)
        }
    
    analysis = {
        'total_reports': len(all_metrics),
        'date_range': {
            'earliest': min(m['timestamp'] for m in all_metrics if m['timestamp']).strftime('%Y-%m-%d %H:%M'),
            'latest': max(m['timestamp'] for m in all_metrics if m['timestamp']).strftime('%Y-%m-%d %H:%M')
        },
        'overall_stats': {
            'success_rate': calculate_stats(all_metrics, 'success_rate'),
            'accuracy': calculate_stats(all_metrics, 'accuracy'),
            'latency_ms': calculate_stats(all_metrics, 'avg_latency_ms'),
            'cost_usd': calculate_stats(all_metrics, 'cost_usd')
        },
        'recent_vs_historical': {},
        'trend_analysis': {},
        'recent_reports': recent_metrics[-5:],  # Last 5 reports
        'regression_detected': False,
        'regression_details': []
    }
    
    # Compare recent vs historical
    for metric_key in ['success_rate', 'accuracy', 'avg_latency_ms', 'cost_usd']:
        recent_stats = calculate_stats(recent_metrics, metric_key)
        historical_stats = calculate_stats(historical_metrics, metric_key)
        
        if recent_stats and historical_stats and recent_stats['count'] > 0 and historical_stats['count'] > 0:
            recent_mean = recent_stats['mean']
            historical_mean = historical_stats['mean']
            
            if metric_key in ['success_rate', 'accuracy']:
                # Higher is better
                change = recent_mean - historical_mean
                change_pct = (change / historical_mean) * 100
                regression = change < -0.05  # 5% drop threshold
            else:
                # Lower is better for latency/cost
                change = recent_mean - historical_mean
                change_pct = (change / historical_mean) * 100
                regression = change > 0.20 * historical_mean  # 20% increase threshold
            
            analysis['recent_vs_historical'][metric_key] = {
                'recent_mean': recent_mean,
                'historical_mean': historical_mean,
                'change': change,
                'change_percent': change_pct,
                'regression_detected': regression
            }
            
            if regression:
                analysis['regression_detected'] = True
                analysis['regression_details'].append({
                    'metric': metric_key,
                    'change_percent': change_pct,
                    'threshold_exceeded': True
                })
    
    return analysis

def print_trend_analysis(analysis: Dict[str, Any]):
    """Print formatted trend analysis"""
    
    if 'error' in analysis:
        print(f"❌ {analysis['error']}")
        return
    
    print(f"📊 Analysis of {analysis['total_reports']} reports")
    print(f"📅 Date range: {analysis['date_range']['earliest']} to {analysis['date_range']['latest']}")
    print()
    
    # Overall statistics
    print("🎯 OVERALL STATISTICS")
    print("-" * 30)
    
    stats = analysis['overall_stats']
    for metric, data in stats.items():
        if data:
            print(f"{metric.upper()}: {data['mean']:.3f} avg | {data['median']:.3f} median | {data['min']:.3f}-{data['max']:.3f} range | {data['count']} reports")
    
    print()
    
    # Recent vs Historical comparison
    print("📈 RECENT vs HISTORICAL COMPARISON")
    print("-" * 40)
    
    recent_vs_hist = analysis['recent_vs_historical']
    for metric, comparison in recent_vs_hist.items():
        recent = comparison['recent_mean']
        historical = comparison['historical_mean']
        change_pct = comparison['change_percent']
        regression = comparison['regression_detected']
        
        direction = "📈" if change_pct > 0 else "📉"
        if metric in ['success_rate', 'accuracy']:
            # Higher is better
            status = "🎉" if change_pct > 5 else "⚠️" if change_pct < -5 else "✅"
        else:
            # Lower is better
            status = "🎉" if change_pct < -10 else "⚠️" if change_pct > 20 else "✅"
        
        if regression:
            status = "❌"
        
        print(f"{status} {metric.upper()}: {historical:.3f} → {recent:.3f} ({direction}{change_pct:+.1f}%)")
    
    print()
    
    # Recent reports summary
    print("🕒 MOST RECENT REPORTS")
    print("-" * 30)
    
    for i, report in enumerate(analysis['recent_reports']):
        timestamp = report['timestamp'].strftime('%m-%d %H:%M') if report['timestamp'] else 'Unknown'
        success = f"{report['success_rate']:.1%}" if report['success_rate'] else "N/A"
        accuracy = f"{report['accuracy']:.3f}" if report['accuracy'] else "N/A"
        latency = f"{report['avg_latency_ms']:.0f}ms" if report['avg_latency_ms'] else "N/A"
        
        print(f"  {timestamp}: {success} success | {accuracy} accuracy | {latency}")
    
    print()
    
    # Regression detection
    if analysis['regression_detected']:
        print("🚨 REGRESSION DETECTED")
        print("-" * 25)
        
        for detail in analysis['regression_details']:
            metric = detail['metric']
            change = detail['change_percent']
            print(f"❌ {metric.upper()}: {change:+.1f}% change exceeds threshold")
        
        print()
        print("🔧 RECOMMENDED ACTIONS:")
        print("  1. Review recent model changes or deployments")
        print("  2. Check for infrastructure issues")
        print("  3. Run fresh accuracy tests to confirm")
        print("  4. Consider rolling back recent changes")
        
    else:
        print("✅ NO SIGNIFICANT REGRESSION DETECTED")
        print("   Performance appears stable or improving")
    
    print()

def main():
    """Main execution"""
    
    print("📈 TITANIC ACCURACY TREND ANALYSIS")
    print("=" * 50)
    print("Analyzing historical reports to detect accuracy regression...")
    print()
    
    # Load reports
    reports = load_titanic_reports()
    
    if not reports:
        print("❌ No reports found to analyze")
        return
    
    # Analyze trends
    analysis = analyze_accuracy_trends(reports)
    
    # Print results
    print_trend_analysis(analysis)
    
    # Save analysis
    output_file = f"reports/accuracy_trend_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        # Make analysis JSON serializable
        serializable_analysis = json.loads(json.dumps(analysis, default=str))
        json.dump(serializable_analysis, f, indent=2)
    
    print(f"📄 Detailed analysis saved: {output_file}")

if __name__ == "__main__":
    main() 