from fastapi import FastAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from api.metrics import record_canary, IS_CANARY
import time
import os

app = FastAPI(title="Council API Canary" if IS_CANARY else "Council API")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "canary": IS_CANARY, "timestamp": time.time()}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return generate_latest().decode('utf-8')

@app.get("/")
async def root():
    """Root endpoint"""
    record_canary("root", True)
    return {
        "message": "Council API Canary" if IS_CANARY else "Council API", 
        "version": "1.0.0",
        "canary": IS_CANARY,
        "gpu_id": os.getenv("GPU_AUX_ID", "0")
    }

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint for canary traffic"""
    try:
        record_canary("test", True)
        return {
            "success": True,
            "canary": IS_CANARY,
            "gpu": os.getenv("GPU_AUX_ID", "0"),
            "message": "Canary test successful" if IS_CANARY else "Main API test successful"
        }
    except Exception as e:
        record_canary("test", False)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 