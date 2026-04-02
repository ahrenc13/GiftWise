"""
Awin product search via Data Feed API.

Awin does not offer a keyword search API. Product data comes from product feeds (CSV).
This module:
1. Fetches the feed list: https://productdata.awin.com/datafeed/list/apikey/{key}
2. Downloads one or more feed CSVs (prefer "Joined" advertisers)
3. Searches within cached feed rows by profile interests (e.g. "hiking gift")

Env: AWIN_DATA_FEED_API_KEY (from Awin Toolbox → Create-a-Feed).
"""

import csv
import gzip
import io
import logging
import re
import time
import zlib
import requests

from api_client import APIClient

logger = logging.getLogger(__name__)


def _ci_get(row, *keys):
    """Case-insensitive dict lookup: try each key against actual row keys."""
    # Fast path: try exact match first
    for k in keys:
        v = row.get(k)
        if v:
            return v.strip() if isinstance(v, str) else v
    # Slow path: case-insensitive match
    row_lower = {k.lower().strip(): v for k, v in row.items()}
    for k in keys:
        v = row_lower.get(k.lower().strip())
        if v:
            return v.strip() if isinstance(v, str) else v
    return ""


def _decompress_if_gzipped(data):
    """Detect gzip magic bytes and decompress. Awin feeds often return gzip without Content-Encoding header."""
    if data[:2] == b'\x1f\x8b':
        try:
            decompressed = gzip.decompress(data)
            logger.info("Awin feed: decompressed gzip %d bytes -> %d bytes", len(data), len(decompressed))
            return decompressed
        except Exception as e:
            logger.warning("Awin feed gzip decompress failed: %s", e)
            # Try zlib as fallback (handles truncated gzip streams)
            try:
                decompressed = zlib.decompress(data, zlib.MAX_WBITS | 16)
                logger.info("Awin feed: decompressed via zlib %d bytes -> %d bytes", len(data), len(decompressed))
                return decompressed
            except Exception:
                pass
    return data


# Max price for Awin products. Raised from $200 to $1500 (Mar 2026) to allow
# splurge-worthy items (premium gear, high-end equipment from partner advertisers)
# into the inventory pool. The splurge slot and interest-relevance gate in
# post_curation_cleanup.py handle quality filtering; this cap prevents absurd outliers.
# The $800 scooter incident is now handled by the interest-relevance gate + blocked
# domains list, not by a crude price cap.
AWIN_MAX_PRICE_USD = 1500

# Merchants approved in our Awin account whose product categories are never
# appropriate for gift recommendations. Block at source so their feed products
# never enter the inventory pool — even if they survive the price cap or pass
# the interest-relevance gate on a coincidental keyword match.
#
# Yadea (store.yadea.com): electric scooters/e-bikes. Root cause of the $800
#   scooter incident. feedEnabled=yes so they WILL appear without this block.
#   365-day cookie and $24 EPC are irrelevant when the products aren't gifts.
# POSIE AND PENN (posieandpenn.co.uk): bed frames. Amber payment status,
#   exposure level 5, UK-only domain. Not gifts.
_AWIN_BLOCKED_DOMAINS = {
    "store.yadea.com",
    "posieandpenn.co.uk",
}

# ---------------------------------------------------------------------------
# Static product lists for approved Awin merchants with feedEnabled=no.
# These merchants are in our account but don't publish a data feed, so the
# dynamic search will never surface them. Hand-curated lists are the only way.
#
# Link format: use Awin deep links from the Awin dashboard (Publisher > Links
# > Deep Link Generator). Format: https://www.awin1.com/cread.php?
#   awinmid=<ADVERTISER_ID>&awinaffid=<YOUR_PUBLISHER_ID>&ued=<PRODUCT_URL>
#
# Commission notes (from Awin advertiser descriptions):
#   VitaJuwel: check Awin dashboard (feedEnabled=no, advertiser ID 97077)
#   VSGO:      15% commission (advertiser ID 120898)
# ---------------------------------------------------------------------------

