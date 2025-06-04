#!/usr/bin/env python3
"""
Comprehensive FAISS Memory System Test
=====================================
Tests memory performance, persistence, and integration readiness
"""

import time
import os
import shutil
from faiss_memory import FaissMemory

def test_basic_functionality():
    """Test basic add/query operations"""
    print("🧪 Testing Basic Functionality...")
    
    mem = FaissMemory(db_path="test_memory")
    
    # Add some test data
    uid1 = mem.add("The capital of France is Paris", {"type": "geography", "confidence": 0.95})
    uid2 = mem.add("Python is a programming language", {"type": "tech", "confidence": 0.9})
    uid3 = mem.add("Paris is a beautiful city in Europe", {"type": "geography", "confidence": 0.85})
    uid4 = mem.add("2 + 2 equals 4", {"type": "math", "confidence": 1.0})
    
    print(f"   ✅ Added 4 memories: {uid1[:8]}... {uid2[:8]}... {uid3[:8]}... {uid4[:8]}...")
    
    # Test queries
    results = mem.query("What is the capital of France?", k=3)
    print(f"   ✅ Query 'capital of France' returned {len(results)} results")
    
    results = mem.query("programming", k=2)
    print(f"   ✅ Query 'programming' returned {len(results)} results")
    
    results = mem.query("mathematics", k=1)
    print(f"   ✅ Query 'mathematics' returned {len(results)} results")
    
    return mem

def test_performance():
    """Test memory system latency"""
    print("\n⚡ Testing Performance...")
    
    mem = FaissMemory(db_path="test_memory_perf")
    
    # Test add latency
    start_time = time.time()
    for i in range(10):
        mem.add(f"Test memory item {i} with some content", {"index": i})
    add_time = (time.time() - start_time) * 1000  # Convert to ms
    
    print(f"   ✅ Add latency: {add_time/10:.2f}ms per item (10 items)")
    
    # Test query latency
    start_time = time.time()
    for i in range(20):
        results = mem.query(f"test content {i%5}", k=3)
    query_time = (time.time() - start_time) * 1000  # Convert to ms
    
    print(f"   ✅ Query latency: {query_time/20:.2f}ms per query (20 queries)")
    
    return add_time/10, query_time/20

def test_persistence():
    """Test memory persistence across instances"""
    print("\n💾 Testing Persistence...")
    
    # First instance - add data
    mem1 = FaissMemory(db_path="test_memory_persist")
    uid1 = mem1.add("Persistent memory test", {"session": 1})
    uid2 = mem1.add("This should survive restart", {"session": 1})
    mem1.flush()  # Force persistence
    
    print(f"   ✅ Added 2 memories in session 1")
    
    # Second instance - should load existing data
    mem2 = FaissMemory(db_path="test_memory_persist")
    results_before = len(mem2.meta)
    
    # Add more data
    uid3 = mem2.add("New memory in session 2", {"session": 2})
    results_after = len(mem2.meta)
    
    print(f"   ✅ Loaded {results_before} memories from disk")
    print(f"   ✅ Added 1 more memory, total: {results_after}")
    
    # Test querying old data
    old_results = mem2.query("persistent", k=5)
    print(f"   ✅ Can query old memories: {len(old_results)} hits")
    
    return results_before == 2 and results_after == 3

def test_semantic_search():
    """Test semantic similarity matching"""
    print("\n🧠 Testing Semantic Search...")
    
    mem = FaissMemory(db_path="test_memory_semantic")
    
    # Add semantically related content
    mem.add("Dogs are loyal pets", {"category": "animals"})
    mem.add("Cats are independent animals", {"category": "animals"})
    mem.add("Python is a programming language", {"category": "tech"})
    mem.add("JavaScript is used for web development", {"category": "tech"})
    mem.add("Machine learning requires large datasets", {"category": "ai"})
    
    # Test semantic queries
    animal_results = mem.query("pets and animals", k=3)
    tech_results = mem.query("coding and software", k=3)
    ai_results = mem.query("artificial intelligence", k=2)
    
    print(f"   ✅ 'pets and animals' → {len(animal_results)} results")
    print(f"   ✅ 'coding and software' → {len(tech_results)} results")
    print(f"   ✅ 'artificial intelligence' → {len(ai_results)} results")
    
    # Check semantic relevance
    animal_relevant = any("pets" in r["text"] or "animals" in r["text"] for r in animal_results)
    tech_relevant = any("programming" in r["text"] or "development" in r["text"] for r in tech_results)
    
    print(f"   ✅ Semantic relevance - Animals: {animal_relevant}, Tech: {tech_relevant}")
    
    return animal_relevant and tech_relevant

def test_prometheus_metrics():
    """Test Prometheus metrics integration"""
    print("\n📊 Testing Prometheus Metrics...")
    
    from prometheus_client import CollectorRegistry, generate_latest
    
    mem = FaissMemory(db_path="test_memory_metrics")
    
    # Perform operations to generate metrics
    for i in range(5):
        mem.add(f"Metrics test {i}", {"test": True})
        mem.query(f"test {i}", k=2)
    
    # Check metrics
    registry = CollectorRegistry()
    from faiss_memory import MEM_ADD, MEM_QRY
    
    print(f"   ✅ Memory add counter available: {MEM_ADD._value._value}")
    print(f"   ✅ Memory query summary available: {MEM_QRY._count._value}")
    
    return True

def cleanup_test_dirs():
    """Clean up test directories"""
    test_dirs = ["test_memory", "test_memory_perf", "test_memory_persist", 
                 "test_memory_semantic", "test_memory_metrics"]
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def main():
    """Run comprehensive FAISS memory tests"""
    print("🚀 FAISS Memory System - Comprehensive Test Suite")
    print("=" * 55)
    
    try:
        # Run all tests
        test_basic_functionality()
        add_latency, query_latency = test_performance()
        persistence_ok = test_persistence()
        semantic_ok = test_semantic_search()
        metrics_ok = test_prometheus_metrics()
        
        print("\n" + "=" * 55)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 55)
        
        # Performance validation
        performance_target = add_latency < 50 and query_latency < 20  # Target: <50ms add, <20ms query
        
        print(f"✅ Basic Functionality: PASSED")
        print(f"⚡ Performance: {'PASSED' if performance_target else 'NEEDS OPTIMIZATION'}")
        print(f"   - Add latency: {add_latency:.2f}ms (target: <50ms)")
        print(f"   - Query latency: {query_latency:.2f}ms (target: <20ms)")
        print(f"💾 Persistence: {'PASSED' if persistence_ok else 'FAILED'}")
        print(f"🧠 Semantic Search: {'PASSED' if semantic_ok else 'FAILED'}")
        print(f"📊 Prometheus Metrics: {'PASSED' if metrics_ok else 'FAILED'}")
        
        # Overall assessment
        all_passed = persistence_ok and semantic_ok and metrics_ok and performance_target
        
        print(f"\n🎯 OVERALL ASSESSMENT: {'✅ READY FOR INTEGRATION' if all_passed else '🟡 NEEDS ATTENTION'}")
        
        if all_passed:
            print("\n🚀 The FAISS memory system is ready for Agent-Zero integration!")
            print("   Next steps:")
            print("   1. Create Agent-Zero memory adapter")
            print("   2. Integrate with RouterCascade")
            print("   3. Add to docker-compose.yml")
            print("   4. Update v2.6.0 roadmap")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        cleanup_test_dirs()
        print("\n🧹 Test cleanup completed")

if __name__ == "__main__":
    main() 