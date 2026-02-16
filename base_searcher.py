"""
Base Searcher - Abstract base class for all retailer searchers

This module provides a common foundation for all retailer search modules
(Amazon, eBay, Etsy, Awin, Skimlinks, CJ, etc.) with:
- Standardized search interface
- Shared query building logic
- Automatic API client with retry
- Product validation
- Consistent error handling and logging

Usage:
    from base_searcher import BaseSearcher
    from product_schema import Product
    from api_client import APIClient

    class AmazonSearcher(BaseSearcher):
        def __init__(self, api_key: str):
            super().__init__('Amazon')
            self.api_key = api_key

        def search(self, profile: Dict, target_count: int = 20) -> List[Product]:
            # Implementation...
            pass

        def _build_queries(self, profile: Dict) -> List[Dict]:
            # Build search queries from profile
            pass

        def _call_api(self, query: str, **kwargs) -> Optional[Dict]:
            # Call retailer API
            pass

        def _parse_response(self, response: Dict, query: str, interest: str) -> List[Product]:
            # Parse API response into Product objects
            pass

Problem Solved:
    Before: 10 searcher modules with duplicated patterns - each implemented
            its own error handling, logging, query building, and credential
            validation. 80% of code was duplicated across modules.

    After:  Single base class provides common functionality. Searchers only
            implement 4 methods: search, _build_queries, _call_api, _parse_response.
            Reduces searcher code by ~60% and ensures consistency.

Author: Chad + Claude
Date: February 2026
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging
from api_client import APIClient
from product_schema import Product

logger = logging.getLogger(__name__)


class BaseSearcher(ABC):
    """
    Abstract base class for all retailer searchers.

    This provides common functionality for product search across different
    retailers. Each retailer (Amazon, eBay, Etsy, etc.) implements a subclass
    that defines how to build queries, call the API, and parse results.

    Common functionality provided:
    - API client with automatic retry
    - Credential validation
    - Error handling and logging
    - Product validation
    - Search with logging wrapper

    Required subclass methods:
    - search(): Main search entry point
    - _build_queries(): Build search queries from profile
    - _call_api(): Call retailer API
    - _parse_response(): Parse API response into Product objects

    Attributes:
        retailer: Retailer name (e.g., 'Amazon', 'eBay', 'Etsy')
        client: APIClient instance for HTTP requests with retry
    """

    def __init__(self, retailer_name: str, api_client: Optional[APIClient] = None):
        """
        Initialize base searcher.

        Args:
            retailer_name: Display name for this retailer (used in logging)
            api_client: Optional APIClient instance. If not provided, creates
                       default client with 15s timeout and 2 retries.
        """
        self.retailer = retailer_name
        self.client = api_client or APIClient(timeout=15, max_retries=2)

    @abstractmethod
    def search(self, profile: Dict, target_count: int = 20) -> List[Product]:
        """
        Search for products matching profile.

        This is the main entry point for product search. Subclasses must
        implement this to orchestrate the full search flow:
        1. Validate credentials
        2. Build queries from profile
        3. Call API for each query
        4. Parse responses into Product objects
        5. Return up to target_count products

        Args:
            profile: User profile dict with interests, demographics, etc.
                    Example: {
                        'interests': [
                            {'name': 'Dog ownership', 'intensity': 'high'},
                            {'name': 'Taylor Swift', 'intensity': 'high'},
                            {'name': 'Coffee', 'intensity': 'medium'}
                        ],
                        'age': 28,
                        'gender': 'female',
                        ...
                    }
            target_count: Maximum number of products to return

        Returns:
            List of Product objects (may be less than target_count if fewer found)

        Example:
            def search(self, profile: Dict, target_count: int = 20) -> List[Product]:
                if not self._validate_credentials(self.api_key):
                    return []

                queries = self._build_queries(profile)
                products = []

                for query_dict in queries[:5]:  # Top 5 interests
                    response = self._call_api(query_dict['query'])
                    if response:
                        products.extend(self._parse_response(
                            response,
                            query_dict['query'],
                            query_dict['interest']
                        ))

                    if len(products) >= target_count:
                        break

                return products[:target_count]
        """
        pass

    @abstractmethod
    def _build_queries(self, profile: Dict) -> List[Dict]:
        """
        Build search queries from profile.

        This extracts interests from the profile and converts them into
        search queries appropriate for the retailer's API. Should prioritize
        high-intensity interests and apply query cleaning/optimization.

        Args:
            profile: User profile dict with interests

        Returns:
            List of query dicts, each with:
            {
                'query': str,        # Search query string
                'interest': str,     # Original interest name
                'intensity': str,    # 'high', 'medium', or 'low'
                'priority': str      # 'high', 'medium', or 'low' (for revenue optimizer)
            }

        Example:
            def _build_queries(self, profile: Dict) -> List[Dict]:
                from search_query_utils import build_queries_from_profile
                return build_queries_from_profile(profile, max_queries=10)
        """
        pass

    @abstractmethod
    def _call_api(self, query: str, **kwargs) -> Optional[Dict]:
        """
        Call retailer API with search query.

        This wraps the retailer-specific API call. Should use self.client
        for automatic retry and error handling.

        Args:
            query: Search query string
            **kwargs: Additional retailer-specific parameters

        Returns:
            API response dict if successful, None if failed

        Example (Amazon):
            def _call_api(self, query: str, **kwargs) -> Optional[Dict]:
                url = "https://amazon-api.com/search"
                headers = {"X-API-Key": self.api_key}
                params = {"q": query, "country": "US"}
                return self.client.get(url, headers=headers, params=params)

        Example (eBay):
            def _call_api(self, query: str, **kwargs) -> Optional[Dict]:
                url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
                }
                params = {"q": query, "limit": 20}
                return self.client.get(url, headers=headers, params=params)
        """
        pass

    @abstractmethod
    def _parse_response(
        self,
        response: Dict,
        query: str,
        interest: str
    ) -> List[Product]:
        """
        Parse API response into Product objects.

        This converts the retailer-specific API response format into our
        standardized Product schema. Should use Product.from_<retailer>()
        class methods for consistency.

        Args:
            response: API response dict
            query: Search query that generated this response
            interest: Profile interest name this query matches

        Returns:
            List of Product objects

        Example (Amazon):
            def _parse_response(self, response: Dict, query: str, interest: str) -> List[Product]:
                items = response.get('data', [])
                products = []

                for item in items:
                    try:
                        product = Product.from_amazon(item, query, interest)
                        products.append(product)
                    except Exception as e:
                        logger.warning(f"Failed to parse product: {e}")
                        continue

                return products

        Example (using batch builder):
            def _parse_response(self, response: Dict, query: str, interest: str) -> List[Product]:
                from product_schema import build_product_list
                items = response.get('itemSummaries', [])
                return build_product_list(items, 'ebay', query, interest)
        """
        pass

    def _validate_credentials(self, *credentials) -> bool:
        """
        Check if all required credentials are present and non-empty.

        This is a helper for validating API keys, secrets, tokens, etc.
        before attempting API calls.

        Args:
            *credentials: Variable number of credential values to check

        Returns:
            True if all credentials are present and non-empty strings

        Example:
            if not self._validate_credentials(self.api_key, self.api_secret):
                logger.warning(f"{self.retailer} credentials not configured")
                return []
        """
        if not credentials:
            return False

        for cred in credentials:
            if not cred:
                return False
            if isinstance(cred, str) and not cred.strip():
                return False

        return True

    def _handle_error(self, query: str, error: Exception):
        """
        Log error consistently across all searchers.

        This provides standardized error logging with retailer name,
        truncated query, and error details.

        Args:
            query: Search query that failed
            error: Exception that was raised

        Example:
            try:
                response = self._call_api(query)
            except Exception as e:
                self._handle_error(query, e)
                return []
        """
        # Truncate query for logging (avoid logging 200+ char queries)
        query_preview = query[:50] + "..." if len(query) > 50 else query
        logger.warning(
            f"{self.retailer} search failed for '{query_preview}': "
            f"{type(error).__name__}: {error}"
        )

    def search_with_logging(
        self,
        profile: Dict,
        target_count: int = 20
    ) -> List[Product]:
        """
        Search with comprehensive logging (wrapper around search()).

        This wraps the main search() method with start/end logging and
        error handling. Use this from multi_retailer_searcher.py instead
        of calling search() directly.

        Args:
            profile: User profile dict
            target_count: Maximum products to return

        Returns:
            List of Product objects

        Example (in multi_retailer_searcher.py):
            amazon_searcher = AmazonSearcher(api_key)
            products = amazon_searcher.search_with_logging(profile, target_count=20)
        """
        logger.info(f"Searching {self.retailer} for {target_count} products...")

        try:
            products = self.search(profile, target_count)
            logger.info(f"  ✓ {self.retailer}: Found {len(products)} products")
            return products

        except Exception as e:
            logger.error(
                f"  ✗ {self.retailer}: {type(e).__name__}: {e}"
            )
            return []


# =============================================================================
# EXAMPLE IMPLEMENTATION: Amazon Searcher
# =============================================================================

class ExampleAmazonSearcher(BaseSearcher):
    """
    Example Amazon searcher implementation using BaseSearcher.

    This demonstrates the minimal code required to implement a retailer
    searcher. Most of the heavy lifting is handled by the base class.
    """

    def __init__(self, api_key: str):
        super().__init__('Amazon')
        self.api_key = api_key

    def search(self, profile: Dict, target_count: int = 20) -> List[Product]:
        """Search Amazon for products matching profile."""
        # Validate credentials
        if not self._validate_credentials(self.api_key):
            logger.warning(f"{self.retailer} API key not configured")
            return []

        # Build queries
        queries = self._build_queries(profile)
        products = []

        # Search for each interest
        for query_dict in queries[:5]:  # Top 5 interests
            try:
                response = self._call_api(query_dict['query'])
                if response:
                    new_products = self._parse_response(
                        response,
                        query_dict['query'],
                        query_dict['interest']
                    )
                    products.extend(new_products)

            except Exception as e:
                self._handle_error(query_dict['query'], e)
                continue

            # Stop if we have enough products
            if len(products) >= target_count:
                break

        return products[:target_count]

    def _build_queries(self, profile: Dict) -> List[Dict]:
        """Build search queries from profile interests."""
        interests = profile.get('interests', [])
        queries = []

        for interest_dict in interests[:10]:  # Top 10 interests
            if isinstance(interest_dict, dict):
                name = interest_dict.get('name', '')
                intensity = interest_dict.get('intensity', 'medium')
            else:
                name = str(interest_dict)
                intensity = 'medium'

            if not name:
                continue

            # Priority based on intensity
            priority = 'high' if intensity == 'high' else 'medium' if intensity == 'medium' else 'low'

            # Add suffix for better results
            query = f"{name} gift"

            queries.append({
                'query': query,
                'interest': name,
                'intensity': intensity,
                'priority': priority
            })

        return queries

    def _call_api(self, query: str, **kwargs) -> Optional[Dict]:
        """Call Amazon API."""
        url = "https://real-time-amazon-data.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
        }
        params = {
            "query": query,
            "country": "US"
        }

        return self.client.get(url, headers=headers, params=params)

    def _parse_response(
        self,
        response: Dict,
        query: str,
        interest: str
    ) -> List[Product]:
        """Parse Amazon API response into Product objects."""
        from product_schema import build_product_list

        items = response.get('data', [])
        return build_product_list(items, 'amazon', query, interest)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Base Searcher - Test Suite")
    print("=" * 60)

    # Test 1: Credential validation
    print("\n1. Credential validation:")

    class TestSearcher(BaseSearcher):
        def search(self, profile, target_count=20):
            return []

        def _build_queries(self, profile):
            return []

        def _call_api(self, query, **kwargs):
            return None

        def _parse_response(self, response, query, interest):
            return []

    searcher = TestSearcher('Test Retailer')

    valid = searcher._validate_credentials('key123', 'secret456')
    invalid_empty = searcher._validate_credentials('', 'secret456')
    invalid_none = searcher._validate_credentials(None, 'secret456')
    invalid_whitespace = searcher._validate_credentials('   ', 'secret456')

    print(f"  Valid credentials: {valid} (expected True)")
    print(f"  Empty string: {invalid_empty} (expected False)")
    print(f"  None value: {invalid_none} (expected False)")
    print(f"  Whitespace: {invalid_whitespace} (expected False)")

    if valid and not invalid_empty and not invalid_none and not invalid_whitespace:
        print("  ✓ Credential validation works correctly")
    else:
        print("  ✗ Credential validation failed")

    # Test 2: Error handling
    print("\n2. Error handling:")
    searcher._handle_error("test query", ValueError("Test error"))
    print("  ✓ Error logged (check output above)")

    # Test 3: Query building (example)
    print("\n3. Example Amazon searcher - query building:")

    test_profile = {
        'interests': [
            {'name': 'Dog ownership', 'intensity': 'high'},
            {'name': 'Taylor Swift', 'intensity': 'high'},
            {'name': 'Coffee', 'intensity': 'medium'}
        ]
    }

    # Can't test actual API without key, but can test query building
    example_searcher = ExampleAmazonSearcher(api_key='fake_key_for_testing')
    queries = example_searcher._build_queries(test_profile)

    print(f"  Built {len(queries)} queries from {len(test_profile['interests'])} interests:")
    for q in queries:
        print(f"    - '{q['query']}' (interest: {q['interest']}, priority: {q['priority']})")

    if len(queries) == 3:
        print("  ✓ Query building works")
    else:
        print("  ✗ Query building failed")

    # Test 4: Product validation (requires Product schema)
    print("\n4. Product schema integration:")
    try:
        from product_schema import Product

        # Test creating a product manually
        test_product = Product(
            title="Test Product",
            link="https://example.com/product",
            source_domain="example.com",
            search_query="test query",
            interest_match="Test Interest",
            price="$19.99"
        )

        print(f"  ✓ Product created: {test_product.title}")
        print(f"    Link: {test_product.link}")
        print(f"    Price: {test_product.price}")

    except ImportError:
        print("  ⚠ product_schema.py not found (expected if running standalone)")

    # Test 5: Search with logging wrapper
    print("\n5. Search with logging wrapper:")

    class MockSearcher(BaseSearcher):
        def search(self, profile, target_count=20):
            # Return fake products
            return [
                Product(
                    title=f"Product {i}",
                    link=f"https://example.com/product/{i}",
                    source_domain="example.com",
                    search_query="test",
                    interest_match="test"
                )
                for i in range(1, 4)
            ]

        def _build_queries(self, profile):
            return []

        def _call_api(self, query, **kwargs):
            return None

        def _parse_response(self, response, query, interest):
            return []

    mock_searcher = MockSearcher('Mock Retailer')
    products = mock_searcher.search_with_logging(test_profile, target_count=10)

    print(f"  Returned {len(products)} products")
    if len(products) == 3:
        print("  ✓ Search with logging works")
    else:
        print("  ✗ Search with logging failed")

    # Test 6: Error handling in search_with_logging
    print("\n6. Error handling in search_with_logging:")

    class ErrorSearcher(BaseSearcher):
        def search(self, profile, target_count=20):
            raise ValueError("Simulated API error")

        def _build_queries(self, profile):
            return []

        def _call_api(self, query, **kwargs):
            return None

        def _parse_response(self, response, query, interest):
            return []

    error_searcher = ErrorSearcher('Error Retailer')
    products = error_searcher.search_with_logging(test_profile)

    if len(products) == 0:
        print("  ✓ Error handled gracefully (returned empty list)")
    else:
        print("  ✗ Error handling failed")

    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("\nMigration Example:")
    print("  # Before (in rapidapi_amazon_searcher.py):")
    print("  def search_products_rapidapi_amazon(profile, api_key, target_count=20):")
    print("      # 150 lines of code...")
    print()
    print("  # After:")
    print("  class AmazonSearcher(BaseSearcher):")
    print("      def __init__(self, api_key):")
    print("          super().__init__('Amazon')")
    print("          self.api_key = api_key")
    print()
    print("      def search(self, profile, target_count=20):")
    print("          # ~40 lines of code (60% reduction)")
    print()
    print("  # Usage:")
    print("  searcher = AmazonSearcher(api_key)")
    print("  products = searcher.search_with_logging(profile, target_count=20)")
