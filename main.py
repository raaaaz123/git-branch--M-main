"""
Entry point for the modular backend - maintains same API structure as original
"""
import os
import sys

# Add error handling for imports
try:
    from app.main import app
    print("✅ Successfully imported FastAPI app")
except Exception as e:
    print(f"❌ Failed to import FastAPI app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting server on {host}:{port}")
    
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=False,  # Disable reload in production
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)
