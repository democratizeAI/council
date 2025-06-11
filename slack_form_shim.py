#!/usr/bin/env python3
"""
Slack Form→JSON Shim
Converts Slack's application/x-www-form-urlencoded to JSON for /orchestrate
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse
import httpx
import os
import urllib.parse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Slack Form Shim")

# Configuration
ORCHESTRATE_URL = os.getenv("COUNCIL_API_URL", "http://localhost:9010") + "/orchestrate"

@app.post("/slack")
async def slack_form_shim(request: Request):
    """Convert Slack form data to JSON and forward to orchestrate"""
    try:
        # Get form data from Slack
        body_bytes = await request.body()
        params = urllib.parse.parse_qs(body_bytes.decode())
        
        # Extract Slack fields
        slack_data = {k: v[0] if v else "" for k, v in params.items()}
        
        # Extract command and text  
        command = slack_data.get('command', '')
        text = slack_data.get('text', '')
        
        # Map command to agent
        agent_mapping = {
            '/phi3': 'router',
            '/o3': 'o3', 
            '/opus': 'opus',
            '/commlink': 'router'
        }
        
        agent = agent_mapping.get(command, 'router')
        
        # Create prompt for orchestrate
        if text:
            prompt = f"{command} {text}"
        else:
            prompt = f"{command} ping"
            
        # Forward to orchestrate as JSON
        json_payload = {
            "prompt": prompt,
            "temperature": 0.7,
            "max_tokens": 512
        }
        
        headers = {
            "X-Agent": agent,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Forwarding {command} to agent {agent}: {prompt}")
        
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.post(
                ORCHESTRATE_URL,
                json=json_payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                return JSONResponse({
                    "response_type": "in_channel",
                    "text": f"🤖 {agent} ▸ {result.get('response', 'Processing...')}"
                })
            else:
                logger.error(f"Orchestrate error {response.status_code}: {response.text}")
                return JSONResponse({
                    "response_type": "ephemeral", 
                    "text": f"⚠️ Service temporarily unavailable (error {response.status_code})"
                })
                
    except Exception as e:
        logger.error(f"Shim error: {e}")
        return JSONResponse({
            "response_type": "ephemeral",
            "text": "⚠️ Internal error - check logs"
        })

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "slack-form-shim"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8089) 