# VitaJuwel (vitajuwel.us) — Gemstone-infused crystal water bottles and carafes.
# Triggers: wellness, crystals, yoga, meditation, spiritual, self-care.
# Advertiser ID: 97077. Cookie: 45 days. No product feed — static list only.
_VITAJUWEL_ALL_PRODUCTS = [
    {
        "title": "VitaJuwel ViA Water Bottle — INDIAN SUMMER (Sunstone & Maifan Stone)",
        "snippet": "Portable gemstone water bottle with hand-selected sunstone and maifan stone gems. BPA-free borosilicate glass, stainless steel cap. Carry the energy of crystals wherever you go.",
        "price": "$130.00",
        "source_domain": "vitajuwel.us",
        "link": "https://www.awin1.com/cread.php?awinmid=97077&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fwww.vitajuwel.us%2Fproducts%2Fvia-indian-summer",
        "image_url": "",
        "interest_match": "wellness crystals gemstone",
    },
    {
        "title": "VitaJuwel ViA Water Bottle — WELLNESS (Amethyst, Rose Quartz & Clear Quartz)",
        "snippet": "The bestselling VitaJuwel bottle. Trio of amethyst, rose quartz, and clear quartz suspended in a glass gem pod. Loved by yoga and meditation practitioners.",
        "price": "$130.00",
        "source_domain": "vitajuwel.us",
        "link": "https://www.awin1.com/cread.php?awinmid=97077&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fwww.vitajuwel.us%2Fproducts%2Fvia-wellness",
        "image_url": "",
        "interest_match": "yoga meditation crystals wellness",
    },
    {
        "title": "VitaJuwel Era Water Carafe — WELLNESS (Amethyst, Rose Quartz & Clear Quartz)",
        "snippet": "Elegant 1-liter glass carafe with removable gemstone vial. Perfect for the home altar, bedside table, or gifting to anyone obsessed with crystals and intentional living.",
        "price": "$135.00",
        "source_domain": "vitajuwel.us",
        "link": "https://www.awin1.com/cread.php?awinmid=97077&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fwww.vitajuwel.us%2Fproducts%2Fera-wellness",
        "image_url": "",
        "interest_match": "crystals wellness spiritual self-care",
    },
]

# VSGO (vsgotech.com) — Premium camera bags and accessories.
# Triggers: photography, cameras, travel photography, content creation.
# Advertiser ID: 120898. Cookie: 30 days. Commission: 15%. No product feed.
_VSGO_ALL_PRODUCTS = [
    {
        "title": "VSGO Black Snipe Camera Backpack",
        "snippet": "Award-winning camera backpack with ultra-light carrying system and patented camera compartment. Fits mirrorless and DSLR kits. Weatherproof exterior, laptop sleeve, tripod holder.",
        "price": "$119.00",
        "source_domain": "vsgotech.com",
        "link": "https://www.awin1.com/cread.php?awinmid=120898&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fvsgotech.com%2Fproducts%2Fblack-snipe-camera-backpack",
        "image_url": "",
        "interest_match": "photography cameras travel content creation",
    },
    {
        "title": "VSGO Pocket Ranger Camera Sling Bag",
        "snippet": "Compact sling bag designed for mirrorless shooters on the go. Fast-access side opening, padded dividers, weather-resistant. Great for street photography and travel.",
        "price": "$79.00",
        "source_domain": "vsgotech.com",
        "link": "https://www.awin1.com/cread.php?awinmid=120898&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fvsgotech.com%2Fproducts%2Fpocket-ranger-camera-sling-bag",
        "image_url": "",
        "interest_match": "photography street photography travel cameras",
    },
]


# Gourmet Gift Basket Store (gourmetgiftbasketstore.com) — Curated gourmet gift baskets.
# Triggers: food, gourmet, chocolate, cheese, snacks, gift basket, hostess, housewarming.
# Advertiser ID: 33247. Cookie: 60 days. No product feed.
# NOTE: Canada-based but ships to US with low delivery rates.
_GOURMET_GIFT_BASKET_ALL_PRODUCTS = [
    {
        "title": "Golden Greeting — Lavishing Celebration Gift Basket",
        "snippet": "Premium celebration gift basket with gourmet chocolates, artisan crackers, fine cheese, and elegant presentation. Perfect for birthdays, congratulations, or milestone events.",
        "price": "$248.95",
        "source_domain": "gourmetgiftbasketstore.com",
        "link": "https://www.gourmetgiftbasketstore.com/product-category/gift-baskets/gift-baskets-to-canada/best-sellers-gift-baskets/",  # Replace with Awin deep link
        "image_url": "",
        "interest_match": "gourmet food chocolate gift celebration",
    },
    {
        "title": "Gourmet Chocolate & Snacks Gift Basket",
        "snippet": "Curated selection of premium chocolates, gourmet snacks, and artisan treats. Beautifully packaged for any occasion — birthdays, thank you, or just because.",
        "price": "$99.95",
        "source_domain": "gourmetgiftbasketstore.com",
        "link": "https://www.gourmetgiftbasketstore.com/product-category/gift-baskets/gift-baskets-to-canada/best-sellers-gift-baskets/",  # Replace with Awin deep link
        "image_url": "",
        "interest_match": "chocolate snacks food gourmet treats",
    },
    {
        "title": "Spa & Relaxation Gift Basket",
        "snippet": "Pampering spa gift basket with luxurious bath products, scented candles, and self-care essentials. Ideal for birthdays, holidays, or anyone who deserves a treat.",
        "price": "$89.95",
        "source_domain": "gourmetgiftbasketstore.com",
        "link": "https://www.gourmetgiftbasketstore.com/vs/gift-baskets/luxury-gift-baskets/",  # Replace with Awin deep link
        "image_url": "",
        "interest_match": "spa relaxation self-care wellness pampering",
    },
]

