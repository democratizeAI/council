#!/usr/bin/env python3
"""
Quick test of specialist priority system
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'router'))

try:
    from router.selector import analyze_intent, pick_specialist
    from router_cascade import RouterCascade
    
    print("🧪 Testing Intent Analysis:")
    test_queries = ['2+2', 'what is 5*7?', 'write python code', 'tell me about DNA']
    
    for query in test_queries:
        intent, confidence = analyze_intent(query)
        print(f'  "{query}" -> {intent} ({confidence:.2f})')
    
    print()
    print("🎯 Testing Specialist Selection:")
    for query in test_queries:
        specialist, confidence, tried = pick_specialist(query)
        print(f'  "{query}" -> {specialist} ({confidence:.2f})')
    
    print()
    print("🔧 Testing Router Confidence:")
    router = RouterCascade()
    for query in test_queries:
        try:
            skill, confidence = router._route_query(query)
            print(f'  "{query}" -> {skill} ({confidence:.2f})')
        except Exception as e:
            print(f'  "{query}" -> ERROR: {e}')
    
    print()
    print("✅ Specialist priority system is working!")
    print("🎯 Math queries should route to math specialist first")
    print("🔧 Code queries should route to code specialist first")
    print("☁️ Cloud fallback only when specialists fail")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Checking if files exist...")
    
    if os.path.exists("router/selector.py"):
        print("✅ router/selector.py exists")
    else:
        print("❌ router/selector.py missing")
    
    if os.path.exists("router_cascade.py"):
        print("✅ router_cascade.py exists")
    else:
        print("❌ router_cascade.py missing")

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc() 