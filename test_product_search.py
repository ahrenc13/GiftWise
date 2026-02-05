"""
Quick test for product search - run: python test_product_search.py
Use this to see the real error if generation crashes.
"""
import os
import sys

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    serpapi_key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if not serpapi_key:
        print("Set SERPAPI_API_KEY in .env or environment, then run again.")
        sys.exit(1)
    
    profile = {
        "interests": [
            {"name": "coffee", "intensity": "moderate", "type": "current"}
        ]
    }
    
    print("Calling search_real_products (validate_realtime=False)...")
    try:
        from product_searcher import search_real_products
        products = search_real_products(
            profile,
            serpapi_key,
            rec_count=10,
            validate_realtime=False
        )
        print(f"Got {len(products)} products")
        for i, p in enumerate(products[:3]):
            print(f"  [{i+1}] {p.get('title', '')[:50]}... | {p.get('link', '')[:60]}...")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
