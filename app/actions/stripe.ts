'use server'

import { stripe } from '@/lib/stripe'
import { PRODUCTS } from '@/lib/products'
import { createClient } from '@/lib/supabase/server'

export async function startCheckout(productId: string) {
  console.log('[v0] Starting Stripe checkout for product:', productId)
  
  try {
    const product = PRODUCTS.find((p) => p.id === productId)
    
    if (!product) {
      console.error('[v0] Product not found:', productId)
      throw new Error('Product not found')
    }

    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()
    
    if (!user) {
      throw new Error('Not authenticated')
    }

    // Get or create Stripe customer
    const { data: profile } = await supabase
      .from('profiles')
      .select('stripe_customer_id')
      .eq('id', user.id)
      .single()

    let customerId = profile?.stripe_customer_id

    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email,
        metadata: {
          supabase_user_id: user.id,
        },
      })
      customerId = customer.id

      // Save customer ID to profile
      await supabase
        .from('profiles')
        .update({ stripe_customer_id: customerId })
        .eq('id', user.id)
    }

    console.log('[v0] Creating checkout session')

    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      line_items: [
        {
          price_data: {
            currency: 'usd',
            product_data: {
              name: product.name,
              description: product.description,
            },
            unit_amount: product.priceInCents,
            recurring: {
              interval: 'month',
            },
          },
          quantity: 1,
        },
      ],
      mode: 'subscription',
      ui_mode: 'embedded',
      return_url: `${process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'}/pricing/success?session_id={CHECKOUT_SESSION_ID}`,
      metadata: {
        product_id: productId,
        user_id: user.id,
        tier: product.tier,
      },
    })

    console.log('[v0] Checkout session created:', session.id)

    return { clientSecret: session.client_secret }
  } catch (error) {
    console.error('[v0] Error creating checkout session:', error)
    throw error
  }
}

export async function verifyCheckoutSession(sessionId: string) {
  console.log('[v0] Verifying checkout session:', sessionId)
  
  try {
    const session = await stripe.checkout.sessions.retrieve(sessionId)
    
    if (session.payment_status === 'paid') {
      const supabase = await createClient()
      const userId = session.metadata?.user_id
      const tier = session.metadata?.tier
      const productId = session.metadata?.product_id

      if (userId && tier) {
        const product = PRODUCTS.find((p) => p.id === productId)
        
        // Update user subscription
        await supabase
          .from('profiles')
          .update({
            subscription_tier: tier,
            credits_remaining: product?.credits || 10,
            stripe_customer_id: session.customer as string,
          })
          .eq('id', userId)

        // Record purchase
        await supabase
          .from('purchases')
          .insert({
            user_id: userId,
            stripe_payment_intent_id: session.payment_intent as string,
            stripe_subscription_id: session.subscription as string,
            amount: session.amount_total ? session.amount_total / 100 : 0,
            currency: 'usd',
            purchase_type: 'subscription',
            status: 'completed',
          })

        console.log('[v0] Subscription activated for user:', userId)
      }
    }

    return { status: session.payment_status, session }
  } catch (error) {
    console.error('[v0] Error verifying session:', error)
    throw error
  }
}
