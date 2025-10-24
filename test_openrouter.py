"""
Test script specifically for OpenRouter integration
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_openrouter_connection():
    """Test OpenRouter API connection"""
    print("🔍 Testing OpenRouter connection...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/test-openrouter")
        print(f"✅ OpenRouter test: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Status: {result.get('status')}")
            print(f"   Message: {result.get('message')}")
            print(f"   Model: {result.get('model')}")
            print(f"   Response: {result.get('response')}")
            return True
        else:
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_ai_chat_with_openrouter():
    """Test AI chat using OpenRouter"""
    print("\n🔍 Testing AI chat with OpenRouter...")
    
    test_chat = {
        "message": "Hello! Can you tell me about your company?",
        "widgetId": "test-widget-456",
        "conversationId": "test-conversation-123",
        "aiConfig": {
            "enabled": True,
            "provider": "openrouter",
            "model": "x-ai/grok-4-fast:free",
            "temperature": 0.7,
            "maxTokens": 500,
            "confidenceThreshold": 0.6,
            "maxRetrievalDocs": 5,
            "ragEnabled": False,  # Test without RAG first
            "fallbackToHuman": True
        },
        "customerName": "Test Customer",
        "customerEmail": "customer@example.com"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=test_chat)
        print(f"✅ AI chat: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Response: {result.get('response')}")
            print(f"   Confidence: {result.get('confidence')}")
            print(f"   Mode: {result.get('metadata', {}).get('mode')}")
            return True
        else:
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ AI chat test failed: {e}")
        return False

def test_ai_chat_with_rag():
    """Test AI chat with RAG using OpenRouter"""
    print("\n🔍 Testing AI chat with RAG using OpenRouter...")
    
    test_chat = {
        "message": "What services do you offer?",
        "widgetId": "test-widget-456",
        "conversationId": "test-conversation-123",
        "aiConfig": {
            "enabled": True,
            "provider": "openrouter",
            "model": "x-ai/grok-4-fast:free",
            "temperature": 0.7,
            "maxTokens": 500,
            "confidenceThreshold": 0.6,
            "maxRetrievalDocs": 5,
            "ragEnabled": True,  # Test with RAG
            "fallbackToHuman": True
        },
        "customerName": "Test Customer",
        "customerEmail": "customer@example.com"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=test_chat)
        print(f"✅ AI chat with RAG: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Response: {result.get('response')}")
            print(f"   Confidence: {result.get('confidence')}")
            print(f"   Sources: {len(result.get('sources', []))}")
            print(f"   Mode: {result.get('metadata', {}).get('mode')}")
            return True
        else:
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ AI chat with RAG test failed: {e}")
        return False

def main():
    """Run OpenRouter tests"""
    print("🚀 Starting OpenRouter integration tests...")
    print("=" * 60)
    
    try:
        # Test connection
        connection_ok = test_openrouter_connection()
        
        if connection_ok:
            # Test direct chat
            chat_ok = test_ai_chat_with_openrouter()
            
            # Test RAG chat
            rag_ok = test_ai_chat_with_rag()
            
            print("\n" + "=" * 60)
            if connection_ok and chat_ok and rag_ok:
                print("✅ All OpenRouter tests passed!")
            else:
                print("⚠️ Some tests failed, but OpenRouter is working")
        else:
            print("❌ OpenRouter connection failed")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the backend is running on http://localhost:8001")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
