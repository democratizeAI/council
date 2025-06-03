#!/usr/bin/env python3
"""
🚢 Run Titanic Gauntlet
Ultimate SwarmAI benchmark with statistical rigor
"""

import os
import asyncio
import sys
import time
import requests
from datetime import datetime

# Set environment and add path
sys.path.insert(0, os.getcwd())

def check_environment():
    """Check required environment variables and dependencies"""
    required_vars = ["MISTRAL_API_KEY"]  # Only Mistral needed for Titanic Gauntlet
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Set them before running Titanic Gauntlet:")
        for var in missing:
            print(f"   export {var}=your_key_here")
        return False
    return True

def wait_for_server(max_wait_time=30):
    """Wait for the swarm server to be ready"""
    print("🌌 Checking SwarmAI server status...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get('http://localhost:8000/health', timeout=2)
            if response.status_code == 200:
                print("✅ SwarmAI server is ready!")
                return True
        except:
            pass
        
        print("   ⏳ Server starting up... (waiting)")
        time.sleep(2)
    
    print("⚠️  Server not available. Please start with: python start_swarm_server.py")
    return False

async def main():
    print("🚢 TITANIC GAUNTLET - The Ultimate SwarmAI Benchmark")
    print("=" * 70)
    print("🎯 Purpose: Test if micro-swarm beats mega-model")
    print("⚖️  Statistical rigor: 95% confidence intervals, 380 prompts")
    print("🧠 Domains: Math(30%), Reasoning(25%), Code(20%), Science(15%), Planning(5%), Writing(5%)")
    print("💰 Budget: $20 cap with adaptive throttling")
    print("🏆 Target: 15pp accuracy advantage, 10x cost savings, <1s latency")
    
    # Environment check
    if not check_environment():
        return 1
    
    # Server check
    server_ready = wait_for_server()
    if not server_ready:
        print("❌ SwarmAI server required for Titanic Gauntlet. Exiting.")
        return 1
    
    # Configuration
    config_file = 'nexus_jobs/titanic_gauntlet.yaml'
    
    print(f"\n🎯 Configuration:")
    print(f"   📋 Dataset: 380 prompts across 6 domains")
    print(f"   🛡️  Guards: Statistical significance required")
    print(f"   ⏱️  Execution: Chunked (38 items/chunk), checkpointed")
    print(f"   📊 Metrics: Prometheus monitoring on :8001")
    print(f"   💾 Reports: JSON + statistical analysis")
    
    # Import and run
    from nexus.titanic_runner import TitanicGauntletRunner
    
    try:
        print(f"\n🚀 LAUNCHING TITANIC GAUNTLET...")
        
        async with TitanicGauntletRunner(config_file) as runner:
            result = await runner.run_titanic_gauntlet()
            
            # Save comprehensive report
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
            report_path = f"reports/titanic_gauntlet_{date_str}.json"
            
            os.makedirs("reports", exist_ok=True)
            
            import json
            with open(report_path, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"\n📊 Titanic Gauntlet report saved to: {report_path}")
            
            # ULTIMATE RESULTS SUMMARY
            report = result["report"]
            print(f"\n🚢 TITANIC GAUNTLET RESULTS")
            print(f"   Status: {result['status']}")
            
            if result["status"] == "FAILED":
                print(f"   ❌ REASON: {result['reason']}")
                print("   ⚖️  Statistical guards detected inconclusive or insufficient performance")
                print("   📊 This is rigorous benchmarking - failures indicate real limitations")
            else:
                print(f"   🏆 PASSED: All statistical and performance guards satisfied!")
                print("   📊 Ready for confident README claims")
            
            print(f"   Duration: {report['total_duration_seconds']:.1f} seconds")
            print(f"   Total tests: {report['total_tests']}")
            print(f"   Total cost: ${report['total_cost_usd']:.2f}")
            print(f"   Cloud cost: ${report['cloud_cost_usd']:.2f}")
            
            # Statistical analysis summary
            if "statistical_analysis" in report:
                print(f"\n### 📊 STATISTICAL ANALYSIS")
                
                for provider, stats in report["statistical_analysis"].items():
                    ci_lower, ci_upper = stats["confidence_interval"]
                    print(f"\n**{provider}:**")
                    print(f"   Composite Accuracy: {stats['composite_accuracy']:.1%}")
                    print(f"   95% Confidence Interval: [{ci_lower:.1%}, {ci_upper:.1%}]")
                    print(f"   Cost per Request: ${stats['cost_mean_per_request']:.4f}")
                    print(f"   P95 Latency: {stats['latency_p95_ms']:.0f}ms")
                    print(f"   Success Rate: {stats['success_rate']:.1%}")
                
                # Calculate advantages if both providers present
                swarm_stats = report["statistical_analysis"].get("swarm_council", {})
                mistral_stats = report["statistical_analysis"].get("mistral_medium_3", {})
                
                if swarm_stats and mistral_stats:
                    accuracy_advantage = (swarm_stats.get("composite_accuracy", 0) - 
                                        mistral_stats.get("composite_accuracy", 0)) * 100
                    
                    if mistral_stats.get("cost_mean_per_request", 0) > 0:
                        cost_advantage = (mistral_stats["cost_mean_per_request"] / 
                                        swarm_stats.get("cost_mean_per_request", 1))
                    else:
                        cost_advantage = 0
                    
                    print(f"\n### 🎯 ADVANTAGES:")
                    print(f"   Accuracy Advantage: {accuracy_advantage:+.1f} percentage points")
                    print(f"   Cost Advantage: {cost_advantage:.1f}x cheaper")
                    
                    # README-ready assessment
                    print(f"\n### 📝 README-READY ASSESSMENT:")
                    if result["status"] == "PASSED":
                        print(f"   ✅ 'SwarmAI passes Titanic Gauntlet with {accuracy_advantage:.0f}pp accuracy advantage'")
                        print(f"   ✅ '{cost_advantage:.0f}x cost savings over Mistral-Medium 3'")
                        print(f"   ✅ 'Sub-second latency ({swarm_stats.get('latency_p95_ms', 0):.0f}ms P95)'")
                        print(f"   ✅ 'Statistical significance confirmed (95% CI non-overlapping)'")
                        print(f"   ✅ 'Comprehensive 6-domain evaluation (380 prompts)'")
                    else:
                        print(f"   ❌ 'SwarmAI requires optimization before production claims'")
                        print(f"   📊 'Statistical analysis available for development guidance'")
            
            return 0 if result["status"] == "PASSED" else 1
                
    except Exception as e:
        print(f"💥 Titanic Gauntlet failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 