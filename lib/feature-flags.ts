/**
 * Feature Flags - Control product features via environment variables
 */

export const FEATURES = {
  /**
   * Payment enforcement - set to "true" to require subscriptions
   * During testing: set to "false" to allow unlimited free use
   * For launch: set to "true" to enforce freemium limits
   */
  PAYMENTS_ENABLED: process.env.NEXT_PUBLIC_PAYMENTS_ENABLED === 'true',

  /**
   * Viral features - referral system and sharing
   */
  REFERRALS_ENABLED: process.env.NEXT_PUBLIC_REFERRALS_ENABLED !== 'false', // Default ON

  /**
   * Advanced scraping - YouTube, Last.fm, etc
   */
  ADVANCED_SCRAPING_ENABLED: process.env.NEXT_PUBLIC_ADVANCED_SCRAPING_ENABLED !== 'false', // Default ON
}

/**
 * Get user tier limits based on subscription
 */
export function getUserLimits(subscriptionTier: string | null) {
  // If payments disabled, everyone gets unlimited
  if (!FEATURES.PAYMENTS_ENABLED) {
    return {
      monthlyRecommendations: 999,
      tier: 'unlimited-testing',
      canGenerate: true,
    }
  }

  // Payments enabled - enforce tiers
  switch (subscriptionTier) {
    case 'pro':
      return {
        monthlyRecommendations: 999, // Unlimited
        tier: 'pro',
        canGenerate: true,
      }
    case 'basic':
      return {
        monthlyRecommendations: 5,
        tier: 'basic',
        canGenerate: true,
      }
    case 'free':
    default:
      return {
        monthlyRecommendations: 1,
        tier: 'free',
        canGenerate: true,
      }
  }
}

/**
 * Check if user can generate a recommendation
 */
export async function canUserGenerate(
  userId: string,
  subscriptionTier: string | null,
  supabase: any
): Promise<{ allowed: boolean; reason?: string; remainingCount?: number }> {
  // Payments disabled = always allow
  if (!FEATURES.PAYMENTS_ENABLED) {
    return { allowed: true, remainingCount: 999 }
  }

  const limits = getUserLimits(subscriptionTier)

  // Pro tier = unlimited
  if (subscriptionTier === 'pro') {
    return { allowed: true, remainingCount: 999 }
  }

  // Check monthly usage
  const startOfMonth = new Date()
  startOfMonth.setDate(1)
  startOfMonth.setHours(0, 0, 0, 0)

  const { count } = await supabase
    .from('recommendation_sessions')
    .select('*', { count: 'exact', head: true })
    .eq('user_id', userId)
    .gte('created_at', startOfMonth.toISOString())

  const used = count || 0
  const remaining = limits.monthlyRecommendations - used

  if (remaining <= 0) {
    return {
      allowed: false,
      reason: `You've used all ${limits.monthlyRecommendations} recommendations this month. Upgrade to get more!`,
      remainingCount: 0,
    }
  }

  return {
    allowed: true,
    remainingCount: remaining,
  }
}
