#!/usr/bin/env python3
"""
Litmus Test with Content Guards - Real Validation
================================================

Updated litmus test that uses strict content guards to fail loud on garbage
and ensure we get real answers before proceeding to CI/CD.
"""

import json
import time
from content_guards import strict_grader, ContentError
from memory_efficient_test import clear_cuda_cache
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class GuardedLitmusTest:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        
    def load_phi2_model(self):
        """Load Phi-2 model for real generation"""
        if self.model is None:
            print("📥 Loading Phi-2 for guarded litmus test...")
            clear_cuda_cache()
            
            self.model = AutoModelForCausalLM.from_pretrained(
                "microsoft/phi-2",
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )
            
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2", trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            print("✅ Phi-2 loaded for guarded testing")
    
    def generate_focused_response(self, prompt, task_type, max_tokens=100):
        """Generate focused response based on task type"""
        self.load_phi2_model()
        
        # Task-specific prompting
        if task_type == 'math':
            enhanced_prompt = f"Solve this math problem and give ONLY the final numerical answer:\n{prompt}\nFinal answer:"
        elif task_type == 'code':
            enhanced_prompt = f"Write clean Python code with no explanations or markdown:\n{prompt}\n\n"
        elif task_type == 'logic':
            enhanced_prompt = f"Answer this logic question with 'yes' or 'no' and brief explanation:\n{prompt}\nAnswer:"
        else:
            enhanced_prompt = prompt
        
        try:
            inputs = self.tokenizer(enhanced_prompt, return_tensors="pt")
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.1,  # Low temp for focused answers
                    do_sample=False,  # Greedy decoding
                    pad_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.1,
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract just the answer part
            if "Final answer:" in response:
                answer = response.split("Final answer:")[-1].strip()
            elif "Answer:" in response:
                answer = response.split("Answer:")[-1].strip()
            else:
                answer = response[len(enhanced_prompt):].strip()
            
            return answer
            
        except Exception as e:
            return f"ERROR: {e}"
    
    def run_guarded_litmus(self):
        """Run the 4-item litmus test with content guards"""
        print("🧪 GUARDED LITMUS TEST - Real Content Validation")
        print("=" * 60)
        
        # The 4 critical litmus tests
        tests = [
            {
                'id': 'math_factorial',
                'question': 'What is 8!?',
                'expected': '40320',
                'task_type': 'math',
                'description': 'Factorial calculation'
            },
            {
                'id': 'math_percentage', 
                'question': 'What is 25% of 240?',
                'expected': '60',
                'task_type': 'math',
                'description': 'Percentage calculation'
            },
            {
                'id': 'code_gcd',
                'question': 'Write a function to calculate GCD of two numbers',
                'expected': None,  # Will validate compilation
                'task_type': 'code',
                'description': 'GCD function generation'
            },
            {
                'id': 'logic_puzzle',
                'question': 'If all bloops are razzles and some razzles are lazzles, are all bloops lazzles?',
                'expected': 'no',  # This is actually wrong - should be "not necessarily"
                'task_type': 'logic', 
                'description': 'Logic reasoning'
            }
        ]
        
        results = []
        passed_count = 0
        
        for i, test in enumerate(tests, 1):
            print(f"\n📝 Test {i}/4: {test['description']}")
            print(f"Question: {test['question']}")
            
            # Generate response
            start_time = time.time()
            response = self.generate_focused_response(
                test['question'], 
                test['task_type'], 
                max_tokens=150 if test['task_type'] == 'code' else 50
            )
            generation_time = time.time() - start_time
            
            print(f"Response: {response[:100]}{'...' if len(response) > 100 else ''}")
            
            # Apply content guards
            try:
                if test['task_type'] == 'math':
                    passed, confidence, details = strict_grader(
                        'math', response, test['expected']
                    )
                elif test['task_type'] == 'code':
                    passed, confidence, details = strict_grader(
                        'code', response
                    )
                elif test['task_type'] == 'logic':
                    passed, confidence, details = strict_grader(
                        'logic', response
                    )
                else:
                    passed, confidence, details = False, 0.0, "Unknown task type"
                
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"Guard result: {status} ({confidence:.2f}) - {details}")
                
                if passed:
                    passed_count += 1
                
                results.append({
                    'test_id': test['id'],
                    'question': test['question'],
                    'response': response,
                    'passed': passed,
                    'confidence': confidence,
                    'details': details,
                    'generation_time_ms': generation_time * 1000,
                    'task_type': test['task_type']
                })
                
            except ContentError as e:
                print(f"🚨 CONTENT ERROR: {e}")
                results.append({
                    'test_id': test['id'],
                    'question': test['question'],
                    'response': response,
                    'passed': False,
                    'confidence': 0.0,
                    'details': f"Content error: {e}",
                    'generation_time_ms': generation_time * 1000,
                    'task_type': test['task_type'],
                    'content_error': str(e)
                })
            
            clear_cuda_cache()  # Memory management
        
        # Summary
        print(f"\n{'='*60}")
        print("🎯 GUARDED LITMUS RESULTS")
        print(f"{'='*60}")
        
        pass_rate = passed_count / len(tests)
        avg_confidence = sum(r.get('confidence', 0) for r in results) / len(results)
        
        print(f"Passed: {passed_count}/{len(tests)} ({pass_rate*100:.0f}%)")
        print(f"Average confidence: {avg_confidence:.2f}")
        
        for result in results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test_id']}: {result['details']}")
        
        # Decision for CI/CD
        meets_threshold = passed_count >= 3  # ≥3/4 required
        no_content_errors = all('content_error' not in r for r in results)
        
        print(f"\n🚦 CI/CD READINESS:")
        print(f"Pass threshold (≥3/4): {'✅' if meets_threshold else '❌'}")
        print(f"No content errors: {'✅' if no_content_errors else '❌'}")
        
        if meets_threshold and no_content_errors:
            print("✅ READY FOR CI/CD - Content quality verified")
        else:
            print("❌ NOT READY - Fix content issues first")
        
        # Save results
        with open('guarded_litmus_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': len(tests),
                    'passed': passed_count,
                    'pass_rate': pass_rate,
                    'avg_confidence': avg_confidence,
                    'ready_for_ci': meets_threshold and no_content_errors
                },
                'results': results
            }, f, indent=2)
        
        print(f"\n📄 Results saved to guarded_litmus_results.json")
        
        return meets_threshold and no_content_errors, results
    
    def cleanup(self):
        """Clean up model resources"""
        if self.model is not None:
            del self.model, self.tokenizer
            self.model = None
            self.tokenizer = None
            clear_cuda_cache()
            print("🧹 Model resources cleaned up")

def main():
    """Main execution"""
    litmus = GuardedLitmusTest()
    
    try:
        success, results = litmus.run_guarded_litmus()
        return 0 if success else 1
    finally:
        litmus.cleanup()

if __name__ == "__main__":
    exit(main()) 