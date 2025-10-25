"""
Entry point for the modular backend - maintains same API structure as original
"""
import os
import sys

# Add comprehensive error handling for imports
print("🔍 Starting container initialization...")
print(f"🔧 Python version: {sys.version}")
print(f"🔧 Working directory: {os.getcwd()}")
print(f"🔧 Environment variables:")
print(f"   - PORT: {os.getenv('PORT', 'not set')}")
print(f"   - HOST: {os.getenv('HOST', 'not set')}")

try:
    print("🔍 Importing FastAPI app...")
    from app.main import app
    print("✅ Successfully imported FastAPI app")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("🔍 Checking if app directory exists...")
    if os.path.exists("app"):
        print("✅ app directory exists")
        print("🔍 Checking app contents...")
        for item in os.listdir("app"):
            print(f"   - {item}")
    else:
        print("❌ app directory not found")
    sys.exit(1)
except Exception as e:
    print(f"❌ Failed to import FastAPI app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable (Cloud Run sets PORT=8001)
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting server on {host}:{port}")
    print(f"🔧 Environment PORT: {os.getenv('PORT', 'not set')}")
    print(f"🔧 Environment HOST: {os.getenv('HOST', 'not set')}")
    
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
