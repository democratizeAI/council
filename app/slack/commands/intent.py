#!/usr/bin/env python3
"""
/intent Slack Command - IDR-01 Integration
Converts user intent to structured ledger rows via IDA micro-service
"""

import os
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Any

# Configure logging
logger = logging.getLogger('intent-command')

# Configuration
IDA_SERVICE_URL = os.getenv('IDA_SERVICE_URL', 'http://ida-service:8080')
COUNCIL_API_URL = os.getenv('COUNCIL_API_URL', 'http://council-api:8000')


class IntentProcessor:
    """Processes user intent via IDA and creates ledger rows"""
    
    def __init__(self):
        self.ida_url = IDA_SERVICE_URL
        self.council_url = COUNCIL_API_URL
        self.ledger_endpoint = f"{self.council_url}/ledger/new"
    
    def call_ida_service(self, user_intent: str, user_id: str) -> Dict[str, Any]:
        """Call IDA micro-service to convert intent to structured data"""
        try:
            payload = {
                "intent": user_intent,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "source": "slack-intent-command"
            }
            
            response = requests.post(
                f"{self.ida_url}/analyze-intent",
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"IDA service call failed: {e}")
            return self._fallback_intent_parsing(user_intent, user_id)
    
    def _fallback_intent_parsing(self, intent: str, user_id: str) -> Dict[str, Any]:
        """Fallback intent parsing when IDA service is unavailable"""
        intent_lower = intent.lower()
        
        if any(word in intent_lower for word in ['bug', 'error', 'broken']):
            ticket_type = 'bug'
            priority = 'high'
        elif any(word in intent_lower for word in ['feature', 'add', 'new']):
            ticket_type = 'feature' 
            priority = 'medium'
        else:
            ticket_type = 'task'
            priority = 'medium'
        
        return {
            "ticket_type": ticket_type,
            "priority": priority,
            "title": intent[:100],
            "description": intent,
            "estimated_hours": 8,
            "labels": ["slack-intent"],
            "ida_available": False
        }
    
    def post_to_ledger(self, ida_result: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Post structured row to ledger via Council API"""
        row_id = f"INTENT_{user_id}_{int(time.time())}"
        
        payload = {
            "row_id": row_id,
            "row_type": "ticket",
            "created_at": datetime.now().isoformat(),
            "created_by": f"slack-user-{user_id}",
            "ticket_data": {
                "id": row_id,
                "status": "open",
                **ida_result
            },
            "metadata": {
                "source": "slack-intent-command",
                "version": "IDR-01",
                "user_id": user_id
            }
        }
        
        response = requests.post(self.ledger_endpoint, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


def handle_intent_command(text: str, user_id: str, channel_id: str) -> Dict[str, Any]:
    """Handle /intent Slack command"""
    processor = IntentProcessor()
    
    try:
        # Analyze intent via IDA
        ida_result = processor.call_ida_service(text, user_id)
        
        # Post to ledger
        ledger_result = processor.post_to_ledger(ida_result, user_id)
        
        response_text = f"""✅ **Intent processed successfully!**

📋 **Ticket Created:** `{ida_result.get('title', 'New Ticket')}`
🎯 **Type:** {ida_result['ticket_type'].title()}
⚡ **Priority:** {ida_result['priority'].title()}

🔗 **Next Steps:**
• Builder-swarm will automatically scaffold PR
• CI will run security + arch checks
• Auto-merge on green if autonomous label applied

🎛️ **IDA Service:** {'✅ Available' if ida_result.get('ida_available', True) else '⚠️ Fallback mode'}
"""
        
        return {
            "response_type": "ephemeral",
            "text": response_text
        }
        
    except Exception as e:
        logger.error(f"Intent processing failed: {e}")
        return {
            "response_type": "ephemeral",
            "text": f"❌ **Intent processing failed:** {str(e)}"
        }


# FastAPI endpoint for Slack integration
if __name__ == "__main__":
    # Example usage for testing
    test_result = handle_intent_command(
        text="Add authentication to the API endpoints",
        user_id="U12345",
        channel_id="C67890"
    )
    print(json.dumps(test_result, indent=2)) 