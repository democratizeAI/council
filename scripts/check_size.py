#!/usr/bin/env python3
"""
Token Size Check Script

Validates that prompt files stay under the specified token limit using tiktoken.
Usage: python scripts/check_size.py <file_path> <token_limit>
"""

import sys
import tiktoken
import pathlib

def check_token_size(file_path, token_limit):
    """Check if file content exceeds token limit"""
    try:
        # Load the tiktoken encoder (OpenAI's tokenizer)
        enc = tiktoken.get_encoding("cl100k_base")
        
        # Read the file content
        text = pathlib.Path(file_path).read_text(encoding='utf-8')
        
        # Encode to tokens and count
        tokens = len(enc.encode(text))
        
        # Check against limit
        if tokens > token_limit:
            print(f"❌ FAIL: {tokens} tokens > {token_limit} limit")
            sys.exit(1)
        else:
            print(f"✅ OK – {tokens:,} tokens (limit: {token_limit:,})")
            return tokens
            
    except FileNotFoundError:
        print(f"❌ ERROR: File not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/check_size.py <file_path> <token_limit>")
        print("Example: python scripts/check_size.py o3_context.md 32000")
        sys.exit(1)
    
    file_path = sys.argv[1]
    token_limit = int(sys.argv[2])
    
    check_token_size(file_path, token_limit) 