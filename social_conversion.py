"""
SOCIAL & CONVERSION - Viral loops and purchase nudges
Handles sharing, referrals, urgency messaging, and conversion optimization

Author: Chad + Claude
Date: February 2026
"""

import hashlib
import time
import random
from datetime import datetime, timedelta

class SocialFeatures:
    """Manage social sharing and viral features"""
    
    @staticmethod
    def generate_share_link(recommendations, user_id, base_url):
        """
        Generate shareable link for gift recommendations
        
        Returns:
            {
                'share_url': 'https://giftwise.com/share/abc123',
                'share_id': 'abc123',
                'share_text': 'Help me pick! Which gift should I get?'
            }
        """
        
        # Create unique share ID
        share_data = f"{user_id}:{time.time()}:{len(recommendations)}"
        share_id = hashlib.md5(share_data.encode()).hexdigest()[:12]
        
        share_url = f"{base_url}/share/{share_id}"
        
        return {
            'share_url': share_url,
            'share_id': share_id,
            'share_text': '🎁 Help me pick the perfect gift! Which one would you choose?',
            'created_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def generate_voting_link(gift_options, user_id, base_url):
        """
        Create a link for friends to vote on gift choices
        
        Args:
            gift_options: List of 2-3 gift dicts they're deciding between
            user_id: User ID
            base_url: Base URL
        
        Returns:
            {
                'vote_url': 'https://giftwise.com/vote/xyz789',
                'vote_id': 'xyz789'
            }
        """
        
        vote_data = f"{user_id}:vote:{time.time()}"
        vote_id = hashlib.md5(vote_data.encode()).hexdigest()[:12]
        
        vote_url = f"{base_url}/vote/{vote_id}"
        
        return {
            'vote_url': vote_url,
            'vote_id': vote_id,
            'options': gift_options,
            'created_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def generate_referral_code(user_email):
        """
        Generate unique referral code for user
        
        Returns:
            'FRIEND5' format code
        """
        
        # Create readable referral code from email
        hash_val = hashlib.md5(user_email.encode()).hexdigest()[:6].upper()
        return f"GIFT{hash_val[:4]}"


class ConversionNudges:
    """Generate urgency and conversion messaging"""
    
    @staticmethod
    def get_valentines_urgency():
        """Get Valentine's Day specific urgency message"""
        
        valentines = datetime(2026, 2, 14)
        today = datetime.now()
        days_until = (valentines - today).days
        
        if days_until <= 0:
            return {
                'message': "⚠️ Valentine's Day is TODAY! Order ASAP for any chance of delivery.",
                'urgency_level': 'critical',
                'show': True
            }
        elif days_until <= 3:
            return {
                'message': f"⚠️ Only {days_until} days until Valentine's Day! Order now for guaranteed delivery.",
                'urgency_level': 'high',
                'show': True
            }
        elif days_until <= 7:
            return {
                'message': f"🎁 Valentine's Day is in {days_until} days. Order soon to ensure delivery!",
                'urgency_level': 'medium',
                'show': True
            }
        elif days_until <= 14:
            return {
                'message': f"📦 {days_until} days until Valentine's Day. Plenty of time, but don't wait!",
                'urgency_level': 'low',
                'show': True
            }
        else:
            return {
                'message': None,
                'urgency_level': 'none',
                'show': False
            }
    
    @staticmethod
    def get_social_proof(product_title):
        """
        Generate social proof message for a product
        
        Simulated for now - in production, track real views/purchases
        """
        
        # Simulate realistic social proof
        views_today = random.randint(5, 50)
        purchased_recently = random.randint(1, 8)
        
        messages = [
            f"👀 {views_today} people viewed this today",
            f"🔥 {purchased_recently} purchased in the last 24 hours",
            f"⭐ Trending in this category",
            f"💝 Popular for Valentine's Day",
        ]
        
        # Return 1-2 random messages
        selected = random.sample(messages, k=min(2, len(messages)))
        
        return {
            'badges': selected,
            'show_trending': views_today > 30
        }
    
    @staticmethod
    def get_scarcity_message(product_link):
        """
        Generate scarcity/stock messaging
        
        In production, could scrape actual stock levels or use API
        """
        
        # Randomly decide if we show scarcity (33% of products)
        if random.random() < 0.33:
            messages = [
                "⚠️ Low stock - order soon",
                "🔥 Selling fast",
                "⏰ Limited availability",
            ]
            return random.choice(messages)
        
        return None
    
    @staticmethod
    def get_abandonment_recovery_message(user_email, days_since_visit):
        """
        Generate message for users who haven't completed purchase
        
        For email campaigns or re-engagement
        """
        
        if days_since_visit == 1:
            return {
                'subject': '🎁 Still deciding? Your gift recommendations are waiting!',
                'message': 'We saved your recommendations! Come back and complete your order.',
                'offer': None
            }
        elif days_since_visit >= 3:
            return {
                'subject': '💝 $5 OFF to help you decide!',
                'message': 'Use code COMEBACK5 for $5 off your first Pro subscription.',
                'offer': {
                    'code': 'COMEBACK5',
                    'discount': 5,
                    'type': 'dollars_off'
                }
            }
        
        return None
    
    @staticmethod
    def get_upgrade_nudge(current_tier, recommendations_count):
        """
        Generate messaging to encourage Pro/Premium upgrade
        
        Args:
            current_tier: 'free', 'pro', 'premium'
            recommendations_count: Number of recs they got
        """
        
        if current_tier == 'free':
            return {
                'message': f"You got {recommendations_count} recommendations. Upgrade to Pro for unlimited generations!",
                'cta': 'Upgrade to Pro - $4.99',
                'benefits': [
                    'Unlimited gift generations',
                    'Save favorites',
                    'Share recommendations with friends',
                    'Priority customer support'
                ],
                'show': True
            }
        elif current_tier == 'pro':
            return {
                'message': 'Want even more? Premium gets you concierge service and exclusive deals.',
                'cta': 'Upgrade to Premium - $24.99',
                'benefits': [
                    'Everything in Pro',
                    'Personal gift concierge',
                    'Exclusive brand discounts',
                    'Gift tracking & reminders'
                ],
                'show': True
            }
        
        return {'show': False}


class ShareTracking:
    """Track share performance and viral coefficients"""
    
    def __init__(self):
        self.shares = {}  # share_id -> data
        self.referrals = {}  # referral_code -> data
        self.viral_metrics = {}  # user_id -> viral metrics
    
    def track_share(self, share_id, user_id, platform):
        """Track when user shares recommendations"""
        
        if share_id not in self.shares:
            self.shares[share_id] = {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'views': 0,
                'clicks': 0,
                'conversions': 0,
                'platform': platform  # 'facebook', 'twitter', 'copy_link', etc.
            }
    
    def track_share_view(self, share_id):
        """Track when someone views a shared link"""
        
        if share_id in self.shares:
            self.shares[share_id]['views'] += 1
    
    def track_share_click(self, share_id, clicked_product_index):
        """Track when someone clicks a product from shared link"""
        
        if share_id in self.shares:
            self.shares[share_id]['clicks'] += 1
    
    def track_share_conversion(self, share_id, new_user_id):
        """Track when someone signs up from a shared link"""
        
        if share_id in self.shares:
            self.shares[share_id]['conversions'] += 1
            
            # Credit the referrer
            referrer_id = self.shares[share_id]['user_id']
            if referrer_id not in self.viral_metrics:
                self.viral_metrics[referrer_id] = {
                    'total_shares': 0,
                    'total_referrals': 0,
                    'k_factor': 0,
                    'credits_earned': 0,
                    'tier': 'bronze'  # bronze, silver, gold, platinum
                }
            
            self.viral_metrics[referrer_id]['total_referrals'] += 1
            self.viral_metrics[referrer_id]['credits_earned'] += 5  # $5 credit per referral
            
            # Update tier based on referrals
            referrals = self.viral_metrics[referrer_id]['total_referrals']
            if referrals >= 50:
                self.viral_metrics[referrer_id]['tier'] = 'platinum'
            elif referrals >= 20:
                self.viral_metrics[referrer_id]['tier'] = 'gold'
            elif referrals >= 5:
                self.viral_metrics[referrer_id]['tier'] = 'silver'
    
    def get_viral_coefficient(self, user_id):
        """
        Calculate how many new users this user has brought in
        
        Viral coefficient (k-factor):
        - k < 1: Not viral
        - k = 1: Each user brings 1 new user (sustaining)
        - k > 1: Viral growth! Each user brings multiple users
        
        Returns:
            {
                'k_factor': float,
                'total_shares': int,
                'total_referrals': int,
                'conversion_rate': float,
                'tier': str,
                'credits': int
            }
        """
        
        shares_by_user = [s for s in self.shares.values() if s['user_id'] == user_id]
        
        if not shares_by_user:
            return {
                'k_factor': 0,
                'total_shares': 0,
                'total_referrals': 0,
                'conversion_rate': 0,
                'tier': 'bronze',
                'credits': 0
            }
        
        total_conversions = sum(s['conversions'] for s in shares_by_user)
        total_views = sum(s['views'] for s in shares_by_user)
        
        metrics = self.viral_metrics.get(user_id, {
            'total_shares': len(shares_by_user),
            'total_referrals': total_conversions,
            'k_factor': total_conversions,  # Simplified k-factor
            'credits_earned': 0,
            'tier': 'bronze'
        })
        
        # Calculate conversion rate
        conversion_rate = (total_conversions / total_views * 100) if total_views > 0 else 0
        
        metrics['conversion_rate'] = round(conversion_rate, 2)
        
        return metrics
    
    def get_leaderboard(self, limit=10):
        """
        Get top referrers for gamification
        
        Returns:
            List of top users by referrals
        """
        
        leaderboard = []
        
        for user_id, metrics in self.viral_metrics.items():
            leaderboard.append({
                'user_id': user_id,
                'referrals': metrics['total_referrals'],
                'tier': metrics['tier'],
                'k_factor': metrics['k_factor']
            })
        
        # Sort by referrals descending
        leaderboard.sort(key=lambda x: x['referrals'], reverse=True)
        
        return leaderboard[:limit]
    
    def get_incentive_progress(self, user_id):
        """
        Show user their progress toward next tier/reward
        
        Returns:
            {
                'current_tier': str,
                'next_tier': str,
                'referrals_needed': int,
                'current_referrals': int,
                'progress_pct': float,
                'next_reward': str
            }
        """
        
        metrics = self.viral_metrics.get(user_id, {
            'total_referrals': 0,
            'tier': 'bronze'
        })
        
        referrals = metrics['total_referrals']
        
        tier_thresholds = {
            'bronze': {'next': 'silver', 'needed': 5, 'reward': 'Silver badge + 10% off Premium'},
            'silver': {'next': 'gold', 'needed': 20, 'reward': 'Gold badge + Free month Premium'},
            'gold': {'next': 'platinum', 'needed': 50, 'reward': 'Platinum badge + Lifetime Pro'},
            'platinum': {'next': None, 'needed': None, 'reward': 'You\'re at the top!'}
        }
        
        current_tier = metrics['tier']
        tier_info = tier_thresholds[current_tier]
        
        if tier_info['next']:
            referrals_needed = tier_info['needed'] - referrals
            progress_pct = (referrals / tier_info['needed']) * 100
        else:
            referrals_needed = 0
            progress_pct = 100
        
        return {
            'current_tier': current_tier,
            'next_tier': tier_info['next'],
            'referrals_needed': max(0, referrals_needed),
            'current_referrals': referrals,
            'progress_pct': min(100, progress_pct),
            'next_reward': tier_info['reward']
        }


class GrowthLoops:
    """Viral growth loop triggers and messaging"""
    
    @staticmethod
    def get_share_prompt(trigger_moment):
        """
        Get contextual share prompt based on user action
        
        Args:
            trigger_moment: 'after_recommendations', 'favorited_item', 
                          'purchased_item', 'repeated_use'
        
        Returns:
            {
                'message': str,
                'cta': str,
                'incentive': str
            }
        """
        
        prompts = {
            'after_recommendations': {
                'message': '🎁 Love these recommendations? Your friends will too!',
                'cta': 'Share with friends',
                'incentive': 'You both get $5 off when they sign up'
            },
            'favorited_item': {
                'message': '❤️ Can\'t decide? Get your friends to vote!',
                'cta': 'Ask friends to vote',
                'incentive': 'See which gift they think is best'
            },
            'purchased_item': {
                'message': '🎉 Nice choice! Know someone else who needs gift help?',
                'cta': 'Refer a friend',
                'incentive': 'Earn $5 credit for each signup'
            },
            'repeated_use': {
                'message': '🌟 Using Giftwise again? You must love it!',
                'cta': 'Share the love',
                'incentive': 'Unlock Gold tier with 20 referrals'
            }
        }
        
        return prompts.get(trigger_moment, prompts['after_recommendations'])
    
    @staticmethod
    def get_network_effect_message(user_connections):
        """
        Show how the network effect works
        
        Args:
            user_connections: Number of friends who also use Giftwise
        
        Returns:
            Message explaining network benefits
        """
        
        if user_connections == 0:
            return {
                'message': 'Be the first in your friend group to discover Giftwise!',
                'benefit': 'When friends join, they can vote on your gift choices'
            }
        elif user_connections < 3:
            return {
                'message': f'{user_connections} of your friends use Giftwise!',
                'benefit': 'The more friends join, the better gift voting gets'
            }
        else:
            return {
                'message': f'🎉 {user_connections} friends are on Giftwise!',
                'benefit': 'You\'ve unlocked group gift voting and recommendations'
            }


# Global instances
social_features = SocialFeatures()
conversion_nudges = ConversionNudges()
share_tracking = ShareTracking()
