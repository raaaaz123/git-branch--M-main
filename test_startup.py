#!/usr/bin/env python3
"""
Test script to verify the application can start successfully
"""
import os
import sys
import subprocess
import time

def test_imports():
    """Test that all imports work"""
    print("Testing imports...")
    try:
        from app.main import app
        print("✅ FastAPI app import successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_startup():
    """Test that the app can start"""
    print("Testing app startup...")
    try:
        # Set environment variables
        env = os.environ.copy()
        env['PORT'] = '8081'
        env['HOST'] = '0.0.0.0'
        
        # Start the app in background
        process = subprocess.Popen([
            sys.executable, 'main.py'
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait a bit for startup
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ App started successfully")
            process.terminate()
            process.wait()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ App failed to start")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Startup test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing backend startup...")
    
    tests = [
        test_imports,
        test_startup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
