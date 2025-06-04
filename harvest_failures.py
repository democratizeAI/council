#!/usr/bin/env python3
"""
Agent-0 Failure Harvester - Phase 3 Self-Improvement
===================================================

Analyzes yesterday's failed responses and uses Agent-0 to rewrite them
into high-quality training data for QLoRA fine-tuning.

Flow:
1. Query memory for responses with success=False
2. Agent-0 rewrites each failure with step-by-step reasoning
3. Log improved Q&A pairs to training dataset
4. Generate training statistics and quality metrics
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio

# Add project paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fork', 'swarm_autogen'))

from faiss_memory import FaissMemory
from router.voting import vote

class FailureHarvester:
    """Agent-0 powered failure harvesting system"""
    
    def __init__(self, memory_path: str = "memory/vector_store"):
        """Initialize with memory connection"""
        self.memory = FaissMemory(memory_path)
        self.harvest_stats = {
            "failures_found": 0,
            "rewrites_successful": 0,
            "quality_improvements": 0,
            "training_pairs_generated": 0,
            "harvest_timestamp": time.time()
        }
        
    async def harvest_yesterday_failures(self) -> List[Dict[str, Any]]:
        """Find all failed responses from yesterday"""
        
        print("🔍 Scanning memory for yesterday's failures...")
        
        # Calculate yesterday's time range
        yesterday = datetime.now() - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0).timestamp()
        end_time = yesterday.replace(hour=23, minute=59, second=59).timestamp()
        
        # Query memory for failures in time range
        failures = []
        try:
            # Get all memories and filter for failures
            # Note: This is a simplified implementation - in production you'd
            # want indexed queries by timestamp and success flag
            all_memories = self.memory.query("failure OR error OR wrong", k=100)
            
            for memory in all_memories:
                metadata = memory.get("metadata", {})
                timestamp = metadata.get("timestamp", 0)
                success = metadata.get("success", True)
                
                # Filter for yesterday's failures
                if start_time <= timestamp <= end_time and not success:
                    failures.append({
                        "query": metadata.get("query", ""),
                        "response": metadata.get("response", ""),
                        "timestamp": timestamp,
                        "model": metadata.get("model", "unknown"),
                        "confidence": metadata.get("confidence", 0.0),
                        "failure_reason": metadata.get("failure_reason", "unknown")
                    })
            
            self.harvest_stats["failures_found"] = len(failures)
            print(f"📊 Found {len(failures)} failures from yesterday")
            
            return failures
            
        except Exception as e:
            print(f"❌ Error harvesting failures: {e}")
            return []
    
    async def agent0_rewrite(self, failure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use Agent-0 to rewrite a failure into high-quality response"""
        
        query = failure["query"]
        bad_response = failure["response"]
        
        # Agent-0 rewrite prompt with detailed reasoning
        agent0_prompt = f"""You are Agent-0, an expert response improver. A user asked:

QUERY: {query}

The system gave this poor response:
BAD_RESPONSE: {bad_response}

Your task: Provide a much better response with clear reasoning.

Requirements:
1. Be accurate, helpful, and complete
2. Show step-by-step thinking for complex problems
3. Cite reasoning where applicable
4. If it's math, show calculations
5. If it's code, provide working examples
6. If it's knowledge, be precise and current

Format your response as:
REASONING: [Your step-by-step thinking]
ANSWER: [The improved response to give the user]"""

        try:
            # Use Council voting to get Agent-0's rewrite
            result = await vote(
                prompt=agent0_prompt,
                model_names=["autogen-hybrid", "math", "code", "logic", "knowledge"],
                top_k=1,
                use_context=False  # Don't use context for rewriting
            )
            
            rewrite_text = result.get("text", "")
            
            # Parse Agent-0's response
            if "REASONING:" in rewrite_text and "ANSWER:" in rewrite_text:
                parts = rewrite_text.split("ANSWER:", 1)
                reasoning = parts[0].replace("REASONING:", "").strip()
                answer = parts[1].strip()
                
                return {
                    "original_query": query,
                    "original_bad_response": bad_response,
                    "agent0_reasoning": reasoning,
                    "agent0_improved_response": answer,
                    "rewrite_timestamp": time.time(),
                    "quality_score": self._assess_quality(query, bad_response, answer)
                }
            else:
                print(f"⚠️ Agent-0 response format issue for query: {query[:50]}...")
                return None
                
        except Exception as e:
            print(f"❌ Agent-0 rewrite failed for query '{query[:30]}...': {e}")
            return None
    
    def _assess_quality(self, query: str, bad_response: str, good_response: str) -> float:
        """Simple quality assessment (can be enhanced with LLM scoring)"""
        
        # Basic heuristics for quality improvement
        score = 0.5  # baseline
        
        # Length improvement (more detailed usually better)
        if len(good_response) > len(bad_response) * 1.5:
            score += 0.2
        
        # Step-by-step reasoning indicators
        reasoning_words = ["because", "therefore", "step", "first", "then", "finally", "calculation"]
        if any(word in good_response.lower() for word in reasoning_words):
            score += 0.15
        
        # Code/math specific improvements
        if "```" in good_response and "```" not in bad_response:
            score += 0.1  # Added code examples
        
        if any(op in query.lower() for op in ["calculate", "solve", "what is"]) and "=" in good_response:
            score += 0.1  # Mathematical solution
        
        # Cap at 1.0
        return min(score, 1.0)
    
    async def generate_training_data(self, rewrites: List[Dict[str, Any]]) -> str:
        """Generate QLoRA training dataset from rewrites"""
        
        training_data = []
        
        for rewrite in rewrites:
            if rewrite["quality_score"] >= 0.7:  # Only high-quality rewrites
                
                # Format for instruction tuning
                training_example = {
                    "instruction": rewrite["original_query"],
                    "input": "",  # No additional input needed
                    "output": rewrite["agent0_improved_response"],
                    "reasoning": rewrite["agent0_reasoning"],
                    "quality_score": rewrite["quality_score"],
                    "harvest_timestamp": rewrite["rewrite_timestamp"]
                }
                
                training_data.append(training_example)
                self.harvest_stats["training_pairs_generated"] += 1
        
        # Save training dataset
        output_file = f"training_data/harvest_{datetime.now().strftime('%Y%m%d')}.jsonl"
        os.makedirs("training_data", exist_ok=True)
        
        with open(output_file, 'w') as f:
            for example in training_data:
                f.write(json.dumps(example) + '\n')
        
        print(f"💾 Generated {len(training_data)} training examples → {output_file}")
        return output_file
    
    async def run_harvest(self) -> Dict[str, Any]:
        """Main harvest execution"""
        
        print("🤖 Agent-0 Failure Harvester Starting...")
        print("=" * 50)
        
        start_time = time.time()
        
        # Step 1: Find failures
        failures = await self.harvest_yesterday_failures()
        
        if not failures:
            print("✅ No failures found to harvest (good news!)")
            return self.harvest_stats
        
        # Step 2: Agent-0 rewrites
        print(f"\n🔄 Starting Agent-0 rewrites for {len(failures)} failures...")
        
        rewrites = []
        for i, failure in enumerate(failures, 1):
            print(f"  📝 Rewriting {i}/{len(failures)}: {failure['query'][:40]}...")
            
            rewrite = await self.agent0_rewrite(failure)
            if rewrite:
                rewrites.append(rewrite)
                self.harvest_stats["rewrites_successful"] += 1
                
                if rewrite["quality_score"] >= 0.7:
                    self.harvest_stats["quality_improvements"] += 1
        
        # Step 3: Generate training data
        if rewrites:
            training_file = await self.generate_training_data(rewrites)
            
            # Log harvest results
            self._log_harvest_results(rewrites, training_file)
        
        elapsed = time.time() - start_time
        print(f"\n🎯 Harvest completed in {elapsed:.1f}s")
        print(f"   Failures found: {self.harvest_stats['failures_found']}")
        print(f"   Successful rewrites: {self.harvest_stats['rewrites_successful']}")
        print(f"   Quality improvements: {self.harvest_stats['quality_improvements']}")
        print(f"   Training pairs: {self.harvest_stats['training_pairs_generated']}")
        
        return self.harvest_stats
    
    def _log_harvest_results(self, rewrites: List[Dict[str, Any]], training_file: str):
        """Log detailed harvest results"""
        
        # Create harvest log
        log_file = f"logs/harvest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("logs", exist_ok=True)
        
        harvest_log = {
            "harvest_stats": self.harvest_stats,
            "training_file": training_file,
            "sample_rewrites": rewrites[:3],  # First 3 as examples
            "quality_distribution": {
                "high_quality": len([r for r in rewrites if r["quality_score"] >= 0.8]),
                "medium_quality": len([r for r in rewrites if 0.6 <= r["quality_score"] < 0.8]),
                "low_quality": len([r for r in rewrites if r["quality_score"] < 0.6])
            }
        }
        
        with open(log_file, 'w') as f:
            json.dump(harvest_log, f, indent=2)
        
        print(f"📋 Harvest log saved: {log_file}")

async def main():
    """Run daily failure harvest"""
    
    harvester = FailureHarvester()
    
    try:
        stats = await harvester.run_harvest()
        
        # Exit with success code
        if stats["training_pairs_generated"] > 0:
            print("\n✅ Harvest successful - training data ready for QLoRA")
            return 0
        else:
            print("\n⚠️ No training data generated (no failures or low quality)")
            return 1
            
    except Exception as e:
        print(f"\n💥 Harvest failed: {e}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 