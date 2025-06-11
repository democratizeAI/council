import json

# Read current metrics
with open('current_metrics.json') as f:
    data = json.load(f)

up_count = sum(1 for r in data['data']['result'] if r['value'][1] == '1')
down_count = sum(1 for r in data['data']['result'] if r['value'][1] == '0')
total = len(data['data']['result'])

print(f'Current OPS Board: {up_count}/{total} targets UP ({down_count} DOWN)')
print(f'Need: {20 - up_count} more UP targets to reach 20/39 for IDR-01 merge')
print()

# Check if Agent-0 API is in targets
agent_targets = [r for r in data['data']['result'] if 'host.docker.internal:8000' in r['metric'].get('instance', '')]
print(f'Agent-0 API targets found: {len(agent_targets)}')

if len(agent_targets) == 0:
    print('❌ Agent-0 API not being scraped by Prometheus yet')
    print('💡 Solutions:')
    print('   1. Wait for Prometheus to discover the new target (can take 1-2 minutes)')
    print('   2. Or fix one of the DOWN targets to reach 20/39')
else:
    for target in agent_targets:
        status = "UP" if target['value'][1] == '1' else "DOWN"
        print(f'   • {target["metric"]["instance"]} ({target["metric"]["job"]}): {status}')

print()
print('=== EASIEST TARGETS TO FIX ===')
print('These are localhost targets that should be UP:')

easy_fixes = []
for r in data['data']['result']:
    if r['value'][1] == '0':
        instance = r['metric']['instance']
        job = r['metric']['job']
        
        # Find targets that are probably misconfigured or just need a service restart
        if ('localhost' in instance and 'reliable' in job) or 'static-web' in instance:
            easy_fixes.append((instance, job))

for instance, job in easy_fixes[:3]:  # Show top 3 easiest fixes
    print(f'🔧 {instance} ({job}) - probably just needs service restart or config fix')

print()
if up_count >= 20:
    print('🟢 IDR-01 MERGE GATE: OPEN! ✅')
    print('   Can proceed with PR builder/IDR-01-intent-agent merge')
else:
    print('🟡 IDR-01 MERGE GATE: BLOCKED ❌')
    print(f'   Need {20 - up_count} more UP targets to proceed') 