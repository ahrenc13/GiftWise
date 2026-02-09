"""
SMART FILTERS - Filter gift recommendations intelligently
- Work Exclusion: Don't suggest work-related gifts
- Passive/Active: Don't suggest sports equipment to people who just watch
- Workplace Experiences: Don't suggest tours of their workplace

Author: Chad + Claude
Date: February 2026
"""

import logging
import re

logger = logging.getLogger(__name__)


class WorkExclusionFilter:
    """Filter out gift suggestions that are obviously work-related"""
    
    # Keywords that indicate professional/work items
    PROFESSIONAL_KEYWORDS = [
        'professional development', 'certification', 'training course',
        'industry conference', 'trade show', 'workshop', 'seminar',
        'safety equipment', 'safety tools', 'safety awareness',
        'work uniform', 'protective gear', 'industry tools',
        'professional membership', 'license', 'credential',
        'continuing education', 'ceu', 'ce credits'
    ]
    
    # Indicators of professional reference materials
    PROFESSIONAL_BOOK_INDICATORS = [
        'handbook', 'manual', 'textbook', 'reference', 'guide',
        'clinical', 'medical reference', 'professional guide',
        'certification prep', 'exam prep', 'study guide',
        'encyclopedia', 'compendium', 'protocols', 'procedures'
    ]
    
    @staticmethod
    def is_work_related_gift(product, interest_name, profile):
        """
        Check if product is work-related and should be excluded
        
        Args:
            product: Product dict with title, snippet
            interest_name: Which interest this product matches
            profile: Full user profile
            
        Returns:
            bool: True if should be excluded
        """
        
        product_title = (product.get('title') or '').lower()
        product_snippet = (product.get('snippet') or '').lower()
        
        # Defensive: Handle missing location_context
        location_context = profile.get('location_context') or {}
        city = location_context.get('city_region', '').lower()
        
        # Get all interests to check for work flags
        interests = profile.get('interests', [])
        work_interests = [i for i in interests if i.get('is_work', False)]
        
        # Check if no work interests, nothing to exclude
        if not work_interests:
            return False
        
        # Build key terms from work interests (not just full names)
        work_terms = set()
        for work_interest in work_interests:
            work_name = (work_interest.get('name') or '').lower()
            work_desc = (work_interest.get('description') or '').lower()
            
            # Add full name
            work_terms.add(work_name)
            
            # Extract key terms (words that are likely unique to the work domain)
            # Split on common separators and add significant terms
            for term in work_name.split():
                if len(term) > 3 and term not in ['and', 'the', 'for', 'with']:
                    work_terms.add(term)
            
            # Extract work venues if present
            if 'works at' in work_desc or 'work at' in work_desc:
                try:
                    match = re.search(r'works? (?:at|for) ([a-z0-9\s]+?)(?:\.|,|;|$)', work_desc)
                    if match:
                        venue = match.group(1).strip()
                        work_terms.add(venue)
                        # Add individual words from venue name
                        for word in venue.split():
                            if len(word) > 3:
                                work_terms.add(word)
                except:
                    pass
        
        # Check 1: Professional books/reference materials about work topics
        is_reference_book = any(
            indicator in product_title or indicator in product_snippet 
            for indicator in WorkExclusionFilter.PROFESSIONAL_BOOK_INDICATORS
        )
        
        if is_reference_book:
            # Check if book topic overlaps with work interests
            work_term_matches = sum(1 for term in work_terms if term in product_title or term in product_snippet)
            if work_term_matches >= 2:  # At least 2 work-related terms = professional book about their job
                logger.info(f"EXCLUDED work item: {product.get('title', 'Unknown')[:60]} - Professional reference about work topic")
                return True
        
        # Check 2: Products with professional/work keywords + work topic overlap
        has_work_keywords = any(
            keyword in product_title or keyword in product_snippet
            for keyword in ['professional', 'safety', 'medical', 'emergency', 'clinical', 
                          'training', 'certification', 'equipment', 'gear', 'tools']
        )
        
        if has_work_keywords:
            work_term_matches = sum(1 for term in work_terms if term in product_title or term in product_snippet)
            if work_term_matches >= 2:  # Professional item + work topic = work-related
                logger.info(f"EXCLUDED work item: {product.get('title', 'Unknown')[:60]} - Professional item about work topic")
                return True
        
        # Check 3: Experiences at workplace (original logic)
        for work_interest in work_interests:
            work_name = (work_interest.get('name') or '').lower()
            work_desc = (work_interest.get('description') or '').lower()
            
            # Extract work venue names if present
            work_venues = []
            if 'works at' in work_desc or 'work at' in work_desc:
                try:
                    match = re.search(r'works? (?:at|for) ([a-z0-9\s]+?)(?:\.|,|;|$)', work_desc)
                    if match:
                        venue = match.group(1).strip()
                        work_venues.append(venue)
                        
                        # Special case: Indianapolis Motor Speedway variations
                        if 'motor speedway' in venue or 'speedway' in venue or 'ims' in work_desc.lower():
                            work_venues.extend(['ims', 'indianapolis motor speedway', 'indy 500', 'indianapolis 500'])
                except:
                    pass  # Fail gracefully if parsing fails
            
            # Check for experiences at workplace
            experience_indicators = ['tour', 'visit', 'behind the scenes', 'backstage', 'vip access']
            if any(ind in product_title or ind in product_snippet for ind in experience_indicators):
                # Check if it's at their work venue
                for venue in work_venues:
                    if venue and (venue in product_title or venue in product_snippet):
                        logger.info(f"EXCLUDED work item: {product.get('title', 'Unknown')[:60]} - Experience at workplace: {venue}")
                        return True
        
        return False
    
    @staticmethod
    def filter_products(products, profile):
        """Filter out work-related products"""
        
        # Defensive: Handle None or empty inputs
        if not products:
            return []
        
        if not profile:
            logger.warning("No profile provided to WorkExclusionFilter")
            return products
        
        filtered = []
        excluded_count = 0
        
        for product in products:
            interest = product.get('interest_match', '')
            
            # Check if this is a work-related gift
            if not WorkExclusionFilter.is_work_related_gift(product, interest, profile):
                filtered.append(product)
            else:
                excluded_count += 1
        
        logger.info(f"Work filter removed {excluded_count} items, kept {len(filtered)}")
        return filtered


