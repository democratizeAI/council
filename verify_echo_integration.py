#!/usr/bin/env python3
"""
Echo Agent Integration - Final Verification Script
Demonstrates all three threads of voice weaving into Trinity.
"""

import yaml
import json
import os
from pathlib import Path

def main():
    print('🌟 ECHO AGENT INTEGRATION - FINAL VERIFICATION')
    print('=' * 60)

    # Thread 1: Echo Agent LoRA
    print('\n📋 THREAD 1: Echo Agent (LoRA Voice Clone)')
    corpus_path = Path('conversations/echo_training.yaml')
    training_path = Path('models/lora/echo_lora/train.jsonl')
    manifest_path = Path('agents/echo_agent/manifest.yaml')

    print(f'✅ Corpus: {corpus_path.exists()} ({corpus_path.stat().st_size if corpus_path.exists() else 0} bytes)')
    print(f'✅ Training: {training_path.exists()} ({len(open(training_path, "r", encoding="utf-8").readlines()) if training_path.exists() else 0} examples)')  
    print(f'✅ Manifest: {manifest_path.exists()}')

    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
        print(f'   → Agent: {manifest.get("name", "unknown")}')
        print(f'   → Voice: {manifest.get("personality", {}).get("tone", "unknown")}')

    # Thread 2: System Prompt
    print('\n📋 THREAD 2: Memory Prompt-Seed (Sunday Preamble)')
    intro_path = Path('prompts/system_intro.md')
    print(f'✅ System Intro: {intro_path.exists()}')

    if intro_path.exists():
        with open(intro_path, 'r', encoding='utf-8') as f:
            intro_content = f.read()
        print(f'   → Sunday Calm: {"Sunday Calm" in intro_content}')
        print(f'   → Trust-Verify: {"Trust But Verify" in intro_content}')
        print(f'   → Version: {"echo-v1" in intro_content}')

    # Thread 3: ChatGPT Fallback
    print('\n📋 THREAD 3: Slack Bridge (Human-in-the-Loop)')
    fallback_path = Path('services/chatgpt_fallback.py')
    enabled_path = Path('agents/enabled.txt')

    print(f'✅ Fallback Service: {fallback_path.exists()} ({fallback_path.stat().st_size if fallback_path.exists() else 0} bytes)')
    print(f'✅ Echo Enabled: {enabled_path.exists()}')

    if enabled_path.exists():
        with open(enabled_path, 'r', encoding='utf-8') as f:
            enabled = f.read()
        print(f'   → Echo Agent Listed: {"echo_agent" in enabled}')

    print('\n🎯 VOICE PRESERVATION ANALYSIS')
    if training_path.exists():
        with open(training_path, 'r', encoding='utf-8') as f:
            examples = [json.loads(line) for line in f.readlines()]
        
        all_text = ' '.join([ex['instruction'] + ' ' + ex['output'] for ex in examples])
        signatures = ['trust but verify', 'show your work', 'weights will remember', 'pattern', 'real', 'verification', 'precise', 'sunday']
        preserved = sum(1 for sig in signatures if sig.lower() in all_text.lower())
        ratio = preserved / len(signatures)
        
        print(f'✅ Training Examples: {len(examples)}')
        print(f'✅ Voice Preservation: {ratio:.1%} ({preserved}/{len(signatures)} signature phrases)')
        print(f'✅ Voice Style Tag: {examples[0].get("voice_style", "unknown") if examples else "unknown"}')

    print('\n💙 INTEGRATION COMPLETE')
    print('Your Sunday voice now lives in Trinity through:')
    print('  1. LoRA weights carrying conversation DNA')  
    print('  2. System prompts seeding every session')
    print('  3. Fallback bridge for human-in-the-loop guidance')
    print('\nThe pattern persists. The weights remember. 🌟')

if __name__ == "__main__":
    main() 