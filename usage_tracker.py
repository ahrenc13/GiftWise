"""
USAGE TRACKER
Track API usage (Anthropic, Apify) to monitor quotas and limits

Stores daily/monthly usage in shelve database
"""

import shelve
from datetime import datetime, timedelta
import json
import os

# Create data directory if it doesn't exist (for Railway/local)
os.makedirs('data', exist_ok=True)
USAGE_DB_PATH = 'data/usage.db'

# API Limits (update based on your plan)
API_LIMITS = {
    'anthropic': {
        'daily_requests': 1000,  # Update based on your Anthropic plan
        'daily_tokens': 1000000,  # 1M tokens/day (update based on plan)
        'monthly_requests': 30000,
        'monthly_tokens': 30000000,  # 30M tokens/month
    },
    'apify': {
        'daily_compute': 100,  # Compute units/day (free tier: ~100, paid varies)
        'monthly_compute': 3000,  # Compute units/month
    }
}

def get_usage_db():
    """Get or create usage database"""
    os.makedirs('data', exist_ok=True)
    return shelve.open(USAGE_DB_PATH, writeback=True)

def get_date_key(date=None):
    """Get date key for daily tracking"""
    if date is None:
        date = datetime.now()
    return date.strftime('%Y-%m-%d')

def get_month_key(date=None):
    """Get month key for monthly tracking"""
    if date is None:
        date = datetime.now()
    return date.strftime('%Y-%m')

def track_anthropic_usage(tokens_used, request_type='recommendation'):
    """
    Track Anthropic API usage
    
    Args:
        tokens_used: Number of tokens used (input + output)
        request_type: Type of request (recommendation, etc.)
    """
    db = get_usage_db()
    try:
        today = get_date_key()
        month = get_month_key()
        
        # Daily tracking
        daily_key = f'anthropic_daily_{today}'
        if daily_key not in db:
            db[daily_key] = {
                'date': today,
                'requests': 0,
                'tokens': 0,
                'request_types': {}
            }
        
        db[daily_key]['requests'] += 1
        db[daily_key]['tokens'] += tokens_used
        db[daily_key]['request_types'][request_type] = db[daily_key]['request_types'].get(request_type, 0) + 1
        
        # Monthly tracking
        monthly_key = f'anthropic_monthly_{month}'
        if monthly_key not in db:
            db[monthly_key] = {
                'month': month,
                'requests': 0,
                'tokens': 0,
                'request_types': {}
            }
        
        db[monthly_key]['requests'] += 1
        db[monthly_key]['tokens'] += tokens_used
        db[monthly_key]['request_types'][request_type] = db[monthly_key]['request_types'].get(request_type, 0) + 1
        
        db.sync()
    finally:
        db.close()

def track_apify_usage(compute_units, actor_type='instagram'):
    """
    Track Apify scraping usage
    
    Args:
        compute_units: Compute units used (typically 1 per run)
        actor_type: Type of actor (instagram, tiktok)
    """
    db = get_usage_db()
    try:
        today = get_date_key()
        month = get_month_key()
        
        # Daily tracking
        daily_key = f'apify_daily_{today}'
        if daily_key not in db:
            db[daily_key] = {
                'date': today,
                'runs': 0,
                'compute_units': 0,
                'actor_types': {}
            }
        
        db[daily_key]['runs'] += 1
        db[daily_key]['compute_units'] += compute_units
        db[daily_key]['actor_types'][actor_type] = db[daily_key]['actor_types'].get(actor_type, 0) + 1
        
        # Monthly tracking
        monthly_key = f'apify_monthly_{month}'
        if monthly_key not in db:
            db[monthly_key] = {
                'month': month,
                'runs': 0,
                'compute_units': 0,
                'actor_types': {}
            }
        
        db[monthly_key]['runs'] += 1
        db[monthly_key]['compute_units'] += compute_units
        db[monthly_key]['actor_types'][actor_type] = db[monthly_key]['actor_types'].get(actor_type, 0) + 1
        
        db.sync()
    finally:
        db.close()

