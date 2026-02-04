import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { scrapeInstagramProfile, scrapeTikTokProfile } from '@/lib/apify-scraper'

/**
 * API Route: Scrape social media profile data
 * Called automatically when user connects a platform with username
 */
export async function POST(request: NextRequest) {
  try {
    const { platform, username, userId } = await request.json()

    console.log('[v0] Starting scrape for:', platform, username)

    if (!platform || !username) {
      return NextResponse.json({ error: 'Missing platform or username' }, { status: 400 })
    }

    const supabase = await createClient()

    // Verify user is authenticated
    const { data: { user } } = await supabase.auth.getUser()
    if (!user || (userId && user.id !== userId)) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    let scrapedData = null

    // Scrape based on platform
    if (platform === 'instagram') {
      scrapedData = await scrapeInstagramProfile(username)
    } else if (platform === 'tiktok') {
      scrapedData = await scrapeTikTokProfile(username)
    } else {
      return NextResponse.json({ error: 'Unsupported platform for scraping' }, { status: 400 })
    }

    if (!scrapedData) {
      return NextResponse.json({ error: 'Scraping failed' }, { status: 500 })
    }

    // Save scraped data to social_profiles table
    const { error: saveError } = await supabase
      .from('social_profiles')
      .upsert({
        user_id: user.id,
        platform,
        platform_username: username,
        profile_data: scrapedData,
        scraped_at: new Date().toISOString(),
      }, {
        onConflict: 'user_id,platform,platform_username'
      })

    if (saveError) {
      console.error('[v0] Error saving scraped data:', saveError)
      return NextResponse.json({ error: 'Failed to save data' }, { status: 500 })
    }

    console.log('[v0] Scraping complete and data saved')

    return NextResponse.json({
      success: true,
      platform,
      username,
      dataPoints: platform === 'instagram' 
        ? Object.keys(scrapedData.hashtags).length 
        : scrapedData.postsCount
    })
  } catch (error) {
    console.error('[v0] Scraping API error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