# Goldia.com (goldia.com) — Fine jewelry, 95K products.
# Triggers: jewelry, necklace, ring, bracelet, earrings, gold, silver, diamond, pendant, gift.
# Advertiser ID: 64508. Cookie: 30 days. Commission: 7.5%. No product feed.
# $160 average order value. 100% approval rate. Green payment status.
_GOLDIA_ALL_PRODUCTS = [
    {
        "title": "14K Gold Diamond Pendant Necklace",
        "snippet": "Classic 14K gold pendant necklace with genuine diamond accent. Timeless elegance for any occasion — birthday, anniversary, or holiday gifting.",
        "price": "$149.00",
        "source_domain": "goldia.com",
        "link": "https://www.goldia.com",  # Replace with Awin deep link to specific SKU
        "image_url": "",
        "interest_match": "jewelry necklace gold diamond elegant",
    },
    {
        "title": "Sterling Silver Charm Bracelet",
        "snippet": "Beautiful sterling silver bracelet perfect for stacking or wearing solo. A thoughtful gift for someone who loves minimalist, everyday jewelry.",
        "price": "$89.00",
        "source_domain": "goldia.com",
        "link": "https://www.goldia.com",  # Replace with Awin deep link to specific SKU
        "image_url": "",
        "interest_match": "jewelry bracelet silver charm accessories",
    },
    {
        "title": "Gold Hoop Earrings — 14K Yellow Gold",
        "snippet": "Classic 14K yellow gold hoop earrings. Lightweight, versatile, and perfect for everyday wear or gifting to jewelry lovers.",
        "price": "$120.00",
        "source_domain": "goldia.com",
        "link": "https://www.goldia.com",  # Replace with Awin deep link to specific SKU
        "image_url": "",
        "interest_match": "jewelry earrings gold hoops fashion accessories",
    },
]

# OUTFITR (outfitrer.com) — Bike racks, cargo carriers, outdoor vehicle gear.
# NOTE: Awin description says "adventure backpacks and camping gear" but actual
# products are bike racks, cargo carriers, and trailer accessories. Still useful
# for cycling/outdoor/road trip enthusiasts.
# Triggers: cycling, biking, road trip, RV, camping, outdoor, adventure.
# Advertiser ID: 117613. Cookie: 30 days. Commission: 10%. No product feed.
_OUTFITR_ALL_PRODUCTS = [
    {
        "title": "OUTFITR 2-Bike Hitch Bike Rack — Foldable Platform Style",
        "snippet": "Foldable platform-style bike rack for 2 bikes. 200 lbs capacity, fits 2\" receiver. Works with cars, trucks, SUVs, RVs. Anti-wobble design with free shipping.",
        "price": "$159.99",
        "source_domain": "outfitrer.com",
        "link": "https://outfitrer.com/products/foldable-2-bike-hitch-rack-platform-style-2-receiver-200-lbs-capacity",  # Replace with Awin deep link
        "image_url": "",
        "interest_match": "cycling biking outdoor adventure road trip",
    },
    {
        "title": "OUTFITR 2-Bike Hitch E-Bike Rack — EZ-Fold Electric Bike Carrier",
        "snippet": "Heavy-duty e-bike rack with EZ-fold design. 200 lbs capacity for electric bikes. Fits 2\" receiver on cars, trucks, SUVs, and RVs.",
        "price": "$189.99",
        "source_domain": "outfitrer.com",
        "link": "https://outfitrer.com/products/2-bike-hitch-e-bike-rack-ez-fold-electric-bike-carrier-200-lbs-capacity-fits-2-receiver",  # Replace with Awin deep link
        "image_url": "",
        "interest_match": "cycling e-bike electric bike outdoor adventure",
    },
]

