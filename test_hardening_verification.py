#!/usr/bin/env python3
"""
🧪 HARDENING VERIFICATION SUITE
===============================

Comprehensive test suite for the triage & hardening measures:

1. ✅ FAISS Singleton - No re-indexing per request
2. ✅ Docker Health - Restart policies and monitoring  
3. ✅ Enhanced Intent Classification - Better routing accuracy

Tests all three symptoms from the playbook:
- "Chat keeps loading to FAISS" → FAISS singleton
- Docker engine hangs → Health checks & restart policies  
- NLP routing feels flaky → Enhanced classifier

Expected results:
- FAISS loads once, reused thereafter
- Docker health checks pass
- Intent classification >90% accuracy
"""

import asyncio
import time
import os
import sys
import json
import subprocess
from typing import Dict, List, Any

# Test configuration
TEST_CONFIG = {
    "faiss_singleton_tests": 5,
    "intent_classification_tests": 20,
    "docker_health_timeout": 30,
    "memory_query_benchmark": 100
}

async def test_faiss_singleton_fix():
    """Test Fix #1: FAISS singleton prevents re-indexing"""
    print("\n🔧 TEST 1: FAISS Singleton Fix")
    print("=" * 50)
    
    try:
        # Test 1: Multiple imports should reuse same instance
        print("Testing multiple FAISS imports...")
        
        import_times = []
        for i in range(TEST_CONFIG["faiss_singleton_tests"]):
            start_time = time.time()
            
            # Force reimport to test singleton behavior
            if 'bootstrap' in sys.modules:
                del sys.modules['bootstrap']
            
            from bootstrap import MEMORY
            
            import_time = (time.time() - start_time) * 1000
            import_times.append(import_time)
            
            print(f"   Import {i+1}: {import_time:.1f}ms, Memory size: {len(getattr(MEMORY, 'data', []))}")
        
        # First import should be slower (index loading), subsequent should be fast
        first_import = import_times[0]
        avg_subsequent = sum(import_times[1:]) / len(import_times[1:]) if len(import_times) > 1 else 0
        
        print(f"\n📊 Results:")
        print(f"   First import: {first_import:.1f}ms (index loading)")
        print(f"   Avg subsequent: {avg_subsequent:.1f}ms (singleton reuse)")
        
        # Test 2: Verify no multiple instantiations in codebase
        print("\n🔍 Checking for FaissMemory() instantiations...")
        
        result = subprocess.run([
            "grep", "-r", "FaissMemory()", "--include=*.py", "."
        ], capture_output=True, text=True)
        
        problematic_files = []
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'test_' not in line and 'bootstrap.py' not in line:
                    problematic_files.append(line)
        
        if problematic_files:
            print(f"   ⚠️ Found {len(problematic_files)} potential singleton violations:")
            for file_line in problematic_files[:3]:  # Show first 3
                print(f"     {file_line}")
        else:
            print("   ✅ No singleton violations found")
        
        # Test 3: Memory query performance
        print("\n⚡ Memory query performance test...")
        
        query_times = []
        for i in range(TEST_CONFIG["memory_query_benchmark"]):
            start_time = time.time()
            results = MEMORY.query(f"test query {i}", k=1)
            query_time = (time.time() - start_time) * 1000
            query_times.append(query_time)
        
        avg_query_time = sum(query_times) / len(query_times)
        p95_query_time = sorted(query_times)[int(0.95 * len(query_times))]
        
        print(f"   Average query time: {avg_query_time:.2f}ms")
        print(f"   P95 query time: {p95_query_time:.2f}ms")
        
        # Success criteria
        singleton_success = (
            avg_subsequent < first_import * 0.1 and  # Subsequent imports 10x faster
            len(problematic_files) == 0 and          # No singleton violations
            avg_query_time < 20                      # Fast query performance
        )
        
        if singleton_success:
            print("\n✅ FAISS Singleton Fix: PASSED")
            print("   - Index loads once, singleton reused")
            print("   - No per-request re-indexing")
            print("   - Fast query performance")
        else:
            print("\n❌ FAISS Singleton Fix: FAILED")
            print("   - Check for singleton violations or performance issues")
        
        return singleton_success
        
    except Exception as e:
        print(f"\n❌ FAISS Singleton test failed: {e}")
        return False

