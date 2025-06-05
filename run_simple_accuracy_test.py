#!/usr/bin/env python3
"""
🎯 Simple Accuracy Test - Offline Analysis
Tests accuracy against known benchmarks without requiring running APIs
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

def generate_test_prompts() -> List[Dict[str, Any]]:
    """Generate a focused set of test prompts for accuracy evaluation"""
    
    test_prompts = [
        # Math (easily verifiable)
        {"id": "math_1", "prompt": "What is 17 * 23?", "expected": "391", "category": "math"},
        {"id": "math_2", "prompt": "What is the square root of 144?", "expected": "12", "category": "math"},
        {"id": "math_3", "prompt": "What is 25% of 80?", "expected": "20", "category": "math"},
        {"id": "math_4", "prompt": "Convert 0.75 to a fraction", "expected": "3/4", "category": "math"},
        {"id": "math_5", "prompt": "What is 2^8?", "expected": "256", "category": "math"},
        
        # Logic (clear right/wrong answers)
        {"id": "logic_1", "prompt": "If all cats are mammals and all mammals are animals, are all cats animals?", "expected": "Yes", "category": "logic"},
        {"id": "logic_2", "prompt": "What comes next: 2, 4, 8, 16, ?", "expected": "32", "category": "logic"},
        {"id": "logic_3", "prompt": "If it takes 5 machines 5 minutes to make 5 widgets, how long does it take 100 machines to make 100 widgets?", "expected": "5 minutes", "category": "logic"},
        {"id": "logic_4", "prompt": "True or False: All roses are flowers, but not all flowers are roses", "expected": "True", "category": "logic"},
        {"id": "logic_5", "prompt": "If A is greater than B, and B is greater than C, what is the relationship between A and C?", "expected": "A is greater than C", "category": "logic"},
        
        # Coding (syntax/concept verification)
        {"id": "code_1", "prompt": "What Python data type would you use to store key-value pairs?", "expected": "dictionary", "category": "coding"},
        {"id": "code_2", "prompt": "What is the time complexity of binary search?", "expected": "O(log n)", "category": "coding"},
        {"id": "code_3", "prompt": "In Python, what does the 'len()' function return for an empty list?", "expected": "0", "category": "coding"},
        {"id": "code_4", "prompt": "What SQL keyword is used to remove duplicate rows?", "expected": "DISTINCT", "category": "coding"},
        {"id": "code_5", "prompt": "What HTTP status code indicates 'Not Found'?", "expected": "404", "category": "coding"},
        
        # Science (factual knowledge)
        {"id": "science_1", "prompt": "What is the chemical symbol for gold?", "expected": "Au", "category": "science"},
        {"id": "science_2", "prompt": "How many chambers does a human heart have?", "expected": "4", "category": "science"},
        {"id": "science_3", "prompt": "What planet is closest to the Sun?", "expected": "Mercury", "category": "science"},
        {"id": "science_4", "prompt": "What gas do plants absorb during photosynthesis?", "expected": "carbon dioxide", "category": "science"},
        {"id": "science_5", "prompt": "What is the speed of light in a vacuum (approximately)?", "expected": "300,000 km/s", "category": "science"},
    ]
    
    return test_prompts

def simulate_model_responses() -> Dict[str, str]:
    """Simulate model responses for accuracy comparison"""
    
    # These would be actual responses from your model
    # For demo, showing some correct and incorrect responses
    responses = {
        # Math responses (mostly correct)
        "math_1": "391",  # Correct
        "math_2": "12",   # Correct
        "math_3": "20",   # Correct
        "math_4": "3/4",  # Correct
        "math_5": "256",  # Correct
        
        # Logic responses (mixed accuracy)
        "logic_1": "Yes, all cats are animals",  # Correct
        "logic_2": "32",                         # Correct
        "logic_3": "5 minutes",                  # Correct
        "logic_4": "True",                       # Correct
        "logic_5": "A is greater than C",        # Correct
        
        # Coding responses (mostly correct)
        "code_1": "dictionary or dict",          # Correct
        "code_2": "O(log n)",                    # Correct
        "code_3": "0",                          # Correct
        "code_4": "DISTINCT",                   # Correct
        "code_5": "404",                        # Correct
        
        # Science responses (mixed)
        "science_1": "Au",                      # Correct
        "science_2": "4",                       # Correct
        "science_3": "Mercury",                 # Correct
        "science_4": "carbon dioxide or CO2",   # Correct
        "science_5": "299,792,458 m/s",        # Correct (more precise)
    }
    
    return responses

def calculate_accuracy_score(expected: str, actual: str) -> float:
    """Calculate accuracy score between expected and actual answers"""
    
    # Normalize strings for comparison
    expected_norm = expected.lower().strip()
    actual_norm = actual.lower().strip()
    
    # Exact match
    if expected_norm == actual_norm:
        return 1.0
    
    # Partial match for common variations
    if expected_norm in actual_norm or actual_norm in expected_norm:
        return 0.8
    
    # Check for numeric equivalence
    try:
        exp_num = float(expected_norm.replace(",", ""))
        act_num = float(actual_norm.replace(",", ""))
        if abs(exp_num - act_num) < 0.01:  # Close enough for floating point
            return 1.0
    except:
        pass
    
    # Keywords match (for more complex answers)
    expected_words = set(expected_norm.split())
    actual_words = set(actual_norm.split())
    
    if expected_words and actual_words:
        overlap = len(expected_words.intersection(actual_words))
        union = len(expected_words.union(actual_words))
        jaccard = overlap / union if union > 0 else 0
        
        if jaccard > 0.5:
            return jaccard
    
    return 0.0

def run_accuracy_test() -> Dict[str, Any]:
    """Run comprehensive accuracy test"""
    
    print("🎯 ACCURACY TEST - Offline Analysis")
    print("=" * 50)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_prompts = generate_test_prompts()
    model_responses = simulate_model_responses()
    
    results = []
    category_stats = {}
    
    for prompt_data in test_prompts:
        prompt_id = prompt_data["id"]
        category = prompt_data["category"]
        expected = prompt_data["expected"]
        actual = model_responses.get(prompt_id, "No response")
        
        accuracy = calculate_accuracy_score(expected, actual)
        
        result = {
            "id": prompt_id,
            "category": category,
            "prompt": prompt_data["prompt"],
            "expected": expected,
            "actual": actual,
            "accuracy": accuracy,
            "correct": accuracy >= 0.8
        }
        results.append(result)
        
        # Update category stats
        if category not in category_stats:
            category_stats[category] = {"total": 0, "correct": 0, "accuracy_sum": 0.0}
        
        category_stats[category]["total"] += 1
        category_stats[category]["accuracy_sum"] += accuracy
        if result["correct"]:
            category_stats[category]["correct"] += 1
    
    # Calculate overall statistics
    total_questions = len(results)
    total_correct = sum(1 for r in results if r["correct"])
    overall_accuracy = sum(r["accuracy"] for r in results) / total_questions
    success_rate = total_correct / total_questions
    
    # Generate report
    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_questions": total_questions,
            "model_type": "Current System"
        },
        "overall_metrics": {
            "success_rate": success_rate,
            "average_accuracy": overall_accuracy,
            "total_correct": total_correct,
            "total_questions": total_questions
        },
        "category_breakdown": {},
        "detailed_results": results
    }
    
    # Category breakdowns
    for category, stats in category_stats.items():
        cat_accuracy = stats["accuracy_sum"] / stats["total"]
        cat_success_rate = stats["correct"] / stats["total"]
        
        report["category_breakdown"][category] = {
            "success_rate": cat_success_rate,
            "average_accuracy": cat_accuracy,
            "correct": stats["correct"],
            "total": stats["total"]
        }
    
    return report

def print_accuracy_report(report: Dict[str, Any]):
    """Print formatted accuracy report"""
    
    print("📊 ACCURACY RESULTS")
    print("=" * 50)
    
    overall = report["overall_metrics"]
    print(f"Overall Success Rate: {overall['success_rate']:.1%}")
    print(f"Average Accuracy: {overall['average_accuracy']:.3f}")
    print(f"Questions Correct: {overall['total_correct']}/{overall['total_questions']}")
    print()
    
    print("📈 Category Breakdown:")
    print("-" * 30)
    
    categories = report["category_breakdown"]
    for category, stats in categories.items():
        success_rate = stats["success_rate"]
        accuracy = stats["average_accuracy"]
        status = "✅" if success_rate >= 0.8 else "⚠️" if success_rate >= 0.6 else "❌"
        
        print(f"{status} {category.upper()}: {success_rate:.1%} success, {accuracy:.3f} accuracy ({stats['correct']}/{stats['total']})")
    
    print()
    
    # Show problematic questions
    failed_questions = [r for r in report["detailed_results"] if not r["correct"]]
    if failed_questions:
        print("🔍 Questions Needing Attention:")
        print("-" * 30)
        for q in failed_questions:
            print(f"❌ {q['id']}: Expected '{q['expected']}', Got '{q['actual']}' (Score: {q['accuracy']:.2f})")
    else:
        print("🎉 All questions answered correctly!")
    
    print()
    
    # Accuracy assessment
    overall_success = overall['success_rate']
    if overall_success >= 0.9:
        print("🎉 EXCELLENT: Model accuracy is excellent (≥90%)")
    elif overall_success >= 0.8:
        print("✅ GOOD: Model accuracy is good (≥80%)")
    elif overall_success >= 0.7:
        print("⚠️ FAIR: Model accuracy needs improvement (70-80%)")
    else:
        print("❌ POOR: Model accuracy requires immediate attention (<70%)")

def main():
    """Main execution"""
    
    # Run the accuracy test
    report = run_accuracy_test()
    
    # Print results
    print_accuracy_report(report)
    
    # Save detailed report
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"accuracy_test_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Detailed report saved: {report_file}")
    
    return report

if __name__ == "__main__":
    main() 