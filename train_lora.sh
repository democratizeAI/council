#!/bin/bash
# QLoRA Training Pipeline - Phase 3 Self-Improvement
# ==================================================
#
# Nightly fine-tuning script that:
# 1. Processes harvested failure data
# 2. Runs QLoRA fine-tuning on local models
# 3. Saves adapter to loras/latest/
# 4. Validates adapter quality
# 5. Triggers automatic deployment

set -euo pipefail

# Configuration
TRAINING_DATA_DIR="training_data"
LORA_OUTPUT_DIR="loras/latest"
BASE_MODEL_PATH="models/mistral-7b-instruct"  # Adjust to your local model
BATCH_SIZE=4
GRADIENT_ACCUMULATION=8
LEARNING_RATE=5e-5
NUM_EPOCHS=3
LORA_RANK=16
LORA_ALPHA=32
MAX_SEQ_LENGTH=2048

# Logging
LOG_FILE="logs/training_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

echo "🧠 QLoRA Training Pipeline Starting..." | tee -a "$LOG_FILE"
echo "===============================================" | tee -a "$LOG_FILE"
echo "📅 Timestamp: $(date)" | tee -a "$LOG_FILE"
echo "📂 Training data: $TRAINING_DATA_DIR" | tee -a "$LOG_FILE"
echo "🎯 Output: $LORA_OUTPUT_DIR" | tee -a "$LOG_FILE"

# Check for training data
LATEST_HARVEST=$(find "$TRAINING_DATA_DIR" -name "harvest_*.jsonl" -type f -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2- 2>/dev/null || echo "")

if [[ -z "$LATEST_HARVEST" ]]; then
    echo "⚠️ No training data found. Run harvest_failures.py first." | tee -a "$LOG_FILE"
    exit 1
fi

echo "📊 Using training data: $LATEST_HARVEST" | tee -a "$LOG_FILE"

# Count training examples
TRAINING_COUNT=$(wc -l < "$LATEST_HARVEST")
echo "📈 Training examples: $TRAINING_COUNT" | tee -a "$LOG_FILE"

if [[ $TRAINING_COUNT -lt 10 ]]; then
    echo "⚠️ Too few training examples ($TRAINING_COUNT < 10). Skipping training." | tee -a "$LOG_FILE"
    exit 0
fi

# Backup previous LoRA if exists
if [[ -d "$LORA_OUTPUT_DIR" ]]; then
    BACKUP_DIR="loras/backup_$(date +%Y%m%d_%H%M%S)"
    echo "💾 Backing up previous LoRA: $LORA_OUTPUT_DIR -> $BACKUP_DIR" | tee -a "$LOG_FILE"
    mv "$LORA_OUTPUT_DIR" "$BACKUP_DIR"
fi

mkdir -p "$LORA_OUTPUT_DIR"

# Create training configuration
cat > "$LORA_OUTPUT_DIR/training_config.json" << EOF
{
    "base_model": "$BASE_MODEL_PATH",
    "training_data": "$LATEST_HARVEST",
    "output_dir": "$LORA_OUTPUT_DIR",
    "batch_size": $BATCH_SIZE,
    "gradient_accumulation_steps": $GRADIENT_ACCUMULATION,
    "learning_rate": $LEARNING_RATE,
    "num_epochs": $NUM_EPOCHS,
    "lora_rank": $LORA_RANK,
    "lora_alpha": $LORA_ALPHA,
    "max_seq_length": $MAX_SEQ_LENGTH,
    "training_timestamp": "$(date -Iseconds)",
    "training_examples": $TRAINING_COUNT
}
EOF

echo "⚙️ Training configuration saved" | tee -a "$LOG_FILE"

# Start training (using Unsloth for efficient QLoRA)
echo "🚀 Starting QLoRA training..." | tee -a "$LOG_FILE"

python3 -c "
import json
import os
import sys
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_training_data(file_path):
    '''Load JSONL training data'''
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            example = json.loads(line.strip())
            # Format for instruction tuning
            formatted_text = f\"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['output']}\"
            data.append({'text': formatted_text})
    return Dataset.from_list(data)

def setup_lora_model(model_name, lora_rank=16, lora_alpha=32):
    '''Setup model with LoRA configuration'''
    
    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map='auto',
        trust_remote_code=True
    )
    
    # LoRA configuration
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=0.1,
        target_modules=['q_proj', 'v_proj', 'k_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']
    )
    
    # Apply LoRA
    model = get_peft_model(model, lora_config)
    return model