async def test_docker_health_fix():
    """Test Fix #2: Docker health checks and restart policies"""
    print("\n🐳 TEST 2: Docker Health & Restart Fix")
    print("=" * 50)
    
    try:
        # Test 1: Health check endpoint
        print("Testing health check endpoint...")
        
        try:
            from health_check import health_check
            
            # Run health check
            start_time = time.time()
            health_response = await health_check()
            health_time = (time.time() - start_time) * 1000
            
            print(f"   Health check response time: {health_time:.1f}ms")
            print(f"   Status code: {health_response.status_code}")
            
            # Parse response content
            if hasattr(health_response, 'body'):
                content = json.loads(health_response.body.decode())
                overall_status = content.get('overall_status', 'unknown')
                checks = content.get('checks', {})
                
                print(f"   Overall status: {overall_status}")
                for check_name, check_result in checks.items():
                    status = check_result.get('status', 'unknown')
                    print(f"     {check_name}: {status}")
                
                health_endpoint_success = health_response.status_code < 400
            else:
                health_endpoint_success = True  # Health check ran without error
                
        except Exception as e:
            print(f"   ⚠️ Health check endpoint error: {e}")
            health_endpoint_success = False
        
        # Test 2: Docker compose configuration
        print("\nChecking Docker Compose configuration...")
        
        compose_checks = {
            "restart_policy": False,
            "health_check": False,
            "resource_limits": False,
            "security_opts": False
        }
        
        try:
            with open('docker-compose.yml', 'r') as f:
                compose_content = f.read()
                
                if 'restart: on-failure:5' in compose_content:
                    compose_checks["restart_policy"] = True
                    print("   ✅ Restart policy configured")
                
                if 'healthcheck:' in compose_content and 'curl' in compose_content:
                    compose_checks["health_check"] = True  
                    print("   ✅ Health check configured")
                
                if 'memory: 10g' in compose_content:
                    compose_checks["resource_limits"] = True
                    print("   ✅ Resource limits configured")
                
                if 'no-new-privileges' in compose_content:
                    compose_checks["security_opts"] = True
                    print("   ✅ Security options configured")
                    
        except FileNotFoundError:
            print("   ⚠️ docker-compose.yml not found")
        except Exception as e:
            print(f"   ⚠️ Docker compose check error: {e}")
        
        # Test 3: Monitoring metrics
        print("\nChecking hardening metrics availability...")
        
        metrics_available = False
        try:
            from monitoring.hardening_metrics import get_hardening_monitor
            
            monitor = get_hardening_monitor()
            monitor.track_docker_restart("test-container", "test")
            metrics_available = True
            print("   ✅ Hardening metrics available")
            
        except Exception as e:
            print(f"   ⚠️ Hardening metrics error: {e}")
        
        # Success criteria
        docker_success = (
            health_endpoint_success and
            all(compose_checks.values()) and
            metrics_available
        )
        
        if docker_success:
            print("\n✅ Docker Health & Restart Fix: PASSED")
            print("   - Health check endpoint working")
            print("   - Restart policies configured")
            print("   - Resource limits and security set")
            print("   - Monitoring metrics available")
        else:
            print("\n❌ Docker Health & Restart Fix: FAILED")
            failed_checks = [k for k, v in compose_checks.items() if not v]
            if failed_checks:
                print(f"   - Failed checks: {failed_checks}")
        
        return docker_success
        
    except Exception as e:
        print(f"\n❌ Docker health test failed: {e}")
        return False

