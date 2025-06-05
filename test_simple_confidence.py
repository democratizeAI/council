#!/usr/bin/env python3
"""
Simple confidence calculation test to debug the pattern matching
"""

import os
import re
os.environ["SWARM_COUNCIL_ENABLED"] = "true"

from router.council import council_router

def test_specific_case():
    prompt = "Compare React vs Vue architecture"
    print(f"Testing: '{prompt}'")
    
    confidence = council_router._calculate_local_confidence(prompt)
    print(f"Result: {confidence}")
    
    # Test each pattern manually
    prompt_lower = prompt.lower()
    print(f"Lowercase: '{prompt_lower}'")
    
    patterns = [
        r'compare\s+\w+.*vs.*\w+',     # Comparisons with "vs" 
        r'compare\s+\w+.*and.*\w+',    # Comparisons with "and"
        r'analyze.*trade.*offs?',      # Trade-off analysis
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt_lower)
        print(f"Pattern '{pattern}' → Match: {match}")
        if match:
            print(f"  Matched text: '{match.group()}'")

if __name__ == "__main__":
    test_specific_case() 