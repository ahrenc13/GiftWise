import { createClient } from '@/lib/supabase/server'
import { NextRequest, NextResponse } from 'next/server'
import { scrapeInstagram, scrapeTikTok } from '@/lib/apify-scraper'
import { scrapeYouTube, scrapeGoodreads, scrapeLastFm } from '@/lib/additional-scrapers'

export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient()
    
    // Get current user
    const { data: { user }, error: userError } = await supabase.auth.getUser()
    
    if (userError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { platform, username } = await request.json()

    if (!platform || !username) {
      return NextResponse.json({ error: 'Platform and username required' }, { status: 400 })
    }

    console.log(`[v0] Connecting ${platform} for user ${user.id}, username: ${username}`)

    // Check if connection already exists
    const { data: existingConnection } = await supabase
      .from('oauth_connections')
      .select('*')
      .eq('user_id', user.id)
      .eq('platform', platform)
      .single()

    if (existingConnection) {
      return NextResponse.json({ error: 'Platform already connected' }, { status: 400 })
    }

    // Create connection record
    const { data: connection, error: connectionError } = await supabase
      .from('oauth_connections')
      .insert({
        user_id: user.id,
        platform,
        platform_username: username,
        status: 'pending',
      })
      .select()
      .single()

    if (connectionError) {
      console.error('[v0] Error creating connection:', connectionError)
      return NextResponse.json({ error: 'Failed to create connection' }, { status: 500 })
    }

    // Initiate scraping based on platform
    let scrapedData = null
    
    try {
      if (platform === 'instagram') {
        console.log('[v0] Starting Instagram scrape...')
        scrapedData = await scrapeInstagram(username)
      } else if (platform === 'tiktok') {
        console.log('[v0] Starting TikTok scrape...')
        scrapedData = await scrapeTikTok(username)
      } else if (platform === 'youtube') {
        console.log('[v0] Starting YouTube scrape...')
        scrapedData = await scrapeYouTube(username)
      } else if (platform === 'goodreads') {
        console.log('[v0] Starting Goodreads scrape...')
        scrapedData = await scrapeGoodreads(username)
      } else if (platform === 'lastfm') {
        console.log('[v0] Starting Last.fm scrape...')
        scrapedData = await scrapeLastFm(username)
      } else {
        return NextResponse.json({ error: 'Platform not supported for scraping' }, { status: 400 })
      }

      console.log('[v0] Scraping completed, storing data...')

      // Store scraped data in social_profiles
      const { error: profileError } = await supabase
        .from('social_profiles')
        .insert({
          user_id: user.id,
          platform,
          platform_username: username,
          profile_data: scrapedData,
          scraped_at: new Date().toISOString(),
        })

      if (profileError) {
        console.error('[v0] Error storing profile data:', profileError)
      }

      // Update connection status to active
      await supabase
        .from('oauth_connections')
        .update({ status: 'active' })
        .eq('id', connection.id)

      console.log('[v0] Platform connected successfully')

      return NextResponse.json({ 
        success: true, 
        message: `${platform} connected successfully`,
        data: scrapedData 
      })

    } catch (scrapeError: any) {
      console.error('[v0] Scraping error:', scrapeError)
      
      // Update connection status to error
      await supabase
        .from('oauth_connections')
        .update({ 
          status: 'error',
          error_message: scrapeError.message 
        })
        .eq('id', connection.id)

      return NextResponse.json({ 
        error: `Failed to scrape ${platform}: ${scrapeError.message}` 
      }, { status: 500 })
    }

  } catch (error: any) {
    console.error('[v0] Connection error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}
