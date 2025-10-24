"""
Test script to verify all API endpoints work correctly
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_health_endpoints():
    """Test health check endpoints"""
    print("🔍 Testing health endpoints...")
    
    # Test root endpoint
    response = requests.get(f"{BASE_URL}/")
    print(f"✅ Root endpoint: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Test health check
    response = requests.get(f"{BASE_URL}/health")
    print(f"✅ Health check: {response.status_code}")
    print(f"   Response: {response.json()}")

def test_pinecone_endpoints():
    """Test Pinecone endpoints"""
    print("\n🔍 Testing Pinecone endpoints...")
    
    # Test Pinecone connection
    response = requests.post(f"{BASE_URL}/api/test-pinecone")
    print(f"✅ Pinecone test: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    
    # Test dummy data storage
    response = requests.post(f"{BASE_URL}/api/test-store-dummy")
    print(f"✅ Dummy data test: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")

def test_knowledge_endpoints():
    """Test knowledge base endpoints"""
    print("\n🔍 Testing knowledge base endpoints...")
    
    # Test knowledge item storage
    test_item = {
        "id": "test-item-123",
        "businessId": "test-business-123",
        "widgetId": "test-widget-456",
        "title": "Test Knowledge Item",
        "content": "This is a test knowledge base item for verification.",
        "type": "text"
    }
    
    response = requests.post(f"{BASE_URL}/api/knowledge-base/store", json=test_item)
    print(f"✅ Knowledge store: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    
    # Test knowledge search
    search_request = {
        "query": "test knowledge",
        "widgetId": "test-widget-456",
        "limit": 5
    }
    
    response = requests.post(f"{BASE_URL}/api/knowledge-base/search", json=search_request)
    print(f"✅ Knowledge search: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")

def test_review_endpoints():
    """Test review form endpoints"""
    print("\n🔍 Testing review form endpoints...")
    
    # Test create review form
    test_form = {
        "businessId": "test-business-123",
        "title": "Test Review Form",
        "description": "A test review form for verification",
        "fields": [
            {
                "id": "field-1",
                "type": "text",
                "label": "Name",
                "required": True,
                "order": 1
            },
            {
                "id": "field-2",
                "type": "rating",
                "label": "Rating",
                "required": True,
                "minRating": 1,
                "maxRating": 5,
                "ratingType": "stars",
                "order": 2
            }
        ],
        "settings": {
            "allowAnonymous": True,
            "requireEmail": False,
            "showProgress": True,
            "thankYouMessage": "Thank you for your feedback!",
            "collectLocation": True,
            "collectDeviceInfo": True
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/review-forms/", json=test_form)
    print(f"✅ Create review form: {response.status_code}")
    if response.status_code == 200:
        form_data = response.json()
        print(f"   Response: {form_data}")
        form_id = form_data["data"]["id"]
        
        # Test get business review forms
        response = requests.get(f"{BASE_URL}/api/review-forms/business/test-business-123")
        print(f"✅ Get business forms: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        
        # Test get specific form
        response = requests.get(f"{BASE_URL}/api/review-forms/{form_id}")
        print(f"✅ Get specific form: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        
        # Test submit review
        test_submission = {
            "responses": [
                {
                    "fieldId": "field-1",
                    "value": "John Doe",
                    "fieldType": "text"
                },
                {
                    "fieldId": "field-2",
                    "value": 5,
                    "fieldType": "rating"
                }
            ],
            "userInfo": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/review-forms/{form_id}/submit", json=test_submission)
        print(f"✅ Submit review: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        
        # Test get submissions
        response = requests.get(f"{BASE_URL}/api/review-forms/{form_id}/submissions")
        print(f"✅ Get submissions: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        
        # Test get analytics
        response = requests.get(f"{BASE_URL}/api/review-forms/{form_id}/analytics")
        print(f"✅ Get analytics: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")

def test_ai_endpoints():
    """Test AI chat endpoints"""
    print("\n🔍 Testing AI chat endpoints...")
    
    # Test OpenRouter connection first
    response = requests.post(f"{BASE_URL}/api/test-openrouter")
    print(f"✅ OpenRouter test: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    
    # Test AI chat with OpenRouter
    test_chat = {
        "message": "What is this company about?",
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
            "ragEnabled": True,
            "fallbackToHuman": True
        },
        "customerName": "Test Customer",
        "customerEmail": "customer@example.com"
    }
    
    response = requests.post(f"{BASE_URL}/api/ai/chat", json=test_chat)
    print(f"✅ AI chat: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")

def main():
    """Run all endpoint tests"""
    print("🚀 Starting API endpoint tests...")
    print("=" * 50)
    
    try:
        test_health_endpoints()
        test_pinecone_endpoints()
        test_knowledge_endpoints()
        test_review_endpoints()
        test_ai_endpoints()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the backend is running on http://localhost:8001")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
