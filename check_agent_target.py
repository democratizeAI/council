import json

# Load Prometheus targets data
with open('targets_check.json') as f:
    data = json.load(f)

# Look for agent-0-api targets
agent_targets = [t for t in data['data']['activeTargets'] 
                if 'agent-0-api' in t.get('labels', {}).get('job', '')]

print(f"=== AGENT-0 TARGET CHECK ===")
print(f"Agent-0 targets found: {len(agent_targets)}")

for target in agent_targets:
    job = target['labels']['job']
    instance = target['labels']['instance']
    health = target['health']
    last_scrape = target.get('lastScrape', 'never')
    print(f"  Job: {job}")
    print(f"  Instance: {instance}")
    print(f"  Health: {health}")
    print(f"  Last Scrape: {last_scrape}")

# Check total UP count
total_up = sum(1 for t in data['data']['activeTargets'] if t['health'] == 'up')
total_targets = len(data['data']['activeTargets'])

print(f"\n=== OPS BOARD STATUS ===")
print(f"UP targets: {total_up}/{total_targets}")
print(f"Status: {'🟢 GREEN' if total_up >= 20 else '🟡 YELLOW'}")
print(f"Need: {max(0, 20 - total_up)} more UP targets for IDR-01")

if len(agent_targets) == 0:
    print(f"\n❌ Agent-0 API target NOT discovered yet")
    print(f"   Configuration may need adjustment")
elif agent_targets[0]['health'] != 'up':
    print(f"\n⚠️  Agent-0 API target discovered but DOWN")
    print(f"   Need to check metrics endpoint")
else:
    print(f"\n✅ Agent-0 API target UP and healthy") 