import json

# Prometheus up metrics data
data = '''{"status":"success","data":{"resultType":"vector","result":[{"metric":{"__name__":"up","instance":"council-api:9000","job":"council-api"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"pushgateway:9091","job":"pushgateway"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"alertmanager:9093","job":"alertmanager"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"redis-exporter:9121","job":"redis-exporter"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"localhost:9090","job":"prometheus"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"grafana:3000","job":"grafana"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"lb-traefik:8080","job":"traefik"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"council-api-canary:8001","job":"api-canary"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9090","job":"localhost-reliable"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"localhost:8080","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9091","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:3000","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9093","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9121","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9000","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9205","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9203","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9204","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9202","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"localhost:9201","job":"localhost-reliable"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"static-web:80","job":"static-web-health"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"phi3-vllm:9102","job":"working-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"blackbox-exporter:9115","job":"working-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"llm-svc-cpu:8007","job":"working-containers"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"lab-node_exporter-1:9100","job":"node-exporter"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"tiny-svc:8005","job":"working-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"metrics-mock-3:8080","job":"working-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"council-api-canary:8001","job":"direct-containers"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"alertmanager:9093","job":"direct-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"metrics-mock-5:8080","job":"working-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"grafana:3000","job":"direct-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"traefik-lb:8080","job":"direct-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"council-api:9000","job":"direct-containers"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"metrics-mock-1:8080","job":"working-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"lab-node_exporter-1:9100","job":"direct-containers"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"metrics-mock-4:8080","job":"working-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"metrics-mock-2:8080","job":"working-containers"},"value":[1749625383.905,"1"]},{"metric":{"__name__":"up","instance":"council-redis:6379","job":"direct-containers"},"value":[1749625383.905,"0"]},{"metric":{"__name__":"up","instance":"redis-exporter:9121","job":"direct-containers"},"value":[1749625383.905,"1"]}]}}'''

result = json.loads(data)
up_count = sum(1 for r in result['data']['result'] if r['value'][1] == '1')
down_count = sum(1 for r in result['data']['result'] if r['value'][1] == '0')
total = len(result['data']['result'])

print(f'OPS Board Status: {up_count}/{total} targets UP ({down_count} DOWN)')
print(f'Status: {"🟢 GREEN" if up_count >= 20 else "🟡 YELLOW"}')
print()

print('=== DOWN TARGETS (BLOCKING IDR-01) ===')
for r in result['data']['result']:
    if r['value'][1] == '0':
        instance = r['metric']['instance']
        job = r['metric']['job']
        print(f'❌ {instance} ({job})')

print()
print('=== CRITICAL BLOCKERS ===')
critical_targets = []
for r in result['data']['result']:
    if r['value'][1] == '0':
        instance = r['metric']['instance']
        job = r['metric']['job']
        # Identify critical services for Agent-0 API
        if 'localhost:8000' in instance or 'council-api' in instance or 'localhost:9000' in instance:
            critical_targets.append(f'{instance} ({job})')

if critical_targets:
    print('🚨 Agent-0 API related targets DOWN:')
    for target in critical_targets:
        print(f'   • {target}')
else:
    print('✅ No obvious Agent-0 API targets found in DOWN list')
    print('🔍 Need to add Agent-0 API (localhost:8000) to Prometheus scrape config') 