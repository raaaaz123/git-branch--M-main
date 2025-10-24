import requests
import json

BASE_URL = "http://localhost:8001"

def test_widget_preview_api():
    """Test AI chat API exactly as the widget preview calls it"""
    print("=" * 80)
    print("Testing Widget Preview API Call")
    print("=" * 80)
    
    # Exact payload as sent by widget preview
    payload = {
        "message": "Get Support",
        "widgetId": "preview-widget-id",
        "conversationId": "preview-conversation",
        "aiConfig": {
            "enabled": True,
            "provider": "openrouter",
            "model": "deepseek/deepseek-chat-v3.1:free",
            "temperature": 0.7,
            "maxTokens": 500,
            "confidenceThreshold": 0.6,
            "maxRetrievalDocs": 5,
            "ragEnabled": True,
            "fallbackToHuman": True
        },
        "businessId": "ygtGolij4bCKpovFMRF8",
        "customerName": "Preview User",
        "customerEmail": "preview@example.com"
    }
    
    print(f"\nRequest URL: {BASE_URL}/api/ai/chat")
    print(f"Message: '{payload['message']}'")
    print(f"Business ID: {payload['businessId']}")
    print(f"Confidence Threshold: {payload['aiConfig']['confidenceThreshold']}")
    print(f"RAG Enabled: {payload['aiConfig']['ragEnabled']}")
    print("\nSending request...\n")
    
    try:
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=payload, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        print("-" * 80)
        
        if response.status_code == 200:
            result = response.json()
            
            print("\nBACKEND RESPONSE:")
            print(json.dumps(result, indent=2))
            print("\n" + "=" * 80)
            
            print("\nKEY FIELDS:")
            print(f"  success: {result.get('success')}")
            print(f"  confidence: {result.get('confidence')}")
            print(f"  shouldFallbackToHuman: {result.get('shouldFallbackToHuman')}")
            print(f"  sources count: {len(result.get('sources', []))}")
            print(f"  response length: {len(result.get('response', ''))}")
            print(f"  response preview: {result.get('response', '')[:100]}...")
            
            print("\n" + "=" * 80)
            print("CONFIDENCE CHECK:")
            confidence = result.get('confidence', 0)
            threshold = payload['aiConfig']['confidenceThreshold']
            passes = confidence >= threshold
            
            print(f"  Backend Confidence: {confidence} ({confidence * 100:.1f}%)")
            print(f"  Frontend Threshold: {threshold} ({threshold * 100:.1f}%)")
            print(f"  Passes Threshold: {passes}")
            print(f"  Should Show AI Response: {passes and not result.get('shouldFallbackToHuman', True)}")
            
            return True
        else:
            print(f"\nERROR: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to backend. Make sure it's running on port 8001")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    test_widget_preview_api()

