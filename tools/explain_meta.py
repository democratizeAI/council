#!/usr/bin/env python3
# tools/explain_meta.py - QA-301 Meta Explainer Hashing
"""
🧠 Meta Explainer Hashing - QA-301
==================================

Generates compact explanations of PR intent using Phi-3-mini for deterministic
tie-breaking in nondeterministic diffs and downstream Gemini auditing.

Features:
- Phi-3-mini powered PR intent summarization
- Deterministic hashing for reproducible results
- Integration with PatchCtl and A2A events
- Prometheus metrics for tracking

Usage:
    python tools/explain_meta.py --pr-path=/path/to/pr > meta_hash.yaml
    python tools/explain_meta.py --diff-file=changes.diff --intent="Fix latency"
"""

import os
import sys
import json
import yaml
import hashlib
import time
import argparse
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
import asyncio
import aiohttp

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prometheus_client import Counter, Histogram, push_to_gateway, CollectorRegistry
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
registry = CollectorRegistry()
BUILDER_META_EXPLAINED = Counter(
    'builder_meta_explained_total',
    'Total meta explanations generated',
    ['result'],
    registry=registry
)

META_EXPLANATION_LATENCY = Histogram(
    'meta_explanation_latency_seconds',
    'Latency for generating meta explanations',
    registry=registry
)