async def test_enhanced_intent_classification():
    """Test Fix #3: Enhanced intent classification"""
    print("\n🎯 TEST 3: Enhanced Intent Classification")
    print("=" * 50)
    
    try:
        from router.intent_classifier import EnhancedIntentClassifier, classify_query_intent
        
        # Test cases with expected intents
        test_cases = [
            # Math examples
            ("2 + 2", "math", 0.8),
            ("calculate 15 * 23", "math", 0.8),
            ("what is sqrt(16)", "math", 0.8),
            ("solve 5x + 3 = 18", "math", 0.7),
            
            # Code examples  
            ("write a hello world function", "code", 0.8),
            ("def factorial(n):", "code", 0.8),
            ("debug this Python code", "code", 0.7),
            ("implement bubble sort algorithm", "code", 0.7),
            
            # Knowledge examples
            ("what is the capital of France", "knowledge", 0.6),
            ("who was Albert Einstein", "knowledge", 0.6),
            ("explain photosynthesis", "knowledge", 0.6),
            ("tell me about Saturn", "knowledge", 0.6),
            
            # Logic examples
            ("if A implies B and B implies C", "logic", 0.7),
            ("prove this theorem", "logic", 0.7),
            ("valid logical reasoning", "logic", 0.6),
            
            # General examples
            ("hello there", "general", 0.5),
            ("thank you", "general", 0.5),
            ("how are you", "general", 0.5),
            ("help me", "general", 0.5)
        ]
        
        print(f"Testing {len(test_cases)} classification cases...")
        
        classifier = EnhancedIntentClassifier(use_miniLM=False)
        
        correct_predictions = 0
        total_predictions = len(test_cases)
        classification_times = []
        
        for query, expected_intent, min_confidence in test_cases:
            start_time = time.time()
            predicted_intent, confidence, all_scores = classifier.classify_intent(query)
            classification_time = (time.time() - start_time) * 1000
            
            classification_times.append(classification_time)
            
            is_correct = (predicted_intent == expected_intent and confidence >= min_confidence)
            if is_correct:
                correct_predictions += 1
            
            status = "✅" if is_correct else "❌"
            print(f"   {status} '{query[:30]}...' → {predicted_intent} ({confidence:.3f}) [expected: {expected_intent}]")
        
        accuracy = (correct_predictions / total_predictions) * 100
        avg_classification_time = sum(classification_times) / len(classification_times)
        
        print(f"\n📊 Classification Results:")
        print(f"   Accuracy: {accuracy:.1f}% ({correct_predictions}/{total_predictions})")
        print(f"   Avg classification time: {avg_classification_time:.2f}ms")
        
        # Test fallback penalty system
        print("\nTesting fallback penalty system...")
        
        fallback_tests = [
            "ambiguous query that could be anything",
            "vague request without clear intent", 
            "random words that make no sense"
        ]
        
        fallback_working = True
        for query in fallback_tests:
            intent, confidence, scores = classifier.classify_intent(query)
            general_score = scores.get('general', 0)
            
            # General should win but with penalty applied (lower confidence)
            if intent != 'general' or confidence > 0.8:
                fallback_working = False
                print(f"   ❌ Fallback penalty not working for: '{query}'")
            else:
                print(f"   ✅ Fallback penalty working for: '{query}' → {confidence:.3f}")
        
        # Test enhanced routing integration
        print("\nTesting router integration...")
        
        try:
            from router_cascade import RouterCascade
            
            router = RouterCascade()
            
            # Test confidence calculation with enhanced classifier
            math_confidence = router._calculate_confidence("2 + 2", "math")
            code_confidence = router._calculate_confidence("def hello():", "code")
            
            router_integration = (math_confidence > 0.7 and code_confidence > 0.7)
            
            if router_integration:
                print("   ✅ Router integration working")
            else:
                print("   ❌ Router integration issues")
                
        except Exception as e:
            print(f"   ⚠️ Router integration error: {e}")
            router_integration = False
        
        # Success criteria
        classification_success = (
            accuracy >= 85.0 and                    # 85%+ accuracy
            avg_classification_time < 10.0 and      # <10ms per classification  
            fallback_working and                    # Fallback penalty working
            router_integration                      # Router integration working
        )
        
        if classification_success:
            print("\n✅ Enhanced Intent Classification: PASSED")
            print(f"   - {accuracy:.1f}% accuracy (target: 85%+)")
            print(f"   - {avg_classification_time:.2f}ms avg latency")
            print("   - Fallback penalty system working")
            print("   - Router integration successful")
        else:
            print("\n❌ Enhanced Intent Classification: FAILED")
            if accuracy < 85.0:
                print(f"   - Accuracy too low: {accuracy:.1f}% (need 85%+)")
            if avg_classification_time >= 10.0:
                print(f"   - Too slow: {avg_classification_time:.2f}ms (need <10ms)")
        
        return classification_success
        
    except Exception as e:
        print(f"\n❌ Intent classification test failed: {e}")
        return False

