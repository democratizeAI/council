#!/usr/bin/env python3
"""
Merge multiple preference JSONL files into a single training dataset.
Normalizes schema, deduplicates, and shuffles for LoRA training.
"""

import json
import argparse
import random
from pathlib import Path
from typing import List, Dict, Set

def load_jsonl(filepath: str) -> List[Dict]:
    """Load JSONL file and return list of records."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data

def normalize_record(record: Dict) -> Dict:
    """Normalize record to standard schema: {prompt, chosen, rejected}."""
    # Handle different possible schemas
    if all(k in record for k in ['prompt', 'chosen', 'rejected']):
        return {
            'prompt': record['prompt'].strip(),
            'chosen': record['chosen'].strip(),
            'rejected': record['rejected'].strip()
        }
    elif all(k in record for k in ['prompt', 'response_a', 'response_b', 'winner']):
        # Convert A/B testing format
        if record['winner'] == 'A':
            chosen, rejected = record['response_a'], record['response_b']
        else:
            chosen, rejected = record['response_b'], record['response_a']
        return {
            'prompt': record['prompt'].strip(),
            'chosen': chosen.strip(),
            'rejected': rejected.strip()
        }
    else:
        raise ValueError(f"Unknown record schema: {record.keys()}")

def deduplicate(records: List[Dict]) -> List[Dict]:
    """Remove duplicate prompt-response pairs."""
    seen: Set[str] = set()
    unique_records = []
    
    for record in records:
        # Create hash of prompt + chosen + rejected
        key = f"{record['prompt']}||{record['chosen']}||{record['rejected']}"
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
    
    return unique_records

def main():
    parser = argparse.ArgumentParser(description='Merge preference datasets')
    parser.add_argument('input_files', nargs='+', help='Input JSONL files')
    parser.add_argument('--out', required=True, help='Output file path')
    parser.add_argument('--shuffle', action='store_true', default=True, 
                       help='Shuffle the merged dataset')
    
    args = parser.parse_args()
    
    all_records = []
    
    # Load and normalize all input files
    for input_file in args.input_files:
        print(f"Loading {input_file}...")
        records = load_jsonl(input_file)
        normalized = [normalize_record(r) for r in records]
        all_records.extend(normalized)
        print(f"  Loaded {len(records)} records")
    
    print(f"Total records before deduplication: {len(all_records)}")
    
    # Deduplicate
    all_records = deduplicate(all_records)
    print(f"Total records after deduplication: {len(all_records)}")
    
    # Shuffle if requested
    if args.shuffle:
        random.shuffle(all_records)
        print("Dataset shuffled for training")
    
    # Write output
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"Merged dataset saved to {args.out}")
    print(f"Final count: {len(all_records)} preference pairs")

if __name__ == '__main__':
    main() 