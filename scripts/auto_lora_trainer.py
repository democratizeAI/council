#!/usr/bin/env python3
"""
🧠 AutoGen LoRA "Tamagotchi" Trainer for Day-2 Operations
Fine-tunes each head on the day's misses; pushes new delta if val ↑ and cost < $0.20
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
import subprocess
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LoRATrainer:
    """Automated LoRA training pipeline"""
    
    def __init__(self, config_path: str = "config/lora_config.json"):
        self.config = self.load_config(config_path)
        self.training_dir = Path(self.config["training_dir"])
        self.training_dir.mkdir(parents=True, exist_ok=True)
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load training configuration"""
        default_config = {
            "budget_limit_usd": 0.20,
            "min_validation_improvement": 0.02,
            "training_dir": "training/lora_jobs",
            "models_dir": "models",
            "lora_adapters_dir": "lora_adapters",
            "base_model": "mistral-13b-gptq",
            "training_params": {
                "learning_rate": 2e-4,
                "batch_size": 4,
                "gradient_accumulation_steps": 4,
                "num_train_epochs": 3,
                "warmup_steps": 100,
                "logging_steps": 10,
                "save_steps": 500,
                "eval_steps": 250,
                "max_seq_length": 2048,
                "lora_r": 16,
                "lora_alpha": 32,
                "lora_dropout": 0.1,
                "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
            },
            "evaluation_metrics": ["accuracy", "perplexity", "loss"],
            "heads": ["math", "logic", "code", "reasoning"],
            "data_sources": {
                "misses_log": "logs/daily_misses.jsonl",
                "validation_set": "datasets/validation_holdout.json"
            }
        }
        
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            
        return default_config
    
    def collect_daily_misses(self) -> Dict[str, List[Dict[str, Any]]]:
        """Collect yesterday's misses for each head"""
        logger.info("📊 Collecting daily misses for training...")
        
        misses_by_head = {head: [] for head in self.config["heads"]}
        misses_log_path = Path(self.config["data_sources"]["misses_log"])
        
        if not misses_log_path.exists():
            logger.warning(f"⚠️ Misses log not found: {misses_log_path}")
            return misses_by_head
        
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")
        
        try:
            with open(misses_log_path, 'r') as f:
                for line in f:
                    try:
                        miss_data = json.loads(line.strip())
                        miss_date = miss_data.get("timestamp", "").split("T")[0]
                        
                        if miss_date == yesterday_str:
                            head = miss_data.get("head", "unknown")
                            if head in misses_by_head:
                                misses_by_head[head].append(miss_data)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"❌ Failed to read misses log: {e}")
        
        total_misses = sum(len(misses) for misses in misses_by_head.values())
        logger.info(f"📈 Collected {total_misses} misses across {len(self.config['heads'])} heads")
        
        for head, misses in misses_by_head.items():
            logger.info(f"  {head}: {len(misses)} misses")
        
        return misses_by_head
    
    def prepare_training_data(self, misses_by_head: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        """Prepare training datasets for each head"""
        logger.info("🔄 Preparing training datasets...")
        
        training_files = {}
        
        for head, misses in misses_by_head.items():
            if not misses:
                logger.info(f"⏭️ Skipping {head} - no misses to train on")
                continue
            
            # Create training dataset
            training_data = []
            for miss in misses:
                # Convert miss to training format
                training_example = {
                    "instruction": miss.get("query", ""),
                    "input": "",
                    "output": miss.get("expected_answer", ""),
                    "head": head,
                    "difficulty": miss.get("difficulty", "medium"),
                    "timestamp": miss.get("timestamp")
                }
                training_data.append(training_example)
            
            # Save training file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            training_file = self.training_dir / f"train_{head}_{timestamp}.json"
            
            with open(training_file, 'w') as f:
                json.dump(training_data, f, indent=2)
            
            training_files[head] = str(training_file)
            logger.info(f"💾 Prepared {len(training_data)} examples for {head} -> {training_file.name}")
        
        return training_files
    
    async def train_head(self, head: str, training_file: str) -> Optional[Dict[str, Any]]:
        """Train LoRA adapter for specific head"""
        logger.info(f"🏋️ Starting LoRA training for {head}...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.training_dir / f"lora_{head}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Training command
        cmd = [
            "python", "-m", "scripts.train_lora",
            "--model_name", self.config["base_model"],
            "--dataset", training_file,
            "--output_dir", str(output_dir),
            "--head", head,
            "--learning_rate", str(self.config["training_params"]["learning_rate"]),
            "--batch_size", str(self.config["training_params"]["batch_size"]),
            "--num_train_epochs", str(self.config["training_params"]["num_train_epochs"]),
            "--lora_r", str(self.config["training_params"]["lora_r"]),
            "--lora_alpha", str(self.config["training_params"]["lora_alpha"]),
            "--max_seq_length", str(self.config["training_params"]["max_seq_length"]),
            "--logging_steps", str(self.config["training_params"]["logging_steps"]),
            "--save_steps", str(self.config["training_params"]["save_steps"]),
            "--eval_steps", str(self.config["training_params"]["eval_steps"]),
            "--budget_limit", str(self.config["budget_limit_usd"])
        ]
        
        try:
            logger.info(f"🚀 Running training command: {' '.join(cmd)}")
            
            # Run training with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            # Wait for completion with timeout (30 minutes)
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=1800)
            except asyncio.TimeoutError:
                process.kill()
                logger.error(f"❌ Training for {head} timed out after 30 minutes")
                return None
            
            if process.returncode != 0:
                logger.error(f"❌ Training failed for {head}: {stderr.decode()}")
                return None
            
            # Parse training results
            training_log = output_dir / "training_log.json"
            if training_log.exists():
                with open(training_log, 'r') as f:
                    results = json.load(f)
                
                logger.info(f"✅ Training completed for {head}")
                logger.info(f"  Final loss: {results.get('final_loss', 'N/A')}")
                logger.info(f"  Training cost: ${results.get('cost_usd', 'N/A')}")
                logger.info(f"  Training time: {results.get('training_time_minutes', 'N/A')} min")
                
                return results
            else:
                logger.warning(f"⚠️ Training log not found for {head}")
                return {"status": "completed", "output_dir": str(output_dir)}
        
        except Exception as e:
            logger.error(f"❌ Training failed for {head}: {e}")
            return None
    
    async def evaluate_adapter(self, head: str, adapter_path: str) -> Optional[Dict[str, float]]:
        """Evaluate LoRA adapter on validation set"""
        logger.info(f"📊 Evaluating {head} adapter...")
        
        validation_file = self.config["data_sources"]["validation_set"]
        if not Path(validation_file).exists():
            logger.warning(f"⚠️ Validation set not found: {validation_file}")
            return None
        
        # Evaluation command
        cmd = [
            "python", "-m", "scripts.evaluate_lora",
            "--adapter_path", adapter_path,
            "--validation_file", validation_file,
            "--head", head,
            "--metrics", ",".join(self.config["evaluation_metrics"])
        ]
        
        try:
            logger.info(f"🧪 Running evaluation: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
            
            if process.returncode != 0:
                logger.error(f"❌ Evaluation failed for {head}: {stderr.decode()}")
                return None
            
            # Parse evaluation results
            results = json.loads(stdout.decode())
            
            logger.info(f"📈 Evaluation results for {head}:")
            for metric, value in results.items():
                logger.info(f"  {metric}: {value}")
            
            return results
        
        except Exception as e:
            logger.error(f"❌ Evaluation failed for {head}: {e}")
            return None
    
    def check_improvement(self, head: str, new_metrics: Dict[str, float]) -> bool:
        """Check if new adapter shows improvement"""
        
        # Load baseline metrics
        baseline_file = Path(f"models/baselines/{head}_baseline.json")
        if not baseline_file.exists():
            logger.info(f"📊 No baseline found for {head}, considering as improvement")
            return True
        
        try:
            with open(baseline_file, 'r') as f:
                baseline_metrics = json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Failed to load baseline for {head}: {e}")
            return True
        
        # Check primary metric improvement
        primary_metric = "accuracy"
        if primary_metric in new_metrics and primary_metric in baseline_metrics:
            improvement = new_metrics[primary_metric] - baseline_metrics[primary_metric]
            min_improvement = self.config["min_validation_improvement"]
            
            logger.info(f"📊 {head} {primary_metric}: {baseline_metrics[primary_metric]:.3f} -> {new_metrics[primary_metric]:.3f} (Δ{improvement:+.3f})")
            
            if improvement >= min_improvement:
                logger.info(f"✅ {head} shows improvement of {improvement:.3f} >= {min_improvement}")
                return True
            else:
                logger.info(f"❌ {head} improvement {improvement:.3f} < {min_improvement} threshold")
                return False
        
        logger.warning(f"⚠️ Could not compare metrics for {head}")
        return False
    
    def deploy_adapter(self, head: str, adapter_path: str, metrics: Dict[str, float]) -> bool:
        """Deploy adapter to production if it passes validation"""
        try:
            # Copy to production adapters directory
            production_dir = Path(self.config["lora_adapters_dir"])
            production_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped backup of current adapter
            current_adapter = production_dir / f"{head}_lora"
            if current_adapter.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = production_dir / f"{head}_lora_backup_{timestamp}"
                subprocess.run(["cp", "-r", str(current_adapter), str(backup_path)], check=True)
                logger.info(f"💾 Backed up current {head} adapter")
            
            # Deploy new adapter
            subprocess.run(["cp", "-r", adapter_path, str(current_adapter)], check=True)
            
            # Update baseline metrics
            baseline_file = Path(f"models/baselines/{head}_baseline.json")
            baseline_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(baseline_file, 'w') as f:
                json.dump({
                    **metrics,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "adapter_path": str(current_adapter)
                }, f, indent=2)
            
            logger.info(f"🚀 Deployed {head} adapter to production")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to deploy {head} adapter: {e}")
            return False

async def main():
    """Main training execution"""
    parser = argparse.ArgumentParser(description="AutoGen LoRA Trainer")
    parser.add_argument("--config", default="config/lora_config.json", help="Config file path")
    parser.add_argument("--budget", type=float, default=0.20, help="Budget limit in USD")
    parser.add_argument("--heads", nargs="+", help="Specific heads to train")
    parser.add_argument("--dry-run", action="store_true", help="Don't deploy, just log")
    
    args = parser.parse_args()
    
    trainer = LoRATrainer(args.config)
    
    # Override budget if specified
    if args.budget:
        trainer.config["budget_limit_usd"] = args.budget
    
    # Collect training data
    misses_by_head = trainer.collect_daily_misses()
    
    if not any(misses_by_head.values()):
        logger.info("✅ No misses found - skipping training")
        return
    
    # Prepare training datasets
    training_files = trainer.prepare_training_data(misses_by_head)
    
    if not training_files:
        logger.info("⏭️ No training data prepared - skipping training")
        return
    
    # Filter heads if specified
    if args.heads:
        training_files = {head: path for head, path in training_files.items() if head in args.heads}
    
    # Train each head
    total_cost = 0.0
    successful_deployments = 0
    
    for head, training_file in training_files.items():
        logger.info(f"🎯 Processing {head}...")
        
        # Check remaining budget
        remaining_budget = trainer.config["budget_limit_usd"] - total_cost
        if remaining_budget <= 0.01:
            logger.warning(f"💰 Budget exhausted, skipping remaining heads")
            break
        
        # Train adapter
        training_results = await trainer.train_head(head, training_file)
        if not training_results:
            logger.error(f"❌ Training failed for {head}")
            continue
        
        # Track cost
        cost = training_results.get("cost_usd", 0.0)
        total_cost += cost
        
        # Find adapter path
        adapter_path = training_results.get("adapter_path") or training_results.get("output_dir")
        if not adapter_path:
            logger.error(f"❌ No adapter path found for {head}")
            continue
        
        # Evaluate adapter
        eval_results = await trainer.evaluate_adapter(head, adapter_path)
        if not eval_results:
            logger.error(f"❌ Evaluation failed for {head}")
            continue
        
        # Check improvement
        if trainer.check_improvement(head, eval_results):
            if not args.dry_run:
                if trainer.deploy_adapter(head, adapter_path, eval_results):
                    successful_deployments += 1
                    logger.info(f"🎉 Successfully deployed {head} adapter")
                else:
                    logger.error(f"❌ Failed to deploy {head} adapter")
            else:
                logger.info(f"🔍 [DRY RUN] Would deploy {head} adapter")
                successful_deployments += 1
        else:
            logger.info(f"⏭️ Skipping deployment for {head} - insufficient improvement")
    
    logger.info(f"🏁 Training completed:")
    logger.info(f"  Total cost: ${total_cost:.3f}")
    logger.info(f"  Successful deployments: {successful_deployments}/{len(training_files)}")
    
    if successful_deployments > 0:
        logger.info("🧠 LoRA Tamagotchi training cycle completed successfully! 🎉")

if __name__ == "__main__":
    asyncio.run(main()) 