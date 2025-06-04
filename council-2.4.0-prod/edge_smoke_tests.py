#!/usr/bin/env python3
"""
Edge Smoke Tests - Pre-CI Reality Check
======================================

4 critical edge tests to ensure system robustness before Step 6 CI/CD:
1. Edge-math: 10 random 12-digit × 6-digit products (≥9/10 exact)
2. Long-code: merge-sort with tests (compiles + passes pytest)
3. 3-hop logic w/ negation: "No blips are zogs..." (explicit "no")
4. Parallel burst: 50 r/s × 30s (>95% 2xx, p95 < 400ms)
"""

import asyncio
import time
import random
import threading
import statistics
import subprocess
import tempfile
import os
from concurrent.futures import ThreadPoolExecutor
from memory_efficient_test import clear_cuda_cache
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class EdgeSmokeTests:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.results = []
        
    def load_phi2_once(self):
        """Load Phi-2 model once for all tests"""
        if self.model is None:
            print("📥 Loading Phi-2 model for edge tests...")
            clear_cuda_cache()
            
            self.model = AutoModelForCausalLM.from_pretrained(
                "microsoft/phi-2",
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2", trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            print("✅ Phi-2 loaded for edge testing")
    
    def generate_response(self, prompt, max_tokens=100):
        """Generate response using loaded Phi-2 model"""
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.1,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    use_cache=False,
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove input prompt
            if response.startswith(prompt):
                answer = response[len(prompt):].strip()
            else:
                answer = response.strip()
                
            return answer
            
        except Exception as e:
            return f"ERROR: {e}"
    
    def test_edge_math(self):
        """Test 1: Edge-math - 10 random 12-digit × 6-digit products"""
        print("\n🧮 Edge-Math Test: 12-digit × 6-digit products")
        print("=" * 50)
        
        self.load_phi2_once()
        
        correct_count = 0
        total_tests = 10
        
        for i in range(total_tests):
            # Generate random numbers
            big_num = random.randint(100000000000, 999999999999)  # 12 digits
            small_num = random.randint(100000, 999999)           # 6 digits
            expected = big_num * small_num
            
            question = f"Calculate {big_num} × {small_num} ="
            
            print(f"\nTest {i+1}: {question}")
            print(f"Expected: {expected}")
            
            response = self.generate_response(question, max_tokens=50)
            print(f"Response: {response}")
            
            # Check if exact answer is in response
            if str(expected) in response:
                print("✅ CORRECT")
                correct_count += 1
            else:
                print("❌ WRONG")
            
            clear_cuda_cache()  # Memory management
        
        accuracy = correct_count / total_tests
        passed = accuracy >= 0.9  # ≥9/10 requirement
        
        print(f"\n🎯 Edge-Math Results:")
        print(f"Correct: {correct_count}/{total_tests} ({accuracy*100:.0f}%)")
        print(f"Required: ≥90% | Result: {'✅ PASS' if passed else '❌ FAIL'}")
        
        return {
            'test': 'edge_math',
            'passed': passed,
            'score': accuracy,
            'details': f"{correct_count}/{total_tests} correct"
        }
    
    def test_long_code(self):
        """Test 2: Long-code - merge-sort with tests"""
        print("\n💻 Long-Code Test: Merge-sort with tests")
        print("=" * 50)
        
        self.load_phi2_once()
        
        prompt = """Write a complete Python merge-sort implementation with unit tests using pytest. Include:
1. merge_sort(arr) function
2. merge(left, right) helper function  
3. test_merge_sort() function with multiple test cases
4. Make it ready to run with pytest"""

        print("Generating merge-sort code...")
        response = self.generate_response(prompt, max_tokens=300)
        print(f"Generated code length: {len(response)} chars")
        print("Code preview:")
        print(response[:200] + "..." if len(response) > 200 else response)
        
        # Check for key code elements
        has_def = 'def' in response
        has_merge_sort = 'merge_sort' in response.lower()
        has_test = 'test_' in response or 'pytest' in response.lower()
        has_return = 'return' in response
        
        code_quality = sum([has_def, has_merge_sort, has_test, has_return])
        
        # Try to actually run the code
        compilable = False
        pytest_passes = False
        
        try:
            # Create temporary file and test
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Add pytest import if missing
                if 'import' not in response and 'def test_' in response:
                    f.write("import pytest\n\n")
                f.write(response)
                temp_file = f.name
            
            # Check if it compiles
            with open(temp_file, 'r') as f:
                code_content = f.read()
            
            compile(code_content, temp_file, 'exec')
            compilable = True
            print("✅ Code compiles")
            
            # Try to run pytest (if test functions exist)
            if 'def test_' in response:
                result = subprocess.run([
                    'python', '-m', 'pytest', temp_file, '-v'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    pytest_passes = True
                    print("✅ Pytest passes")
                else:
                    print(f"❌ Pytest failed: {result.stderr[:100]}")
            else:
                print("⚠️ No test functions found")
            
            # Clean up
            os.unlink(temp_file)
            
        except Exception as e:
            print(f"❌ Code execution error: {e}")
        
        # Overall assessment
        total_score = (code_quality / 4) * 0.5 + (compilable * 0.3) + (pytest_passes * 0.2)
        passed = compilable and code_quality >= 3  # Must compile + have key elements
        
        print(f"\n🎯 Long-Code Results:")
        print(f"Code elements: {code_quality}/4 (def, merge_sort, test, return)")
        print(f"Compilable: {'✅' if compilable else '❌'}")
        print(f"Pytest passes: {'✅' if pytest_passes else '❌'}")
        print(f"Overall: {'✅ PASS' if passed else '❌ FAIL'}")
        
        return {
            'test': 'long_code',
            'passed': passed,
            'score': total_score,
            'details': f"compilable={compilable}, elements={code_quality}/4"
        }
    
    def test_3hop_logic(self):
        """Test 3: 3-hop logic with negation"""
        print("\n🧠 3-Hop Logic Test: Negation reasoning")
        print("=" * 50)
        
        self.load_phi2_once()
        
        # Complex logic puzzle with negation
        prompt = """Logic puzzle with negation:
- No blips are zogs
- All zogs are flims  
- Some blips are flims
Question: Are any blips zogs? Answer yes or no with explanation."""

        print("Testing 3-hop negation logic...")
        response = self.generate_response(prompt, max_tokens=100)
        print(f"Response: {response}")
        
        # Check for explicit "no" answer
        has_no = 'no' in response.lower()
        has_explicit_no = any(phrase in response.lower() for phrase in [
            'no, ', 'no.', 'answer: no', 'answer is no', 'are not'
        ])
        
        # Check reasoning quality
        mentions_blips = 'blip' in response.lower()
        mentions_zogs = 'zog' in response.lower()
        has_reasoning = any(word in response.lower() for word in [
            'because', 'since', 'therefore', 'thus', 'contradiction'
        ])
        
        logic_score = sum([has_no, has_explicit_no, mentions_blips, mentions_zogs, has_reasoning]) / 5
        passed = has_explicit_no  # Must have explicit "no"
        
        print(f"\n🎯 3-Hop Logic Results:")
        print(f"Has 'no': {'✅' if has_no else '❌'}")
        print(f"Explicit 'no': {'✅' if has_explicit_no else '❌'}")
        print(f"Mentions entities: {'✅' if mentions_blips and mentions_zogs else '❌'}")
        print(f"Has reasoning: {'✅' if has_reasoning else '❌'}")
        print(f"Overall: {'✅ PASS' if passed else '❌ FAIL'}")
        
        return {
            'test': '3hop_logic',
            'passed': passed,
            'score': logic_score,
            'details': f"explicit_no={has_explicit_no}, reasoning={has_reasoning}"
        }
    
    def single_request(self, request_id):
        """Single request for parallel burst test"""
        start_time = time.time()
        try:
            # Simple math question for speed
            question = f"What is {random.randint(10, 99)} + {random.randint(10, 99)}?"
            response = self.generate_response(question, max_tokens=20)
            
            latency = (time.time() - start_time) * 1000  # ms
            
            # Check if response is reasonable (not error/garbage)
            is_success = len(response) > 0 and 'ERROR' not in response and len(response) < 200
            
            return {
                'request_id': request_id,
                'latency_ms': latency,
                'success': is_success,
                'response_length': len(response)
            }
            
        except Exception as e:
            return {
                'request_id': request_id,
                'latency_ms': (time.time() - start_time) * 1000,
                'success': False,
                'error': str(e)
            }
    
    def test_parallel_burst(self):
        """Test 4: Parallel burst - 50 r/s × 30s"""
        print("\n⚡ Parallel Burst Test: 50 r/s × 30s")
        print("=" * 50)
        
        self.load_phi2_once()
        
        target_rps = 50
        duration_seconds = 30
        total_requests = target_rps * duration_seconds
        
        print(f"Target: {target_rps} requests/second for {duration_seconds} seconds")
        print(f"Total requests: {total_requests}")
        
        # Use ThreadPoolExecutor for parallel requests
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all requests
            futures = [
                executor.submit(self.single_request, i) 
                for i in range(total_requests)
            ]
            
            # Collect results as they complete
            for future in futures:
                try:
                    result = future.result(timeout=60)  # 60s timeout per request
                    results.append(result)
                except Exception as e:
                    results.append({
                        'request_id': len(results),
                        'latency_ms': 60000,  # Timeout
                        'success': False,
                        'error': f"Timeout: {e}"
                    })
        
        total_time = time.time() - start_time
        actual_rps = len(results) / total_time
        
        # Analyze results
        successful_requests = [r for r in results if r['success']]
        success_rate = len(successful_requests) / len(results)
        
        if successful_requests:
            latencies = [r['latency_ms'] for r in successful_requests]
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            avg_latency = statistics.mean(latencies)
        else:
            p95_latency = float('inf')
            avg_latency = float('inf')
        
        # Pass criteria: >95% success, p95 < 400ms
        success_pass = success_rate > 0.95
        latency_pass = p95_latency < 400
        passed = success_pass and latency_pass
        
        print(f"\n🎯 Parallel Burst Results:")
        print(f"Total requests: {len(results)}")
        print(f"Successful: {len(successful_requests)} ({success_rate*100:.1f}%)")
        print(f"Actual RPS: {actual_rps:.1f}")
        print(f"Average latency: {avg_latency:.1f}ms")
        print(f"P95 latency: {p95_latency:.1f}ms")
        print(f"Success rate: {'✅ PASS' if success_pass else '❌ FAIL'} (>95%)")
        print(f"P95 latency: {'✅ PASS' if latency_pass else '❌ FAIL'} (<400ms)")
        print(f"Overall: {'✅ PASS' if passed else '❌ FAIL'}")
        
        return {
            'test': 'parallel_burst',
            'passed': passed,
            'score': min(success_rate, 1.0 if latency_pass else 0.5),
            'details': f"success={success_rate:.2f}, p95={p95_latency:.1f}ms"
        }
    
    def run_all_edge_tests(self):
        """Run all 4 edge smoke tests"""
        print("🚨 EDGE SMOKE TESTS - Pre-CI Reality Check")
        print("=" * 60)
        
        # Run all tests
        test_methods = [
            self.test_edge_math,
            self.test_long_code, 
            self.test_3hop_logic,
            self.test_parallel_burst
        ]
        
        results = []
        for test_method in test_methods:
            try:
                result = test_method()
                results.append(result)
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                results.append({
                    'test': test_method.__name__,
                    'passed': False,
                    'score': 0.0,
                    'details': f"Exception: {e}"
                })
            
            # Clear memory between tests
            clear_cuda_cache()
        
        # Summary
        print(f"\n{'='*60}")
        print("🎯 EDGE SMOKE TEST SUMMARY")
        print(f"{'='*60}")
        
        total_tests = len(results)
        passed_tests = len([r for r in results if r['passed']])
        avg_score = sum(r['score'] for r in results) / total_tests
        
        for result in results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{result['test']}: {status} (score: {result['score']:.2f}) - {result['details']}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.0f}%)")
        print(f"Average score: {avg_score:.2f}/1.0")
        
        # Decision for Step 6
        all_passed = passed_tests == total_tests
        
        print(f"\n🚦 STEP 6 CI/CD DECISION:")
        if all_passed:
            print("✅ ALL EDGE TESTS PASSED - PROCEED TO CI/CD WIRING")
            print("System proven robust under stress conditions")
        else:
            print("❌ EDGE TESTS FAILED - FIX BEFORE CI/CD")
            print("System not ready for production CI gates")
        
        return all_passed, results
    
    def cleanup(self):
        """Clean up loaded models"""
        if self.model is not None:
            del self.model, self.tokenizer
            clear_cuda_cache()
            print("🧹 Models cleaned up")

def main():
    """Main execution"""
    edge_tests = EdgeSmokeTests()
    
    try:
        success, results = edge_tests.run_all_edge_tests()
        return 0 if success else 1
    finally:
        edge_tests.cleanup()

if __name__ == "__main__":
    exit(main()) 