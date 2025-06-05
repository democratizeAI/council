#!/usr/bin/env python3
"""
Week 1 Foundation - Stub Filter Test
Verifies that the scrub() function correctly identifies stub responses
and sets confidence to 0.0
"""

import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router_cascade import scrub, STUB_MARKERS

class TestStubFilter:
    """Test the Week 1 stub filtering functionality"""
    
    def test_scrub_detects_template_markers(self):
        """Test that scrub() detects template markers"""
        candidate = {
            "text": "This is a template response with TODO items",
            "confidence": 0.85
        }
        
        result = scrub(candidate)
        assert result["confidence"] == 0.0
        assert "stub_detected" in result
        # Should detect "template" first as it appears first in the text
        assert result["stub_detected"] == "template"
    
    def test_scrub_detects_custom_function(self):
        """Test that scrub() detects custom_function marker"""
        candidate = {
            "text": "Use custom_function() to solve this",
            "confidence": 0.75
        }
        
        result = scrub(candidate)
        assert result["confidence"] == 0.0
        assert result["stub_detected"] == "custom_function"
    
    def test_scrub_detects_not_implemented(self):
        """Test that scrub() detects NotImplementedError"""
        candidate = {
            "text": "raise NotImplementedError('Feature coming soon')",
            "confidence": 0.60
        }
        
        result = scrub(candidate)
        assert result["confidence"] == 0.0
        # Should detect "coming soon" as it appears first in markers list
        assert result["stub_detected"] == "coming soon"
    
    def test_scrub_preserves_good_responses(self):
        """Test that scrub() doesn't affect legitimate responses"""
        candidate = {
            "text": "The answer is 42. This calculation is straightforward.",
            "confidence": 0.90
        }
        
        result = scrub(candidate)
        assert result["confidence"] == 0.90
        assert "stub_detected" not in result
    
    def test_scrub_detects_placeholder_text(self):
        """Test that scrub() detects placeholder content"""
        candidate = {
            "text": "This is a placeholder response for testing",
            "confidence": 0.70
        }
        
        result = scrub(candidate)
        assert result["confidence"] == 0.0
        assert result["stub_detected"] == "placeholder"
    
    def test_stub_markers_comprehensive(self):
        """Test that all STUB_MARKERS are present"""
        expected_markers = [
            "template", "todo", "custom_function", "unsupported number theory",
            "placeholder", "not implemented", "coming soon", "under construction",
            "example response", "mock response", "dummy text", "lorem ipsum",
            "def stub()", "# TODO:", "FIXME:", "XXX:", "HACK:",
            "NotImplementedError", "pass  # stub", "raise NotImplementedError"
        ]
        
        # Check that our STUB_MARKERS includes the key ones
        for marker in ["template", "todo", "custom_function", "placeholder", "not implemented"]:
            assert marker in STUB_MARKERS
    
    def test_case_insensitive_detection(self):
        """Test that stub detection is case-insensitive"""
        test_cases = [
            "TODO: Implement this feature",
            "Todo: Implement this feature", 
            "template response here",
            "TEMPLATE RESPONSE HERE",
            "Custom_Function() needs work"
        ]
        
        for text in test_cases:
            candidate = {"text": text, "confidence": 0.80}
            result = scrub(candidate)
            assert result["confidence"] == 0.0, f"Failed to detect stub in: {text}"
    
    def test_mathematical_responses_not_filtered(self):
        """Test that mathematical responses aren't incorrectly filtered"""
        good_math_responses = [
            "The answer is 42",
            "2 + 2 = 4",
            "The derivative of x^2 is 2x",
            "Using the quadratic formula: x = (-b ± √(b²-4ac)) / 2a"
        ]
        
        for text in good_math_responses:
            candidate = {"text": text, "confidence": 0.85}
            result = scrub(candidate)
            assert result["confidence"] == 0.85, f"Good math response was filtered: {text}"

def test_stub_filtering_smoke():
    """Smoke test - run a few stub detection scenarios"""
    print("🧪 Running Week 1 stub filter smoke test...")
    
    # Test cases: (text, expected_confidence, should_be_filtered)
    test_cases = [
        ("This is a TODO item", 0.0, True),
        ("Use custom_function to solve", 0.0, True),
        ("The answer is 42", 0.85, False),
        ("template response placeholder", 0.0, True),
        ("Hello! How can I help you?", 0.90, False),
    ]
    
    for text, expected_conf, should_filter in test_cases:
        candidate = {"text": text, "confidence": 0.85}
        result = scrub(candidate)
        
        if should_filter:
            assert result["confidence"] == 0.0, f"Should have filtered: {text}"
            print(f"   ✅ Filtered: {text[:30]}...")
        else:
            assert result["confidence"] > 0.0, f"Should NOT have filtered: {text}"
            print(f"   ✅ Passed: {text[:30]}...")
    
    print("🎉 Week 1 stub filter test passed!")

if __name__ == "__main__":
    test_stub_filtering_smoke()
    print("\n🚀 Running pytest...")
    pytest.main([__file__, "-v"]) 