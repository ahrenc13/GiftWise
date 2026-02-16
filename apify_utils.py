"""
Apify Scraper Utilities
Generic Apify actor runner with polling and progress tracking

Eliminates code duplication between Instagram and TikTok scrapers
(previously 85% identical implementations)

Author: Chad + Claude
Date: February 16, 2026
"""

import requests
import time
import logging
from datetime import datetime

logger = logging.getLogger('giftwise')


def run_apify_scraper(
    actor_id,
    input_params,
    max_wait=120,
    task_id=None,
    progress_callback=None,
    progress_messages=None,
    platform_name='platform',
    apify_token=None
):
    """
    Generic Apify actor runner with polling and progress tracking.

    This function handles the common pattern used by Instagram, TikTok, and
    other Apify-based scrapers:
    1. Start actor run
    2. Poll for completion with progress updates
    3. Fetch results from dataset
    4. Return raw data (caller handles platform-specific parsing)

    Args:
        actor_id: Apify actor ID (e.g., APIFY_INSTAGRAM_ACTOR)
        input_params: Dict of input parameters for the actor
        max_wait: Maximum seconds to wait for completion (default: 120)
        task_id: Optional task ID for progress tracking
        progress_callback: Optional function(task_id, state, message, percent)
        progress_messages: Optional dict mapping progress% → message
                          (e.g., {30: 'Analyzing posts...', 50: 'Downloading...'})
        platform_name: Name for logging (e.g., 'Instagram', 'TikTok')
        apify_token: Apify API token

    Returns:
        list: Raw dataset items from Apify actor, or None if failed

    Example:
        >>> data = run_apify_scraper(
        ...     actor_id='apify/instagram-scraper',
        ...     input_params={'username': ['testuser'], 'resultsLimit': 50},
        ...     max_wait=120,
        ...     task_id='task_123',
        ...     progress_callback=set_progress,
        ...     progress_messages={
        ...         10: 'Finding @testuser...',
        ...         30: 'Analyzing profile...',
        ...         50: 'Downloading posts...',
        ...         70: 'Extracting interests...',
        ...         85: 'Processing data...'
        ...     },
        ...     platform_name='Instagram',
        ...     apify_token='apify_api_xxxx'
        ... )
    """
    if not apify_token:
        logger.warning(f"No Apify token configured for {platform_name}")
        return None

    try:
        # Set initial progress
        if progress_callback and task_id:
            progress_callback(task_id, 'running', f'Starting {platform_name} scraper...', 5)

        logger.info(f"Starting {platform_name} scrape with actor {actor_id}")

        # Start Apify actor run
        response = requests.post(
            f'https://api.apify.com/v2/acts/{actor_id}/runs?token={apify_token}',
            json=input_params,
            timeout=30
        )

        if response.status_code != 201:
            if progress_callback and task_id:
                progress_callback(task_id, 'error', 'Failed to start scraper', 0)
            logger.error(f"Failed to start {platform_name} scraper: HTTP {response.status_code}")
            return None

        run_id = response.json()['data']['id']
        logger.info(f"{platform_name} scraper run started: {run_id}")

        if progress_callback and task_id:
            progress_callback(task_id, 'running', f'Searching {platform_name}...', 15)

        # Poll for completion
        elapsed = 0
        while elapsed < max_wait:
            # Adaptive wait time: faster polls early, slower later
            wait_time = 2 if elapsed < 30 else 5
            time.sleep(wait_time)
            elapsed += wait_time

            # Update progress
            if progress_callback and task_id:
                progress_pct = min(15 + (elapsed / max_wait) * 75, 90)

                # Use custom progress messages if provided
                if progress_messages:
                    # Round to nearest 10 for message lookup
                    progress_bucket = int(progress_pct // 10) * 10
                    message = progress_messages.get(progress_bucket, f'Analyzing {platform_name}...')
                else:
                    message = f'Scraping {platform_name}... ({int(progress_pct)}%)'

                progress_callback(task_id, 'running', message, progress_pct)

            # Check run status
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={apify_token}',
                timeout=10
            )

            if status_response.status_code != 200:
                logger.warning(f"{platform_name} status check failed: HTTP {status_response.status_code}")
                continue

            status_data = status_response.json()['data']
            status = status_data['status']

            if status == 'SUCCEEDED':
                logger.info(f"{platform_name} scraper run succeeded")
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                if progress_callback and task_id:
                    progress_callback(task_id, 'error', f'{platform_name} scraping failed', 0)
                logger.error(f"{platform_name} scraper run failed with status: {status}")
                return None

        # Check if we timed out
        if elapsed >= max_wait:
            logger.warning(f"{platform_name} scraper timed out after {max_wait}s")
            if progress_callback and task_id:
                progress_callback(task_id, 'error', 'Scraping timed out', 0)
            return None

        # Fetch results from dataset
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={apify_token}',
            timeout=30
        )

        if results_response.status_code != 200:
            if progress_callback and task_id:
                progress_callback(task_id, 'error', 'Failed to retrieve data', 0)
            logger.error(f"Failed to retrieve {platform_name} data: HTTP {results_response.status_code}")
            return None

        data = results_response.json()

        if not data:
            if progress_callback and task_id:
                progress_callback(task_id, 'error', 'No data found', 0)
            logger.warning(f"No data returned from {platform_name} scraper")
            return None

        logger.info(f"{platform_name} scraper returned {len(data)} items")
        return data

    except Exception as e:
        logger.error(f"{platform_name} scraping error: {e}", exc_info=True)
        if progress_callback and task_id:
            progress_callback(task_id, 'error', f'Error: {str(e)}', 0)
        return None


