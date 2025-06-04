#!/usr/bin/env python3
"""
Memory-Efficient Model Test
==========================

Test one model at a time with proper memory management to avoid CUDA OOM.
"""

import torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
import gc
import time

def clear_cuda_cache():
    """Clear CUDA cache to free memory"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()

def test_phi2_math():
    """Test Phi-2 for mathematical reasoning with memory management"""
    print("🧮 Testing Phi-2 Math with Memory Management")
    print("=" * 50)
    
    try:
        # Clear memory first
        clear_cuda_cache()
        
        print("📥 Loading Phi-2 model...")
        
        # Load model with memory-efficient settings
        model = AutoModelForCausalLM.from_pretrained(
            "microsoft/phi-2",
            torch_dtype=torch.float16,  # Half precision
            device_map="auto",          # Auto device placement
            trust_remote_code=True,
            low_cpu_mem_usage=True      # Reduce CPU memory usage
        )
        
        tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2", trust_remote_code=True)
        
        # Fix tokenizer padding issue
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        print("✅ Model loaded successfully")
        
        # Test the 4 critical litmus questions
        test_cases = [
            {
                'question': 'What is 8!?',
                'expected': '40320',
                'category': 'math'
            },
            {
                'question': 'What is 25% of 240?',
                'expected': '60',
                'category': 'math' 
            },
            {
                'question': 'Write a Python function to calculate GCD of two numbers',
                'expected_keywords': ['def', 'gcd'],
                'category': 'code'
            },
            {
                'question': 'Logic: All bloops are razzles. All razzles are lazzles. Are all bloops lazzles?',
                'expected': 'yes',
                'category': 'logic'
            }
        ]
        
        results = []
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n{'='*40}")
            print(f"Test {i}: {test['category'].upper()}")
            print(f"Q: {test['question']}")
            
            try:
                # Generate response with memory-efficient settings
                inputs = tokenizer(test['question'], return_tensors="pt")  # Remove padding=True
                
                # Move inputs to same device as model
                inputs = {k: v.to(model.device) for k, v in inputs.items()}
                
                with torch.no_grad():  # No gradients needed for inference
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=50,
                        temperature=0.1,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id,
                        # Memory efficient settings
                        use_cache=False,  # Don't cache for memory efficiency
                    )
                
                # Decode response
                response = tokenizer.decode(outputs[0], skip_special_tokens=True)
                
                # Remove the input prompt from response
                if response.startswith(test['question']):
                    answer = response[len(test['question']):].strip()
                else:
                    answer = response.strip()
                
                print(f"A: {answer}")
                
                # Clear memory after each generation
                clear_cuda_cache()
                
                # Grade the response
                is_garbage = any(phrase in answer.lower() for phrase in [
                    'i understand your question',
                    'response from',
                    'i appreciate your inquiry',
                    'that\'s an interesting'
                ])
                
                if is_garbage:
                    grade = "FAIL_LOUD"
                    score = 0.0
                    reason = "Template garbage"
                    print("🚨 TEMPLATE GARBAGE!")
                else:
                    if test['category'] == 'math':
                        if test['expected'] in answer:
                            grade = "PASS"
                            score = 1.0
                            reason = f"Contains {test['expected']}"
                        else:
                            grade = "FAIL"
                            score = 0.0
                            reason = f"Missing {test['expected']}"
                            
                    elif test['category'] == 'code':
                        found_keywords = [kw for kw in test['expected_keywords'] 
                                        if kw.lower() in answer.lower()]
                        if len(found_keywords) >= 2:
                            grade = "PASS"
                            score = 1.0
                            reason = f"Has keywords: {found_keywords}"
                        elif len(found_keywords) >= 1:
                            grade = "PARTIAL"
                            score = 0.5
                            reason = f"Partial: {found_keywords}"
                        else:
                            grade = "FAIL"
                            score = 0.0
                            reason = "No code keywords"
                            
                    elif test['category'] == 'logic':
                        if 'yes' in answer.lower() or 'true' in answer.lower():
                            grade = "PASS"
                            score = 1.0
                            reason = "Correct logic"
                        else:
                            grade = "FAIL"
                            score = 0.0
                            reason = "Wrong logic"
                
                print(f"Grade: {grade} ({score}/1.0) - {reason}")
                
                results.append({
                    'test': i,
                    'category': test['category'],
                    'grade': grade,
                    'score': score,
                    'is_garbage': is_garbage,
                    'answer': answer
                })
                
            except Exception as e:
                print(f"❌ Generation error: {e}")
                results.append({
                    'test': i,
                    'category': test['category'],
                    'grade': 'ERROR',
                    'score': 0.0,
                    'is_garbage': False,
                    'answer': f"ERROR: {e}"
                })
                clear_cuda_cache()  # Clear memory even on error
        
        # Summary
        print(f"\n{'='*50}")
        print("🎯 PHI-2 LITMUS RESULTS")
        print(f"{'='*50}")
        
        total = len(results)
        passed = len([r for r in results if r['grade'] == 'PASS'])
        partial = len([r for r in results if r['grade'] == 'PARTIAL'])
        failed = len([r for r in results if r['grade'] in ['FAIL', 'FAIL_LOUD']])
        errors = len([r for r in results if r['grade'] == 'ERROR'])
        garbage_count = len([r for r in results if r['is_garbage']])
        
        avg_score = sum(r['score'] for r in results) / total
        
        print(f"Tests: {total}")
        print(f"PASS: {passed} ({passed/total*100:.0f}%)")
        print(f"PARTIAL: {partial} ({partial/total*100:.0f}%)")
        print(f"FAIL: {failed} ({failed/total*100:.0f}%)")
        print(f"ERROR: {errors} ({errors/total*100:.0f}%)")
        print(f"Garbage: {garbage_count} ({garbage_count/total*100:.0f}%)")
        print(f"Score: {avg_score:.2f}/1.0")
        
        # Step 6 decision
        print(f"\n🚦 STEP 6 DECISION:")
        print(f"Required: ≥3 PASS, 0 garbage")
        print(f"Actual: {passed} PASS, {garbage_count} garbage")
        
        if passed >= 3 and garbage_count == 0:
            print("✅ PROCEED TO STEP 6 - Real answers achieved!")
            return True
        else:
            print("❌ DO NOT PROCEED - Need accuracy fixes")
            
            # Show what failed for debugging
            print("\n🔍 Failed tests:")
            for r in results:
                if r['grade'] in ['FAIL', 'FAIL_LOUD', 'ERROR']:
                    print(f"  Test {r['test']} ({r['category']}): {r['grade']} - {r.get('answer', 'No answer')[:50]}...")
            
            return False
        
    except Exception as e:
        print(f"❌ Model loading error: {e}")
        return False
        
    finally:
        # Clean up
        print("\n🧹 Cleaning up memory...")
        try:
            del model, tokenizer
        except:
            pass
        clear_cuda_cache()
        print("✅ Memory cleared")

def main():
    """Main execution"""
    print("🔧 Memory-Efficient Phi-2 Test")
    print("Testing real model accuracy before Step 6")
    
    if not torch.cuda.is_available():
        print("❌ CUDA not available - cannot test")
        return 1
    
    print(f"🔧 CUDA Device: {torch.cuda.get_device_name()}")
    print(f"🔧 CUDA Memory: {torch.cuda.get_device_properties(0).total_memory // 1024**3} GB")
    
    success = test_phi2_math()
    
    if success:
        print("\n🎉 SUCCESS: Ready for Step 6 CI/CD!")
        return 0
    else:
        print("\n⚠️ Need more accuracy work before Step 6")
        return 1

if __name__ == "__main__":
    exit(main()) 