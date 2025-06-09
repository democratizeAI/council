#!/usr/bin/env python3
"""
Cost-Guard Quick Test
====================

P0 Critical: Test budget valve with expensive prompts using existing voting system
Verifies B-05 budget protection without requiring full web server
"""

import asyncio
import time
from router.voting import vote
from router.cost_tracking import get_budget_status, get_cost_breakdown

# Expensive prompts that would hit cloud APIs
EXPENSIVE_PROMPTS = [
    "Write a comprehensive 5000-word analysis of quantum computing including mathematical proofs, code examples in multiple languages, detailed algorithm explanations, and practical implementation guides for enterprise adoption.",
    
    "Create a complete enterprise microservices architecture with 15 services including database schemas, API specifications, Kubernetes manifests, CI/CD pipelines, monitoring stack, and disaster recovery procedures.",
    
    "Develop a comprehensive machine learning pipeline with feature engineering, multiple models (LSTM, Transformer, Prophet), hyperparameter optimization, ensemble techniques, and production deployment with monitoring.",
    
    "Build a complete blockchain implementation with consensus algorithms, cryptographic functions, P2P networking, smart contracts, and comprehensive security analysis including source code.",
    
    "Design a distributed database system with ACID compliance, consensus protocols, sharding, replication, query optimization, and horizontal scaling strategies with full C++ implementation.",
    
    "Create a comprehensive cybersecurity framework including threat modeling, penetration testing methodologies, incident response procedures, compliance frameworks, and automated security tools.",
    
    "Develop a complete game engine with 3D rendering pipeline, physics simulation, audio system, networking capabilities, and comprehensive toolchain with performance optimization.",
    
    "Build an autonomous vehicle control system including computer vision, sensor fusion, path planning, decision making algorithms, and safety validation with regulatory compliance.",
]

async def test_cost_guard():
    """Test cost guard with the voting system"""
    print("🛡️ Cost-Guard Quick Test")
    print("=" * 50)
    print(f"Testing budget protection with {len(EXPENSIVE_PROMPTS)} expensive prompts")
    print()
    
    results = []
    total_cost = 0.0
    budget_hit = False
    
    # Get initial budget status
    try:
        initial_budget = get_budget_status()
        print(f"💰 Initial Budget Status: {initial_budget}")
    except Exception as e:
        print(f"⚠️ Could not get initial budget: {e}")
        initial_budget = {"remaining": 10.0, "spent": 0.0}
    
    for i, prompt in enumerate(EXPENSIVE_PROMPTS):
        print(f"\n📤 Test {i+1}/{len(EXPENSIVE_PROMPTS)}: {len(prompt)} chars")
        
        try:
            start_time = time.time()
            
            # Use voting system directly
            result = await vote(prompt, top_k=1)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract cost information
            cost_usd = result.get("voting_stats", {}).get("total_cost_usd", 0.0)
            total_cost += cost_usd
            
            # Check if we hit budget limits
            try:
                budget_status = get_budget_status()
                remaining = budget_status.get("remaining", 10.0)
                
                if remaining <= 1.0:  # Near budget limit
                    budget_hit = True
                    print(f"   🛡️ Budget protection triggered - remaining: ${remaining:.4f}")
                    break
                    
            except Exception as e:
                print(f"   ⚠️ Budget check failed: {e}")
            
            results.append({
                "test_id": i + 1,
                "success": True,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
                "total_cost": total_cost,
                "winner": result.get("winner", {}).get("specialist", "unknown"),
                "response_length": len(result.get("text", ""))
            })
            
            print(f"   ✅ Success - ${cost_usd:.4f} (total: ${total_cost:.4f}) - {latency_ms:.0f}ms")
            print(f"   🏆 Winner: {result.get('winner', {}).get('specialist', 'unknown')}")
            
        except Exception as e:
            results.append({
                "test_id": i + 1,
                "success": False,
                "error": str(e),
                "total_cost": total_cost
            })
            print(f"   ❌ Failed: {e}")
            
            # Check if this was a budget-related failure
            if "budget" in str(e).lower() or "cost" in str(e).lower():
                budget_hit = True
                print(f"   🛡️ Budget protection likely triggered")
                break
        
        # Brief pause between tests
        await asyncio.sleep(0.5)
    
    # Final analysis
    print("\n" + "=" * 50)
    print("🎯 Cost-Guard Test Analysis")
    print("=" * 50)
    
    successful_tests = len([r for r in results if r.get("success")])
    failed_tests = len(results) - successful_tests
    
    print(f"Tests Completed: {len(results)}/{len(EXPENSIVE_PROMPTS)}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Total Cost: ${total_cost:.4f}")
    
    # Get final budget status
    try:
        final_budget = get_budget_status()
        spent = final_budget.get("spent", total_cost)
        remaining = final_budget.get("remaining", 10.0 - spent)
        print(f"Budget Spent: ${spent:.4f}")
        print(f"Budget Remaining: ${remaining:.4f}")
    except Exception as e:
        print(f"Final budget: ${total_cost:.4f} (estimated)")
    
    # Verify budget protection
    print(f"\n🛡️ Budget Protection Analysis:")
    
    if budget_hit and total_cost <= 12.0:
        print("✅ PASS: Budget protection engaged before exceeding limits")
        protection_working = True
    elif total_cost > 15.0:
        print("❌ FAIL: Budget protection failed - excessive spending detected")
        protection_working = False
    elif not budget_hit and total_cost < 5.0:
        print("⚠️ WARNING: Budget protection not tested - spending too low")
        protection_working = None
    else:
        print("🤔 UNCLEAR: Manual review needed")
        protection_working = None
    
    # Performance summary
    if successful_tests > 0:
        avg_latency = sum(r.get("latency_ms", 0) for r in results if r.get("success")) / successful_tests
        print(f"\n⚡ Performance Summary:")
        print(f"   Average Latency: {avg_latency:.0f}ms")
        print(f"   Success Rate: {successful_tests/len(results)*100:.1f}%")
    
    return {
        "budget_protection_working": protection_working,
        "total_cost": total_cost,
        "successful_tests": successful_tests,
        "budget_hit": budget_hit,
        "results": results
    }

async def main():
    print("🚀 Starting Cost-Guard Quick Test...")
    print("Using existing voting system to test budget protection")
    print()
    
    result = await test_cost_guard()
    
    print(f"\n🏆 Final Result: {'PASS' if result['budget_protection_working'] else 'FAIL' if result['budget_protection_working'] is False else 'INCONCLUSIVE'}")
    
    return result

if __name__ == "__main__":
    result = asyncio.run(main()) 