# Young Electric Bikes (youngelectricbikes.com) — Premium e-bikes for commuting and adventure.
# Triggers: cycling, outdoor adventure, fitness, e-bike themes. Splurge-tier price points.
# Advertiser ID: 120209. No product feed — static list only.
_YOUNG_ELECTRIC_BIKES_ALL_PRODUCTS = [
    {
        "title": "Young Electric E-Scout Pro Electric Mountain Bike",
        "snippet": "Full-suspension electric mountain bike with 750W motor, 48V 15Ah battery, and 28 mph top speed. 7-speed Shimano drivetrain, hydraulic disc brakes, front suspension fork. Built for trail riding and adventure.",
        "price": "$1,499.00",
        "source_domain": "youngelectricbikes.com",
        "link": "https://www.awin1.com/cread.php?awinmid=120209&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fyoungelectricbikes.com%2Fproducts%2Fe-scout-pro",
        "image_url": "",
        "interest_match": "cycling mountain biking electric bike outdoor adventure fitness",
    },
    {
        "title": "Young Electric E-Cross Pro Electric Commuter Bike",
        "snippet": "Versatile electric commuter and trail bike with 750W motor, 48V 15Ah battery, 28 mph top speed, and integrated rear rack. Shimano 7-speed gears, hydraulic disc brakes, aluminum frame.",
        "price": "$1,299.00",
        "source_domain": "youngelectricbikes.com",
        "link": "https://www.awin1.com/cread.php?awinmid=120209&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fyoungelectricbikes.com%2Fproducts%2Fe-cross-pro",
        "image_url": "",
        "interest_match": "cycling commuting electric bike fitness outdoor adventure",
    },
    {
        "title": "Young Electric E-Scout Electric Mountain Bike (Standard)",
        "snippet": "Entry-point electric mountain bike with 500W motor, 48V 10.4Ah battery, 25 mph top speed. 7-speed Shimano drivetrain, mechanical disc brakes. Great first e-bike for trail riders.",
        "price": "$999.00",
        "source_domain": "youngelectricbikes.com",
        "link": "https://www.awin1.com/cread.php?awinmid=120209&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fyoungelectricbikes.com%2Fproducts%2Fe-scout",
        "image_url": "",
        "interest_match": "cycling mountain biking electric bike outdoor adventure",
    },
]

# Tayst Coffee (taystcoffee.com) — Sustainable coffee subscriptions in 100% compostable pods.
# Triggers: coffee, sustainability, eco-friendly, subscription, morning routine themes.
# Advertiser ID: 90529. No product feed — static list only.
_TAYST_COFFEE_ALL_PRODUCTS = [
    {
        "title": "Tayst Coffee — Sustainable Coffee Pod Subscription (6-Month Prepaid)",
        "snippet": "Six months of freshly-roasted coffee delivered in 100% compostable pods — no plastic, no landfill. Choose your roast profile (light, medium, dark). Better for the planet and your morning.",
        "price": "$89.00",
        "source_domain": "taystcoffee.com",
        "link": "https://www.awin1.com/cread.php?awinmid=90529&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fwww.tayst.com%2Fpages%2Fsubscriptions",
        "image_url": "",
        "interest_match": "coffee sustainability eco-friendly subscription morning routine environment",
    },
    {
        "title": "Tayst Coffee — Gift Box Sampler (Compostable Pods, 3 Roasts)",
        "snippet": "A curated sampler gift box with Tayst's three signature roasts — light, medium, and dark — all in compostable pods. The perfect gift for coffee lovers who care about sustainability.",
        "price": "$29.00",
        "source_domain": "taystcoffee.com",
        "link": "https://www.awin1.com/cread.php?awinmid=90529&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fwww.tayst.com%2Fpages%2Four-coffee-promotion",
        "image_url": "",
        "interest_match": "coffee eco-friendly sustainability gift morning routine",
    },
    {
        "title": "Tayst Coffee — Monthly Coffee Subscription (Compostable Pods)",
        "snippet": "Monthly delivery of freshly-roasted coffee in 100% compostable pods. Customize roast, grind, and quantity. Cancel anytime. A thoughtful recurring gift for eco-conscious coffee drinkers.",
        "price": "$19.00",
        "source_domain": "taystcoffee.com",
        "link": "https://www.awin1.com/cread.php?awinmid=90529&awinaffid=!!id!!&agen=&clickref=&p=https%3A%2F%2Fwww.tayst.com%2Fpages%2Fsubscriptions",
        "image_url": "",
        "interest_match": "coffee subscription sustainability eco-friendly morning routine",
    },
]


