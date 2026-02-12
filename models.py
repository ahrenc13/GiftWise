"""
GIFTWISE DATA MODELS
Dataclasses for type safety and validation

Author: Chad + Claude
Date: February 2026
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


# =============================================================================
# PRODUCT MODEL
# =============================================================================

@dataclass
class Product:
    """
    Standardized product model used across all retailers.

    Every searcher module returns products in this format.
    Database stores products in this format.
    Gift curator receives products in this format.
    """
    # Required fields
    title: str
    link: str
    source_domain: str
    retailer: str  # 'amazon', 'ebay', 'etsy', 'awin', 'skimlinks', 'cj'

    # Optional product details
    snippet: str = ''
    description: str = ''
    price: Optional[float] = None
    price_str: str = 'Price varies'
    currency: str = 'USD'

    # Images
    image: str = ''
    thumbnail: str = ''
    image_url: str = ''

    # Identifiers
    product_id: str = ''

    # Categorization
    brand: Optional[str] = None
    category: Optional[str] = None
    interest_tags: List[str] = field(default_factory=list)

    # Search metadata
    search_query: str = ''
    interest_match: str = ''
    priority: int = 10  # Retailer priority (lower = higher priority)

    # Availability
    in_stock: bool = True

    # Timestamps
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    last_checked: Optional[datetime] = None
    removed_at: Optional[datetime] = None

    # Popularity
    popularity_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization or database storage"""
        data = asdict(self)

        # Convert datetime objects to ISO strings
        for key in ['created_at', 'last_updated', 'last_checked', 'removed_at']:
            if data.get(key) and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()

        # Convert interest_tags list to JSON string for database
        if isinstance(data.get('interest_tags'), list):
            data['interest_tags'] = json.dumps(data['interest_tags'])

        return data

    def to_curator_format(self) -> Dict[str, Any]:
        """
        Convert to format expected by gift_curator.py

        Curator expects: title, link, snippet, image, thumbnail, source_domain, price
        """
        return {
            'title': self.title,
            'link': self.link,
            'snippet': self.snippet or self.description[:200] if self.description else '',
            'image': self.image or self.image_url or self.thumbnail,
            'thumbnail': self.thumbnail or self.image or self.image_url,
            'image_url': self.image_url or self.image or self.thumbnail,
            'source_domain': self.source_domain,
            'price': self.price_str if self.price_str != 'Price varies' else f"${self.price:.2f}" if self.price else 'Price varies',
            'search_query': self.search_query,
            'interest_match': self.interest_match,
            'priority': self.priority,
        }

    def to_db_format(self) -> Dict[str, Any]:
        """
        Convert to format for database.upsert_product()

        Maps Product fields to database column names
        """
        return {
            'product_id': self.product_id or f"{self.retailer}_{hash(self.link)}",
            'retailer': self.retailer,
            'title': self.title,
            'description': self.description or self.snippet,
            'price': self.price,
            'currency': self.currency,
            'image_url': self.image_url or self.image or self.thumbnail,
            'affiliate_link': self.link,
            'brand': self.brand,
            'category': self.category,
            'interest_tags': self.interest_tags,
            'in_stock': self.in_stock,
        }

    @classmethod
    def from_searcher_dict(cls, data: Dict[str, Any], retailer: str) -> 'Product':
        """
        Create Product from searcher module output

        Handles variations in searcher output formats
        """
        return cls(
            title=data.get('title', 'Unknown Product'),
            link=data.get('link', ''),
            source_domain=data.get('source_domain', retailer),
            retailer=retailer,
            snippet=data.get('snippet', ''),
            description=data.get('description', ''),
            price=data.get('price') if isinstance(data.get('price'), (int, float)) else None,
            price_str=data.get('price', 'Price varies') if isinstance(data.get('price'), str) else 'Price varies',
            currency=data.get('currency', 'USD'),
            image=data.get('image', ''),
            thumbnail=data.get('thumbnail', ''),
            image_url=data.get('image_url', ''),
            product_id=data.get('product_id', ''),
            brand=data.get('brand'),
            category=data.get('category'),
            interest_tags=data.get('interest_tags', []),
            search_query=data.get('search_query', ''),
            interest_match=data.get('interest_match', ''),
            priority=data.get('priority', 10),
            in_stock=data.get('in_stock', True),
        )

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Product':
        """
        Create Product from database row

        Args:
            row: sqlite3.Row dict from database query
        """
        # Parse interest_tags JSON
        interest_tags = []
        if row.get('interest_tags'):
            try:
                interest_tags = json.loads(row['interest_tags'])
            except (json.JSONDecodeError, TypeError):
                pass

        # Parse timestamps
        created_at = None
        last_updated = None
        last_checked = None
        removed_at = None

        if row.get('created_at'):
            try:
                created_at = datetime.fromisoformat(row['created_at'])
            except (ValueError, TypeError):
                pass

        if row.get('last_updated'):
            try:
                last_updated = datetime.fromisoformat(row['last_updated'])
            except (ValueError, TypeError):
                pass

        if row.get('last_checked'):
            try:
                last_checked = datetime.fromisoformat(row['last_checked'])
            except (ValueError, TypeError):
                pass

        if row.get('removed_at'):
            try:
                removed_at = datetime.fromisoformat(row['removed_at'])
            except (ValueError, TypeError):
                pass

        return cls(
            title=row.get('title', 'Unknown Product'),
            link=row.get('affiliate_link', ''),
            source_domain=row.get('retailer', ''),
            retailer=row.get('retailer', ''),
            snippet=row.get('description', '')[:200],
            description=row.get('description', ''),
            price=row.get('price'),
            price_str=f"${row.get('price'):.2f}" if row.get('price') else 'Price varies',
            currency=row.get('currency', 'USD'),
            image=row.get('image_url', ''),
            thumbnail=row.get('image_url', ''),
            image_url=row.get('image_url', ''),
            product_id=row.get('product_id', ''),
            brand=row.get('brand'),
            category=row.get('category'),
            interest_tags=interest_tags,
            in_stock=bool(row.get('in_stock', True)),
            created_at=created_at,
            last_updated=last_updated,
            last_checked=last_checked,
            removed_at=removed_at,
            popularity_score=row.get('popularity_score', 0),
        )


