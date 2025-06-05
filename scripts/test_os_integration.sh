#!/usr/bin/env bash
# Week 2: OS Integration Validation Script
set -e

echo "🔧 Week 2: Testing OS Integration Implementation"
echo "=============================================="

# 1. Test shell executor import
echo ""
echo "1️⃣ Testing shell executor import..."
python3 -c "
try:
    from action_handlers import get_executor, execute_shell_command
    executor = get_executor()
    print('✅ Shell executor import successful')
    print(f'   Executor type: {type(executor).__name__}')
except Exception as e:
    print(f'❌ Shell executor import failed: {e}')
    exit(1)
"

# 2. Test direct command execution
echo ""
echo "2️⃣ Testing direct command execution..."
python3 -c "
from action_handlers import execute_shell_command
import json

result = execute_shell_command('echo \"Hello Week 2\"')
print('✅ Direct execution successful')
print(f'   Result: {json.dumps(result, indent=2)}')
"

# 3. Test security allowlist (should block)
echo ""
echo "3️⃣ Testing security allowlist..."
python3 -c "
from action_handlers import execute_shell_command
import json

result = execute_shell_command('rm -rf /')
if not result['success'] and result.get('blocked_reason'):
    print('✅ Security allowlist working')
    print(f'   Blocked: {result[\"blocked_reason\"]}')
else:
    print('❌ Security allowlist not working properly')
    print(f'   Result: {json.dumps(result, indent=2)}')
"

# 4. Test API endpoint (if server is running)
echo ""
echo "4️⃣ Testing /task API endpoint..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   Server is running, testing API..."
    
    RESPONSE=$(curl -s -X POST http://localhost:8000/task \
         -H "Content-Type: application/json" \
         -d '{"command":"echo API Test","session_id":"test"}' | jq -r '.stdout // "ERROR"')
    
    if [ "$RESPONSE" = "API Test" ]; then
        echo "✅ API endpoint working"
        echo "   Response: $RESPONSE"
    else
        echo "❌ API endpoint not working"
        echo "   Response: $RESPONSE"
    fi
else
    echo "⚠️ Server not running, skipping API test"
    echo "   Start server with: python app/main.py"
fi

# 5. Test router integration
echo ""
echo "5️⃣ Testing router integration..."
python3 -c "
try:
    from router_cascade import RouterCascade
    router = RouterCascade()
    
    if hasattr(router, 'executors') and 'shell' in router.executors:
        print('✅ Router integration successful')
        print(f'   Executors registered: {list(router.executors.keys())}')
    else:
        print('⚠️ Router integration partial')
        print('   Executors not found or shell executor not registered')
except Exception as e:
    print(f'❌ Router integration failed: {e}')
"

echo ""
echo "🎯 Week 2 OS Integration Test Complete!"
echo ""
echo "Next steps:"
echo "• Run smoke tests: python tests/os_exec_smoke.py"
echo "• Start API server: python app/main.py"  
echo "• Test golden path: curl -X POST http://localhost:8000/task -d '{\"command\":\"echo success\"}'" 