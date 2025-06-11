"""
SciWave: Long-Term Science Planning & Literature Summarization
Triple Agent Synergy: Fetch → Review → Peer

🔬 SCI-100: Fetch Agent - ArXiv + PubMed daily scraper
🧠 SCI-110: Review Agent - Extractive + abstractive paper summary  
👥 SCI-120: Peer Agent - Self-critique + cross-agent comparison
"""

from .fetch_agent import FetchAgent
from .review_agent import ReviewAgent
from .peer_agent import PeerAgent
from .swarm_coordinator import SciWaveCoordinator

__all__ = ['FetchAgent', 'ReviewAgent', 'PeerAgent', 'SciWaveCoordinator']
__version__ = '0.1.0' 