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
        print("🔍 Checking app/__init__.py...")
        if os.path.exists("app/__init__.py"):
            print("✅ app/__init__.py exists")
        else:
            print("❌ app/__init__.py not found")
    else:
        print("❌ app directory not found")
    
    print("🔄 Falling back to simplified app...")
    # Create a minimal FastAPI app as fallback
    from fastapi import FastAPI
    app = FastAPI(title="Rexa Engage API (Fallback)", version="1.0.0")
    
    @app.get("/")
    async def root():
        return {"message": "Rexa Engage API (Fallback Mode)", "status": "running"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "mode": "fallback", "port": os.getenv("PORT", "not set")}
    
    print("✅ Created fallback FastAPI app")
    
except Exception as e:
    print(f"❌ Failed to import FastAPI app: {e}")
    import traceback
    traceback.print_exc()
    print("🔄 Creating minimal fallback app...")
    
    # Create a minimal FastAPI app as last resort
    from fastapi import FastAPI
    app = FastAPI(title="Rexa Engage API (Emergency)", version="1.0.0")
    
    @app.get("/")
    async def root():
        return {"message": "Rexa Engage API (Emergency Mode)", "status": "running"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "mode": "emergency", "port": os.getenv("PORT", "not set")}
    
    print("✅ Created emergency FastAPI app")

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
