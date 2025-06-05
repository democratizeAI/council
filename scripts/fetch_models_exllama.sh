#!/usr/bin/env bash
# Week 2-1: Fetch TinyLlama Q4_K_M for ExLlama V2
set -e

echo "🚀 Week 2-1: Fetching TinyLlama Q4_K_M for ExLlama V2..."

# Create models directory
mkdir -p /models/tinyllama
cd /models/tinyllama

echo "⏬ Downloading TinyLlama-1B-Chat-Q4_K_M.gguf (1.1 GB)..."
curl -L -o TinyLlama-1B-chat-q4_k_m.gguf \
  https://huggingface.co/TheBloke/TinyLlama-1B-Chat-GGUF/resolve/main/TinyLlama-1B-Chat-q4_K_M.gguf

# Verify download
if [ -f "TinyLlama-1B-chat-q4_k_m.gguf" ]; then
    SIZE=$(stat -c%s "TinyLlama-1B-chat-q4_k_m.gguf" 2>/dev/null || stat -f%z "TinyLlama-1B-chat-q4_k_m.gguf" 2>/dev/null || wc -c < "TinyLlama-1B-chat-q4_k_m.gguf")
    echo "✅ Downloaded: $(($SIZE / 1024 / 1024)) MB"
    
    # Calculate SHA256 for CI verification
    if command -v sha256sum >/dev/null 2>&1; then
        CHECKSUM=$(sha256sum TinyLlama-1B-chat-q4_k_m.gguf | cut -d' ' -f1)
        echo "🔍 SHA256: ${CHECKSUM:0:8}..."
    elif command -v shasum >/dev/null 2>&1; then
        CHECKSUM=$(shasum -a 256 TinyLlama-1B-chat-q4_k_m.gguf | cut -d' ' -f1)
        echo "🔍 SHA256: ${CHECKSUM:0:8}..."
    fi
    
    echo "✅ TinyLlama Q4_K_M ready for ExLlama V2!"
else
    echo "❌ Download failed"
    exit 1
fi 