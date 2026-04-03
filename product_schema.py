"""
Product Schema - Standardized product representation across all retailers

This module provides a unified Product dataclass and builder functions to
eliminate inconsistent product dict construction across 7+ searcher modules.

Every retailer (Amazon, eBay, Etsy, Awin, Skimlinks, CJ) has different API
response formats. This module normalizes them into a single schema with
validation and type safety.

Usage:
    from product_schema import Product, build_product_list

    # Create from Amazon API response
    product = Product.from_amazon(api_item, query="dog toy", interest="Dog")

    # Create from eBay API response
    product = Product.from_ebay(api_item, query="hiking gear", interest="Hiking")

    # Convert to dict for curator (backward compatible)
    product_dict = product.to_dict()

    # Batch building
    products = build_product_list(api_items, platform='amazon',
                                  query='coffee', interest='Coffee')

Migration from old pattern:
    # Before (in rapidapi_amazon_searcher.py lines 210-223):
    product = {
        "title": title[:200],
        "link": link,
        "snippet": title[:100],
        "image": image,
        "thumbnail": image,
        "image_url": image,
        "source_domain": "amazon.com",
        "search_query": query,
        "interest_match": interest,
        "priority": priority,
        "price": price or "",
        "product_id": asin or str(hash(title + link))[:16],
    }
    all_products.append(product)

    # After (replace entire product dict building with):
    from product_schema import Product

    try:
        product = Product.from_amazon(item, query, interest)
        # Priority is auto-detected from interest intensity in build_queries_from_profile
        # Or override: product.priority = priority
        all_products.append(product.to_dict())
    except Exception as e:
        logger.warning(f"Failed to build product: {e}")
        continue

    # Or use batch builder:
    from product_schema import build_product_list

    products = build_product_list(products_list, 'amazon', query, interest)
    all_products.extend([p.to_dict() for p in products])

Author: Chad + Claude
Date: February 2026
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import hashlib
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# COMMISSION RATES (Revenue Optimization)
# =============================================================================

# Commission rates by retailer (used by revenue_optimizer.py)
COMMISSION_RATES = {
    'amazon': 0.02,      # 2% - lowest but highest conversion
    'ebay': 0.03,        # 3% - broad inventory
    'etsy': 0.04,        # 4% - unique items, higher commission
    'awin': 0.05,        # 5% - varies by advertiser, using conservative avg
    'shareasale': 0.05,  # 5% - legacy, migrated to Awin
    'cj': 0.06,          # 6% - varies by brand, often higher than others
    'default': 0.02,     # Fallback
}


# =============================================================================
# PRODUCT SCHEMA
# =============================================================================

@dataclass
class Product:
    """
    Standardized product schema for all retailers.

    This is the single source of truth for product representation.
    All searcher modules build instances of this class, ensuring
    consistency and type safety.

    Fields:
        Required:
            - title: Product name (max 200 chars, auto-truncated)
            - link: Product URL (affiliate link if available)
            - source_domain: Retailer domain (e.g., 'amazon.com', 'etsy.com')
            - search_query: Query that found this product
            - interest_match: Profile interest this product matches

        Optional:
            - snippet: Product description (max 500 chars)
            - image: Primary image URL
            - thumbnail: Thumbnail image URL (fallback to image if missing)
            - image_url: Legacy field (fallback to image if missing)
            - price: Price string (e.g., "$24.99", "24.99")
            - product_id: Retailer-specific ID (ASIN, listing_id, etc.)
            - priority: 'low', 'medium', 'high' (based on interest intensity)
            - commission_rate: Expected commission (0.0-1.0)
            - metadata: Retailer-specific extra data (not passed to curator)
    """

    # Required fields
    title: str
    link: str
    source_domain: str
    search_query: str
    interest_match: str

    # Optional fields with defaults
    snippet: str = ""
    image: str = ""
    thumbnail: str = ""
    image_url: str = ""
    price: str = ""
    product_id: str = ""
    priority: str = "medium"
    commission_rate: float = 0.02  # Default 2%

    # Retailer-specific metadata (not passed to curator)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """
        Validate and normalize after creation.

        - Trims title to 200 chars
        - Trims snippet to 500 chars
        - Ensures all image fields are populated
        - Generates product_id if missing
        - Validates commission_rate range
        """
        # Trim title
        if len(self.title) > 200:
            original_title = self.title
            self.title = self.title[:200].strip()
            logger.debug(f"Truncated title: '{original_title}' → '{self.title}'")

        # Trim snippet
        if len(self.snippet) > 500:
            self.snippet = self.snippet[:500].strip()

        # Ensure all image fields populated (backward compatibility)
        if not self.thumbnail and self.image:
            self.thumbnail = self.image
        if not self.image_url and self.image:
            self.image_url = self.image

        # Reverse: if only image_url is set, populate others
        if self.image_url and not self.image:
            self.image = self.image_url
            self.thumbnail = self.image_url

        # Generate product_id if missing
        if not self.product_id:
            self.product_id = self._generate_id()

        # Validate commission_rate
        if not (0.0 <= self.commission_rate <= 1.0):
            logger.warning(f"Invalid commission_rate {self.commission_rate}, clamping to [0.0, 1.0]")
            self.commission_rate = max(0.0, min(1.0, self.commission_rate))

    def _generate_id(self) -> str:
        """Generate hash-based ID from link"""
        if not self.link:
            return ""
        return hashlib.md5(self.link.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict for curator (backward compatible).

        This returns a dict matching the old product schema format
        that the curator expects. Metadata is excluded.

        Returns:
            Dict with all product fields except metadata
        """
        data = asdict(self)
        # Remove metadata (internal only, not for curator)
        data.pop('metadata', None)
        return data

    @classmethod
    def from_amazon(cls, item: Dict, query: str, interest: str) -> 'Product':
        """
        Create Product from Amazon RapidAPI response.

        Amazon API response format:
            {
                "product_title": "...",
                "product_url": "...",
                "product_description": "...",
                "product_photo": "...",
                "product_price": "$24.99",
                "asin": "B00XYZ123",
            }

        Args:
            item: Amazon API response item
            query: Search query that found this product
            interest: Profile interest name

        Returns:
            Product instance
        """
        return cls(
            title=item.get('product_title', 'Untitled')[:200],
            link=item.get('product_url', ''),
            snippet=item.get('product_description', '')[:500],
            image=item.get('product_photo') or item.get('thumbnail', ''),
            source_domain='amazon.com',
            search_query=query,
            interest_match=interest,
            price=item.get('product_price', ''),
            product_id=item.get('asin', ''),
            priority='medium',
            commission_rate=COMMISSION_RATES['amazon'],
            metadata={'raw_item': item},  # Store raw for debugging
        )

    @classmethod
    def from_ebay(cls, item: Dict, query: str, interest: str) -> 'Product':
        """
        Create Product from eBay Browse API response.

        eBay API response format:
            {
                "title": "...",
                "itemWebUrl": "...",
                "shortDescription": "...",
                "image": {"imageUrl": "..."},
                "price": {"value": "24.99", "currency": "USD"},
                "itemId": "123456789",
            }

        Args:
            item: eBay API response item
            query: Search query that found this product
            interest: Profile interest name

        Returns:
            Product instance
        """
        # Extract image URL (can be dict or string)
        image_dict = item.get('image', {})
        image_url = ''
        if isinstance(image_dict, dict):
            image_url = image_dict.get('imageUrl', '')
        elif isinstance(image_dict, str):
            image_url = image_dict

        # Extract price
        price_dict = item.get('price', {})
        if isinstance(price_dict, dict):
            price_value = price_dict.get('value', '')
            price_currency = price_dict.get('currency', 'USD')
            price = f"${price_value}" if price_value else ""
        else:
            price = str(price_dict) if price_dict else ""

        return cls(
            title=item.get('title', 'Untitled')[:200],
            link=item.get('itemWebUrl', ''),
            snippet=item.get('shortDescription', '')[:500],
            image=image_url,
            source_domain='ebay.com',
            search_query=query,
            interest_match=interest,
            price=price,
            product_id=item.get('itemId', ''),
            priority='medium',
            commission_rate=COMMISSION_RATES['ebay'],
            metadata={'raw_item': item},
        )

    @classmethod
    def from_etsy(cls, item: Dict, query: str, interest: str) -> 'Product':
        """
        Create Product from Etsy API response.

        Etsy API response format:
            {
                "listing_id": 123456789,
                "title": "...",
                "url": "...",
                "description": "...",
                "Images": [{"url_570xN": "...", "url_fullxfull": "..."}],
                "price": "24.99",
                "currency_code": "USD",
            }

        Args:
            item: Etsy API response item
            query: Search query that found this product
            interest: Profile interest name

        Returns:
            Product instance
        """
        # Extract image (first from Images array)
        images = item.get('Images', [])
        image_url = ''
        if images and isinstance(images, list) and len(images) > 0:
            first_image = images[0]
            if isinstance(first_image, dict):
                # Prefer 570xN (medium size), fallback to fullxfull
                image_url = first_image.get('url_570xN') or first_image.get('url_fullxfull', '')

        # Format price
        price_value = item.get('price', '')
        currency = item.get('currency_code', 'USD')
        price = f"${price_value}" if price_value else ""

        return cls(
            title=item.get('title', 'Untitled')[:200],
            link=item.get('url', ''),
            snippet=item.get('description', '')[:500],
            image=image_url,
            source_domain='etsy.com',
            search_query=query,
            interest_match=interest,
            price=price,
            product_id=str(item.get('listing_id', '')),
            priority='high',  # Etsy products are high priority (unique, higher commission)
            commission_rate=COMMISSION_RATES['etsy'],
            metadata={'raw_item': item},
        )

    @classmethod
    def from_awin(cls, item: Dict, query: str, interest: str) -> 'Product':
        """
        Create Product from Awin data feed.

        Awin feed format (CSV row as dict):
            {
                "product_id": "123",
                "product_name": "...",
                "aw_deep_link": "...",
                "merchant_deep_link": "...",
                "description": "...",
                "aw_image_url": "...",
                "merchant_image_url": "...",
                "search_price": "24.99",
                "currency": "USD",
                "merchant_name": "Cool Brand",
                "commission_amount": "5.00",  # Percentage
            }

        Args:
            item: Awin feed row dict
            query: Search query that found this product
            interest: Profile interest name

        Returns:
            Product instance
        """
        # Prefer Awin deep link over merchant link (tracking)
        link = item.get('aw_deep_link') or item.get('merchant_deep_link', '')

        # Prefer Awin image over merchant image
        image = item.get('aw_image_url') or item.get('merchant_image_url', '')

        # Extract merchant name for source_domain
        merchant_name = item.get('merchant_name', 'awin')
        # Convert "Cool Brand" → "coolbrand.com" (approximate)
        source_domain = merchant_name.lower().replace(' ', '') + '.com'

        # Parse commission rate
        commission_str = item.get('commission_amount', '5.0')
        try:
            commission_rate = float(commission_str) / 100.0  # Convert percentage to decimal
        except (ValueError, TypeError):
            commission_rate = COMMISSION_RATES['awin']

        # Format price
        price_value = item.get('search_price', '')
        currency = item.get('currency', 'USD')
        price = f"${price_value}" if price_value else ""

        return cls(
            title=item.get('product_name', 'Untitled')[:200],
            link=link,
            snippet=item.get('description', '')[:500],
            image=image,
            source_domain=source_domain,
            search_query=query,
            interest_match=interest,
            price=price,
            product_id=str(item.get('product_id', '')),
            priority='high',  # Awin products are high priority (good commission)
            commission_rate=commission_rate,
            metadata={'raw_item': item, 'merchant': merchant_name},
        )

    @classmethod
    def from_cj(cls, item: Dict, query: str, interest: str) -> 'Product':
        """
        Create Product from CJ Affiliate API response.

        CJ API response format (TBD - awaiting developer access):
            {
                "catalogId": "123",
                "name": "...",
                "linkUrl": "...",
                "description": "...",
                "imageUrl": "...",
                "price": "24.99",
                "currency": "USD",
                "advertiserName": "Brand Name",
            }

        Args:
            item: CJ API response item
            query: Search query that found this product
            interest: Profile interest name

        Returns:
            Product instance
        """
        # Extract advertiser for source_domain
        advertiser = item.get('advertiserName', 'cj')
        source_domain = advertiser.lower().replace(' ', '') + '.com'

        return cls(
            title=item.get('name', 'Untitled')[:200],
            link=item.get('linkUrl', ''),
            snippet=item.get('description', '')[:500],
            image=item.get('imageUrl', ''),
            source_domain=source_domain,
            search_query=query,
            interest_match=interest,
            price=item.get('price', ''),
            product_id=str(item.get('catalogId', '')),
            priority='high',  # CJ has good commission rates
            commission_rate=COMMISSION_RATES['cj'],
            metadata={'raw_item': item, 'advertiser': advertiser},
        )


