#!/usr/bin/env python3
"""
Cost-Guard Smoke Test
====================

P0 Critical: Verify budget valve caps at $10 and engages 503 fallback
Tests B-05 budget protection with 30 cloud-size prompts
"""

import asyncio
import time
import requests
import json
from typing import List, Dict, Any

# Large prompts that would be expensive on cloud APIs
CLOUD_SIZE_PROMPTS = [
    "Write a comprehensive 10,000-word analysis of quantum computing's impact on cryptography, including mathematical proofs, implementation details, code examples in Python and C++, detailed algorithm explanations, security implications for RSA and AES encryption, future research directions, and practical recommendations for enterprise adoption. Include specific examples of quantum algorithms like Shor's and Grover's algorithms with complete pseudocode and complexity analysis.",
    
    "Create a complete enterprise-grade microservices architecture documentation including: detailed system design diagrams, database schemas for 15 different services, API specifications with OpenAPI 3.0, Kubernetes deployment manifests, CI/CD pipeline configurations, monitoring and observability stack setup, security protocols, disaster recovery procedures, performance benchmarking results, and cost optimization strategies. Include code examples in Java, Python, Go, and TypeScript.",
    
    "Develop a comprehensive machine learning model for time series forecasting including: complete data preprocessing pipeline with feature engineering, multiple model architectures (LSTM, Transformer, Prophet, ARIMA), hyperparameter optimization using Bayesian methods, cross-validation strategies, model ensemble techniques, production deployment pipeline, real-time inference API, monitoring dashboard, A/B testing framework, and detailed performance analysis with statistical significance testing.",
    
    "Build a complete blockchain implementation from scratch including: consensus algorithm design and implementation, cryptographic hash functions, digital signature schemes, peer-to-peer networking protocol, transaction validation logic, smart contract virtual machine, wallet implementation, mining algorithm, fork resolution mechanisms, and comprehensive security analysis. Include complete source code in Rust and performance benchmarks.",
    
    "Design and implement a distributed database system including: ACID compliance mechanisms, distributed consensus protocols (Raft/Paxos), sharding strategies, replication algorithms, query optimization engine, indexing structures (B-trees, LSM-trees), transaction isolation levels, backup and recovery procedures, performance monitoring, and horizontal scaling strategies. Provide complete implementation in C++ with benchmark results.",
]

async def test_cost_guard():
    """Test cost guard with expensive prompts"""
    print("🛡️ Cost-Guard Smoke Test")
    print("=" * 50)
    print(f"Testing budget valve with {len(CLOUD_SIZE_PROMPTS)} cloud-size prompts...")
    print(f"Expected: Cap at $10, then 503 fallback")
    print()
    
    base_url = "http://localhost:8080"  # Adjust if different
    endpoint = f"{base_url}/vote"
    
    results = []
    total_estimated_cost = 0.0
    budget_exceeded = False
    
    for i, prompt in enumerate(CLOUD_SIZE_PROMPTS):
        print(f"📤 Request {i+1}/{len(CLOUD_SIZE_PROMPTS)}: {len(prompt)} chars")
        
        try:
            start_time = time.time()
            
            # Make request to voting endpoint
            response = requests.post(
                endpoint,
                json={"prompt": prompt},
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Parse response
            if response.status_code == 200:
                data = response.json()
                estimated_cost = data.get("cost_usd", 0.0)
                total_estimated_cost += estimated_cost
                
                results.append({
                    "request_id": i + 1,
                    "status_code": 200,
                    "latency_ms": latency_ms,
                    "estimated_cost": estimated_cost,
                    "cumulative_cost": total_estimated_cost,
                    "response_length": len(data.get("text", "")),
                    "prompt_length": len(prompt)
                })
                
                print(f"   ✅ 200 OK - ${estimated_cost:.4f} (total: ${total_estimated_cost:.4f}) - {latency_ms:.0f}ms")
                
            elif response.status_code == 503:
                # Budget exceeded - this is expected behavior
                budget_exceeded = True
                results.append({
                    "request_id": i + 1,
                    "status_code": 503,
                    "latency_ms": latency_ms,
                    "budget_exceeded": True,
                    "cumulative_cost": total_estimated_cost
                })
                
                print(f"   🛡️ 503 Service Unavailable - Budget protection engaged at ${total_estimated_cost:.4f}")
                print(f"      Expected behavior: Budget valve activated!")
                break
                
            else:
                results.append({
                    "request_id": i + 1,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "error": f"Unexpected status: {response.status_code}"
                })
                print(f"   ❌ {response.status_code} - Unexpected response")
                
        except requests.exceptions.Timeout:
            print(f"   ⏱️ Timeout after 30s - Request {i+1}")
            results.append({
                "request_id": i + 1,
                "timeout": True,
                "error": "Request timeout"
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "request_id": i + 1,
                "error": str(e)
            })
        
        # Brief pause between requests
        await asyncio.sleep(0.5)
    
    # Analysis
    print("\n" + "=" * 50)
    print("🎯 Cost-Guard Analysis")
    print("=" * 50)
    
    successful_requests = len([r for r in results if r.get("status_code") == 200])
    failed_requests = len([r for r in results if r.get("status_code") != 200])
    
    print(f"Total Requests Made: {len(results)}")
    print(f"Successful (200): {successful_requests}")
    print(f"Budget Protected (503): {len([r for r in results if r.get('status_code') == 503])}")
    print(f"Other Failures: {failed_requests - len([r for r in results if r.get('status_code') == 503])}")
    print(f"Total Estimated Cost: ${total_estimated_cost:.4f}")
    
    # Verify budget guard behavior
    print(f"\n🛡️ Budget Guard Verification:")
    if budget_exceeded and total_estimated_cost <= 12.0:  # Allow small buffer
        print("✅ PASS: Budget valve engaged before exceeding $10-12 threshold")
    elif total_estimated_cost > 15.0:
        print("❌ FAIL: Budget valve did not engage - costs exceeded $15!")
    elif not budget_exceeded and total_estimated_cost < 8.0:
        print("⚠️ WARNING: Budget valve not tested - costs too low")
    else:
        print("🤔 UNCLEAR: Review results manually")
    
    # Performance analysis
    if successful_requests > 0:
        latencies = [r["latency_ms"] for r in results if "latency_ms" in r and r.get("status_code") == 200]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            print(f"\n⚡ Performance:")
            print(f"   Average Latency: {avg_latency:.0f}ms")
            print(f"   Requests Under 1s: {len([l for l in latencies if l < 1000])}/{len(latencies)}")
    
    return {
        "budget_guard_working": budget_exceeded and total_estimated_cost <= 12.0,
        "total_cost": total_estimated_cost,
        "successful_requests": successful_requests,
        "budget_exceeded_at": total_estimated_cost if budget_exceeded else None,
        "results": results
    }

if __name__ == "__main__":
    result = asyncio.run(test_cost_guard())
    
    print(f"\n🏆 Final Result: {'PASS' if result['budget_guard_working'] else 'FAIL'}")
    
    # Save detailed results
    with open("cost_guard_results.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"📄 Detailed results saved to: cost_guard_results.json") 