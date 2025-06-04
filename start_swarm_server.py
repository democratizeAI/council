#!/usr/bin/env python3
"""
Start SwarmAI server for Titanic Gauntlet testing
"""

import os
import uvicorn
import sys

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

if __name__ == "__main__":
    print("🚀 Starting SwarmAI server for Titanic Gauntlet...")
    print("📊 Server will be available at http://localhost:8000")
    print("🏥 Health check: http://localhost:8000/health")
    
    # Set environment for local testing
    os.environ.setdefault("SWARM_GPU_PROFILE", "rtx_4070")
    os.environ.setdefault("SWARM_COUNCIL_ENABLED", "true")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"💥 Server failed to start: {e}")
        sys.exit(1) 