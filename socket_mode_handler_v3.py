#!/usr/bin/env python3
"""
Socket Mode Handler v3 - Real AI Integration
Connects Slack Socket Mode to real AI services (cloud APIs)
"""

import os
import asyncio
import aiohttp
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

# Initialize Slack app
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN_RO"))

# Real AI API configurations
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

async def call_openai_api(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    """Call OpenAI API for real AI responses"""
    if not OPENAI_API_KEY:
        return "❌ OpenAI API key not configured"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150,
        "temperature": 0.7
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error {response.status}: {error_text}")
                    return f"❌ OpenAI API error: {response.status}"
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return f"❌ OpenAI API call failed: {str(e)}"

async def call_anthropic_api(prompt: str) -> str:
    """Call Anthropic Claude API for real AI responses"""
    if not ANTHROPIC_API_KEY:
        return "❌ Anthropic API key not configured"
    
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["content"][0]["text"].strip()
                else:
                    error_text = await response.text()
                    logger.error(f"Anthropic API error {response.status}: {error_text}")
                    return f"❌ Anthropic API error: {response.status}"
    except Exception as e:
        logger.error(f"Anthropic API call failed: {e}")
        return f"❌ Anthropic API call failed: {str(e)}"

async def process_ai_request(prompt: str, agent: str) -> str:
    """Route requests to appropriate real AI services"""
    logger.info(f"Processing AI request for agent '{agent}': {prompt[:50]}...")
    
    try:
        if agent in ["phi3", "router"]:
            # Use GPT-3.5-turbo for phi3/router requests
            response = await call_openai_api(prompt, "gpt-3.5-turbo")
        elif agent == "opus":
            # Use Claude for opus requests
            response = await call_anthropic_api(prompt)
        elif agent == "o3":
            # Use GPT-4 for o3 requests
            response = await call_openai_api(prompt, "gpt-4")
        else:
            # Default to GPT-3.5-turbo
            response = await call_openai_api(prompt, "gpt-3.5-turbo")
        
        logger.info(f"✅ AI response received for {agent}: {len(response)} chars")
        return response
        
    except Exception as e:
        logger.error(f"❌ AI processing failed: {e}")
        return f"❌ AI processing failed: {str(e)}"

# Slack command handlers
@app.command("/phi3")
async def handle_phi3_command(ack, command, client):
    """Handle /phi3 command with real AI"""
    await ack()
    logger.info(f"📱 /phi3 command: {command['text']}")
    
    # Send immediate acknowledgment
    await client.chat_postMessage(
        channel=command["channel_id"],
        text="🤖 Phi3 is thinking..."
    )
    
    # Process with real AI
    response = await process_ai_request(command["text"], "phi3")
    
    # Send real AI response
    await client.chat_postMessage(
        channel=command["channel_id"],
        text=f"🤖 **Phi3**: {response}"
    )

@app.command("/opus")
async def handle_opus_command(ack, command, client):
    """Handle /opus command with real AI"""
    await ack()
    logger.info(f"📱 /opus command: {command['text']}")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text="🎭 Opus is composing..."
    )
    
    response = await process_ai_request(command["text"], "opus")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text=f"🎭 **Opus**: {response}"
    )

@app.command("/o3")
async def handle_o3_command(ack, command, client):
    """Handle /o3 command with real AI"""
    await ack()
    logger.info(f"📱 /o3 command: {command['text']}")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text="🧠 O3 is processing..."
    )
    
    response = await process_ai_request(command["text"], "o3")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text=f"🧠 **O3**: {response}"
    )

@app.command("/commlink")
async def handle_commlink_command(ack, command, client):
    """Handle /commlink command with real AI"""
    await ack()
    logger.info(f"📱 /commlink command: {command['text']}")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text="📡 Commlink router engaging..."
    )
    
    response = await process_ai_request(command["text"], "router")
    
    await client.chat_postMessage(
        channel=command["channel_id"],
        text=f"📡 **Commlink**: {response}"
    )

async def main():
    """Start the Socket Mode handler with real AI integration"""
    logger.info("🚀 Starting Socket Mode Handler v3 with Real AI")
    logger.info("=" * 60)
    
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
    
    # Check AI API keys
    if OPENAI_API_KEY:
        logger.info(f"✅ OpenAI API key: {OPENAI_API_KEY[:12]}...")
    else:
        logger.warning("⚠️ OpenAI API key not configured")
    
    if ANTHROPIC_API_KEY:
        logger.info(f"✅ Anthropic API key: {ANTHROPIC_API_KEY[:12]}...")
    else:
        logger.warning("⚠️ Anthropic API key not configured")
    
    # Start Socket Mode handler
    handler = AsyncSocketModeHandler(app, app_token)
    
    logger.info("🔌 Connecting to Slack Socket Mode...")
    await handler.start_async()

if __name__ == "__main__":
    asyncio.run(main()) 