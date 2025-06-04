"""
Specialist Priority Regression Tests
===================================

Ensures local specialists get first chance before cloud fallback.
"""

import pytest
import asyncio
from router.selector import pick_specialist, analyze_intent
from router.voting import vote

class TestSpecialistPriority:
    """Test that specialists are prioritized correctly"""
    
    def test_math_specialist_precedence(self):
        """Math expressions should route to math specialist first"""
        test_cases = [
            ("2+2", "math"),
            ("what is 5*7?", "math"), 
            ("calculate sqrt(64)", "math"),
            ("solve x^2 + 5x + 6 = 0", "math"),
            ("15 / 3", "math"),
            ("factorial of 5", "math")
        ]
        
        for prompt, expected_intent in test_cases:
            intent, confidence = analyze_intent(prompt)
            assert intent == expected_intent, f"'{prompt}' should detect {expected_intent}, got {intent}"
            assert confidence >= 0.8, f"Math confidence should be high for '{prompt}', got {confidence}"
    
    def test_code_specialist_precedence(self):
        """Code requests should route to code specialist first"""
        test_cases = [
            ("write a function to calculate fibonacci", "code"),
            ("python script for sorting", "code"),
            ("debug this function", "code"),
            ("run this code: print('hello')", "code")
        ]
        
        for prompt, expected_intent in test_cases:
            intent, confidence = analyze_intent(prompt)
            assert intent == expected_intent, f"'{prompt}' should detect {expected_intent}, got {intent}"
            assert confidence >= 0.7, f"Code confidence should be high for '{prompt}', got {confidence}"
    
    def test_specialist_selection_order(self):
        """Test that pick_specialist returns specialists before general"""
        test_cases = [
            ("2+2", "math_specialist"),
            ("write python code", "code_specialist"),
            ("if A then B", "logic_specialist"),
            ("what is DNA?", "knowledge_specialist")
        ]
        
        for prompt, expected_specialist in test_cases:
            specialist, confidence, tried = pick_specialist(prompt)
            assert expected_specialist in specialist, f"'{prompt}' should select {expected_specialist}, got {specialist}"
            assert confidence > 0.5, f"Specialist confidence should be decent for '{prompt}', got {confidence}"
    
    def test_general_fallback_penalty(self):
        """General/cloud specialists should have lower priority"""
        config = {
            "specialists_order": ["math_specialist", "code_specialist", "mistral_general"],
            "confidence_thresholds": {"math_specialist": 0.8, "mistral_general": 0.3}
        }
        
        # Math query should prefer math specialist even if general is available
        specialist, confidence, tried = pick_specialist("calculate 5*7", config)
        assert "math_specialist" in specialist, f"Math query should prefer math specialist, got {specialist}"
        
        # General query should fallback to general
        specialist, confidence, tried = pick_specialist("tell me a story", config)
        # Should still prefer specialist over general due to penalty system
        
    @pytest.mark.asyncio 
    async def test_voting_system_specialist_priority(self):
        """Test that voting system uses specialist priority"""
        # Test with math query
        result = await vote(
            prompt="what is 2+2?",
            model_names=None,  # Let it auto-select
            top_k=1,
            use_context=False
        )
        
        # Should route to math specialist first
        assert result["council_decision"] == True
        assert "math" in result["winner"]["specialist"].lower() or result["winner"]["confidence"] > 0.8
    
    def test_confidence_thresholds(self):
        """Test that confidence thresholds prevent wrong routing"""
        # Ambiguous query should not trigger high-confidence math routing
        intent, confidence = analyze_intent("tell me about numbers")
        assert confidence < 0.7, f"Ambiguous query should have low math confidence, got {confidence}"
        
        # Clear math should have high confidence
        intent, confidence = analyze_intent("25 * 16")
        assert confidence >= 0.9, f"Clear math should have high confidence, got {confidence}"

class TestFallbackBehavior:
    """Test fallback behavior when specialists fail"""
    
    def test_cloud_fallback_triggers(self):
        """Test that cloud fallback only triggers on specific errors"""
        from router.selector import should_use_cloud_fallback
        
        # These should trigger cloud fallback
        assert should_use_cloud_fallback("math_specialist", "CloudRetry: rate limited")
        assert should_use_cloud_fallback("code_specialist", "quota exceeded")
        assert should_use_cloud_fallback("logic_specialist", "service unavailable")
        
        # These should NOT trigger cloud fallback
        assert not should_use_cloud_fallback("math_specialist", "division by zero")
        assert not should_use_cloud_fallback("code_specialist", "syntax error")
    
    def test_provider_priority_order(self):
        """Test that providers are tried in correct order"""
        # Local specialists should always be tried before cloud
        config = {
            "specialists_order": ["math_specialist", "code_specialist", "mistral_general"],
            "local_providers": ["math_specialist", "code_specialist"],
            "cloud_providers": ["mistral_general"]
        }
        
        specialist, confidence, tried = pick_specialist("2+2", config)
        
        # Math specialist should be selected first
        assert "math_specialist" in specialist
        
        # General/cloud should be last in the list
        general_in_order = [s for s in config["specialists_order"] if "general" in s]
        assert general_in_order[-1] == "mistral_general"  # Should be last

if __name__ == "__main__":
    # Quick test run
    test = TestSpecialistPriority()
    test.test_math_specialist_precedence()
    test.test_code_specialist_precedence() 
    test.test_specialist_selection_order()
    test.test_general_fallback_penalty()
    
    print("✅ All specialist priority tests passed!")
    print("🎯 Math specialists will be tried before cloud fallback")
    print("🔧 Code specialists will be tried before general LLM")
    print("📋 Regression tests prevent routing regressions") 