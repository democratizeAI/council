import json, time, os, subprocess, pathlib, logging, sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/swarm/trainer.log')
    ]
)

QUEUE = pathlib.Path("tasks/lora_queue.json")
BUDGET = float(os.getenv("TIER2_TRAIN_BUDGET_USD", 0.20))
LORA_OUTPUT = pathlib.Path("/data/lora/checkpoints")
MODEL_PATH = os.getenv("BASE_MODEL_PATH", "/data/faiss/base_model")

def train(job):
    """Execute LoRA training for a given job"""
    try:
        logging.info(f"🚀 Starting LoRA training for job: {job['name']}")
        
        # Ensure output directory exists
        LORA_OUTPUT.mkdir(parents=True, exist_ok=True)
        
        # Build training command
        cmd = [
            "python", "lora_train.py",
            "--data", json.dumps(job["dataset"]),
            "--budget", str(BUDGET),
            "--output", str(LORA_OUTPUT / job["name"]),
            "--base_model", MODEL_PATH,
            "--job_name", job["name"]
        ]
        
        logging.info(f"Executing: {' '.join(cmd)}")
        
        # For now, simulate training with a mock script
        # In production, this would call your actual lora_train.py
        result = simulate_lora_training(job)
        
        if result:
            logging.info(f"✅ Successfully trained {job['name']}")
            # Update metrics
            update_training_metrics(job["name"], success=True)
            return True
        else:
            logging.error(f"❌ Failed to train {job['name']}")
            update_training_metrics(job["name"], success=False)
            return False
            
    except Exception as e:
        logging.error(f"❌ Exception during training {job['name']}: {str(e)}")
        return False

def simulate_lora_training(job):
    """Simulate LoRA training process"""
    logging.info(f"📊 Simulating LoRA training for {len(job['dataset'])} samples")
    logging.info(f"💰 Budget: ${BUDGET}")
    
    # Simulate training time based on dataset size
    training_time = min(len(job['dataset']) * 2, 30)  # Max 30 seconds for demo
    
    for i in range(training_time):
        if i % 5 == 0:
            logging.info(f"📈 Training progress: {int((i/training_time)*100)}%")
        time.sleep(1)
    
    logging.info("🎯 Training completed successfully")
    
    # Create mock checkpoint
    checkpoint_dir = LORA_OUTPUT / job["name"]
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    checkpoint_info = {
        "model_name": job["name"],
        "trained_at": datetime.now().isoformat(),
        "dataset_size": len(job["dataset"]),
        "budget_used": BUDGET,
        "status": "completed"
    }
    
    (checkpoint_dir / "checkpoint_info.json").write_text(json.dumps(checkpoint_info, indent=2))
    logging.info(f"💾 Checkpoint saved to {checkpoint_dir}")
    
    return True

def update_training_metrics(job_name, success):
    """Update Prometheus metrics"""
    try:
        # In a real implementation, this would push to Pushgateway
        metrics = {
            "swarm_lora_training_total": 1,
            "swarm_lora_training_success" if success else "swarm_lora_training_failures": 1,
            "swarm_lora_reload_timestamp_seconds": time.time()
        }
        logging.info(f"📊 Updated metrics: {metrics}")
    except Exception as e:
        logging.warning(f"Failed to update metrics: {e}")

def main():
    global QUEUE
    logging.info("🧠 LoRA Trainer Worker starting...")
    logging.info(f"💰 Training budget: ${BUDGET}")
    logging.info(f"📁 Queue file: {QUEUE}")
    logging.info(f"📁 Output directory: {LORA_OUTPUT}")
    
    # Parse command line args
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        queue_file = sys.argv[2] if len(sys.argv) > 2 else "tasks/lora_queue.json"
        QUEUE = pathlib.Path(queue_file)
        logging.info(f"👀 Watching queue file: {QUEUE}")
    
    while True:
        try:
            if QUEUE.exists():
                logging.info(f"📥 Found queue file, processing jobs...")
                jobs = json.loads(QUEUE.read_text())
                
                for job in jobs:
                    logging.info(f"🔄 Processing job: {job}")
                    success = train(job)
                    if success:
                        logging.info(f"✅ Job {job['name']} completed successfully")
                    else:
                        logging.error(f"❌ Job {job['name']} failed")
                
                # Remove processed queue file
                QUEUE.unlink()
                logging.info("🗑️ Queue file processed and removed")
            else:
                logging.debug(f"⏳ No queue file found at {QUEUE}, waiting...")
            
            time.sleep(30)
            
        except Exception as e:
            logging.error(f"💥 Error in main loop: {str(e)}")
            time.sleep(30)

if __name__ == "__main__":
    main() 