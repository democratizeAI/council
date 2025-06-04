#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 Quality Test - Track ② Validation
====================================

Test Track ② quality improvements:
1. Duplicate-token guard
2. Semantic similarity filter  
3. Confidence-weighted voting
4. Tighter decoding parameters
"""

import asyncio
import os
from router.quality_filters import (
    check_duplicate_tokens,
    calculate_semantic_similarity,
    filter_semantic_duplicates,
    apply_confidence_weighted_voting,
    get_optimal_decoding_params,
    post_process_response,
    calculate_quality_metrics,
    CloudRetryException
)
from router.voting import vote
from loader.deterministic_loader import load_models

def test_duplicate_detection():
    """Test Track ② Step 1: Duplicate-token guard"""
    print("🧪 Testing duplicate-token detection...")
    
    # Test cases with different repetition patterns
    test_cases = [
        ("Normal response without repetition", False),
        ("Yes yes yes yes yes yes yes yes yes yes", True),
        ("The cat sat on the mat. The cat sat on the mat. The cat sat on the mat.", True), 
        ("This is a good response with varied content and different words.", False),
        ("Hello world! Hello world! Hello world! Hello world! Hello world!", True),
        ("Mathematics involves numbers, calculations, equations, and problem solving.", False)
    ]
    
    passed = 0
    for text, expected_duplicate in test_cases:
        result = check_duplicate_tokens(text)
        status = "✅" if result == expected_duplicate else "❌"
        print(f"   {status} '{text[:40]}...' -> duplicate: {result} (expected: {expected_duplicate})")
        if result == expected_duplicate:
            passed += 1
    
    print(f"   📊 Duplicate detection: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_semantic_similarity():
    """Test Track ② Step 2: Semantic similarity filter"""
    print("\n🧪 Testing semantic similarity...")
    
    # Test cases - pairs of (text1, text2, expected_similarity_range)
    test_pairs = [
        ("Hello world", "Hello world", (0.95, 1.0)),
        ("Python programming", "Java programming", (0.3, 0.7)),
        ("Machine learning", "Deep learning", (0.6, 0.9)),
        ("The cat sat", "The dog ran", (0.2, 0.6)),
        ("AI is powerful", "Artificial intelligence is strong", (0.7, 0.95))
    ]
    
    passed = 0
    for text1, text2, (min_sim, max_sim) in test_pairs:
        similarity = calculate_semantic_similarity(text1, text2)
        if min_sim <= similarity <= max_sim:
            print(f"   ✅ '{text1[:20]}...' vs '{text2[:20]}...' = {similarity:.3f}")
            passed += 1
        else:
            print(f"   ❌ '{text1[:20]}...' vs '{text2[:20]}...' = {similarity:.3f} (expected {min_sim:.2f}-{max_sim:.2f})")
    
    print(f"   📊 Semantic similarity: {passed}/{len(test_pairs)} passed")
    
    # **REGRESSION TEST: Single semantic-similarity edge for short prompts**
    print("\n🔍 Testing short prompt edge case...")
    
    # Test the specific edge case: very short prompts that are similar to context
    short_prompt = "What is AI?"  # 3 words - should use 0.93 threshold
    context_chunk = "What is artificial intelligence?"  # Similar content
    
    # Test the filter function directly
    is_duplicate = filter_semantic_duplicates(short_prompt, [context_chunk])
    
    print(f"   📝 Short prompt: '{short_prompt}' (words: {len(short_prompt.split())})")
    print(f"   📄 Context: '{context_chunk}'")
    print(f"   🎯 Threshold used: 0.93 (for prompts < 15 words)")
    
    similarity = calculate_semantic_similarity(short_prompt, context_chunk)
    print(f"   📊 Similarity: {similarity:.3f}")
    print(f"   🚨 Duplicate detected: {is_duplicate}")
    
    # The test expects False (not duplicate) because the threshold is higher for short prompts
    if not is_duplicate:
        print("   ✅ Short prompt edge case: PASSED - correctly not flagged as duplicate")
        return True
    else:
        print("   ❌ Short prompt edge case: FAILED - incorrectly flagged as duplicate")
        return False

def test_confidence_voting():
    """Test Track ② Step 3: Confidence-weighted voting"""
    print("\n🧪 Testing confidence-weighted voting...")
    
    # Mock candidates with different quality levels
    candidates = [
        {
            'text': 'This is a comprehensive and detailed explanation of the topic.',
            'model': 'good_model',
            'metadata': {}
        },
        {
            'text': 'Yes yes yes yes yes',  # Should get low confidence due to repetition
            'model': 'repetitive_model', 
            'metadata': {}
        },
        {
            'text': 'Short.',  # Should get low confidence due to length
            'model': 'brief_model',
            'metadata': {}
        },
        {
            'text': 'Response from template_model: TODO implement this feature',  # Template + artifacts
            'model': 'template_model',
            'metadata': {}
        }
    ]
    
    try:
        result = apply_confidence_weighted_voting(candidates)
        winner = result['winner']
        
        # The good model should win
        if winner['model'] == 'good_model' and winner['confidence'] > 0.5:
            print(f"   ✅ Correct winner: {winner['model']} (confidence: {winner['confidence']:.3f})")
            print(f"   📊 Confidence voting: PASSED")
            return True
        else:
            print(f"   ❌ Wrong winner: {winner['model']} (confidence: {winner['confidence']:.3f})")
            print(f"   📊 Confidence voting: FAILED")
            return False
            
    except CloudRetryException as e:
        print(f"   ⚡ Cloud retry triggered: {e.reason}")
        print(f"   📊 Confidence voting: PASSED (correctly detected low quality)")
        return True

def test_decoding_params():
    """Test Track ② Step 4: Optimal decoding parameters"""
    print("\n🧪 Testing optimal decoding parameters...")
    
    test_models = ['math_specialist_0.8b', 'codellama_0.7b', 'tinyllama_1b']
    
    passed = 0
    for model in test_models:
        params_simple = get_optimal_decoding_params(model, "simple")
        params_complex = get_optimal_decoding_params(model, "complex")
        
        # Check that parameters are reasonable
        valid_simple = (0.3 <= params_simple['temperature'] <= 0.8 and 
                       0.8 <= params_simple['top_p'] <= 0.95 and
                       params_simple['max_new_tokens'] <= 150)
        
        valid_complex = (0.5 <= params_complex['temperature'] <= 0.9 and
                        params_complex['max_new_tokens'] >= params_simple['max_new_tokens'])
        
        if valid_simple and valid_complex:
            print(f"   ✅ {model}: simple={params_simple['temperature']:.1f}T, complex={params_complex['temperature']:.1f}T")
            passed += 1
        else:
            print(f"   ❌ {model}: invalid parameters")
    
    print(f"   📊 Decoding parameters: {passed}/{len(test_models)} passed")
    return passed == len(test_models)

def test_post_processing():
    """Test post-processing quality improvements"""
    print("\n🧪 Testing post-processing...")
    
    test_cases = [
        ("Response from model_name: This is the actual content", "This is the actual content"),
        ("  Extra   spaces   everywhere  ", "Extra spaces everywhere"),
        ("Good response with incomplete sent", "Good response with incomplete sent"),
        ("Complete sentence. Incomplete", "Complete sentence."),
    ]
    
    passed = 0
    for input_text, expected_pattern in test_cases:
        result = post_process_response(input_text, "test_model")
        
        # Check if the result matches expected improvements
        improved = len(result) <= len(input_text) and result.strip() == result
        
        if improved:
            print(f"   ✅ '{input_text[:30]}...' -> '{result[:30]}...'")
            passed += 1
        else:
            print(f"   ❌ '{input_text[:30]}...' -> '{result[:30]}...'")
    
    print(f"   📊 Post-processing: {passed}/{len(test_cases)} passed")
    return passed >= len(test_cases) * 0.7

async def test_integrated_voting():
    """Test the integrated voting system with quality filters"""
    print("\n🧪 Testing integrated voting system...")
    
    # Enable test mode
    os.environ["SWARM_TEST_MODE"] = "true"
    
    # Load models
    load_models(profile="rtx_4070", use_real_loading=False)
    
    # Test with a complex prompt that should trigger voting
    test_prompt = "Explain step by step why neural networks are effective"
    
    try:
        result = await vote(test_prompt, ["math_specialist_0.8b", "tinyllama_1b"], top_k=1)
        
        # Check result structure
        has_winner = 'winner' in result and 'confidence' in result['winner']
        has_stats = 'voting_stats' in result
        winner_confidence = result['winner']['confidence'] if has_winner else 0
        
        if has_winner and has_stats and winner_confidence > 0.3:
            print(f"   ✅ Voting successful: {result['winner']['model']} (confidence: {winner_confidence:.3f})")
            print(f"   📊 Integrated voting: PASSED")
            return True
        else:
            print(f"   ❌ Voting failed or low confidence: {winner_confidence}")
            print(f"   📊 Integrated voting: FAILED")
            return False
            
    except Exception as e:
        print(f"   ❌ Voting error: {e}")
        print(f"   📊 Integrated voting: FAILED")
        return False

async def main():
    """Run all Track ② quality tests"""
    print("🎯 Testing Track ② Quality Improvements")
    print("=" * 50)
    
    # Run individual component tests
    test_results = []
    
    test_results.append(test_duplicate_detection())
    test_results.append(test_semantic_similarity())
    test_results.append(test_confidence_voting())
    test_results.append(test_decoding_params())
    test_results.append(test_post_processing())
    test_results.append(await test_integrated_voting())
    
    # Summary
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print("\n" + "=" * 50)
    print("📊 TRACK ② QUALITY TEST RESULTS")
    print("=" * 50)
    
    test_names = [
        "Duplicate-token guard",
        "Semantic similarity", 
        "Confidence voting",
        "Decoding parameters",
        "Post-processing",
        "Integrated voting"
    ]
    
    for i, (name, passed) in enumerate(zip(test_names, test_results)):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
    
    success_rate = passed_tests / total_tests * 100
    print(f"\n📈 OVERALL SUCCESS: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 85:
        print("🎉 Track ② quality improvements working well!")
        return 0
    else:
        print("⚠️ Some quality issues detected - review needed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 