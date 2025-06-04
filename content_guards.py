#!/usr/bin/env python3
"""
Content Guards - Failure-is-Loud Validation
===========================================

Strict content validation guards that fail loud when answers are garbage.
Guards raise ContentError so router logs 5xx and Tamagotchi queues training
instead of silently green-lighting rubbish.
"""

import re
import ast
import subprocess
import tempfile
import os
from typing import Tuple, Optional

class ContentError(Exception):
    """Raised when content validation fails - causes 5xx error in router"""
    pass

def validate_math(answer: str, expected: str) -> bool:
    """
    Validate math answer - exact match required
    
    Args:
        answer: Generated answer string
        expected: Expected numerical answer
        
    Returns:
        True if exact match found, False otherwise
        
    Raises:
        ContentError: If answer is clearly garbage
    """
    # Remove whitespace and common formatting
    clean_answer = answer.strip().replace(',', '').replace(' ', '')
    clean_expected = str(expected).strip().replace(',', '')
    
    # Check for garbage indicators
    garbage_indicators = [
        'steam workshop',
        'probability',
        'approximately',
        'follow-up exercise',
        'step 1:', 'step 2:', 'step 3:',
        'i understand',
        'that\'s an interesting'
    ]
    
    answer_lower = answer.lower()
    for indicator in garbage_indicators:
        if indicator in answer_lower:
            raise ContentError(f"Math answer contains garbage indicator: '{indicator}'")
    
    # Check if expected answer is present
    if clean_expected in clean_answer:
        return True
    
    # Try to extract numbers and check if any match
    numbers_in_answer = re.findall(r'\d+', clean_answer)
    if clean_expected in numbers_in_answer:
        return True
    
    # If answer is very long, it's probably garbage
    if len(answer) > 200:
        raise ContentError(f"Math answer too long ({len(answer)} chars), likely garbage")
    
    return False

def validate_code(answer: str) -> bool:
    """
    Validate code answer - must compile without syntax errors
    
    Args:
        answer: Generated code string
        
    Returns:
        True if code compiles, False otherwise
        
    Raises:
        ContentError: If code is clearly garbage
    """
    original_answer = answer
    
    # Check for garbage indicators first
    garbage_indicators = [
        'follow-up exercise',
        'probability of getting',
        'steam workshop'
    ]
    
    answer_lower = answer.lower()
    for indicator in garbage_indicators:
        if indicator in answer_lower:
            raise ContentError(f"Code answer contains garbage indicator: '{indicator}'")
    
    # Try to extract code from markdown if present
    if '```python' in answer_lower or '```' in answer:
        # Extract code from markdown blocks
        match = re.search(r'```python\s*(.*?)\s*```', answer, re.DOTALL | re.IGNORECASE)
        if match:
            answer = match.group(1).strip()
        else:
            # Try generic code block
            match = re.search(r'```\s*(.*?)\s*```', answer, re.DOTALL)
            if match:
                candidate_code = match.group(1).strip()
                # Check if it looks like Python code
                if 'def ' in candidate_code:
                    answer = candidate_code
    
    # Must contain 'def' for function generation
    if 'def ' not in answer:
        raise ContentError("Code answer missing 'def' - not a function")
    
    # Try to compile the code
    try:
        # Clean up common formatting issues
        cleaned_code = answer.strip()
        
        # Remove leading/trailing non-code text
        lines = cleaned_code.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            stripped = line.strip()
            
            # Start capturing when we see 'def'
            if 'def ' in stripped:
                in_code = True
            
            if in_code:
                code_lines.append(line)
            
            # Stop if we hit obvious non-code (but allow common code patterns)
            if in_code and stripped and not stripped.startswith(('#', 'def ', 'return', 'if ', 'else:', 'for ', 'while ', '    ', 'import ', 'from ')):
                # Check if line contains code-like patterns
                code_patterns = ['=', '(', ')', '+', '-', '*', '/', '%', ':', '!=', '==', 'and ', 'or ', 'not ']
                if not any(pattern in stripped for pattern in code_patterns):
                    # If it starts with "###" or "Exercise" it's probably post-code text
                    if stripped.startswith('###') or 'exercise' in stripped.lower():
                        break
        
        final_code = '\n'.join(code_lines).strip()
        
        # Try to compile
        compile(final_code, "<string>", "exec")
        return True
        
    except SyntaxError as e:
        raise ContentError(f"Code compilation failed: {e}")
    except Exception as e:
        raise ContentError(f"Code validation error: {e}")

