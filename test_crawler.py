"""
Test Production Web Crawler
"""
import requests
import json

BACKEND_URL = "http://localhost:8001"

def test_url_crawl():
    """Test URL-based crawling"""
    print("\n" + "="*80)
    print("TEST 1: URL CRAWLING")
    print("="*80 + "\n")
    
    request_data = {
        "url": "https://example.com",
        "widget_id": "test-widget-123",
        "title": "Example Website",
        "max_pages": 10,
        "max_depth": 2,
        "is_sitemap": False,
        "metadata": {
            "business_id": "test-business-123"
        }
    }
    
    print(f"Crawling: {request_data['url']}")
    print(f"Method: URL Crawling")
    print(f"Max Pages: {request_data['max_pages']}\n")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/crawler/crawl-website",
            json=request_data,
            timeout=120
        )
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            print(">> SUCCESS!")
            print(f"   Method Used: {data['data']['crawl_method']}")
            print(f"   Pages Crawled: {data['data']['total_pages']}")
            print(f"   Words: {data['data']['total_word_count']:,}")
            print(f"   Chunks Created: {data['data']['chunks_created']}")
            print(f"   Time: {data['data']['elapsed_time']:.1f}s")
            return True
        else:
            print(f">> ERROR: {response.text}")
            return False
    except Exception as e:
        print(f">> ERROR: {str(e)}")
        return False


def test_sitemap_crawl():
    """Test sitemap-based crawling"""
    print("\n" + "="*80)
    print("TEST 2: SITEMAP CRAWLING")
    print("="*80 + "\n")
    
    request_data = {
        "url": "https://www.example.com/sitemap.xml",
        "widget_id": "test-widget-456",
        "title": "Example Sitemap",
        "max_pages": 20,
        "is_sitemap": True,
        "metadata": {
            "business_id": "test-business-456"
        }
    }
    
    print(f"Crawling: {request_data['url']}")
    print(f"Method: Sitemap")
    print(f"Max Pages: {request_data['max_pages']}\n")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/crawler/crawl-website",
            json=request_data,
            timeout=120
        )
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            print(">> SUCCESS!")
            print(f"   Method Used: {data['data']['crawl_method']}")
            print(f"   Pages Crawled: {data['data']['total_pages']}")
            print(f"   Words: {data['data']['total_word_count']:,}")
            print(f"   Chunks Created: {data['data']['chunks_created']}")
            print(f"   Time: {data['data']['elapsed_time']:.1f}s")
            return True
        else:
            print(f">> ERROR: {response.text}")
            return False
    except Exception as e:
        print(f">> ERROR: {str(e)}")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PRODUCTION WEB CRAWLER TEST SUITE")
    print("="*80)
    print("\nMake sure backend is running on http://localhost:8001\n")
    
    # Run tests
    results = []
    results.append(("URL Crawling", test_url_crawl()))
    # Uncomment to test sitemap (if you have a valid sitemap URL)
    # results.append(("Sitemap Crawling", test_sitemap_crawl()))
    
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