class ObsoleteFormatFilter:
    """Filter out obsolete media *content* (DVDs, random CDs) and low-effort products.

    Key distinction: we filter the *content format* (a Toto concert DVD), NOT the
    *hardware* (a retro CD player, a turntable, a cassette deck). If someone has
    retro/vinyl/analog signals in their profile, we skip this filter entirely for
    products matched to that interest — those are intentional passion purchases.

    Also catches generic filler items (bumper stickers, rubber bracelets) that
    read as low-effort regardless of interest.
    """

    # Obsolete physical media CONTENT — title keywords
    # These are the discs/tapes themselves, not players/hardware
    OBSOLETE_CONTENT_KEYWORDS = [
        'dvd', 'blu-ray', 'bluray', 'blu ray', 'vhs',
        'laserdisc', 'betamax',
    ]

    # Patterns for media content in title (case-sensitive)
    OBSOLETE_CONTENT_PATTERNS = [
        r'\bDVD\b', r'\bDVDs\b', r'\bVHS\b', r'\bBlu-?[Rr]ay\b',
    ]

    # Generic low-effort gift indicators (always filtered, no exceptions)
    LOW_EFFORT_KEYWORDS = [
        'bumper sticker', 'car sticker', 'fridge magnet',
        'rubber bracelet', 'lanyard', 'wristband',
    ]

    # Retro/analog interest signals — if ANY interest matches these,
    # skip the obsolete content filter for products tied to that interest
    RETRO_SIGNALS = [
        'vinyl', 'record', 'turntable', 'retro', 'analog', 'analogue',
        'cassette', 'tape deck', 'hi-fi', 'hifi', 'audiophile',
        'vintage audio', 'vintage music', 'record collection',
        'record store', 'crate digging',
    ]

    @staticmethod
    def _has_retro_interest(profile):
        """Check if profile has retro/analog audio interests."""
        if not profile:
            return set()
        retro_interest_names = set()
        for interest in profile.get('interests', []):
            name = (interest.get('name') or '').lower()
            desc = (interest.get('description') or '').lower()
            combined = name + ' ' + desc
            if any(signal in combined for signal in ObsoleteFormatFilter.RETRO_SIGNALS):
                retro_interest_names.add(name)
        return retro_interest_names

    @staticmethod
    def is_obsolete_or_low_effort(product, retro_interests=None):
        """Check if product is obsolete content or generic low-effort item.

        Returns (should_exclude, reason) tuple.
        """
        title = (product.get('title') or '').lower()
        snippet = (product.get('snippet') or '').lower()
        combined = title + ' ' + snippet

        # Low-effort items are always filtered regardless of interests
        for keyword in ObsoleteFormatFilter.LOW_EFFORT_KEYWORDS:
            if keyword in combined:
                return True, f"low-effort item: '{keyword}'"

        # If this product matches a retro interest, don't filter it
        if retro_interests:
            product_interest = (product.get('interest_match') or '').lower()
            if product_interest in retro_interests:
                return False, None

        # Check obsolete content keywords
        for keyword in ObsoleteFormatFilter.OBSOLETE_CONTENT_KEYWORDS:
            if keyword in combined:
                return True, f"obsolete media: '{keyword}'"

        # Check regex patterns (case-sensitive: "DVD", "VHS")
        title_raw = product.get('title') or ''
        for pattern in ObsoleteFormatFilter.OBSOLETE_CONTENT_PATTERNS:
            if re.search(pattern, title_raw):
                return True, f"obsolete media pattern: {pattern}"

        return False, None

    @staticmethod
    def filter_products(products, profile=None):
        """Filter out obsolete format and low-effort products."""
        if not products:
            return []

        retro_interests = ObsoleteFormatFilter._has_retro_interest(profile)
        if retro_interests:
            logger.info(f"Retro/analog interests detected: {retro_interests} — allowing vintage media for those interests")

        filtered = []
        excluded_count = 0

        for product in products:
            should_exclude, reason = ObsoleteFormatFilter.is_obsolete_or_low_effort(product, retro_interests)
            if should_exclude:
                excluded_count += 1
                logger.info(
                    "EXCLUDED %s: %s",
                    reason,
                    (product.get('title') or 'Unknown')[:60],
                )
            else:
                filtered.append(product)

        logger.info(f"Obsolete/low-effort filter removed {excluded_count} items, kept {len(filtered)}")
        return filtered


