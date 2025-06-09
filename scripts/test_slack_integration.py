#!/usr/bin/env python3
"""
Slack Integration Test - Verify webhooks and signature validation
Tests the Trinity Council Slack integration pipeline
"""

import os
import time
import hashlib
import hmac
import requests
import json
from urllib.parse import urlencode

def test_signature_validation():
    """Test Slack signature validation against local API"""
    
    # Load secrets from environment
    signing_secret = os.getenv('SLACK_SIGNING_SECRET')
    if not signing_secret:
        print("❌ SLACK_SIGNING_SECRET not found in environment")
        return False
    
    # Test payload
    timestamp = str(int(time.time()))
    body = 'token=fake&command=/status&text=ping'
    
    # Generate signature
    sig_basestring = f'v0:{timestamp}:{body}'
    computed_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"🔍 Testing signature validation...")
    print(f"Timestamp: {timestamp}")
    print(f"Body: {body}")
    print(f"Signature: {computed_signature}")
    
    # Test against local API (adjust URL as needed)
    api_url = os.getenv('SLACK_API_URL', 'http://localhost:9000')
    
    try:
        response = requests.post(
            f"{api_url}/slack/commands",
            data=body,
            headers={
                'X-Slack-Request-Timestamp': timestamp,
                'X-Slack-Signature': computed_signature,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=5
        )
        
        print(f"✅ Response status: {response.status_code}")
        print(f"Response body: {response.text[:200]}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Signature test failed: {e}")
        return False

def test_webhook_endpoints():
    """Test webhook endpoints for alerts and patches"""
    
    webhooks = {
        'alerts': os.getenv('SLACK_WEBHOOK_ALERTS'),
        'patches': os.getenv('SLACK_WEBHOOK_PATCHES'),
        'installs': os.getenv('SLACK_WEBHOOK_INSTALLS'),
        'incoming': os.getenv('SLACK_WEBHOOK_INCOMING')
    }
    
    results = {}
    
    for name, webhook_url in webhooks.items():
        if not webhook_url:
            print(f"⚠️ {name.upper()} webhook URL not configured")
            results[name] = False
            continue
            
        # Test message
        test_payload = {
            "text": f"🧪 Test message from Trinity Council ({name})",
            "username": "Trinity-CI-Test",
            "icon_emoji": ":robot_face:"
        }
        
        try:
            response = requests.post(
                webhook_url,
                json=test_payload,
                timeout=5
            )
            
            success = response.status_code == 200
            print(f"{'✅' if success else '❌'} {name} webhook: {response.status_code}")
            results[name] = success
            
        except Exception as e:
            print(f"❌ {name} webhook failed: {e}")
            results[name] = False
    
    return results

def main():
    """Run complete Slack integration test suite"""
    print("🧪 Trinity Council Slack Integration Test")
    print("=" * 50)
    
    # Check environment
    print("\n🔍 Environment Check:")
    required_vars = [
        'SLACK_SIGNING_SECRET',
        'SLACK_BOT_TOKEN', 
        'SLACK_WEBHOOK_ALERTS',
        'SLACK_WEBHOOK_PATCHES'
    ]
    
    env_ok = True
    for var in required_vars:
        value = os.getenv(var)
        status = "✅" if value else "❌"
        print(f"{status} {var}: {'configured' if value else 'missing'}")
        if not value:
            env_ok = False
    
    if not env_ok:
        print("\n💡 Load environment: source .env.swarm or docker-compose up")
        return False
    
    # Test signature validation
    print("\n🔐 Signature Validation Test:")
    sig_ok = test_signature_validation()
    
    # Test webhooks
    print("\n📡 Webhook Tests:")
    webhook_results = test_webhook_endpoints()
    
    # Summary
    print("\n📊 Test Results:")
    print(f"Environment: {'✅' if env_ok else '❌'}")
    print(f"Signature: {'✅' if sig_ok else '❌'}")
    
    webhook_ok = all(webhook_results.values())
    print(f"Webhooks: {'✅' if webhook_ok else '❌'}")
    
    overall_success = env_ok and sig_ok and webhook_ok
    print(f"\n🎯 Overall: {'✅ PASS' if overall_success else '❌ FAIL'}")
    
    if overall_success:
        print("🚀 Slack integration ready for production!")
    else:
        print("🔧 Fix issues above before deploying")
    
    return overall_success

if __name__ == "__main__":
    main() 