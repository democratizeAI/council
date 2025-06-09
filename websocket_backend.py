import asyncio
import json
import logging
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from concurrent.futures import ThreadPoolExecutor

# Note: These would normally be imported from your main app
# from your_main_app import app, vote

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

manager = ConnectionManager()

# Placeholder for app - should be imported from main module
app = FastAPI()

async def vote(prompt: str):
    """Placeholder vote function - should be imported from router"""
    return {"text": f"Response to: {prompt}", "voting_stats": {}}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "chat":
                # Stream response through WebSocket
                prompt = message["prompt"]
                result = await vote(prompt)
                
                # Stream tokens
                text = result.get("text", "")
                words = text.split()
                
                for i, word in enumerate(words):
                    token_msg = {
                        "type": "token",
                        "token": word + " ",
                        "index": i,
                        "total": len(words)
                    }
                    await manager.send_message(token_msg, websocket)
                    await asyncio.sleep(0.05)
                
                # Send completion
                completion_msg = {
                    "type": "complete",
                    "meta": result.get("voting_stats", {})
                }
                await manager.send_message(completion_msg, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
