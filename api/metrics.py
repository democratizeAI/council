from prometheus_client import Gauge, Counter, Histogram
import os

# Kill-switch monitoring
killswitch_state = Gauge(
    "killswitch_state",
    "0 = normal • 1 = engaged (all /orchestrate blocked)"
)

# Standard swarm metrics
swarm_router_flag_total = Counter('swarm_router_flag_total', 'Total router flag events')
swarm_execution_success_total = Counter('swarm_execution_success_total', 'Total successful executions')
merge_efficiency = Gauge('merge_efficiency', 'Merge efficiency ratio')
cost_usd_total = Counter('cost_usd_total', 'Total cost in USD', ['agent'])

# Pattern-miner metrics
pattern_miner_lag_seconds = Gauge('pattern_miner_lag_seconds', 'Pattern miner lag in seconds')
pattern_clusters_total = Counter('pattern_clusters_total', 'Total pattern clusters', ['cid'])
pattern_miner_run_seconds = Gauge('pattern_miner_run_seconds', 'Pattern miner run duration')

# Redis metrics
redis_list_length = Gauge('redis_list_length', 'Redis list length', ['key'])

# Canary metrics  
IS_CANARY = os.getenv("CANARY_MODE", "false").lower() == "true"

swarm_canary_success_total = Counter('swarm_canary_success_total', 'Canary success count', ['route'])
swarm_canary_fail_total = Counter('swarm_canary_fail_total', 'Canary failure count', ['route'])

def record_canary(route: str, ok: bool):
    """Record canary request outcome"""
    if IS_CANARY:
        (swarm_canary_success_total if ok else swarm_canary_fail_total).labels(route=route).inc()

# Ensemble adapter metrics
ensemble_mappings_total = Counter(
    'ensemble_mappings_total',
    'Manual ensemble cluster→adapter mapping updates'
)

ensemble_miss_total = Counter(
    'ensemble_miss_total',
    'Prompts without cluster→adapter mapping (fallback to base model)',
    ['reason']  # no_cluster_mapping, no_adapter_mapping, adapter_load_failed
)

ensemble_cache_size = Gauge(
    'ensemble_cache_size',
    'Number of LoRA adapters currently loaded in memory'
)

ensemble_cache_hits_total = Counter(
    'ensemble_cache_hits_total',
    'LoRA adapter cache hits'
)

ensemble_cache_misses_total = Counter(
    'ensemble_cache_misses_total', 
    'LoRA adapter cache misses requiring disk load'
)

ensemble_cache_evictions_total = Counter(
    'ensemble_cache_evictions_total',
    'LoRA adapters evicted from cache due to LRU policy'
)

ensemble_adapter_load_duration_seconds = Histogram(
    'ensemble_adapter_load_duration_seconds',
    'Time to load LoRA adapter from disk',
    ['adapter_tag']
)

ensemble_resolution_duration_seconds = Histogram(
    'ensemble_resolution_duration_seconds',
    'Time to resolve prompt to adapter (including cache/load)',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float('inf'))
)

ensemble_active_adapters = Gauge(
    'ensemble_active_adapters',
    'Number of unique adapters mapped to clusters',
    ['adapter_tag']
)

# NEW: Weighted adapter selection tracking
adapter_select_total = Counter(
    'adapter_select_total',
    'Selections per adapter (weighted)',
    ['adapter']
)

# Lineage tracking
lineage_last_push_timestamp = Gauge(
    'lineage_last_push_timestamp',
    'Epoch timestamp when lineage was last pushed to IPFS'
)

# Streaming metrics
stream_requests_total = Counter(
    'stream_requests_total',
    'Total streaming requests',
    ['model', 'stream']
)

stream_chunk_duration_seconds = Histogram(
    'stream_chunk_duration_seconds',
    'Time between streaming chunks',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float('inf'))
)

stream_total_duration_seconds = Histogram(
    'stream_total_duration_seconds', 
    'Total streaming response duration',
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float('inf'))
) 