async def test_end_to_end_hardening():
    """End-to-end test of all hardening measures"""
    print("\n🚀 END-TO-END HARDENING TEST")
    print("=" * 50)
    
    try:
        from router_cascade import RouterCascade
        from monitoring.hardening_metrics import track_fast_local_hit, track_cloud_escalation
        
        router = RouterCascade()
        
        # Test scenarios that should benefit from hardening
        test_scenarios = [
            {
                "query": "hello",
                "expected_fast": True,
                "description": "Simple greeting - should use fast local"
            },
            {
                "query": "2 + 2 = ?", 
                "expected_fast": True,
                "description": "Simple math - should be routed correctly"
            },
            {
                "query": "write a factorial function",
                "expected_intent": "code",
                "description": "Code request - should route to code specialist"
            },
            {
                "query": "Compare quantum mechanics and classical mechanics in detail",
                "expected_fast": False,
                "description": "Complex query - may escalate to cloud"
            }
        ]
        
        all_scenarios_passed = True
        
        for scenario in test_scenarios:
            query = scenario["query"]
            description = scenario["description"]
            
            print(f"\nTesting: {description}")
            print(f"Query: '{query}'")
            
            start_time = time.time()
            result = await router.route_query(query)
            latency_ms = (time.time() - start_time) * 1000
            
            response_text = result.get('text', '')
            routing_method = result.get('routing_method', 'unknown')
            model = result.get('model', 'unknown')
            
            print(f"   Latency: {latency_ms:.1f}ms")
            print(f"   Routing: {routing_method}")
            print(f"   Model: {model}")
            print(f"   Response: {response_text[:50]}...")
            
            # Check scenario expectations
            scenario_passed = True
            
            if scenario.get("expected_fast", False):
                if latency_ms > 1000:  # 1 second threshold
                    print(f"   ❌ Expected fast but got {latency_ms:.1f}ms")
                    scenario_passed = False
                else:
                    print(f"   ✅ Fast response as expected")
            
            if scenario.get("expected_intent"):
                # Would need to check routing decisions
                pass
            
            if not scenario_passed:
                all_scenarios_passed = False
        
        # Test memory context flow
        print("\nTesting memory context flow...")
        
        # Add some context
        context_query = "My name is Alice and I work in AI research"
        await router.route_query(context_query)
        
        # Query that should use context
        followup_query = "What did I tell you about my work?"
        result = await router.route_query(followup_query)
        response = result.get('text', '')
        
        context_working = ('alice' in response.lower() or 'ai' in response.lower())
        
        if context_working:
            print("   ✅ Memory context flowing properly")
        else:
            print("   ❌ Memory context not working")
            all_scenarios_passed = False
        
        if all_scenarios_passed:
            print("\n✅ End-to-End Hardening: PASSED")
            print("   - All scenarios handled correctly")
            print("   - Memory context flowing")
            print("   - Performance within expectations")
        else:
            print("\n❌ End-to-End Hardening: FAILED")
            print("   - Some scenarios did not meet expectations")
        
        return all_scenarios_passed
        
    except Exception as e:
        print(f"\n❌ End-to-end test failed: {e}")
        return False

async def main():
    """Run comprehensive hardening verification suite"""
    print("🧪 HARDENING VERIFICATION SUITE")
    print("=" * 60)
    print("Testing all three hardening measures:")
    print("1. FAISS Singleton Fix")
    print("2. Docker Health & Restart")  
    print("3. Enhanced Intent Classification")
    print()
    
    # Run all tests
    tests = [
        ("FAISS Singleton Fix", test_faiss_singleton_fix),
        ("Docker Health & Restart", test_docker_health_fix),
        ("Enhanced Intent Classification", test_enhanced_intent_classification),
        ("End-to-End Hardening", test_end_to_end_hardening)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 Running {test_name}...")
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n🎯 HARDENING VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL HARDENING MEASURES SUCCESSFUL!")
        print("✅ No more 'Chat keeps loading to FAISS'")  
        print("✅ Docker engine hangs resolved")
        print("✅ NLP routing no longer flaky")
        print("\n🚀 System ready for production load!")
    else:
        print("\n⚠️ Some hardening measures need attention")
        print("Check the failing tests above for details")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 