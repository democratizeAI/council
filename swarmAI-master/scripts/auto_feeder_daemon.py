#!/usr/bin/env python3
"""
🍽️🎯 Emotional Tamagotchi Evolution - Auto Feeder Daemon
Processes discovered challenges and feeds them to the training system
"""

import os
import json
import time
import yaml
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoFeeder:
    """Auto-feeder daemon for processing and queuing challenges"""
    
    def __init__(self):
        self.enabled = os.getenv('FEEDER_ENABLED', 'true').lower() == 'true'
        self.interval_minutes = int(os.getenv('FEEDER_INTERVAL_MINUTES', '360'))  # 6 hours
        self.min_queue_size = int(os.getenv('FEEDER_MIN_QUEUE_SIZE', '5'))
        self.max_queue_size = int(os.getenv('FEEDER_MAX_QUEUE_SIZE', '50'))
        self.priority_domains = os.getenv('FEEDER_PRIORITY_DOMAINS', 'logic,math').split(',')
        self.adaptive_difficulty = os.getenv('FEEDER_ADAPTIVE_DIFFICULTY', 'true').lower() == 'true'
        self.batch_size = int(os.getenv('FEEDER_BATCH_SIZE', '10'))
        
        # Directories
        self.datasets_dir = 'datasets'
        self.queue_dir = 'jobs/queue'
        self.completed_dir = 'jobs/completed'
        self.logs_dir = 'logs'
        
        # Create directories if they don't exist
        for directory in [self.datasets_dir, self.queue_dir, self.completed_dir, self.logs_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            queue_files = os.listdir(self.queue_dir)
            completed_files = os.listdir(self.completed_dir)
            
            return {
                'queue_count': len(queue_files),
                'completed_count': len(completed_files),
                'queue_files': queue_files,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {'queue_count': 0, 'completed_count': 0, 'queue_files': [], 'last_updated': None}
    
    def find_challenge_files(self) -> List[str]:
        """Find available challenge files to process"""
        challenge_files = []
        
        if not os.path.exists(self.datasets_dir):
            return challenge_files
        
        for filename in os.listdir(self.datasets_dir):
            if filename.endswith('.jsonl') and ('crawled' in filename or 'challenges' in filename):
                file_path = os.path.join(self.datasets_dir, filename)
                challenge_files.append(file_path)
        
        # Sort by modification time, newest first
        challenge_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return challenge_files
    
    def load_challenges_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load challenges from a JSONL file"""
        challenges = []
        
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        challenge = json.loads(line.strip())
                        challenges.append(challenge)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on line {line_num} in {file_path}: {e}")
                        continue
            
            logger.info(f"📁 Loaded {len(challenges)} challenges from {file_path}")
            return challenges
            
        except Exception as e:
            logger.error(f"Error loading challenges from {file_path}: {e}")
            return []
    
    def validate_challenge(self, challenge: Dict[str, Any]) -> bool:
        """Validate challenge before feeding"""
        required_fields = ['id', 'domain', 'title', 'description', 'difficulty']
        
        # Check required fields
        for field in required_fields:
            if field not in challenge:
                logger.warning(f"Challenge missing required field: {field}")
                return False
        
        # Check difficulty range
        if not (1 <= challenge.get('difficulty', 0) <= 10):
            logger.warning(f"Challenge difficulty out of range: {challenge.get('difficulty')}")
            return False
        
        # Check description length
        if len(challenge.get('description', '')) < 20:
            logger.warning(f"Challenge description too short: {len(challenge.get('description', ''))}")
            return False
        
        return True
    
    def prioritize_challenges(self, challenges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize challenges based on domain and quality"""
        def priority_score(challenge):
            score = 0
            
            # Domain priority
            if challenge.get('domain') in self.priority_domains:
                score += 10
            
            # Quality score
            score += challenge.get('quality_score', 0.5) * 5
            
            # Difficulty balance (prefer medium difficulty)
            difficulty = challenge.get('difficulty', 5)
            if 4 <= difficulty <= 6:
                score += 3
            elif 3 <= difficulty <= 7:
                score += 1
            
            # Recency (newer challenges get slight boost)
            timestamp = challenge.get('timestamp')
            if timestamp:
                try:
                    challenge_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hours_old = (datetime.now() - challenge_time.replace(tzinfo=None)).total_seconds() / 3600
                    if hours_old < 24:
                        score += 2
                    elif hours_old < 72:
                        score += 1
                except:
                    pass
            
            return score
        
        # Sort by priority score, highest first
        prioritized = sorted(challenges, key=priority_score, reverse=True)
        logger.info(f"🎯 Prioritized {len(prioritized)} challenges")
        return prioritized
    
    def create_training_job(self, challenge: Dict[str, Any]) -> str:
        """Create a training job YAML file for a challenge"""
        job_id = f"{challenge['domain']}_{challenge['id']}_{int(time.time())}"
        
        job_config = {
            'job_id': job_id,
            'type': 'challenge_training',
            'domain': challenge['domain'],
            'challenge_id': challenge['id'],
            'created': datetime.now().isoformat(),
            'priority': 'high' if challenge.get('domain') in self.priority_domains else 'normal',
            'config': {
                'challenge_title': challenge['title'],
                'challenge_description': challenge['description'],
                'difficulty': challenge['difficulty'],
                'quality_score': challenge.get('quality_score', 0.7),
                'training_params': {
                    'learning_rate': 1e-4,
                    'batch_size': 4,
                    'max_steps': 100,
                    'warmup_steps': 10,
                    'save_steps': 50
                }
            },
            'challenge_data': challenge
        }
        
        # Adjust training parameters based on difficulty
        difficulty = challenge['difficulty']
        if difficulty >= 7:
            job_config['config']['training_params']['max_steps'] = 200
            job_config['config']['training_params']['learning_rate'] = 5e-5
        elif difficulty <= 3:
            job_config['config']['training_params']['max_steps'] = 50
            job_config['config']['training_params']['learning_rate'] = 2e-4
        
        job_file = os.path.join(self.queue_dir, f"{job_id}.yaml")
        
        try:
            with open(job_file, 'w') as f:
                yaml.dump(job_config, f, default_flow_style=False)
            
            logger.info(f"📝 Created training job: {job_file}")
            return job_file
            
        except Exception as e:
            logger.error(f"Error creating training job: {e}")
            return None
    
    def feed_challenges(self, challenges: List[Dict[str, Any]], max_count: int = None) -> int:
        """Feed challenges to the training queue"""
        if not challenges:
            logger.info("No challenges to feed")
            return 0
        
        max_count = max_count or self.batch_size
        queue_status = self.get_queue_status()
        
        # Check if queue is full
        if queue_status['queue_count'] >= self.max_queue_size:
            logger.warning(f"Queue is full ({queue_status['queue_count']}/{self.max_queue_size}), skipping feeding")
            return 0
        
        # Calculate how many we can add
        available_slots = self.max_queue_size - queue_status['queue_count']
        feed_count = min(max_count, available_slots, len(challenges))
        
        fed_count = 0
        for i in range(feed_count):
            challenge = challenges[i]
            
            if self.validate_challenge(challenge):
                job_file = self.create_training_job(challenge)
                if job_file:
                    fed_count += 1
                else:
                    logger.warning(f"Failed to create job for challenge: {challenge.get('id')}")
            else:
                logger.warning(f"Invalid challenge skipped: {challenge.get('id')}")
        
        logger.info(f"🍽️ Fed {fed_count} challenges to training queue")
        return fed_count
    
    def process_challenge_files(self) -> int:
        """Process all available challenge files"""
        challenge_files = self.find_challenge_files()
        
        if not challenge_files:
            logger.info("No challenge files found to process")
            return 0
        
        all_challenges = []
        processed_files = []
        
        for file_path in challenge_files:
            challenges = self.load_challenges_from_file(file_path)
            if challenges:
                all_challenges.extend(challenges)
                processed_files.append(file_path)
        
        if not all_challenges:
            logger.info("No valid challenges found in files")
            return 0
        
        # Remove duplicates based on challenge ID
        seen_ids = set()
        unique_challenges = []
        for challenge in all_challenges:
            challenge_id = challenge.get('id')
            if challenge_id and challenge_id not in seen_ids:
                seen_ids.add(challenge_id)
                unique_challenges.append(challenge)
        
        logger.info(f"📊 Found {len(unique_challenges)} unique challenges from {len(processed_files)} files")
        
        # Prioritize challenges
        prioritized_challenges = self.prioritize_challenges(unique_challenges)
        
        # Feed challenges
        fed_count = self.feed_challenges(prioritized_challenges)
        
        # Log feeding session
        self.log_feeding_session(fed_count, len(unique_challenges), processed_files)
        
        # Archive processed files
        self.archive_processed_files(processed_files)
        
        return fed_count
    
    def log_feeding_session(self, fed_count: int, total_challenges: int, processed_files: List[str]):
        """Log feeding session details"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': f"feed_{int(time.time())}",
            'challenges_fed': fed_count,
            'total_challenges_available': total_challenges,
            'processed_files': [os.path.basename(f) for f in processed_files],
            'queue_status': self.get_queue_status()
        }
        
        log_file = os.path.join(self.logs_dir, 'feeding_history.jsonl')
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        logger.info(f"📊 Logged feeding session: {fed_count} challenges fed")
    
    def archive_processed_files(self, processed_files: List[str]):
        """Archive processed challenge files"""
        archive_dir = os.path.join(self.datasets_dir, 'processed')
        os.makedirs(archive_dir, exist_ok=True)
        
        for file_path in processed_files:
            try:
                filename = os.path.basename(file_path)
                archive_path = os.path.join(archive_dir, f"processed_{int(time.time())}_{filename}")
                shutil.move(file_path, archive_path)
                logger.info(f"📦 Archived {filename} to {archive_path}")
            except Exception as e:
                logger.error(f"Error archiving {file_path}: {e}")
    
    def check_queue_health(self) -> bool:
        """Check if queue needs feeding"""
        queue_status = self.get_queue_status()
        
        if queue_status['queue_count'] < self.min_queue_size:
            logger.info(f"Queue below minimum size ({queue_status['queue_count']}/{self.min_queue_size}), feeding needed")
            return False
        
        logger.info(f"Queue healthy ({queue_status['queue_count']} jobs)")
        return True
    
    def run_feeding_cycle(self) -> Dict[str, Any]:
        """Run a complete feeding cycle"""
        if not self.enabled:
            logger.info("Auto-feeder is disabled")
            return {'status': 'disabled', 'fed_count': 0}
        
        logger.info("🍽️ Starting feeding cycle...")
        
        start_time = time.time()
        fed_count = self.process_challenge_files()
        duration = time.time() - start_time
        
        result = {
            'status': 'completed',
            'fed_count': fed_count,
            'duration_seconds': round(duration, 2),
            'timestamp': datetime.now().isoformat(),
            'queue_status': self.get_queue_status()
        }
        
        logger.info(f"✅ Feeding cycle completed: {fed_count} challenges fed in {duration:.2f}s")
        return result
    
    def daemon_loop(self):
        """Main daemon loop"""
        logger.info(f"🍽️🎯 Starting Auto-Feeder Daemon (interval: {self.interval_minutes} minutes)")
        
        while True:
            try:
                # Check if feeding is needed
                if not self.check_queue_health():
                    self.run_feeding_cycle()
                else:
                    logger.info("Queue is healthy, skipping feeding cycle")
                
                # Sleep until next cycle
                sleep_seconds = self.interval_minutes * 60
                logger.info(f"😴 Sleeping for {self.interval_minutes} minutes...")
                time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                logger.info("🛑 Auto-feeder daemon stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                time.sleep(60)  # Sleep 1 minute on error

def main():
    """Main feeder function"""
    parser = argparse.ArgumentParser(description='🍽️ Tamagotchi Evolution Auto Feeder')
    parser.add_argument('--status', action='store_true', help='Show feeder status')
    parser.add_argument('--feed-now', action='store_true', help='Force immediate feeding')
    parser.add_argument('--feed-file', type=str, help='Feed specific challenge file')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--check-queue', action='store_true', help='Check queue health')
    
    args = parser.parse_args()
    
    feeder = AutoFeeder()
    
    if args.status:
        # Show status
        queue_status = feeder.get_queue_status()
        print(f"\n🍽️ Auto-Feeder Status:")
        print(f"   ⚡ Enabled: {feeder.enabled}")
        print(f"   ⏰ Interval: {feeder.interval_minutes} minutes")
        print(f"   📊 Queue: {queue_status['queue_count']} jobs")
        print(f"   ✅ Completed: {queue_status['completed_count']} jobs")
        print(f"   🎯 Min queue size: {feeder.min_queue_size}")
        print(f"   📈 Max queue size: {feeder.max_queue_size}")
        print(f"   🔥 Priority domains: {', '.join(feeder.priority_domains)}")
        
    elif args.feed_now:
        # Force immediate feeding
        result = feeder.run_feeding_cycle()
        print(f"\n🍽️ Feeding Result:")
        print(f"   📊 Status: {result['status']}")
        print(f"   🎯 Challenges fed: {result['fed_count']}")
        print(f"   ⏱️ Duration: {result['duration_seconds']}s")
        
    elif args.feed_file:
        # Feed specific file
        if os.path.exists(args.feed_file):
            challenges = feeder.load_challenges_from_file(args.feed_file)
            if challenges:
                prioritized = feeder.prioritize_challenges(challenges)
                fed_count = feeder.feed_challenges(prioritized)
                print(f"🍽️ Fed {fed_count} challenges from {args.feed_file}")
            else:
                print(f"❌ No valid challenges found in {args.feed_file}")
        else:
            print(f"❌ File not found: {args.feed_file}")
            
    elif args.check_queue:
        # Check queue health
        healthy = feeder.check_queue_health()
        status = "healthy" if healthy else "needs feeding"
        print(f"🏥 Queue status: {status}")
        
    elif args.daemon:
        # Run as daemon
        feeder.daemon_loop()
        
    else:
        # Default: run single feeding cycle
        result = feeder.run_feeding_cycle()
        print(f"🍽️ Fed {result['fed_count']} challenges")

if __name__ == '__main__':
    main() 