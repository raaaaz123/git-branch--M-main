"""
Test FAQ storage functionality
"""
import requests
import json

BACKEND_URL = "http://localhost:8001"

def test_faq_storage():
    """Test FAQ storage to Pinecone and Firestore"""
    print("\n" + "="*80)
    print("TEST: FAQ STORAGE")
    print("="*80 + "\n")
    
    # Test FAQ data
    faq_data = {
        "widget_id": "test-widget-faq-123",
        "title": "Return Policy Question",
        "question": "What is your return policy?",
        "answer": "Our return policy allows returns within 30 days of purchase. Items must be in original condition with tags attached. Refunds are processed within 5-7 business days after we receive the returned item.",
        "type": "faq",
        "metadata": {
            "business_id": "test-business-123",
            "tags": ["returns", "policy", "customer-service"]
        }
    }
    
    print(f"Question: {faq_data['question']}")
    print(f"Answer Length: {len(faq_data['answer'])} chars")
    print(f"Tags: {faq_data['metadata']['tags']}")
    print()
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/knowledge-base/store-faq",
            json=faq_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS!")
            print(f"   FAQ ID: {data['data']['faq_id']}")
            print(f"   Vector ID: {data['data']['vector_id']}")
            print(f"   Question: {data['data']['question']}")
            print(f"   Answer Length: {len(data['data']['answer'])} chars")
            print(f"   Word Count: {data['data']['word_count']}")
            print(f"   Chunks Created: {data['data']['chunks_created']}")
            print(f"   Firestore Stored: {data['data']['firestore_stored']}")
            return True
        else:
            print(f"ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False


def test_multiple_faqs():
    """Test storing multiple FAQs"""
    print("\n" + "="*80)
    print("TEST: MULTIPLE FAQs")
    print("="*80 + "\n")
    
    faqs = [
        {
            "question": "What payment methods do you accept?",
            "answer": "We accept all major credit cards (Visa, MasterCard, American Express), PayPal, and Apple Pay."
        },
        {
            "question": "How long does shipping take?",
            "answer": "Standard shipping takes 5-7 business days. Express shipping is available and takes 2-3 business days."
        },
        {
            "question": "Do you ship internationally?",
            "answer": "Yes, we ship to over 50 countries worldwide. International shipping times vary by location, typically 10-15 business days."
        }
    ]
    
    success_count = 0
    
    for i, faq in enumerate(faqs, 1):
        print(f"Storing FAQ {i}/{len(faqs)}: {faq['question'][:50]}...")
        
        faq_data = {
            "widget_id": "test-widget-faq-456",
            "title": faq['question'][:50],
            "question": faq['question'],
            "answer": faq['answer'],
            "type": "faq",
            "metadata": {
                "business_id": "test-business-456",
                "tags": ["faq"]
            }
        }
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/knowledge-base/store-faq",
                json=faq_data,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"   SUCCESS - ID: {response.json()['data']['faq_id']}")
                success_count += 1
            else:
                print(f"   FAILED: {response.status_code}")
        except Exception as e:
            print(f"   ERROR: {str(e)}")
    
    print(f"\nTotal Success: {success_count}/{len(faqs)}")
    return success_count == len(faqs)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FAQ STORAGE TEST SUITE")
    print("="*80)
    print("\nMake sure backend is running on http://localhost:8001\n")
    
    # Run tests
    results = []
    results.append(("Single FAQ Storage", test_faq_storage()))
    results.append(("Multiple FAQs Storage", test_multiple_faqs()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        icon = ">>" if passed else "XX"
        print(f"{icon} {test_name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

