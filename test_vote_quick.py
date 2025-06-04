#!/usr/bin/env python3
"""Quick test for voting system"""

import asyncio
import sys
sys.path.append('.')
from router.voting import vote

async def test_vote():
    try:
        result = await vote('What is 2 + 2?', ['math_specialist_0.8b', 'tinyllama_1b'], 2)
        print('✅ Voting test successful!')
        print(f'Winner: {result["winner"]["model"]}')
        print(f'Confidence: {result["winner"]["confidence"]:.3f}')
        print(f'Response: {result["text"][:100]}...')
        return True
    except Exception as e:
        print(f'❌ Voting test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_vote())
    sys.exit(0 if result else 1) 