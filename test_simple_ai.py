import requests
import json

BASE_URL = "http://localhost:8001"

def test_ai_chat():
    """Test AI chat with the new DeepSeek model"""
    print("Testing AI Chat with DeepSeek model...")
    
    # Test payload
    payload = {
        "message": "Hello, how are you?",
        "widgetId": "test-widget-456",
        "conversationId": "test-conversation-123",
        "aiConfig": {
            "enabled": True,
            "provider": "openrouter",
            "model": "deepseek/deepseek-chat-v3.1:free",
            "temperature": 0.7,
            "maxTokens": 500,
            "confidenceThreshold": 0.6,
            "maxRetrievalDocs": 5,
            "ragEnabled": False,
            "fallbackToHuman": True
        },
        "businessId": "ygtGolij4bCKpovFMRF8",
        "customerName": "Test User",
        "customerEmail": "test@example.com"
    }
    
    try:
        print(f"Sending request to {BASE_URL}/api/ai/chat")
        print(f"Model: {payload['aiConfig']['model']}")
        print(f"Message: {payload['message']}")
        
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=payload, timeout=30)
        
        print(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
            print(f"Response: {result.get('response', 'No response')}")
            print(f"Confidence: {result.get('confidence', 0)}")
            print(f"Sources: {len(result.get('sources', []))}")
            return True
        else:
            print(f"Error Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to the API server. Make sure the backend is running.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    test_ai_chat()
