#!/usr/bin/env python3
"""
Test vLLM API endpoints to understand the correct way to call it
"""

import requests
import time
import subprocess
import sys

def start_vllm_server():
    """Start vLLM server"""
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", "microsoft/phi-2",
        "--port", "8001",
        "--gpu-memory-utilization", "0.6",
        "--max-model-len", "512",
        "--dtype", "float16",
        "--enforce-eager"
    ]
    
    process = subprocess.Popen(cmd)
    
    # Wait for server
    print("⏱️ Waiting for vLLM server...")
    for i in range(30):
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Server ready after {i+1} seconds")
                return process
        except:
            pass
        time.sleep(1)
    
    return process

def test_endpoints():
    """Test different API endpoints"""
    print("\n🔍 Testing API endpoints...")
    
    endpoints_to_test = [
        ("GET", "/health"),
        ("GET", "/v1/models"),
        ("POST", "/v1/completions"),
        ("POST", "/v1/chat/completions"),
        ("POST", "/generate"),
        ("POST", "/v1/generate")
    ]
    
    for method, endpoint in endpoints_to_test:
        try:
            url = f"http://localhost:8001{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:  # POST
                test_data = {
                    "prompt": "What is 2+2?",
                    "max_tokens": 10,
                    "temperature": 0.1
                }
                response = requests.post(url, json=test_data, timeout=5)
            
            print(f"{method} {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ Success: {str(data)[:100]}...")
                except:
                    print(f"  ✅ Success (non-JSON): {response.text[:100]}...")
            else:
                print(f"  ❌ Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"{method} {endpoint}: ERROR - {e}")
    
def test_working_endpoint():
    """Test with the working endpoint once we find it"""
    print("\n🧪 Testing math with working endpoint...")
    
    # Try the standard OpenAI format first
    try:
        response = requests.post(
            "http://localhost:8001/v1/completions",
            json={
                "model": "microsoft/phi-2", 
                "prompt": "What is 8 factorial?\n",
                "max_tokens": 50,
                "temperature": 0.1,
                "stop": ["\n\n"]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['text'].strip()
            print(f"Math Answer: '{answer}'")
            
            if "40320" in answer:
                print("✅ CORRECT - Found 40320!")
                return True
            else:
                print("❌ Wrong - 40320 not found")
                return False
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Main test"""
    print("🧪 vLLM API Test")
    
    # Start server
    process = start_vllm_server()
    
    try:
        # Test endpoints
        test_endpoints()
        
        # Test actual generation
        success = test_working_endpoint()
        
        if success:
            print("\n🎉 SUCCESS: vLLM generating real math answers!")
        else:
            print("\n⚠️ Still need to debug API calls")
            
    finally:
        print("\n🧹 Stopping server...")
        process.terminate()

if __name__ == "__main__":
    main() 