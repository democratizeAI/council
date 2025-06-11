#!/usr/bin/env python3
import os
from slack_sdk import WebClient

# Test Slack connectivity
client = WebClient(token=os.environ['SLACK_BOT_TOKEN_RO'])

try:
    result = client.chat_postMessage(
        channel='#trinity-alerts',
        text='✅ CommLink Specialist online – drift & press alerts active'
    )
    print(f"Banner sent: {result.get('ok', False)}")
    if not result.get('ok'):
        print(f"Error: {result.get('error', 'unknown')}")
except Exception as e:
    print(f"Exception: {e}") 