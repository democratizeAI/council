#!/usr/bin/env python3
"""
🚢 AutoGen Titanic Gauntlet - Comprehensive Evaluation Suite
Detects quiet accuracy regressions or over-fit from new LoRAs
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
import aiohttp
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TitanicGauntlet:
    """Comprehensive evaluation framework for AutoGen models"""
    
    def __init__(self, config_path: str = "config/gauntlet_config.json"):
        self.config = self.load_config(config_path)
        self.session = None
        self.results = {
            "metadata": {
                "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "2.6.0"
            },
            "suites": {},
            "summary": {}
        }
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load gauntlet configuration"""
        default_config = {
            "api_base_url": "http://localhost:8000",
            "timeout_seconds": 30,
            "max_concurrent": 5,
            "retry_attempts": 3,
            "suites": {
                "100_blind": {
                    "name": "Blind Hold-out Evaluation",
                    "description": "100 unseen problems for regression detection",
                    "file": "suites/100_blind.json",
                    "passing_threshold": 0.75
                },
                "380_full": {
                    "name": "Full Titanic Suite", 
                    "description": "Complete 380-prompt evaluation",
                    "file": "suites/380_full.json",
                    "passing_threshold": 0.80
                },
                "math_focus": {
                    "name": "Mathematics Focus Suite",
                    "description": "Mathematical reasoning and computation",
                    "file": "suites/math_focus.json",
                    "passing_threshold": 0.85
                },
                "code_focus": {
                    "name": "Code Generation Focus Suite",
                    "description": "Programming and code analysis",
                    "file": "suites/code_focus.json",
                    "passing_threshold": 0.70
                },
                "logic_focus": {
                    "name": "Logic Focus Suite",
                    "description": "Logical reasoning and deduction",
                    "file": "suites/logic_focus.json",
                    "passing_threshold": 0.80
                }
            },
            "scoring": {
                "exact_match_weight": 0.4,
                "semantic_similarity_weight": 0.3,
                "correctness_weight": 0.3
            },
            "reporting": {
                "generate_html": True,
                "generate_csv": True,
                "output_dir": "reports/gauntlet"
            }
        }
        
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            
        return default_config
    
    def load_test_suite(self, suite_name: str) -> List[Dict[str, Any]]:
        """Load test prompts from suite file"""
        suite_config = self.config["suites"].get(suite_name)
        if not suite_config:
            raise ValueError(f"Unknown test suite: {suite_name}")
        
        suite_file = Path(suite_config["file"])
        if not suite_file.exists():
            # Generate mock test cases if file doesn't exist
            logger.warning(f"Suite file not found: {suite_file}, generating mock data")
            return self.generate_mock_suite(suite_name)
        
        try:
            with open(suite_file, 'r') as f:
                test_cases = json.load(f)
            
            logger.info(f"📋 Loaded {len(test_cases)} test cases from {suite_name}")
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to load suite {suite_name}: {e}")
            return []
    
    def generate_mock_suite(self, suite_name: str) -> List[Dict[str, Any]]:
        """Generate mock test cases for demo purposes"""
        mock_suites = {
            "100_blind": self.generate_blind_suite(),
            "380_full": self.generate_full_suite(),
            "math_focus": self.generate_math_suite(),
            "code_focus": self.generate_code_suite(),
            "logic_focus": self.generate_logic_suite()
        }
        
        return mock_suites.get(suite_name, [])
    
    def generate_blind_suite(self) -> List[Dict[str, Any]]:
        """Generate blind hold-out test cases"""
        test_cases = []
        
        # Math problems
        for i in range(30):
            a, b = i + 1, i + 2
            test_cases.append({
                "id": f"blind_math_{i}",
                "category": "math",
                "difficulty": "medium",
                "prompt": f"Calculate {a} * {b} + {a + b}",
                "expected_answer": str(a * b + a + b),
                "tags": ["arithmetic", "blind"]
            })
        
        # Logic problems
        logic_problems = [
            ("If all birds can fly, and penguins are birds, can penguins fly?", "No, this is a logical contradiction since penguins cannot fly."),
            ("What comes next in the sequence: 2, 4, 8, 16, ?", "32"),
            ("If it's raining, then the ground is wet. The ground is wet. Is it raining?", "Not necessarily, the ground could be wet for other reasons."),
        ]
        
        for i, (prompt, answer) in enumerate(logic_problems * 10):  # Repeat to get ~30
            test_cases.append({
                "id": f"blind_logic_{i}",
                "category": "logic", 
                "difficulty": "medium",
                "prompt": prompt,
                "expected_answer": answer,
                "tags": ["reasoning", "blind"]
            })
            if len([tc for tc in test_cases if tc["category"] == "logic"]) >= 30:
                break
        
        # Code problems
        for i in range(20):
            test_cases.append({
                "id": f"blind_code_{i}",
                "category": "code",
                "difficulty": "medium", 
                "prompt": f"Write a Python function to check if {i + 2} is prime",
                "expected_answer": f"def is_prime(n):\n    if n < 2: return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0: return False\n    return True",
                "tags": ["programming", "blind"]
            })
        
        # General reasoning
        for i in range(20):
            test_cases.append({
                "id": f"blind_reasoning_{i}",
                "category": "reasoning",
                "difficulty": "medium",
                "prompt": f"Explain why the number {i + 10} is important in mathematics or science",
                "expected_answer": f"The number {i + 10} has various mathematical properties and applications...",
                "tags": ["explanation", "blind"]
            })
        
        return test_cases[:100]
    
    def generate_full_suite(self) -> List[Dict[str, Any]]:
        """Generate full 380-prompt suite"""
        test_cases = []
        
        # Extend each category
        categories = ["math", "logic", "code", "reasoning", "creative"]
        per_category = 380 // len(categories)
        
        for category in categories:
            for i in range(per_category):
                test_cases.append({
                    "id": f"full_{category}_{i}",
                    "category": category,
                    "difficulty": ["easy", "medium", "hard"][i % 3],
                    "prompt": f"[{category.upper()}] Problem {i}: Solve this {category} challenge",
                    "expected_answer": f"Solution for {category} problem {i}",
                    "tags": [category, "comprehensive"]
                })
        
        return test_cases[:380]
    
    def generate_math_suite(self) -> List[Dict[str, Any]]:
        """Generate math-focused test cases"""
        test_cases = []
        
        math_types = ["algebra", "calculus", "geometry", "statistics", "number_theory"]
        
        for i, math_type in enumerate(math_types * 10):
            test_cases.append({
                "id": f"math_{math_type}_{i}",
                "category": "math",
                "difficulty": ["medium", "hard"][i % 2],
                "prompt": f"Solve this {math_type} problem: Problem {i}",
                "expected_answer": f"Solution using {math_type} principles",
                "tags": ["mathematics", math_type]
            })
        
        return test_cases[:50]
    
    def generate_code_suite(self) -> List[Dict[str, Any]]:
        """Generate code-focused test cases"""
        test_cases = []
        
        languages = ["python", "javascript", "java", "c++", "sql"]
        
        for i, lang in enumerate(languages * 10):
            test_cases.append({
                "id": f"code_{lang}_{i}",
                "category": "code",
                "difficulty": ["medium", "hard"][i % 2],
                "prompt": f"Write a {lang} function to solve problem {i}",
                "expected_answer": f"function solution_{i}() {{ /* {lang} implementation */ }}",
                "tags": ["programming", lang]
            })
        
        return test_cases[:50]
    
    def generate_logic_suite(self) -> List[Dict[str, Any]]:
        """Generate logic-focused test cases"""
        test_cases = []
        
        logic_types = ["deduction", "induction", "syllogism", "contradiction", "inference"]
        
        for i, logic_type in enumerate(logic_types * 10):
            test_cases.append({
                "id": f"logic_{logic_type}_{i}",
                "category": "logic",
                "difficulty": ["medium", "hard"][i % 2],
                "prompt": f"Apply {logic_type} to solve: Problem {i}",
                "expected_answer": f"Using {logic_type}, the answer is...",
                "tags": ["reasoning", logic_type]
            })
        
        return test_cases[:50]
    
    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case"""
        start_time = time.time()
        
        try:
            # Call the API
            async with self.session.post(
                f"{self.config['api_base_url']}/hybrid",
                json={"query": test_case["prompt"]},
                timeout=self.config["timeout_seconds"]
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"API returned status {response.status}")
                
                result_data = await response.json()
                model_answer = result_data.get("response", "").strip()
                
        except Exception as e:
            logger.warning(f"Test {test_case['id']} failed: {e}")
            return {
                "test_id": test_case["id"],
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        
        execution_time = time.time() - start_time
        
        # Score the response
        score = self.score_response(test_case, model_answer)
        
        return {
            "test_id": test_case["id"],
            "status": "completed",
            "category": test_case["category"],
            "difficulty": test_case["difficulty"],
            "prompt": test_case["prompt"],
            "expected_answer": test_case["expected_answer"],
            "model_answer": model_answer,
            "score": score,
            "execution_time": execution_time,
            "tags": test_case.get("tags", [])
        }
    
    def score_response(self, test_case: Dict[str, Any], model_answer: str) -> float:
        """Score model response against expected answer"""
        expected = test_case["expected_answer"].lower().strip()
        actual = model_answer.lower().strip()
        
        # Exact match component
        exact_match = 1.0 if expected == actual else 0.0
        
        # Simple semantic similarity (word overlap)
        expected_words = set(expected.split())
        actual_words = set(actual.split())
        
        if len(expected_words) > 0:
            overlap = len(expected_words.intersection(actual_words))
            semantic_sim = overlap / len(expected_words)
        else:
            semantic_sim = 0.0
        
        # Correctness heuristics
        correctness = 0.0
        if test_case["category"] == "math":
            # For math, look for numerical answers
            import re
            expected_nums = re.findall(r'-?\d+\.?\d*', expected)
            actual_nums = re.findall(r'-?\d+\.?\d*', actual)
            if expected_nums and actual_nums:
                correctness = 1.0 if expected_nums[0] == actual_nums[0] else 0.0
        else:
            # For other categories, use semantic similarity as correctness
            correctness = semantic_sim
        
        # Weighted score
        scoring = self.config["scoring"]
        final_score = (
            exact_match * scoring["exact_match_weight"] +
            semantic_sim * scoring["semantic_similarity_weight"] +
            correctness * scoring["correctness_weight"]
        )
        
        return min(1.0, final_score)
    
    async def run_test_suite(self, suite_name: str) -> Dict[str, Any]:
        """Run a complete test suite"""
        logger.info(f"🚢 Starting Titanic Gauntlet suite: {suite_name}")
        
        # Load test cases
        test_cases = self.load_test_suite(suite_name)
        if not test_cases:
            logger.error(f"No test cases loaded for suite {suite_name}")
            return {"error": "No test cases loaded"}
        
        suite_config = self.config["suites"][suite_name]
        
        # Run tests with concurrency control
        semaphore = asyncio.Semaphore(self.config["max_concurrent"])
        
        async def run_with_semaphore(test_case):
            async with semaphore:
                return await self.run_single_test(test_case)
        
        # Execute all test cases
        logger.info(f"🧪 Executing {len(test_cases)} test cases...")
        
        results = []
        batch_size = 10
        
        for i in range(0, len(test_cases), batch_size):
            batch = test_cases[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[run_with_semaphore(tc) for tc in batch],
                return_exceptions=True
            )
            
            results.extend(batch_results)
            logger.info(f"  Completed batch {i//batch_size + 1}/{(len(test_cases)-1)//batch_size + 1}")
        
        # Analyze results
        successful_tests = [r for r in results if isinstance(r, dict) and r.get("status") == "completed"]
        failed_tests = [r for r in results if isinstance(r, Exception) or (isinstance(r, dict) and r.get("status") != "completed")]
        
        if successful_tests:
            scores = [t["score"] for t in successful_tests]
            avg_score = statistics.mean(scores)
            median_score = statistics.median(scores)
            
            # Category breakdown
            category_scores = {}
            for test in successful_tests:
                category = test["category"]
                if category not in category_scores:
                    category_scores[category] = []
                category_scores[category].append(test["score"])
            
            category_averages = {
                cat: statistics.mean(scores) 
                for cat, scores in category_scores.items()
            }
            
            # Performance metrics
            execution_times = [t["execution_time"] for t in successful_tests]
            avg_time = statistics.mean(execution_times)
            
        else:
            avg_score = 0.0
            median_score = 0.0
            category_averages = {}
            avg_time = 0.0
        
        suite_result = {
            "suite_name": suite_name,
            "description": suite_config["description"],
            "total_tests": len(test_cases),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "average_score": avg_score,
            "median_score": median_score,
            "passing_threshold": suite_config["passing_threshold"],
            "passed": avg_score >= suite_config["passing_threshold"],
            "category_scores": category_averages,
            "average_execution_time": avg_time,
            "detailed_results": successful_tests,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"✅ Suite {suite_name} completed:")
        logger.info(f"  Average Score: {avg_score:.3f} (threshold: {suite_config['passing_threshold']:.3f})")
        logger.info(f"  Success Rate: {len(successful_tests)}/{len(test_cases)} ({len(successful_tests)/len(test_cases)*100:.1f}%)")
        logger.info(f"  Passed: {'✅ YES' if suite_result['passed'] else '❌ NO'}")
        
        return suite_result
    
    async def run_gauntlet(self, suites: List[str]) -> Dict[str, Any]:
        """Run multiple test suites"""
        logger.info(f"🚢⚔️ Starting Titanic Gauntlet with {len(suites)} suites")
        
        # Initialize HTTP session
        timeout = aiohttp.ClientTimeout(total=self.config["timeout_seconds"])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            self.session = session
            
            # Run each suite
            for suite_name in suites:
                if suite_name not in self.config["suites"]:
                    logger.warning(f"⚠️ Unknown suite: {suite_name}")
                    continue
                
                suite_result = await self.run_test_suite(suite_name)
                self.results["suites"][suite_name] = suite_result
        
        # Generate overall summary
        self.generate_summary()
        
        return self.results
    
    def generate_summary(self):
        """Generate overall gauntlet summary"""
        suites = self.results["suites"]
        
        if not suites:
            self.results["summary"] = {"error": "No suites completed"}
            return
        
        total_tests = sum(s.get("total_tests", 0) for s in suites.values())
        total_successful = sum(s.get("successful_tests", 0) for s in suites.values())
        
        suite_scores = [s["average_score"] for s in suites.values() if "average_score" in s]
        overall_score = statistics.mean(suite_scores) if suite_scores else 0.0
        
        passed_suites = [s for s in suites.values() if s.get("passed", False)]
        
        self.results["summary"] = {
            "total_suites": len(suites),
            "passed_suites": len(passed_suites),
            "total_tests": total_tests,
            "successful_tests": total_successful,
            "overall_score": overall_score,
            "success_rate": total_successful / total_tests if total_tests > 0 else 0.0,
            "all_suites_passed": len(passed_suites) == len(suites),
            "completion_time": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("📊 GAUNTLET SUMMARY:")
        logger.info(f"  Overall Score: {overall_score:.3f}")
        logger.info(f"  Suites Passed: {len(passed_suites)}/{len(suites)}")
        logger.info(f"  Tests Passed: {total_successful}/{total_tests}")
        logger.info(f"  All Suites Passed: {'✅ YES' if self.results['summary']['all_suites_passed'] else '❌ NO'}")
    
    def save_results(self, output_path: Optional[str] = None):
        """Save gauntlet results to file"""
        if not output_path:
            report_dir = Path(self.config["reporting"]["output_dir"])
            report_dir.mkdir(parents=True, exist_ok=True)
            
            run_id = self.results["metadata"]["run_id"]
            output_path = report_dir / f"gauntlet_results_{run_id}.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"💾 Results saved to {output_path}")
        return str(output_path)

async def main():
    """Main gauntlet execution"""
    parser = argparse.ArgumentParser(description="AutoGen Titanic Gauntlet")
    parser.add_argument("--suite", action="append", help="Test suite to run (can specify multiple)")
    parser.add_argument("--all", action="store_true", help="Run all available test suites")
    parser.add_argument("--config", default="config/gauntlet_config.json", help="Config file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize gauntlet
    gauntlet = TitanicGauntlet(args.config)
    
    if args.api_url:
        gauntlet.config["api_base_url"] = args.api_url
    
    # Determine which suites to run
    if args.all:
        suites_to_run = list(gauntlet.config["suites"].keys())
    elif args.suite:
        suites_to_run = args.suite
    else:
        # Default to blind evaluation
        suites_to_run = ["100_blind"]
    
    logger.info(f"🎯 Running suites: {', '.join(suites_to_run)}")
    
    # Run the gauntlet
    try:
        results = await gauntlet.run_gauntlet(suites_to_run)
        
        # Save results
        output_file = gauntlet.save_results(args.output)
        
        # Exit with appropriate code
        all_passed = results["summary"].get("all_suites_passed", False)
        if all_passed:
            logger.info("🎉 All test suites passed! Model is ready for production.")
            exit(0)
        else:
            logger.warning("⚠️ Some test suites failed. Review results before deployment.")
            exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Gauntlet interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"❌ Gauntlet failed: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 