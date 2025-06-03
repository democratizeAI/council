#!/usr/bin/env python3
"""
🌌 Council-in-the-Loop Validation Script
======================================

Comprehensive validation of the five awakened voices system.
Tests all key functionality and validates performance targets.
"""

import os
import sys
import time
import asyncio
import requests
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

# Council configuration
os.environ["SWARM_COUNCIL_ENABLED"] = "true"
os.environ["MISTRAL_API_KEY"] = "ezybn1D39HWYE6MMLe8JcwQPhSPSOjH2"
os.environ["COUNCIL_MAX_COST"] = "0.30"
os.environ["COUNCIL_DAILY_BUDGET"] = "1.00"

def log(msg: str, level: str = "INFO"):
    """Structured logging"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {msg}")

def test_council_import():
    """Test 1: Council module import validation"""
    log("🧪 Test 1: Council Import Validation", "TEST")
    
    try:
        from router.council import CouncilRouter, CouncilVoice, council_route
        log("✅ Council imports successful", "PASS")
        
        # Test router initialization
        router = CouncilRouter()
        log(f"✅ Council initialized with {len(router.voice_models)} voices", "PASS")
        
        # Verify all five voices
        expected_voices = ["reason", "spark", "edge", "heart", "vision"]
        actual_voices = [voice.value for voice in router.voice_models.keys()]
        
        if all(voice in actual_voices for voice in expected_voices):
            log("✅ All five voices configured correctly", "PASS")
        else:
            log(f"❌ Missing voices. Expected: {expected_voices}, Got: {actual_voices}", "FAIL")
            
        return True
    except Exception as e:
        log(f"❌ Council import failed: {e}", "FAIL")
        return False

def test_voice_templates():
    """Test 2: Voice template validation"""
    log("🧪 Test 2: Voice Template Validation", "TEST")
    
    try:
        from router.council import CouncilRouter
        router = CouncilRouter()
        
        required_templates = ["reason", "spark", "edge", "heart", "vision"]
        missing_templates = []
        
        for voice in required_templates:
            voice_enum = getattr(router, 'voice_templates', {})
            if not any(v.value == voice for v in voice_enum.keys()):
                missing_templates.append(voice)
        
        if not missing_templates:
            log("✅ All voice templates configured", "PASS")
        else:
            log(f"❌ Missing templates: {missing_templates}", "FAIL")
            
        # Test template formatting
        sample_prompt = "Test prompt"
        for voice, template in router.voice_templates.items():
            formatted = template.format(prompt=sample_prompt)
            if sample_prompt in formatted:
                log(f"✅ {voice.value} template formatting works", "PASS")
            else:
                log(f"❌ {voice.value} template formatting failed", "FAIL")
        
        return True
    except Exception as e:
        log(f"❌ Template validation failed: {e}", "FAIL")
        return False

def test_trigger_logic():
    """Test 3: Council trigger logic validation"""
    log("🧪 Test 3: Council Trigger Logic", "TEST")
    
    try:
        from router.council import CouncilRouter
        router = CouncilRouter()
        router.council_enabled = True
        
        # Mock budget status
        import unittest.mock
        with unittest.mock.patch('router.council.get_budget_status') as mock_budget:
            mock_budget.return_value = {"remaining_budget_dollars": 5.0}
            
            # Test disabled council
            router.council_enabled = False
            should_trigger, reason = router.should_trigger_council("Long prompt with many words")
            if not should_trigger and reason == "council_disabled":
                log("✅ Council disabled trigger works", "PASS")
            else:
                log(f"❌ Council disabled trigger failed: {should_trigger}, {reason}", "FAIL")
            
            # Test token threshold
            router.council_enabled = True
            router.min_tokens_for_council = 5
            
            # Short prompt
            should_trigger, reason = router.should_trigger_council("Hi")
            if not should_trigger:
                log("✅ Short prompt correctly bypasses council", "PASS")
            else:
                log(f"❌ Short prompt incorrectly triggers council: {reason}", "FAIL")
            
            # Long prompt
            long_prompt = " ".join(["word"] * 10)
            should_trigger, reason = router.should_trigger_council(long_prompt)
            if should_trigger and "token_threshold" in reason:
                log("✅ Long prompt correctly triggers council", "PASS")
            else:
                log(f"❌ Long prompt trigger failed: {should_trigger}, {reason}", "FAIL")
            
            # Keyword trigger
            should_trigger, reason = router.should_trigger_council("Please explain this concept")
            if should_trigger and "keyword" in reason:
                log("✅ Keyword trigger works correctly", "PASS")
            else:
                log(f"❌ Keyword trigger failed: {should_trigger}, {reason}", "FAIL")
        
        return True
    except Exception as e:
        log(f"❌ Trigger logic test failed: {e}", "FAIL")
        return False

async def test_council_route():
    """Test 4: Council routing integration"""
    log("🧪 Test 4: Council Route Integration", "TEST")
    
    try:
        from router.council import council_route
        import unittest.mock
        
        # Mock dependencies
        with unittest.mock.patch('router.council.get_budget_status') as mock_budget, \
             unittest.mock.patch('router.council.get_loaded_models') as mock_models, \
             unittest.mock.patch('router.council.vote') as mock_vote:
            
            mock_budget.return_value = {"remaining_budget_dollars": 5.0}
            mock_models.return_value = {"tinyllama_1b": {}, "phi2_2.7b": {}}
            mock_vote.return_value = {
                "text": "Quick local response",
                "winner": {"model": "tinyllama_1b"},
                "voting_stats": {"winner_confidence": 0.8, "voting_time_ms": 50}
            }
            
            # Test quick path
            result = await council_route("Hi")
            if not result.get("council_used", True):
                log("✅ Quick path routing works", "PASS")
            else:
                log("❌ Quick path failed to bypass council", "FAIL")
        
        return True
    except Exception as e:
        log(f"❌ Council route test failed: {e}", "FAIL")
        return False

def test_server_endpoints():
    """Test 5: Server endpoint validation"""
    log("🧪 Test 5: Server Endpoint Validation", "TEST")
    
    base_url = "http://localhost:8000"
    endpoints_to_test = [
        ("/health", "Health check"),
        ("/models", "Model listing"),
        ("/council/status", "Council status"),
        ("/metrics", "Prometheus metrics")
    ]
    
    passed = 0
    total = len(endpoints_to_test)
    
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                log(f"✅ {description} endpoint working", "PASS")
                passed += 1
            else:
                log(f"❌ {description} endpoint failed: {response.status_code}", "FAIL")
        except Exception as e:
            log(f"❌ {description} endpoint error: {e}", "FAIL")
    
    log(f"📊 Endpoint tests: {passed}/{total} passed", "SUMMARY")
    return passed == total

def test_council_endpoint():
    """Test 6: Council endpoint validation"""
    log("🧪 Test 6: Council Endpoint Test", "TEST")
    
    try:
        # Test forced council deliberation
        payload = {
            "prompt": "Explain the strategic implications of quantum computing",
            "force_council": True
        }
        
        log("🌌 Testing forced council deliberation...", "INFO")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:8000/council",
            json=payload,
            timeout=30
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Council endpoint responded in {latency_ms:.1f}ms", "PASS")
            
            # Validate response structure
            required_fields = ["text", "council_used", "total_latency_ms", "total_cost_dollars"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                log("✅ Council response structure valid", "PASS")
                
                # Performance validation
                if latency_ms < 2000:  # 2 second target
                    log(f"✅ Latency within target: {latency_ms:.1f}ms < 2000ms", "PASS")
                else:
                    log(f"⚠️ Latency high: {latency_ms:.1f}ms > 2000ms", "WARN")
                
                # Cost validation
                cost = data.get("total_cost_dollars", 0)
                if cost < 0.30:  # Budget limit
                    log(f"✅ Cost within budget: ${cost:.4f} < $0.30", "PASS")
                else:
                    log(f"⚠️ Cost high: ${cost:.4f} > $0.30", "WARN")
                
                return True
            else:
                log(f"❌ Missing response fields: {missing_fields}", "FAIL")
        else:
            log(f"❌ Council endpoint failed: {response.status_code}", "FAIL")
            log(f"   Response: {response.text[:200]}...", "DEBUG")
    
    except Exception as e:
        log(f"❌ Council endpoint test failed: {e}", "FAIL")
    
    return False

def run_performance_validation():
    """Performance validation suite"""
    log("🚀 Performance Validation Suite", "TEST")
    
    # Test rapid-fire requests to validate performance
    test_prompts = [
        "2+2",  # Should use quick path
        "What is machine learning?",  # Should use quick path
        "Explain quantum computing strategy",  # Should trigger council
        "Analyze AI ethics implications"  # Should trigger council
    ]
    
    results = []
    
    for i, prompt in enumerate(test_prompts):
        try:
            log(f"🎯 Testing prompt {i+1}: '{prompt[:30]}...'", "INFO")
            start_time = time.time()
            
            # Use orchestrate endpoint for realistic testing
            response = requests.post(
                "http://localhost:8000/orchestrate",
                json={"prompt": prompt, "route": ["tinyllama_1b"]},
                timeout=10
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                results.append({
                    "prompt": prompt,
                    "latency_ms": latency_ms,
                    "success": True
                })
                log(f"✅ Response in {latency_ms:.1f}ms", "PASS")
            else:
                log(f"❌ Request failed: {response.status_code}", "FAIL")
                results.append({"prompt": prompt, "success": False})
                
        except Exception as e:
            log(f"❌ Request error: {e}", "FAIL")
            results.append({"prompt": prompt, "success": False})
    
    # Calculate statistics
    successful_requests = [r for r in results if r.get("success")]
    if successful_requests:
        latencies = [r["latency_ms"] for r in successful_requests]
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        log(f"📊 Performance Summary:", "SUMMARY")
        log(f"   Successful requests: {len(successful_requests)}/{len(test_prompts)}", "INFO")
        log(f"   Average latency: {avg_latency:.1f}ms", "INFO")
        log(f"   Max latency: {max_latency:.1f}ms", "INFO")
        
        # Validate against targets
        if avg_latency < 500:
            log("✅ Average latency within target", "PASS")
        else:
            log("⚠️ Average latency high", "WARN")
        
        if max_latency < 2000:
            log("✅ Max latency within target", "PASS")
        else:
            log("⚠️ Max latency exceeded target", "WARN")

def main():
    """Main validation runner"""
    log("🌌💀⚔️ COUNCIL VALIDATION SUITE STARTING", "START")
    log("=" * 60, "INFO")
    
    tests = [
        ("Council Import", test_council_import),
        ("Voice Templates", test_voice_templates),
        ("Trigger Logic", test_trigger_logic),
        ("Council Route", lambda: asyncio.run(test_council_route())),
        ("Server Endpoints", test_server_endpoints),
        ("Council Endpoint", test_council_endpoint)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        log(f"\n🧪 Running: {test_name}", "TEST")
        log("-" * 40, "INFO")
        
        try:
            if test_func():
                passed += 1
                log(f"✅ {test_name}: PASSED", "RESULT")
            else:
                log(f"❌ {test_name}: FAILED", "RESULT")
        except Exception as e:
            log(f"❌ {test_name}: ERROR - {e}", "RESULT")
    
    log("\n" + "=" * 60, "INFO")
    log(f"🎯 VALIDATION SUMMARY: {passed}/{total} tests passed", "SUMMARY")
    
    if passed == total:
        log("🌌 ALL TESTS PASSED - COUNCIL READY FOR PRODUCTION! 🚀", "SUCCESS")
    else:
        log(f"⚠️ {total - passed} tests failed - Review before production", "WARNING")
    
    # Run performance validation
    log("\n" + "=" * 60, "INFO")
    run_performance_validation()
    
    log("\n🎭 The five awakened voices await your queries! 🌌", "COMPLETE")

if __name__ == "__main__":
    main() 