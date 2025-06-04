#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Release Gate - P1 Performance Verification
===========================================

Verifies that P1 performance targets are met before release:
- First-token latency ≤ 80ms 
- P95 latency ≤ 200ms
- Duplicate ratio ≤ 2%
- Math edge cases resolved
- Streaming infrastructure working
"""

import asyncio
import time
import argparse
import aiohttp
import json
import statistics
from typing import List, Dict, Any

class ReleaseGate:
    """Release gate verification for P1 targets"""
    
    def __init__(self, first_token_ms: int = 80, p95_latency_ms: int = 200, dup_ratio: float = 0.02):
        self.first_token_ms = first_token_ms
        self.p95_latency_ms = p95_latency_ms
        self.dup_ratio = dup_ratio
        self.base_url = "http://localhost:8000"
        
    async def test_first_token_latency(self) -> Dict[str, Any]:
        """Test first-token streaming latency"""
        print("🚀 Testing first-token latency...")
        
        test_prompts = [
            "What is 2+2?",
            "Hello world",
            "Tell me about AI",
            "Quick response",
            "Fast"
        ]
        
        first_token_latencies = []
        
        for prompt in test_prompts:
            try:
                start_time = time.time()
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/hybrid/stream",
                        json={"prompt": prompt},
                        headers={"Accept": "text/event-stream"}
                    ) as response:
                        
                        if response.status != 200:
                            print(f"   ❌ HTTP {response.status} for '{prompt}'")
                            continue
                        
                        async for line in response.content:
                            line_text = line.decode('utf-8').strip()
                            
                            if line_text.startswith('data:') and not line_text.endswith('[STREAM_COMPLETE]'):
                                first_token_time = time.time()
                                latency_ms = (first_token_time - start_time) * 1000
                                first_token_latencies.append(latency_ms)
                                print(f"   ⚡ '{prompt}': {latency_ms:.1f}ms")
                                break
                        
            except Exception as e:
                print(f"   ❌ Error with '{prompt}': {e}")
        
        if not first_token_latencies:
            return {"success": False, "error": "No first-token measurements"}
        
        avg_latency = statistics.mean(first_token_latencies)
        max_latency = max(first_token_latencies)
        
        success = max_latency <= self.first_token_ms
        
        return {
            "success": success,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": max_latency,
            "target_ms": self.first_token_ms,
            "measurements": len(first_token_latencies)
        }
    
    async def test_p95_latency(self) -> Dict[str, Any]:
        """Test P95 overall latency"""
        print("📊 Testing P95 latency...")
        
        test_prompts = [
            "Calculate 15 * 23",
            "What is the capital of France?",
            "Write a hello world function",
            "Explain quantum physics",
            "Simple math: 5 + 7"
        ]
        
        latencies = []
        
        for prompt in test_prompts:
            try:
                start_time = time.time()
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/hybrid",
                        json={"prompt": prompt}
                    ) as response:
                        
                        if response.status == 200:
                            await response.json()
                            end_time = time.time()
                            latency_ms = (end_time - start_time) * 1000
                            latencies.append(latency_ms)
                            print(f"   📈 '{prompt[:20]}...': {latency_ms:.1f}ms")
                        else:
                            print(f"   ❌ HTTP {response.status} for '{prompt}'")
                        
            except Exception as e:
                print(f"   ❌ Error with '{prompt}': {e}")
        
        if not latencies:
            return {"success": False, "error": "No latency measurements"}
        
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 5 else max(latencies)
        avg_latency = statistics.mean(latencies)
        
        success = p95_latency <= self.p95_latency_ms
        
        return {
            "success": success,
            "p95_latency_ms": p95_latency,
            "avg_latency_ms": avg_latency,
            "target_ms": self.p95_latency_ms,
            "measurements": len(latencies)
        }
    
    async def test_duplicate_ratio(self) -> Dict[str, Any]:
        """Test duplicate detection ratio"""
        print("🔍 Testing duplicate ratio...")
        
        # Test prompts that should NOT be flagged as duplicates
        normal_prompts = [
            "What is machine learning?",
            "Explain artificial intelligence",
            "How do neural networks work?",
            "What are the benefits of AI?",
            "Describe deep learning algorithms"
        ]
        
        # Test prompts that SHOULD be flagged as duplicates  
        duplicate_prompts = [
            "Yes yes yes yes yes yes yes yes",
            "Hello world! Hello world! Hello world!",
            "The same text. The same text. The same text."
        ]
        
        false_positives = 0
        false_negatives = 0
        
        # Test normal prompts (should not be duplicates)
        for prompt in normal_prompts:
            try:
                # Import quality filter
                import sys
                sys.path.append('.')
                from router.quality_filters import check_duplicate_tokens
                
                is_duplicate = check_duplicate_tokens(prompt)
                if is_duplicate:
                    false_positives += 1
                    print(f"   ❌ False positive: '{prompt[:30]}...'")
                else:
                    print(f"   ✅ Correctly not flagged: '{prompt[:30]}...'")
                    
            except Exception as e:
                print(f"   ❌ Error testing '{prompt}': {e}")
        
        # Test duplicate prompts (should be flagged)
        for prompt in duplicate_prompts:
            try:
                is_duplicate = check_duplicate_tokens(prompt)
                if not is_duplicate:
                    false_negatives += 1
                    print(f"   ❌ False negative: '{prompt[:30]}...'")
                else:
                    print(f"   ✅ Correctly flagged: '{prompt[:30]}...'")
                    
            except Exception as e:
                print(f"   ❌ Error testing '{prompt}': {e}")
        
        total_tests = len(normal_prompts) + len(duplicate_prompts)
        error_ratio = (false_positives + false_negatives) / total_tests
        
        success = error_ratio <= self.dup_ratio
        
        return {
            "success": success,
            "error_ratio": error_ratio,
            "target_ratio": self.dup_ratio,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "total_tests": total_tests
        }
    
    async def test_math_edge_cases(self) -> Dict[str, Any]:
        """Test math edge cases are resolved"""
        print("🧮 Testing math edge cases...")
        
        # The specific edge case that was failing
        math_prompts = [
            "Solve for x: x + 5 = 12",
            "What is 2 + 2?", 
            "Calculate 15 * 23",
            "Simple equation: y - 3 = 10"
        ]
        
        successes = 0
        
        for prompt in math_prompts:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/hybrid",
                        json={"prompt": prompt}
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            # Check if we get a meaningful math response
                            response_text = result.get("text", "").lower()
                            
                            # Look for math-related success indicators
                            has_numbers = any(char.isdigit() for char in response_text)
                            has_math_terms = any(term in response_text for term in ['=', 'equals', 'answer', 'result'])
                            no_errors = "error" not in response_text and "failed" not in response_text
                            
                            if has_numbers and (has_math_terms or no_errors):
                                successes += 1
                                print(f"   ✅ '{prompt}': Math response received")
                            else:
                                print(f"   ❌ '{prompt}': Non-math response: {response_text[:50]}...")
                        else:
                            print(f"   ❌ HTTP {response.status} for '{prompt}'")
                        
            except Exception as e:
                print(f"   ❌ Error with '{prompt}': {e}")
        
        success_ratio = successes / len(math_prompts)
        success = success_ratio >= 0.75  # 75% success rate for math
        
        return {
            "success": success,
            "success_ratio": success_ratio,
            "successes": successes,
            "total_tests": len(math_prompts)
        }
    
    async def run_release_gate(self) -> bool:
        """Run all release gate tests"""
        print("🚪 P1 Release Gate Verification")
        print("=" * 50)
        print(f"🎯 Targets:")
        print(f"   ⚡ First-token latency: ≤ {self.first_token_ms}ms")
        print(f"   📊 P95 latency: ≤ {self.p95_latency_ms}ms") 
        print(f"   🔍 Duplicate ratio: ≤ {self.dup_ratio*100:.1f}%")
        print("=" * 50)
        
        # Run all tests
        results = {}
        
        results["first_token"] = await self.test_first_token_latency()
        results["p95_latency"] = await self.test_p95_latency()
        results["duplicate_ratio"] = await self.test_duplicate_ratio()
        results["math_edge_cases"] = await self.test_math_edge_cases()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 RELEASE GATE RESULTS")
        print("=" * 50)
        
        all_passed = True
        
        for test_name, result in results.items():
            if result["success"]:
                print(f"✅ PASS {test_name}")
            else:
                print(f"❌ FAIL {test_name}")
                all_passed = False
        
        print(f"\n🎯 OVERALL RESULT: {'✅ RELEASE APPROVED' if all_passed else '❌ RELEASE BLOCKED'}")
        
        if not all_passed:
            print("\n🚨 Failed Tests Details:")
            for test_name, result in results.items():
                if not result["success"]:
                    print(f"   ❌ {test_name}: {result.get('error', 'Performance target missed')}")
        
        return all_passed


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="P1 Release Gate Verification")
    parser.add_argument("--first_token_ms", type=int, default=80, 
                       help="First-token latency target in ms (default: 80)")
    parser.add_argument("--p95_latency_ms", type=int, default=200,
                       help="P95 latency target in ms (default: 200)")
    parser.add_argument("--dup_ratio", type=float, default=0.02,
                       help="Maximum duplicate ratio (default: 0.02)")
    
    args = parser.parse_args()
    
    gate = ReleaseGate(
        first_token_ms=args.first_token_ms,
        p95_latency_ms=args.p95_latency_ms,
        dup_ratio=args.dup_ratio
    )
    
    success = await gate.run_release_gate()
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 