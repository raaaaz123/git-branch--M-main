#!/usr/bin/env python3
"""
Test script for AI chat functionality with detailed logging
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_ai_chat_with_rag():
    """Test AI chat with RAG using actual widget data"""
    print("🔍 Testing AI chat with RAG...")
    print("=" * 80)
    
    # Test with Make My Flyer question
    test_chat = {
        "message": "what's make my flyer",
        "widgetId": "6k4PxwgXvafUQ7Gj7WUf",
        "conversationId": "test-conversation-123",
        "businessId": "ygtGolij4bCKpovFMRF8",
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
        "customerName": "Test Customer",
        "customerEmail": "customer@example.com"
    }
    
    print("📤 Request Data:")
    print(json.dumps(test_chat, indent=2))
    print("\n" + "=" * 80)
    
    try:
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=test_chat, timeout=30)
        print(f"\n✅ Response Status: {response.status_code}")
        print("=" * 80)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n📊 AI Response Results:")
            print("-" * 80)
            print(f"Success: {result.get('success')}")
            print(f"Confidence: {result.get('confidence')}")
            print(f"Sources Found: {len(result.get('sources', []))}")
            print(f"Should Fallback: {result.get('shouldFallbackToHuman')}")
            print(f"Mode: {result.get('metadata', {}).get('mode')}")
            print(f"\nAI Response Text:")
            print("-" * 80)
            print(result.get('response'))
            print("-" * 80)
            
            if result.get('sources'):
                print(f"\n📚 Sources ({len(result['sources'])}):")
                print("-" * 80)
                for i, source in enumerate(result['sources'], 1):
                    print(f"\nSource {i}:")
                    print(f"  Title: {source.get('title')}")
                    print(f"  Type: {source.get('type')}")
                    print(f"  Score: {source.get('score')}")
                    print(f"  Content Preview: {source.get('content')[:100]}...")
            
            print("\n" + "=" * 80)
            
            # Analysis
            print("\n🔍 Analysis:")
            print("-" * 80)
            if not result.get('success'):
                print("❌ AI request failed!")
            elif len(result.get('sources', [])) == 0:
                print("⚠️  No sources found in Pinecone - check businessId and data")
            elif result.get('confidence', 0) < 0.6:
                print(f"⚠️  Confidence {result.get('confidence')} is below threshold 0.6")
                print("   Check if AI response contains uncertainty phrases")
            elif result.get('shouldFallbackToHuman'):
                print("⚠️  Fallback triggered even with good confidence")
                print("   Check confidence calculation logic")
            else:
                print("✅ Everything looks good!")
            
            return result
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - OpenRouter might be slow")
        return None
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return None

def test_simple_query():
    """Test with a simple greeting"""
    print("\n\n🔍 Testing simple query (hi)...")
    print("=" * 80)
    
    test_chat = {
        "message": "hi",
        "widgetId": "6k4PxwgXvafUQ7Gj7WUf",
        "conversationId": "test-conversation-456",
        "businessId": "ygtGolij4bCKpovFMRF8",
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
        "customerName": "Test Customer",
        "customerEmail": "customer@example.com"
    }
    
    print("📤 Request: 'hi'")
    print("=" * 80)
    
    try:
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=test_chat, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success: {result.get('success')}")
            print(f"Confidence: {result.get('confidence')}")
            print(f"Response: {result.get('response')}")
            print(f"Should Fallback: {result.get('shouldFallbackToHuman')}")
            return result
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None

def main():
    """Run AI chat tests"""
    print("Starting AI Chat Tests")
    print("=" * 80)
    print("This will test the AI chat functionality with actual widget data")
    print("Make sure the backend is running on http://localhost:8001")
    print("=" * 80 + "\n")
    
    try:
        # Test 1: Make My Flyer question
        result1 = test_ai_chat_with_rag()
        
        # Test 2: Simple greeting
        result2 = test_simple_query()
        
        print("\n" + "=" * 80)
        print("✅ Tests completed!")
        print("=" * 80)
        
        # Summary
        print("\n📋 Summary:")
        print("-" * 80)
        if result1:
            print(f"Test 1 (Make My Flyer): Confidence={result1.get('confidence')}, Sources={len(result1.get('sources', []))}")
        if result2:
            print(f"Test 2 (Hi): Confidence={result2.get('confidence')}, Sources={len(result2.get('sources', []))}")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to the API server.")
        print("   Make sure the backend is running on http://localhost:8001")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()