# =============================================================================
# PROFILE MODEL
# =============================================================================

@dataclass
class Interest:
    """Single interest from profile analysis"""
    name: str
    confidence: str = 'high'  # 'high', 'medium', 'low'
    evidence: List[str] = field(default_factory=list)
    category: Optional[str] = None  # 'hobby', 'style', 'music', 'sports', etc.


@dataclass
class PriceSignal:
    """Price preference signals from profile"""
    preferred_range: Optional[Dict[str, float]] = None  # {'min': 25, 'max': 150}
    luxury_tolerance: str = 'medium'  # 'low', 'medium', 'high'
    practical_vs_experiential: str = 'balanced'  # 'practical', 'balanced', 'experiential'


@dataclass
class Profile:
    """
    User profile generated by profile_analyzer.py

    This is the structured output from Claude's profile analysis.
    Used for caching, database storage, and gift curation.
    """
    # Core demographics
    age_range: Optional[str] = None  # '18-24', '25-34', etc.
    gender: Optional[str] = None
    location: Optional[str] = None

    # Interests and personality
    interests: List[Interest] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    style_preferences: List[str] = field(default_factory=list)

    # Shopping behavior
    price_signals: Optional[PriceSignal] = None
    brand_preferences: List[str] = field(default_factory=list)

    # Context
    relationship: str = 'friend'  # Relationship to gift recipient
    occasion: Optional[str] = None  # 'birthday', 'christmas', etc.

    # Metadata
    profile_hash: Optional[str] = None  # Hash for caching
    created_at: Optional[datetime] = None
    source_platforms: List[str] = field(default_factory=list)  # ['instagram', 'spotify']

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        data = asdict(self)

        # Convert datetime to ISO string
        if data.get('created_at') and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()

        return data

    def to_json(self) -> str:
        """Convert to JSON string for database storage"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'Profile':
        """Create Profile from JSON string"""
        data = json.loads(json_str)

        # Parse nested Interest objects
        interests = []
        for interest_data in data.get('interests', []):
            if isinstance(interest_data, dict):
                interests.append(Interest(**interest_data))
            else:
                # Legacy format: just strings
                interests.append(Interest(name=str(interest_data)))

        # Parse PriceSignal
        price_signals = None
        if data.get('price_signals'):
            if isinstance(data['price_signals'], dict):
                price_signals = PriceSignal(**data['price_signals'])

        # Parse created_at
        created_at = None
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except (ValueError, TypeError):
                pass

        return cls(
            age_range=data.get('age_range'),
            gender=data.get('gender'),
            location=data.get('location'),
            interests=interests,
            personality_traits=data.get('personality_traits', []),
            style_preferences=data.get('style_preferences', []),
            price_signals=price_signals,
            brand_preferences=data.get('brand_preferences', []),
            relationship=data.get('relationship', 'friend'),
            occasion=data.get('occasion'),
            profile_hash=data.get('profile_hash'),
            created_at=created_at,
            source_platforms=data.get('source_platforms', []),
        )

    @classmethod
    def from_analyzer_output(cls, analyzer_output: Dict[str, Any]) -> 'Profile':
        """
        Create Profile from profile_analyzer.py output

        Handles the specific format returned by Claude's profile analysis
        """
        # Parse interests (can be dicts or simple objects)
        interests = []
        for item in analyzer_output.get('interests', []):
            if isinstance(item, dict):
                interests.append(Interest(
                    name=item.get('name', ''),
                    confidence=item.get('confidence', 'high'),
                    evidence=item.get('evidence', []),
                    category=item.get('category')
                ))
            else:
                # Legacy: interests might be simple dicts with just 'name'
                interests.append(Interest(name=str(item.get('name', item))))

        # Parse price signals
        price_signals = None
        if analyzer_output.get('price_signals'):
            ps = analyzer_output['price_signals']
            price_signals = PriceSignal(
                preferred_range=ps.get('preferred_range'),
                luxury_tolerance=ps.get('luxury_tolerance', 'medium'),
                practical_vs_experiential=ps.get('practical_vs_experiential', 'balanced')
            )

        return cls(
            age_range=analyzer_output.get('age_range'),
            gender=analyzer_output.get('gender'),
            location=analyzer_output.get('location'),
            interests=interests,
            personality_traits=analyzer_output.get('personality_traits', []),
            style_preferences=analyzer_output.get('style_preferences', []),
            price_signals=price_signals,
            brand_preferences=analyzer_output.get('brand_preferences', []),
            relationship=analyzer_output.get('relationship', 'friend'),
            occasion=analyzer_output.get('occasion'),
            source_platforms=analyzer_output.get('source_platforms', []),
        )

    def get_search_interests(self, limit: int = 10) -> List[str]:
        """
        Get list of interest names for product searching

        Returns top N interests sorted by confidence
        """
        # Sort by confidence: high > medium > low
        confidence_order = {'high': 0, 'medium': 1, 'low': 2}
        sorted_interests = sorted(
            self.interests,
            key=lambda i: confidence_order.get(i.confidence, 3)
        )

        return [i.name for i in sorted_interests[:limit]]

    def compute_hash(self) -> str:
        """
        Generate hash for profile caching

        Hash is based on core profile data (excludes metadata like timestamps)
        """
        import hashlib

        # Build string from core data
        core_data = {
            'interests': [i.name for i in self.interests],
            'age_range': self.age_range,
            'gender': self.gender,
            'style': self.style_preferences,
            'relationship': self.relationship,
        }

        data_str = json.dumps(core_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()


# =============================================================================
# VALIDATION
# =============================================================================

if __name__ == "__main__":
    print("GiftWise Data Models")
    print("=" * 50)

    # Test Product creation from searcher dict
    searcher_data = {
        'title': 'Yoga Mat',
        'link': 'https://example.com/yoga-mat',
        'source_domain': 'Amazon',
        'price': 29.99,
        'image_url': 'https://example.com/image.jpg',
        'search_query': 'yoga gifts',
        'interest_match': 'yoga',
        'priority': 10,
    }

    product = Product.from_searcher_dict(searcher_data, retailer='amazon')
    print("Product created from searcher dict:")
    print(f"  Title: {product.title}")
    print(f"  Price: ${product.price}")
    print(f"  Retailer: {product.retailer}")
    print()

    # Test Profile creation
    profile_data = {
        'age_range': '25-34',
        'gender': 'female',
        'interests': [
            {'name': 'yoga', 'confidence': 'high', 'category': 'fitness'},
            {'name': 'travel', 'confidence': 'medium', 'category': 'lifestyle'},
        ],
        'personality_traits': ['adventurous', 'health-conscious'],
        'relationship': 'friend',
    }

    profile = Profile.from_analyzer_output(profile_data)
    print("Profile created from analyzer output:")
    print(f"  Age: {profile.age_range}")
    print(f"  Interests: {', '.join(profile.get_search_interests())}")
    print(f"  Hash: {profile.compute_hash()}")
    print()

    # Test serialization round-trip
    profile_json = profile.to_json()
    profile_restored = Profile.from_json(profile_json)
    print("Serialization test:")
    print(f"  Original interests: {len(profile.interests)}")
    print(f"  Restored interests: {len(profile_restored.interests)}")
    print(f"  Match: {profile.interests[0].name == profile_restored.interests[0].name}")
