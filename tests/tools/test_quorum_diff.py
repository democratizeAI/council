#!/usr/bin/env python3
"""
Test cases for QA-300 Dual-Render Diff Engine
🧪 Pass/fail test case simulation for AST comparison logic
"""

import ast
import os
import tempfile
import unittest
from pathlib import Path
import sys

# Add tools directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / 'tools' / 'qa'))

from compare_ast import ASTAnalyzer, ASTComparison

class TestQuorumDiff(unittest.TestCase):
    """Test suite for QA-300 AST comparison logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ASTAnalyzer(threshold=0.03)
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, filename: str, content: str) -> str:
        """Create a temporary test file"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def test_identical_files_should_pass(self):
        """Test Case 1: Identical files should achieve 100% similarity"""
        code = '''
def hello_world():
    """Simple test function"""
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"

if __name__ == "__main__":
    test = TestClass("Alice")
    print(test.greet())
'''
        
        file_a = self.create_test_file("identical_a.py", code)
        file_b = self.create_test_file("identical_b.py", code)
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "pass")
        self.assertEqual(result.route_to, "none")
        self.assertGreaterEqual(result.ast_similarity, 0.99)
        self.assertLessEqual(result.semantic_distance, 0.01)

    def test_minor_differences_should_pass(self):
        """Test Case 2: Minor differences (whitespace, comments) should pass"""
        code_a = '''
def calculate_sum(a, b):
    """Calculate sum of two numbers"""
    return a + b

def main():
    result = calculate_sum(5, 3)
    print(f"Result: {result}")
'''
        
        code_b = '''
def calculate_sum(a, b):
    # Calculate sum of two numbers
    return a + b

def main():
    result = calculate_sum(5, 3)
    print(f"Result: {result}")
'''
        
        file_a = self.create_test_file("minor_a.py", code_a)
        file_b = self.create_test_file("minor_b.py", code_b)
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "pass")
        self.assertEqual(result.route_to, "none")
        self.assertGreaterEqual(result.ast_similarity, 0.97)  # Should pass 97% threshold

    def test_variable_rename_should_pass(self):
        """Test Case 3: Variable renaming should still pass (similar structure)"""
        code_a = '''
def process_data(input_list):
    result = []
    for item in input_list:
        if item > 0:
            result.append(item * 2)
    return result
'''
        
        code_b = '''
def process_data(data_list):
    output = []
    for element in data_list:
        if element > 0:
            output.append(element * 2)
    return output
'''
        
        file_a = self.create_test_file("rename_a.py", code_a)
        file_b = self.create_test_file("rename_b.py", code_b)
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "pass")
        self.assertEqual(result.route_to, "none")
        # Structure is identical, only names differ

    def test_significant_logic_difference_should_fail(self):
        """Test Case 4: Significant logic differences should fail"""
        code_a = '''
def fibonacci(n):
    """Iterative fibonacci"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
'''
        
        code_b = '''
def fibonacci(n):
    """Recursive fibonacci"""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
'''
        
        file_a = self.create_test_file("logic_a.py", code_a)
        file_b = self.create_test_file("logic_b.py", code_b)
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "fail")
        self.assertEqual(result.route_to, "gemini-audit")
        self.assertLess(result.ast_similarity, 0.97)  # Should fail 97% threshold

    def test_different_algorithms_should_fail(self):
        """Test Case 5: Completely different algorithms should fail"""
        code_a = '''
def sort_numbers(numbers):
    """Bubble sort implementation"""
    n = len(numbers)
    for i in range(n):
        for j in range(0, n - i - 1):
            if numbers[j] > numbers[j + 1]:
                numbers[j], numbers[j + 1] = numbers[j + 1], numbers[j]
    return numbers
'''
        
        code_b = '''
def sort_numbers(numbers):
    """Quick sort implementation"""
    if len(numbers) <= 1:
        return numbers
    
    pivot = numbers[len(numbers) // 2]
    left = [x for x in numbers if x < pivot]
    middle = [x for x in numbers if x == pivot]
    right = [x for x in numbers if x > pivot]
    
    return sort_numbers(left) + middle + sort_numbers(right)
'''
        
        file_a = self.create_test_file("algo_a.py", code_a)
        file_b = self.create_test_file("algo_b.py", code_b)
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "fail")
        self.assertEqual(result.route_to, "gemini-audit")
        self.assertLess(result.ast_similarity, 0.97)

    def test_missing_functions_should_fail(self):
        """Test Case 6: Missing functions should fail"""
        code_a = '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
