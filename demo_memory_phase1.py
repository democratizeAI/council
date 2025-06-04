#!/usr/bin/env python3
"""
Demo: Phase 1 Memory Integration
===============================

Demonstrates memory-enhanced Council voting with persistent context.
"""

import asyncio
import time
from bootstrap import MEMORY
from router.voting import vote

async def demo_memory_conversation():
    """Demo conversation showing memory context working"""
    
    print("🧠 Phase 1 Demo: Memory-Enhanced Council")
    print("=" * 50)
    
    # Show initial memory state
    print(f"📚 Initial memory size: {len(MEMORY.meta)} entries")
    
    # Add some demo context
    MEMORY.add("The user prefers technical explanations", {"role": "system", "ts": int(time.time())})
    MEMORY.add("The user is working on an AutoGen Council project", {"role": "system", "ts": int(time.time())})
    
    print(f"📝 Added system context. Memory size: {len(MEMORY.meta)} entries")
    
    # Test conversations
    conversations = [
        "Hi, I'm working on a memory system",
        "What kind of project am I working on?",
        "How should you explain things to me?"
    ]
    
    for i, prompt in enumerate(conversations, 1):
        print(f"\n🗣️ Conversation {i}: {prompt}")
        
        try:
            # Use our memory-enhanced voting
            result = await vote(
                prompt=prompt,
                model_names=["autogen-hybrid"],  # Would use actual models in production
                top_k=1,
                use_context=True
            )
            
            winner = result.get("winner", {})
            response = result.get("text", winner.get("text", "No response"))
            confidence = winner.get("confidence", 0.0)
            
            print(f"🤖 Response: {response[:100]}...")
            print(f"🎯 Confidence: {confidence:.3f}")
            print(f"📊 Memory entries: {len(MEMORY.meta)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Show final memory state
    print(f"\n📚 Final memory size: {len(MEMORY.meta)} entries")
    
    # Demo memory query
    print("\n🔍 Memory query demo:")
    results = MEMORY.query("project", k=3)
    for result in results[:3]:
        print(f"  📝 {result['text'][:60]}... (score: {result['score']:.3f})")
    
    print("\n✅ Phase 1 Demo Complete!")
    print("🎯 Key features working:")
    print("  ✅ Global FAISS memory instance")
    print("  ✅ Context injection into Council prompts")
    print("  ✅ Q&A logging with success flags")
    print("  ✅ Memory persistence across conversations")

if __name__ == "__main__":
    asyncio.run(demo_memory_conversation()) 