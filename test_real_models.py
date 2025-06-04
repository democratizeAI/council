#!/usr/bin/env python3
"""
Real Model Testing - Accuracy Check Before Step 6
================================================================

Tests the actual model loading and generation to ensure we get real answers
instead of template/mock responses before proceeding to CI/CD.
"""

import asyncio
import time
from loader.deterministic_loader import load_models, generate_response, get_loaded_models

async def test_real_model_accuracy():
    """Test that real models produce accurate answers instead of template garbage"""
    
    print("🔧 Loading real models...")
    
    # Load models with real backends
    summary = load_models(profile='rtx_4070', use_real_loading=True)
    print(f"✅ Loaded {len(summary['loaded_models'])} models: {summary['loaded_models']}")
    print(f"🔧 Backends used: {summary['backends_used']}")
    
    # Test key litmus questions
    test_cases = [
        {
            'question': 'What is 8!?',
            'expected_answer': '40320',
            'category': 'math'
        },
        {
            'question': 'What is 25% of 240?', 
            'expected_answer': '60',
            'category': 'math'
        },
        {
            'question': 'Write a Python function to calculate GCD of two numbers',
            'expected_keywords': ['def', 'gcd', 'return'],
            'category': 'code'
        },
        {
            'question': 'Logic puzzle: All bloops are razzles. All razzles are lazzles. Are all bloops lazzles?',
            'expected_answer': 'yes',
            'category': 'logic'
        }
    ]
    
    # Get the loaded models
    loaded_models = get_loaded_models()
    print(f"\nAvailable models: {list(loaded_models.keys())}")
    
    # Test with the best available model
    test_model = 'tinyllama_1b'  # This should be loaded as microsoft/phi-2
    if test_model not in loaded_models:
        print(f"❌ Model {test_model} not available")
        return
    
    model_info = loaded_models[test_model]
    print(f"\n🧪 Testing {test_model} (backend: {model_info['backend']}, type: {model_info['type']})")
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test_case['category'].upper()}")
        print(f"Question: {test_case['question']}")
        
        try:
            # Generate response
            start_time = time.time()
            response = generate_response(test_model, test_case['question'], max_tokens=100)
            generation_time = time.time() - start_time
            
            print(f"Response: '{response}'")
            print(f"Time: {generation_time:.2f}s")
            
            # Check for template garbage
            is_template = any(phrase in response.lower() for phrase in [
                'i understand your question',
                'that\'s an interesting topic', 
                'i appreciate your inquiry',
                'let me provide a thoughtful response',
                'i can help with'
            ])
            
            if is_template:
                print("🚨 TEMPLATE/GARBAGE DETECTED")
                grade = "FAIL_LOUD"
                score = 0.0
                reason = "Template response detected"
            else:
                # Grade the response
                if test_case['category'] == 'math':
                    expected = test_case['expected_answer']
                    if expected in response:
                        grade = "PASS"
                        score = 1.0
                        reason = f"Contains correct answer: {expected}"
                    else:
                        grade = "FAIL"
                        score = 0.0
                        reason = f"Expected {expected}, not found in response"
                        
                elif test_case['category'] == 'code':
                    expected_keywords = test_case['expected_keywords']
                    found_keywords = [kw for kw in expected_keywords if kw.lower() in response.lower()]
                    if len(found_keywords) >= 2:
                        grade = "PASS"
                        score = 1.0
                        reason = f"Contains code keywords: {found_keywords}"
                    elif len(found_keywords) >= 1:
                        grade = "PARTIAL"
                        score = 0.5
                        reason = f"Partial keywords found: {found_keywords}"
                    else:
                        grade = "FAIL"
                        score = 0.0
                        reason = "No code keywords found"
                        
                elif test_case['category'] == 'logic':
                    if 'yes' in response.lower() or 'true' in response.lower():
                        grade = "PASS"
                        score = 1.0
                        reason = "Correct logical reasoning"
                    else:
                        grade = "FAIL"
                        score = 0.0
                        reason = "Incorrect or unclear logical reasoning"
                        
            print(f"Grade: {grade} ({score}/1.0)")
            print(f"Reason: {reason}")
            
            results.append({
                'question': test_case['question'],
                'category': test_case['category'],
                'response': response,
                'grade': grade,
                'score': score,
                'reason': reason,
                'time': generation_time,
                'is_template': is_template
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                'question': test_case['question'],
                'category': test_case['category'],
                'response': f"ERROR: {e}",
                'grade': "ERROR",
                'score': 0.0,
                'reason': str(e),
                'time': 0.0,
                'is_template': False
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("🎯 REAL MODEL ACCURACY SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(results)
    passed = len([r for r in results if r['grade'] == 'PASS'])
    partial = len([r for r in results if r['grade'] == 'PARTIAL'])
    failed = len([r for r in results if r['grade'] in ['FAIL', 'FAIL_LOUD']])
    errors = len([r for r in results if r['grade'] == 'ERROR'])
    template_count = len([r for r in results if r['is_template']])
    
    avg_score = sum(r['score'] for r in results) / total_tests if total_tests > 0 else 0.0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed} ({passed/total_tests*100:.1f}%)")
    print(f"Partial: {partial} ({partial/total_tests*100:.1f}%)")  
    print(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")
    print(f"Errors: {errors} ({errors/total_tests*100:.1f}%)")
    print(f"Template Responses: {template_count} ({template_count/total_tests*100:.1f}%)")
    print(f"Average Score: {avg_score:.2f}/1.0")
    
    # Decision
    print(f"\n🚦 STEP 6 DECISION:")
    if passed >= 3 and template_count == 0:
        print("✅ PROCEED TO STEP 6 - Models are generating real answers")
        print("   ≥3 PASS ✓, 0 template garbage ✓")
        return True
    else:
        print("❌ DO NOT PROCEED TO STEP 6 - Fix accuracy first")
        print(f"   Need ≥3 PASS (got {passed}), 0 templates (got {template_count})")
        print("   Recommendations:")
        if template_count > 0:
            print("   - Fix template/mock fallback issues")
        if passed < 3:
            print("   - Improve model accuracy or switch to better models")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_real_model_accuracy())
    exit(0 if success else 1) 