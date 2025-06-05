#!/bin/bash
# LoRA fine-tuning script for preference model training
# Usage: bash train_lora.sh --base phi2-2.7b --data data.jsonl --output models/output

set -e

# Default values
BASE_MODEL=""
DATA_PATH=""
OUTPUT_PATH=""
LEARNING_RATE="2e-5"
BATCH_SIZE="64"
EPOCHS="2"
LORA_RANK="8"
LORA_ALPHA="8"
TARGET_MODULES="q_proj,k_proj,v_proj,o_proj"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --base)
            BASE_MODEL="$2"
            shift 2
            ;;
        --data)
            DATA_PATH="$2"
            shift 2
            ;;
        --output)
            OUTPUT_PATH="$2"
            shift 2
            ;;
        --lr)
            LEARNING_RATE="$2"
            shift 2
            ;;
        --batch)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --epochs)
            EPOCHS="$2"
            shift 2
            ;;
        --target_modules)
            TARGET_MODULES="$2"
            shift 2
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$BASE_MODEL" || -z "$DATA_PATH" || -z "$OUTPUT_PATH" ]]; then
    echo "Usage: $0 --base MODEL --data DATA.jsonl --output OUTPUT_DIR [OPTIONS]"
    echo "Required: --base, --data, --output"
    echo "Optional: --lr, --batch, --epochs, --target_modules"
    exit 1
fi

# Set environment variables for CUDA memory management
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
export HF_HOME=${HF_HOME:-/models/hf-cache}

# Convert model name to HuggingFace format
case $BASE_MODEL in
    "phi2-2.7b")
        HF_MODEL="microsoft/phi-2"
        ;;
    "mistral-7B-instruct")
        HF_MODEL="mistralai/Mistral-7B-Instruct-v0.1"
        ;;
    "tinyllama-1B")
        HF_MODEL="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        ;;
    *)
        HF_MODEL="$BASE_MODEL"  # Assume it's already HF format
        ;;
esac

echo "🔥 Starting LoRA fine-tuning..."
echo "  Base model: $HF_MODEL"
echo "  Data: $DATA_PATH"
echo "  Output: $OUTPUT_PATH"
echo "  Learning rate: $LEARNING_RATE"
echo "  Batch size: $BATCH_SIZE"
echo "  Epochs: $EPOCHS"
echo "  LoRA rank: $LORA_RANK"

# Create output directory
mkdir -p "$OUTPUT_PATH"

# Create temporary training script
cat > /tmp/train_preference_lora.py << 'EOF'
import os
import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    TrainingArguments, Trainer, DataCollatorWithPadding
)
from peft import LoraConfig, get_peft_model, TaskType
import argparse

def load_preference_data(file_path):
    """Load and preprocess preference data."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            data.append(item)
    return data

def preprocess_function(examples, tokenizer):
    """Tokenize preference pairs."""
    # Format: prompt + " [SEP] " + chosen/rejected
    chosen_texts = [f"{ex['prompt']} [SEP] {ex['chosen']}" for ex in examples]
    rejected_texts = [f"{ex['prompt']} [SEP] {ex['rejected']}" for ex in examples]
    
    # Tokenize chosen (label=1) and rejected (label=0)
    chosen_tokens = tokenizer(chosen_texts, truncation=True, padding=True, max_length=512)
    rejected_tokens = tokenizer(rejected_texts, truncation=True, padding=True, max_length=512)
    
    # Combine both with labels
    all_input_ids = chosen_tokens['input_ids'] + rejected_tokens['input_ids']
    all_attention_mask = chosen_tokens['attention_mask'] + rejected_tokens['attention_mask']
    all_labels = [1] * len(chosen_tokens['input_ids']) + [0] * len(rejected_tokens['input_ids'])
    
    return {
        'input_ids': all_input_ids,
        'attention_mask': all_attention_mask,
        'labels': all_labels
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--lr', type=float, default=2e-5)
    parser.add_argument('--batch', type=int, default=64)
    parser.add_argument('--epochs', type=int, default=2)
    parser.add_argument('--lora_rank', type=int, default=8)
    parser.add_argument('--target_modules', default="q_proj,k_proj,v_proj,o_proj")
    
    args = parser.parse_args()
    
    # Load model and tokenizer
    print(f"Loading model: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=2,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    # Configure LoRA
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        inference_mode=False,
        r=args.lora_rank,
        lora_alpha=args.lora_rank,
        target_modules=args.target_modules.split(','),
        lora_dropout=0.1
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load and preprocess data
    print(f"Loading data from: {args.data}")
    raw_data = load_preference_data(args.data)
    
    # Convert to format expected by preprocess_function
    processed_data = preprocess_function(raw_data, tokenizer)
    dataset = Dataset.from_dict(processed_data)
    
    # Split train/eval (80/20)
    train_dataset = dataset.select(range(int(0.8 * len(dataset))))
    eval_dataset = dataset.select(range(int(0.8 * len(dataset)), len(dataset)))
    
    print(f"Train samples: {len(train_dataset)}")
    print(f"Eval samples: {len(eval_dataset)}")
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir=f"{args.output}/logs",
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        fp16=True,
        dataloader_drop_last=False,
        learning_rate=args.lr,
        save_total_limit=3,
    )
    
    # Data collator
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )
    
    # Train
    print("🚀 Starting training...")
    trainer.train()
    
    # Save final model
    trainer.save_model()
    tokenizer.save_pretrained(args.output)
    
    print(f"✅ Training complete! Model saved to {args.output}")

if __name__ == "__main__":
    main()
EOF

# Run the training script
python /tmp/train_preference_lora.py \
    --model "$HF_MODEL" \
    --data "$DATA_PATH" \
    --output "$OUTPUT_PATH" \
    --lr "$LEARNING_RATE" \
    --batch "$BATCH_SIZE" \
    --epochs "$EPOCHS" \
    --lora_rank "$LORA_RANK" \
    --target_modules "$TARGET_MODULES"

echo "🎉 LoRA training completed successfully!"
echo "Model artifacts saved to: $OUTPUT_PATH" 