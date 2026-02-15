"""
REFERRAL SYSTEM
Generates referral codes, tracks referrals, credits rewards.
Storage: shelve DB (same pattern as share_manager.py).

Author: Chad + Claude
Date: February 2026
"""

import hashlib
import os
import shelve
from datetime import datetime, timedelta

REFERRAL_DB_PATH = 'data/referrals.db'
os.makedirs('data', exist_ok=True)


def generate_referral_code(user_email):
    """Generate a short, memorable referral code from user email."""
    hash_val = hashlib.md5(user_email.encode()).hexdigest()[:5].upper()
    return f"GIFT{hash_val}"


def validate_referral_code(code):
    """Check if a referral code exists and return the referrer's email, or None."""
    db = shelve.open(REFERRAL_DB_PATH)
    try:
        for email, data in db.items():
            if data.get('code') == code:
                return email
        return None
    finally:
        db.close()


def _ensure_referrer(user):
    """Make sure a user has a referral code stored. Returns the code."""
    email = user.get('email', user.get('user_id', 'anonymous'))
    code = generate_referral_code(email)

    db = shelve.open(REFERRAL_DB_PATH, writeback=True)
    try:
        if email not in db:
            db[email] = {
                'code': code,
                'referrals': [],
                'credits': 0,
                'created_at': datetime.now().isoformat(),
            }
            db.sync()
        return db[email]['code']
    finally:
        db.close()


def apply_referral_to_user(new_user_email, referral_code):
    """
    Apply a referral: mark the new user as referred and credit the referrer.
    Returns True if the code was valid and applied.
    """
    referrer_email = validate_referral_code(referral_code)
    if not referrer_email:
        return False
    credit_referrer(referrer_email, new_user_email)
    return True


def credit_referrer(referrer_email, new_user_email=None):
    """Give the referrer credit for bringing in a new user."""
    db = shelve.open(REFERRAL_DB_PATH, writeback=True)
    try:
        entry = db.get(referrer_email, {
            'code': generate_referral_code(referrer_email),
            'referrals': [],
            'credits': 0,
            'created_at': datetime.now().isoformat(),
        })
        entry['referrals'].append({
            'referred_email': new_user_email or 'unknown',
            'date': datetime.now().isoformat(),
        })
        entry['credits'] += 5  # $5 credit per referral
        db[referrer_email] = entry
        db.sync()
    finally:
        db.close()


def get_referral_stats(user):
    """Return referral stats for a user."""
    email = user.get('email', user.get('user_id', 'anonymous'))
    code = _ensure_referrer(user)

    db = shelve.open(REFERRAL_DB_PATH)
    try:
        entry = db.get(email, {})
        referrals = entry.get('referrals', [])
        credits = entry.get('credits', 0)
        return {
            'referral_code': code,
            'total_referrals': len(referrals),
            'credits_earned': credits,
            'referrals': referrals[-10:],  # last 10
        }
    finally:
        db.close()


