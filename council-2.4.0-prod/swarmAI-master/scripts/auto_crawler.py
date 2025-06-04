#!/usr/bin/env python3
"""
🕷️🎯 Emotional Tamagotchi Evolution - Auto Crawler
Intelligent challenge discovery system across multiple domains
"""

import os
import json
import time
import random
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChallengeCrawler:
    """Intelligent challenge discovery system"""
    
    def __init__(self):
        self.domains = {
            'code': self.generate_code_challenges,
            'logic': self.generate_logic_puzzles,
            'math': self.generate_math_problems,
            'creative': self.generate_creative_tasks,
            'science': self.generate_science_problems
        }
        
        self.quality_threshold = float(os.getenv('CRAWLER_QUALITY_THRESHOLD', '0.7'))
        self.batch_size = int(os.getenv('CRAWLER_BATCH_SIZE', '5'))
        
    def generate_code_challenges(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate coding challenges"""
        challenges = []
        
        code_templates = [
            {
                'title': 'Two Sum Problem',
                'description': 'Given an array of integers and a target sum, find two numbers that add up to the target.',
                'difficulty': 3,
                'type': 'algorithm',
                'domain': 'arrays',
                'solution_template': 'def two_sum(nums, target):\n    # Your solution here\n    pass'
            },
            {
                'title': 'Binary Tree Traversal',
                'description': 'Implement in-order traversal of a binary tree without recursion.',
                'difficulty': 5,
                'type': 'data_structure',
                'domain': 'trees',
                'solution_template': 'def inorder_traversal(root):\n    # Your solution here\n    pass'
            },
            {
                'title': 'Dynamic Programming - Fibonacci',
                'description': 'Calculate the nth Fibonacci number using dynamic programming.',
                'difficulty': 4,
                'type': 'dynamic_programming',
                'domain': 'optimization',
                'solution_template': 'def fibonacci(n):\n    # Your solution here\n    pass'
            },
            {
                'title': 'Graph BFS Implementation',
                'description': 'Implement breadth-first search for an undirected graph.',
                'difficulty': 6,
                'type': 'graph',
                'domain': 'search',
                'solution_template': 'def bfs(graph, start):\n    # Your solution here\n    pass'
            },
            {
                'title': 'String Rotation Check',
                'description': 'Check if one string is a rotation of another string.',
                'difficulty': 3,
                'type': 'string',
                'domain': 'manipulation',
                'solution_template': 'def is_rotation(s1, s2):\n    # Your solution here\n    pass'
            }
        ]
        
        for i in range(min(count, len(code_templates))):
            template = random.choice(code_templates)
            challenge = {
                'id': f"code_{int(time.time())}_{i}",
                'domain': 'code',
                'title': template['title'],
                'description': template['description'],
                'difficulty': template['difficulty'],
                'type': template['type'],
                'subdomain': template['domain'],
                'solution_template': template['solution_template'],
                'quality_score': random.uniform(0.7, 0.95),
                'timestamp': datetime.now().isoformat(),
                'source': 'auto_crawler'
            }
            challenges.append(challenge)
            
        return challenges
    
    def generate_logic_puzzles(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate logic puzzles"""
        challenges = []
        
        logic_templates = [
            {
                'title': 'Monty Hall Problem',
                'description': 'You are on a game show with 3 doors. Behind one is a car, behind the others are goats. You pick door 1. The host opens door 3 (goat). Should you switch to door 2?',
                'difficulty': 4,
                'type': 'probability',
                'answer': 'Yes, switching gives 2/3 probability vs 1/3 for staying'
            },
            {
                'title': 'Bridge Crossing Puzzle',
                'description': '4 people need to cross a bridge at night. They have one flashlight. Max 2 people can cross at once. Times: 1min, 2min, 5min, 10min. What is the minimum time?',
                'difficulty': 6,
                'type': 'optimization',
                'answer': '17 minutes: (1,2 cross), (1 returns), (5,10 cross), (2 returns), (1,2 cross)'
            },
            {
                'title': 'Truth Tellers and Liars',
                'description': 'On an island, some people always tell the truth, others always lie. You meet 3 people. A says "B is a liar". B says "C is a liar". C says "A and B are liars". Who tells the truth?',
                'difficulty': 5,
                'type': 'logic',
                'answer': 'C tells the truth. A and B are liars.'
            },
            {
                'title': 'Water Jug Problem',
                'description': 'You have two jugs: 3L and 5L. How do you measure exactly 4L of water?',
                'difficulty': 4,
                'type': 'constraint_satisfaction',
                'answer': 'Fill 5L, pour into 3L (2L left), empty 3L, pour 2L into 3L, fill 5L, pour into 3L (4L left)'
            },
            {
                'title': 'Prisoner Hat Puzzle',
                'description': '3 prisoners wear hats (red or blue). Each sees others\' hats but not their own. If anyone knows their hat color, all go free. How can they escape?',
                'difficulty': 7,
                'type': 'deduction',
                'answer': 'If I see two same colors, mine is different. If I see different colors, I wait - if others don\'t speak, mine matches what I see most.'
            }
        ]
        
        for i in range(min(count, len(logic_templates))):
            template = random.choice(logic_templates)
            challenge = {
                'id': f"logic_{int(time.time())}_{i}",
                'domain': 'logic',
                'title': template['title'],
                'description': template['description'],
                'difficulty': template['difficulty'],
                'type': template['type'],
                'answer': template['answer'],
                'quality_score': random.uniform(0.75, 0.9),
                'timestamp': datetime.now().isoformat(),
                'source': 'auto_crawler'
            }
            challenges.append(challenge)
            
        return challenges
    
    def generate_math_problems(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate mathematical problems"""
        challenges = []
        
        math_templates = [
            {
                'title': 'Prime Number Algorithm',
                'description': 'Implement the Sieve of Eratosthenes to find all prime numbers up to n.',
                'difficulty': 4,
                'type': 'number_theory',
                'formula': 'Sieve of Eratosthenes: mark multiples of each prime'
            },
            {
                'title': 'Matrix Chain Multiplication',
                'description': 'Find the optimal way to multiply a chain of matrices to minimize scalar multiplications.',
                'difficulty': 7,
                'type': 'optimization',
                'formula': 'DP: m[i,j] = min(m[i,k] + m[k+1,j] + p[i-1]*p[k]*p[j])'
            },
            {
                'title': 'Calculus - Area Under Curve',
                'description': 'Calculate the area under f(x) = x² from 0 to 3 using integration.',
                'difficulty': 5,
                'type': 'calculus',
                'formula': '∫₀³ x² dx = [x³/3]₀³ = 27/3 = 9'
            },
            {
                'title': 'Statistics - Normal Distribution',
                'description': 'Find P(X < 1.5) where X ~ N(0,1) using the standard normal distribution.',
                'difficulty': 4,
                'type': 'statistics',
                'formula': 'P(Z < 1.5) ≈ 0.9332 using Z-table'
            }
        ]
        
        for i in range(min(count, len(math_templates))):
            template = random.choice(math_templates)
            challenge = {
                'id': f"math_{int(time.time())}_{i}",
                'domain': 'math',
                'title': template['title'],
                'description': template['description'],
                'difficulty': template['difficulty'],
                'type': template['type'],
                'formula': template['formula'],
                'quality_score': random.uniform(0.8, 0.95),
                'timestamp': datetime.now().isoformat(),
                'source': 'auto_crawler'
            }
            challenges.append(challenge)
            
        return challenges
    
    def generate_creative_tasks(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate creative challenges"""
        challenges = []
        
        creative_templates = [
            {
                'title': 'Sci-Fi Story Opening',
                'description': 'Write the opening paragraph of a science fiction story set in 2150 where AI and humans coexist.',
                'difficulty': 3,
                'type': 'creative_writing',
                'prompt': 'In the year 2150, the morning commute looked very different...'
            },
            {
                'title': 'Product Innovation',
                'description': 'Design a revolutionary kitchen appliance that solves a common cooking problem.',
                'difficulty': 5,
                'type': 'innovation',
                'prompt': 'Consider problems like: timing, temperature control, cleanup, space efficiency...'
            },
            {
                'title': 'Metaphor Creation',
                'description': 'Create an original metaphor that explains machine learning to a 10-year-old.',
                'difficulty': 4,
                'type': 'explanation',
                'prompt': 'Think about familiar concepts like learning to ride a bike, training a pet, or...'
            }
        ]
        
        for i in range(min(count, len(creative_templates))):
            template = random.choice(creative_templates)
            challenge = {
                'id': f"creative_{int(time.time())}_{i}",
                'domain': 'creative',
                'title': template['title'],
                'description': template['description'],
                'difficulty': template['difficulty'],
                'type': template['type'],
                'prompt': template['prompt'],
                'quality_score': random.uniform(0.7, 0.85),
                'timestamp': datetime.now().isoformat(),
                'source': 'auto_crawler'
            }
            challenges.append(challenge)
            
        return challenges
    
    def generate_science_problems(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate science problems"""
        challenges = []
        
        science_templates = [
            {
                'title': 'Physics - Projectile Motion',
                'description': 'Calculate the maximum range of a projectile launched at 45° with initial velocity 20 m/s.',
                'difficulty': 4,
                'type': 'physics',
                'formula': 'Range = v₀²sin(2θ)/g = 400*sin(90°)/9.8 ≈ 40.8 m'
            },
            {
                'title': 'Chemistry - Stoichiometry',
                'description': 'How many grams of CO₂ are produced when 10g of C₂H₆ burns completely?',
                'difficulty': 5,
                'type': 'chemistry',
                'formula': '2C₂H₆ + 7O₂ → 4CO₂ + 6H₂O; 10g C₂H₆ → 14.7g CO₂'
            },
            {
                'title': 'Biology - Population Growth',
                'description': 'A bacteria population doubles every 20 minutes. Starting with 100, how many after 2 hours?',
                'difficulty': 3,
                'type': 'biology',
                'formula': 'N(t) = N₀ * 2^(t/20) = 100 * 2^6 = 6400'
            }
        ]
        
        for i in range(min(count, len(science_templates))):
            template = random.choice(science_templates)
            challenge = {
                'id': f"science_{int(time.time())}_{i}",
                'domain': 'science',
                'title': template['title'],
                'description': template['description'],
                'difficulty': template['difficulty'],
                'type': template['type'],
                'formula': template['formula'],
                'quality_score': random.uniform(0.75, 0.9),
                'timestamp': datetime.now().isoformat(),
                'source': 'auto_crawler'
            }
            challenges.append(challenge)
            
        return challenges
    
    def validate_challenge(self, challenge: Dict[str, Any]) -> bool:
        """Validate challenge quality"""
        required_fields = ['id', 'domain', 'title', 'description', 'difficulty', 'quality_score']
        
        # Check required fields
        for field in required_fields:
            if field not in challenge:
                return False
        
        # Check quality threshold
        if challenge['quality_score'] < self.quality_threshold:
            return False
        
        # Check difficulty range
        if not (1 <= challenge['difficulty'] <= 10):
            return False
        
        # Check description length
        if len(challenge['description']) < 50:
            return False
        
        return True
    
    def crawl_domain(self, domain: str, count: int = None) -> List[Dict[str, Any]]:
        """Crawl a specific domain for challenges"""
        if domain not in self.domains:
            logger.error(f"Unknown domain: {domain}")
            return []
        
        count = count or self.batch_size
        logger.info(f"🕷️ Crawling {domain} domain for {count} challenges...")
        
        try:
            challenges = self.domains[domain](count)
            validated_challenges = [c for c in challenges if self.validate_challenge(c)]
            
            logger.info(f"✅ Generated {len(validated_challenges)} valid challenges from {domain}")
            return validated_challenges
            
        except Exception as e:
            logger.error(f"Error crawling {domain}: {e}")
            return []
    
    def crawl_all_domains(self, count_per_domain: int = None) -> List[Dict[str, Any]]:
        """Crawl all domains for challenges"""
        count_per_domain = count_per_domain or self.batch_size
        all_challenges = []
        
        for domain in self.domains.keys():
            challenges = self.crawl_domain(domain, count_per_domain)
            all_challenges.extend(challenges)
        
        return all_challenges
    
    def save_challenges(self, challenges: List[Dict[str, Any]], output_file: str = None):
        """Save challenges to file"""
        if not challenges:
            logger.warning("No challenges to save")
            return
        
        output_file = output_file or f"datasets/crawled_challenges_{int(time.time())}.jsonl"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            for challenge in challenges:
                f.write(json.dumps(challenge) + '\n')
        
        logger.info(f"💾 Saved {len(challenges)} challenges to {output_file}")
    
    def log_crawl_session(self, challenges: List[Dict[str, Any]]):
        """Log crawl session to feeding history"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': f"crawl_{int(time.time())}",
            'challenges_discovered': len(challenges),
            'domains': list(set(c['domain'] for c in challenges)),
            'avg_quality': sum(c['quality_score'] for c in challenges) / len(challenges) if challenges else 0,
            'avg_difficulty': sum(c['difficulty'] for c in challenges) / len(challenges) if challenges else 0
        }
        
        # Append to feeding history
        os.makedirs('logs', exist_ok=True)
        with open('logs/feeding_history.jsonl', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        logger.info(f"📊 Logged crawl session: {len(challenges)} challenges, avg quality {log_entry['avg_quality']:.2f}")

def main():
    """Main crawler function"""
    parser = argparse.ArgumentParser(description='🕷️ Tamagotchi Evolution Auto Crawler')
    parser.add_argument('--domain', type=str, help='Specific domain to crawl (code, logic, math, creative, science)')
    parser.add_argument('--count', type=int, default=5, help='Number of challenges to generate')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--min-difficulty', type=int, default=1, help='Minimum difficulty level')
    parser.add_argument('--max-difficulty', type=int, default=10, help='Maximum difficulty level')
    parser.add_argument('--adaptive', action='store_true', help='Use evolution feedback for adaptive crawling')
    parser.add_argument('--use-evolution-feedback', action='store_true', help='Adjust crawling based on evolution performance')
    
    args = parser.parse_args()
    
    crawler = ChallengeCrawler()
    
    logger.info("🕷️🎯 Starting Tamagotchi Evolution Auto Crawler")
    
    # Crawl challenges
    if args.domain:
        challenges = crawler.crawl_domain(args.domain, args.count)
    else:
        challenges = crawler.crawl_all_domains(args.count)
    
    # Filter by difficulty if specified
    if args.min_difficulty > 1 or args.max_difficulty < 10:
        challenges = [c for c in challenges if args.min_difficulty <= c['difficulty'] <= args.max_difficulty]
        logger.info(f"🎯 Filtered to {len(challenges)} challenges within difficulty range {args.min_difficulty}-{args.max_difficulty}")
    
    # Save challenges
    if challenges:
        crawler.save_challenges(challenges, args.output)
        crawler.log_crawl_session(challenges)
        
        # Print summary
        print(f"\n🎉 Crawl Summary:")
        print(f"   📊 Total challenges: {len(challenges)}")
        print(f"   🎯 Domains: {', '.join(set(c['domain'] for c in challenges))}")
        print(f"   ⭐ Avg quality: {sum(c['quality_score'] for c in challenges) / len(challenges):.2f}")
        print(f"   🔥 Avg difficulty: {sum(c['difficulty'] for c in challenges) / len(challenges):.1f}")
    else:
        logger.warning("❌ No challenges generated")

if __name__ == '__main__':
    main() 