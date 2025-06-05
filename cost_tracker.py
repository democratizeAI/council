#!/usr/bin/env python3
"""
Cost Tracker - Budget Enforcement for Autonomous Spiral
========================================================

Enforces $0.10/day budget limit and tracks cost savings from:
- Pattern specialists (5ms responses)
- Shallow cache hits
- Local model usage vs cloud

Retires cloud providers when hit rate < 10%
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import redis

logger = logging.getLogger(__name__)

# Configuration
DAILY_BUDGET_USD = 0.10
EMERGENCY_STOP_THRESHOLD = 0.08  # Stop at 80% of budget
WARN_THRESHOLD = 0.05            # Warn at 50% of budget
BUDGET_RESET_HOUR = 0            # Reset at midnight

# Provider costs (per 1K tokens, estimated)
PROVIDER_COSTS = {
    'openai': 0.002,
    'mistral': 0.004, 
    'claude': 0.015,
    'anthropic': 0.015,
    'local_tinyllama': 0.0,
    'pattern_specialist': 0.0,
    'agent0': 0.0,
    'cache_hit': 0.0
}

# Hit rate tracking for provider retirement
PROVIDER_RETIREMENT_THRESHOLD = 0.10  # Retire if hit rate < 10%

@dataclass
class CostEvent:
    """Individual cost tracking event"""
    timestamp: float
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    saved_usd: float = 0.0
    source: str = "inference"  # inference, cache, pattern, etc.

@dataclass
class DailyCostSummary:
    """Daily cost summary"""
    date: str
    total_cost_usd: float
    total_saved_usd: float
    provider_costs: Dict[str, float]
    provider_hits: Dict[str, int]
    pattern_specialist_hits: int
    cache_hits: int
    budget_remaining_usd: float
    over_budget: bool

class CostTracker:
    """Cost tracking and budget enforcement system"""
    
    def __init__(self):
        """Initialize cost tracker"""
        self.redis_client = None
        self.memory_store = {}  # Fallback if Redis unavailable
        
        # Try to connect to Redis for persistence
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)
            self.redis_client.ping()
            logger.info("💰 Cost tracker connected to Redis")
        except Exception as e:
            logger.warning(f"💰 Redis unavailable, using memory store: {e}")
        
        # Ensure data directory exists
        os.makedirs("data/costs", exist_ok=True)
    
    def _get_today_key(self) -> str:
        """Get Redis key for today's costs"""
        return f"costs:{datetime.now().strftime('%Y-%m-%d')}"
    
    def _get_provider_hits_key(self) -> str:
        """Get Redis key for provider hit tracking"""
        return f"hits:{datetime.now().strftime('%Y-%m-%d')}"
    
    def record_cost_event(self, provider: str, model: str, input_tokens: int, 
                         output_tokens: int, cost_usd: float, saved_usd: float = 0.0,
                         source: str = "inference") -> bool:
        """
        Record a cost event and check budget constraints.
        
        Args:
            provider: Provider name (openai, mistral, etc.)
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens  
            cost_usd: Actual cost in USD
            saved_usd: Cost saved (for cache/pattern hits)
            source: Source of the call (inference, cache, pattern)
            
        Returns:
            True if within budget, False if over budget
        """
        event = CostEvent(
            timestamp=time.time(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            saved_usd=saved_usd,
            source=source
        )
        
        # Store event
        self._store_event(event)
        
        # Update daily totals
        today_total = self._get_daily_total()
        
        # Check budget constraints
        if today_total >= EMERGENCY_STOP_THRESHOLD:
            logger.error(f"💰 EMERGENCY STOP: Daily cost ${today_total:.4f} >= ${EMERGENCY_STOP_THRESHOLD}")
            return False
        elif today_total >= WARN_THRESHOLD:
            logger.warning(f"💰 WARNING: Daily cost ${today_total:.4f} >= ${WARN_THRESHOLD}")
        
        # Update provider hit counts
        self._increment_provider_hits(provider)
        
        logger.debug(f"💰 Cost event: {provider} ${cost_usd:.4f} (total today: ${today_total:.4f})")
        return True
    
    def _store_event(self, event: CostEvent) -> None:
        """Store cost event in Redis or memory"""
        event_data = asdict(event)
        
        if self.redis_client:
            try:
                # Store in Redis list for today
                key = self._get_today_key()
                self.redis_client.lpush(key, json.dumps(event_data))
                self.redis_client.expire(key, 86400 * 7)  # Keep for 7 days
            except Exception as e:
                logger.debug(f"💰 Redis store error: {e}")
                self._store_in_memory(event_data)
        else:
            self._store_in_memory(event_data)
    
    def _store_in_memory(self, event_data: Dict) -> None:
        """Store event in memory fallback"""
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.memory_store:
            self.memory_store[today] = []
        self.memory_store[today].append(event_data)
    
    def _get_daily_total(self) -> float:
        """Get total cost for today"""
        events = self._get_todays_events()
        return sum(event.get('cost_usd', 0) for event in events)
    
    def _get_todays_events(self) -> List[Dict]:
        """Get all cost events for today"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if self.redis_client:
            try:
                key = self._get_today_key()
                event_strings = self.redis_client.lrange(key, 0, -1)
                return [json.loads(event_str) for event_str in event_strings]
            except Exception as e:
                logger.debug(f"💰 Redis read error: {e}")
        
        # Fallback to memory
        return self.memory_store.get(today, [])
    
    def _increment_provider_hits(self, provider: str) -> None:
        """Increment hit count for provider"""
        if self.redis_client:
            try:
                key = self._get_provider_hits_key()
                self.redis_client.hincrby(key, provider, 1)
                self.redis_client.expire(key, 86400 * 7)  # Keep for 7 days
            except Exception as e:
                logger.debug(f"💰 Redis hits error: {e}")
    
    def get_provider_hit_rates(self, days: int = 7) -> Dict[str, float]:
        """
        Get hit rates for providers over the last N days.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict mapping provider to hit rate (0.0 to 1.0)
        """
        hit_rates = {}
        total_hits = {}
        
        # Collect hits for each day
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            if self.redis_client:
                try:
                    key = f"hits:{date}"
                    day_hits = self.redis_client.hgetall(key)
                    
                    for provider, hits in day_hits.items():
                        total_hits[provider] = total_hits.get(provider, 0) + int(hits)
                        
                except Exception as e:
                    logger.debug(f"💰 Hit rate error for {date}: {e}")
        
        # Calculate hit rates
        total_requests = sum(total_hits.values())
        if total_requests > 0:
            for provider, hits in total_hits.items():
                hit_rates[provider] = hits / total_requests
        
        return hit_rates
    
    def get_retirement_candidates(self) -> List[str]:
        """
        Get list of providers that should be retired (hit rate < 10%).
        
        Returns:
            List of provider names to retire
        """
        hit_rates = self.get_provider_hit_rates()
        candidates = []
        
        for provider, rate in hit_rates.items():
            if rate < PROVIDER_RETIREMENT_THRESHOLD and provider not in ['local_tinyllama', 'pattern_specialist']:
                candidates.append(provider)
                logger.info(f"💰 Retirement candidate: {provider} (hit rate: {rate:.1%})")
        
        return candidates
    
    def is_within_budget(self) -> bool:
        """Check if we're within daily budget"""
        daily_total = self._get_daily_total()
        return daily_total < DAILY_BUDGET_USD
    
    def get_budget_remaining(self) -> float:
        """Get remaining budget for today"""
        daily_total = self._get_daily_total()
        return max(0, DAILY_BUDGET_USD - daily_total)
    
    def estimate_query_cost(self, provider: str, input_length: int, expected_output_length: int = 100) -> float:
        """
        Estimate cost for a query before making it.
        
        Args:
            provider: Provider name
            input_length: Length of input text
            expected_output_length: Expected output length
            
        Returns:
            Estimated cost in USD
        """
        # Rough token estimation (4 chars per token)
        input_tokens = input_length // 4
        output_tokens = expected_output_length // 4
        
        cost_per_1k = PROVIDER_COSTS.get(provider, 0.005)  # Default cost
        
        total_cost = ((input_tokens + output_tokens) / 1000) * cost_per_1k
        return total_cost
    
    def can_afford_query(self, provider: str, input_length: int, expected_output_length: int = 100) -> bool:
        """
        Check if we can afford a query given current budget.
        
        Args:
            provider: Provider name
            input_length: Length of input text
            expected_output_length: Expected output length
            
        Returns:
            True if affordable, False otherwise
        """
        estimated_cost = self.estimate_query_cost(provider, input_length, expected_output_length)
        remaining_budget = self.get_budget_remaining()
        
        affordable = estimated_cost <= remaining_budget
        
        if not affordable:
            logger.warning(f"💰 Query not affordable: ${estimated_cost:.4f} > ${remaining_budget:.4f} remaining")
        
        return affordable
    
    def generate_daily_summary(self, date: Optional[str] = None) -> DailyCostSummary:
        """
        Generate daily cost summary.
        
        Args:
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Daily cost summary
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Get events for the date
        if self.redis_client:
            try:
                key = f"costs:{date}"
                event_strings = self.redis_client.lrange(key, 0, -1)
                events = [json.loads(event_str) for event_str in event_strings]
            except Exception:
                events = self.memory_store.get(date, [])
        else:
            events = self.memory_store.get(date, [])
        
        # Calculate totals
        total_cost = sum(event.get('cost_usd', 0) for event in events)
        total_saved = sum(event.get('saved_usd', 0) for event in events)
        
        # Group by provider
        provider_costs = {}
        provider_hits = {}
        pattern_hits = 0
        cache_hits = 0
        
        for event in events:
            provider = event.get('provider', 'unknown')
            cost = event.get('cost_usd', 0)
            source = event.get('source', 'inference')
            
            provider_costs[provider] = provider_costs.get(provider, 0) + cost
            provider_hits[provider] = provider_hits.get(provider, 0) + 1
            
            if source == 'pattern':
                pattern_hits += 1
            elif source == 'cache':
                cache_hits += 1
        
        return DailyCostSummary(
            date=date,
            total_cost_usd=total_cost,
            total_saved_usd=total_saved,
            provider_costs=provider_costs,
            provider_hits=provider_hits,
            pattern_specialist_hits=pattern_hits,
            cache_hits=cache_hits,
            budget_remaining_usd=DAILY_BUDGET_USD - total_cost,
            over_budget=total_cost > DAILY_BUDGET_USD
        )
    
    def save_daily_report(self, summary: DailyCostSummary) -> str:
        """Save daily cost report to file"""
        filename = f"data/costs/daily_report_{summary.date}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(asdict(summary), f, indent=2)
            
            logger.info(f"💰 Daily report saved: {filename}")
            logger.info(f"💰 Cost: ${summary.total_cost_usd:.4f}, Saved: ${summary.total_saved_usd:.4f}")
            
        except Exception as e:
            logger.error(f"💰 Failed to save daily report: {e}")
        
        return filename

# Global cost tracker instance
_cost_tracker = None

def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker

def record_cost(provider: str, model: str, input_tokens: int, output_tokens: int, 
               cost_usd: float, saved_usd: float = 0.0, source: str = "inference") -> bool:
    """Convenience function to record a cost event"""
    tracker = get_cost_tracker()
    return tracker.record_cost_event(provider, model, input_tokens, output_tokens, 
                                    cost_usd, saved_usd, source)

def can_afford(provider: str, input_length: int, expected_output_length: int = 100) -> bool:
    """Convenience function to check if we can afford a query"""
    tracker = get_cost_tracker()
    return tracker.can_afford_query(provider, input_length, expected_output_length)

def get_daily_summary() -> DailyCostSummary:
    """Convenience function to get today's cost summary"""
    tracker = get_cost_tracker()
    return tracker.generate_daily_summary()

if __name__ == "__main__":
    # Test the cost tracker
    tracker = CostTracker()
    
    # Simulate some cost events
    print("🧪 Testing cost tracker...")
    
    # Pattern specialist hit (free)
    tracker.record_cost_event("pattern_specialist", "pattern_1", 50, 30, 0.0, 0.002, "pattern")
    
    # Cache hit (free but saves cost)
    tracker.record_cost_event("cache_hit", "cached", 60, 40, 0.0, 0.003, "cache")
    
    # Local model (free)
    tracker.record_cost_event("local_tinyllama", "phi-1.5", 100, 80, 0.0, 0.0, "inference")
    
    # Cloud call (costs money)
    tracker.record_cost_event("openai", "gpt-3.5-turbo", 200, 150, 0.0007, 0.0, "inference")
    
    # Generate summary
    summary = tracker.generate_daily_summary()
    print(f"✅ Daily summary: ${summary.total_cost_usd:.4f} spent, ${summary.total_saved_usd:.4f} saved")
    print(f"✅ Pattern hits: {summary.pattern_specialist_hits}, Cache hits: {summary.cache_hits}")
    
    # Save report
    tracker.save_daily_report(summary)
    
    print("🧪 Cost tracker test complete!") 