class PhiMiniExplainer:
    """
    Phi-3-mini powered explanation generator
    Optimized for compact, deterministic PR summaries
    """
    
    def __init__(self, model_endpoint: str = "http://localhost:8001/v1/completions"):
        self.model_endpoint = model_endpoint
        self.model_name = "microsoft/Phi-3-mini-4k-instruct"
        self.max_tokens = 256  # Compact explanations
        self.temperature = 0.1  # Low for determinism
        
    async def explain_changes(self, diff_content: str, intent: str = "", 
                            affected_files: List[str] = None) -> Dict[str, Any]:
        """Generate compact explanation of changes using Phi-3-mini"""
        
        start_time = time.time()
        
        try:
            # Prepare context for Phi-3-mini
            context = self._prepare_context(diff_content, intent, affected_files or [])
            
            # Generate explanation
            explanation = await self._query_phi_mini(context)
            
            # Parse and structure response
            structured_explanation = self._structure_explanation(
                explanation, diff_content, affected_files or []
            )
            
            # Generate deterministic hash
            explanation_hash = self._generate_hash(structured_explanation)
            
            result = {
                "meta_hash": explanation_hash,
                "summary": structured_explanation["summary"],
                "logic_change_type": structured_explanation["change_type"],
                "affected_modules": structured_explanation["modules"],
                "intent": intent or "Auto-detected",
                "timestamp": time.time(),
                "model": self.model_name,
                "deterministic": True
            }
            
            latency = time.time() - start_time
            META_EXPLANATION_LATENCY.observe(latency)
            BUILDER_META_EXPLAINED.labels(result="hash_added").inc()
            
            logger.info(f"✅ Meta explanation generated: {explanation_hash} ({latency:.2f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Meta explanation failed: {e}")
            BUILDER_META_EXPLAINED.labels(result="error").inc()
            
            # Fallback to deterministic summary
            return self._fallback_explanation(diff_content, intent, affected_files or [])
            
    def _prepare_context(self, diff_content: str, intent: str, affected_files: List[str]) -> str:
        """Prepare optimized context for Phi-3-mini"""
        
        # Truncate diff if too long (Phi-3-mini has 4k context)
        max_diff_chars = 2000
        if len(diff_content) > max_diff_chars:
            diff_content = diff_content[:max_diff_chars] + "\n... (truncated)"
            
        # Extract key diff patterns
        added_lines = len([line for line in diff_content.split('\n') if line.startswith('+')])
        removed_lines = len([line for line in diff_content.split('\n') if line.startswith('-')])
        
        context = f"""Analyze this code change and provide a compact explanation.

INTENT: {intent or 'Not specified'}

AFFECTED FILES: {', '.join(affected_files) if affected_files else 'Unknown'}

DIFF STATS: +{added_lines} -{removed_lines} lines

DIFF CONTENT:
{diff_content}

Provide a structured response with:
1. SUMMARY: One sentence describing the main change
2. CHANGE_TYPE: One of [feature, bugfix, refactor, performance, security, config]
3. MODULES: List affected modules/components

Keep response under 150 words total."""

        return context
        
    async def _query_phi_mini(self, context: str) -> str:
        """Query Phi-3-mini via API"""
        
        payload = {
            "model": self.model_name,
            "prompt": context,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stop": ["\n\n", "---"],
            "echo": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.model_endpoint, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["text"].strip()
                else:
                    raise Exception(f"Phi-3-mini API error: {response.status}")
                    
    def _structure_explanation(self, raw_explanation: str, diff_content: str, 
                             affected_files: List[str]) -> Dict[str, Any]:
        """Structure raw explanation into standardized format"""
        
        # Parse Phi-3-mini response
        lines = raw_explanation.strip().split('\n')
        
        summary = ""
        change_type = "refactor"  # default
        modules = affected_files.copy()
        
        for line in lines:
            line = line.strip()
            if line.upper().startswith("SUMMARY:"):
                summary = line[8:].strip()
            elif line.upper().startswith("CHANGE_TYPE:"):
                change_type = line[12:].strip().lower()
            elif line.upper().startswith("MODULES:"):
                modules_text = line[8:].strip()
                if modules_text:
                    modules = [m.strip() for m in modules_text.split(',')]
                    
        # Fallback to first line if no structured response
        if not summary and lines:
            summary = lines[0][:100]  # First 100 chars
            
        # Validate change type
        valid_types = ["feature", "bugfix", "refactor", "performance", "security", "config"]
        if change_type not in valid_types:
            change_type = "refactor"
            
        return {
            "summary": summary or "Code changes detected",
            "change_type": change_type,
            "modules": modules or ["unknown"]
        }
        
    def _generate_hash(self, explanation: Dict[str, Any]) -> str:
        """Generate deterministic hash from explanation"""
        
        # Create deterministic string for hashing
        hash_input = f"{explanation['summary']}|{explanation['change_type']}|{','.join(sorted(explanation['modules']))}"
        
        # Generate 8-character hash (matches QA-301 spec)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        
    def _fallback_explanation(self, diff_content: str, intent: str, 
                            affected_files: List[str]) -> Dict[str, Any]:
        """Fallback explanation when Phi-3-mini fails"""
        
        # Simple heuristic-based explanation
        added_lines = len([line for line in diff_content.split('\n') if line.startswith('+')])
        removed_lines = len([line for line in diff_content.split('\n') if line.startswith('-')])
        
        if added_lines > removed_lines * 2:
            change_type = "feature"
            summary = f"Adds new functionality with {added_lines} new lines"
        elif removed_lines > added_lines * 2:
            change_type = "refactor"
            summary = f"Removes code with {removed_lines} deleted lines"
        else:
            change_type = "refactor"
            summary = f"Modifies existing code (+{added_lines} -{removed_lines})"
            
        if intent:
            summary = f"{intent}: {summary}"
            
        fallback_explanation = {
            "summary": summary,
            "change_type": change_type,
            "modules": affected_files or ["unknown"]
        }
        
        return {
            "meta_hash": self._generate_hash(fallback_explanation),
            "summary": summary,
            "logic_change_type": change_type,
            "affected_modules": affected_files or ["unknown"],
            "intent": intent or "Auto-detected",
            "timestamp": time.time(),
            "model": "fallback_heuristic",
            "deterministic": True
        }

class MetaExplainerCLI:
    """Command-line interface for meta explanation generation"""
    
    def __init__(self):
        self.explainer = PhiMiniExplainer()
        self.redis_client = None
        
    async def initialize(self):
        """Initialize Redis connection for A2A events"""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379/0")
            await self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            
    async def explain_pr(self, pr_path: str = None, diff_file: str = None, 
                        intent: str = "", output_file: str = None) -> Dict[str, Any]:
        """Generate meta explanation for PR"""
        
        # Determine input source
        if pr_path:
            diff_content, affected_files = await self._extract_from_pr_path(pr_path)
        elif diff_file:
            diff_content, affected_files = await self._extract_from_diff_file(diff_file)
        else:
            # Try to detect current git changes
            diff_content, affected_files = await self._extract_from_git()
            
        # Generate explanation
        explanation = await self.explainer.explain_changes(
            diff_content, intent, affected_files
        )
        
        # Output as YAML
        yaml_output = yaml.dump(explanation, default_flow_style=False)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(yaml_output)
            logger.info(f"📝 Meta explanation saved to {output_file}")
        else:
            print(yaml_output)
            
        # Publish A2A event
        await self._publish_a2a_event(explanation)
        
        # Push metrics
        await self._push_metrics()
        
        return explanation
        
    async def _extract_from_pr_path(self, pr_path: str) -> Tuple[str, List[str]]:
        """Extract diff and files from PR directory"""
        pr_dir = Path(pr_path)
        
        # Look for common diff files
        diff_files = list(pr_dir.glob("*.diff")) + list(pr_dir.glob("*.patch"))
        
        if diff_files:
            with open(diff_files[0]) as f:
                diff_content = f.read()
        else:
            # Generate diff from directory
            diff_content = await self._generate_diff_from_directory(pr_dir)
            
        # Find affected files
        affected_files = []
        for line in diff_content.split('\n'):
            if line.startswith('+++') or line.startswith('---'):
                file_path = line.split('\t')[0][4:]  # Remove +++ or ---
                if file_path != '/dev/null':
                    affected_files.append(os.path.basename(file_path))
                    
        return diff_content, list(set(affected_files))
        
    async def _extract_from_diff_file(self, diff_file: str) -> Tuple[str, List[str]]:
        """Extract diff content and affected files from diff file"""
        with open(diff_file) as f:
            diff_content = f.read()
            
        affected_files = []
        for line in diff_content.split('\n'):
            if line.startswith('+++') or line.startswith('---'):
                file_path = line.split('\t')[0][4:]
                if file_path != '/dev/null':
                    affected_files.append(os.path.basename(file_path))
                    
        return diff_content, list(set(affected_files))
        
    async def _extract_from_git(self) -> Tuple[str, List[str]]:
        """Extract diff from current git changes"""
        try:
            # Get staged changes
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True,
                text=True,
                check=True
            )
            
            diff_content = result.stdout
            
            if not diff_content:
                # Get unstaged changes if no staged changes
                result = subprocess.run(
                    ["git", "diff"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                diff_content = result.stdout
                
            # Get affected files
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True,
                text=True
            )
            
            affected_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            if not affected_files:
                result = subprocess.run(
                    ["git", "diff", "--name-only"],
                    capture_output=True,
                    text=True
                )
                affected_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                
            return diff_content, [os.path.basename(f) for f in affected_files]
            
        except subprocess.CalledProcessError:
            logger.warning("Git not available, using empty diff")
            return "", []
            
    async def _generate_diff_from_directory(self, directory: Path) -> str:
        """Generate diff by comparing directory contents"""
        # Simplified: just list modified files
        files = list(directory.rglob("*.py"))
        diff_content = f"# Directory scan: {len(files)} Python files found\n"
        
        for file in files[:10]:  # Limit to first 10
            diff_content += f"# Modified: {file.name}\n"
            
        return diff_content
        
    async def _publish_a2a_event(self, explanation: Dict[str, Any]):
        """Publish EXPLAIN_META_HASH event to A2A ticket-bus"""
        if not self.redis_client:
            return
            
        try:
            event = {
                "event_type": "EXPLAIN_META_HASH",
                "meta_hash": explanation["meta_hash"],
                "summary": explanation["summary"],
                "timestamp": explanation["timestamp"],
                "source": "explain_meta.py"
            }
            
            await self.redis_client.xadd("ticket-bus", event)
            logger.info(f"📤 Published A2A event: EXPLAIN_META_HASH")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish A2A event: {e}")
            
    async def _push_metrics(self):
        """Push metrics to Prometheus gateway"""
        try:
            gateway = os.environ.get("PROMETHEUS_GATEWAY", "localhost:9091")
            push_to_gateway(gateway, job="meta_explainer", registry=registry)
        except Exception as e:
            logger.debug(f"Metrics push failed: {e}")

async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="QA-301 Meta Explainer Hashing")
    parser.add_argument("--pr-path", help="Path to PR directory")
    parser.add_argument("--diff-file", help="Path to diff file")
    parser.add_argument("--intent", default="", help="PR intent description")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    cli = MetaExplainerCLI()
    await cli.initialize()
    
    try:
        explanation = await cli.explain_pr(
            pr_path=args.pr_path,
            diff_file=args.diff_file,
            intent=args.intent,
            output_file=args.output
        )
        
        logger.info(f"✅ Meta explanation complete: {explanation['meta_hash']}")
        
    except Exception as e:
        logger.error(f"❌ Meta explanation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())