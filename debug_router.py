#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(''), 'fork', 'swarm_autogen'))

from router_cascade import RouterCascade

# Test router classification
router = RouterCascade()

test_queries = [
    "What is the square root of 64?",
    "Calculate 2 + 2",
    "What is 8 factorial?",
    "square root of 64",
    "sqrt(64)"
]

for query in test_queries:
    route = router.classify_query(query)
    print(f"Query: '{query}'")
    print(f"  → Skill: {route.skill_type}")
    print(f"  → Confidence: {route.confidence:.3f}")
    print(f"  → Patterns: {route.patterns_matched}")
    print() 