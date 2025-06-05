from prometheus_client import Gauge, Counter, Histogram
import os

# Kill-switch monitoring
killswitch_state = Gauge(
    "killswitch_state",
    "0 = normal • 1 = engaged (all /orchestrate blocked)"
)

# Standard swarm metrics (if not already defined elsewhere)
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