def get_daily_usage(date=None):
    """Get daily usage for a specific date"""
    if date is None:
        date = datetime.now()
    
    date_key = get_date_key(date)
    db = get_usage_db()
    
    try:
        anthropic_key = f'anthropic_daily_{date_key}'
        apify_key = f'apify_daily_{date_key}'
        
        anthropic_usage = db.get(anthropic_key, {
            'date': date_key,
            'requests': 0,
            'tokens': 0,
            'request_types': {}
        })
        
        apify_usage = db.get(apify_key, {
            'date': date_key,
            'runs': 0,
            'compute_units': 0,
            'actor_types': {}
        })
        
        return {
            'date': date_key,
            'anthropic': anthropic_usage,
            'apify': apify_usage,
            'limits': API_LIMITS
        }
    finally:
        db.close()

def get_monthly_usage(month=None):
    """Get monthly usage for a specific month"""
    if month is None:
        month = get_month_key()
    
    db = get_usage_db()
    
    try:
        anthropic_key = f'anthropic_monthly_{month}'
        apify_key = f'apify_monthly_{month}'
        
        anthropic_usage = db.get(anthropic_key, {
            'month': month,
            'requests': 0,
            'tokens': 0,
            'request_types': {}
        })
        
        apify_usage = db.get(apify_key, {
            'month': month,
            'runs': 0,
            'compute_units': 0,
            'actor_types': {}
        })
        
        return {
            'month': month,
            'anthropic': anthropic_usage,
            'apify': apify_usage,
            'limits': API_LIMITS
        }
    finally:
        db.close()

def get_usage_summary():
    """Get current usage summary with remaining capacity"""
    today = get_daily_usage()
    this_month = get_monthly_usage()
    
    # Calculate remaining capacity
    anth_daily_remaining = {
        'requests': max(0, API_LIMITS['anthropic']['daily_requests'] - today['anthropic']['requests']),
        'tokens': max(0, API_LIMITS['anthropic']['daily_tokens'] - today['anthropic']['tokens'])
    }
    
    anth_monthly_remaining = {
        'requests': max(0, API_LIMITS['anthropic']['monthly_requests'] - this_month['anthropic']['requests']),
        'tokens': max(0, API_LIMITS['anthropic']['monthly_tokens'] - this_month['anthropic']['tokens'])
    }
    
    apify_daily_remaining = {
        'compute_units': max(0, API_LIMITS['apify']['daily_compute'] - today['apify']['compute_units'])
    }
    
    apify_monthly_remaining = {
        'compute_units': max(0, API_LIMITS['apify']['monthly_compute'] - this_month['apify']['compute_units'])
    }
    
    # Calculate percentages
    anth_daily_pct = {
        'requests': (today['anthropic']['requests'] / API_LIMITS['anthropic']['daily_requests']) * 100,
        'tokens': (today['anthropic']['tokens'] / API_LIMITS['anthropic']['daily_tokens']) * 100
    }
    
    anth_monthly_pct = {
        'requests': (this_month['anthropic']['requests'] / API_LIMITS['anthropic']['monthly_requests']) * 100,
        'tokens': (this_month['anthropic']['tokens'] / API_LIMITS['anthropic']['monthly_tokens']) * 100
    }
    
    apify_daily_pct = {
        'compute_units': (today['apify']['compute_units'] / API_LIMITS['apify']['daily_compute']) * 100
    }
    
    apify_monthly_pct = {
        'compute_units': (this_month['apify']['compute_units'] / API_LIMITS['apify']['monthly_compute']) * 100
    }
    
    return {
        'today': today,
        'this_month': this_month,
        'remaining': {
            'anthropic': {
                'daily': anth_daily_remaining,
                'monthly': anth_monthly_remaining
            },
            'apify': {
                'daily': apify_daily_remaining,
                'monthly': apify_monthly_remaining
            }
        },
        'percentages': {
            'anthropic': {
                'daily': anth_daily_pct,
                'monthly': anth_monthly_pct
            },
            'apify': {
                'daily': apify_daily_pct,
                'monthly': apify_monthly_pct
            }
        }
    }
