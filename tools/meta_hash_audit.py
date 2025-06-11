#!/usr/bin/env python3
"""
QA-301 Meta Hash Audit - Hash Comparison & Quorum Enforcement
=============================================================

Compares explanation hashes from Phi-3/TinyLlama with PatchCtl audit logs
to determine quorum passability and flip quorum_passed flags.

Features:
- Hash comparison between phi3_explain() and audit logs
- PatchCtl integration for quorum enforcement
- Automatic quorum_passed flag management
- CI integration hooks

Usage:
    python tools/meta_hash_audit.py --pr-id QA-301-test
    python tools/meta_hash_audit.py --meta-file meta.yaml --audit-log audit.log
"""

import os
import sys
import json
import yaml
import hashlib
import time
import argparse
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import aiohttp
import redis.asyncio as redis

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.explain_meta import PhiMiniExplainer
from prometheus_client import Counter, Histogram, Gauge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics for hash audit
HASH_COMPARISONS_TOTAL = Counter(
    'hash_comparisons_total',
    'Total hash comparisons performed',
    ['result', 'pr_id']
)

QUORUM_DECISIONS_TOTAL = Counter(
    'quorum_decisions_total', 
    'Total quorum decisions made',
    ['decision', 'reason']
)

AUDIT_LATENCY = Histogram(
    'meta_hash_audit_latency_seconds',
    'Latency for hash audit operations'
)

@dataclass
class HashComparison:
    """Result of hash comparison operation"""
    phi3_hash: str
    audit_hash: str
    match: bool
    confidence: float
    explanation: str
    timestamp: float

@dataclass
class QuorumDecision:
    """Quorum decision based on hash comparison"""
    pr_id: str
    passed: bool
    reason: str
    phi3_hash: str
    audit_hash: str
    confidence: float
    timestamp: float
    actions_taken: List[str]