class PassiveActiveFilter:
    """Filter out active products for passive interests (e.g. don't suggest basketballs to people who just watch games)"""
    
    @staticmethod
    def is_active_product(product_title, product_snippet):
        """Check if product requires active participation"""
        
        # Defensive: Handle None values
        title = (product_title or '').lower()
        snippet = (product_snippet or '').lower()
        
        combined_text = title + ' ' + snippet
        
        # Active participation indicators
        active_indicators = [
            'basketball', 'soccer ball', 'football', 
            'golf clubs', 'tennis racket', 'equipment',
            'gear', 'training', 'practice', 'play',
            'workout', 'exercise', 'fitness', 'gym',
            'sports equipment', 'athletic gear'
        ]
        
        return any(indicator in combined_text for indicator in active_indicators)
    
    @staticmethod
    def filter_products(products, profile):
        """Filter out active products for passive interests"""
        
        # Defensive: Handle None or empty inputs
        if not products:
            return []
        
        if not profile:
            logger.warning("No profile provided to PassiveActiveFilter")
            return products
        
        interests = profile.get('interests', [])
        if not interests:
            return products
        
        # Build map of passive interests
        passive_interests = {}
        for interest in interests:
            if interest.get('activity_type') == 'passive':
                passive_interests[interest.get('name', '').lower()] = interest
        
        # If no passive interests, nothing to filter
        if not passive_interests:
            logger.info(f"Activity filter removed 0 items, kept {len(products)}")
            return products
        
        filtered = []
        excluded_count = 0
        
        for product in products:
            interest_match = (product.get('interest_match') or '').lower()
            
            # Check if this matches a passive interest
            if interest_match in passive_interests:
                # Check if product requires active participation
                if PassiveActiveFilter.is_active_product(
                    product.get('title'), 
                    product.get('snippet')
                ):
                    excluded_count += 1
                    logger.info(f"EXCLUDED active item for passive interest: {product.get('title', 'Unknown')[:60]}")
                    continue
            
            filtered.append(product)
        
        logger.info(f"Activity filter removed {excluded_count} items, kept {len(filtered)}")
        return filtered


