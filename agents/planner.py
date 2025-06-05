#!/usr/bin/env python3
"""
Planner Agent
============

Agent that reads from scratchpad every 5 seconds and weaves notes into plans.
Continuously monitors shared scratchpad for research findings and updates plans.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from shared.scratchpad import write, read, search

logger = logging.getLogger(__name__)

class PlannerAgent:
    """Agent specialized in planning and strategy coordination"""
    
    def __init__(self):
        self.session_id = "planning_session"
        self.agent_name = "planner"
        self.monitoring = False
        self.monitor_task = None
        self.current_plan = None
        self.last_update = 0
    
    async def start_monitoring(self, session_id: str = None, interval: int = 5):
        """Start monitoring scratchpad every 5 seconds"""
        
        if session_id is None:
            session_id = self.session_id
            
        if self.monitoring:
            logger.warning("🎯 Planner already monitoring")
            return
        
        self.monitoring = True
        logger.info(f"🎯 Planner monitoring started: session={session_id}, interval={interval}s")
        
        self.monitor_task = asyncio.create_task(
            self._monitor_loop(session_id, interval)
        )
    
    async def stop_monitoring(self):
        """Stop monitoring scratchpad"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("🎯 Planner monitoring stopped")
    
    async def _monitor_loop(self, session_id: str, interval: int):
        """Main monitoring loop"""
        
        while self.monitoring:
            try:
                await self._check_and_update_plan(session_id)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Planner monitoring error: {e}")
                await asyncio.sleep(interval)  # Continue monitoring despite errors
    
    async def _check_and_update_plan(self, session_id: str):
        """Check for new information and update plan"""
        
        # Read recent entries since last update
        entries = read(session_id, limit=20)
        
        # Filter for new entries since last update
        new_entries = [
            entry for entry in entries 
            if entry.timestamp > self.last_update and entry.agent != self.agent_name
        ]
        
        if not new_entries:
            return  # No new information
        
        logger.info(f"🎯 Planner found {len(new_entries)} new entries")
        
        # Group entries by agent and type
        research_findings = [e for e in new_entries if e.agent == "researcher" and e.entry_type == "finding"]
        other_notes = [e for e in new_entries if e.entry_type == "note"]
        
        # Update plan based on new information
        updated_plan = await self._weave_plan(research_findings, other_notes, session_id)
        
        if updated_plan:
            # Write updated plan to scratchpad
            entry_id = write(
                session_id=session_id,
                agent=self.agent_name,
                content=updated_plan,
                tags=["plan", "updated"],
                entry_type="plan"
            )
            
            self.current_plan = updated_plan
            self.last_update = time.time()
            
            logger.info(f"📋 Planner updated plan: {entry_id}")
    
    async def _weave_plan(self, research_findings: List, other_notes: List, session_id: str) -> Optional[str]:
        """Weave research findings and notes into an updated plan"""
        
        if not research_findings and not other_notes:
            return None
        
        # Get current plan context
        existing_plans = read(session_id, limit=3, agent_filter=self.agent_name)
        
        # Create updated plan
        plan_sections = []
        
        # Plan header
        plan_sections.append(f"# Updated Plan - {time.strftime('%H:%M:%S')}")
        plan_sections.append("")
        
        # Incorporate research findings
        if research_findings:
            plan_sections.append("## Research Integration")
            for finding in research_findings:
                # Extract key insights from research
                insight = self._extract_insight(finding.content)
                plan_sections.append(f"- {insight}")
                
                # Add specific actions based on findings
                if "RFC" in finding.content:
                    plan_sections.append("  → Review RFC specifications for compliance")
                elif "GitHub" in finding.content:
                    plan_sections.append("  → Analyze implementation patterns")
                elif "Stack Overflow" in finding.content:
                    plan_sections.append("  → Review common issues and solutions")
            plan_sections.append("")
        
        # Incorporate other notes
        if other_notes:
            plan_sections.append("## Context Updates")
            for note in other_notes:
                plan_sections.append(f"- {note.content[:100]}...")
            plan_sections.append("")
        
        # Strategic recommendations
        plan_sections.append("## Next Steps")
        if research_findings:
            plan_sections.append("1. Deep dive into key research findings")
            plan_sections.append("2. Validate findings with additional sources")
            plan_sections.append("3. Update implementation approach based on evidence")
        else:
            plan_sections.append("1. Continue monitoring for new information")
            plan_sections.append("2. Review existing plan effectiveness")
        
        plan_sections.append("")
        
        # Priority matrix
        plan_sections.append("## Priority Matrix")
        plan_sections.append("- **High Priority**: Implementation-critical findings")
        plan_sections.append("- **Medium Priority**: Performance and optimization insights")
        plan_sections.append("- **Low Priority**: Background and reference material")
        
        return "\n".join(plan_sections)
    
    def _extract_insight(self, content: str) -> str:
        """Extract key insight from research finding"""
        
        if "RFC" in content:
            return f"Standards compliance: {content[:60]}..."
        elif "Stack Overflow" in content:
            return f"Community insight: {content[:60]}..."
        elif "GitHub" in content:
            return f"Implementation example: {content[:60]}..."
        elif "paper" in content.lower():
            return f"Academic research: {content[:60]}..."
        else:
            return f"General finding: {content[:60]}..."
    
    async def create_initial_plan(self, objective: str, session_id: str = None) -> Dict[str, Any]:
        """Create initial plan for an objective"""
        
        if session_id is None:
            session_id = self.session_id
        
        start_time = time.time()
        
        plan_content = f"""# Initial Plan: {objective}

## Objective
{objective}

## Strategy
1. **Research Phase**: Gather relevant information and evidence
2. **Analysis Phase**: Analyze findings and identify patterns
3. **Implementation Phase**: Execute based on evidence
4. **Review Phase**: Validate results and iterate

## Success Criteria
- [ ] Comprehensive research completed
- [ ] Clear implementation path identified
- [ ] Stakeholder approval obtained
- [ ] Measurable outcomes defined

## Timeline
- Research: 2-3 days
- Analysis: 1 day
- Implementation: 3-5 days
- Review: 1 day

## Resource Requirements
- Research team access
- Technical infrastructure
- Quality assurance process

*Plan created at {time.strftime('%Y-%m-%d %H:%M:%S')} by {self.agent_name}*
"""
        
        # Write initial plan to scratchpad
        entry_id = write(
            session_id=session_id,
            agent=self.agent_name,
            content=plan_content,
            tags=["plan", "initial", "objective"],
            entry_type="plan"
        )
        
        self.current_plan = plan_content
        self.last_update = time.time()
        
        return {
            "objective": objective,
            "plan_id": entry_id,
            "session_id": session_id,
            "latency_ms": (time.time() - start_time) * 1000,
            "status": "success"
        }
    
    def get_current_plan(self, session_id: str = None) -> Optional[str]:
        """Get the most recent plan"""
        
        if session_id is None:
            session_id = self.session_id
        
        plans = read(session_id, limit=1, agent_filter=self.agent_name)
        
        if plans:
            return plans[0].content
        return self.current_plan

# Global planner instance
planner = PlannerAgent()

async def start_plan_monitoring(session_id: str = "default", interval: int = 5):
    """Convenience function to start plan monitoring"""
    await planner.start_monitoring(session_id, interval)

async def stop_plan_monitoring():
    """Convenience function to stop plan monitoring"""
    await planner.stop_monitoring()

async def create_plan(objective: str, session_id: str = "default") -> Dict[str, Any]:
    """Convenience function to create initial plan"""
    return await planner.create_initial_plan(objective, session_id)