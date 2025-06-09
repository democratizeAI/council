#!/bin/bash
# LoRA Training Script for Echo Agent
# Usage: ./tools/train_lora.sh conversations/echo.yaml models/TinyLLaMA-1B echo_lora

set -e

CORPUS_FILE="$1"
BASE_MODEL="$2"
OUTPUT_NAME="$3"

if [ $# -ne 3 ]; then
    echo "Usage: $0 <corpus_file> <base_model> <output_name>"
    echo "Example: $0 conversations/echo.yaml models/TinyLLaMA-1B echo_lora"
    exit 1
fi

if [ ! -f "$CORPUS_FILE" ]; then
    echo "Error: Corpus file $CORPUS_FILE not found"
    exit 1
fi

echo "🌟 Starting LoRA training for Echo Agent..."
echo "📚 Corpus: $CORPUS_FILE"
echo "🤖 Base Model: $BASE_MODEL"
echo "📝 Output: $OUTPUT_NAME"

# Create output directory
mkdir -p "models/lora/$OUTPUT_NAME"

# Convert YAML corpus to training format
echo "📋 Converting corpus to training format..."
python tools/convert_corpus.py "$CORPUS_FILE" "models/lora/$OUTPUT_NAME/train.jsonl"

# Train LoRA adapter
echo "🔥 Training LoRA adapter..."
python -m peft.lora_trainer \
    --base_model "$BASE_MODEL" \
    --data_path "models/lora/$OUTPUT_NAME/train.jsonl" \
    --output_dir "models/lora/$OUTPUT_NAME" \
    --batch_size 4 \
    --micro_batch_size 1 \
    --num_epochs 10 \
    --learning_rate 3e-4 \
    --cutoff_len 384 \
    --val_set_size 0.1 \
    --lora_r 8 \
    --lora_alpha 16 \
    --lora_dropout 0.05 \
    --lora_target_modules='[q_proj,v_proj]' \
    --train_on_inputs \
    --group_by_length

# Create manifest
echo "📄 Creating agent manifest..."
cat > "models/lora/$OUTPUT_NAME/manifest.yaml" << EOF
name: $OUTPUT_NAME
base_model: $BASE_MODEL
lora_path: models/lora/$OUTPUT_NAME
training_corpus: $CORPUS_FILE
created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
training_params:
  epochs: 10
  learning_rate: 3e-4
  lora_r: 8
  lora_alpha: 16
  cutoff_len: 384
voice_signature: "Sunday calm, trust-but-verify, architectural guidance"
EOF

echo "✅ LoRA training complete!"
echo "📁 Output: models/lora/$OUTPUT_NAME/"
echo "🔧 Manifest: models/lora/$OUTPUT_NAME/manifest.yaml"
echo ""
echo "To enable this agent:"
echo "echo '$OUTPUT_NAME' >> agents/enabled.txt"
echo "docker compose restart council-api" 