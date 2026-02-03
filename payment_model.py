"""
PAYMENT MODEL
Hybrid pricing system: one-time, monthly, annual
Includes gift occasion calendar and subscription guards.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

# =============================================================================
# PRICING TIERS
# =============================================================================

PRICING = {
    'one_time': {
        'price': 7.99,
        'price_id': 'price_one_time_799',
        'name': 'Single Generation',
        'short_name': 'One-Time',
        'features': [
            'All 3 platforms (Instagram + TikTok + Pinterest)',
            '10 curated product recommendations',
            '3 bespoke experience packages',
            'Valid for 30 days',
            'Shareable profile link'
        ],
        'limitations': [
            'Single use only',
            'No regeneration',
            'No gift reminders',
            'Profile expires after 30 days'
        ],
        'best_for': ['one-time gift', 'trying the service', 'occasional gifting'],
        'cta': 'Get Recommendations',
        'urgency_text': 'Perfect for this occasion',
        'trial_mode': False
    },
    
    'monthly': {
        'price': 4.99,
        'annual_equivalent': 59.88,
        'price_id': 'price_monthly_499',
        'name': 'Pro Monthly',
        'short_name': 'Monthly',
        'features': [
            'Everything in Single Generation',
            'Unlimited regenerations (once per month per person)',
            'Gift occasion reminders',
            'Save multiple recipient profiles',
            'Priority support',
            'Cancel anytime'
        ],
        'limitations': [],
        'best_for': ['regular gift-givers', 'multiple recipients', 'year-round use'],
        'cta': 'Start Monthly',
        'urgency_text': 'Save $3 per generation',
        'trial_mode': False,
        'billing_cycle': 'monthly',
        'commitment': 'Month-to-month, cancel anytime'
    },
    
    'annual': {
        'price': 49.99,
        'monthly_equivalent': 4.17,
        'savings': 9.89,
        'price_id': 'price_annual_4999',
        'name': 'Pro Annual',
        'short_name': 'Annual',
        'features': [
            'Everything in Pro Monthly',
            'Save $10 per year',
            'Extended profile storage (1 year)',
            'Priority feature access',
            'Anniversary reminder service',
            'Best value'
        ],
        'limitations': [],
        'best_for': ['serious gift-givers', 'maximum savings', 'commitment to quality'],
        'cta': 'Start Annual',
        'urgency_text': 'Best value - Save $10',
        'trial_mode': False,
        'billing_cycle': 'annual',
        'commitment': 'Annual billing, best value'
    }
}

VALENTINES_PROMO = {
    'monthly': {
        'promo_price': 3.99,
        'original_price': 4.99,
        'discount_percent': 20,
        'promo_text': "Valentine's Launch Special",
        'valid_until': '2026-02-28',
        'promo_code': 'VDAY2026'
    }
}

# =============================================================================
# GIFT OCCASION CALENDAR
# =============================================================================

def get_gift_occasions_by_demographics(age: int, life_stage: Optional[str] = None) -> Dict:
    """
    Return upcoming gift occasions based on user demographics.
    """
    if not life_stage:
        if age < 25:
            life_stage = 'student'
        elif age < 35:
            life_stage = 'young_professional'
        elif age < 50:
            life_stage = 'parent'
        else:
            life_stage = 'established'
    
    base_occasions = [
        {'name': "Valentine's Day", 'date': '02/14', 'recipients': 1, 'avg_spend': 80},
        {'name': "Mother's Day", 'date': '05/12', 'recipients': 1, 'avg_spend': 70},
        {'name': "Father's Day", 'date': '06/16', 'recipients': 1, 'avg_spend': 70},
        {'name': 'Christmas', 'date': '12/25', 'recipients': 5, 'avg_spend': 300}
    ]
    
    life_stage_occasions = {
        'student': [
            {'name': 'Friend Birthdays', 'date': 'Monthly', 'recipients': 3, 'avg_spend': 30},
            {'name': 'Graduation Gifts', 'date': '05/15', 'recipients': 2, 'avg_spend': 50}
        ],
        'young_professional': [
            {'name': 'Friend Birthdays', 'date': 'Monthly', 'recipients': 2, 'avg_spend': 50},
            {'name': 'Weddings', 'date': 'May-Oct', 'recipients': 3, 'avg_spend': 120},
            {'name': 'Housewarming Gifts', 'date': 'Quarterly', 'recipients': 2, 'avg_spend': 60}
        ],
        'parent': [
            {'name': 'Kids Birthdays', 'date': 'Varies', 'recipients': 2, 'avg_spend': 80},
            {'name': 'Teacher Gifts', 'date': '12/20', 'recipients': 2, 'avg_spend': 30},
            {'name': 'Anniversary', 'date': 'Varies', 'recipients': 1, 'avg_spend': 150}
        ],
        'established': [
            {'name': 'Anniversary', 'date': 'Varies', 'recipients': 1, 'avg_spend': 200},
            {'name': 'Grandkids Birthdays', 'date': 'Quarterly', 'recipients': 3, 'avg_spend': 60}
        ]
    }
    
    all_occasions = base_occasions + life_stage_occasions.get(life_stage, [])
    total_occasions = len(all_occasions)
    total_recipients = sum(occ['recipients'] for occ in all_occasions)
    total_spend = sum(occ['recipients'] * occ['avg_spend'] for occ in all_occasions)
    
    return {
        'total_occasions': total_occasions,
        'total_recipients': total_recipients,
        'total_annual_spend': total_spend,
        'life_stage': life_stage,
        'occasions': all_occasions
    }


def calculate_roi_for_subscription(occasions_data: Dict) -> Dict:
    """Calculate ROI of subscription vs one-time purchases."""
    total_occasions = occasions_data['total_occasions']
    
    one_time_total = total_occasions * PRICING['one_time']['price']
    annual_cost = PRICING['annual']['price']
    monthly_cost = PRICING['monthly']['price'] * 12
    
    annual_savings = one_time_total - annual_cost
    monthly_savings = one_time_total - monthly_cost
    
    return {
        'occasions_per_year': total_occasions,
        'one_time_total': round(one_time_total, 2),
        'annual_subscription': round(annual_cost, 2),
        'annual_savings': round(annual_savings, 2),
        'annual_savings_percent': round((annual_savings / one_time_total) * 100, 1) if one_time_total > 0 else 0,
        'monthly_subscription': round(monthly_cost, 2),
        'monthly_savings': round(monthly_savings, 2),
        'monthly_savings_percent': round((monthly_savings / one_time_total) * 100, 1) if one_time_total > 0 else 0,
        'break_even_occasions': {
            'monthly': int(PRICING['monthly']['price'] / PRICING['one_time']['price']) + 1,
            'annual': int(PRICING['annual']['price'] / PRICING['one_time']['price']) + 1
        }
    }


# =============================================================================
# SUBSCRIPTION GUARDS
# =============================================================================

class SubscriptionGuard:
    """Prevents subscription abuse and manages promotional cooldowns."""
    
    def __init__(self, user_history_path='/mnt/user-data/user_subscriptions'):
        self.history_path = user_history_path
        os.makedirs(user_history_path, exist_ok=True)
    
    def can_use_promo(self, user_id: str, promo_code: str) -> Tuple[bool, str]:
        """Check if user can use promotional pricing."""
        user_file = os.path.join(self.history_path, f"{user_id}.json")
        
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                history = json.load(f)
        else:
            history = {
                'user_id': user_id,
                'promo_codes_used': [],
                'subscription_history': [],
                'created_at': datetime.now().isoformat()
            }
        
        promo_records = history.get('promo_codes_used', [])
        for record in promo_records:
            if record['code'] == promo_code:
                used_date = datetime.fromisoformat(record['used_at'])
                cooldown_end = used_date + timedelta(days=180)
                
                if datetime.now() < cooldown_end:
                    days_remaining = (cooldown_end - datetime.now()).days
                    return False, f"Promo code on cooldown ({days_remaining} days remaining)"
        
        return True, "Promo code available"
    
    def record_promo_use(self, user_id: str, promo_code: str):
        """Record that user used a promo code."""
        user_file = os.path.join(self.history_path, f"{user_id}.json")
        
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                history = json.load(f)
        else:
            history = {
                'user_id': user_id,
                'promo_codes_used': [],
                'subscription_history': [],
                'created_at': datetime.now().isoformat()
            }
        
        history['promo_codes_used'].append({
            'code': promo_code,
            'used_at': datetime.now().isoformat()
        })
        
        with open(user_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def record_subscription(self, user_id: str, tier: str, action: str):
        """Record subscription event."""
        user_file = os.path.join(self.history_path, f"{user_id}.json")
        
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                history = json.load(f)
        else:
            history = {
                'user_id': user_id,
                'promo_codes_used': [],
                'subscription_history': [],
                'created_at': datetime.now().isoformat()
            }
        
        history['subscription_history'].append({
            'tier': tier,
            'action': action,
            'timestamp': datetime.now().isoformat()
        })
        
        with open(user_file, 'w') as f:
            json.dump(history, f, indent=2)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_pricing_for_user(user_tier: Optional[str] = None, is_valentine_season: bool = False) -> Dict:
    """Get pricing information for user."""
    pricing = PRICING.copy()
    
    if is_valentine_season and user_tier is None:
        pricing['monthly']['promo'] = VALENTINES_PROMO['monthly']
    
    return pricing


def get_recommended_tier(occasions_data: Dict) -> str:
    """Recommend a pricing tier based on user's gift occasions."""
    total_occasions = occasions_data['total_occasions']
    
    if total_occasions <= 1:
        return 'one_time'
    elif total_occasions <= 5:
        return 'monthly'
    else:
        return 'annual'


