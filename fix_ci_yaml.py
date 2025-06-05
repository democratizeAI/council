#!/usr/bin/env python3
"""
Quick fix for ci.yaml YAML syntax error
"""

def fix_ci_yaml():
    with open('.github/workflows/ci.yaml', 'r') as f:
        content = f.read()
    
    # Fix the specific indentation issue
    content = content.replace(
        "        sleep 15  # Wait for full startup\n        \n        - name: Canary 100 QPS and check metrics\n      run: |",
        "        sleep 15  # Wait for full startup\n        \n    - name: Canary 100 QPS and check metrics\n      run: |"
    )
    
    with open('.github/workflows/ci.yaml', 'w') as f:
        f.write(content)
    
    print("✅ Fixed ci.yaml indentation issue")

if __name__ == '__main__':
    fix_ci_yaml() 