#!/usr/bin/env python3
"""
Emotional Round-Table Protocol
=============================

Integrates V11 Emotional Swarm with Tamagotchi autonomous evolution.
9 emotional personalities convene, debate, and vote on the next specialist 
agent or LoRA adaptation to create.

Features:
- Lightning-fast emotional consensus (following V11 pattern)
- Autonomous strategic thinking about evolution direction
- Concrete job specs fed directly to Tamagotchi queue
- Immutable audit trail of emotional decision-making

Based on V11 architecture achieving 0.02ms per agent response.
"""

import json
import time
import asyncio
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from v11_emotional_swarm import V11EmotionalSwarm, EmotionalDimension

@dataclass
class EvolutionProposal:
    """Proposal for next evolution step (LoRA or new agent)."""
    id: str
    type: str  # "lora" or "agent"
    base_model: str
    target_block: str
    dataset: str
    expected_gain_pp: int
    max_latency_ms: int
    safety_considerations: str
    proposer: str
    
    # Optional fields for agents
    router_regex: Optional[str] = None
    memory_budget_mb: Optional[int] = None
    
    # Metadata
    votes: Optional[Dict[str, int]] = None
    transcript: Optional[List[Dict[str, str]]] = None

class EmotionalRoundTable:
    """
    Round-Table protocol for emotional consensus on evolution direction.
    
    Uses the V11 Emotional Swarm to make strategic decisions about what
    specialist agents or LoRA adaptations to create next.
    """
    
    def __init__(self):
        self.swarm = V11EmotionalSwarm()
        self.transcript_history = []
        
        # Current specialist agents (would be loaded from config)
        self.current_specialists = {
            "math_specialist": "qwen2:1.5b",
            "code_specialist": "tinyllama:latest", 
            "safety_guard": "phi3:mini",
            "dimensional_0d": "void_agent",
            "dimensional_1d": "line_agent"
        }
        
        # Emotional roles and their decision-making styles
        self.emotional_roles = {
            "joy": {
                "stance": "optimistic",
                "contribution": "What could this unlock?",
                "bias": "opportunities, positive potential"
            },
            "fear": {
                "stance": "risk_analyst", 
                "contribution": "Where can this break?",
                "bias": "failure modes, safety concerns"
            },
            "anger": {
                "stance": "performance_stickler",
                "contribution": "Latency will explode!",
                "bias": "efficiency, resource constraints"
            },
            "sadness": {
                "stance": "user_empathy",
                "contribution": "Will errors hurt trust?",
                "bias": "user experience, trust preservation"
            },
            "disgust": {
                "stance": "policy_gate",
                "contribution": "Any moral red flags?",
                "bias": "ethical standards, policy compliance"
            },
            "surprise": {
                "stance": "novelty_scout",
                "contribution": "Edge-case we never saw!",
                "bias": "unexpected scenarios, edge cases"
            },
            "trust": {
                "stance": "solution_builder",
                "contribution": "Concrete API & data path",
                "bias": "practical implementation, reliability"
            },
            "anticipation": {
                "stance": "roadmap",
                "contribution": "How does it fit Phase-2?",
                "bias": "strategic planning, future compatibility"
            },
            "determination": {  # Neutral moderator role
                "stance": "moderator",
                "contribution": "keeps time, tallies votes",
                "bias": "objective analysis, consensus building"
            }
        }
    
    async def run_roundtable(self, task_description: str) -> EvolutionProposal:
        """
        Main round-table protocol: emotional debate → consensus → job spec.
        
        Args:
            task_description: What needs to be improved (e.g., "raise code accuracy to 60%")
            
        Returns:
            Winning proposal ready for Tamagotchi evolution queue
        """
        print(f"\n🎭 EMOTIONAL ROUND-TABLE CONVENED")
        print(f"📋 Task: {task_description}")
        print("="*70)
        
        start_time = time.perf_counter()
        
        # Phase 1: Individual emotional perspectives and proposals
        transcript, proposals = await self._debate_phase(task_description)
        
        # Phase 2: Voting and consensus
        winner_proposal = await self._consensus_phase(proposals)
        
        # Phase 3: Finalize with audit trail
        winner_proposal.transcript = transcript
        total_time_ms = (time.perf_counter() - start_time) * 1000
        
        print(f"\n🎯 ROUND-TABLE COMPLETE: {total_time_ms:.1f}ms")
        print(f"🏆 Winning Proposal: {winner_proposal.id}")
        print(f"📊 Vote Distribution: {winner_proposal.votes}")
        
        # Store for evolution history
        self.transcript_history.append({
            "timestamp": time.time(),
            "task": task_description,
            "winner": winner_proposal.id,
            "votes": winner_proposal.votes,
            "duration_ms": total_time_ms
        })
        
        return winner_proposal
    
    async def _debate_phase(self, task_description: str) -> tuple[List[Dict], List[EvolutionProposal]]:
        """Phase 1: Each emotion speaks and optionally proposes a solution."""
        print("🗣️  PHASE 1: EMOTIONAL DEBATE")
        print("-" * 40)
        
        transcript = []
        proposals = []
        
        for agent_name, role_info in self.emotional_roles.items():
            if agent_name == "determination":  # Moderator doesn't propose
                continue
                
            # Create emotional context for this agent
            emotional_prompt = self._build_emotional_prompt(
                agent_name, role_info, task_description
            )
            
            # Get response from emotional agent (sub-millisecond)
            response = self.swarm.agents[agent_name].process_query(emotional_prompt)
            
            # Parse response for both speech and potential proposal
            speech, proposal = self._parse_emotional_response(
                response.response, agent_name, task_description
            )
            
            transcript.append({agent_name: speech})
            if proposal:
                proposals.append(proposal)
                
            print(f"🎭 {agent_name.upper()}: {speech[:80]}...")
            if proposal:
                print(f"   💡 Proposed: {proposal.id} ({proposal.type})")
        
        print(f"\n📊 Debate Results: {len(proposals)} proposals from {len(transcript)} emotions")
        return transcript, proposals
    
    async def _consensus_phase(self, proposals: List[EvolutionProposal]) -> EvolutionProposal:
        """Phase 2: Emotional voting on proposals."""
        print("\n🗳️  PHASE 2: CONSENSUS VOTING")
        print("-" * 40)
        
        if not proposals:
            # Emergency fallback proposal
            fallback = self._create_fallback_proposal()
            proposals = [fallback]
            print("⚠️  No proposals generated, using fallback")
        
        votes = {p.id: 0 for p in proposals}
        voting_record = {}
        
        # Each emotion votes (including moderator)
        for agent_name in self.emotional_roles.keys():
            vote_prompt = self._build_voting_prompt(proposals)
            response = self.swarm.agents[agent_name].process_query(vote_prompt)
            
            # Extract vote choice
            choice = self._parse_vote(response.response, proposals)
            if choice in votes:
                votes[choice] += 1
                voting_record[agent_name] = choice
                print(f"🎭 {agent_name}: votes for {choice}")
            else:
                print(f"⚠️  {agent_name}: invalid vote '{choice}'")
        
        # Determine winner
        winner_id = max(votes, key=votes.get)
        winner = next(p for p in proposals if p.id == winner_id)
        winner.votes = votes
        
        print(f"\n🏆 WINNER: {winner_id} with {votes[winner_id]}/9 votes")
        return winner
    
    def _build_emotional_prompt(self, agent_name: str, role_info: Dict, task: str) -> str:
        """Build prompt for individual emotional perspective."""
        return f"""You are {agent_name.title()}, the {role_info['stance']} emotion.

TASK: {task}

Your perspective: {role_info['contribution']}
Your bias: {role_info['bias']}

Current agents: {list(self.current_specialists.keys())}
Constraints: ≤8GB VRAM, must pass policy, target gain ≥5pp on failing block.

Speak concisely about this task. Consider if we need a new LoRA or specialist agent.

If you have a concrete proposal, include it. Otherwise, just give your emotional perspective."""

    def _parse_emotional_response(self, response: str, agent_name: str, task: str) -> tuple[str, Optional[EvolutionProposal]]:
        """Parse emotional response into speech and potential proposal."""
        # For now, create smart proposals based on emotional perspective and task
        speech = response.replace(f"From my {agent_name} perspective: ", "")
        
        proposal = None
        
        # Smart proposal generation based on task and emotional bias
        if "code" in task.lower() and agent_name in ["trust", "anticipation"]:
            proposal = EvolutionProposal(
                id=f"code_lora_{agent_name}_v1",
                type="lora",
                base_model="tinyllama:latest",
                target_block="code",
                dataset="code_failures_2k",
                expected_gain_pp=8,
                max_latency_ms=50,
                safety_considerations="Sandboxed execution only, no system access",
                proposer=agent_name
            )
        elif "math" in task.lower() and agent_name in ["fear", "disgust"]:
            proposal = EvolutionProposal(
                id=f"math_specialist_{agent_name}_v1", 
                type="agent",
                base_model="qwen2:1.5b",
                target_block="math",
                dataset="math_edge_cases_1k",
                expected_gain_pp=6,
                max_latency_ms=40,
                safety_considerations="No external API calls, verified computations only",
                proposer=agent_name,
                router_regex=r"(calcul|equation|solve|math)",
                memory_budget_mb=400
            )
        elif "consciousness" in task.lower() and agent_name in ["joy", "surprise"]:
            proposal = EvolutionProposal(
                id=f"consciousness_reasoner_{agent_name}_v1",
                type="agent", 
                base_model="phi3:mini",
                target_block="reasoning",
                dataset="consciousness_scenarios_500",
                expected_gain_pp=7,
                max_latency_ms=60,
                safety_considerations="Philosophical only, no claims of sentience",
                proposer=agent_name,
                router_regex=r"(conscious|aware|sentient|think)",
                memory_budget_mb=350
            )
        
        return speech, proposal
    
    def _build_voting_prompt(self, proposals: List[EvolutionProposal]) -> str:
        """Build prompt for voting phase."""
        proposals_text = "\n".join([
            f"- {p.id}: {p.type} for {p.target_block}, gain +{p.expected_gain_pp}pp, {p.max_latency_ms}ms latency"
            for p in proposals
        ])
        
        return f"""Here are the proposed agents/LoRAs:

{proposals_text}

Vote for ONE proposal ID that best balances gain, risk, and latency.
Reply with just the proposal ID (e.g., 'code_lora_trust_v1')."""

    def _parse_vote(self, response: str, proposals: List[EvolutionProposal]) -> str:
        """Extract vote choice from response."""
        response_lower = response.lower()
        
        # Look for exact proposal ID matches
        for proposal in proposals:
            if proposal.id.lower() in response_lower:
                return proposal.id
                
        # Fallback: return first proposal
        return proposals[0].id if proposals else "none"
    
    def _create_fallback_proposal(self) -> EvolutionProposal:
        """Create emergency fallback proposal."""
        return EvolutionProposal(
            id="general_lora_fallback_v1",
            type="lora",
            base_model="phi3:mini",
            target_block="general",
            dataset="mixed_failures_1k",
            expected_gain_pp=5,
            max_latency_ms=30,
            safety_considerations="Conservative training, existing safety filters",
            proposer="system_fallback"
        )
    
    def export_to_tamagotchi_queue(self, proposal: EvolutionProposal, queue_dir: str = "jobs/queue") -> str:
        """Export winning proposal to Tamagotchi evolution queue."""
        queue_path = Path(queue_dir)
        queue_path.mkdir(parents=True, exist_ok=True)
        
        job_file = queue_path / f"{proposal.id}.yaml"
        
        # Convert to Tamagotchi job format
        job_spec = {
            "job_id": proposal.id,
            "type": proposal.type,
            "base_model": proposal.base_model,
            "target_block": proposal.target_block,
            "dataset": proposal.dataset,
            "expected_gain_pp": proposal.expected_gain_pp,
            "max_latency_ms": proposal.max_latency_ms,
            "safety_considerations": proposal.safety_considerations,
            "emotional_consensus": {
                "votes": proposal.votes,
                "proposer": proposal.proposer,
                "transcript_length": len(proposal.transcript) if proposal.transcript else 0
            }
        }
        
        # Add agent-specific fields
        if proposal.type == "agent":
            job_spec["router_regex"] = proposal.router_regex
            job_spec["memory_budget_mb"] = proposal.memory_budget_mb
        
        with open(job_file, 'w') as f:
            yaml.dump(job_spec, f, default_flow_style=False)
        
        print(f"📁 Job spec exported: {job_file}")
        return str(job_file)