def get_retention_message(tier: str, occasions_remaining: int) -> Dict:
    """Get retention message to show before cancellation."""
    if tier == 'monthly':
        return {
            'headline': 'Before You Go...',
            'message': f"You have {occasions_remaining} gift occasions coming up this year.",
            'value_prop': f"At $7.99 each, that's ${occasions_remaining * 7.99:.2f} vs your $49.99 annual price.",
            'savings': f"You'd save ${(occasions_remaining * 7.99) - 49.99:.2f} by staying subscribed.",
            'cta': 'Keep My Subscription'
        }
    elif tier == 'annual':
        return {
            'headline': 'Your Annual Plan Has Great Value',
            'message': f"You have {occasions_remaining} occasions remaining on your plan.",
            'value_prop': f"That's only ${49.99 / 12:.2f}/month for unlimited use.",
            'cta': 'Keep My Plan'
        }
    else:
        return {}


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    occasions = get_gift_occasions_by_demographics(age=30, life_stage='young_professional')
    
    print("\n" + "="*70)
    print("GIFT OCCASIONS ANALYSIS")
    print("="*70)
    print(f"Life Stage: {occasions['life_stage']}")
    print(f"Total Occasions: {occasions['total_occasions']}")
    print(f"Total Annual Spend: ${occasions['total_annual_spend']}")
    
    roi = calculate_roi_for_subscription(occasions)
    
    print(f"\n{'='*70}")
    print("PRICING COMPARISON")
    print("="*70)
    print(f"One-Time Each Time: ${roi['one_time_total']}")
    print(f"Annual Subscription: ${roi['annual_subscription']}")
    print(f"  Savings: ${roi['annual_savings']} ({roi['annual_savings_percent']}%)")
    
    recommended = get_recommended_tier(occasions)
    print(f"\nRecommended Tier: {PRICING[recommended]['name']}")
    print("\n" + "="*70)