def apply_smart_filters(products, profile):
    """
    Apply all smart filters to products
    
    Args:
        products: List of product dicts
        profile: Recipient profile dict
    
    Returns:
        Filtered list of products
    """
    
    # Defensive: Validate inputs
    if not products:
        logger.warning("No products to filter")
        return []
    
    if not profile:
        logger.warning("No profile provided for filtering, returning all products")
        return products
    
    logger.info(f"Applying smart filters to {len(products)} products")
    
    # Apply work exclusion filter
    try:
        products = WorkExclusionFilter.filter_products(products, profile)
    except Exception as e:
        logger.error(f"Error in WorkExclusionFilter: {e}")
        # Continue with unfiltered products rather than crash
    
    # Apply passive/active filter
    try:
        products = PassiveActiveFilter.filter_products(products, profile)
    except Exception as e:
        logger.error(f"Error in PassiveActiveFilter: {e}")
        # Continue with unfiltered products rather than crash

    # Apply obsolete format / low-effort filter
    try:
        products = ObsoleteFormatFilter.filter_products(products, profile)
    except Exception as e:
        logger.error(f"Error in ObsoleteFormatFilter: {e}")
        # Continue with unfiltered products rather than crash

    logger.info(f"Smart filters complete: {len(products)} products remaining")
    
    return products


def get_work_venue_phrases(profile):
    """
    Extract work venue/company names from profile
    
    Returns list of phrases like ['indianapolis motor speedway', 'ims', 'acme corp']
    """
    if not profile:
        return []
    
    phrases = []
    interests = profile.get('interests', [])
    
    for interest in interests:
        if not interest.get('is_work'):
            continue
        
        desc = (interest.get('description') or interest.get('evidence', '')).lower()
        name = interest.get('name', '').lower()
        
        # Extract "works at X" or "work at X"
        if 'works at' in desc or 'work at' in desc:
            try:
                match = re.search(r'works? (?:at|for) ([a-z0-9\s]+?)(?:\.|,|;|$)', desc)
                if match:
                    venue = match.group(1).strip()
                    phrases.append(venue)
                    
                    # Special handling for Indianapolis Motor Speedway
                    if 'motor speedway' in venue or 'speedway' in venue or 'ims' in desc:
                        phrases.extend(['ims', 'indianapolis motor speedway', 'indy 500', 'indianapolis 500'])
            except:
                pass  # Fail gracefully
        
        # Add the interest name itself
        if name:
            phrases.append(name)
    
    return list(set(phrases))


def filter_workplace_experiences(experience_gifts, profile):
    """
    Remove experience gifts that are at the recipient's workplace
    Example: Don't suggest Indy 500 tour to someone who works at Indianapolis Motor Speedway
    """
    if not experience_gifts:
        return []
    
    if not profile:
        return experience_gifts
    
    work_phrases = get_work_venue_phrases(profile)
    if not work_phrases:
        return experience_gifts
    
    workplace_indicators = ['behind the scenes', 'backstage', 'vip access', 'tour', 'experience at']
    
    filtered = []
    for exp in experience_gifts:
        # Combine all text fields for checking
        combined = f"{exp.get('name', '')} {exp.get('location_details', '')} {exp.get('description', '')}".lower()
        
        is_workplace = False
        for phrase in work_phrases:
            if phrase.lower() in combined and any(ind in combined for ind in workplace_indicators):
                is_workplace = True
                logger.info(f"EXCLUDED workplace experience: {exp.get('name', 'Unknown')[:60]} - matches work venue '{phrase}'")
                break
        
        if not is_workplace:
            filtered.append(exp)
    
    return filtered


