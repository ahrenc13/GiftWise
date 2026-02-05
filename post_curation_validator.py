"""
POST-CURATION VALIDATOR
Validates the final curated products and replaces dead links with backups

This runs AFTER Claude curates the best gifts, so we only validate what we show.

Author: Chad + Claude
Date: February 2026
"""

import requests
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

VALIDATION_TIMEOUT = 5  # More thorough than search-time validation
MAX_CONCURRENT_VALIDATIONS = 5


def validate_product_link(product, timeout=VALIDATION_TIMEOUT):
    """
    Validate that a product link works
    
    Returns:
        (product, True) if valid
        (product, False) if invalid
    """
    link = product.get('link', '')
    
    if not link or not link.startswith(('http://', 'https://')):
        return (product, False)
    
    try:
        # Try HEAD request first (faster)
        response = requests.head(link, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            return (product, True)
        
        # If HEAD fails, try GET (some servers don't support HEAD)
        response = requests.get(link, timeout=timeout, stream=True, allow_redirects=True)
        response.close()
        
        if response.status_code == 200:
            return (product, True)
        else:
            logger.warning(f"Product link failed validation: {link[:60]}... (status {response.status_code})")
            return (product, False)
            
    except requests.exceptions.Timeout:
        logger.warning(f"Product link timed out: {link[:60]}...")
        return (product, False)
    except Exception as e:
        logger.warning(f"Product link validation error: {link[:60]}... ({str(e)[:50]})")
        return (product, False)


def validate_and_fix_recommendations(curated_products, backup_products, target_count=10):
    """
    Validate curated products and replace dead links with backups
    
    Args:
        curated_products: List of products Claude selected
        backup_products: Full inventory to pull replacements from
        target_count: Number of valid products needed (default 10)
    
    Returns:
        List of validated products with no dead links
    """
    start_time = time.time()
    
    logger.info(f"Validating {len(curated_products)} curated products...")
    
    # Validate curated products in parallel
    valid_products = []
    invalid_products = []
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_VALIDATIONS) as executor:
        futures = [executor.submit(validate_product_link, p) for p in curated_products]
        
        for future in as_completed(futures):
            product, is_valid = future.result()
            if is_valid:
                valid_products.append(product)
            else:
                invalid_products.append(product)
    
    logger.info(f"Validation results: {len(valid_products)} valid, {len(invalid_products)} invalid")
    
    # If we have enough valid products, we're done
    if len(valid_products) >= target_count:
        elapsed = time.time() - start_time
        logger.info(f"All products validated in {elapsed:.1f}s")
        return valid_products[:target_count]
    
    # Need to replace invalid products with backups
    needed = target_count - len(valid_products)
    logger.info(f"Need {needed} replacement products from backup inventory")
    
    # Filter backups: exclude already-used products
    used_links = {p['link'] for p in curated_products}
    available_backups = [p for p in backup_products if p['link'] not in used_links]
    
    if not available_backups:
        logger.warning("No backup products available - returning what we have")
        elapsed = time.time() - start_time
        logger.info(f"Validation complete in {elapsed:.1f}s (only {len(valid_products)} products)")
        return valid_products
    
    # Validate backups until we have enough
    logger.info(f"Validating backup products (have {len(available_backups)} available)...")
    
    replacements = []
    batch_size = min(needed * 2, len(available_backups))  # Check 2x what we need
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_VALIDATIONS) as executor:
        futures = [executor.submit(validate_product_link, p) for p in available_backups[:batch_size]]
        
        for future in as_completed(futures):
            product, is_valid = future.result()
            if is_valid:
                replacements.append(product)
                if len(replacements) >= needed:
                    break
    
    logger.info(f"Found {len(replacements)} valid replacement products")
    
    # Combine valid originals + replacements
    final_products = valid_products + replacements
    
    elapsed = time.time() - start_time
    logger.info(f"Validation complete in {elapsed:.1f}s: {len(final_products)} valid products")
    
    return final_products[:target_count]
