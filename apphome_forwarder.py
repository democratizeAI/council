#!/usr/bin/env python3
"""
CommLink App-Home Forwarder
Standalone Slack Bolt app that forwards App-Home events to CommLink
Freeze-safe: runs in separate container, no impact on core CommLink
"""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack Bolt app
app = App(token=os.environ["SLACK_BOT_TOKEN_RO"])

@app.event("app_home_opened")
def handle_home(event, say):
    """Forward App-Home events to CommLink for processing"""
    try:
        # Extract user and view data
        user_id = event.get("user")
        view_data = event.get("view", {})
        
        logger.info(f"App-Home opened by user: {user_id}")
        
        # Forward to CommLink for processing
        response = requests.post(
            "http://localhost:8088/commlink/apphome",
            json={
                "user": user_id,
                "view": view_data,
                "timestamp": event.get("event_ts"),
                "type": "app_home_opened"
            },
            timeout=5,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully forwarded App-Home event for {user_id}")
        else:
            logger.warning(f"CommLink returned status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to forward App-Home event: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in App-Home handler: {e}")

@app.event("message")
def handle_dm(event, say):
    """Forward direct messages to CommLink for context"""
    try:
        # Only process DMs (no channel)
        if event.get("channel_type") == "im":
            user_id = event.get("user")
            text = event.get("text", "")
            
            logger.info(f"DM received from user: {user_id}")
            
            # Forward to CommLink
            requests.post(
                "http://localhost:8088/commlink/dm",
                json={
                    "user": user_id,
                    "text": text,
                    "timestamp": event.get("ts"),
                    "type": "direct_message"
                },
                timeout=3
            )
            
    except Exception as e:
        logger.error(f"Error handling DM: {e}")

if __name__ == "__main__":
    logger.info("Starting CommLink App-Home Forwarder...")
    
    # Verify required environment variables
    required_vars = ["SLACK_BOT_TOKEN_RO", "SLACK_APP_TOKEN"]
    for var in required_vars:
        if not os.environ.get(var):
            logger.error(f"Missing required environment variable: {var}")
            exit(1)
    
    # Start Socket Mode handler
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    
    logger.info("App-Home Forwarder ready - listening for events...")
    handler.start() 