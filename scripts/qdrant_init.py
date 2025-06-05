#!/usr/bin/env python3
"""
Qdrant Initialization Script for Phase 3 Memory Integration
Sets up quantized HNSW index for fast retrieval
"""

import argparse
import sys
from pathlib import Path

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import VectorParams, Distance, OptimizersConfig, HnswConfig, QuantizationConfig, ScalarQuantization
    QDRANT_AVAILABLE = True
except ImportError:
    print("❌ qdrant-client not installed. Run: pip install qdrant-client>=1.6.0")
    QDRANT_AVAILABLE = False

def create_quantized_collection(
    collection_name: str,
    dimension: int = 384,
    quantization: bool = True,
    hnsw_m: int = 32,
    ef_construction: int = 256
):
    """Create optimized Qdrant collection for Phase 3"""
    
    if not QDRANT_AVAILABLE:
        return False
    
    try:
        # Connect to Qdrant
        client = QdrantClient(host="localhost", port=6333)
        
        print(f"🚀 Creating collection: {collection_name}")
        print(f"   Dimensions: {dimension}")
        print(f"   Quantization: {quantization}")
        print(f"   HNSW M: {hnsw_m}, EF: {ef_construction}")
        
        # Configure HNSW parameters for RTX 4070 optimization
        hnsw_config = HnswConfig(
            m=hnsw_m,                    # 32 for good recall/speed balance
            ef_construct=ef_construction, # 256 for quality index build
            full_scan_threshold=10000,   # Use HNSW for collections > 10k
            max_indexing_threads=4       # RTX 4070 has good thread perf
        )
        
        # Configure quantization for memory efficiency
        quantization_config = None
        if quantization:
            quantization_config = QuantizationConfig(
                scalar=ScalarQuantization(
                    type="int8",                # 8-bit quantization
                    quantile=0.99,             # Preserve 99% of precision
                    always_ram=True            # Keep quantized vectors in RAM
                )
            )
        
        # Configure optimizers for write performance
        optimizer_config = OptimizersConfig(
            deleted_threshold=0.2,          # Clean up deleted vectors at 20%
            vacuum_min_vector_number=1000,  # Minimum vectors before vacuum
            default_segment_number=0,       # Auto-configure segments
            max_segment_size=None,          # Auto-configure max size
            memmap_threshold=None,          # Auto-configure memmap
            indexing_threshold=20000,       # Start indexing at 20k vectors
            flush_interval_sec=5,           # Flush every 5 seconds
            max_optimization_threads=2      # Limit optimization threads
        )
        
        # Delete existing collection if it exists
        try:
            client.delete_collection(collection_name)
            print(f"✅ Deleted existing collection: {collection_name}")
        except:
            pass
        
        # Create collection with optimized configuration
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=dimension,
                distance=Distance.COSINE,    # Cosine similarity for embeddings
                hnsw_config=hnsw_config,
                quantization_config=quantization_config
            ),
            optimizers_config=optimizer_config
        )
        
        print(f"✅ Collection created successfully!")
        
        # Verify collection
        collection_info = client.get_collection(collection_name)
        print(f"📊 Collection Info:")
        print(f"   Status: {collection_info.status}")
        print(f"   Vector count: {collection_info.vectors_count}")
        print(f"   Index size: {collection_info.indexed_vectors_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create collection: {e}")
        return False

def main():
    """Main initialization routine"""
    parser = argparse.ArgumentParser(description="Initialize Qdrant collection for Phase 3")
    parser.add_argument("--collection", default="lumina_mem_v3", help="Collection name")
    parser.add_argument("--dim", type=int, default=384, help="Vector dimensions")
    parser.add_argument("--quantization", action="store_true", help="Enable quantization")
    parser.add_argument("--hnsw-m", type=int, default=32, help="HNSW M parameter")
    parser.add_argument("--ef-construction", type=int, default=256, help="HNSW EF construction")
    
    args = parser.parse_args()
    
    print("🚀 Phase 3: Qdrant Collection Initialization")
    print("=" * 50)
    
    success = create_quantized_collection(
        collection_name=args.collection,
        dimension=args.dim,
        quantization=args.quantization,
        hnsw_m=args.hnsw_m,
        ef_construction=args.ef_construction
    )
    
    if success:
        print("\n🎉 Qdrant collection ready for Phase 3 memory integration!")
        sys.exit(0)
    else:
        print("\n❌ Collection initialization failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 