"""
SHARE MANAGER
Generate shareable links for gift recommendations
"""

import hashlib
import json
import shelve
from datetime import datetime, timedelta
import os

SHARE_DB_PATH = 'data/shares.db'
SHARE_EXPIRY_DAYS = 30

os.makedirs('data', exist_ok=True)

def generate_share_id(recommendations, user_id):
    """
    Generate unique share ID for recommendations
    
    Args:
        recommendations: List of recommendations
        user_id: User ID
    
    Returns:
        Share ID string
    """
    # Create hash from recommendations + timestamp
    data = json.dumps(recommendations, sort_keys=True) + str(user_id) + str(datetime.now().isoformat())
    share_id = hashlib.md5(data.encode()).hexdigest()[:12]
    return share_id

def save_share(share_id, recommendations, user_id):
    """
    Save shareable recommendations
    
    Args:
        share_id: Unique share ID
        recommendations: List of recommendations
        user_id: User ID
    
    Returns:
        True if saved successfully
    """
    db = shelve.open(SHARE_DB_PATH, writeback=True)
    try:
        db[share_id] = {
            'recommendations': recommendations,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=SHARE_EXPIRY_DAYS)).isoformat()
        }
        db.sync()
        return True
    finally:
        db.close()

def get_share(share_id):
    """
    Get shared recommendations
    
    Args:
        share_id: Share ID
    
    Returns:
        Dict with recommendations and metadata, or None if not found/expired
    """
    db = shelve.open(SHARE_DB_PATH, writeback=True)
    try:
        share_data = db.get(share_id)
        
        if not share_data:
            return None
        
        # Check expiry
        expires_at = datetime.fromisoformat(share_data['expires_at'])
        if datetime.now() > expires_at:
            # Expired - delete it
            del db[share_id]
            db.sync()
            return None
        
        return share_data
    finally:
        db.close()

def cleanup_expired_shares():
    """
    Clean up expired shares (run periodically)
    """
    db = shelve.open(SHARE_DB_PATH, writeback=True)
    try:
        expired_keys = []
        for share_id, share_data in db.items():
            expires_at = datetime.fromisoformat(share_data['expires_at'])
            if datetime.now() > expires_at:
                expired_keys.append(share_id)
        
        for key in expired_keys:
            del db[key]
        
        db.sync()
        return len(expired_keys)
    finally:
        db.close()