# =============================================================================
# PLATFORM-SPECIFIC WRAPPERS (for backward compatibility)
# =============================================================================

def scrape_instagram_apify(username, max_posts=50, task_id=None, progress_callback=None, apify_token=None, actor_id=None):
    """
    Scrape Instagram profile using Apify.

    Args:
        username: Instagram username (without @)
        max_posts: Maximum posts to scrape
        task_id: Optional task ID for progress tracking
        progress_callback: Optional progress callback function
        apify_token: Apify API token
        actor_id: Apify Instagram actor ID

    Returns:
        list: Raw Instagram data from Apify, or None if failed
    """
    if not actor_id:
        raise ValueError("Instagram actor ID must be provided")

    progress_messages = {
        10: f'Finding @{username}...',
        30: 'Analyzing profile...',
        50: 'Downloading posts...',
        70: 'Extracting interests...',
        85: 'Processing data...'
    }

    return run_apify_scraper(
        actor_id=actor_id,
        input_params={
            'username': [username],
            'resultsLimit': max_posts
        },
        max_wait=120,
        task_id=task_id,
        progress_callback=progress_callback,
        progress_messages=progress_messages,
        platform_name='Instagram',
        apify_token=apify_token
    )


def scrape_tiktok_apify(username, max_videos=50, task_id=None, progress_callback=None, apify_token=None, actor_id=None):
    """
    Scrape TikTok profile using Apify.

    Args:
        username: TikTok username (without @)
        max_videos: Maximum videos to scrape
        task_id: Optional task ID for progress tracking
        progress_callback: Optional progress callback function
        apify_token: Apify API token
        actor_id: Apify TikTok actor ID

    Returns:
        list: Raw TikTok data from Apify, or None if failed
    """
    if not actor_id:
        raise ValueError("TikTok actor ID must be provided")

    progress_messages = {
        10: f'Finding @{username}...',
        30: 'Analyzing videos...',
        50: 'Detecting reposts...',
        70: 'Extracting interests...',
        85: 'Processing data...'
    }

    return run_apify_scraper(
        actor_id=actor_id,
        input_params={
            'profiles': [username],
            'resultsPerPage': max_videos
        },
        max_wait=120,
        task_id=task_id,
        progress_callback=progress_callback,
        progress_messages=progress_messages,
        platform_name='TikTok',
        apify_token=apify_token
    )


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Apify Utils Test Suite\n" + "=" * 50)
    print("\nThis module provides:")
    print("  1. run_apify_scraper() - Generic Apify runner with polling")
    print("  2. scrape_instagram_apify() - Instagram-specific wrapper")
    print("  3. scrape_tiktok_apify() - TikTok-specific wrapper")
    print("\nUsage in giftwise_app.py:")
    print("  from apify_utils import scrape_instagram_apify, scrape_tiktok_apify")
    print("  data = scrape_instagram_apify('username', apify_token=token, actor_id=actor)")
