import time
from fastapi import FastAPI, Form, Query
from router.voting import vote

app = FastAPI()

def extract_token_counts(result):
    """Extract token counts from result"""
    return result.get("token_counts", {})

def extract_confidences(result):
    """Extract confidence scores from result"""
    return result.get("confidence_scores", {})

@app.post("/chat")
async def chat(
    prompt: str = Form(...), 
    debug: bool = Query(False, description="Include debug metadata")
):
    """Chat endpoint with optional debug metadata"""
    
    result = await vote(prompt)
    
    response = {
        "text": result["text"],
        "model": result.get("model", "unknown"),
        "timestamp": result.get("timestamp", time.time())
    }
    
    if debug:
        # Include full debug metadata only when requested
        response.update({
            "voices": result.get("candidates", []),
            "voting_stats": result.get("voting_stats", {}),
            "specialists_tried": result.get("specialists_tried", []),
            "provider_chain": result.get("provider_chain", []),
            "council_decision": result.get("council_decision", False),
            "debug_info": {
                "latency_breakdown": result.get("voting_stats", {}),
                "token_counts": extract_token_counts(result),
                "confidence_scores": extract_confidences(result)
            }
        })
    
    return response
