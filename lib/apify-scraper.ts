/**
 * APIFY SCRAPING SERVICE
 * Handles Instagram and TikTok public profile scraping via Apify
 */

const APIFY_API_TOKEN = process.env.APIFY_API_TOKEN
const APIFY_INSTAGRAM_ACTOR = 'apify/instagram-profile-scraper'
const APIFY_TIKTOK_ACTOR = 'clockworks/tiktok-scraper'

interface ApifyRunStatus {
  status: 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'ABORTED'
  defaultDatasetId: string
}

interface InstagramData {
  username: string
  postsCount: number
  hashtags: Record<string, number>
  captions: string[]
  mentions: string[]
  collectedAt: string
}

interface TikTokData {
  username: string
  postsCount: number
  hashtags: Record<string, number>
  music: string[]
  captions: string[]
  collectedAt: string
}

/**
 * Scrape Instagram profile via Apify
 */
export async function scrapeInstagramProfile(username: string): Promise<InstagramData | null> {
  if (!APIFY_API_TOKEN) {
    console.error('[v0] APIFY_API_TOKEN not configured')
    return null
  }

  try {
    console.log(`[v0] Starting Instagram scrape for @${username}`)

    // Start Apify actor
    const runResponse = await fetch(
      `https://api.apify.com/v2/acts/${APIFY_INSTAGRAM_ACTOR}/runs?token=${APIFY_API_TOKEN}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          usernames: [username],
          resultsLimit: 100, // Get up to 100 posts
        }),
      }
    )

    if (!runResponse.ok) {
      console.error('[v0] Failed to start Instagram scraper:', runResponse.statusText)
      return null
    }

    const runData = await runResponse.json()
    const runId = runData.data.id
    const datasetId = runData.data.defaultDatasetId

    console.log(`[v0] Instagram scraper started, run ID: ${runId}`)

    // Poll for completion (max 3 minutes)
    const maxAttempts = 36 // 36 * 5s = 3 minutes
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 5000)) // Wait 5 seconds

      const statusResponse = await fetch(
        `https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_API_TOKEN}`
      )
      const statusData: { data: ApifyRunStatus } = await statusResponse.json()

      console.log(`[v0] Instagram scrape status: ${statusData.data.status}`)

      if (statusData.data.status === 'SUCCEEDED') {
        // Fetch results
        const datasetResponse = await fetch(
          `https://api.apify.com/v2/datasets/${datasetId}/items?token=${APIFY_API_TOKEN}`
        )
        const posts = await datasetResponse.json()

        return parseInstagramData(username, posts)
      }

      if (statusData.data.status === 'FAILED' || statusData.data.status === 'ABORTED') {
        console.error('[v0] Instagram scraper failed')
        return null
      }
    }

    console.error('[v0] Instagram scraper timed out')
    return null
  } catch (error) {
    console.error('[v0] Instagram scrape error:', error)
    return null
  }
}

/**
 * Scrape TikTok profile via Apify
 */
export async function scrapeTikTokProfile(username: string): Promise<TikTokData | null> {
  if (!APIFY_API_TOKEN) {
    console.error('[v0] APIFY_API_TOKEN not configured')
    return null
  }

  try {
    console.log(`[v0] Starting TikTok scrape for @${username}`)

    // Start Apify actor
    const runResponse = await fetch(
      `https://api.apify.com/v2/acts/${APIFY_TIKTOK_ACTOR}/runs?token=${APIFY_API_TOKEN}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profiles: [username],
          resultsPerPage: 100,
        }),
      }
    )

    if (!runResponse.ok) {
      console.error('[v0] Failed to start TikTok scraper:', runResponse.statusText)
      return null
    }

    const runData = await runResponse.json()
    const runId = runData.data.id
    const datasetId = runData.data.defaultDatasetId

    console.log(`[v0] TikTok scraper started, run ID: ${runId}`)

    // Poll for completion (max 3 minutes)
    const maxAttempts = 36
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 5000))

      const statusResponse = await fetch(
        `https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_API_TOKEN}`
      )
      const statusData: { data: ApifyRunStatus } = await statusResponse.json()

      console.log(`[v0] TikTok scrape status: ${statusData.data.status}`)

      if (statusData.data.status === 'SUCCEEDED') {
        const datasetResponse = await fetch(
          `https://api.apify.com/v2/datasets/${datasetId}/items?token=${APIFY_API_TOKEN}`
        )
        const posts = await datasetResponse.json()

        return parseTikTokData(username, posts)
      }

      if (statusData.data.status === 'FAILED' || statusData.data.status === 'ABORTED') {
        console.error('[v0] TikTok scraper failed')
        return null
      }
    }

    console.error('[v0] TikTok scraper timed out')
    return null
  } catch (error) {
    console.error('[v0] TikTok scrape error:', error)
    return null
  }
}

/**
 * Parse Instagram API response into structured data
 */
function parseInstagramData(username: string, posts: any[]): InstagramData {
  const hashtags: Record<string, number> = {}
  const captions: string[] = []
  const mentions: string[] = []

  for (const post of posts) {
    // Extract hashtags
    const caption = post.caption || ''
    captions.push(caption.substring(0, 200))

    const hashtagMatches = caption.match(/#(\w+)/g) || []
    for (const tag of hashtagMatches) {
      hashtags[tag] = (hashtags[tag] || 0) + 1
    }

    // Extract mentions
    const mentionMatches = caption.match(/@(\w+)/g) || []
    for (const mention of mentionMatches) {
      if (!mentions.includes(mention)) {
        mentions.push(mention)
      }
    }
  }

  return {
    username,
    postsCount: posts.length,
    hashtags,
    captions: captions.slice(0, 50), // Top 50 captions
    mentions: mentions.slice(0, 30), // Top 30 mentions
    collectedAt: new Date().toISOString(),
  }
}

/**
 * Parse TikTok API response into structured data
 */
function parseTikTokData(username: string, posts: any[]): TikTokData {
  const hashtags: Record<string, number> = {}
  const music: string[] = []
  const captions: string[] = []

  for (const post of posts) {
    // Extract hashtags
    const postHashtags = post.hashtags || []
    for (const tag of postHashtags) {
      const tagName = typeof tag === 'string' ? tag : tag.name
      if (tagName) {
        hashtags[`#${tagName}`] = (hashtags[`#${tagName}`] || 0) + 1
      }
    }

    // Extract music
    const musicName = post.musicMeta?.musicName || post.music?.title
    if (musicName && !music.includes(musicName)) {
      music.push(musicName)
    }

    // Extract caption
    const caption = post.text || post.caption || ''
    if (caption) {
      captions.push(caption.substring(0, 200))
    }
  }

  return {
    username,
    postsCount: posts.length,
    hashtags,
    music: music.slice(0, 30), // Top 30 songs
    captions: captions.slice(0, 50), // Top 50 captions
    collectedAt: new Date().toISOString(),
  }
}
