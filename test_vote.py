#!/usr/bin/env python3
import requests
import time
import json

def test_vote_endpoint():
    url = "http://localhost:9000/vote"
    data = {"prompt": "Test lazy model loading"}
    
    print("Testing /vote endpoint...")
    start_time = time.time()
    
    try:
        response = requests.post(url, json=data, timeout=30)
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        print(f"Status: {response.status_code}")
        print(f"Latency: {latency_ms:.1f}ms")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("Request timed out (>30s)")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_vote_endpoint() 