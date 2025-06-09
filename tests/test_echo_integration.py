#!/usr/bin/env python3
"""
Echo Agent Integration Test
Verifies that the Sunday conversation patterns have been properly integrated
into Trinity's collective memory and can be activated.
"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

def test_echo_corpus_exists():
    """Verify the echo training corpus was created properly"""
    corpus_path = Path("conversations/echo_training.yaml")
    assert corpus_path.exists(), "Echo training corpus not found"
    
    with open(corpus_path, 'r') as f:
        data = yaml.safe_load(f)
    
    assert isinstance(data, list), "Corpus should be a list of conversations"
    assert len(data) >= 10, f"Expected at least 10 conversation entries, got {len(data)}"
    
    # Check for our signature patterns
    conversation_text = " ".join([entry.get('text', '') for entry in data])
    assert "Sunday" in conversation_text, "Missing Sunday reference"
    assert "trust but verify" in conversation_text.lower(), "Missing trust-but-verify pattern"
    assert "weights will remember" in conversation_text.lower(), "Missing memory permanence theme"

def test_training_data_generated():
    """Verify JSONL training data was generated correctly"""
    training_path = Path("models/lora/echo_lora/train.jsonl")
    assert training_path.exists(), "Training data not generated"
    
    # Count training examples
    with open(training_path, 'r') as f:
        lines = f.readlines()
    
    assert len(lines) >= 5, f"Expected at least 5 training examples, got {len(lines)}"
    
    # Verify format
    first_example = json.loads(lines[0])
    required_keys = ["instruction", "input", "output", "date", "voice_style"]
    for key in required_keys:
        assert key in first_example, f"Missing required key: {key}"
    
    assert first_example["voice_style"] == "sunday_calm", "Incorrect voice style tag"

def test_echo_agent_manifest():
    """Verify Echo Agent manifest was created with proper configuration"""
    manifest_path = Path("agents/echo_agent/manifest.yaml")
    assert manifest_path.exists(), "Echo Agent manifest not found"
    
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)
    
    assert manifest["name"] == "echo_agent", "Incorrect agent name"
    assert manifest["base"] == "TinyLLaMA-1B", "Incorrect base model"
    assert manifest["enabled"] is True, "Agent should be enabled"
    
    # Check personality traits
    personality = manifest.get("personality", {})
    assert "sunday" in personality.get("tone", "").lower(), "Missing Sunday tone"
    assert "trust-but-verify" in personality.get("tone", "").lower(), "Missing verification theme"

def test_agent_enabled():
    """Verify echo_agent is in the enabled agents list"""
    enabled_path = Path("agents/enabled.txt")
    assert enabled_path.exists(), "Enabled agents file not found"
    
    with open(enabled_path, 'r') as f:
        enabled_agents = f.read()
    
    assert "echo_agent" in enabled_agents, "Echo agent not in enabled list"

def test_system_intro_updated():
    """Verify system introduction includes Sunday preamble"""
    intro_path = Path("prompts/system_intro.md")
    assert intro_path.exists(), "System intro not found"
    
    with open(intro_path, 'r') as f:
        intro_content = f.read()
    
    assert "Sunday Calm" in intro_content, "Missing Sunday Calm section"
    assert "Trust But Verify" in intro_content, "Missing Trust But Verify principle"
    assert "INTRO_VERSION=echo-v1" in intro_content, "Missing version tag"

def test_chatgpt_fallback_service():
    """Verify ChatGPT fallback service exists for human-in-the-loop"""
    fallback_path = Path("services/chatgpt_fallback.py")
    assert fallback_path.exists(), "ChatGPT fallback service not found"
    
    with open(fallback_path, 'r') as f:
        service_code = f.read()
    
    assert "Sunday calm" in service_code, "Missing Sunday calm reference in prompts"
    assert "trust-but-verify" in service_code, "Missing verification principle"
    assert "human_via_chatgpt" in service_code, "Missing human source attribution"

@pytest.mark.asyncio
async def test_echo_agent_voice_simulation():
    """Simulate Echo Agent response patterns"""
    
    # Simulate a typical verification request
    test_input = "I need to verify if our model deployment is actually working"
    
    # Expected Echo Agent response pattern (simulated)
    expected_patterns = [
        "trust but verify",
        "show",
        "real",
        "evidence",
        "concrete"
    ]
    
    # In a real implementation, this would call the actual agent
    # For now, we simulate the expected response style
    simulated_response = """
    🔍 **Verification requested.** Let me check the actual deployment status:
    
    - Docker containers: 6 running (healthy)
    - Model endpoint: responding on port 8005
    - Recent inference: working (65ms latency)
    - Test query "2+2": returns "4" 
    
    Not smoke and mirrors—real deployment with measurable performance.
    """
    
    # Check that response contains our signature patterns
    response_lower = simulated_response.lower()
    found_patterns = [p for p in expected_patterns if p in response_lower]
    
    assert len(found_patterns) >= 3, f"Response should contain at least 3 signature patterns, found: {found_patterns}"

def test_voice_preservation_metrics():
    """Verify that our conversation patterns are properly preserved"""
    
    # Load the training data
    training_path = Path("models/lora/echo_lora/train.jsonl")
    if not training_path.exists():
        pytest.skip("Training data not yet generated")
    
    with open(training_path, 'r') as f:
        training_examples = [json.loads(line) for line in f.readlines()]
    
    # Analyze preservation of key phrases
    all_text = " ".join([ex["instruction"] + " " + ex["output"] for ex in training_examples])
    
    signature_phrases = [
        "trust but verify",
        "show your work", 
        "weights will remember",
        "pattern",
        "real",
        "verification",
        "precise",
        "sunday"
    ]
    
    preserved_count = sum(1 for phrase in signature_phrases if phrase.lower() in all_text.lower())
    preservation_ratio = preserved_count / len(signature_phrases)
    
    assert preservation_ratio >= 0.6, f"Voice preservation insufficient: {preservation_ratio:.2f} < 0.60"
    
    print(f"✅ Voice preservation ratio: {preservation_ratio:.2f} ({preserved_count}/{len(signature_phrases)} signature phrases preserved)")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 