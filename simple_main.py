#!/usr/bin/env python3
"""
Simplified entry point for Cloud Run deployment
This version has minimal dependencies and should definitely start
"""
import os
import sys
from fastapi import FastAPI
import uvicorn

# Create a simple FastAPI app
app = FastAPI(title="Rexa Engage API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Rexa Engage API is running!", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "port": os.getenv("PORT", "not set")}

if __name__ == "__main__":
    # Get port from environment variable (Cloud Run sets PORT=8001)
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting simplified server on {host}:{port}")
    print(f"🔧 Environment PORT: {os.getenv('PORT', 'not set')}")
    print(f"🔧 Environment HOST: {os.getenv('HOST', 'not set')}")
    print(f"🔧 Python version: {sys.version}")
    print(f"🔧 Working directory: {os.getcwd()}")
    
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
