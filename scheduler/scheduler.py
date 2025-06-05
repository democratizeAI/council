from apscheduler.schedulers.blocking import BlockingScheduler
import httpx, datetime, os, json, pathlib, logging, sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

API = os.getenv("SWARM_API", "http://api:9000")
DEST_QUEUE = pathlib.Path("/app/tasks/lora_queue.json")

def crawl_and_enqueue():
    """Fetch hard prompts and enqueue LoRA training job"""
    try:
        logging.info("🌙 Starting nightly LoRA job creation...")
        
        # Ensure tasks directory exists
        DEST_QUEUE.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to fetch hard prompts from API
        try:
            logging.info(f"📡 Fetching hard prompts from {API}/hard_prompts")
            response = httpx.get(f"{API}/hard_prompts", timeout=30)
            if response.status_code == 200:
                prompts = response.json()
                logging.info(f"✅ Fetched {len(prompts)} hard prompts from API")
            else:
                logging.warning(f"⚠️ API returned {response.status_code}, using fallback prompts")
                prompts = get_fallback_prompts()
        except Exception as e:
            logging.warning(f"⚠️ Failed to fetch from API: {e}, using fallback prompts")
            prompts = get_fallback_prompts()
        
        # Create job
        job_name = f"night_{datetime.date.today().strftime('%Y%m%d')}"
        job = {
            "name": job_name,
            "dataset": prompts,
            "created_at": datetime.datetime.now().isoformat(),
            "type": "nightly_lora"
        }
        
        # Write to queue
        DEST_QUEUE.write_text(json.dumps([job], indent=2))
        logging.info(f"✅ Enqueued LoRA job: {job['name']} with {len(prompts)} prompts")
        
        # Log job details
        logging.info(f"📋 Job details:")
        logging.info(f"   - Name: {job['name']}")
        logging.info(f"   - Dataset size: {len(prompts)}")
        logging.info(f"   - Created: {job['created_at']}")
        logging.info(f"   - Queue file: {DEST_QUEUE}")
        
    except Exception as e:
        logging.error(f"❌ Failed to create nightly job: {str(e)}")

def get_fallback_prompts():
    """Fallback prompts when API is unavailable"""
    return [
        "Explain quantum computing in simple terms",
        "What are the implications of artificial general intelligence?",
        "How do neural networks learn?",
        "Describe the future of renewable energy",
        "What is the relationship between consciousness and computation?",
        "Analyze the economic impact of automation",
        "How does blockchain technology work?",
        "What are the ethical considerations in AI development?",
        "Explain the concept of emergence in complex systems",
        "Describe the potential of quantum machine learning"
    ]

def test_scheduler():
    """Test function that runs immediately for demo purposes"""
    logging.info("🧪 Running test job creation...")
    crawl_and_enqueue()

def main():
    logging.info("⏰ Scheduler starting...")
    logging.info(f"🎯 API endpoint: {API}")
    logging.info(f"📁 Queue destination: {DEST_QUEUE}")
    
    # Check if we're in test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("🧪 Running in test mode - creating job immediately")
        test_scheduler()
        return
    
    # Create scheduler
    sched = BlockingScheduler(timezone="UTC")
    
    # Add nightly job at 2:15 AM UTC
    sched.add_job(
        crawl_and_enqueue, 
        "cron", 
        hour=2, 
        minute=15,
        id='nightly_lora_job'
    )
    
    # For demo: also add a job every 2 minutes
    sched.add_job(
        crawl_and_enqueue,
        "interval",
        minutes=2,
        id='demo_frequent_job'
    )
    
    logging.info("📅 Scheduled jobs:")
    logging.info("   - Nightly LoRA: 02:15 UTC daily")
    logging.info("   - Demo: Every 2 minutes")
    
    try:
        logging.info("🚀 Scheduler started, waiting for scheduled jobs...")
        sched.start()
    except KeyboardInterrupt:
        logging.info("⏹️ Scheduler stopped by user")
    except Exception as e:
        logging.error(f"💥 Scheduler error: {str(e)}")

if __name__ == "__main__":
    main() 