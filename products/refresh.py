#!/usr/bin/env python3
"""
PRODUCT REFRESH CLI
Simple entry point for automated database refresh

Usage:
    python products/refresh.py                  # Refresh all retailers
    python products/refresh.py --retailer ebay  # Refresh specific retailer

Called by:
    - Railway Cron Jobs
    - GitHub Actions
    - Manual cron setup

Author: Chad + Claude
Date: February 2026
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from products.ingestion import refresh_all_products, refresh_retailer

if __name__ == "__main__":
    # Simple CLI - no argparse to keep it lightweight
    import sys

    retailer = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if retailer == 'all':
        results = refresh_all_products()
        print(f"Refresh complete: {sum(results.values())} total products")
    else:
        count = refresh_retailer(retailer)
        print(f"{retailer}: {count} products")
