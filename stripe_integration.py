"""
STRIPE INTEGRATION - PAYMENT PROCESSING
Handles Pro tier subscriptions and one-time payments

Author: Chad + Claude
Date: January 2026
"""

import os
import stripe
import logging
from datetime import datetime

logger = logging.getLogger('giftwise')

# Initialize Stripe
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PRO_PRICE_ID = os.environ.get('STRIPE_PRO_PRICE_ID')  # Monthly Pro subscription
STRIPE_PRO_ANNUAL_PRICE_ID = os.environ.get('STRIPE_PRO_ANNUAL_PRICE_ID')  # Annual Pro
STRIPE_PREMIUM_PRICE_ID = os.environ.get('STRIPE_PREMIUM_PRICE_ID')  # Premium tier
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    logger.warning("Stripe not configured - payment processing will fail")


def create_checkout_session(user_email, price_id, success_url, cancel_url, metadata=None):
    """
    Create a Stripe Checkout Session for subscription
    
    Args:
        user_email: User's email address
        price_id: Stripe Price ID (Pro, Premium, etc.)
        success_url: URL to redirect on success
        cancel_url: URL to redirect on cancel
        metadata: Additional metadata to attach
    
    Returns:
        Checkout session URL or None
    """
    if not STRIPE_SECRET_KEY:
        logger.error("Stripe not configured")
        return None
    
    try:
        session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',  # For recurring payments
            success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url,
            metadata=metadata or {},
            allow_promotion_codes=True,  # Allow discount codes
            billing_address_collection='auto',
        )
        
        logger.info(f"Created checkout session for {user_email}: {session.id}")
        return session.url
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        return None
    except Exception as e:
        logger.error(f"Checkout session creation error: {e}")
        return None


def create_portal_session(customer_id, return_url):
    """
    Create a Stripe Customer Portal session for managing subscription
    
    Args:
        customer_id: Stripe Customer ID
        return_url: URL to return to after portal
    
    Returns:
        Portal session URL or None
    """
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        return session.url
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe portal error: {e}")
        return None


def handle_webhook(payload, sig_header):
    """
    Handle Stripe webhook events
    
    Critical events:
    - checkout.session.completed: Subscription created
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription cancelled
    - invoice.payment_failed: Payment failed
    
    Args:
        payload: Request body
        sig_header: Stripe signature header
    
    Returns:
        dict with 'event_type', 'success', 'data'
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("Webhook secret not configured")
        return None
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        return None
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return None
    
    event_type = event['type']
    data = event['data']['object']
    
    logger.info(f"Received Stripe webhook: {event_type}")
    
    # Handle different event types
    if event_type == 'checkout.session.completed':
        # Payment successful, subscription created
        return {
            'event_type': 'subscription_created',
            'success': True,
            'customer_id': data.get('customer'),
            'customer_email': data.get('customer_email'),
            'subscription_id': data.get('subscription'),
            'metadata': data.get('metadata', {})
        }
    
    elif event_type == 'customer.subscription.updated':
        # Subscription updated (upgraded, downgraded, etc.)
        return {
            'event_type': 'subscription_updated',
            'success': True,
            'customer_id': data.get('customer'),
            'subscription_id': data.get('id'),
            'status': data.get('status'),
            'cancel_at_period_end': data.get('cancel_at_period_end'),
            'current_period_end': data.get('current_period_end')
        }
    
    elif event_type == 'customer.subscription.deleted':
        # Subscription cancelled
        return {
            'event_type': 'subscription_cancelled',
            'success': True,
            'customer_id': data.get('customer'),
            'subscription_id': data.get('id'),
            'cancelled_at': data.get('canceled_at')
        }
    
    elif event_type == 'invoice.payment_succeeded':
        # Payment succeeded (monthly renewal)
        return {
            'event_type': 'payment_succeeded',
            'success': True,
            'customer_id': data.get('customer'),
            'subscription_id': data.get('subscription'),
            'amount_paid': data.get('amount_paid') / 100,  # Convert from cents
            'invoice_id': data.get('id')
        }
    
    elif event_type == 'invoice.payment_failed':
        # Payment failed
        return {
            'event_type': 'payment_failed',
            'success': False,
            'customer_id': data.get('customer'),
            'subscription_id': data.get('subscription'),
            'amount_due': data.get('amount_due') / 100,
            'attempt_count': data.get('attempt_count')
        }
    
    else:
        # Other events we don't handle
        return {
            'event_type': event_type,
            'success': True,
            'data': data
        }


def get_subscription_status(subscription_id):
    """
    Get current status of a subscription
    
    Args:
        subscription_id: Stripe Subscription ID
    
    Returns:
        dict with subscription details or None
    """
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        return {
            'id': subscription.id,
            'status': subscription.status,  # active, past_due, canceled, etc.
            'customer_id': subscription.customer,
            'current_period_start': subscription.current_period_start,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'canceled_at': subscription.canceled_at,
            'plan_amount': subscription.plan.amount / 100,  # Convert from cents
            'plan_interval': subscription.plan.interval  # month, year
        }
    
    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving subscription: {e}")
        return None


def cancel_subscription(subscription_id, at_period_end=True):
    """
    Cancel a subscription
    
    Args:
        subscription_id: Stripe Subscription ID
        at_period_end: If True, cancel at end of billing period (default)
                      If False, cancel immediately
    
    Returns:
        True if successful, False otherwise
    """
    if not STRIPE_SECRET_KEY:
        return False
    
    try:
        if at_period_end:
            # Cancel at end of period (user keeps access until then)
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        else:
            # Cancel immediately
            subscription = stripe.Subscription.delete(subscription_id)
        
        logger.info(f"Cancelled subscription {subscription_id}")
        return True
    
    except stripe.error.StripeError as e:
        logger.error(f"Error cancelling subscription: {e}")
        return False


def get_customer_subscriptions(customer_id):
    """
    Get all subscriptions for a customer
    
    Args:
        customer_id: Stripe Customer ID
    
    Returns:
        List of subscription dicts or None
    """
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            limit=10
        )
        
        return [{
            'id': sub.id,
            'status': sub.status,
            'current_period_end': sub.current_period_end,
            'cancel_at_period_end': sub.cancel_at_period_end,
            'plan_amount': sub.plan.amount / 100,
            'plan_interval': sub.plan.interval
        } for sub in subscriptions.data]
    
    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving customer subscriptions: {e}")
        return None


# Helper function to determine user tier from subscription
def get_tier_from_price_id(price_id):
    """
    Determine subscription tier from Stripe Price ID
    
    Args:
        price_id: Stripe Price ID
    
    Returns:
        'pro', 'pro_annual', 'premium', or 'free'
    """
    if price_id == STRIPE_PRO_PRICE_ID:
        return 'pro'
    elif price_id == STRIPE_PRO_ANNUAL_PRICE_ID:
        return 'pro_annual'
    elif price_id == STRIPE_PREMIUM_PRICE_ID:
        return 'premium'
    else:
        return 'free'
