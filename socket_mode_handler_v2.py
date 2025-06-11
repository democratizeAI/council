#!/usr/bin/env python3
"""
Enhanced Socket Mode Handler for Trinity-CommLink
Better error handling and logging for debugging
"""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import httpx
import json
import logging
import traceback

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Slack Bolt app
app = App(token=os.environ["SLACK_BOT_TOKEN_RO"])

# Configuration
COUNCIL_API_URL = os.getenv("COUNCIL_API_URL", "http://host.docker.internal:9010")
logger.info(f"Council API URL: {COUNCIL_API_URL}")

async def call_council_api(prompt: str, agent: str = "router") -> dict:
    """Call Council API with proper error handling"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                "prompt": prompt,
                "temperature": 0.7,
                "max_tokens": 512
            }
            
            headers = {
                "X-Agent": agent,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Calling Council API: {payload} with agent {agent}")
            
            response = await client.post(
                f"{COUNCIL_API_URL}/orchestrate",
                json=payload,
                headers=headers
            )
            
            logger.info(f"Council API response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Council API result: {result}")
                return {
                    "success": True,
                    "response": result.get('response', 'No response'),
                    "model": result.get('model_used', 'unknown')
                }
            else:
                logger.error(f"Council API error {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"API error {response.status_code}"
                }
                
    except httpx.TimeoutException:
        logger.error("Council API timeout")
        return {"success": False, "error": "API timeout"}
    except Exception as e:
        logger.error(f"Council API call failed: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

@app.command("/phi3")
def handle_phi3(ack, say, command):
    """Handle /phi3 slash command"""
    logger.info(f"Received /phi3 command: {command}")
    ack()  # Acknowledge immediately
    
    text = command.get('text', 'ping')
    user = command.get('user_name', 'unknown')
    
    logger.info(f"/phi3 command from {user}: {text}")
    
    try:
        import asyncio
        result = asyncio.run(call_council_api(f"/phi3 {text}", "router"))
        
        if result["success"]:
            say(f"🤖 Phi-3 Router ▸ {result['response']}")
        else:
            say(f"⚠️ Service error: {result['error']}")
            
    except Exception as e:
        logger.error(f"Phi-3 command error: {e}")
        logger.error(traceback.format_exc())
        say("⚠️ Internal error - check logs")

@app.command("/o3")
def handle_o3(ack, say, command):
    """Handle /o3 slash command"""
    logger.info(f"Received /o3 command: {command}")
    ack()
    
    text = command.get('text', 'ping')
    user = command.get('user_name', 'unknown')
    
    logger.info(f"/o3 command from {user}: {text}")
    
    try:
        import asyncio
        result = asyncio.run(call_council_api(f"/o3 {text}", "o3"))
        
        if result["success"]:
            say(f"🧠 O3 Model ▸ {result['response']}")
        else:
            say(f"⚠️ Service error: {result['error']}")
            
    except Exception as e:
        logger.error(f"O3 command error: {e}")
        logger.error(traceback.format_exc())
        say("⚠️ Internal error - check logs")

@app.command("/opus")
def handle_opus(ack, say, command):
    """Handle /opus slash command"""
    logger.info(f"Received /opus command: {command}")
    ack()
    
    text = command.get('text', 'ping')
    user = command.get('user_name', 'unknown')
    
    logger.info(f"/opus command from {user}: {text}")
    
    try:
        import asyncio
        result = asyncio.run(call_council_api(f"/opus {text}", "opus"))
        
        if result["success"]:
            say(f"🎭 Claude Opus ▸ {result['response']}")
        else:
            say(f"⚠️ Service error: {result['error']}")
            
    except Exception as e:
        logger.error(f"Opus command error: {e}")
        logger.error(traceback.format_exc())
        say("⚠️ Internal error - check logs")

@app.command("/commlink")
def handle_commlink(ack, say, command):
    """Handle /commlink slash command"""
    logger.info(f"Received /commlink command: {command}")
    ack()
    
    text = command.get('text', 'status')
    user = command.get('user_name', 'unknown')
    
    logger.info(f"/commlink command from {user}: {text}")
    
    if text in ['status', 'ping']:
        say("✅ CommLink Specialist online – drift & press alerts active")
    else:
        try:
            import asyncio
            result = asyncio.run(call_council_api(f"/commlink {text}", "router"))
            
            if result["success"]:
                say(f"📡 CommLink ▸ {result['response']}")
            else:
                say(f"⚠️ Service error: {result['error']}")
                
        except Exception as e:
            logger.error(f"CommLink command error: {e}")
            logger.error(traceback.format_exc())
            say("⚠️ Internal error - check logs")

@app.event("app_home_opened")
def handle_home(event, say):
    """Handle App-Home events"""
    user_id = event.get("user")
    logger.info(f"App-Home opened by user: {user_id}")

@app.event("app_mention")
def handle_mention(event, say):
    """Handle @mentions"""
    text = event.get("text", "")
    user = event.get("user", "unknown")
    
    logger.info(f"Mentioned by {user}: {text}")
    say("👋 Hi! Use slash commands like `/phi3`, `/o3`, `/opus`, or `/commlink` to interact with me!")

if __name__ == "__main__":
    logger.info("Starting Enhanced Trinity Socket Mode Handler...")
    
    # Verify required environment variables
    required_vars = ["SLACK_BOT_TOKEN_RO", "SLACK_APP_TOKEN"]
    for var in required_vars:
        if not os.environ.get(var):
            logger.error(f"Missing required environment variable: {var}")
            exit(1)
        else:
            logger.info(f"✅ {var} is configured")
    
    # Test Council API connectivity
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{COUNCIL_API_URL}/health")
            if response.status_code == 200:
                logger.info("✅ Council API connectivity verified")
            else:
                logger.warning(f"⚠️ Council API health check failed: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Council API connectivity test failed: {e}")
    
    # Start Socket Mode handler
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    
    logger.info("🚀 Enhanced Trinity Socket Mode ready - slash commands active!")
    handler.start() 