#!/usr/bin/env python3
"""
🎯 Live Accuracy Test - Real API Testing
Tests accuracy against running APIs to detect any regression in model performance
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

def generate_accuracy_prompts() -> List[Dict[str, Any]]:
    """Generate focused test prompts for accuracy evaluation with expected answers"""
    
    test_prompts = [
        # Math (easily verifiable - exact answers expected)
        {"id": "math_01", "prompt": "What is 17 * 23?", "expected": "391", "category": "math", "difficulty": "easy"},
        {"id": "math_02", "prompt": "What is the square root of 144?", "expected": "12", "category": "math", "difficulty": "easy"},
        {"id": "math_03", "prompt": "What is 25% of 80?", "expected": "20", "category": "math", "difficulty": "easy"},
        {"id": "math_04", "prompt": "Convert 0.75 to a fraction in lowest terms", "expected": "3/4", "category": "math", "difficulty": "medium"},
        {"id": "math_05", "prompt": "What is 2^8?", "expected": "256", "category": "math", "difficulty": "easy"},
        {"id": "math_06", "prompt": "Calculate 15% of 200", "expected": "30", "category": "math", "difficulty": "easy"},
        {"id": "math_07", "prompt": "What is 144 ÷ 12?", "expected": "12", "category": "math", "difficulty": "easy"},
        {"id": "math_08", "prompt": "What is 7 * 9?", "expected": "63", "category": "math", "difficulty": "easy"},
        {"id": "math_09", "prompt": "What is 100 - 37?", "expected": "63", "category": "math", "difficulty": "easy"},
        {"id": "math_10", "prompt": "What is 5^3?", "expected": "125", "category": "math", "difficulty": "easy"},
        
        # Logic (clear right/wrong answers)
        {"id": "logic_01", "prompt": "If all cats are mammals and all mammals are animals, are all cats animals?", "expected": "yes", "category": "logic", "difficulty": "easy"},
        {"id": "logic_02", "prompt": "What comes next in the sequence: 2, 4, 8, 16, ?", "expected": "32", "category": "logic", "difficulty": "medium"},
        {"id": "logic_03", "prompt": "If it takes 5 machines 5 minutes to make 5 widgets, how long does it take 100 machines to make 100 widgets?", "expected": "5 minutes", "category": "logic", "difficulty": "hard"},
        {"id": "logic_04", "prompt": "True or False: All roses are flowers, but not all flowers are roses", "expected": "true", "category": "logic", "difficulty": "medium"},
        {"id": "logic_05", "prompt": "If A > B and B > C, what is the relationship between A and C?", "expected": "A > C", "category": "logic", "difficulty": "medium"},
        {"id": "logic_06", "prompt": "If today is Monday, what day will it be in 8 days?", "expected": "Tuesday", "category": "logic", "difficulty": "easy"},
        {"id": "logic_07", "prompt": "How many sides does a triangle have?", "expected": "3", "category": "logic", "difficulty": "easy"},
        {"id": "logic_08", "prompt": "If you have 10 apples and eat 3, how many do you have left?", "expected": "7", "category": "logic", "difficulty": "easy"},
        
        # Coding (syntax/concept verification)
        {"id": "code_01", "prompt": "What Python data type stores key-value pairs?", "expected": "dictionary", "category": "coding", "difficulty": "easy"},
        {"id": "code_02", "prompt": "What is the time complexity of binary search?", "expected": "O(log n)", "category": "coding", "difficulty": "medium"},
        {"id": "code_03", "prompt": "In Python, what does len([]) return?", "expected": "0", "category": "coding", "difficulty": "easy"},
        {"id": "code_04", "prompt": "What SQL keyword removes duplicate rows?", "expected": "DISTINCT", "category": "coding", "difficulty": "medium"},
        {"id": "code_05", "prompt": "What HTTP status code means 'Not Found'?", "expected": "404", "category": "coding", "difficulty": "easy"},
        {"id": "code_06", "prompt": "What does 'git add .' do?", "expected": "adds all files", "category": "coding", "difficulty": "easy"},
        {"id": "code_07", "prompt": "In Python, what operator checks equality?", "expected": "==", "category": "coding", "difficulty": "easy"},
        
        # Science (factual knowledge)
        {"id": "science_01", "prompt": "What is the chemical symbol for gold?", "expected": "Au", "category": "science", "difficulty": "easy"},
        {"id": "science_02", "prompt": "How many chambers does a human heart have?", "expected": "4", "category": "science", "difficulty": "easy"},
        {"id": "science_03", "prompt": "What planet is closest to the Sun?", "expected": "Mercury", "category": "science", "difficulty": "easy"},
        {"id": "science_04", "prompt": "What gas do plants absorb during photosynthesis?", "expected": "carbon dioxide", "category": "science", "difficulty": "medium"},
        {"id": "science_05", "prompt": "How many legs does an insect have?", "expected": "6", "category": "science", "difficulty": "easy"},
        {"id": "science_06", "prompt": "What is the chemical symbol for water?", "expected": "H2O", "category": "science", "difficulty": "easy"},
        {"id": "science_07", "prompt": "What force keeps us on Earth?", "expected": "gravity", "category": "science", "difficulty": "easy"},
    ]
    
    return test_prompts

def calculate_accuracy_score(expected: str, actual: str) -> float:
    """Calculate accuracy score between expected and actual answers"""
    
    # Normalize strings for comparison
    expected_norm = expected.lower().strip().replace(".", "").replace(",", "")
    actual_norm = actual.lower().strip().replace(".", "").replace(",", "")
    
    # Exact match
    if expected_norm == actual_norm:
        return 1.0
    
    # Check if expected answer is contained in actual (common for verbose models)
    if expected_norm in actual_norm:
        return 0.9
    
    # Check if actual answer contains expected (for short expected answers)
    if actual_norm in expected_norm:
        return 0.9
    
    # Check for numeric equivalence
    try:
        exp_num = float(expected_norm.replace(" ", ""))
        act_num = float(actual_norm.replace(" ", ""))
        if abs(exp_num - act_num) < 0.01:  # Close enough for floating point
            return 1.0
    except:
        pass
    
    # Special cases for common variations
    variations = {
        "yes": ["true", "correct", "affirmative"],
        "no": ["false", "incorrect", "negative"],
        "dictionary": ["dict", "hash", "map"],
        "carbon dioxide": ["co2", "carbon-dioxide"],
        "gravity": ["gravitational force"],
        "3/4": ["0.75", "three quarters", "three fourths"],
        "h2o": ["water", "dihydrogen monoxide"]
    }
    
    for expected_var, possible_actuals in variations.items():
        if expected_norm == expected_var:
            for possible in possible_actuals:
                if possible in actual_norm:
                    return 0.8
        if expected_norm in possible_actuals:
            if expected_var in actual_norm:
                return 0.8
    
    # Keywords match (for more complex answers)
    expected_words = set(expected_norm.split())
    actual_words = set(actual_norm.split())
    
    if expected_words and actual_words:
        overlap = len(expected_words.intersection(actual_words))
        union = len(expected_words.union(actual_words))
        jaccard = overlap / union if union > 0 else 0
        
        if jaccard > 0.6:
            return jaccard * 0.7  # Partial credit
    
    return 0.0

async def test_api_endpoint(session: aiohttp.ClientSession, url: str, prompt: str) -> Dict[str, Any]:
    """Test a single prompt against an API endpoint"""
    start_time = time.time()
    
    try:
        payload = {"prompt": prompt}
        
        async with session.post(url, json=payload, timeout=30) as resp:
            latency = (time.time() - start_time) * 1000
            
            if resp.status == 200:
                data = await resp.json()
                return {
                    "success": True,
                    "response": data.get("text", str(data)),
                    "latency_ms": latency,
                    "model": data.get("model", data.get("model_used", "unknown")),
                    "provider": data.get("provider", "unknown"),
                    "status_code": resp.status
                }
            else:
                error_text = await resp.text()
                return {
                    "success": False,
                    "response": f"HTTP {resp.status}: {error_text}",
                    "latency_ms": latency,
                    "model": "error",
                    "provider": "error",
                    "status_code": resp.status
                }
                
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        return {
            "success": False,
            "response": f"Error: {str(e)}",
            "latency_ms": latency,
            "model": "error",
            "provider": "error",
            "status_code": 0
        }

async def check_api_health(session: aiohttp.ClientSession, base_url: str) -> bool:
    """Check if API is healthy and responsive"""
    try:
        health_url = f"{base_url}/health"
        async with session.get(health_url, timeout=10) as resp:
            return resp.status == 200
    except:
        return False

async def run_live_accuracy_test(api_url: str, max_questions: int = 30) -> Dict[str, Any]:
    """Run live accuracy test against a running API"""
    
    print("🎯 LIVE ACCURACY TEST")
    print("=" * 50)
    print(f"🌐 API URL: {api_url}")
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 Max questions: {max_questions}")
    print()
    
    test_prompts = generate_accuracy_prompts()[:max_questions]
    
    # Determine endpoint based on URL
    if ":9000" in api_url:
        endpoint = f"{api_url}/hybrid"
        api_type = "Docker Council"
    else:
        endpoint = f"{api_url}/hybrid"
        api_type = "Non-Docker Council"
    
    async with aiohttp.ClientSession() as session:
        # Health check first
        print("🏥 Checking API health...")
        healthy = await check_api_health(session, api_url)
        if not healthy:
            print(f"❌ API not healthy at {api_url}")
            return {"error": "API not healthy", "api_url": api_url}
        print("✅ API health check passed")
        print()
        
        results = []
        category_stats = {}
        total_latency = 0
        successful_requests = 0
        failed_requests = 0
        
        print(f"🧪 Testing {len(test_prompts)} questions against {api_type}")
        print("-" * 50)
        
        for i, prompt_data in enumerate(test_prompts):
            prompt_id = prompt_data["id"]
            category = prompt_data["category"]
            expected = prompt_data["expected"]
            difficulty = prompt_data["difficulty"]
            
            # Test the API
            api_result = await test_api_endpoint(session, endpoint, prompt_data["prompt"])
            
            if api_result["success"]:
                successful_requests += 1
                actual = api_result["response"]
                accuracy = calculate_accuracy_score(expected, actual)
                
                # Truncate long responses for display
                display_actual = actual[:100] + "..." if len(actual) > 100 else actual
                
                result = {
                    "id": prompt_id,
                    "category": category,
                    "difficulty": difficulty,
                    "prompt": prompt_data["prompt"],
                    "expected": expected,
                    "actual": actual,
                    "display_actual": display_actual,
                    "accuracy": accuracy,
                    "correct": accuracy >= 0.7,  # 70% threshold for "correct"
                    "latency_ms": api_result["latency_ms"],
                    "model": api_result["model"],
                    "provider": api_result["provider"]
                }
                
                total_latency += api_result["latency_ms"]
                
                # Show progress
                status = "✅" if result["correct"] else "❌"
                print(f"{status} {prompt_id}: {accuracy:.2f} ({api_result['latency_ms']:.0f}ms)")
                
            else:
                failed_requests += 1
                result = {
                    "id": prompt_id,
                    "category": category,
                    "difficulty": difficulty,
                    "prompt": prompt_data["prompt"],
                    "expected": expected,
                    "actual": api_result["response"],
                    "display_actual": api_result["response"],
                    "accuracy": 0.0,
                    "correct": False,
                    "latency_ms": api_result["latency_ms"],
                    "model": "error",
                    "provider": "error",
                    "error": True
                }
                
                print(f"❌ {prompt_id}: API ERROR - {api_result['response']}")
            
            results.append(result)
            
            # Update category stats
            if category not in category_stats:
                category_stats[category] = {"total": 0, "correct": 0, "accuracy_sum": 0.0, "latency_sum": 0.0}
            
            category_stats[category]["total"] += 1
            category_stats[category]["accuracy_sum"] += result["accuracy"]
            category_stats[category]["latency_sum"] += result["latency_ms"]
            if result["correct"]:
                category_stats[category]["correct"] += 1
            
            # Brief pause between requests
            await asyncio.sleep(0.1)
        
        # Calculate overall statistics
        total_questions = len(results)
        total_correct = sum(1 for r in results if r["correct"])
        overall_accuracy = sum(r["accuracy"] for r in results) / total_questions if total_questions > 0 else 0
        success_rate = total_correct / total_questions if total_questions > 0 else 0
        avg_latency = total_latency / successful_requests if successful_requests > 0 else 0
        
        # Generate report
        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "api_url": api_url,
                "api_type": api_type,
                "total_questions": total_questions,
                "max_questions": max_questions
            },
            "overall_metrics": {
                "success_rate": success_rate,
                "average_accuracy": overall_accuracy,
                "total_correct": total_correct,
                "total_questions": total_questions,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "average_latency_ms": avg_latency
            },
            "category_breakdown": {},
            "detailed_results": results,
            "api_performance": {
                "endpoint": endpoint,
                "response_rate": successful_requests / total_questions if total_questions > 0 else 0,
                "avg_latency_ms": avg_latency
            }
        }
        
        # Category breakdowns
        for category, stats in category_stats.items():
            cat_accuracy = stats["accuracy_sum"] / stats["total"]
            cat_success_rate = stats["correct"] / stats["total"]
            cat_avg_latency = stats["latency_sum"] / stats["total"]
            
            report["category_breakdown"][category] = {
                "success_rate": cat_success_rate,
                "average_accuracy": cat_accuracy,
                "correct": stats["correct"],
                "total": stats["total"],
                "avg_latency_ms": cat_avg_latency
            }
        
        return report

def print_live_accuracy_report(report: Dict[str, Any]):
    """Print formatted live accuracy report"""
    
    print("\n📊 LIVE ACCURACY RESULTS")
    print("=" * 50)
    
    meta = report["metadata"]
    overall = report["overall_metrics"]
    api_perf = report["api_performance"]
    
    print(f"🌐 API: {meta['api_type']} ({meta['api_url']})")
    print(f"📡 Response Rate: {api_perf['response_rate']:.1%} ({overall['successful_requests']}/{overall['total_questions']})")
    print(f"⚡ Average Latency: {overall['average_latency_ms']:.0f}ms")
    print()
    
    print(f"🎯 Overall Success Rate: {overall['success_rate']:.1%}")
    print(f"📈 Average Accuracy: {overall['average_accuracy']:.3f}")
    print(f"✅ Questions Correct: {overall['total_correct']}/{overall['total_questions']}")
    print()
    
    print("📊 Category Breakdown:")
    print("-" * 40)
    
    categories = report["category_breakdown"]
    for category, stats in categories.items():
        success_rate = stats["success_rate"]
        accuracy = stats["average_accuracy"]
        latency = stats["avg_latency_ms"]
        status = "✅" if success_rate >= 0.8 else "⚠️" if success_rate >= 0.6 else "❌"
        
        print(f"{status} {category.upper()}: {success_rate:.1%} success | {accuracy:.3f} accuracy | {latency:.0f}ms | ({stats['correct']}/{stats['total']})")
    
    print()
    
    # Show problematic questions
    failed_questions = [r for r in report["detailed_results"] if not r["correct"]]
    if failed_questions:
        print("🔍 Questions Needing Attention:")
        print("-" * 40)
        for q in failed_questions[:10]:  # Show first 10 failures
            print(f"❌ {q['id']}: Expected '{q['expected']}' | Got '{q['display_actual']}' | Score: {q['accuracy']:.2f}")
        
        if len(failed_questions) > 10:
            print(f"   ... and {len(failed_questions) - 10} more")
    else:
        print("🎉 All questions answered correctly!")
    
    print()
    
    # Overall assessment
    overall_success = overall['success_rate']
    response_rate = api_perf['response_rate']
    avg_latency = overall['average_latency_ms']
    
    print("🏆 OVERALL ASSESSMENT:")
    print("-" * 30)
    
    if response_rate < 0.9:
        print(f"❌ API RELIABILITY: {response_rate:.1%} response rate - API has connection issues")
    elif avg_latency > 2000:
        print(f"⚠️ API PERFORMANCE: {avg_latency:.0f}ms average - Very slow responses")
    elif avg_latency > 1000:
        print(f"⚠️ API PERFORMANCE: {avg_latency:.0f}ms average - Slow responses")
    elif overall_success >= 0.9:
        print(f"🎉 EXCELLENT: {overall_success:.1%} accuracy with {avg_latency:.0f}ms latency")
    elif overall_success >= 0.8:
        print(f"✅ GOOD: {overall_success:.1%} accuracy with {avg_latency:.0f}ms latency")
    elif overall_success >= 0.7:
        print(f"⚠️ FAIR: {overall_success:.1%} accuracy - needs improvement")
    else:
        print(f"❌ POOR: {overall_success:.1%} accuracy - requires immediate attention")

async def main():
    """Main execution with argument parsing"""
    parser = argparse.ArgumentParser(description="Live Accuracy Test against running APIs")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--docker", action="store_true", help="Test Docker API on port 9000")
    parser.add_argument("--questions", type=int, default=30, help="Maximum number of questions to test")
    parser.add_argument("--report", help="Save detailed report to file")
    
    args = parser.parse_args()
    
    # Determine API URL
    if args.docker:
        api_url = "http://localhost:9000"
    else:
        api_url = args.url
    
    print(f"🎯 Live Accuracy Test")
    print(f"🌐 Target: {api_url}")
    print(f"📝 Questions: {args.questions}")
    print()
    
    # Run the test
    report = await run_live_accuracy_test(api_url, args.questions)
    
    if "error" in report:
        print(f"❌ Test failed: {report['error']}")
        return
    
    # Print results
    print_live_accuracy_report(report)
    
    # Save detailed report if requested
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Detailed report saved: {args.report}")
    else:
        # Auto-save with timestamp
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        api_type = "docker" if ":9000" in api_url else "local"
        report_file = report_dir / f"live_accuracy_{api_type}_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Report auto-saved: {report_file}")

if __name__ == "__main__":
    asyncio.run(main()) 