#!/usr/bin/env python3
"""
🏋️‍♂️🎯 Emotional Tamagotchi Evolution - Trainer Worker
Processes training jobs from the queue and creates LoRA adapters
"""

import os
import json
import yaml
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, TaskType
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainerWorker:
    """Training worker for processing challenge-based training jobs"""
    
    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"worker_{int(time.time())}"
        self.model_name = os.getenv('BASE_MODEL', 'microsoft/DialoGPT-medium')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Directories
        self.queue_dir = 'jobs/queue'
        self.completed_dir = 'jobs/completed'
        self.failed_dir = 'jobs/failed'
        self.lora_dir = 'lora_adapters'
        self.logs_dir = 'logs'
        
        # Create directories
        for directory in [self.completed_dir, self.failed_dir, self.lora_dir, self.logs_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Training configuration
        self.max_length = int(os.getenv('MAX_LENGTH', '512'))
        self.default_batch_size = int(os.getenv('BATCH_SIZE', '4'))
        self.default_learning_rate = float(os.getenv('LEARNING_RATE', '1e-4'))
        
        # LoRA configuration
        self.lora_r = int(os.getenv('LORA_R', '16'))
        self.lora_alpha = int(os.getenv('LORA_ALPHA', '32'))
        self.lora_dropout = float(os.getenv('LORA_DROPOUT', '0.1'))
        
        # Model and tokenizer (loaded lazily)
        self.model = None
        self.tokenizer = None
        
    def load_model(self):
        """Load the base model and tokenizer"""
        if self.model is None:
            logger.info(f"🤖 Loading model: {self.model_name}")
            
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device.type == 'cuda' else torch.float32,
                    device_map='auto' if self.device.type == 'cuda' else None
                )
                
                logger.info(f"✅ Model loaded on {self.device}")
                
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                raise
    
    def find_next_job(self) -> Optional[str]:
        """Find the next job to process"""
        if not os.path.exists(self.queue_dir):
            return None
        
        job_files = [f for f in os.listdir(self.queue_dir) if f.endswith('.yaml')]
        
        if not job_files:
            return None
        
        # Sort by creation time (oldest first)
        job_files.sort(key=lambda x: os.path.getctime(os.path.join(self.queue_dir, x)))
        
        return os.path.join(self.queue_dir, job_files[0])
    
    def load_job(self, job_file: str) -> Optional[Dict[str, Any]]:
        """Load job configuration from YAML file"""
        try:
            with open(job_file, 'r') as f:
                job_config = yaml.safe_load(f)
            
            logger.info(f"📋 Loaded job: {job_config.get('job_id', 'unknown')}")
            return job_config
            
        except Exception as e:
            logger.error(f"Error loading job {job_file}: {e}")
            return None
    
    def prepare_training_data(self, challenge: Dict[str, Any]) -> str:
        """Prepare training prompt from challenge data"""
        domain = challenge.get('domain', 'general')
        title = challenge.get('title', 'Challenge')
        description = challenge.get('description', '')
        difficulty = challenge.get('difficulty', 5)
        
        # Create a training prompt based on the challenge
        if domain == 'code':
            prompt = f"""### Coding Challenge: {title}
**Difficulty:** {difficulty}/10
**Description:** {description}

**Solution:**
```python
{challenge.get('solution_template', '# Your solution here')}
```

**Explanation:** This solution addresses the challenge by implementing the required algorithm efficiently."""
            
        elif domain == 'math':
            prompt = f"""### Mathematical Problem: {title}
**Difficulty:** {difficulty}/10
**Problem:** {description}

**Solution:**
{challenge.get('formula', 'Mathematical solution steps here')}

**Explanation:** This solution uses mathematical principles to solve the problem systematically."""
            
        elif domain == 'logic':
            prompt = f"""### Logic Puzzle: {title}
**Difficulty:** {difficulty}/10
**Puzzle:** {description}

**Solution:**
{challenge.get('answer', 'Logical reasoning and answer here')}

**Explanation:** This solution applies logical reasoning to reach the correct conclusion."""
            
        elif domain == 'creative':
            prompt = f"""### Creative Challenge: {title}
**Difficulty:** {difficulty}/10
**Task:** {description}

**Response:**
{challenge.get('prompt', 'Creative response here')}

**Explanation:** This response demonstrates creativity while addressing the challenge requirements."""
            
        elif domain == 'science':
            prompt = f"""### Science Problem: {title}
**Difficulty:** {difficulty}/10
**Problem:** {description}

**Solution:**
{challenge.get('formula', 'Scientific solution and calculations here')}

**Explanation:** This solution applies scientific principles and calculations to solve the problem."""
            
        else:
            prompt = f"""### Challenge: {title}
**Difficulty:** {difficulty}/10
**Description:** {description}

**Response:**
This challenge requires careful analysis and systematic problem-solving approach.

**Explanation:** The solution demonstrates understanding of the core concepts involved."""
        
        return prompt
    
    def create_lora_model(self, base_model, job_config: Dict[str, Any]):
        """Create LoRA adapter for the base model"""
        training_params = job_config.get('config', {}).get('training_params', {})
        
        # LoRA configuration
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.lora_r,
            lora_alpha=self.lora_alpha,
            lora_dropout=self.lora_dropout,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],  # Common attention modules
            bias="none"
        )
        
        try:
            peft_model = get_peft_model(base_model, lora_config)
            logger.info(f"🔧 Created LoRA adapter with r={self.lora_r}, alpha={self.lora_alpha}")
            return peft_model
            
        except Exception as e:
            logger.error(f"Error creating LoRA model: {e}")
            # Fallback: try with different target modules
            try:
                lora_config.target_modules = ["c_attn", "c_proj"]  # GPT-style modules
                peft_model = get_peft_model(base_model, lora_config)
                logger.info(f"🔧 Created LoRA adapter with fallback modules")
                return peft_model
            except Exception as e2:
                logger.error(f"Error with fallback LoRA config: {e2}")
                raise
    
    def train_on_challenge(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Train the model on a specific challenge"""
        challenge = job_config.get('challenge_data', {})
        training_params = job_config.get('config', {}).get('training_params', {})
        
        # Prepare training data
        training_prompt = self.prepare_training_data(challenge)
        
        # Tokenize the prompt
        inputs = self.tokenizer(
            training_prompt,
            return_tensors="pt",
            max_length=self.max_length,
            truncation=True,
            padding=True
        )
        
        if self.device.type == 'cuda':
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Create LoRA model
        peft_model = self.create_lora_model(self.model, job_config)
        peft_model.train()
        
        # Training parameters
        learning_rate = training_params.get('learning_rate', self.default_learning_rate)
        max_steps = training_params.get('max_steps', 100)
        batch_size = training_params.get('batch_size', self.default_batch_size)
        
        # Simple training loop (for demonstration)
        optimizer = torch.optim.AdamW(peft_model.parameters(), lr=learning_rate)
        
        total_loss = 0.0
        step_losses = []
        
        logger.info(f"🏋️‍♂️ Starting training: {max_steps} steps, lr={learning_rate}")
        
        for step in range(max_steps):
            optimizer.zero_grad()
            
            # Forward pass
            outputs = peft_model(**inputs, labels=inputs['input_ids'])
            loss = outputs.loss
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            step_loss = loss.item()
            total_loss += step_loss
            step_losses.append(step_loss)
            
            if step % 10 == 0:
                logger.info(f"Step {step}/{max_steps}, Loss: {step_loss:.4f}")
        
        avg_loss = total_loss / max_steps
        logger.info(f"✅ Training completed. Average loss: {avg_loss:.4f}")
        
        # Save the LoRA adapter
        adapter_name = f"{challenge.get('domain', 'general')}_{challenge.get('id', 'unknown')}_{int(time.time())}"
        adapter_path = os.path.join(self.lora_dir, adapter_name)
        
        try:
            peft_model.save_pretrained(adapter_path)
            logger.info(f"💾 Saved LoRA adapter: {adapter_path}")
            
            # Save training metadata
            metadata = {
                'adapter_name': adapter_name,
                'adapter_path': adapter_path,
                'challenge_id': challenge.get('id'),
                'domain': challenge.get('domain'),
                'difficulty': challenge.get('difficulty'),
                'training_steps': max_steps,
                'final_loss': avg_loss,
                'learning_rate': learning_rate,
                'created': datetime.now().isoformat(),
                'worker_id': self.worker_id
            }
            
            metadata_file = os.path.join(adapter_path, 'training_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                'status': 'success',
                'adapter_name': adapter_name,
                'adapter_path': adapter_path,
                'final_loss': avg_loss,
                'training_steps': max_steps,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error saving adapter: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'final_loss': avg_loss,
                'training_steps': max_steps
            }
    
    def process_job(self, job_file: str) -> Dict[str, Any]:
        """Process a single training job"""
        job_config = self.load_job(job_file)
        if not job_config:
            return {'status': 'error', 'error': 'Failed to load job config'}
        
        job_id = job_config.get('job_id', 'unknown')
        logger.info(f"🎯 Processing job: {job_id}")
        
        start_time = time.time()
        
        try:
            # Ensure model is loaded
            self.load_model()
            
            # Train on the challenge
            result = self.train_on_challenge(job_config)
            
            duration = time.time() - start_time
            result['duration_seconds'] = round(duration, 2)
            result['job_id'] = job_id
            result['worker_id'] = self.worker_id
            result['completed_at'] = datetime.now().isoformat()
            
            # Move job file to completed directory
            completed_file = os.path.join(self.completed_dir, os.path.basename(job_file))
            shutil.move(job_file, completed_file)
            
            # Log the result
            self.log_training_result(result)
            
            logger.info(f"✅ Job {job_id} completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            
            # Move job file to failed directory
            failed_file = os.path.join(self.failed_dir, os.path.basename(job_file))
            shutil.move(job_file, failed_file)
            
            error_result = {
                'status': 'error',
                'error': str(e),
                'job_id': job_id,
                'worker_id': self.worker_id,
                'failed_at': datetime.now().isoformat(),
                'duration_seconds': round(time.time() - start_time, 2)
            }
            
            self.log_training_result(error_result)
            return error_result
    
    def log_training_result(self, result: Dict[str, Any]):
        """Log training result to performance history"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'worker_id': self.worker_id,
            'job_id': result.get('job_id'),
            'status': result.get('status'),
            'duration_seconds': result.get('duration_seconds'),
            'final_loss': result.get('final_loss'),
            'adapter_name': result.get('adapter_name'),
            'error': result.get('error')
        }
        
        log_file = os.path.join(self.logs_dir, 'training_history.jsonl')
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Also append to performance history for monitoring
        performance_file = 'performance_history.jsonl'
        with open(performance_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def worker_loop(self, max_jobs: int = None):
        """Main worker loop"""
        logger.info(f"🏋️‍♂️ Starting trainer worker: {self.worker_id}")
        
        jobs_processed = 0
        
        while True:
            try:
                # Find next job
                job_file = self.find_next_job()
                
                if not job_file:
                    logger.info("No jobs in queue, waiting...")
                    time.sleep(30)  # Wait 30 seconds before checking again
                    continue
                
                # Process the job
                result = self.process_job(job_file)
                jobs_processed += 1
                
                logger.info(f"📊 Jobs processed: {jobs_processed}")
                
                # Check if we've reached the maximum number of jobs
                if max_jobs and jobs_processed >= max_jobs:
                    logger.info(f"Reached maximum jobs limit ({max_jobs}), stopping")
                    break
                
                # Brief pause between jobs
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("🛑 Worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(60)  # Wait 1 minute on error

def main():
    """Main trainer worker function"""
    parser = argparse.ArgumentParser(description='🏋️‍♂️ Tamagotchi Evolution Trainer Worker')
    parser.add_argument('--worker-id', type=str, help='Worker ID')
    parser.add_argument('--max-jobs', type=int, help='Maximum number of jobs to process')
    parser.add_argument('--single-job', type=str, help='Process a single job file')
    parser.add_argument('--status', action='store_true', help='Show worker status')
    
    args = parser.parse_args()
    
    worker = TrainerWorker(worker_id=args.worker_id)
    
    if args.status:
        # Show status
        queue_count = len(os.listdir(worker.queue_dir)) if os.path.exists(worker.queue_dir) else 0
        completed_count = len(os.listdir(worker.completed_dir)) if os.path.exists(worker.completed_dir) else 0
        failed_count = len(os.listdir(worker.failed_dir)) if os.path.exists(worker.failed_dir) else 0
        
        print(f"\n🏋️‍♂️ Trainer Worker Status:")
        print(f"   🆔 Worker ID: {worker.worker_id}")
        print(f"   🤖 Model: {worker.model_name}")
        print(f"   💻 Device: {worker.device}")
        print(f"   📊 Queue: {queue_count} jobs")
        print(f"   ✅ Completed: {completed_count} jobs")
        print(f"   ❌ Failed: {failed_count} jobs")
        
    elif args.single_job:
        # Process single job
        if os.path.exists(args.single_job):
            result = worker.process_job(args.single_job)
            print(f"🏋️‍♂️ Job result: {result['status']}")
            if result['status'] == 'success':
                print(f"   📦 Adapter: {result['adapter_name']}")
                print(f"   📉 Final loss: {result['final_loss']:.4f}")
            else:
                print(f"   ❌ Error: {result['error']}")
        else:
            print(f"❌ Job file not found: {args.single_job}")
            
    else:
        # Run worker loop
        worker.worker_loop(max_jobs=args.max_jobs)

if __name__ == '__main__':
    main() 