class MetaHashAuditor:
    """
    Hash comparison and quorum enforcement engine
    Implements QA-301 hash audit logic
    """
    
    def __init__(self, patchctl_url: str = "http://localhost:8090"):
        self.patchctl_url = patchctl_url
        self.explainer = PhiMiniExplainer()
        self.redis_client = None
        
        # Hash comparison thresholds
        self.exact_match_threshold = 1.0  # Exact hash match
        self.similarity_threshold = 0.85  # Semantic similarity threshold
        
    async def initialize(self):
        """Initialize connections"""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379/0")
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            
    async def audit_pr_hash(self, pr_id: str, meta_file: str = None, 
                           audit_log: str = None) -> QuorumDecision:
        """
        Main hash audit function - compares phi3_explain() with audit logs
        Returns quorum decision with pass/fail status
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Starting hash audit for PR {pr_id}")
            
            # Get phi3 explanation hash
            phi3_hash, phi3_explanation = await self._get_phi3_hash(pr_id, meta_file)
            
            # Get audit hash from PatchCtl
            audit_hash, audit_data = await self._get_audit_hash(pr_id, audit_log)
            
            # Compare hashes
            comparison = await self._compare_hashes(phi3_hash, audit_hash, phi3_explanation, audit_data)
            
            # Make quorum decision
            decision = await self._make_quorum_decision(pr_id, comparison)
            
            # Update PatchCtl with decision
            await self._update_patchctl_quorum(decision)
            
            # Update meta.yaml with quorum_passed flag
            await self._update_meta_yaml(pr_id, decision, meta_file)
            
            # Record metrics
            latency = time.time() - start_time
            AUDIT_LATENCY.observe(latency)
            
            HASH_COMPARISONS_TOTAL.labels(
                result="match" if comparison.match else "mismatch",
                pr_id=pr_id
            ).inc()
            
            QUORUM_DECISIONS_TOTAL.labels(
                decision="pass" if decision.passed else "fail",
                reason=decision.reason
            ).inc()
            
            logger.info(f"✅ Hash audit complete for PR {pr_id}: {'PASS' if decision.passed else 'FAIL'} ({latency:.2f}s)")
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Hash audit failed for PR {pr_id}: {e}")
            HASH_COMPARISONS_TOTAL.labels(result="error", pr_id=pr_id).inc()
            raise
            
    async def _get_phi3_hash(self, pr_id: str, meta_file: str = None) -> Tuple[str, Dict]:
        """Get or generate Phi-3 explanation hash"""
        
        if meta_file and os.path.exists(meta_file):
            # Load existing meta.yaml
            with open(meta_file) as f:
                meta_data = yaml.safe_load(f)
                
            phi3_hash = meta_data.get("meta_hash")
            if phi3_hash:
                logger.info(f"📄 Loaded existing Phi-3 hash: {phi3_hash}")
                return phi3_hash, meta_data
                
        # Generate new explanation
        logger.info("🧠 Generating new Phi-3 explanation...")
        
        # Try to get diff from current git state
        try:
            import subprocess
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True,
                text=True
            )
            diff_content = result.stdout or subprocess.run(
                ["git", "diff"], capture_output=True, text=True
            ).stdout
            
            explanation = await self.explainer.explain_changes(
                diff_content=diff_content,
                intent=f"PR {pr_id} changes"
            )
            
            return explanation["meta_hash"], explanation
            
        except Exception as e:
            logger.warning(f"Failed to generate Phi-3 explanation: {e}")
            # Fallback hash
            fallback_hash = hashlib.sha256(f"pr_{pr_id}_{time.time()}".encode()).hexdigest()[:8]
            return fallback_hash, {"meta_hash": fallback_hash, "source": "fallback"}
            
    async def _get_audit_hash(self, pr_id: str, audit_log: str = None) -> Tuple[str, Dict]:
        """Get audit hash from PatchCtl or audit log"""
        
        if audit_log and os.path.exists(audit_log):
            # Parse audit log file
            audit_data = await self._parse_audit_log(audit_log)
            audit_hash = audit_data.get("hash", "unknown")
            logger.info(f"📋 Loaded audit hash from log: {audit_hash}")
            return audit_hash, audit_data
            
        # Query PatchCtl for audit data
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.patchctl_url}/audit/{pr_id}") as response:
                    if response.status == 200:
                        audit_data = await response.json()
                        audit_hash = audit_data.get("audit_hash", audit_data.get("hash", "unknown"))
                        logger.info(f"🔗 Retrieved audit hash from PatchCtl: {audit_hash}")
                        return audit_hash, audit_data
                    else:
                        logger.warning(f"PatchCtl audit query failed: HTTP {response.status}")
                        
        except Exception as e:
            logger.warning(f"Failed to query PatchCtl: {e}")
            
        # Fallback: generate pseudo-audit hash
        fallback_hash = hashlib.sha256(f"audit_{pr_id}_{time.time()}".encode()).hexdigest()[:8]
        logger.info(f"⚠️ Using fallback audit hash: {fallback_hash}")
        return fallback_hash, {"hash": fallback_hash, "source": "fallback"}
        
    async def _parse_audit_log(self, audit_log: str) -> Dict[str, Any]:
        """Parse audit log file for hash and metadata"""
        try:
            with open(audit_log) as f:
                content = f.read()
                
            # Try JSON format first
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
                
            # Try YAML format
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError:
                pass
                
            # Parse as plain text log
            lines = content.strip().split('\n')
            audit_data = {"raw_log": content}
            
            # Look for hash patterns
            for line in lines:
                if "hash:" in line.lower() or "audit_hash:" in line.lower():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        audit_data["hash"] = parts[1].strip()
                        break
                        
            return audit_data
            
        except Exception as e:
            logger.error(f"Failed to parse audit log {audit_log}: {e}")
            return {"error": str(e)}
            
    async def _compare_hashes(self, phi3_hash: str, audit_hash: str, 
                            phi3_data: Dict, audit_data: Dict) -> HashComparison:
        """Compare phi3 and audit hashes with multiple strategies"""
        
        # Exact match check
        exact_match = phi3_hash.lower() == audit_hash.lower()
        
        if exact_match:
            return HashComparison(
                phi3_hash=phi3_hash,
                audit_hash=audit_hash,
                match=True,
                confidence=1.0,
                explanation="Exact hash match",
                timestamp=time.time()
            )
            
        # Semantic similarity check (if both have summaries)
        phi3_summary = phi3_data.get("summary", "")
        audit_summary = audit_data.get("summary", audit_data.get("description", ""))
        
        if phi3_summary and audit_summary:
            similarity = self._calculate_text_similarity(phi3_summary, audit_summary)
            
            if similarity >= self.similarity_threshold:
                return HashComparison(
                    phi3_hash=phi3_hash,
                    audit_hash=audit_hash,
                    match=True,
                    confidence=similarity,
                    explanation=f"Semantic similarity {similarity:.2f} >= {self.similarity_threshold}",
                    timestamp=time.time()
                )
                
        # No match
        return HashComparison(
            phi3_hash=phi3_hash,
            audit_hash=audit_hash,
            match=False,
            confidence=0.0,
            explanation="No hash or semantic match found",
            timestamp=time.time()
        )
        
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity score"""
        
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
        
    async def _make_quorum_decision(self, pr_id: str, comparison: HashComparison) -> QuorumDecision:
        """Make quorum decision based on hash comparison"""
        
        # Decision logic: pass if hashes match with sufficient confidence
        passed = comparison.match and comparison.confidence >= self.similarity_threshold
        
        reason = "hash_match" if comparison.match else "hash_mismatch"
        if comparison.match and comparison.confidence < self.similarity_threshold:
            reason = "low_confidence"
            
        actions_taken = []
        
        decision = QuorumDecision(
            pr_id=pr_id,
            passed=passed,
            reason=reason,
            phi3_hash=comparison.phi3_hash,
            audit_hash=comparison.audit_hash,
            confidence=comparison.confidence,
            timestamp=time.time(),
            actions_taken=actions_taken
        )
        
        logger.info(f"🎯 Quorum decision for PR {pr_id}: {'PASS' if passed else 'FAIL'} ({reason})")
        
        return decision
        
    async def _update_patchctl_quorum(self, decision: QuorumDecision):
        """Update PatchCtl with quorum decision"""
        
        try:
            payload = {
                "pr_id": decision.pr_id,
                "quorum_passed": decision.passed,
                "reason": decision.reason,
                "phi3_hash": decision.phi3_hash,
                "audit_hash": decision.audit_hash,
                "confidence": decision.confidence,
                "timestamp": decision.timestamp
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    f"{self.patchctl_url}/quorum/{decision.pr_id}",
                    json=payload
                ) as response:
                    if response.status == 200:
                        logger.info(f"✅ PatchCtl updated with quorum decision: {decision.pr_id}")
                        decision.actions_taken.append("patchctl_updated")
                    else:
                        logger.warning(f"⚠️ PatchCtl update failed: HTTP {response.status}")
                        decision.actions_taken.append("patchctl_failed")
                        
        except Exception as e:
            logger.error(f"❌ PatchCtl update error: {e}")
            decision.actions_taken.append("patchctl_error")
            
    async def _update_meta_yaml(self, pr_id: str, decision: QuorumDecision, meta_file: str = None):
        """Update meta.yaml with quorum_passed flag"""
        
        meta_file = meta_file or "meta.yaml"
        
        try:
            # Load existing meta.yaml or create new
            if os.path.exists(meta_file):
                with open(meta_file) as f:
                    meta_data = yaml.safe_load(f) or {}
            else:
                meta_data = {}
                
            # Update with quorum decision
            meta_data.update({
                "quorum_passed": decision.passed,
                "quorum_reason": decision.reason,
                "quorum_timestamp": decision.timestamp,
                "phi3_hash": decision.phi3_hash,
                "audit_hash": decision.audit_hash,
                "hash_confidence": decision.confidence
            })
            
            # Write updated meta.yaml
            with open(meta_file, 'w') as f:
                yaml.dump(meta_data, f, default_flow_style=False)
                
            logger.info(f"📝 Updated {meta_file} with quorum_passed={decision.passed}")
            decision.actions_taken.append("meta_yaml_updated")
            
        except Exception as e:
            logger.error(f"❌ Failed to update {meta_file}: {e}")
            decision.actions_taken.append("meta_yaml_failed")