def _word_match(term, text):
    """Check if term appears in text as a whole word/phrase, not as a substring."""
    return bool(re.search(r'\b' + re.escape(term) + r'\b', text))


def get_work_theme_keywords(profile):
    """
    Keywords that indicate an experience is work-themed (IndyCar, EMS, nursing, etc.).
    Used to drop experiences based on work even when not at a specific venue.

    Uses word-boundary matching to prevent false positives from substrings
    (e.g. 'ems' matching inside 'systems', 'ims' matching inside 'animations').
    """
    if not profile:
        return []

    keywords = []

    # Unambiguous work-specific terms (matched with word boundaries)
    specific_work_terms = [
        'indycar', 'indy 500', 'indianapolis motor speedway', 'racing team', 'motorsport',
        'ems', 'paramedic', 'emergency medical', 'ambulance', 'first responder',
        'nursing', 'healthcare administration', 'hospital operations', 'medical staff',
        'firefighter', 'fire department', 'fire station',
        'police', 'law enforcement', 'police department',
    ]

    for i in profile.get('interests', []):
        if not i.get('is_work'):
            continue
        name = (i.get('name') or '').lower()
        if not name:
            continue

        # Only add the full work interest name if it contains clearly work-specific terms
        if any(_word_match(term, name) for term in specific_work_terms):
            keywords.append(name)

        # Add specific variants for known work domains (word-boundary matching)
        if _word_match('indycar', name) or _word_match('indy 500', name) or _word_match('motorsport', name) or _word_match('racing team', name):
            keywords.extend(['indycar', 'indy 500', 'indianapolis motor speedway', 'racing experience', 'motorsport'])
        if _word_match('ems', name) or _word_match('paramedic', name) or _word_match('emergency medical', name):
            keywords.extend(['ems', 'paramedic', 'emergency medical', 'ambulance', 'first responder'])
        if _word_match('nursing', name) or _word_match('healthcare', name) or _word_match('medical', name):
            keywords.extend(['nursing', 'healthcare', 'medical', 'hospital'])
        if _word_match('firefighter', name) or _word_match('fire department', name):
            keywords.extend(['firefighter', 'fire department', 'fire station', 'fire service'])
        if _word_match('police', name) or _word_match('law enforcement', name):
            keywords.extend(['police', 'law enforcement', 'police department'])

    return list(set(kw for kw in keywords if len(kw) > 2))


def filter_work_themed_experiences(experience_gifts, profile):
    """
    Remove experience gifts that are themed around work (IndyCar, EMS, nursing, etc.).
    Call after filter_workplace_experiences so we drop any work-themed experience regardless of venue.

    Uses word-boundary matching to prevent false positives.
    """
    if not experience_gifts or not profile:
        return experience_gifts
    work_keywords = get_work_theme_keywords(profile)
    if not work_keywords:
        return experience_gifts
    logger.info(f"Work-theme keywords for filtering: {work_keywords}")
    filtered = []
    for exp in experience_gifts:
        combined = f"{exp.get('name', '')} {exp.get('description', '')} {exp.get('why_perfect', '')} {exp.get('location_details', '')}".lower()
        matched_kw = next((_word_match(kw, combined) and kw for kw in work_keywords), None)
        if matched_kw:
            logger.info(f"EXCLUDED work-themed experience (matched '{matched_kw}'): {exp.get('name', 'Unknown')[:60]}")
            continue
        filtered.append(exp)
    return filtered
