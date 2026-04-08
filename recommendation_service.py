"""
Recommendation Service
Orchestrates the full gift recommendation generation pipeline.

This service coordinates all steps of recommendation generation:
1. Profile building/analysis
2. Profile enrichment (intelligence layer)
3. Regional context integration
4. Multi-retailer product search
5. AI-powered gift curation
6. Post-curation cleanup and validation
7. Material backfill and image validation
8. Final assembly and storage

Author: Chad + Claude
Date: February 2026
"""

import os
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from urllib.parse import quote

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Orchestrates the full recommendation generation pipeline.

    Manages the multi-step process of building recipient profiles,
    searching retailers, curating personalized gifts, and assembling
    final recommendations with validated images and links.
    """

    def __init__(self, app_context, claude_client, models_config: Dict[str, str],
                 progress_callback: Optional[Callable] = None):
        """
        Initialize recommendation service.

        Args:
            app_context: Flask application context
            claude_client: Anthropic Claude API client
            models_config: Dict with 'profile' and 'curator' model names
            progress_callback: Optional callback(stage, stage_label, **kwargs) for progress updates
        """
        self.app_context = app_context
        self.claude_client = claude_client
        self.profile_model = models_config.get('profile', 'claude-sonnet-4-20250514')
        self.curator_model = models_config.get('curator', 'claude-sonnet-4-20250514')
        self.progress_callback = progress_callback or (lambda *args, **kwargs: None)

        # Load environment variables
        self.amazon_affiliate_tag = os.environ.get('AMAZON_AFFILIATE_TAG', '')

        # Import required modules
        self._import_modules()

    def _import_modules(self):
        """Import all required modules for the pipeline."""
        from profile_analyzer import build_recipient_profile
        from multi_retailer_searcher import search_products_multi_retailer
        from gift_curator import curate_gifts
        from smart_filters import apply_smart_filters, filter_workplace_experiences, filter_work_themed_experiences
        from url_utils import normalize_product_url

        self.build_recipient_profile = build_recipient_profile
        self.search_products_multi_retailer = search_products_multi_retailer
        self.curate_gifts = curate_gifts
        self.apply_smart_filters = apply_smart_filters
        self.filter_workplace_experiences = filter_workplace_experiences
        self.filter_work_themed_experiences = filter_work_themed_experiences
        self.normalize_product_url = normalize_product_url

        # Optional imports
        try:
            from enrichment_engine import enrich_profile_simple, should_filter_product
            self.enrich_profile_simple = enrich_profile_simple
            self.should_filter_product = should_filter_product
            self.intelligence_layer_available = True
        except ImportError:
            self.enrich_profile_simple = None
            self.should_filter_product = None
            self.intelligence_layer_available = False

        try:
            from regional_culture import get_regional_context
            from local_events import get_local_events_for_month
            self.get_regional_context = get_regional_context
            self.get_local_events_for_month = get_local_events_for_month
            self.regional_intelligence_available = True
        except ImportError:
            self.get_regional_context = None
            self.get_local_events_for_month = None
            self.regional_intelligence_available = False

        try:
            from post_curation_cleanup import cleanup_curated_gifts
            self.cleanup_curated_gifts = cleanup_curated_gifts
        except ImportError:
            self.cleanup_curated_gifts = None

        try:
            from image_fetcher import process_recommendation_images
            self.process_recommendation_images = process_recommendation_images
            self.image_fetching_available = True
        except ImportError:
            self.process_recommendation_images = None
            self.image_fetching_available = False

        try:
            from link_validation import is_bad_product_url
            self.is_bad_product_url = is_bad_product_url
        except ImportError:
            self.is_bad_product_url = lambda url: False

        try:
            from experience_providers import get_experience_providers
            self.get_experience_providers = get_experience_providers
        except ImportError:
            self.get_experience_providers = None

        try:
            from revenue_optimizer import intelligent_product_filter, track_profile_interests, track_curation_outcome
            self.intelligent_product_filter = intelligent_product_filter
            self.track_profile_interests = track_profile_interests
            self.track_curation_outcome = track_curation_outcome
            self.revenue_optimizer_available = True
        except ImportError:
            self.intelligent_product_filter = None
            self.track_profile_interests = None
            self.track_curation_outcome = None
            self.revenue_optimizer_available = False

    def generate_recommendations(self, user_id: str, user: Dict, platforms: List[Dict],
                                recipient_type: str, relationship: str,
                                approved_profile: Optional[Dict] = None,
                                enriched_profile: Optional[Dict] = None,
                                enhanced_search_terms: Optional[List[str]] = None,
                                quality_filters: Optional[List[str]] = None,
                                recipient_age: Optional[int] = None,
                                recipient_gender: Optional[str] = None,
                                gift_context: Optional[str] = None) -> List[Dict]:
        """
        Generate personalized gift recommendations.

        Args:
            user_id: Unique user identifier
            user: User data dict
            platforms: List of connected social platforms
            recipient_type: 'self' or 'other'
            relationship: Relationship type (e.g., 'close_friend', 'romantic_partner')
            approved_profile: Optional pre-approved profile from review step
            enriched_profile: Optional pre-enriched profile
            enhanced_search_terms: Optional pre-computed search terms
            quality_filters: Optional quality filters for products
            recipient_age: Optional recipient age
            recipient_gender: Optional recipient gender

        Returns:
            List of recommendation dicts

        Raises:
            ValueError: If profile building fails or no products found
        """
        logger.info("=" * 60)
        logger.info("STARTING RECOMMENDATION GENERATION PIPELINE")
        logger.info("=" * 60)

        # STEP 1: Build or use approved recipient profile
        profile = self._build_profile(user_id, platforms, recipient_type, relationship, approved_profile, gift_context)

        # Validate profile has interests
        profile_for_backend = self._prepare_profile_for_backend(profile)
        if not profile_for_backend.get('interests'):
            raise ValueError('No personal interests to base recommendations on. Add hobbies or interests that aren\'t work-related.')

        # Report discovered interests
        self._report_interests(user_id, profile, profile_for_backend)

        # STEP 2: Enrich profile with intelligence layer
        enriched_profile, enhanced_search_terms, quality_filters = self._enrich_profile(
            profile_for_backend, relationship, recipient_age, recipient_gender,
            enriched_profile, enhanced_search_terms, quality_filters
        )

        # STEP 3: Search retailers for products
        products, splurge_candidates = self._search_products(
            user_id, profile_for_backend, enhanced_search_terms
        )

        # STEP 4: Apply quality filters
        products = self._apply_filters(products, profile, quality_filters)

        # STEP 5: Curate gifts with AI
        curated_products, curated_experiences, splurge_item = self._curate_gifts(
            user_id, profile_for_backend, products, recipient_type, relationship,
            enhanced_search_terms, enriched_profile, splurge_candidates=splurge_candidates
        )

        # STEP 6: Post-curation cleanup (splurge item bypasses cleanup — it's a separate slot)
        final_products, final_experiences = self._cleanup_curation(
            user_id, curated_products, curated_experiences, products, profile
        )

        # Re-add splurge item after cleanup (it shouldn't be subject to brand/category dedup
        # against regular picks — it's intentionally in a different tier)
        if splurge_item:
            splurge_item['is_splurge'] = True  # Ensure flag survives
            final_products.append(splurge_item)
            logger.info(f"Splurge item added to final products: {splurge_item.get('name', 'unknown')}")

        if not final_products and not final_experiences:
            raise ValueError('Unable to generate recommendations. Please try again.')

        # STEP 7: Build final recommendations
        recommendations = self._build_recommendations(
            user_id, final_products, final_experiences, products, profile,
            recipient_age, recipient_gender
        )

        if not recommendations:
            raise ValueError("We couldn't find enough valid recommendations this time. Please try again.")

        # STEP 8: Backfill images
        recommendations = self._process_images(user_id, recommendations)

        logger.info(f"Generation complete! {len(recommendations)} recommendations generated.")
        return recommendations

    def _build_profile(self, user_id: str, platforms: List[Dict], recipient_type: str,
                      relationship: str, approved_profile: Optional[Dict],
                      gift_context: Optional[str] = None) -> Dict:
        """Build or use approved recipient profile."""
        # Tailor progress message: Spotify-only has no posts to read
        spotify_data = platforms.get('spotify', {}).get('data', {}) if isinstance(platforms, dict) else {}
        has_social_posts = any(
            platforms.get(p, {}).get('data', {})
            for p in ('instagram', 'tiktok', 'pinterest')
        ) if isinstance(platforms, dict) else True
        is_spotify_only = bool(spotify_data) and not has_social_posts

        self.progress_callback(
            stage='profile_analysis',
            stage_label='Analyzing their music taste and listening history...' if is_spotify_only
                        else 'Building a personality profile from their posts...'
        )

        if approved_profile:
            logger.info("Using user-approved profile from review step")
            return approved_profile

        logger.info("STEP 1: Building deep recipient profile...")
        profile = self.build_recipient_profile(
            platforms, recipient_type, relationship,
            self.claude_client, model=self.profile_model,
            gift_context=gift_context
        )

        if not profile.get('interests'):
            raise ValueError('Unable to extract enough information from social media. Please connect more platforms or ensure profiles are public.')

        # Inject Spotify artist images for experience thumbnails.
        # These are raw API data (not Claude output) so we add them after profile is returned,
        # whether it came from cache or from a fresh Claude call.
        artist_images = spotify_data.get('artist_images', {})
        if artist_images:
            profile['spotify_artist_images'] = artist_images
            logger.info(f"Injected {len(artist_images)} Spotify artist images into profile")

        return profile

    def _prepare_profile_for_backend(self, profile: Dict) -> Dict:
        """Prepare profile for search and curation (filter work interests)."""
        from giftwise_app import profile_for_search_and_curation
        return profile_for_search_and_curation(profile)

    def _report_interests(self, user_id: str, profile: Dict, profile_for_backend: Dict):
        """Report discovered interests to progress tracker."""
        interest_names = [i.get('name', '') for i in profile.get('interests', []) if i.get('name')]
        non_work_count = len(profile_for_backend.get('interests', []))
        location = profile.get('location_context', {}).get('city_region')

        logger.info(f"Profile built: {len(interest_names)} interests ({non_work_count} non-work), location: {location}")

        # Log individual interests with confidence for debugging quality issues
        for i in profile.get('interests', []):
            name = i.get('name', '?')
            conf = i.get('confidence', 'unset')
            is_work = i.get('is_work', False)
            in_backend = name in [bi.get('name', '') for bi in profile_for_backend.get('interests', [])]
            status = 'INCLUDED' if in_backend else ('WORK' if is_work else f'EXCLUDED(conf={conf})')
            evidence_snippet = (i.get('evidence', '') or i.get('description', '') or '')[:100]
            logger.info(f"  Interest: {name} | confidence={conf} | {status} | evidence={evidence_snippet}")

        self.progress_callback(
            stage='profile_done',
            stage_label='Profile complete! Enriching with gift intelligence...',
            interests=interest_names
        )

    def _enrich_profile(self, profile_for_backend: Dict, relationship: str,
                       recipient_age: Optional[int], recipient_gender: Optional[str],
                       enriched_profile: Optional[Dict], enhanced_search_terms: Optional[List[str]],
                       quality_filters: Optional[List[str]]) -> tuple:
        """Enrich profile with intelligence layer."""
        if enriched_profile:
            return enriched_profile, enhanced_search_terms or [], quality_filters or []

        if not self.intelligence_layer_available or not self.enrich_profile_simple:
            return None, [], []

        logger.info("Enriching profile with intelligence layer...")
        enriched = self.enrich_profile_simple(
            interests=[i.get('name', '') for i in profile_for_backend.get('interests', [])],
            relationship=relationship or 'close_friend',
            age=recipient_age,
            gender=recipient_gender
        )

        search_terms = []
        for interest_data in enriched.get('enriched_interests', []):
            search_terms.extend(interest_data.get('search_terms', []))

        filters = enriched.get('quality_filters', [])

        logger.info(f"Profile enriched: {len(search_terms)} enhanced search terms")
        return enriched, search_terms, filters

    def _search_products(self, user_id: str, profile_for_backend: Dict,
                        enhanced_search_terms: List[str]) -> tuple:
        """Search retailers for products.

        Returns:
            Tuple of (products, splurge_candidates) where both are lists of product dicts.
        """
        product_rec_count = 10
        inventory_target = product_rec_count * 4

        logger.info("STEP 2: Pulling product inventory...")
        self.progress_callback(
            stage='searching_retailers',
            stage_label='Searching stores for products they\'d actually love...'
        )

        def retailer_progress(retailer, count=None, searching=False, done=False, skipped=False):
            """Progress callback for retailer searches."""
            status = 'searching' if searching else ('done' if done else ('skipped' if skipped else 'unknown'))
            self.progress_callback(
                retailers={retailer: {'status': status, 'count': count or 0}}
            )

        search_result = self.search_products_multi_retailer(
            profile_for_backend,
            etsy_key=os.environ.get('ETSY_API_KEY', ''),
            awin_data_feed_api_key=os.environ.get('AWIN_DATA_FEED_API_KEY', ''),
            ebay_client_id=os.environ.get('EBAY_CLIENT_ID', ''),
            ebay_client_secret=os.environ.get('EBAY_CLIENT_SECRET', ''),
            shareasale_id=os.environ.get('SHAREASALE_AFFILIATE_ID', ''),
            shareasale_token=os.environ.get('SHAREASALE_API_TOKEN', ''),
            shareasale_secret=os.environ.get('SHAREASALE_API_SECRET', ''),
            cj_api_key=os.environ.get('CJ_API_KEY', ''),
            cj_company_id=os.environ.get('CJ_COMPANY_ID', ''),
            cj_publisher_id=os.environ.get('CJ_PUBLISHER_ID', ''),
            amazon_key=os.environ.get('RAPIDAPI_KEY', ''),
            target_count=inventory_target,
            enhanced_search_terms=enhanced_search_terms,
            progress_callback=retailer_progress,
        )

        # Unpack dict return; isinstance guard for safety if ever called differently
        if isinstance(search_result, dict):
            products = search_result.get('products', [])
            splurge_candidates = search_result.get('splurge_candidates', [])
        else:
            products = search_result
            splurge_candidates = []

        if len(products) == 0:
            raise ValueError("We're having trouble loading gift ideas right now. Please try again in a few minutes.")

        logger.info(f"Inventory: {len(products)} products, {len(splurge_candidates)} splurge candidates")
        self.progress_callback(
            product_count=len(products),
            stage='filtering',
            stage_label=f'Found {len(products)} products! Filtering for quality...'
        )

        return products, splurge_candidates

    def _apply_filters(self, products: List[Dict], profile: Dict,
                      quality_filters: Optional[List[str]]) -> List[Dict]:
        """Apply quality and smart filters to products."""
        # Intelligence layer filters
        if quality_filters and self.should_filter_product:
            original_count = len(products)
            products = [
                p for p in products
                if not self.should_filter_product(p.get('title', '') or p.get('name', ''), quality_filters)
            ]
            logger.info(f"Intelligence filters removed {original_count - len(products)} inappropriate products ({len(products)} remaining)")

        # Category blocklist — remove products that should never be gift recommendations
        # (religious ceremony items, baby supplies, industrial goods, etc.)
        # These leak through because the DB has 80k products with loose keyword tags.
        from post_curation_cleanup import _is_wrong_category_for_replacement
        pre_blocklist = len(products)
        products = [
            p for p in products
            if not _is_wrong_category_for_replacement(p.get('title', '') or p.get('name', ''))
        ]
        blocked = pre_blocklist - len(products)
        if blocked:
            logger.info(f"Category blocklist removed {blocked} products ({len(products)} remaining)")

        # Smart filters (work exclusion, passive/active, etc.)
        products = self.apply_smart_filters(products, profile)
        logger.info(f"After smart filters: {len(products)} products")

        return products

    def _curate_gifts(self, user_id: str, profile_for_backend: Dict, products: List[Dict],
                     recipient_type: str, relationship: str, enhanced_search_terms: List[str],
                     enriched_profile: Optional[Dict], splurge_candidates=None) -> tuple:
        """Curate gifts using AI."""
        product_rec_count = 10

        logger.info("STEP 3: Selecting best gifts from inventory...")
        self.progress_callback(
            stage='curating',
            stage_label='AI is handpicking the perfect gifts...'
        )

        # Build enrichment context
        enrichment_context = {}
        if enriched_profile:
            enrichment_context = {
                'demographics': enriched_profile.get('demographics', {}),
                'trending_items': enriched_profile.get('trending_items', []),
                'anti_recommendations': enriched_profile.get('anti_recommendations', []),
                'relationship_guidance': enriched_profile.get('relationship_guidance', {}),
                'price_guidance': enriched_profile.get('price_guidance', {}),
                'enriched_interests': enriched_profile.get('enriched_interests', []),
            }

        # REVENUE OPTIMIZATION: Intelligent pre-filtering
        products_for_curator = self._optimize_product_selection(
            products, profile_for_backend, relationship
        )

        # INTEREST ONTOLOGY: Enrich profile with thematic intelligence (zero API cost)
        # ⚠️ OPUS-ONLY: Do not modify the ontology wiring or briefing format.
        # See interest_ontology.py docstring for what's safe to change.
        ontology_briefing = None
        try:
            from interest_ontology import enrich_profile_with_ontology
            ontology_result = enrich_profile_with_ontology(profile_for_backend)
            ontology_briefing = ontology_result.get('curator_briefing', '')
            if ontology_briefing:
                logger.info(f"Ontology enrichment: {len(ontology_result.get('themes', []))} themes, "
                           f"philosophy={ontology_result.get('gift_philosophy', {})}")
        except ImportError:
            logger.info("interest_ontology not available, proceeding without thematic enrichment")
        except Exception as e:
            logger.warning(f"Ontology enrichment failed (continuing without): {e}")

        # Curate with Claude
        curated = self.curate_gifts(
            profile_for_backend, products_for_curator, recipient_type, relationship,
            self.claude_client, rec_count=product_rec_count + 4,
            enhanced_search_terms=enhanced_search_terms,
            enrichment_context=enrichment_context,
            model=self.curator_model,
            ontology_briefing=ontology_briefing,
            splurge_candidates=splurge_candidates
        )

        product_gifts = curated.get('product_gifts', [])
        experience_gifts = curated.get('experience_gifts', [])
        splurge_item = curated.get('splurge_item')

        # Opus fix: hallucination grounding (Mar 3 2026)
        # Resolve curator selections by inventory_id → real product URL.
        # The curator returns a 1-indexed item number which is far more reliable than
        # a copied URL. When the URL is wrong but the id is valid, fix the URL.
        product_gifts = self._ground_curator_selections(product_gifts, products_for_curator)

        # Ground the splurge item separately against the combined inventory
        # (splurge candidates were appended to the prompt inventory after regular products)
        if splurge_item:
            grounded_splurge = self._ground_curator_selections(
                [splurge_item],
                products_for_curator + (splurge_candidates or [])
            )
            splurge_item = grounded_splurge[0] if grounded_splurge else None
            if splurge_item:
                logger.info(f"Splurge item grounded: {splurge_item.get('name', 'unknown')}")
            else:
                logger.warning("Splurge item failed grounding — dropped")

        # Fallback: if curator returned nothing usable, build minimal set from inventory
        if not product_gifts:
            logger.warning("Curator returned zero grounded products — building fallback from inventory")
            product_gifts = self._build_fallback_selections(
                products_for_curator, profile_for_backend, product_rec_count
            )

        # Track recommended products for learning
        all_tracked = product_gifts + ([splurge_item] if splurge_item else [])
        self._track_recommendations(all_tracked)

        return product_gifts, experience_gifts, splurge_item

    def _optimize_product_selection(self, products: List[Dict], profile: Dict,
                                    relationship: str) -> List[Dict]:
        """Apply revenue optimization to select best products for curator."""
        if not self.revenue_optimizer_available:
            logger.warning("Revenue optimizer not available, sending all products to curator")
            return products

        try:
            logger.info(f"Pre-filtering: {len(products)} products before curator")

            # Track interests for learning
            if self.track_profile_interests:
                self.track_profile_interests(profile)

            # Smart filter: 100 products → 30 high-quality candidates
            if self.intelligent_product_filter:
                products_filtered = self.intelligent_product_filter(
                    products=products,
                    profile=profile,
                    relationship=relationship,
                    target_count=30  # Curator gets 30 products instead of 100
                )
                logger.info(f"After intelligent pre-filtering: {len(products_filtered)} high-quality products")
                return products_filtered

        except Exception as e:
            logger.error(f"Pre-filtering failed: {e}, sending all products to curator")

        return products

    def _ground_curator_selections(self, product_gifts: List[Dict], inventory: List[Dict]) -> List[Dict]:
        """Resolve curator selections to real inventory products using inventory_id.

        The curator returns inventory_id (1-indexed item number from the numbered
        list it was shown) and product_url. The id is reliable — it's just a small
        integer. The URL may be hallucinated, truncated, or corrupted.

        Resolution order:
        1. inventory_id → real product (most reliable)
        2. product_url direct match (if URL is correct)
        3. Fuzzy title match (last resort)
        4. Drop (true hallucination — product doesn't exist)

        Returns the product_gifts list with corrected URLs.
        """
        if not product_gifts or not inventory:
            return product_gifts

        # Build lookups: 1-indexed item number → product, and URL set
        idx_to_product = {}
        url_to_product = {}
        for i, p in enumerate(inventory, 1):
            link = (p.get('link') or '').strip()
            if link:
                idx_to_product[i] = p
                url_to_product[link] = p
                url_to_product[link.rstrip('/')] = p

        grounded = []
        stats = {'id_resolved': 0, 'url_matched': 0, 'title_matched': 0, 'hallucinated': 0}

        for gift in product_gifts:
            inv_id = gift.get('inventory_id')
            url = (gift.get('product_url') or '').strip()
            url_norm = url.rstrip('/')
            name = gift.get('name', '<unnamed>')[:60]
            resolved_product = None

            # Strategy 1: Resolve by inventory_id (most reliable — it's just a number)
            if inv_id is not None:
                try:
                    inv_id_int = int(inv_id)
                    if inv_id_int in idx_to_product:
                        resolved_product = idx_to_product[inv_id_int]
                        real_url = (resolved_product.get('link') or '').strip()
                        if real_url and url != real_url and url_norm != real_url.rstrip('/'):
                            logger.info(
                                f"GROUNDING: Corrected URL via inventory_id={inv_id_int}: "
                                f"'{name}' — curator URL didn't match, using real URL"
                            )
                            stats['id_resolved'] += 1
                        else:
                            stats['url_matched'] += 1
                except (ValueError, TypeError):
                    pass

            # Strategy 2: URL already matches inventory (no correction needed)
            if not resolved_product:
                if url in url_to_product:
                    resolved_product = url_to_product[url]
                    stats['url_matched'] += 1
                elif url_norm in url_to_product:
                    resolved_product = url_to_product[url_norm]
                    stats['url_matched'] += 1

            # Strategy 3: Fuzzy title match (last resort for total hallucinations)
            if not resolved_product:
                resolved_product = self._fuzzy_match_product(name, inventory)
                if resolved_product:
                    stats['title_matched'] += 1
                    logger.info(f"GROUNDING: Matched by title similarity: '{name}'")

            if resolved_product:
                # Fix the gift dict with real inventory data
                real_url = (resolved_product.get('link') or '').strip()
                gift['product_url'] = real_url
                # Carry over inventory metadata for downstream steps
                if not gift.get('image_url'):
                    gift['image_url'] = (resolved_product.get('image') or
                                         resolved_product.get('thumbnail') or '')
                grounded.append(gift)
            else:
                stats['hallucinated'] += 1
                logger.warning(
                    f"GROUNDING: Hallucinated (no match found): "
                    f"'{name}', inventory_id={inv_id}, url={url[:80]}"
                )

        total = len(product_gifts)
        logger.info(
            f"GROUNDING: {len(grounded)}/{total} resolved — "
            f"id_resolved={stats['id_resolved']}, url_matched={stats['url_matched']}, "
            f"title_matched={stats['title_matched']}, hallucinated={stats['hallucinated']}"
        )

        return grounded

    def _fuzzy_match_product(self, curator_name: str, inventory: List[Dict]) -> Optional[Dict]:
        """Try to find a product in inventory by title word overlap.

        Last-resort matching when both inventory_id and URL failed. Requires
        at least 3 overlapping content words and 50% overlap ratio.
        """
        if not curator_name or not inventory:
            return None

        stop = {'the', 'a', 'an', 'and', 'or', 'for', 'of', 'in', 'to', 'with',
                'by', 'on', 'at', 'from', 'is', 'it', 'this', 'that', '-', '—', '|'}
        curator_words = set(curator_name.lower().split()) - stop

        if len(curator_words) < 2:
            return None

        best_score = 0
        best_product = None

        for p in inventory:
            title = (p.get('title') or '').lower()
            title_words = set(title.split()) - stop
            if not title_words:
                continue

            overlap = len(curator_words & title_words)
            # Require at least 3 word overlap and 50% of curator's title words
            if overlap >= 3 and overlap / len(curator_words) >= 0.5:
                if overlap > best_score:
                    best_score = overlap
                    best_product = p

        return best_product

    def _build_fallback_selections(self, inventory: List[Dict], profile: Dict,
                                   count: int = 10) -> List[Dict]:
        """Build minimal product_gifts from top inventory when curator fails entirely.

        This is a last resort — picks diverse products from inventory and constructs
        gift dicts that will pass through cleanup and formatting.
        """
        if not inventory:
            return []

        # Score products by interest diversity
        interest_seen = {}
        source_seen = {}
        selected = []

        for p in inventory:
            if len(selected) >= count + 4:  # Extra buffer for cleanup to trim
                break

            interest = (p.get('interest_match') or 'general').lower()
            source = (p.get('source_domain') or 'unknown').lower()
            link = (p.get('link') or '').strip()

            if not link:
                continue
            if interest_seen.get(interest, 0) >= 2:
                continue
            if source_seen.get(source, 0) >= 4:
                continue

            interest_seen[interest] = interest_seen.get(interest, 0) + 1
            source_seen[source] = source_seen.get(source, 0) + 1

            title = p.get('title', 'Gift')
            snippet = (p.get('snippet') or '')[:80]

            selected.append({
                'name': title,
                'description': snippet,
                'why_perfect': self._build_backfill_why_perfect(p),
                'where_to_buy': p.get('source_domain', 'Online'),
                'product_url': link,
                'image_url': p.get('image') or p.get('thumbnail') or '',
                'confidence_level': 'safe_bet',
                'gift_type': 'physical',
                'interest_match': p.get('interest_match', ''),
            })

        logger.info(f"FALLBACK: Built {len(selected)} product selections from inventory")
        return selected

    @staticmethod
    def _build_backfill_why_perfect(product: Dict) -> str:
        """Build a why_perfect for backfill/fallback products that isn't generic filler.

        Uses the product title, interest match, and snippet to construct something
        that at least names the product and connects it to the interest.
        """
        interest = product.get('interest_match', '')
        title = (product.get('title') or 'this').strip()
        snippet = (product.get('snippet') or '').strip()

        # Clean the title for use in a sentence
        # Truncate overly long marketplace titles
        title_words = title.split()
        if len(title_words) > 8:
            title_short = ' '.join(title_words[:8])
        else:
            title_short = title

        if interest and snippet:
            # Best case: we have interest AND description
            snippet_clean = snippet[:100].rstrip('.').strip()
            return (f"Picked for their {interest} side — {snippet_clean.lower()}. "
                    f"Something they'd actually want but probably wouldn't grab for themselves.")
        elif interest:
            return (f"A solid find for their {interest} passion — {title_short.lower()} "
                    f"that hits the mark.")
        else:
            return f"A thoughtful pick — {title_short.lower()} that adds something personal to the set."

    def _track_recommendations(self, product_gifts: List[Dict]):
        """Track recommended products for learning loop."""
        if not self.revenue_optimizer_available or not self.track_curation_outcome:
            return

        try:
            for gift in product_gifts:
                product_id = gift.get('product_id', '') or gift.get('product_url', '')
                retailer = gift.get('source_domain', '') or gift.get('retailer', '')
                if product_id and retailer:
                    self.track_curation_outcome({'product_id': product_id, 'retailer': retailer}, 'recommended')
        except Exception as e:
            logger.error(f"Failed to track recommended products: {e}")

    def _cleanup_curation(self, user_id: str, product_gifts: List[Dict],
                         experience_gifts: List[Dict], products: List[Dict],
                         profile: Dict) -> tuple:
        """Post-curation cleanup and validation."""
        product_rec_count = 10

        self.progress_callback(
            stage='cleanup',
            stage_label='Curating experiences and validating links...'
        )

        # Product cleanup (brand dedup, category dedup, interest spread)
        if self.cleanup_curated_gifts:
            try:
                interest_names = [i.get('name', '').lower() for i in profile.get('interests', []) if i.get('name')]
                product_gifts = self.cleanup_curated_gifts(product_gifts, products, rec_count=product_rec_count, profile_interests=interest_names)
                logger.info(f"After post-curation cleanup: {len(product_gifts)} products")
            except Exception as e:
                logger.error(f"Post-curation cleanup failed (using raw curator output): {e}")

        # Experience cleanup (filter workplace/work-themed)
        experience_gifts = self.filter_workplace_experiences(experience_gifts, profile)
        experience_gifts = self.filter_work_themed_experiences(experience_gifts, profile)
        logger.info(f"After workplace/work-themed experience filter: {len(experience_gifts)} experiences")

        return product_gifts, experience_gifts

    def _build_recommendations(self, user_id: str, product_gifts: List[Dict],
                              experience_gifts: List[Dict], products: List[Dict],
                              profile: Dict, recipient_age: Optional[int],
                              recipient_gender: Optional[str]) -> List[Dict]:
        """Build final recommendation objects."""
        self.progress_callback(
            stage='images',
            stage_label='Validating every link and image...'
        )

        # Build image map
        product_url_to_image = self._build_image_map(products)
        valid_product_urls = self._build_valid_url_set(products)

        all_recommendations = []

        # Add physical products
        all_recommendations.extend(self._format_product_recommendations(
            product_gifts, valid_product_urls, product_url_to_image, products
        ))

        # Add experience gifts
        all_recommendations.extend(self._format_experience_recommendations(
            experience_gifts, products, profile, recipient_age, recipient_gender
        ))

        logger.info(f"Total recommendations: {len(all_recommendations)}")
        return all_recommendations

    def _build_image_map(self, products: List[Dict]) -> Dict[str, str]:
        """Build map of product URLs to image URLs."""
        product_url_to_image = {}
        for p in products:
            raw_link = (p.get('link') or '').strip()
            if raw_link:
                link = self.normalize_product_url(raw_link)
                if link:
                    img = (p.get('image_url') or p.get('image') or p.get('thumbnail') or '').strip()
                    product_url_to_image[link] = img
                if raw_link and raw_link not in product_url_to_image:
                    product_url_to_image[raw_link] = (p.get('image_url') or p.get('image') or p.get('thumbnail') or '').strip()
        return product_url_to_image

    def _build_valid_url_set(self, products: List[Dict]) -> set:
        """Build set of valid product URLs."""
        valid_urls = set()
        for p in products:
            raw_link = (p.get('link') or '').strip()
            if raw_link:
                valid_urls.add(raw_link)
                valid_urls.add(self.normalize_product_url(raw_link))
        return valid_urls

    def _format_product_recommendations(self, product_gifts: List[Dict],
                                       valid_product_urls: set,
                                       product_url_to_image: Dict[str, str],
                                       inventory: List[Dict] = None) -> List[Dict]:
        """Format physical product recommendations."""
        # Build URL→price lookup from inventory pool — source of truth for price.
        # The curator doesn't output price (removed from schema to avoid "from product" literal).
        url_to_price: Dict[str, str] = {}
        for p in (inventory or []):
            raw = (p.get('link') or '').strip()
            price_val = (p.get('price') or '').strip()
            if raw and price_val:
                url_to_price[raw] = price_val
                url_to_price[self.normalize_product_url(raw)] = price_val

        recommendations = []

        for gift in product_gifts:
            product_url = (gift.get('product_url') or '').strip()

            # Validate URL exists in inventory
            if product_url not in valid_product_urls and self.normalize_product_url(product_url) not in valid_product_urls:
                continue

            # Get image
            image_url = product_url_to_image.get(product_url, '') or product_url_to_image.get(self.normalize_product_url(product_url), '')

            # Skip bad URLs
            if self.is_bad_product_url(product_url):
                product_url = ''
                image_url = ''
            if not product_url:
                continue

            # Look up price from inventory pool (reliable) rather than curator output (unreliable)
            price_display = url_to_price.get(product_url) or url_to_price.get(self.normalize_product_url(product_url), '')

            recommendations.append({
                'name': gift.get('name', 'Unknown Product'),
                'description': gift.get('description', ''),
                'why_perfect': gift.get('why_perfect', ''),
                'price_range': price_display,
                'where_to_buy': gift.get('where_to_buy', 'Online'),
                'product_url': product_url,
                'purchase_link': self._apply_affiliate_tag(product_url),
                'image_url': image_url,
                'image': image_url,
                'gift_type': 'physical',
                'confidence_level': gift.get('confidence_level', 'safe_bet'),
                'is_splurge': gift.get('is_splurge', False),
                'interest_match': gift.get('interest_match', ''),
                'is_direct_link': True,
                'link_source': 'serpapi_search'
            })

        return recommendations

    def _format_experience_recommendations(self, experience_gifts: List[Dict],
                                          products: List[Dict], profile: Dict,
                                          recipient_age: Optional[int],
                                          recipient_gender: Optional[str]) -> List[Dict]:
        """Format experience recommendations with regional context."""
        # Get location context
        loc_ctx = profile.get('location_context') or {}
        city_region = (loc_ctx.get('city_region') or '').strip()
        state_val = (loc_ctx.get('state') or '').strip()
        specific_places = loc_ctx.get('specific_places') or []

        # Sanitize null-ish strings that Claude sometimes outputs instead of null
        _NULL_LOCATION = {'n/a', 'null', 'none', 'unknown', 'not available', 'not specified', 'unknown location'}
        if city_region.lower() in _NULL_LOCATION:
            city_region = ''
        if state_val.lower() in _NULL_LOCATION:
            state_val = ''

        search_geography = city_region or ''
        if state_val and state_val not in search_geography:
            search_geography = f"{search_geography} {state_val}".strip()
        if not search_geography and specific_places:
            first_place = (specific_places[0] or '').strip()
            if first_place and len(first_place) > 1:
                search_geography = first_place
        if not search_geography:
            search_geography = 'near me'

        # Get regional intelligence
        regional_context, local_events = self._get_regional_intelligence(
            city_region, state_val, recipient_age, recipient_gender
        )

        recommendations = []

        for exp in experience_gifts:
            # Backfill materials
            materials_list = self._backfill_materials_links(
                exp.get('materials_needed', []), products
            )

            # Build description with regional context
            full_description = self._build_experience_description(
                exp, materials_list, regional_context
            )

            # Get location details
            location_info = ""
            if exp.get('location_specific'):
                location_info = f" | {exp.get('location_details', 'Location-based')}"

            exp_name = exp.get('name', 'experience')
            location_details = (exp.get('location_details') or '').strip()
            # Prefer user's actual city for link generation over curator's guessed location_details
            search_loc = search_geography if (search_geography and search_geography != 'near me') else (location_details or search_geography)

            # Handle both old format (reservation_link/venue_website from curator)
            # and new format (no URLs from curator, we generate everything)
            reservation_link = ''
            venue_website = ''
            old_res = (exp.get('reservation_link') or '').strip()
            old_venue = (exp.get('venue_website') or '').strip()
            if old_res:
                reservation_link = self._validate_or_replace_experience_link(
                    old_res, exp_name, search_loc, 'reservation'
                )
            if old_venue:
                venue_website = self._validate_or_replace_experience_link(
                    old_venue, location_details or exp_name, search_loc, 'venue'
                )

            primary_link = reservation_link or venue_website
            experience_search_fallback = False

            # Use experience_category for better provider matching (new format)
            # Fall back to name/description classification (old format)
            exp_category = (exp.get('experience_category') or '').strip()
            exp_desc = exp.get('description', '')
            experience_provider_links = self._get_provider_links(
                exp_name, search_loc, exp_desc, category=exp_category
            )

            # Determine primary link
            if not primary_link and experience_provider_links:
                primary_link = experience_provider_links[0]['url']
                experience_search_fallback = False
            elif not primary_link and exp.get('name'):
                primary_link = self._make_experience_search_link(exp_name, search_loc)
                experience_search_fallback = True
            if not primary_link and materials_list:
                first_url = (materials_list[0].get('product_url') or '').strip()
                if first_url and not materials_list[0].get('is_search_link'):
                    primary_link = first_url

            # Determine if bookable or DIY
            is_bookable = bool(experience_provider_links or reservation_link or venue_website)
            is_diy = bool(materials_list and not is_bookable)

            # Use estimated_price from curator if available, otherwise "Variable"
            price_range = (exp.get('estimated_price') or '').strip() or 'Variable'

            # Thumbnail waterfall for experiences:
            # 1. Spotify artist photo — for concert/music experiences where we know the artist
            # 2. First matched material thumbnail — for DIY experiences (shows the centrepiece item)
            # 3. Empty string — template renders category emoji as fallback
            exp_image_url = ''
            artist_images = profile.get('spotify_artist_images', {})
            if exp_category == 'concerts' and artist_images:
                exp_name_lower = exp_name.lower()
                for artist_name, img_url in artist_images.items():
                    if artist_name.lower() in exp_name_lower:
                        exp_image_url = img_url
                        logger.info(f"Experience thumbnail: matched artist '{artist_name}' for '{exp_name}'")
                        break
                # If no direct name match, use the top artist as a generic music thumbnail
                if not exp_image_url:
                    exp_image_url = next(iter(artist_images.values()), '')
            if not exp_image_url and is_diy and materials_list:
                for m in materials_list:
                    thumb = m.get('thumbnail')
                    if thumb:
                        exp_image_url = thumb
                        logger.debug(f"Experience thumbnail: using material thumbnail for '{exp_name}'")
                        break

            recommendations.append({
                'name': exp.get('name', 'Experience Gift'),
                'description': full_description,
                'why_perfect': exp.get('why_perfect', ''),
                'price_range': price_range,
                'where_to_buy': f"Experience{location_info}",
                'product_url': primary_link or None,
                'purchase_link': self._apply_affiliate_tag(primary_link) if primary_link else None,
                'reservation_link': self._apply_affiliate_tag(reservation_link) if reservation_link else None,
                'venue_website': venue_website or None,
                'experience_search_fallback': experience_search_fallback,
                'experience_providers': experience_provider_links,
                'image_url': exp_image_url,
                'gift_type': 'experience',
                'experience_category': exp_category,
                'confidence_level': exp.get('confidence_level', 'adventurous'),
                'materials_needed': materials_list,
                'location_specific': exp.get('location_specific', False),
                'how_to_make_it_special': exp.get('how_to_make_it_special', ''),
                'is_bookable': is_bookable,
                'is_diy': is_diy,
                'regional_context': regional_context.get('city_vibe', '') if regional_context else '',
                'local_events': local_events[:3] if local_events else [],
            })

        return recommendations

    def _get_regional_intelligence(self, city_region: str, state_val: str,
                                   recipient_age: Optional[int],
                                   recipient_gender: Optional[str]) -> tuple:
        """Get regional context and local events."""
        regional_context = {}
        local_events = []

        if not self.regional_intelligence_available or not city_region or not state_val:
            return regional_context, local_events

        try:
            current_month = datetime.now().month

            # Get regional culture context
            if self.get_regional_context:
                regional_context = self.get_regional_context(
                    city=city_region,
                    state=state_val,
                    age=recipient_age,
                    gender=recipient_gender
                )
                logger.info(f"Regional context: {city_region}, {state_val} - {regional_context.get('city_vibe', 'N/A')}")

            # Get local events
            if self.get_local_events_for_month:
                local_events = self.get_local_events_for_month(city_region, current_month)
                if local_events:
                    logger.info(f"Local events found: {len(local_events)} for {city_region} in month {current_month}")

        except Exception as e:
            logger.warning(f"Regional intelligence lookup failed: {e}")

        return regional_context, local_events

    def _build_experience_description(self, exp: Dict, materials_list: List[Dict],
                                     regional_context: Dict) -> str:
        """Build structured experience description."""
        parts = []

        # Lead with the curator's description (the pitch)
        base_desc = (exp.get('description') or '').strip()
        if base_desc:
            parts.append(base_desc)

        # Add regional flavor inline (not as a separate block)
        if regional_context and regional_context.get('city_vibe'):
            vibe = regional_context['city_vibe'].replace('_', ' ').title()
            parts.append(f"Local vibe: {vibe}")

        # How to execute — the actionable plan
        how_to = (exp.get('how_to_execute') or '').strip()
        if how_to:
            parts.append(f"The plan: {how_to}")

        return '\n\n'.join(parts).strip()

    def _validate_or_replace_experience_link(self, url: str, name: str,
                                            location: str, link_type: str) -> str:
        """Validate experience URL or replace with search link."""
        url = (url or '').strip()
        if not url:
            return ''

        if self._validate_experience_url(url):
            logger.info(f"EXP LINK: Validated {link_type} for '{name[:40]}': {url[:80]}")
            return url
        else:
            logger.info(f"EXP LINK: Rejected bad {link_type} for '{name[:40]}': {url[:80]}")
            return self._make_experience_search_link(name, location, link_type)

    def _get_provider_links(self, exp_name: str, location: str, description: str, category: str = '') -> List[Dict]:
        """Get curated experience provider links."""
        if not self.get_experience_providers:
            return []

        try:
            links = self.get_experience_providers(exp_name, location=location, description=description, category=category or None)
            # Apply affiliate tracking
            for link in links:
                link['url'] = self._apply_affiliate_tag(link['url'])
            return links
        except Exception as e:
            logger.warning(f"Experience provider lookup failed: {e}")
            return []

    def _process_images(self, user_id: str, recommendations: List[Dict]) -> List[Dict]:
        """Process and validate images for all recommendations."""
        self.progress_callback(
            stage='images',
            stage_label=f'Almost there — validating images for {len(recommendations)} gifts...'
        )

        # Backfill thumbnails using image fetcher
        if self.image_fetching_available and self.process_recommendation_images:
            try:
                recommendations = self.process_recommendation_images(recommendations)
                with_images = sum(
                    1 for r in recommendations
                    if r.get('image_url') and 'placeholder' not in (r.get('image_url') or '').lower()
                )
                total_recs = len(recommendations)
                pct = int(with_images / total_recs * 100) if total_recs else 0
                logger.info(f"IMAGE_QUALITY: {with_images}/{total_recs} real ({pct}%)")
                # Track as structured metric
                try:
                    from site_stats import track_event
                    if pct < 70:
                        track_event('low_image_quality')
                except Exception:
                    pass
            except Exception as img_err:
                logger.warning(f"Image backfill failed (continuing): {img_err}")

        # Add placeholder fallbacks for physical products
        for rec in recommendations:
            if rec.get('gift_type') != 'physical':
                continue
            img = (rec.get('image_url') or '').strip()
            if not img or not img.startswith('http'):
                name_safe = (rec.get('name') or 'Gift')[:30].replace(' ', '+')
                rec['image_url'] = f"https://via.placeholder.com/400x400/667eea/ffffff?text={quote(name_safe)}"
                rec['image_source'] = rec.get('image_source') or 'placeholder_fallback'
                rec['image_is_fallback'] = True

        return recommendations

    # ========================================================================
    # HELPER METHODS (imported from giftwise_app.py)
    # ========================================================================

    def _apply_affiliate_tag(self, url):
        """Apply affiliate tracking to an outbound product URL."""
        if not url or not isinstance(url, str):
            return url

        # Step 1: Amazon affiliate tag
        if self.amazon_affiliate_tag and 'amazon.com' in url.lower():
            if 'tag=' not in url:
                sep = '&' if '?' in url else '?'
                url = f"{url}{sep}tag={self.amazon_affiliate_tag}"

        return url

    def _validate_experience_url(self, url, timeout=3):
        """Validate a curator-provided experience URL."""
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            return False

        # Reject obvious search pages and bare domains
        try:
            from link_validation import is_search_url, is_generic_domain_url
            if is_search_url(url) or is_generic_domain_url(url):
                return False
        except ImportError:
            pass

        # Quick HEAD check
        try:
            import requests
            resp = requests.head(url, timeout=timeout, allow_redirects=True, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Giftwise/1.0)'
            })
            return resp.status_code < 400
        except Exception:
            try:
                import requests
                resp = requests.get(url, timeout=timeout, stream=True, allow_redirects=True, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; Giftwise/1.0)'
                })
                return resp.status_code < 400
            except Exception:
                return False

    def _make_experience_search_link(self, experience_name, location, link_type='book'):
        """Generate a focused Google search link for finding/booking an experience."""
        query = self._focus_experience_query(experience_name, location)
        return f"https://www.google.com/search?q={quote(query)}"

    def _focus_experience_query(self, experience_name, location):
        """Turn a verbose experience description into a focused search query."""
        name = experience_name.strip()
        loc = location.strip() if location else ''

        # Strip filler phrases
        filler = [
            r'^consultation\s+session\s+with\s+',
            r'^book\s+a\s+',
            r'^gift\s+of\s+a?\s*',
            r'^experience:\s*',
            r'^arrange\s+a\s+',
            r'^plan\s+a\s+',
            r'^organize\s+a\s+',
            r'^schedule\s+a\s+',
            r'^sign\s+(?:them|up)\s+for\s+',
            r'^enroll\s+(?:them\s+)?in\s+',
        ]
        cleaned = name
        for pattern in filler:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()

        # Detect service-provider experiences and restructure
        provider_patterns = [
            (r'([\w\s]+?)\s+specializing\s+in\s+(.+)', lambda m: f"{m.group(1).strip()}s in {loc} specializing in {m.group(2).strip()}"),
            (r'([\w\s]+?)\s+who\s+specialize[s]?\s+in\s+(.+)', lambda m: f"{m.group(1).strip()}s in {loc} specializing in {m.group(2).strip()}"),
            (r'([\w\s]+?)\s+focused\s+on\s+(.+)', lambda m: f"{m.group(1).strip()} {m.group(2).strip()} in {loc}"),
            (r'([\w\s]+?)\s+(?:class|classes|lesson|lessons|workshop|workshops)\b(.*)', lambda m: f"{m.group(1).strip()} {m.group(0).split(m.group(1))[1].strip()} in {loc}"),
        ]

        for pattern, builder in provider_patterns:
            match = re.match(pattern, cleaned, flags=re.IGNORECASE)
            if match and loc:
                return builder(match)

        # For ticket/event experiences
        ticket_words = ['ticket', 'tickets', 'tour', 'show', 'concert', 'game', 'match']
        if any(w in cleaned.lower() for w in ticket_words):
            return f"{cleaned} {loc}".strip()

        # Default
        if loc:
            return f"{cleaned} in {loc}".strip()
        return cleaned

    def _backfill_materials_links(self, materials_list, products):
        """Ensure every materials_needed item has a working link."""
        if not materials_list:
            return materials_list

        # Import from giftwise_app
        from giftwise_app import _backfill_materials_links
        return _backfill_materials_links(
            materials_list, products, self.is_bad_product_url,
            affiliate_tag=self.amazon_affiliate_tag
        )
