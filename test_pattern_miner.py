#!/usr/bin/env python3
"""Simple test for pattern miner"""

import pattern_miner

def test_pattern_mining():
    print("🧪 Testing pattern mining...")
    
    # Initialize miner
    miner = pattern_miner.PatternMiner()
    print(f"✅ ML Available: {miner.ml_available}")
    print(f"✅ Min cluster size: {pattern_miner.MIN_CLUSTER_SIZE}")
    
    # Test with sample data
    sources = ["data/completions/sample_completions.json"]
    print(f"✅ Testing with sources: {sources}")
    
    # Run pattern mining
    try:
        miner.run_pattern_mining(sources)
        print("✅ Pattern mining completed successfully")
    except Exception as e:
        print(f"❌ Pattern mining failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pattern_mining() 