class MetaHashAuditCLI:
    """Command-line interface for meta hash auditing"""
    
    def __init__(self):
        self.auditor = MetaHashAuditor()
        
    async def run_audit(self, pr_id: str, meta_file: str = None, 
                       audit_log: str = None, output_file: str = None) -> QuorumDecision:
        """Run hash audit and output results"""
        
        await self.auditor.initialize()
        
        decision = await self.auditor.audit_pr_hash(
            pr_id=pr_id,
            meta_file=meta_file,
            audit_log=audit_log
        )
        
        # Format output
        output = {
            "pr_id": decision.pr_id,
            "quorum_passed": decision.passed,
            "reason": decision.reason,
            "hashes": {
                "phi3_hash": decision.phi3_hash,
                "audit_hash": decision.audit_hash
            },
            "confidence": decision.confidence,
            "timestamp": decision.timestamp,
            "actions_taken": decision.actions_taken
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                yaml.dump(output, f, default_flow_style=False)
            logger.info(f"📁 Audit results saved to {output_file}")
        else:
            print(yaml.dump(output, default_flow_style=False))
            
        return decision

async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="QA-301 Meta Hash Audit")
    parser.add_argument("--pr-id", required=True, help="PR identifier")
    parser.add_argument("--meta-file", help="Path to meta.yaml file")
    parser.add_argument("--audit-log", help="Path to audit log file")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--patchctl-url", default="http://localhost:8090", help="PatchCtl URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    cli = MetaHashAuditCLI()
    cli.auditor.patchctl_url = args.patchctl_url
    
    try:
        decision = await cli.run_audit(
            pr_id=args.pr_id,
            meta_file=args.meta_file,
            audit_log=args.audit_log,
            output_file=args.output
        )
        
        # Exit code based on quorum decision
        exit_code = 0 if decision.passed else 1
        logger.info(f"🏁 Hash audit complete: {'PASS' if decision.passed else 'FAIL'}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"❌ Hash audit failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())