'''
        
        code_b = '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
'''
        
        file_a = self.create_test_file("missing_a.py", code_a)
        file_b = self.create_test_file("missing_b.py", code_b)
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "fail")
        self.assertEqual(result.route_to, "gemini-audit")
        self.assertLess(result.ast_similarity, 0.97)

    def test_syntax_error_should_fail(self):
        """Test Case 7: Syntax errors should result in fail"""
        code_a = '''
def valid_function():
    print("This is valid Python")
    return True
'''
        
        code_b = '''
def invalid_function(:
    print("This has syntax error")
    return True
'''
        
        file_a = self.create_test_file("valid.py", code_a)
        file_b = self.create_test_file("invalid.py", code_b)
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "fail")
        self.assertEqual(result.route_to, "gemini-audit")
        self.assertEqual(result.ast_similarity, 0.0)

    def test_edge_case_empty_files(self):
        """Test Case 8: Empty files should pass"""
        file_a = self.create_test_file("empty_a.py", "")
        file_b = self.create_test_file("empty_b.py", "")
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "pass")
        self.assertEqual(result.route_to, "none")
        self.assertEqual(result.ast_similarity, 1.0)

    def test_edge_case_one_empty_should_fail(self):
        """Test Case 9: One empty file should fail"""
        code = '''
def function():
    pass
'''
        
        file_a = self.create_test_file("content.py", code)
        file_b = self.create_test_file("empty.py", "")
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        self.assertEqual(result.quorum_decision, "fail")
        self.assertEqual(result.route_to, "gemini-audit")
        self.assertEqual(result.ast_similarity, 0.0)

    def test_threshold_adjustment(self):
        """Test Case 10: Different threshold should affect decisions"""
        code_a = '''
def test_func(x):
    return x * 2
'''
        
        code_b = '''
def test_func(y):
    return y * 3  # Different operation
'''
        
        file_a = self.create_test_file("thresh_a.py", code_a)
        file_b = self.create_test_file("thresh_b.py", code_b)
        
        # Test with strict threshold (should fail)
        strict_analyzer = ASTAnalyzer(threshold=0.01)  # 99% required
        result_strict = strict_analyzer.compare_files(file_a, file_b)
        
        # Test with lenient threshold (might pass)
        lenient_analyzer = ASTAnalyzer(threshold=0.20)  # 80% required
        result_lenient = lenient_analyzer.compare_files(file_a, file_b)
        
        # Strict should be more likely to fail
        # Results depend on actual similarity, but thresholds should differ
        self.assertNotEqual(result_strict.quorum_decision, result_lenient.quorum_decision)

    def test_meta_yaml_generation(self):
        """Test Case 11: Meta YAML generation"""
        code_a = '''
def sample():
    return "test"
'''
        
        code_b = '''
def sample():
    return "test"
'''
        
        file_a = self.create_test_file("meta_a.py", code_a)
        file_b = self.create_test_file("meta_b.py", code_b)
        
        result = self.analyzer.compare_files(file_a, file_b)
        
        meta_path = os.path.join(self.temp_dir, "test_meta.yaml")
        generated_path = self.analyzer.generate_meta_yaml(result, meta_path)
        
        self.assertTrue(os.path.exists(meta_path))
        self.assertEqual(generated_path, meta_path)
        
        # Verify YAML content
        import yaml
        with open(meta_path, 'r') as f:
            meta_data = yaml.safe_load(f)
        
        self.assertIn('qa_300_dual_render', meta_data)
        qa_data = meta_data['qa_300_dual_render']
        
        self.assertIn('ast_similarity', qa_data)
        self.assertIn('quorum_decision', qa_data)
        self.assertIn('route_to', qa_data)
        self.assertEqual(qa_data['rollback'], 'qa-revert')

    def test_prometheus_metric_generation(self):
        """Test Case 12: Prometheus metric generation"""
        code_a = '''
def test():
    pass
'''
        
        code_b = '''
def test():
    pass
'''
        
        file_a = self.create_test_file("metric_a.py", code_a)
        file_b = self.create_test_file("metric_b.py", code_b)
        
        result = self.analyzer.compare_files(file_a, file_b)
        metric = self.analyzer.generate_prometheus_metric(result)
        
        self.assertIn('quorum_ast_diff_percent', metric)
        self.assertIn('builder_pair="sonnet-a:sonnet-b"', metric)
        self.assertRegex(metric, r'= \d+\.\d+$')

class TestQuorumDiffIntegration(unittest.TestCase):
    """Integration tests for QA-300 CLI and workflow"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up integration test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, filename: str, content: str) -> str:
        """Create a temporary test file"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def test_cli_pass_scenario(self):
        """Integration Test 1: CLI pass scenario"""
        code = '''
def integration_test():
    return "success"
'''
        
        file_a = self.create_test_file("cli_a.py", code)
        file_b = self.create_test_file("cli_b.py", code)
        meta_path = os.path.join(self.temp_dir, "cli_meta.yaml")
        
        # Simulate CLI call
        from compare_ast import main, ASTAnalyzer
        
        analyzer = ASTAnalyzer()
        result = analyzer.compare_files(file_a, file_b)
        analyzer.generate_meta_yaml(result, meta_path)
        
        self.assertTrue(os.path.exists(meta_path))
        
        # Verify meta.yaml structure
        import yaml
        with open(meta_path, 'r') as f:
            meta = yaml.safe_load(f)
        
        qa_data = meta['qa_300_dual_render']
        self.assertEqual(qa_data['quorum_decision'], 'pass')
        self.assertEqual(qa_data['route_to'], 'none')

    def test_cli_fail_scenario(self):
        """Integration Test 2: CLI fail scenario"""
        code_a = '''
def method_one():
    for i in range(10):
        print(i)
'''
        
        code_b = '''
def method_two():
    i = 0
    while i < 10:
        print(i)
        i += 1
'''
        
        file_a = self.create_test_file("fail_a.py", code_a)
        file_b = self.create_test_file("fail_b.py", code_b)
        meta_path = os.path.join(self.temp_dir, "fail_meta.yaml")
        
        analyzer = ASTAnalyzer()
        result = analyzer.compare_files(file_a, file_b)
        analyzer.generate_meta_yaml(result, meta_path)
        
        self.assertTrue(os.path.exists(meta_path))
        
        # Verify meta.yaml structure
        import yaml
        with open(meta_path, 'r') as f:
            meta = yaml.safe_load(f)
        
        qa_data = meta['qa_300_dual_render']
        self.assertEqual(qa_data['quorum_decision'], 'fail')
        self.assertEqual(qa_data['route_to'], 'gemini-audit')

def run_test_suite():
    """Run the complete QA-300 test suite"""
    print("🧪 Running QA-300 Dual-Render Diff Engine Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestQuorumDiff))
    suite.addTests(loader.loadTestsFromTestCase(TestQuorumDiffIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ All tests passed! QA-300 is ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Please review and fix issues.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(run_test_suite()) 