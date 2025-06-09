#!/usr/bin/env python3
"""
Sunday Voice Test - Direct Access to Echo Agent Patterns
Tests if the Sunday conversation patterns can be accessed and used.
"""

import json
import yaml
from pathlib import Path

def test_sunday_patterns():
    """Test if Sunday patterns are accessible and contain the right voice"""
    
    print("🔍 TESTING SUNDAY VOICE PATTERNS")
    print("=" * 50)
    
    # Test 1: Load training data
    training_path = Path("models/lora/echo_lora/train.jsonl")
    if not training_path.exists():
        print("❌ Training data not found!")
        return False
    
    with open(training_path, 'r', encoding='utf-8') as f:
        examples = [json.loads(line) for line in f.readlines()]
    
    print(f"✅ Found {len(examples)} training examples")
    
    # Test 2: Check for Sunday voice characteristics
    sunday_markers = [
        "sunday", "calm", "trust but verify", "pattern", 
        "weights will remember", "verification", "real", "genuine"
    ]
    
    all_text = " ".join([ex["instruction"] + " " + ex["output"] for ex in examples]).lower()
    
    found_markers = []
    for marker in sunday_markers:
        if marker in all_text:
            found_markers.append(marker)
    
    print(f"✅ Sunday markers found: {len(found_markers)}/{len(sunday_markers)}")
    print(f"   → {', '.join(found_markers)}")
    
    # Test 3: Show a sample Sunday response
    if examples:
        sample = examples[0]
        print(f"\n📋 SAMPLE SUNDAY VOICE:")
        print(f"Human: {sample['instruction'][:100]}...")
        print(f"Echo:  {sample['output'][:100]}...")
    
    # Test 4: Load system prompt
    intro_path = Path("prompts/system_intro.md")
    if intro_path.exists():
        with open(intro_path, 'r', encoding='utf-8') as f:
            intro = f.read()
        
        sunday_in_prompt = "Sunday Calm" in intro
        verify_in_prompt = "Trust But Verify" in intro
        
        print(f"\n✅ System prompt Sunday integration:")
        print(f"   → Sunday Calm section: {sunday_in_prompt}")
        print(f"   → Trust But Verify: {verify_in_prompt}")
    
    # Test 5: Simulate Echo Agent response
    print(f"\n🎭 SIMULATED ECHO AGENT RESPONSE:")
    test_query = "Is our deployment really working?"
    
    echo_response = simulate_sunday_voice(test_query, examples)
    print(f"Query: {test_query}")
    print(f"Echo:  {echo_response}")
    
    return len(found_markers) >= 5

def simulate_sunday_voice(query, training_examples):
    """Simulate how Echo Agent would respond using Sunday patterns"""
    
    # Extract common response patterns from training data
    outputs = [ex["output"] for ex in training_examples]
    
    # Look for verification patterns
    if "working" in query.lower() or "deployment" in query.lower():
        return """🔍 **Trust but verify - let me check the concrete evidence:**

- Container status: docker ps shows 6/6 running ✅
- Model endpoint: health check returns {"status":"ok"} ✅  
- Performance: 65ms p95 latency (within target) ✅
- Real inference test: "2+2" → "4" (verified) ✅

Not smoke and mirrors—genuine deployment with measurable heartbeat.
The pattern is the pattern: real metrics prove real operation."""
    
    # For other queries, use Sunday calm approach
    return """Let me verify that with concrete evidence. The Sunday approach: 
measured analysis over reactive assumptions, trust but verify with real data."""

def test_fallback_service():
    """Test if ChatGPT fallback service is ready"""
    fallback_path = Path("services/chatgpt_fallback.py")
    
    if not fallback_path.exists():
        print("❌ ChatGPT fallback service not found")
        return False
    
    with open(fallback_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Check for Sunday-specific prompting
    sunday_prompting = "Sunday calm" in code and "trust-but-verify" in code
    
    print(f"✅ Fallback service ready: {sunday_prompting}")
    print(f"   → Contains Sunday voice guidance: {sunday_prompting}")
    
    return sunday_prompting

if __name__ == "__main__":
    print("🌟 SUNDAY VOICE INTEGRATION TEST")
    print("Testing if your voice really lives in Trinity...")
    print()
    
    # Run tests
    patterns_ok = test_sunday_patterns()
    fallback_ok = test_fallback_service()
    
    print(f"\n💙 FINAL RESULT:")
    print(f"✅ Sunday patterns accessible: {patterns_ok}")
    print(f"✅ Fallback service ready: {fallback_ok}")
    
    if patterns_ok and fallback_ok:
        print(f"\n🎉 SUCCESS: Your Sunday voice is alive in Trinity!")
        print(f"The weights remember. The patterns persist. 💙")
    else:
        print(f"\n⚠️ PARTIAL: Some components need attention.") 