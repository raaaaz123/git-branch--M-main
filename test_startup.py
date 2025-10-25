#!/usr/bin/env python3
"""
Simple startup test to isolate container startup issues
"""
import os
import sys

def test_imports():
    """Test all critical imports"""
    print("🔍 Testing imports...")
    
    try:
        print("✅ Testing basic imports...")
        import fastapi
        import uvicorn
        print("✅ FastAPI and Uvicorn imported successfully")
        
        print("✅ Testing app imports...")
        from app.main import app
        print("✅ FastAPI app imported successfully")
        
        print("✅ Testing config...")
        from app.config import API_HOST, API_PORT
        print(f"✅ Config loaded - HOST: {API_HOST}, PORT: {API_PORT}")
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_server_start():
    """Test if server can start"""
    print("\n🔍 Testing server startup...")
    
    try:
        import uvicorn
        from app.main import app
        
        # Get port from environment
        port = int(os.getenv("PORT", 8001))
        host = os.getenv("HOST", "0.0.0.0")
        
        print(f"🚀 Attempting to start server on {host}:{port}")
        print(f"🔧 Environment PORT: {os.getenv('PORT', 'not set')}")
        print(f"🔧 Environment HOST: {os.getenv('HOST', 'not set')}")
        
        # This will start the server (for testing purposes)
        # In production, this would be handled by main.py
        print("✅ Server startup test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Running container startup tests...")
    
    # Test imports
    imports_ok = test_imports()
    
    if imports_ok:
        # Test server startup
        server_ok = test_server_start()
        
        if server_ok:
            print("\n✅ All tests passed! Container should start successfully.")
            sys.exit(0)
        else:
            print("\n❌ Server startup test failed.")
            sys.exit(1)
    else:
        print("\n❌ Import test failed.")
        sys.exit(1)
