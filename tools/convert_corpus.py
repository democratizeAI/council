#!/usr/bin/env python3
"""
Corpus Converter - YAML to LoRA Training Format
Converts conversation YAML files into JSONL format suitable for LoRA training.
"""

import sys
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any

def load_yaml_corpus(file_path: str) -> List[Dict[str, Any]]:
    """Load conversation data from YAML file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, list):
        raise ValueError("YAML corpus must be a list of conversation entries")
    
    return data

def convert_to_training_format(conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert conversations to LoRA training format"""
    training_data = []
    
    # Process conversations sequentially to maintain flow
    for i in range(len(conversations) - 1):
        current = conversations[i]
        next_msg = conversations[i + 1]
        
        # Look for architect/user -> assistant pairs
        if (current.get('role') in ['architect', 'user'] and 
            next_msg.get('role') == 'assistant'):
            
            training_example = {
                "instruction": current.get('text', '').strip(),
                "input": "",  # No additional input context
                "output": next_msg.get('text', '').strip(),
                "date": str(current.get('date', 'unknown')),
                "voice_style": "sunday_calm"
            }
            
            # Only include if both parts have content
            if training_example["instruction"] and training_example["output"]:
                training_data.append(training_example)
    
    return training_data

def save_jsonl(data: List[Dict[str, Any]], output_path: str):
    """Save training data as JSONL file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def main():
    if len(sys.argv) != 3:
        print("Usage: python convert_corpus.py <input_yaml> <output_jsonl>")
        print("Example: python convert_corpus.py conversations/echo.yaml models/lora/echo_lora/train.jsonl")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"📚 Loading corpus from {input_file}...")
    conversations = load_yaml_corpus(input_file)
    
    print(f"🔄 Converting {len(conversations)} conversation entries...")
    training_data = convert_to_training_format(conversations)
    
    # Create output directory if it doesn't exist
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    print(f"💾 Saving {len(training_data)} training examples to {output_file}...")
    save_jsonl(training_data, output_file)
    
    print(f"✅ Conversion complete!")
    print(f"📊 Generated {len(training_data)} training examples from {len(conversations)} conversation entries")
    
    # Show sample
    if training_data:
        print(f"\n📋 Sample training example:")
        sample = training_data[0]
        print(f"Instruction: {sample['instruction'][:100]}...")
        print(f"Output: {sample['output'][:100]}...")

if __name__ == "__main__":
    main() 