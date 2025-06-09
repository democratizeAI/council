#!/usr/bin/env python3
import json

print("🎯 COUNCIL BARRAGE RESULTS")
print("=" * 60)

with open("council_barrage.ndjson", "r") as f:
    for i, line in enumerate(f, 1):
        record = json.loads(line)
        prompt = record["prompt"]
        latency = record["latency_s"]
        reply = record["reply"]
        
        # Extract the actual response content
        if "proposal" in reply and "summary" in reply["proposal"]:
            content = reply["proposal"]["summary"]
        elif "content" in reply:
            content = reply["content"]
        else:
            content = str(reply)[:200] + "..."
        
        print(f"PROMPT {i}: {prompt}")
        print(f"LATENCY: {latency}s")
        print(f"RESPONSE: {content[:300]}...")
        print("-" * 40) 