def _get_awin_static_products(profile):
    """Return static Awin products relevant to the current profile's interests.

    Called at the end of search_products_awin() to supplement dynamic feed
    results for merchants with feedEnabled=no. Only injects products whose
    interest_match overlaps with the profile's actual interests.
    """
    interests = [i.get("name", "").lower() for i in profile.get("interests", []) if isinstance(i, dict)]
    interest_text = " ".join(interests)

    results = []

    # VitaJuwel — trigger on wellness/crystal/yoga/meditation/spiritual themes
    vitajuwel_triggers = {"crystal", "crystals", "yoga", "wellness", "meditation", "spiritual", "gemstone", "self-care", "selfcare", "mindful", "mindfulness", "holistic", "reiki", "chakra"}
    if any(t in interest_text for t in vitajuwel_triggers):
        results.extend(_VITAJUWEL_ALL_PRODUCTS)

    # VSGO — trigger on photography/camera themes
    vsgo_triggers = {"photo", "photography", "camera", "cameras", "photographer", "canon", "nikon", "sony", "mirrorless", "dslr", "content creator", "content creation", "videograph"}
    if any(t in interest_text for t in vsgo_triggers):
        results.extend(_VSGO_ALL_PRODUCTS)

    # Gourmet Gift Basket Store — trigger on food/gourmet/chocolate/hostess themes
    gourmet_triggers = {"food", "foodie", "gourmet", "chocolate", "cheese", "snack", "baking", "cooking", "chef", "brunch", "hostess", "housewarming", "wine", "charcuterie", "treats", "gift basket", "spa", "relaxation", "self-care", "pampering"}
    if any(t in interest_text for t in gourmet_triggers):
        results.extend(_GOURMET_GIFT_BASKET_ALL_PRODUCTS)

    # Goldia — trigger on jewelry/fashion accessories themes
    goldia_triggers = {"jewelry", "jewellery", "necklace", "bracelet", "earring", "earrings", "ring", "gold", "silver", "diamond", "pendant", "charm", "accessories", "fashion", "elegant", "luxury", "bling", "gems", "gemstone"}
    if any(t in interest_text for t in goldia_triggers):
        results.extend(_GOLDIA_ALL_PRODUCTS)

    # OUTFITR — trigger on cycling/biking/outdoor vehicle themes
    outfitr_triggers = {"cycling", "biking", "bike", "bicycle", "cyclist", "road trip", "rv", "camping", "e-bike", "ebike", "mountain bike", "trail"}
    if any(t in interest_text for t in outfitr_triggers):
        results.extend(_OUTFITR_ALL_PRODUCTS)

    # Young Electric Bikes — trigger on cycling/e-bike/outdoor adventure themes
    young_electric_triggers = {"cycling", "biking", "bike", "bicycle", "cyclist", "e-bike", "ebike",
                                "electric bike", "mountain bike", "trail", "outdoor adventure", "commuting"}
    if any(t in interest_text for t in young_electric_triggers):
        results.extend(_YOUNG_ELECTRIC_BIKES_ALL_PRODUCTS)

    # Tayst Coffee — trigger on coffee/sustainability/eco-friendly/subscription themes
    tayst_triggers = {"coffee", "espresso", "cappuccino", "latte", "morning routine", "sustainability",
                      "sustainable", "eco", "eco-friendly", "environment", "environmentalist",
                      "zero waste", "compost", "subscription box"}
    if any(t in interest_text for t in tayst_triggers):
        results.extend(_TAYST_COFFEE_ALL_PRODUCTS)

    return results


# In-memory cache: feed list and one feed's products. TTL 1 hour.
_awin_feed_list_cache = {}
_awin_feed_list_ts = 0
_awin_products_cache = {}
_awin_products_ts = 0
AWIN_CACHE_TTL = 3600


def _get_feed_list(api_key):
    """Fetch CSV list of feeds. Returns list of dicts with url, feed_id, advertiser_name, membership_status."""
    global _awin_feed_list_ts, _awin_feed_list_cache
    now = time.time()
    if now - _awin_feed_list_ts < AWIN_CACHE_TTL and api_key in _awin_feed_list_cache:
        return _awin_feed_list_cache[api_key]

    url = f"https://productdata.awin.com/datafeed/list/apikey/{api_key}"

    # Use APIClient for automatic retry on transient failures
    client = APIClient(timeout=30, max_retries=2)
    text = client.get(url, parse_json=False)

    if not text:
        logger.warning("Awin feed list request failed")
        return []
    if not text.strip():
        return []

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    # Log actual column names on first fetch for debugging
    if rows:
        logger.info("Awin feed list columns: %s", list(rows[0].keys()))
        # Sample membership status values to debug joined=0
        statuses = set()
        for r in rows[:30]:
            for k in r:
                if 'status' in k.lower() or 'member' in k.lower() or 'join' in k.lower():
                    statuses.add(f"{k}={r[k]}")
            # Also check by common Awin column names
            for col in ("Membership Status", "membership_status", "Joined", "Status"):
                v = r.get(col)
                if v:
                    statuses.add(f"{col}={v}")
        if statuses:
            logger.info("Awin feed list status-like values (sample): %s", statuses)

    # Normalize column names (could be with/without spaces); include Vertical and Feed Name for relevance
    out = []
    for row in rows:
        # Case-insensitive column lookup helper
        ci = {k.lower().strip(): v for k, v in row.items()}
        url_val = (ci.get("url") or "").strip()
        feed_id = (ci.get("feed id") or ci.get("feed_id") or "").strip()
        advertiser = (ci.get("advertiser name") or ci.get("advertiser_name") or "").strip()
        # Awin uses various column names for membership: check all known variants
        status = (ci.get("membership status") or ci.get("membership_status")
                  or ci.get("joined") or ci.get("status") or "").strip()
        feed_name = (ci.get("feed name") or ci.get("feed_name") or ci.get("name") or "").strip()
        vertical = (ci.get("vertical") or ci.get("primary region") or "").strip()
        # Also extract number of products and language for smarter feed selection
        num_products = 0
        for np_col in ("no of products", "no_of_products", "number of products", "products"):
            np_val = ci.get(np_col)
            if np_val:
                try:
                    num_products = int(str(np_val).strip().replace(",", ""))
                except (ValueError, TypeError):
                    pass
                break
        language = (ci.get("language") or "").strip()
        primary_region = (ci.get("primary region") or ci.get("primary_region") or "").strip()
        if url_val:
            out.append({
                "url": url_val,
                "feed_id": feed_id,
                "advertiser_name": advertiser,
                "membership_status": status,
                "feed_name": feed_name,
                "vertical": vertical,
                "num_products": num_products,
                "language": language or primary_region,
                "primary_region": primary_region,
            })
    _awin_feed_list_cache[api_key] = out
    _awin_feed_list_ts = now
    # Log breakdown of statuses
    status_counts = {}
    for f in out:
        s = f.get("membership_status", "").lower() or "(empty)"
        status_counts[s] = status_counts.get(s, 0) + 1
    logger.info("Awin feed list: %s feeds, status breakdown: %s", len(out), status_counts)
    return out


