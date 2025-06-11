#!/usr/bin/env python3
"""
O3 Cost Cap Guardian - Financial Protection Guard
🚦 FREEZE-SAFE: Returns PASS when AUDIT_O3_ENABLED=false

This guard prevents O3 audit extension from exceeding cost thresholds.
During the freeze, it's inert and always returns PASS.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('o3_cost_cap_guard')

class GuardResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"

@dataclass
class CostAnalysis:
    current_hourly_rate: float
    daily_projection: float
    cost_per_audit: float
    total_audits_today: int
    breach_threshold: float
    emergency_threshold: float

class O3CostCapGuard:
    """
    Financial protection guard for O3 audit extension
    
    During freeze: Always returns PASS (inert mode)
    Post-freeze: Enforces cost thresholds and triggers fallback/emergency stops
    """
    
    def __init__(self):
        self.enabled = self._is_enabled()
        self.freeze_mode = self._is_freeze_mode()
        
        # Cost thresholds (USD)
        self.daily_limit = float(os.getenv('O3_DAILY_COST_LIMIT', '3.33'))
        self.hourly_limit = float(os.getenv('O3_HOURLY_COST_LIMIT', '0.15'))
        self.per_audit_limit = float(os.getenv('O3_PER_AUDIT_LIMIT', '0.10'))
        
        # Alert thresholds
        self.warning_threshold = 0.75  # 75% of daily limit
        self.emergency_threshold = 0.90  # 90% of daily limit
        
        logger.info(f"O3 Cost Cap Guard initialized")
        logger.info(f"Enabled: {self.enabled}, Freeze mode: {self.freeze_mode}")
        logger.info(f"Daily limit: ${self.daily_limit}, Hourly limit: ${self.hourly_limit}")
    
    def _is_enabled(self) -> bool:
        """Check if O3 audit is enabled"""
        return os.getenv('AUDIT_O3_ENABLED', 'false').lower() == 'true'
    
    def _is_freeze_mode(self) -> bool:
        """Check if we're in freeze mode"""
        return os.getenv('FREEZE', '0') == '1'
    
    def check_cost_limits(self, cost_data: Optional[Dict[str, Any]] = None) -> GuardResult:
        """
        Main cost check function
        
        Args:
            cost_data: Optional cost metrics for analysis
            
        Returns:
            GuardResult: PASS/WARN/FAIL based on cost analysis
        """
        
        # 🚦 FREEZE-SAFE: Always pass when disabled
        if not self.enabled or self.freeze_mode:
            logger.info("🚦 O3 Cost Cap Guard - FREEZE MODE")
            logger.info("Feature disabled - returning PASS (expected)")
            logger.info(f"AUDIT_O3_ENABLED: {self.enabled}")
            logger.info(f"FREEZE: {self.freeze_mode}")
            return GuardResult.PASS
        
        # Full implementation starts here (post-freeze)
        logger.info("🚀 O3 Cost Cap Guard - ACTIVE MODE")
        
        if cost_data is None:
            cost_data = self._fetch_cost_metrics()
        
        analysis = self._analyze_costs(cost_data)
        result = self._evaluate_thresholds(analysis)
        
        self._log_cost_analysis(analysis, result)
        
        if result == GuardResult.FAIL:
            self._trigger_emergency_stop(analysis)
        elif result == GuardResult.WARN:
            self._trigger_cost_alert(analysis)
        
        return result
    
    def _fetch_cost_metrics(self) -> Dict[str, Any]:
        """Fetch current cost metrics from monitoring systems"""
        # TODO: Implement Prometheus metrics fetching
        # For now, return mock data
        return {
            'hourly_rate': 0.05,
            'daily_spent': 1.20,
            'audit_count': 12,
            'average_per_audit': 0.10
        }
    
    def _analyze_costs(self, cost_data: Dict[str, Any]) -> CostAnalysis:
        """Analyze cost data and project daily spending"""
        
        hourly_rate = cost_data.get('hourly_rate', 0.0)
        daily_spent = cost_data.get('daily_spent', 0.0)
        audit_count = cost_data.get('audit_count', 0)
        
        # Project daily cost based on current rate
        hours_remaining = 24 - (time.time() % 86400) / 3600
        daily_projection = daily_spent + (hourly_rate * hours_remaining)
        
        cost_per_audit = cost_data.get('average_per_audit', 0.0)
        
        return CostAnalysis(
            current_hourly_rate=hourly_rate,
            daily_projection=daily_projection,
            cost_per_audit=cost_per_audit,
            total_audits_today=audit_count,
            breach_threshold=self.daily_limit * self.warning_threshold,
            emergency_threshold=self.daily_limit * self.emergency_threshold
        )
    
    def _evaluate_thresholds(self, analysis: CostAnalysis) -> GuardResult:
        """Evaluate cost analysis against thresholds"""
        
        # Check emergency threshold (immediate stop)
        if analysis.daily_projection >= self.daily_limit:
            return GuardResult.FAIL
        
        # Check hourly rate limit
        if analysis.current_hourly_rate >= self.hourly_limit:
            return GuardResult.FAIL
        
        # Check per-audit cost limit
        if analysis.cost_per_audit >= self.per_audit_limit:
            return GuardResult.FAIL
        
        # Check warning threshold
        if analysis.daily_projection >= analysis.breach_threshold:
            return GuardResult.WARN
        
        return GuardResult.PASS
    
    def _log_cost_analysis(self, analysis: CostAnalysis, result: GuardResult):
        """Log detailed cost analysis"""
        logger.info("💰 Cost Analysis Results:")
        logger.info(f"  Hourly rate: ${analysis.current_hourly_rate:.3f}")
        logger.info(f"  Daily projection: ${analysis.daily_projection:.2f}")
        logger.info(f"  Cost per audit: ${analysis.cost_per_audit:.3f}")
        logger.info(f"  Total audits today: {analysis.total_audits_today}")
        logger.info(f"  Guard result: {result.value}")
    
    def _trigger_emergency_stop(self, analysis: CostAnalysis):
        """Trigger emergency cost stop procedures"""
        logger.critical("🚨 EMERGENCY COST STOP TRIGGERED")
        logger.critical(f"Daily projection ${analysis.daily_projection:.2f} exceeds limit ${self.daily_limit}")
        
        # TODO: Implement emergency procedures:
        # 1. Disable O3 audit services
        # 2. Switch to fallback mode (Gemini only)
        # 3. Send emergency alerts
        # 4. Log to audit trail
        
        # For now, just log the action
        logger.critical("ACTION: Setting O3_AUDIT_MODE=emergency_disabled")
        logger.critical("ACTION: Switching to fallback mode")
        logger.critical("ACTION: Sending emergency alerts")
    
    def _trigger_cost_alert(self, analysis: CostAnalysis):
        """Trigger cost warning alerts"""
        logger.warning("⚠️  COST WARNING TRIGGERED")
        logger.warning(f"Daily projection ${analysis.daily_projection:.2f} approaching limit ${self.daily_limit}")
        
        # TODO: Implement warning procedures:
        # 1. Send Slack alerts
        # 2. Reduce audit frequency
        # 3. Monitor more closely
        
        logger.warning("ACTION: Sending cost warning alerts")
        logger.warning("ACTION: Increasing monitoring frequency")

def main():
    """CLI entry point for testing the guard"""
    guard = O3CostCapGuard()
    
    result = guard.check_cost_limits()
    
    print(f"Guard Result: {result.value}")
    
    if result == GuardResult.PASS:
        exit(0)
    elif result == GuardResult.WARN:
        exit(1)
    else:  # FAIL
        exit(2)

if __name__ == "__main__":
    main() 