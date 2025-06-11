#!/usr/bin/env python3
"""
Socket Mode Handler for Trinity-CommLink
Handles all Slack interactions via WebSocket connection
"""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import httpx
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack Bolt app
app = App(token=os.environ["SLACK_BOT_TOKEN_RO"])

# Configuration
COUNCIL_API_URL = os.getenv("COUNCIL_API_URL", "http://localhost:9010")

@app.command("/phi3")
def handle_phi3(ack, say, command):
    """Handle /phi3 slash command"""
    ack()  # Acknowledge immediately
    
    text = command.get('text', 'ping')
    user = command.get('user_name', 'unknown')
    
    logger.info(f"/phi3 command from {user}: {text}")
    
    try:
        # Forward to Council API
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{COUNCIL_API_URL}/orchestrate",
                json={
                    "prompt": f"/phi3 {text}",
                    "temperature": 0.7,
                    "max_tokens": 512
                },
                headers={"X-Agent": "router"}
            )
            
            if response.status_code == 200:
                result = response.json()
                say(f"🤖 Phi-3 Router ▸ {result.get('response', 'Processing...')}")
            else:
                say(f"⚠️ Service error ({response.status_code})")
                
    except Exception as e:
        logger.error(f"Phi-3 command error: {e}")
        say("⚠️ Internal error - check logs")

@app.command("/o3")
def handle_o3(ack, say, command):
    """Handle /o3 slash command"""
    ack()
    
    text = command.get('text', 'ping')
    user = command.get('user_name', 'unknown')
    
    logger.info(f"/o3 command from {user}: {text}")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{COUNCIL_API_URL}/orchestrate",
                json={
                    "prompt": f"/o3 {text}",
                    "temperature": 0.3,
                    "max_tokens": 512
                },
                headers={"X-Agent": "o3"}
            )
            
            if response.status_code == 200:
                result = response.json()
                say(f"🧠 O3 Model ▸ {result.get('response', 'Processing...')}")
            else:
                say(f"⚠️ Service error ({response.status_code})")
                
    except Exception as e:
        logger.error(f"O3 command error: {e}")
        say("⚠️ Internal error - check logs")

@app.command("/opus")
def handle_opus(ack, say, command):
    """Handle /opus slash command"""
    ack()
    
    text = command.get('text', 'ping')
    user = command.get('user_name', 'unknown')
    
    logger.info(f"/opus command from {user}: {text}")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{COUNCIL_API_URL}/orchestrate",
                json={
                    "prompt": f"/opus {text}",
                    "temperature": 0.7,
                    "max_tokens": 1024
                },
                headers={"X-Agent": "opus"}
            )
            
            if response.status_code == 200:
                result = response.json()
                say(f"🎭 Claude Opus ▸ {result.get('response', 'Processing...')}")
            else:
                say(f"⚠️ Service error ({response.status_code})")
                
    except Exception as e:
        logger.error(f"Opus command error: {e}")
        say("⚠️ Internal error - check logs")

@app.command("/commlink")
def handle_commlink(ack, say, command):
    """Handle /commlink slash command"""
    ack()
    
    text = command.get('text', 'status')
    user = command.get('user_name', 'unknown')
    
    logger.info(f"/commlink command from {user}: {text}")
    
    if text in ['status', 'ping']:
        say("✅ CommLink Specialist online – drift & press alerts active")
    else:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{COUNCIL_API_URL}/orchestrate",
                    json={
                        "prompt": f"/commlink {text}",
                        "temperature": 0.5,
                        "max_tokens": 512
                    },
                    headers={"X-Agent": "router"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    say(f"📡 CommLink ▸ {result.get('response', 'Processing...')}")
                else:
                    say(f"⚠️ Service error ({response.status_code})")
                    
        except Exception as e:
            logger.error(f"CommLink command error: {e}")
            say("⚠️ Internal error - check logs")

@app.event("app_home_opened")
def handle_home(event, say):
    """Handle App-Home events"""
    user_id = event.get("user")
    logger.info(f"App-Home opened by user: {user_id}")
    # Add App-Home logic here if needed

@app.event("app_mention")
def handle_mention(event, say):
    """Handle @mentions"""
    text = event.get("text", "")
    user = event.get("user", "unknown")
    
    logger.info(f"Mentioned by {user}: {text}")
    say("👋 Hi! Use slash commands like `/phi3`, `/o3`, `/opus`, or `/commlink` to interact with me!")

if __name__ == "__main__":
    logger.info("Starting Trinity Socket Mode Handler...")
    
    # Verify required environment variables
    required_vars = ["SLACK_BOT_TOKEN_RO", "SLACK_APP_TOKEN"]
    for var in required_vars:
        if not os.environ.get(var):
            logger.error(f"Missing required environment variable: {var}")
            exit(1)
    
    # Start Socket Mode handler
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    
    logger.info("Trinity Socket Mode ready - slash commands active!")
    handler.start() 