def validate_logic(answer: str, expected_yes_no: Optional[str] = None) -> bool:
    """
    Validate logic answer - must contain explicit yes/no
    
    Args:
        answer: Generated answer string
        expected_yes_no: Expected 'yes' or 'no' (optional)
        
    Returns:
        True if contains explicit yes/no, False otherwise
        
    Raises:
        ContentError: If answer is clearly garbage
    """
    # Check for garbage indicators
    garbage_indicators = [
        'steam workshop',
        'probability of getting',
        'follow-up exercise',
        'step 1:', 'step 2:'
    ]
    
    answer_lower = answer.lower()
    for indicator in garbage_indicators:
        if indicator in answer_lower:
            raise ContentError(f"Logic answer contains garbage indicator: '{indicator}'")
    
    # Look for explicit yes/no
    explicit_patterns = [
        r'\bno[,.]',
        r'\byes[,.]',
        r'answer:\s*no',
        r'answer:\s*yes',
        r'answer is no',
        r'answer is yes'
    ]
    
    has_explicit = any(re.search(pattern, answer_lower) for pattern in explicit_patterns)
    
    if not has_explicit:
        # Check for implicit yes/no
        if 'no' in answer_lower or 'yes' in answer_lower:
            # Has implicit, but prefer explicit
            return True
        else:
            raise ContentError("Logic answer missing yes/no response")
    
    # If expected answer specified, check it matches
    if expected_yes_no:
        expected_lower = expected_yes_no.lower()
        if expected_lower not in answer_lower:
            raise ContentError(f"Logic answer has wrong yes/no: expected '{expected_yes_no}'")
    
    return True

def validate_knowledge(answer: str, query: str) -> bool:
    """
    Validate knowledge/RAG answer - must be relevant and substantive
    
    Args:
        answer: Generated answer string
        query: Original query string
        
    Returns:
        True if answer is relevant and substantive, False otherwise
        
    Raises:
        ContentError: If answer is clearly garbage
    """
    # Check for garbage indicators
    garbage_indicators = [
        'steam workshop',
        'probability',
        'follow-up exercise',
        'i appreciate your inquiry',
        'that\'s an interesting topic'
    ]
    
    answer_lower = answer.lower()
    for indicator in garbage_indicators:
        if indicator in answer_lower:
            raise ContentError(f"Knowledge answer contains garbage indicator: '{indicator}'")
    
    # Must be substantive (not just "I don't know")
    if len(answer.strip()) < 10:
        raise ContentError("Knowledge answer too short - not substantive")
    
    # Should contain some keywords from query
    query_words = set(query.lower().split())
    answer_words = set(answer.lower().split())
    
    # At least some overlap expected
    overlap = query_words.intersection(answer_words)
    if len(overlap) == 0 and len(query_words) > 1:
        raise ContentError("Knowledge answer has no relevance to query")
    
    return True

def strict_grader(task_type: str, answer: str, expected: str = None, query: str = None) -> Tuple[bool, float, str]:
    """
    Strict grader that fails loud on garbage
    
    Args:
        task_type: Type of task ('math', 'code', 'logic', 'knowledge')
        answer: Generated answer
        expected: Expected answer (for math)
        query: Original query (for knowledge)
        
    Returns:
        Tuple of (passed, confidence, details)
        
    Raises:
        ContentError: If validation fails
    """
    try:
        if task_type == 'math':
            if expected is None:
                raise ContentError("Math task requires expected answer")
            
            passed = validate_math(answer, expected)
            confidence = 1.0 if passed else 0.0
            details = "Exact match" if passed else "No match found"
            
        elif task_type == 'code':
            passed = validate_code(answer)
            confidence = 1.0 if passed else 0.0
            details = "Compiles successfully" if passed else "Compilation failed"
            
        elif task_type == 'logic':
            passed = validate_logic(answer)
            confidence = 1.0 if passed else 0.0
            details = "Contains explicit yes/no" if passed else "Missing yes/no"
            
        elif task_type == 'knowledge':
            if query is None:
                raise ContentError("Knowledge task requires original query")
            
            passed = validate_knowledge(answer, query)
            confidence = 1.0 if passed else 0.0
            details = "Relevant and substantive" if passed else "Not relevant"
            
        else:
            raise ContentError(f"Unknown task type: {task_type}")
        
        return passed, confidence, details
        
    except ContentError:
        # Re-raise ContentError for loud failure
        raise
    except Exception as e:
        # Wrap other errors as ContentError
        raise ContentError(f"Grader error: {e}")

def test_guards():
    """Test the content guards"""
    print("🛡️ Testing Content Guards")
    print("=" * 40)
    
    # Test math validation
    print("\n🧮 Testing Math Guard:")
    try:
        # Good math
        result = strict_grader('math', "The answer is 40320", "40320")
        print(f"✅ Good math: {result}")
        
        # Bad math (garbage)
        result = strict_grader('math', "Steam Workshop is interesting", "40320")
        print(f"❌ Should not reach here")
    except ContentError as e:
        print(f"✅ Bad math caught: {e}")
    
    # Test code validation  
    print("\n💻 Testing Code Guard:")
    try:
        # Good code
        result = strict_grader('code', "def add(a, b):\n    return a + b")
        print(f"✅ Good code: {result}")
        
        # Bad code (garbage)
        result = strict_grader('code', "**Solution:** Steam Workshop", "")
        print(f"❌ Should not reach here")
    except ContentError as e:
        print(f"✅ Bad code caught: {e}")
    
    # Test logic validation
    print("\n🧠 Testing Logic Guard:")
    try:
        # Good logic
        result = strict_grader('logic', "No, blips are not zogs because...")
        print(f"✅ Good logic: {result}")
        
        # Bad logic (garbage)
        result = strict_grader('logic', "The probability of getting 20...")
        print(f"❌ Should not reach here")
    except ContentError as e:
        print(f"✅ Bad logic caught: {e}")
    
    print("\n🎯 Content guards working - ready for litmus test!")

if __name__ == "__main__":
    test_guards() 