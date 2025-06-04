#!/usr/bin/env python3
"""
Simple vLLM Fix - Memory-Efficient Model Serving
=================================================

Skip quantization complexity and focus on memory-efficient serving
with vLLM to get real answers instead of template garbage.
"""

import subprocess
import time
import requests
import json
import sys
import signal
from pathlib import Path

def check_vllm_availability():
    """Check if vLLM is available, install if needed"""
    print("🔍 Checking vLLM availability...")
    
    try:
        import vllm
        print("✅ vLLM already available")
        return True
    except ImportError:
        print("📦 Installing vLLM...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "vllm"], 
                          check=True)
            print("✅ vLLM installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install vLLM")
            return False

def start_lightweight_vllm():
    """Start a single lightweight vLLM server for testing"""
    print("🚀 Starting lightweight vLLM server...")
    
    # Use a very memory-efficient configuration
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", "microsoft/phi-2",
        "--port", "8001", 
        "--gpu-memory-utilization", "0.8",  # Use 80% of available GPU memory
        "--max-model-len", "1024",          # Reasonable context length
        "--dtype", "float16",               # Half precision to save memory
        "--enforce-eager",                  # Disable CUDA graphs to save memory
        "--disable-log-stats"               # Reduce logging overhead
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Start server in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("⏱️ Waiting for server to start (60 seconds)...")
        
        # Wait for server to be ready
        max_wait = 60
        for i in range(max_wait):
            if test_vllm_health():
                print(f"✅ vLLM server ready after {i+1} seconds")
                return process
            time.sleep(1)
            
            # Check if process crashed
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"❌ Server crashed:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return None
        
        print("⚠️ Server timeout - may still be starting")
        return process
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def test_vllm_health():
    """Test if vLLM server is healthy"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def test_vllm_generation(prompt, max_tokens=50):
    """Test generation via OpenAI-compatible API"""
    try:
        response = requests.post(
            "http://localhost:8001/v1/completions",
            json={
                "model": "microsoft/phi-2",
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": 0.1,
                "stop": ["\n\n", "Question:", "Q:"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['text'].strip()
        else:
            return f"HTTP Error {response.status_code}: {response.text}"
            
    except Exception as e:
        return f"Error: {e}"

def run_litmus_tests():
    """Run the 4 critical litmus tests"""
    print("\n🧪 Running Litmus Tests with vLLM...")
    
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
            'question': 'Write a Python function to calculate GCD',
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
        print(f"\n{'='*50}")
        print(f"Test {i}: {test['category'].upper()}")
        print(f"Q: {test['question']}")
        
        # Generate response
        response = test_vllm_generation(test['question'], max_tokens=100)
        print(f"A: {response}")
        
        # Check for template garbage
        is_garbage = any(phrase in response.lower() for phrase in [
            'i understand your question',
            'response from',
            'i appreciate your inquiry',
            'that\'s an interesting'
        ])
        
        if is_garbage:
            grade = "FAIL_LOUD"
            score = 0.0
            reason = "Template garbage detected"
            print("🚨 TEMPLATE GARBAGE!")
        else:
            # Grade based on category
            if test['category'] == 'math':
                if test['expected'] in response:
                    grade = "PASS"
                    score = 1.0
                    reason = f"Contains {test['expected']}"
                else:
                    grade = "FAIL"
                    score = 0.0
                    reason = f"Missing {test['expected']}"
                    
            elif test['category'] == 'code':
                found_keywords = [kw for kw in test['expected_keywords'] 
                                if kw.lower() in response.lower()]
                if len(found_keywords) >= 2:
                    grade = "PASS"
                    score = 1.0
                    reason = f"Has keywords: {found_keywords}"
                elif len(found_keywords) >= 1:
                    grade = "PARTIAL"
                    score = 0.5
                    reason = f"Partial keywords: {found_keywords}"
                else:
                    grade = "FAIL"
                    score = 0.0
                    reason = "No code keywords"
                    
            elif test['category'] == 'logic':
                if 'yes' in response.lower() or 'true' in response.lower():
                    grade = "PASS"
                    score = 1.0
                    reason = "Correct logic"
                else:
                    grade = "FAIL"
                    score = 0.0
                    reason = "Wrong/unclear logic"
        
        print(f"Grade: {grade} ({score}/1.0) - {reason}")
        
        results.append({
            'test': i,
            'category': test['category'],
            'grade': grade,
            'score': score,
            'is_garbage': is_garbage
        })
    
    # Summary
    print(f"\n{'='*50}")
    print("🎯 LITMUS RESULTS SUMMARY")
    print(f"{'='*50}")
    
    total = len(results)
    passed = len([r for r in results if r['grade'] == 'PASS'])
    partial = len([r for r in results if r['grade'] == 'PARTIAL'])
    failed = len([r for r in results if r['grade'] in ['FAIL', 'FAIL_LOUD']])
    garbage_count = len([r for r in results if r['is_garbage']])
    
    avg_score = sum(r['score'] for r in results) / total
    
    print(f"Tests: {total}")
    print(f"PASS: {passed} ({passed/total*100:.0f}%)")
    print(f"PARTIAL: {partial} ({partial/total*100:.0f}%)")
    print(f"FAIL: {failed} ({failed/total*100:.0f}%)")
    print(f"Garbage: {garbage_count} ({garbage_count/total*100:.0f}%)")
    print(f"Score: {avg_score:.2f}/1.0")
    
    # Decision criteria from user
    print(f"\n🚦 STEP 6 DECISION CRITERIA:")
    print(f"Required: ≥3 PASS, 0 garbage")
    print(f"Actual: {passed} PASS, {garbage_count} garbage")
    
    if passed >= 3 and garbage_count == 0:
        print("✅ PROCEED TO STEP 6 - Real answers achieved!")
        return True
    else:
        print("❌ DO NOT PROCEED - Still need accuracy fixes")
        return False

def main():
    """Main execution"""
    print("🔧 Simple vLLM Fix - Getting Real Answers")
    print("=" * 50)
    
    # Check vLLM
    if not check_vllm_availability():
        return 1
    
    # Start server
    process = start_lightweight_vllm()
    if not process:
        print("❌ Failed to start vLLM server")
        return 1
    
    try:
        # Run tests
        success = run_litmus_tests()
        
        if success:
            print("\n🎉 SUCCESS: Ready for Step 6!")
            return 0
        else:
            print("\n⚠️ Need more work on accuracy")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏸️ Interrupted by user")
        return 1
        
    finally:
        # Cleanup
        if process:
            print("\n🧹 Stopping vLLM server...")
            try:
                process.terminate()
                process.wait(timeout=5)
                print("✅ Server stopped cleanly")
            except:
                process.kill()
                print("⚡ Server force-killed")

if __name__ == "__main__":
    exit(main()) 