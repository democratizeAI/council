#!/usr/bin/env python3
"""
Slack ↔ Trinity Integration Router
=================================
FastAPI routes for Slack command handling with correlation tracking.
"""

import asyncio
import uuid
import logging
import time
import hmac
import hashlib
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])

# Slack event queue for async processing
slack_event_queue = asyncio.Queue()

def make_uuid() -> str:
    """Generate a correlation ID for tracking"""
    return str(uuid.uuid4())[:8]

def verify_slack_signature(body: bytes, timestamp: str, signature: str, signing_secret: str) -> bool:
    """Verify Slack request authenticity using HMAC"""
    try:
        # Slack signature format: v0=<hex>
        if not signature.startswith('v0='):
            return False
            
        basestring = f"v0:{timestamp}:{body.decode()}"
        expected = "v0=" + hmac.new(
            signing_secret.encode(),
            basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        logger.error(f"HMAC verification failed: {e}")
        return False

async def enqueue_slack_event(command: str, text: str, user_id: str, correlation_id: str):
    """Enqueue Slack event for async processing"""
    event = {
        "command": command,
        "text": text,
        "user_id": user_id,
        "correlation_id": correlation_id,
        "timestamp": datetime.now().isoformat(),
        "status": "queued"
    }
    
    await slack_event_queue.put(event)
    logger.info(f"Enqueued Slack event: {command} | corr: {correlation_id}")

async def process_command(command: str, text: str, user_id: str, correlation_id: str) -> Dict[str, Any]:
    """Process individual Slack commands"""
    
    if command == "/o3":
        # Direct o3 model interaction
        logger.info(f"Processing /o3 command | corr: {correlation_id}")
        if text.strip() == "ping":
            return {"text": "pong", "model": "o3", "latency_ms": 50}
        else:
            # Route to o3 model API
            return {"text": f"o3 processing: {text}", "model": "o3"}
    
    elif command == "/opus":
        # Council (Opus) deliberation
        logger.info(f"Processing /opus command | corr: {correlation_id}")
        if text.strip() == "ping":
            return {"text": "pong", "source": "council"}
        else:
            # Route to council voting system
            return {"text": f"Council deliberating: {text}", "source": "council"}
    
    elif command == "/ticket":
        # Ticket management
        logger.info(f"Processing /ticket command | corr: {correlation_id}")
        # Parse ticket creation: /ticket add title="..." wave=B owner=Dev effort=2h
        if text.startswith("add"):
            return {"text": f"Ticket queued for creation | corr: {correlation_id}", "action": "create"}
        else:
            return {"text": "Usage: /ticket add title=\"...\" wave=B owner=Dev effort=2h"}
    
    elif command == "/patches":
        # Patch status query
        logger.info(f"Processing /patches command | corr: {correlation_id}")
        return {"text": "Recent patches: B-01 ✅, B-02 ✅, B-03 🟡 queued"}
    
    elif command == "/status":
        # Pipeline status
        logger.info(f"Processing /status command | corr: {correlation_id}")
        return {
            "text": "Trinity Pipeline Status",
            "attachments": [
                {
                    "color": "good",
                    "fields": [
                        {"title": "Council", "value": "✅ Healthy", "short": True},
                        {"title": "Builder", "value": "✅ Active", "short": True},
                        {"title": "Guardian", "value": "✅ Monitoring", "short": True},
                        {"title": "Queue Depth", "value": "3 items", "short": True}
                    ]
                }
            ]
        }
    
    else:
        return {"text": f"Unknown command: {command}"}

@router.post("/commands")
async def slack_commands(request: Request, background_tasks: BackgroundTasks):
    """
    Main Slack command handler
    Handles: /o3, /opus, /ticket, /patches, /status
    """
    try:
        # Parse form data
        form_data = await request.form()
        
        # Extract Slack command data
        command = form_data.get("command", "")
        text = form_data.get("text", "")
        user_id = form_data.get("user_id", "")
        trigger_id = form_data.get("trigger_id", "")
        
        # Generate correlation ID
        correlation_id = make_uuid()
        
        # Add correlation ID to request headers for downstream services
        request.headers.__dict__["X-Corr-ID"] = correlation_id
        
        # Enqueue for async processing
        background_tasks.add_task(
            enqueue_slack_event, 
            command, text, user_id, correlation_id
        )
        
        # Immediate 3-second response per Slack spec
        return {
            "response_type": "ephemeral",
            "text": f"✅ Received • tracking id `{correlation_id}`",
            "attachments": [
                {
                    "color": "good",
                    "text": f"Command `{command}` queued for processing"
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Slack command error: {e}")
        return {
            "response_type": "ephemeral", 
            "text": f"🔴 Error processing command: {str(e)}"
        }

@router.post("/interactive")
async def slack_interactive(request: Request):
    """Handle Slack interactive components (buttons, modals)"""
    try:
        form_data = await request.form()
        payload = form_data.get("payload", "{}")
        
        # Parse interactive payload
        import json
        interaction = json.loads(payload)
        
        action_type = interaction.get("type", "")
        correlation_id = make_uuid()
        
        if action_type == "block_actions":
            # Handle button clicks, etc.
            actions = interaction.get("actions", [])
            for action in actions:
                if action.get("action_id") == "retry_command":
                    # Retry failed command
                    return {
                        "text": f"🔄 Retrying command | corr: {correlation_id}"
                    }
        
        return {"text": "Interactive component processed"}
        
    except Exception as e:
        logger.error(f"Interactive component error: {e}")
        return {"text": f"🔴 Error: {str(e)}"}

@router.post("/events")
async def slack_events(request: Request):
    """Handle Slack Events API (mentions, reactions, etc.)"""
    try:
        body = await request.json()
        
        # Handle URL verification challenge
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge")}
        
        # Handle actual events
        event = body.get("event", {})
        event_type = event.get("type", "")
        correlation_id = make_uuid()
        
        if event_type == "app_mention":
            # Handle @Trinity-Ops mentions
            text = event.get("text", "")
            user = event.get("user", "")
            logger.info(f"App mention | user: {user} | corr: {correlation_id}")
            
        elif event_type == "reaction_added":
            # Handle emoji reactions to messages
            reaction = event.get("reaction", "")
            logger.info(f"Reaction added: {reaction} | corr: {correlation_id}")
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Events API error: {e}")
        return {"error": str(e)}

@router.get("/health")
async def slack_health():
    """Health check for Slack integration"""
    return {
        "status": "healthy",
        "service": "slack-integration",
        "queue_size": slack_event_queue.qsize(),
        "timestamp": datetime.now().isoformat()
    }

@router.post("/webhook/success")
async def webhook_success(request: Request):
    """
    Webhook for Builder/PatchCtl to post success notifications
    Called from CI workflows and deployment scripts
    """
    try:
        body = await request.json()
        
        correlation_id = body.get("correlation_id", make_uuid())
        event_type = body.get("event_type", "unknown")
        message = body.get("message", "")
        
        # Log success event
        logger.info(f"Success webhook: {event_type} | corr: {correlation_id}")
        
        # In production, this would post back to Slack thread
        # using the correlation_id to find the original message
        
        return {"status": "success", "correlation_id": correlation_id}
        
    except Exception as e:
        logger.error(f"Success webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook/failure")
async def webhook_failure(request: Request):
    """
    Webhook for failure notifications from any service
    Includes retry button in Slack message
    """
    try:
        body = await request.json()
        
        correlation_id = body.get("correlation_id", make_uuid())
        error_stage = body.get("stage", "unknown")
        error_message = body.get("error", "")
        
        # Log failure event
        logger.error(f"Failure webhook: {error_stage} | {error_message} | corr: {correlation_id}")
        
        # In production, this would post retry button to Slack
        failure_response = {
            "status": "failure",
            "correlation_id": correlation_id,
            "stage": error_stage,
            "retry_available": True
        }
        
        return failure_response
        
    except Exception as e:
        logger.error(f"Failure webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) 