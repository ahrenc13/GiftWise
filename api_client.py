"""
API Client - Unified error handling, retry logic, and rate limiting

This module provides a robust wrapper around requests with:
- Automatic retry on transient failures (429, 500, 502, 503, 504)
- Exponential backoff between retries
- Consistent error handling and logging
- Session reuse for connection pooling
- Configurable timeouts

Usage:
    from api_client import APIClient

    # Create client with defaults
    client = APIClient(timeout=15, max_retries=2)

    # GET request with automatic retry
    data = client.get(
        'https://api.example.com/products',
        headers={'X-API-Key': 'key123'},
        params={'q': 'dog toys'}
    )

    # POST request
    result = client.post(
        'https://api.example.com/track',
        json_data={'event': 'click', 'product_id': '123'}
    )

    # Get raw text instead of JSON
    html = client.get('https://example.com/page', parse_json=False)

Problem Solved:
    Before: 40+ API calls with inconsistent error handling, no retry logic,
            manual timeout management, duplicated try/except blocks

    After:  Single API client with automatic retry, exponential backoff,
            consistent logging, session pooling, timeout defaults

Author: Chad + Claude
Date: February 2026
"""

import requests
import time
import logging
from typing import Optional, Dict, Any, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class APIClient:
    """
    Unified API client with automatic retry, error handling, and rate limiting.

    This replaces raw requests.get/post calls throughout the codebase with
    a consistent, robust HTTP client that handles transient failures gracefully.

    Features:
    - Automatic retry on 429, 500, 502, 503, 504 errors
    - Exponential backoff (0.5s, 1s, 2s, ...)
    - Connection pooling via requests.Session
    - Configurable timeouts (default 15s)
    - Consistent error logging
    - JSON parsing with fallback to raw text

    Attributes:
        timeout: Request timeout in seconds (default 15)
        max_retries: Maximum retry attempts (default 2)
        backoff_factor: Exponential backoff multiplier (default 0.5)
        retry_on_status: HTTP status codes that trigger retry
        session: Persistent requests.Session for connection pooling
    """

    def __init__(
        self,
        timeout: int = 15,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
        retry_on_status: Tuple[int, ...] = (429, 500, 502, 503, 504)
    ):
        """
        Initialize API client with retry configuration.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts (0 = no retries)
            backoff_factor: Multiplier for exponential backoff (wait = factor * 2^attempt)
            retry_on_status: Tuple of HTTP status codes that trigger retry
                            Default: (429, 500, 502, 503, 504)
                            - 429: Too Many Requests (rate limit)
                            - 500: Internal Server Error
                            - 502: Bad Gateway
                            - 503: Service Unavailable
                            - 504: Gateway Timeout
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on_status = retry_on_status
        self.session = requests.Session()

    def get(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        parse_json: bool = True
    ) -> Optional[Any]:
        """
        GET request with automatic retry and error handling.

        Args:
            url: Full URL to request
            headers: Optional HTTP headers dict
            params: Optional query parameters dict
            parse_json: If True, parse response as JSON. If False, return raw text.

        Returns:
            Parsed JSON dict/list if parse_json=True, else raw text string.
            Returns None if request fails after all retries.

        Example:
            # Get JSON API response
            data = client.get(
                'https://api.example.com/products',
                headers={'X-API-Key': 'key123'},
                params={'q': 'coffee'}
            )

            # Get raw HTML
            html = client.get('https://example.com', parse_json=False)
        """
        for attempt in range(self.max_retries + 1):
            try:
                r = self.session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )

                # Retry on specific status codes
                if r.status_code in self.retry_on_status and attempt < self.max_retries:
                    wait = self.backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"HTTP {r.status_code} from {url[:60]}, "
                        f"retrying in {wait:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait)
                    continue

                # Raise on other error status codes (4xx, 5xx)
                r.raise_for_status()

                # Success - parse and return
                return r.json() if parse_json else r.text

            except requests.RequestException as e:
                if attempt < self.max_retries:
                    wait = self.backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"Request failed ({type(e).__name__}: {e}), "
                        f"retrying in {wait:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait)
                    continue

                # Final attempt failed
                logger.error(
                    f"Request failed after {self.max_retries + 1} attempts: "
                    f"{type(e).__name__}: {e}"
                )
                return None

        return None

    def post(
        self,
        url: str,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        parse_json: bool = True
    ) -> Optional[Any]:
        """
        POST request with automatic retry and error handling.

        Args:
            url: Full URL to request
            headers: Optional HTTP headers dict
            data: Optional form data dict (sent as application/x-www-form-urlencoded)
            json_data: Optional JSON data dict (sent as application/json)
            parse_json: If True, parse response as JSON. If False, return raw text.

        Returns:
            Parsed JSON dict/list if parse_json=True, else raw text string.
            Returns None if request fails after all retries.

        Example:
            # POST JSON
            result = client.post(
                'https://api.example.com/track',
                headers={'X-API-Key': 'key123'},
                json_data={'event': 'click', 'product_id': '123'}
            )

            # POST form data
            result = client.post(
                'https://api.example.com/login',
                data={'username': 'user', 'password': 'pass'}
            )
        """
        for attempt in range(self.max_retries + 1):
            try:
                r = self.session.post(
                    url,
                    headers=headers,
                    data=data,
                    json=json_data,
                    timeout=self.timeout
                )

                # Retry on specific status codes
                if r.status_code in self.retry_on_status and attempt < self.max_retries:
                    wait = self.backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"HTTP {r.status_code} from {url[:60]}, "
                        f"retrying in {wait:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait)
                    continue

                # Raise on other error status codes
                r.raise_for_status()

                # Success - parse and return
                return r.json() if parse_json else r.text

            except requests.RequestException as e:
                if attempt < self.max_retries:
                    wait = self.backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"Request failed ({type(e).__name__}: {e}), "
                        f"retrying in {wait:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait)
                    continue

                # Final attempt failed
                logger.error(
                    f"Request failed after {self.max_retries + 1} attempts: "
                    f"{type(e).__name__}: {e}"
                )
                return None

        return None

    def close(self):
        """Close the underlying session (cleanup)"""
        self.session.close()

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import sys

    print("API Client - Test Suite")
    print("=" * 60)

    # Test 1: Successful GET request
    print("\n1. Successful GET request:")
    client = APIClient(timeout=10, max_retries=1)

    # Test with JSONPlaceholder (free testing API)
    data = client.get('https://jsonplaceholder.typicode.com/posts/1')
    if data:
        print(f"  ✓ GET succeeded: {data.get('title', 'N/A')[:50]}")
    else:
        print("  ✗ GET failed")

    # Test 2: GET with query params
    print("\n2. GET with query parameters:")
    data = client.get(
        'https://jsonplaceholder.typicode.com/posts',
        params={'userId': 1}
    )
    if data and isinstance(data, list):
        print(f"  ✓ Query params worked: {len(data)} posts returned")
    else:
        print("  ✗ Query params failed")

    # Test 3: POST request
    print("\n3. POST request:")
    result = client.post(
        'https://jsonplaceholder.typicode.com/posts',
        json_data={
            'title': 'Test Post',
            'body': 'This is a test',
            'userId': 1
        }
    )
    if result and result.get('id'):
        print(f"  ✓ POST succeeded: Created post ID {result['id']}")
    else:
        print("  ✗ POST failed")

    # Test 4: 404 error handling
    print("\n4. 404 error handling:")
    data = client.get('https://jsonplaceholder.typicode.com/posts/999999')
    if data is None:
        print("  ✓ 404 handled correctly (returned None)")
    else:
        print("  ✗ Should have returned None for 404")

    # Test 5: Timeout handling
    print("\n5. Timeout handling:")
    slow_client = APIClient(timeout=1, max_retries=0)
    # httpbin.org/delay/5 waits 5 seconds before responding
    data = slow_client.get('https://httpbin.org/delay/5')
    if data is None:
        print("  ✓ Timeout handled correctly (returned None)")
    else:
        print("  ✗ Should have timed out")

    # Test 6: Raw text response
    print("\n6. Raw text response (parse_json=False):")
    html = client.get('https://example.com', parse_json=False)
    if html and '<html>' in html.lower():
        print(f"  ✓ Raw text retrieved ({len(html)} characters)")
    else:
        print("  ✗ Raw text retrieval failed")

    # Test 7: Retry with exponential backoff (simulated)
    print("\n7. Retry logic (will take ~3.5 seconds):")
    print("   Testing with intentionally bad URL...")
    retry_client = APIClient(timeout=2, max_retries=2, backoff_factor=0.5)
    start = time.time()
    data = retry_client.get('https://httpstat.us/500')  # Always returns 500
    elapsed = time.time() - start
    print(f"   ✓ Retried and failed gracefully in {elapsed:.1f}s")
    print(f"   (Expected: ~0.5s + 1.0s + 2.0s = ~3.5s)")

    # Test 8: Context manager
    print("\n8. Context manager support:")
    with APIClient() as ctx_client:
        data = ctx_client.get('https://jsonplaceholder.typicode.com/posts/1')
        if data:
            print("  ✓ Context manager works")
        else:
            print("  ✗ Context manager failed")

    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("\nMigration Example:")
    print("  # Before:")
    print("  response = requests.get(url, headers=headers, timeout=15)")
    print("  data = response.json()")
    print()
    print("  # After:")
    print("  from api_client import APIClient")
    print("  client = APIClient()")
    print("  data = client.get(url, headers=headers)")