def main():
    try:
        # Load configuration
        with open('$LORA_OUTPUT_DIR/training_config.json', 'r') as f:
            config = json.load(f)
        
        print(f'📊 Training {config[\"training_examples\"]} examples...')
        
        # Load tokenizer and data
        tokenizer = AutoTokenizer.from_pretrained(config['base_model'])
        tokenizer.pad_token = tokenizer.eos_token
        
        dataset = load_training_data(config['training_data'])
        print(f'📈 Loaded {len(dataset)} training examples')
        
        # Tokenize dataset
        def tokenize_function(examples):
            return tokenizer(
                examples['text'],
                truncation=True,
                padding='max_length',
                max_length=config['max_seq_length'],
                return_tensors='pt'
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        
        # Setup model with LoRA
        model = setup_lora_model(
            config['base_model'],
            lora_rank=config['lora_rank'],
            lora_alpha=config['lora_alpha']
        )
        
        print(f'🎯 LoRA model setup complete')
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=config['output_dir'],
            num_train_epochs=config['num_epochs'],
            per_device_train_batch_size=config['batch_size'],
            gradient_accumulation_steps=config['gradient_accumulation_steps'],
            learning_rate=config['learning_rate'],
            logging_steps=10,
            save_steps=100,
            save_total_limit=2,
            remove_unused_columns=False,
            dataloader_drop_last=True,
            warmup_steps=100,
            weight_decay=0.01,
            lr_scheduler_type='cosine',
            report_to=[]  # Disable wandb
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            tokenizer=tokenizer
        )
        
        # Start training
        print('🚀 Training started...')
        trainer.train()
        
        # Save the final model
        trainer.save_model()
        print(f'💾 Model saved to {config[\"output_dir\"]}')
        
        # Save training metrics
        metrics = {
            'training_completed': datetime.now().isoformat(),
            'final_loss': float(trainer.state.log_history[-1].get('train_loss', 0)),
            'total_steps': trainer.state.global_step,
            'training_examples': config['training_examples']
        }
        
        with open(f'{config[\"output_dir\"]}/training_metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print('✅ Training completed successfully!')
        return 0
        
    except Exception as e:
        print(f'❌ Training failed: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
" 2>&1 | tee -a "$LOG_FILE"

TRAINING_EXIT_CODE=${PIPESTATUS[0]}

if [[ $TRAINING_EXIT_CODE -eq 0 ]]; then
    echo "✅ QLoRA training completed successfully!" | tee -a "$LOG_FILE"
    
    # Validate the trained adapter
    echo "🔍 Validating trained adapter..." | tee -a "$LOG_FILE"
    
    if [[ -f "$LORA_OUTPUT_DIR/adapter_model.bin" && -f "$LORA_OUTPUT_DIR/adapter_config.json" ]]; then
        echo "✅ Adapter files validated" | tee -a "$LOG_FILE"
        
        # Create deployment marker
        echo "$(date -Iseconds)" > "$LORA_OUTPUT_DIR/deployment_ready.txt"
        
        # Log training summary
        echo "📋 Training Summary:" | tee -a "$LOG_FILE"
        echo "   Output: $LORA_OUTPUT_DIR" | tee -a "$LOG_FILE"
        echo "   Examples: $TRAINING_COUNT" | tee -a "$LOG_FILE"
        echo "   Status: Ready for deployment" | tee -a "$LOG_FILE"
        
        # Trigger automatic deployment (optional)
        if [[ -f "deploy_lora.sh" ]]; then
            echo "🚀 Triggering automatic deployment..." | tee -a "$LOG_FILE"
            bash deploy_lora.sh "$LORA_OUTPUT_DIR" 2>&1 | tee -a "$LOG_FILE"
        fi
        
    else
        echo "❌ Adapter validation failed - missing files" | tee -a "$LOG_FILE"
        exit 1
    fi
    
else
    echo "❌ QLoRA training failed with exit code $TRAINING_EXIT_CODE" | tee -a "$LOG_FILE"
    
    # Restore backup if available
    LATEST_BACKUP=$(find loras -name "backup_*" -type d -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2- 2>/dev/null || echo "")
    if [[ -n "$LATEST_BACKUP" ]]; then
        echo "🔄 Restoring previous LoRA from backup: $LATEST_BACKUP" | tee -a "$LOG_FILE"
        rm -rf "$LORA_OUTPUT_DIR"
        mv "$LATEST_BACKUP" "$LORA_OUTPUT_DIR"
        echo "deployment_restored_$(date -Iseconds)" > "$LORA_OUTPUT_DIR/deployment_ready.txt"
    fi
    
    exit $TRAINING_EXIT_CODE
fi

echo "🎯 QLoRA training pipeline completed" | tee -a "$LOG_FILE"
echo "📊 Check logs: $LOG_FILE" | tee -a "$LOG_FILE" 