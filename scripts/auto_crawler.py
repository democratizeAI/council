#!/usr/bin/env python3
"""
🤖 AutoGen Auto-Crawler for Day-2 Operations
Refreshes training queue with 5-10 high-quality challenges nightly at 02:15
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import aiohttp
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoCrawler:
    """Automated data crawler for training pipeline"""
    
    def __init__(self, config_path: str = "config/crawler_config.json"):
        self.config = self.load_config(config_path)
        self.session = None
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load crawler configuration"""
        default_config = {
            "target_count": 7,
            "categories": ["logic", "math", "code", "reasoning", "creative"],
            "difficulty_levels": ["medium", "hard"],
            "sources": [
                {"name": "leetcode", "weight": 0.3, "enabled": True},
                {"name": "project_euler", "weight": 0.2, "enabled": True},
                {"name": "kaggle_competitions", "weight": 0.2, "enabled": True},
                {"name": "arxiv_papers", "weight": 0.15, "enabled": True},
                {"name": "github_issues", "weight": 0.15, "enabled": True}
            ],
            "quality_threshold": 0.8,
            "output_dir": "datasets/crawler_output"
        }
        
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            
        return default_config
    
    async def crawl_challenges(self) -> List[Dict[str, Any]]:
        """Main crawling logic"""
        logger.info("🕷️ Starting challenge crawl...")
        
        challenges = []
        target_count = self.config["target_count"]
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # Crawl from each enabled source
            for source in self.config["sources"]:
                if not source["enabled"]:
                    continue
                    
                source_name = source["name"]
                target_from_source = max(1, int(target_count * source["weight"]))
                
                logger.info(f"📡 Crawling {target_from_source} challenges from {source_name}")
                
                try:
                    source_challenges = await self.crawl_source(source_name, target_from_source)
                    challenges.extend(source_challenges)
                except Exception as e:
                    logger.error(f"❌ Failed to crawl {source_name}: {e}")
        
        # Filter and rank by quality
        high_quality = [c for c in challenges if c.get("quality_score", 0) >= self.config["quality_threshold"]]
        
        # Shuffle and limit to target count
        random.shuffle(high_quality)
        final_challenges = high_quality[:target_count]
        
        logger.info(f"✅ Collected {len(final_challenges)} high-quality challenges")
        return final_challenges
    
    async def crawl_source(self, source_name: str, count: int) -> List[Dict[str, Any]]:
        """Crawl specific source"""
        
        if source_name == "leetcode":
            return await self.crawl_leetcode(count)
        elif source_name == "project_euler":
            return await self.crawl_project_euler(count)
        elif source_name == "kaggle_competitions":
            return await self.crawl_kaggle(count)
        elif source_name == "arxiv_papers":
            return await self.crawl_arxiv(count)
        elif source_name == "github_issues":
            return await self.crawl_github_issues(count)
        else:
            logger.warning(f"Unknown source: {source_name}")
            return []
    
    async def crawl_leetcode(self, count: int) -> List[Dict[str, Any]]:
        """Mock LeetCode API crawler (replace with actual API)"""
        challenges = []
        
        # Mock challenges for demo
        mock_problems = [
            {"id": "two-sum", "title": "Two Sum", "difficulty": "medium", "category": "logic"},
            {"id": "valid-parentheses", "title": "Valid Parentheses", "difficulty": "medium", "category": "logic"},
            {"id": "merge-intervals", "title": "Merge Intervals", "difficulty": "hard", "category": "logic"},
            {"id": "binary-tree-paths", "title": "Binary Tree Paths", "difficulty": "medium", "category": "logic"},
        ]
        
        for i, problem in enumerate(random.sample(mock_problems, min(count, len(mock_problems)))):
            challenge = {
                "id": f"leetcode_{problem['id']}",
                "title": problem["title"],
                "source": "leetcode",
                "category": problem["category"],
                "difficulty": problem["difficulty"],
                "description": f"Solve the {problem['title']} problem from LeetCode",
                "quality_score": random.uniform(0.7, 0.95),
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["algorithmic", "coding", problem["difficulty"]]
            }
            challenges.append(challenge)
        
        return challenges
    
    async def crawl_project_euler(self, count: int) -> List[Dict[str, Any]]:
        """Mock Project Euler crawler"""
        challenges = []
        
        for i in range(min(count, 3)):
            challenge = {
                "id": f"euler_{100 + i}",
                "title": f"Project Euler Problem {100 + i}",
                "source": "project_euler",
                "category": "math",
                "difficulty": "hard",
                "description": f"Mathematical problem involving number theory and computation",
                "quality_score": random.uniform(0.85, 0.98),
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["mathematical", "computational", "hard"]
            }
            challenges.append(challenge)
        
        return challenges
    
    async def crawl_kaggle(self, count: int) -> List[Dict[str, Any]]:
        """Mock Kaggle competitions crawler"""
        challenges = []
        
        topics = ["ML", "NLP", "Computer Vision", "Time Series"]
        
        for i, topic in enumerate(random.sample(topics, min(count, len(topics)))):
            challenge = {
                "id": f"kaggle_{topic.lower().replace(' ', '_')}",
                "title": f"{topic} Challenge",
                "source": "kaggle",
                "category": "code",
                "difficulty": "hard",
                "description": f"Data science challenge focusing on {topic}",
                "quality_score": random.uniform(0.8, 0.95),
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["data-science", "ml", topic.lower()]
            }
            challenges.append(challenge)
        
        return challenges
    
    async def crawl_arxiv(self, count: int) -> List[Dict[str, Any]]:
        """Mock ArXiv papers crawler"""
        challenges = []
        
        for i in range(min(count, 2)):
            challenge = {
                "id": f"arxiv_summary_{i}",
                "title": f"Research Paper Summary Task {i}",
                "source": "arxiv",
                "category": "reasoning",
                "difficulty": "hard",
                "description": "Summarize and analyze recent research paper",
                "quality_score": random.uniform(0.75, 0.9),
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["research", "analysis", "reasoning"]
            }
            challenges.append(challenge)
        
        return challenges
    
    async def crawl_github_issues(self, count: int) -> List[Dict[str, Any]]:
        """Mock GitHub issues crawler"""
        challenges = []
        
        for i in range(min(count, 2)):
            challenge = {
                "id": f"github_issue_{i}",
                "title": f"Debug Code Issue {i}",
                "source": "github",
                "category": "code",
                "difficulty": "medium",
                "description": "Debug and fix code issue from open source project",
                "quality_score": random.uniform(0.7, 0.88),
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["debugging", "code-review", "open-source"]
            }
            challenges.append(challenge)
        
        return challenges
    
    def save_challenges(self, challenges: List[Dict[str, Any]]) -> str:
        """Save challenges to output directory"""
        output_dir = Path(self.config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"crawled_challenges_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(challenges, f, indent=2, default=str)
        
        logger.info(f"💾 Saved {len(challenges)} challenges to {output_file}")
        return str(output_file)
    
    async def feed_to_queue(self, challenges: List[Dict[str, Any]]) -> bool:
        """Feed challenges to training queue"""
        try:
            # Mock feeding to training queue
            # In real implementation, this would call the training scheduler API
            logger.info(f"🍽️ Feeding {len(challenges)} challenges to training queue")
            
            # Simulate API call to scheduler
            await asyncio.sleep(0.1)  # Simulate network delay
            
            logger.info("✅ Successfully fed challenges to training queue")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to feed challenges to queue: {e}")
            return False

async def main():
    """Main crawler execution"""
    parser = argparse.ArgumentParser(description="AutoGen Auto-Crawler")
    parser.add_argument("--config", default="config/crawler_config.json", help="Config file path")
    parser.add_argument("--feed-now", action="store_true", help="Feed to queue immediately")
    parser.add_argument("--dry-run", action="store_true", help="Don't save or feed, just log")
    
    args = parser.parse_args()
    
    crawler = AutoCrawler(args.config)
    
    # Crawl challenges
    challenges = await crawler.crawl_challenges()
    
    if not challenges:
        logger.warning("⚠️ No challenges collected")
        return
    
    if not args.dry_run:
        # Save to disk
        output_file = crawler.save_challenges(challenges)
        
        # Feed to training queue if requested
        if args.feed_now:
            success = await crawler.feed_to_queue(challenges)
            if not success:
                logger.error("❌ Failed to feed challenges to training queue")
                return
    
    logger.info(f"🎉 Crawler completed successfully - {len(challenges)} challenges processed")

if __name__ == "__main__":
    asyncio.run(main()) 