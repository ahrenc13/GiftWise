/**
 * SerpAPI Enrichment Layer
 * Adds real-time trending products, Reddit insights, and demographic validation
 */

interface TrendingProduct {
  title: string
  price: string
  source: string
  rating?: number
  link: string
}

interface RedditInsight {
  subreddit: string
  topPosts: string[]
  communityInterests: string[]
}

interface DemographicTrend {
  category: string
  trend: string
  confidence: number
}

/**
 * Get trending products for specific interests
 */
export async function getTrendingProducts(interests: string[]): Promise<TrendingProduct[]> {
  const apiKey = process.env.SERPAPI_API_KEY
  if (!apiKey) {
    console.log('[v0] SerpAPI key not set, skipping trending products')
    return []
  }

  const products: TrendingProduct[] = []

  try {
    // Get trending products for top 3 interests
    for (const interest of interests.slice(0, 3)) {
      const query = `best ${interest} gifts 2026`
      const response = await fetch(
        `https://serpapi.com/search.json?q=${encodeURIComponent(query)}&engine=google_shopping&api_key=${apiKey}&num=5`
      )

      if (!response.ok) continue

      const data = await response.json()
      
      if (data.shopping_results) {
        data.shopping_results.forEach((item: any) => {
          products.push({
            title: item.title,
            price: item.price || 'Price varies',
            source: item.source || 'Online retailer',
            rating: item.rating,
            link: item.link,
          })
        })
      }
    }

    console.log(`[v0] Found ${products.length} trending products via SerpAPI`)
    return products.slice(0, 20) // Limit to 20 products
  } catch (error) {
    console.error('[v0] SerpAPI trending products error:', error)
    return []
  }
}

/**
 * Get Reddit community insights for interests
 */
export async function getRedditInsights(interests: string[]): Promise<RedditInsight[]> {
  const apiKey = process.env.SERPAPI_API_KEY
  if (!apiKey) {
    console.log('[v0] SerpAPI key not set, skipping Reddit insights')
    return []
  }

  const insights: RedditInsight[] = []

  try {
    // Find relevant subreddits for top interests
    for (const interest of interests.slice(0, 3)) {
      const query = `site:reddit.com ${interest} recommendations`
      const response = await fetch(
        `https://serpapi.com/search.json?q=${encodeURIComponent(query)}&engine=google&api_key=${apiKey}&num=10`
      )

      if (!response.ok) continue

      const data = await response.json()
      
      if (data.organic_results) {
        const redditPosts = data.organic_results
          .filter((result: any) => result.link?.includes('reddit.com'))
          .slice(0, 5)

        if (redditPosts.length > 0) {
          // Extract subreddit names
          const subreddits = new Set<string>()
          const topPosts: string[] = []

          redditPosts.forEach((post: any) => {
            const match = post.link?.match(/reddit\.com\/r\/([^/]+)/)
            if (match) subreddits.add(match[1])
            if (post.title) topPosts.push(post.title)
          })

          if (subreddits.size > 0) {
            insights.push({
              subreddit: Array.from(subreddits)[0],
              topPosts: topPosts.slice(0, 3),
              communityInterests: [interest],
            })
          }
        }
      }
    }

    console.log(`[v0] Found ${insights.length} Reddit communities via SerpAPI`)
    return insights
  } catch (error) {
    console.error('[v0] SerpAPI Reddit insights error:', error)
    return []
  }
}

/**
 * Get demographic trends for age/location
 */
export async function getDemographicTrends(
  age?: number,
  location?: string,
  interests?: string[]
): Promise<DemographicTrend[]> {
  const apiKey = process.env.SERPAPI_API_KEY
  if (!apiKey) {
    console.log('[v0] SerpAPI key not set, skipping demographic trends')
    return []
  }

  const trends: DemographicTrend[] = []

  try {
    // Build demographic query
    let query = 'trending gifts 2026'
    if (age) {
      if (age < 25) query = 'trending gifts Gen Z 2026'
      else if (age < 40) query = 'trending gifts millennials 2026'
      else query = 'trending gifts 2026'
    }
    if (location) query += ` ${location}`

    const response = await fetch(
      `https://serpapi.com/search.json?q=${encodeURIComponent(query)}&engine=google&api_key=${apiKey}&num=10`
    )

    if (!response.ok) return trends

    const data = await response.json()

    // Extract trends from search results
    if (data.organic_results) {
      data.organic_results.slice(0, 5).forEach((result: any) => {
        if (result.snippet) {
          trends.push({
            category: 'demographic',
            trend: result.snippet,
            confidence: 75,
          })
        }
      })
    }

    // Get trending searches
    if (data.related_searches) {
      data.related_searches.slice(0, 5).forEach((search: any) => {
        trends.push({
          category: 'trending',
          trend: search.query,
          confidence: 60,
        })
      })
    }

    console.log(`[v0] Found ${trends.length} demographic trends via SerpAPI`)
    return trends
  } catch (error) {
    console.error('[v0] SerpAPI demographic trends error:', error)
    return []
  }
}

/**
 * Verify product availability and get real prices
 */
export async function verifyProductAvailability(productName: string): Promise<{
  available: boolean
  price?: string
  retailer?: string
  link?: string
}> {
  const apiKey = process.env.SERPAPI_API_KEY
  if (!apiKey) {
    return { available: true } // Assume available if can't verify
  }

  try {
    const response = await fetch(
      `https://serpapi.com/search.json?q=${encodeURIComponent(productName)}&engine=google_shopping&api_key=${apiKey}&num=3`
    )

    if (!response.ok) return { available: true }

    const data = await response.json()

    if (data.shopping_results && data.shopping_results.length > 0) {
      const topResult = data.shopping_results[0]
      return {
        available: true,
        price: topResult.price,
        retailer: topResult.source,
        link: topResult.link,
      }
    }

    return { available: false }
  } catch (error) {
    console.error('[v0] Product verification error:', error)
    return { available: true }
  }
}

/**
 * Get category bestsellers
 */
export async function getCategoryBestsellers(category: string): Promise<string[]> {
  const apiKey = process.env.SERPAPI_API_KEY
  if (!apiKey) return []

  try {
    const query = `best ${category} 2026`
    const response = await fetch(
      `https://serpapi.com/search.json?q=${encodeURIComponent(query)}&engine=google&api_key=${apiKey}&num=10`
    )

    if (!response.ok) return []

    const data = await response.json()
    const bestsellers: string[] = []

    if (data.organic_results) {
      data.organic_results.slice(0, 10).forEach((result: any) => {
        if (result.title) {
          bestsellers.push(result.title)
        }
      })
    }

    return bestsellers
  } catch (error) {
    console.error('[v0] Bestsellers error:', error)
    return []
  }
}