# =============================================================================
# BATCH BUILDING HELPER
# =============================================================================

def build_product_list(
    items: list[Dict],
    platform: str,
    query: str,
    interest: str,
) -> list[Product]:
    """
    Build list of Product objects from API response.

    This is a convenience function for searcher modules to convert
    a batch of API items into Product instances. It handles errors
    gracefully and logs failures without crashing.

    Args:
        items: List of API response items
        platform: 'amazon', 'ebay', 'etsy', 'awin', 'cj'
        query: Search query that found these products
        interest: Profile interest name

    Returns:
        List of Product instances (excludes failed conversions)

    Example:
        # In amazon searcher:
        from product_schema import build_product_list

        api_items = response.json().get('data', {}).get('products', [])
        products = build_product_list(api_items, 'amazon', query, interest)

        # Convert to dicts for curator
        product_dicts = [p.to_dict() for p in products]
    """
    builders = {
        'amazon': Product.from_amazon,
        'ebay': Product.from_ebay,
        'etsy': Product.from_etsy,
        'awin': Product.from_awin,
        'cj': Product.from_cj,
    }

    builder = builders.get(platform.lower())
    if not builder:
        logger.error(f"Unknown platform: {platform}. Valid: {list(builders.keys())}")
        return []

    products = []
    for i, item in enumerate(items):
        try:
            product = builder(item, query, interest)
            products.append(product)
        except Exception as e:
            logger.warning(f"Failed to build product #{i+1} from {platform}: {e}")
            logger.debug(f"Failed item: {item}")
            continue

    logger.info(f"Built {len(products)}/{len(items)} products from {platform}")
    return products


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Product Schema - Test Suite")
    print("=" * 60)

    # Test 1: Amazon product
    print("\n1. Amazon Product:")
    amazon_item = {
        "product_title": "Orthopedic Dog Bed - Extra Large",
        "product_url": "https://amazon.com/dp/B00XYZ123",
        "product_description": "Memory foam dog bed for large breeds",
        "product_photo": "https://m.media-amazon.com/images/I/71abc.jpg",
        "product_price": "$49.99",
        "asin": "B00XYZ123",
    }
    amazon_product = Product.from_amazon(amazon_item, "dog bed", "Dog ownership")
    print(f"  Title: {amazon_product.title}")
    print(f"  Link: {amazon_product.link}")
    print(f"  Price: {amazon_product.price}")
    print(f"  Commission: {amazon_product.commission_rate * 100}%")
    print(f"  Product ID: {amazon_product.product_id}")

    # Test 2: eBay product
    print("\n2. eBay Product:")
    ebay_item = {
        "title": "Vintage Taylor Swift Concert Poster 2024",
        "itemWebUrl": "https://ebay.com/itm/123456789",
        "shortDescription": "Rare concert poster from Eras Tour",
        "image": {"imageUrl": "https://i.ebayimg.com/images/g/abc/s-l500.jpg"},
        "price": {"value": "34.99", "currency": "USD"},
        "itemId": "123456789",
    }
    ebay_product = Product.from_ebay(ebay_item, "Taylor Swift poster", "Taylor Swift")
    print(f"  Title: {ebay_product.title}")
    print(f"  Price: {ebay_product.price}")
    print(f"  Source: {ebay_product.source_domain}")
    print(f"  Commission: {ebay_product.commission_rate * 100}%")

    # Test 3: Etsy product
    print("\n3. Etsy Product:")
    etsy_item = {
        "listing_id": 987654321,
        "title": "Personalized Dog Name Necklace - Custom Pet Jewelry",
        "url": "https://etsy.com/listing/987654321",
        "description": "Handmade necklace with your dog's name",
        "Images": [
            {"url_570xN": "https://i.etsystatic.com/abc/r/il/570x570.jpg"},
        ],
        "price": "29.99",
        "currency_code": "USD",
    }
    etsy_product = Product.from_etsy(etsy_item, "dog necklace", "Dog ownership")
    print(f"  Title: {etsy_product.title}")
    print(f"  Price: {etsy_product.price}")
    print(f"  Priority: {etsy_product.priority}")
    print(f"  Commission: {etsy_product.commission_rate * 100}%")

    # Test 4: Title truncation
    print("\n4. Title Truncation:")
    long_title = "This is an extremely long product title that exceeds the 200 character limit and should be automatically truncated to ensure consistency across all retailers and prevent issues with display or database storage limitations."
    test_item = {"product_title": long_title, "product_url": "https://test.com"}
    truncated_product = Product.from_amazon(test_item, "test", "test")
    print(f"  Original length: {len(long_title)}")
    print(f"  Truncated length: {len(truncated_product.title)}")
    print(f"  Title: {truncated_product.title}")

    # Test 5: Auto product ID generation
    print("\n5. Auto Product ID Generation:")
    no_id_item = {"product_title": "Test Product", "product_url": "https://test.com/product"}
    no_id_product = Product.from_amazon(no_id_item, "test", "test")
    print(f"  Link: {no_id_product.link}")
    print(f"  Generated ID: {no_id_product.product_id}")

    # Test 6: Batch building
    print("\n6. Batch Building:")
    amazon_items = [
        {"product_title": f"Product {i}", "product_url": f"https://amazon.com/dp/B00{i}"}
        for i in range(1, 6)
    ]
    products = build_product_list(amazon_items, 'amazon', 'test query', 'Test Interest')
    print(f"  Built {len(products)} products")
    for p in products:
        print(f"    - {p.title} ({p.product_id})")

    # Test 7: to_dict conversion
    print("\n7. Dict Conversion (for curator):")
    product_dict = amazon_product.to_dict()
    print(f"  Keys: {list(product_dict.keys())}")
    print(f"  Has metadata: {'metadata' in product_dict}")  # Should be False

    print("\n" + "=" * 60)
    print("All tests complete!")
