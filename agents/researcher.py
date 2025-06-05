#!/usr/bin/env python3
"""
Researcher Agent
===============

Agent that performs web searches and writes findings to shared scratchpad.
Integrates with the scratchpad system for knowledge sharing.
"""

import logging
import time
from typing import Dict, Any, List
from shared.scratchpad import write, read

logger = logging.getLogger(__name__)

class ResearcherAgent:
    """Agent specialized in research and information gathering"""
    
    def __init__(self):
        self.session_id = "research_session"
        self.agent_name = "researcher"
    
    async def research_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Research a query and write findings to scratchpad"""
        
        if session_id is None:
            session_id = self.session_id
            
        start_time = time.time()
        
        try:
            # Simulate web search (in production, use real search API)
            findings = await self._simulate_web_search(query)
            
            # Write findings to scratchpad
            for finding in findings:
                entry_id = write(
                    session_id=session_id,
                    agent=self.agent_name,
                    content=finding["content"],
                    tags=finding.get("tags", ["research"]),
                    entry_type="finding"
                )
                logger.info(f"📝 Researcher wrote finding: {entry_id}")
            
            # Write summary
            summary = f"Research completed for '{query}': Found {len(findings)} relevant sources"
            write(
                session_id=session_id,
                agent=self.agent_name,
                content=summary,
                tags=["research", "summary"],
                entry_type="note"
            )
            
            return {
                "query": query,
                "findings_count": len(findings),
                "findings": findings,
                "latency_ms": (time.time() - start_time) * 1000,
                "session_id": session_id,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Research failed: {e}")
            return {
                "query": query,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000,
                "status": "error"
            }
    
    async def _simulate_web_search(self, query: str) -> List[Dict[str, Any]]:
        """Simulate web search results (replace with real search in production)"""
        
        # Simulate different types of research based on query
        if "programming" in query.lower() or "code" in query.lower():
            return [
                {
                    "content": f"Found 3 relevant RFCs for {query}: RFC-7231 (HTTP semantics), RFC-6265 (HTTP cookies), RFC-7540 (HTTP/2)",
                    "tags": ["rfc", "programming", "web"],
                    "source": "ietf.org"
                },
                {
                    "content": f"Stack Overflow discussion on {query} with 247 upvotes and 18 answers",
                    "tags": ["stackoverflow", "programming"],
                    "source": "stackoverflow.com"
                },
                {
                    "content": f"GitHub repository implementing {query} with 2.3k stars and active development",
                    "tags": ["github", "implementation"],
                    "source": "github.com"
                }
            ]
        elif "math" in query.lower() or "calculate" in query.lower():
            return [
                {
                    "content": f"Mathematical definition from Wolfram MathWorld: {query} is defined as...",
                    "tags": ["math", "definition"],
                    "source": "mathworld.wolfram.com"
                },
                {
                    "content": f"Research paper discussing {query} with 156 citations (published 2023)",
                    "tags": ["academic", "research"],
                    "source": "arxiv.org"
                }
            ]
        else:
            return [
                {
                    "content": f"Wikipedia article on {query}: comprehensive overview with 47 references",
                    "tags": ["wikipedia", "general"],
                    "source": "wikipedia.org"
                },
                {
                    "content": f"Recent news about {query} from last 30 days (5 articles found)",
                    "tags": ["news", "recent"],
                    "source": "news.google.com"
                },
                {
                    "content": f"Academic sources on {query}: 12 peer-reviewed papers found in JSTOR",
                    "tags": ["academic", "peer-reviewed"],
                    "source": "jstor.org"
                }
            ]
    
    def get_research_context(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent research findings for context"""
        
        entries = read(
            session_id=session_id,
            limit=limit,
            agent_filter=self.agent_name
        )
        
        return [
            {
                "content": entry.content,
                "timestamp": entry.timestamp,
                "tags": entry.tags,
                "entry_type": entry.entry_type
            }
            for entry in entries
        ]

# Global researcher instance
researcher = ResearcherAgent()

async def research_and_share(query: str, session_id: str = "default") -> Dict[str, Any]:
    """Convenience function for research + scratchpad sharing"""
    return await researcher.research_query(query, session_id) 