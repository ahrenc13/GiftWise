/**
 * Viral Growth System
 * Handles shareable wishlists, referral tracking, and credit rewards
 */

import { createClient } from '@/lib/supabase/server'
import crypto from 'crypto'

/**
 * Generate unique share ID for recommendations
 */
export function generateShareId(userId: string, sessionId: string): string {
  const data = `${userId}:${sessionId}:${Date.now()}`
  return crypto.createHash('md5').update(data).digest('hex').substring(0, 12)
}

/**
 * Generate referral code from email
 */
export function generateReferralCode(email: string): string {
  const hash = crypto.createHash('md5').update(email).digest('hex')
  return `GIFT${hash.substring(0, 4).toUpperCase()}`
}

/**
 * Create shareable link for recommendations
 */
export async function createShareableLink(sessionId: string, userId: string) {
  const supabase = await createClient()
  
  const shareId = generateShareId(userId, sessionId)
  
  // Create share record
  const { data, error } = await supabase
    .from('shared_recommendations')
    .insert({
      share_id: shareId,
      user_id: userId,
      session_id: sessionId,
      is_public: true,
      expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days
    })
    .select()
    .single()

  if (error) {
    console.error('[v0] Error creating share:', error)
    throw error
  }

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
  const shareUrl = `${baseUrl}/share/${shareId}`

  return {
    shareId,
    shareUrl,
    shareText: '🎁 Help me pick the perfect gift! Which one would you choose?',
    twitterText: '🎁 I found these amazing gift ideas - which one should I choose? #GiftWise',
  }
}

/**
 * Track share event (view, click, conversion)
 */
export async function trackShareEvent(
  shareId: string,
  eventType: 'view' | 'click' | 'conversion',
  metadata?: {
    productIndex?: number
    referrerUrl?: string
    ipAddress?: string
    userAgent?: string
  }
) {
  const supabase = await createClient()

  // Insert event
  await supabase.from('share_events').insert({
    share_id: shareId,
    event_type: eventType,
    product_index: metadata?.productIndex,
    referrer_url: metadata?.referrerUrl,
    ip_address: metadata?.ipAddress,
    user_agent: metadata?.userAgent,
  })

  // Update counts on share
  const updateField =
    eventType === 'view' ? 'views' : eventType === 'click' ? 'clicks' : 'conversions'

  await supabase.rpc('increment_share_count', {
    share_id_param: shareId,
    field: updateField,
  })
}

/**
 * Get or create referral code for user
 */
export async function getOrCreateReferralCode(userId: string, email: string) {
  const supabase = await createClient()

  // Check if user already has code
  const { data: profile } = await supabase
    .from('profiles')
    .select('referral_code')
    .eq('id', userId)
    .single()

  if (profile?.referral_code) {
    return profile.referral_code
  }

  // Generate new code
  const code = generateReferralCode(email)

  // Update profile
  await supabase.from('profiles').update({ referral_code: code }).eq('id', userId)

  return code
}

/**
 * Apply referral code to new user
 */
export async function applyReferralCode(newUserId: string, referralCode: string) {
  const supabase = await createClient()

  // Find referrer by code
  const { data: referrer } = await supabase
    .from('profiles')
    .select('id')
    .eq('referral_code', referralCode)
    .single()

  if (!referrer) {
    return { success: false, error: 'Invalid referral code' }
  }

  // Update new user's profile
  await supabase.from('profiles').update({ referred_by: referrer.id }).eq('id', newUserId)

  // Award credits to referrer
  const creditAmount = 5.0 // $5 credit

  await supabase
    .from('profiles')
    .update({
      referral_credits: supabase.raw('referral_credits + ?', [creditAmount]),
      total_referrals: supabase.raw('total_referrals + 1'),
    })
    .eq('id', referrer.id)

  // Create referral record
  await supabase.from('referrals').insert({
    referrer_id: referrer.id,
    referred_user_id: newUserId,
    referral_code: referralCode,
    status: 'completed',
    credit_awarded: creditAmount,
    completed_at: new Date().toISOString(),
  })

  return { success: true, creditAwarded: creditAmount }
}

/**
 * Get user's viral metrics
 */
export async function getViralMetrics(userId: string) {
  const supabase = await createClient()

  const { data: profile } = await supabase
    .from('profiles')
    .select('total_referrals, referral_credits, referral_tier, referral_code')
    .eq('id', userId)
    .single()

  const { data: shares } = await supabase
    .from('shared_recommendations')
    .select('views, clicks, conversions')
    .eq('user_id', userId)

  const totalViews = shares?.reduce((sum, s) => sum + (s.views || 0), 0) || 0
  const totalClicks = shares?.reduce((sum, s) => sum + (s.clicks || 0), 0) || 0
  const totalConversions = shares?.reduce((sum, s) => sum + (s.conversions || 0), 0) || 0

  // Calculate k-factor (viral coefficient)
  const kFactor = shares && shares.length > 0 ? totalConversions / shares.length : 0

  return {
    referralCode: profile?.referral_code,
    totalReferrals: profile?.total_referrals || 0,
    creditsEarned: profile?.referral_credits || 0,
    tier: profile?.referral_tier || 'bronze',
    totalShares: shares?.length || 0,
    totalViews,
    totalClicks,
    totalConversions,
    kFactor,
    conversionRate: totalViews > 0 ? (totalConversions / totalViews) * 100 : 0,
  }
}

/**
 * Get leaderboard for gamification
 */
export async function getLeaderboard(limit = 10) {
  const supabase = await createClient()

  const { data } = await supabase
    .from('profiles')
    .select('id, full_name, total_referrals, referral_tier')
    .order('total_referrals', { ascending: false })
    .limit(limit)

  return data || []
}