# Max rows to read per feed when loading full feed (legacy path)
MAX_ROWS_PER_FEED = 800
# When streaming: max rows to scan per feed before moving to next (finds matches without loading full feed)
MAX_ROWS_TO_SCAN_PER_FEED = 3500


def _stream_feed_and_match(feed_url, search_queries, max_results_from_feed, seen_ids):
    """
    Download a feed CSV (buffered, not raw-stream) and yield rows that match any search query.
    Stops when we have max_results_from_feed matches or after MAX_ROWS_TO_SCAN_PER_FEED rows.

    We buffer the first ~4 MB into memory rather than wrapping the raw socket with TextIOWrapper,
    because many Awin feeds close the socket mid-read ("I/O operation on closed file").
    """
    BUFFER_BYTES = 4 * 1024 * 1024  # 4 MB — enough for ~3500 CSV rows

    try:
        r = requests.get(feed_url, timeout=90, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed stream failed: %s", e)
        return

    r.raw.decode_content = True  # handle gzip/deflate at the urllib3 level

    # Buffer first BUFFER_BYTES so we aren't at the mercy of the socket staying open
    try:
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            if total >= BUFFER_BYTES:
                break
        r.close()
        data = b"".join(chunks)
    except Exception as e:
        logger.warning("Awin feed download failed: %s", e)
        try:
            r.close()
        except Exception:
            pass
        return

    if not data:
        return

    # Awin feeds often return gzip-compressed data without Content-Encoding header
    data = _decompress_if_gzipped(data)

    count = 0
    scanned = 0
    try:
        text = data.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for row in reader:
            scanned += 1
            # Log column names from first row for debugging
            if scanned == 1:
                logger.info("Awin feed CSV columns: %s", list(row.keys())[:20])
                # Log a sample product to see what data we're working with
                sample_title = _ci_get(row, "product_name", "title", "product_title", "name")
                sample_link = _ci_get(row, "aw_deep_link", "merchant_deep_link", "deep_link", "link", "aw_product_url")
                logger.info("Awin feed sample row: title=%s link=%s",
                            (sample_title or "(none)")[:60], (sample_link or "(none)")[:60])
            if count >= max_results_from_feed or scanned > MAX_ROWS_TO_SCAN_PER_FEED:
                break
            for q in search_queries:
                if count >= max_results_from_feed:
                    break
                terms = list(re.split(r"\s+", q["query"]))
                if q.get("primary_term") and q["primary_term"] not in (t.lower() for t in terms):
                    terms.append(q["primary_term"])
                if not _matches_query(row, terms):
                    continue
                product = _row_to_product(
                    row,
                    q.get("interest", "general"),
                    q.get("query", "gift"),
                    q.get("priority", "medium"),
                )
                if not product or product["product_id"] in seen_ids:
                    continue
                seen_ids.add(product["product_id"])
                count += 1
                yield product
                break
    except Exception as e:
        logger.warning("Awin feed parse failed (buffered): %s", e)
    if scanned > 0:
        logger.info("Awin buffered: scanned %s rows, matched %s from %s", scanned, count, feed_url[:80])


def _fetch_feed_nonstream(feed_url, search_queries, max_results_from_feed, seen_ids):
    """
    Fallback: fetch feed with requests.get (no stream), parse CSV from r.text.
    Use when streaming fails with 'I/O operation on closed file' (e.g. gzip/connection issues).
    """
    try:
        r = requests.get(feed_url, timeout=90)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed non-stream fetch failed: %s", e)
        return
    # Decompress if gzipped (Awin feeds often lack Content-Encoding header)
    raw_data = _decompress_if_gzipped(r.content)
    text = raw_data.decode("utf-8", errors="replace")
    count = 0
    scanned = 0
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for row in reader:
            scanned += 1
            if count >= max_results_from_feed or scanned > MAX_ROWS_TO_SCAN_PER_FEED:
                break
            for q in search_queries:
                if count >= max_results_from_feed:
                    break
                terms = list(re.split(r"\s+", q["query"]))
                if q.get("primary_term") and q["primary_term"] not in (t.lower() for t in terms):
                    terms.append(q["primary_term"])
                if not _matches_query(row, terms):
                    continue
                product = _row_to_product(
                    row,
                    q.get("interest", "general"),
                    q.get("query", "gift"),
                    q.get("priority", "medium"),
                )
                if not product or product["product_id"] in seen_ids:
                    continue
                seen_ids.add(product["product_id"])
                count += 1
                yield product
                break
    except Exception as e:
        logger.warning("Awin feed non-stream parse failed: %s", e)
    if scanned > 0:
        logger.debug("Awin non-stream: scanned %s rows, matched %s", scanned, count)


def _stream_feed_first_n(feed_url, n, seen_ids):
    """Yield first n valid products from feed (no query match). Used when matching returns 0."""
    BUFFER_BYTES = 1 * 1024 * 1024  # 1 MB — only need a few rows

    try:
        r = requests.get(feed_url, timeout=90, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed stream failed: %s", e)
        return
    r.raw.decode_content = True

    try:
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            if total >= BUFFER_BYTES:
                break
        r.close()
        data = b"".join(chunks)
    except Exception as e:
        logger.warning("Awin feed download failed (first_n): %s", e)
        try:
            r.close()
        except Exception:
            pass
        return

    if not data:
        return

    data = _decompress_if_gzipped(data)

    count = 0
    try:
        text = data.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for row in reader:
            if count >= n:
                break
            product = _row_to_product(row, "general", "gift", "medium")
            if not product or product["product_id"] in seen_ids:
                continue
            seen_ids.add(product["product_id"])
            count += 1
            yield product
    except Exception as e:
        logger.warning("Awin feed parse failed (first_n): %s", e)


def _download_feed_csv(feed_url):
    """Download feed CSV; buffer first 4 MB and cap at MAX_ROWS_PER_FEED to avoid OOM on large feeds."""
    BUFFER_BYTES = 4 * 1024 * 1024

    try:
        r = requests.get(feed_url, timeout=60, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed download failed: %s", e)
        return []
    r.raw.decode_content = True

    try:
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            if total >= BUFFER_BYTES:
                break
        r.close()
        data = b"".join(chunks)
    except Exception as e:
        logger.warning("Awin feed download read failed: %s", e)
        try:
            r.close()
        except Exception:
            pass
        return []

    data = _decompress_if_gzipped(data)

    rows = []
    try:
        text = data.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for i, row in enumerate(reader):
            if i >= MAX_ROWS_PER_FEED:
                break
            rows.append(row)
    except Exception as e:
        logger.warning("Awin feed parse failed: %s", e)
        return []
    logger.info("Awin feed parsed: %s product rows (max %s per feed)", len(rows), MAX_ROWS_PER_FEED)
    return rows


def _row_to_product(row, interest, query, priority):
    """Map Awin feed row to our product dict. Case-insensitive column lookup for robustness."""
    title = _ci_get(row, "product_name", "product name", "title", "product_title", "name",
                    "Product Name", "Title")
    link = _ci_get(row, "aw_deep_link", "merchant_deep_link", "deep_link", "link",
                   "aw_product_url", "product_url", "URL", "Merchant Deep Link")
    image = _ci_get(row, "merchant_image_url", "aw_image_url", "aw_thumb_url",
                    "image_url", "merchant_thumb", "product_image", "thumb_url",
                    "image_link", "thumbnail_url", "Image URL", "Merchant Image URL")
    price = _ci_get(row, "search_price", "store_price", "price", "Price",
                    "rrp_price", "display_price")
    merchant = _ci_get(row, "merchant_name", "Merchant Name", "brand_name", "brand",
                       "advertiser_name")
    if not title:
        return None
    if not link:
        return None
    description = _ci_get(row, "product_short_description", "description", "Description",
                          "product_description", "Product Description")
    snippet = description[:150] if description else (f"From {merchant}" if merchant else title[:120])
    # Extract a clean source domain from the merchant name
    # If merchant name contains a domain-like string (e.g. "eSIMania.com"), use it directly
    # Otherwise, build a reasonable slug from the first meaningful words
    if merchant:
        _m = merchant.strip()
        # Check if merchant name already contains a domain
        domain_match = re.search(r'(\w[\w-]*\.(?:com|co\.uk|net|org|io|shop|store))', _m, re.IGNORECASE)
        if domain_match:
            source_domain = domain_match.group(1).lower()
        else:
            # Use first 2-3 words to avoid absurdly long domains
            words = re.split(r'[\s\-]+', _m)
            slug = "".join(w.lower() for w in words[:3] if w)
            source_domain = slug + ".com" if slug else "awin.com"
    else:
        source_domain = "awin.com"
    product_id = _ci_get(row, "aw_product_id", "merchant_product_id", "product_id",
                         "Product ID") or str(hash(title + link))[:16]
    return {
        "title": title[:200],
        "link": link,
        "snippet": snippet,
        "image": image,
        "thumbnail": image,
        "image_url": image,
        "source_domain": source_domain,
        "search_query": query,
        "interest_match": interest,
        "priority": priority,
        "price": str(price) if price else "",
        "product_id": str(product_id),
    }


def _product_text(row):
    """All searchable text from a feed row; case-insensitive column lookup."""
    name = (_ci_get(row, "product_name", "product name", "Product Name", "Name",
                    "Title", "title", "product_title") or "").lower()
    keywords = (_ci_get(row, "keywords", "product_short_description", "description",
                        "Description", "product_description", "category_name",
                        "merchant_category") or "").lower()
    brand = (_ci_get(row, "brand_name", "brand", "merchant_name") or "").lower()
    return name + " " + keywords + " " + brand


def _matches_query(row, query_terms):
    """True if product text contains enough meaningful query terms.

    Awin feeds are full retail catalogs, not gift-curated lists. A single-word
    match (e.g. "home" in an electric scooter description matching a "home
    renovation" query) lets irrelevant products into the pool. Require 2
    meaningful matches when the query has 3+ meaningful terms; 1 match is
    still fine for short queries (e.g. "hiking" or "Taylor Swift").
    """
    text = _product_text(row)
    generic_terms = {"and", "the", "or", "with", "from", "gift", "present", "idea", "unique", "personalized", "accessories", "lover", "fan"}
    meaningful_terms = []
    for term in query_terms:
        t = (term or "").strip().lower()
        if len(t) <= 1 or t in generic_terms:
            continue
        meaningful_terms.append(t)
    matched = sum(1 for t in meaningful_terms if t in text)
    threshold = 2 if len(meaningful_terms) >= 3 else 1
    return matched >= threshold


def search_products_awin(profile, data_feed_api_key, target_count=20, enhanced_search_terms=None):
    """
    Search Awin product feeds by profile interests and intelligence-layer search terms.

    Checks the SQLite catalog cache first (populated by catalog_sync.py nightly Awin sync).
    Falls back to live feed downloads only if the cache doesn't have enough coverage.

    Uses feed list + multiple feed CSVs (cached) for full breadth. Prefers Joined advertisers.
    If enhanced_search_terms (from enrichment) are provided, also matches products against those.
    Returns list of product dicts in our standard format.
    """
    if not (data_feed_api_key and data_feed_api_key.strip()):
        logger.warning("Awin data feed API key not set - skipping Awin search")
        return []

    api_key = data_feed_api_key.strip()

    # --- Catalog-only: Awin products come exclusively from the nightly-synced DB.
    # Live feed CSV download removed (Phase 2, Apr 2026). The nightly sync populates
    # 589 terms via catalog_sync.py. Static Awin partners always inject below.
    # _matches_query() 2-term threshold is preserved in the static partner logic. ---
    try:
        from catalog_sync import get_cached_awin_products_for_interest
        interests = profile.get("interests", [])
        cached_products = []
        seen_ids = set()
        for interest in interests:
            name = interest.get("name", "")
            if not name or interest.get("is_work", False):
                continue
            for p in get_cached_awin_products_for_interest(name, limit=20):
                pid = p.get("product_id", "")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    cached_products.append(p)
        static = _get_awin_static_products(profile)
        result = (cached_products + static)[:target_count]
        logger.info(
            "[CATALOG] Awin live feed skipped — using DB only (%d cached + %d static = %d products)",
            len(cached_products), len(static), len(result)
        )
        return result
    except Exception as e:
        logger.warning("Awin catalog lookup failed (%s) — returning static products only", e)
        try:
            static = _get_awin_static_products(profile)
            logger.info("Awin: returning %d static products after catalog failure", len(static))
            return static
        except Exception as e2:
            logger.error("Awin static products also failed: %s", e2)
            return []