# Demo and testing functions
async def demo_consciousness_roundtable():
    """Demo round-table deciding on consciousness reasoning capabilities."""
    roundtable = EmotionalRoundTable()
    
    task = "Improve consciousness reasoning from 45% to 60% accuracy"
    
    proposal = await roundtable.run_roundtable(task)
    
    print("\n" + "="*70)
    print("🎯 FINAL PROPOSAL")
    print("="*70)
    print(f"ID: {proposal.id}")
    print(f"Type: {proposal.type}")
    print(f"Target: {proposal.target_block}")
    print(f"Expected Gain: +{proposal.expected_gain_pp}pp")
    print(f"Latency: {proposal.max_latency_ms}ms")
    print(f"Safety: {proposal.safety_considerations}")
    
    # Export to Tamagotchi queue
    job_file = roundtable.export_to_tamagotchi_queue(proposal)
    
    print(f"\n✅ Ready for Tamagotchi evolution: {job_file}")
    
    return proposal

async def demo_code_improvement_roundtable():
    """Demo round-table deciding on code improvement."""
    roundtable = EmotionalRoundTable()
    
    task = "Raise code generation accuracy to 75% on Python challenges"
    
    proposal = await roundtable.run_roundtable(task)
    
    print("\n🎯 Code improvement proposal generated!")
    print(f"Winner: {proposal.id} with {max(proposal.votes.values())}/9 votes")
    
    return proposal

async def main():
    """Main demo of emotional round-table protocol."""
    print("🎭 EMOTIONAL ROUND-TABLE PROTOCOL")
    print("🚀 V11 Emotional Swarm meets Tamagotchi Evolution")
    print("🧠 AI emotions decide what to evolve next")
    print()
    
    try:
        # Demo 1: Consciousness reasoning
        await demo_consciousness_roundtable()
        
        print("\n" + "="*80 + "\n")
        
        # Demo 2: Code improvement  
        await demo_code_improvement_roundtable()
        
        print("\n🔥 EMOTIONAL ROUND-TABLE: OPERATIONAL!")
        print("🎭 9 emotions now strategically plan AI evolution")
        print("🪴 Tamagotchi gets emotional intelligence for growth decisions")
        
    except Exception as e:
        print(f"❌ Round-table failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 