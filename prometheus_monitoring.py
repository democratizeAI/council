import time
import logging
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import Histogram, Counter, generate_latest

app = FastAPI()
logger = logging.getLogger(__name__)

# Metrics
REQUEST_LATENCY = Histogram('chat_request_duration_seconds', 
                           'Chat request latency', 
                           buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0])

FIRST_TOKEN_LATENCY = Histogram('chat_first_token_duration_seconds',
                               'Time to first token',
                               buckets=[0.1, 0.3, 0.5, 1.0, 2.0])

CHAT_ERRORS = Counter('chat_errors_total', 'Chat errors by type', ['error_type'])

@app.middleware("http")
async def performance_middleware(request, call_next):
    if request.url.path.startswith('/chat'):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        REQUEST_LATENCY.observe(duration)
        
        # Alert if p95 > 2s
        if duration > 2.0:
            logger.warning(f"Slow chat response: {duration:.2f}s")
        
        return response
    
    return await call_next(request)

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
