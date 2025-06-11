#!/usr/bin/env python3
"""
Socket Mode Handler - Trinity Internal Routing
Routes Slack commands through Trinity's /orchestrate endpoint
Preserves all cost guards, latency optimization, and ledger logging
"""

import os
import asyncio
import httpx
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
try:
    with open('commlink_config.txt', 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
except FileNotFoundError:
    logger.warning("commlink_config.txt not found, using environment variables")

# Trinity orchestrate endpoint (switched to real API - no more templates!)
ORCH_URL = "http://host.docker.internal:9300/orchestrate"

# Initialize Slack app
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN_RO"))

async def route_to_trinity(prompt: str, agent: str) -> str:
    """Route request through Trinity's internal /orchestrate endpoint"""
    logger.info(f"📡 Routing to Trinity: {agent} - {prompt[:50]}...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ORCH_URL,
                json={"prompt": prompt},
                headers={"X-Agent": agent, "Content-Type": "application/json"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("response", data.get("answer", "❌ No response"))
                model = data.get("model_used", "unknown")
                latency = data.get("latency_ms", 0)
                
                logger.info(f"✅ Trinity response: {model} in {latency}ms")
                return result
            else:
                logger.error(f"❌ Trinity error {response.status_code}: {response.text}")
                return f"❌ Trinity API error: {response.status_code}"
                
    except Exception as e:
        logger.error(f"❌ Trinity routing failed: {e}")
        return f"❌ Trinity routing failed: {str(e)}"

# Slack command handlers
@app.command("/phi3")
async def handle_phi3_command(ack, command, client):
    """Handle /phi3 command through Trinity"""
    await ack()
    logger.info(f"📱 /phi3 command: {command['text']}")
    
    # Send immediate acknowledgment
    await client.chat_postMessage(
        channel=command["channel_id"],
        text="🤖 Phi3 processing..."
    )
    
    # Route through Trinity
    response = await route_to_trinity(command["text"], "phi3")
    
    # Send Trinity response
    await client.chat_postMessage(
        channel=command["channel_id"],
        text=f"🤖 **Phi3**: {response}"
    )

@app.command("/opus")
async def handle_opus_command(ack, command, client):
    """Handle /opus command through Trinity"""
    await ack()
    logger.info(f"📱 /opus command: {command['text']}")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text="🎭 Opus thinking..."
    )
    
    response = await route_to_trinity(command["text"], "opus")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text=f"🎭 **Opus**: {response}"
    )

@app.command("/o3")
async def handle_o3_command(ack, command, client):
    """Handle /o3 command through Trinity"""
    await ack()
    logger.info(f"📱 /o3 command: {command['text']}")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text="🧠 O3 analyzing..."
    )
    
    response = await route_to_trinity(command["text"], "o3")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text=f"🧠 **O3**: {response}"
    )

@app.command("/commlink")
async def handle_commlink_command(ack, command, client):
    """Handle /commlink command through Trinity router"""
    await ack()
    logger.info(f"📱 /commlink command: {command['text']}")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text="📡 Commlink routing..."
    )
    
    response = await route_to_trinity(command["text"], "router")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text=f"📡 **Commlink**: {response}"
    )

async def main():
    """Start the Socket Mode handler with Trinity routing"""
    logger.info("🚀 Starting Socket Mode Handler - Trinity Internal")
    logger.info("=" * 60)
    logger.info(f"📡 Trinity endpoint: {ORCH_URL}")
    
    # Verify configuration
    app_token = os.environ.get("SLACK_APP_TOKEN")
    bot_token = os.environ.get("SLACK_BOT_TOKEN_RO")
    
    if not app_token:
        logger.error("❌ SLACK_APP_TOKEN not found")
        return
    
    if not bot_token:
        logger.error("❌ SLACK_BOT_TOKEN_RO not found")
        return
    
    logger.info(f"✅ App token: {app_token[:12]}...")
    logger.info(f"✅ Bot token: {bot_token[:12]}...")
    
    # Test Trinity connectivity
    logger.info("🔍 Testing Trinity connectivity...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://host.docker.internal:9300/health", timeout=5.0)
            if response.status_code == 200:
                logger.info("✅ Trinity health check passed")
            else:
                logger.warning(f"⚠️ Trinity health check failed: {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ Trinity connectivity test failed: {e}")
    
    # Start Socket Mode handler
    handler = AsyncSocketModeHandler(app, app_token)
    
    logger.info("🔌 Connecting to Slack Socket Mode...")
    logger.info("📡 All commands will route through Trinity internal stack")
    await handler.start_async()

if __name__ == "__main__":
    asyncio.run(main()) 