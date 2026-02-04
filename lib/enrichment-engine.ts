/**
 * ENRICHMENT INTELLIGENCE LAYER
 * Enhances social media data with demographic trends, subreddit analysis, and deep signal extraction
 * 
 * This is the "secret sauce" - takes raw social data and enriches it with contextual intelligence
 */

interface SocialProfile {
  instagram?: {
    hashtags: Record<string, number>
    captions: string[]
    mentions: string[]
  }
  tiktok?: {
    hashtags: Record<string, number>
    music: string[]
    captions: string[]
  }
  pinterest?: {
    boards: Array<{ name: string; pins: Array<{ title: string; description: string }> }>
  }
  youtube?: {
    channels: string[]
    interests: string[]
    playlists: { name: string; videos: string[] }[]
  }
  goodreads?: {
    read: { title: string; author: string; rating: number }[]
    toRead: { title: string; author: string }[]
    genres: string[]
  }
  lastfm?: {
    topArtists: { name: string; playcount: number }[]
    topTracks: { name: string; artist: string }[]
    genres: string[]
  }
}

interface RecipientInfo {
  name: string
  age?: number
  location?: string
  relationship: string
  gender?: string
}

interface EnrichedProfile {
  coreInterests: string[]
  aestheticPreferences: string[]
  lifestyleSignals: string[]
  demographicTrends: string[]
  relevantSubreddits: string[]
  trendingProducts: string[]
  redditCommunities: string[]
  categoryBestsellers: string[]
  deepSignals: {
    aspirational?: string[]
    current_investments?: string[]
    aesthetic_style?: string
    activity_level?: string
    price_sensitivity?: string
  }
  confidence: number
}

/**
 * Enrichment Intelligence Layer
 * Takes raw social data and enriches it with cross-platform insights, 
 * demographic trends, and validation to maximize gift recommendation accuracy
 */

import {
  getTrendingProducts,
  getRedditInsights,
  getDemographicTrends,
  getCategoryBestsellers,
} from './serpapi-enrichment'
export async function enrichSocialProfile(
  social: SocialProfile,
  recipient: RecipientInfo
): Promise<EnrichedProfile> {
  console.log('[v0] Starting profile enrichment...')

  // Step 1: Extract core interests from social media
  const coreInterests = extractCoreInterests(social)

  // Step 2: Identify aesthetic preferences
  const aestheticPreferences = extractAestheticPreferences(social)

  // Step 3: Analyze lifestyle signals
  const lifestyleSignals = extractLifestyleSignals(social)

  // Step 4: Match to demographic trends
  const demographicTrends = mapDemographicTrends(coreInterests, recipient)

  // Step 5: Find relevant subreddits for deeper research
  const relevantSubreddits = findRelevantSubreddits(coreInterests, aestheticPreferences)

  // Step 6: Deep signal extraction (aspirations, existing items, etc.)
  const deepSignals = extractDeepSignals(social, coreInterests)

  // Step 7: Get real-time trending products (SerpAPI)
  const trendingProducts = await getTrendingProducts(coreInterests)
  const trendingTitles = trendingProducts.map(p => p.title)

  // Step 8: Get Reddit community insights (SerpAPI)
  const redditInsights = await getRedditInsights(coreInterests)
  const redditCommunities = redditInsights.map(r => `r/${r.subreddit}`)

  // Step 9: Get demographic trends (SerpAPI)
  const serpDemographicTrends = await getDemographicTrends(
    recipient.age,
    recipient.location,
    coreInterests
  )
  const serpTrends = serpDemographicTrends.map(t => t.trend)

  // Step 10: Get category bestsellers
  const categoryBestsellers: string[] = []
  for (const interest of coreInterests.slice(0, 3)) {
    const bestsellers = await getCategoryBestsellers(interest)
    categoryBestsellers.push(...bestsellers.slice(0, 5))
  }

  // Step 11: Calculate confidence score
  const confidence = calculateConfidenceScore(social, coreInterests)

  console.log('[v0] Enrichment complete with SerpAPI:', {
    coreInterests: coreInterests.length,
    aesthetics: aestheticPreferences.length,
    trendingProducts: trendingTitles.length,
    redditCommunities: redditCommunities.length,
    confidence,
  })

  return {
    coreInterests,
    aestheticPreferences,
    lifestyleSignals,
    demographicTrends: [...demographicTrends, ...serpTrends],
    relevantSubreddits,
    trendingProducts: trendingTitles,
    redditCommunities,
    categoryBestsellers,
    deepSignals,
    confidence,
  }
}

/**
 * Extract core interests from all social platforms including YouTube, Goodreads, Last.fm
 */
function extractCoreInterests(social: SocialProfile): string[] {
  const interests = new Set<string>()

  // YouTube interests - explicit from channel categories
  if (social.youtube?.interests) {
    social.youtube.interests.forEach(interest => interests.add(interest))
  }

  // Goodreads interests - book genres reveal deep interests
  if (social.goodreads?.genres) {
    social.goodreads.genres.forEach(genre => {
      interests.add(`Reading: ${genre}`)
    })
  }

  // Last.fm music taste
  if (social.lastfm?.topArtists && social.lastfm.topArtists.length > 0) {
    interests.add('Music')
    // Add specific genres if available
    social.lastfm.genres?.forEach(genre => {
      interests.add(`Music: ${genre}`)
    })
  }

  // From Instagram hashtags
  if (social.instagram) {
    const topHashtags = Object.entries(social.instagram.hashtags)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 20)
      .map(([tag]) => tag.toLowerCase().replace('#', ''))

    for (const tag of topHashtags) {
      const interest = mapHashtagToInterest(tag)
      if (interest) interests.add(interest)
    }

    // Analyze captions for interest keywords
    const captionText = social.instagram.captions.join(' ').toLowerCase()
    extractInterestsFromText(captionText, interests)
  }

  // From TikTok
  if (social.tiktok) {
    const topHashtags = Object.entries(social.tiktok.hashtags)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 20)
      .map(([tag]) => tag.toLowerCase().replace('#', ''))

    for (const tag of topHashtags) {
      const interest = mapHashtagToInterest(tag)
      if (interest) interests.add(interest)
    }

    // Music preferences indicate interests
    for (const song of social.tiktok.music.slice(0, 15)) {
      const genre = inferMusicGenre(song)
      if (genre) interests.add(genre)
    }
  }

  // From Pinterest
  if (social.pinterest) {
    for (const board of social.pinterest.boards) {
      const boardInterest = mapBoardNameToInterest(board.name)
      if (boardInterest) interests.add(boardInterest)

      for (const pin of board.pins.slice(0, 10)) {
        const pinText = `${pin.title} ${pin.description}`.toLowerCase()
        extractInterestsFromText(pinText, interests)
      }
    }
  }

  return Array.from(interests).slice(0, 15) // Top 15 interests
}

/**
 * Extract aesthetic preferences (minimalist, maximalist, vintage, modern, etc.)
 */
function extractAestheticPreferences(social: SocialProfile): string[] {
  const aesthetics = new Set<string>()

  const aestheticKeywords = {
    minimalist: ['minimal', 'clean', 'simple', 'monochrome', 'neutral'],
    maximalist: ['colorful', 'bold', 'eclectic', 'vibrant', 'maximalist'],
    vintage: ['vintage', 'retro', '90s', '80s', 'antique', 'classic'],
    modern: ['modern', 'contemporary', 'sleek', 'minimalist'],
    bohemian: ['boho', 'bohemian', 'eclectic', 'artsy'],
    industrial: ['industrial', 'urban', 'concrete', 'metal'],
    cottagecore: ['cottage', 'cozy', 'cottagecore', 'rural', 'countryside'],
    dark_academia: ['dark academia', 'books', 'classical', 'gothic'],
  }

  const allText = [
    ...(social.instagram?.captions || []),
    ...(social.tiktok?.captions || []),
    ...(social.pinterest?.boards.flatMap((b) => b.pins.map((p) => p.title + ' ' + p.description)) ||
      []),
  ]
    .join(' ')
    .toLowerCase()

  for (const [aesthetic, keywords] of Object.entries(aestheticKeywords)) {
    if (keywords.some((keyword) => allText.includes(keyword))) {
      aesthetics.add(aesthetic)
    }
  }

  return Array.from(aesthetics)
}

/**
 * Extract lifestyle signals (active, creative, tech-savvy, etc.)
 */
function extractLifestyleSignals(social: SocialProfile): string[] {
  const signals = new Set<string>()

  const lifestylePatterns = {
    fitness_enthusiast: ['gym', 'workout', 'fitness', 'running', 'yoga', 'training'],
    foodie: ['food', 'cooking', 'recipe', 'restaurant', 'chef', 'baking'],
    traveler: ['travel', 'vacation', 'explore', 'adventure', 'trip', 'wanderlust'],
    creative: ['art', 'design', 'creative', 'diy', 'craft', 'painting'],
    tech_savvy: ['tech', 'coding', 'app', 'software', 'gadget', 'programming'],
    reader: ['book', 'reading', 'novel', 'author', 'bookstagram'],
    gamer: ['gaming', 'gamer', 'game', 'console', 'pc', 'playstation', 'xbox'],
    music_lover: ['music', 'concert', 'festival', 'band', 'artist', 'song'],
    fashionista: ['fashion', 'style', 'outfit', 'ootd', 'designer', 'clothes'],
    homebody: ['home', 'cozy', 'interior', 'decor', 'house'],
  }

  const allHashtags = [
    ...Object.keys(social.instagram?.hashtags || {}),
    ...Object.keys(social.tiktok?.hashtags || {}),
  ]
    .map((h) => h.toLowerCase())
    .join(' ')

  for (const [lifestyle, keywords] of Object.entries(lifestylePatterns)) {
    const matchCount = keywords.filter((keyword) => allHashtags.includes(keyword)).length
    if (matchCount >= 2) {
      // Require at least 2 keyword matches
      signals.add(lifestyle)
    }
  }

  return Array.from(signals)
}

/**
 * Map interests to demographic trends for that age/gender group
 */
function mapDemographicTrends(interests: string[], recipient: RecipientInfo): string[] {
  const trends: string[] = []

  // Demographic trend mappings (simplified - could be much more sophisticated)
  if (recipient.age && recipient.age < 30) {
    if (interests.includes('fashion')) trends.push('Sustainable fashion')
    if (interests.includes('tech')) trends.push('AI gadgets, Smart home devices')
    if (interests.includes('fitness')) trends.push('Home workout equipment, Athleisure')
  }

  if (recipient.age && recipient.age >= 30 && recipient.age < 50) {
    if (interests.includes('home')) trends.push('Home organization, Premium kitchen tools')
    if (interests.includes('wellness')) trends.push('Wellness tech, Self-care products')
    if (interests.includes('parenting')) trends.push('Educational toys, Family experiences')
  }

  // Add general 2026 trends relevant to their interests
  const general2026Trends = [
    'Personalized AI tools',
    'Sustainable products',
    'Experience gifts over things',
    'Health & wellness tech',
    'Remote work accessories',
  ]

  trends.push(...general2026Trends.slice(0, 3))

  return trends
}

/**
 * Find relevant subreddits based on interests (for deeper product research)
 */
function findRelevantSubreddits(interests: string[], aesthetics: string[]): string[] {
  const subreddits: string[] = []

  const interestSubredditMap: Record<string, string[]> = {
    photography: ['r/photography', 'r/analog', 'r/photocritique'],
    fitness: ['r/fitness', 'r/bodyweightfitness', 'r/running'],
    cooking: ['r/cooking', 'r/recipes', 'r/foodporn'],
    gaming: ['r/gaming', 'r/pcgaming', 'r/boardgames'],
    reading: ['r/books', 'r/suggestmeabook', 'r/fantasy'],
    tech: ['r/gadgets', 'r/technology', 'r/buyitforlife'],
    fashion: ['r/malefashionadvice', 'r/femalefashionadvice', 'r/streetwear'],
    music: ['r/music', 'r/vinyl', 'r/headphones'],
    art: ['r/art', 'r/crafts', 'r/diy'],
    travel: ['r/travel', 'r/solotravel', 'r/backpacking'],
  }

  for (const interest of interests) {
    if (interestSubredditMap[interest]) {
      subreddits.push(...interestSubredditMap[interest])
    }
  }

  // Add general gift subreddits
  subreddits.push('r/GiftIdeas', 'r/BuyItForLife')

  return [...new Set(subreddits)].slice(0, 10) // Unique, max 10
}

/**
 * Deep signal extraction - what do they aspire to? What do they already own?
 */
function extractDeepSignals(
  social: SocialProfile,
  interests: string[]
): EnrichedProfile['deepSignals'] {
  const signals: EnrichedProfile['deepSignals'] = {
    aspirational: [],
    current_investments: [],
  }

  // Pinterest is aspirational (what they want)
  if (social.pinterest) {
    const aspirationalKeywords: string[] = []
    for (const board of social.pinterest.boards) {
      for (const pin of board.pins.slice(0, 5)) {
        const text = `${pin.title} ${pin.description}`.toLowerCase()
        // Extract brand names and product types
        const brands = extractBrandNames(text)
        aspirationalKeywords.push(...brands)
      }
    }
    signals.aspirational = [...new Set(aspirationalKeywords)].slice(0, 10)
  }

  // Instagram shows what they currently have/do
  if (social.instagram) {
    const currentInvestments: string[] = []
    for (const caption of social.instagram.captions.slice(0, 20)) {
      const brands = extractBrandNames(caption)
      currentInvestments.push(...brands)
    }
    signals.current_investments = [...new Set(currentInvestments)].slice(0, 10)
  }

  // Determine aesthetic style
  const allText = [
    ...(social.instagram?.captions || []),
    ...(social.tiktok?.captions || []),
  ]
    .join(' ')
    .toLowerCase()

  if (allText.includes('minimal') || allText.includes('clean')) {
    signals.aesthetic_style = 'minimalist'
  } else if (allText.includes('vintage') || allText.includes('retro')) {
    signals.aesthetic_style = 'vintage'
  } else if (allText.includes('cozy') || allText.includes('cottage')) {
    signals.aesthetic_style = 'cozy/cottagecore'
  }

  return signals
}

/**
 * Calculate confidence score based on data richness
 */
function calculateConfidenceScore(social: SocialProfile, interests: string[]): number {
  let score = 0

  // Data richness
  if (social.instagram) {
    score += Math.min(Object.keys(social.instagram.hashtags).length * 2, 30)
    score += Math.min(social.instagram.captions.length, 20)
  }

  if (social.tiktok) {
    score += Math.min(Object.keys(social.tiktok.hashtags).length * 2, 20)
    score += Math.min(social.tiktok.music.length, 15)
  }

  if (social.pinterest) {
    score += Math.min(social.pinterest.boards.length * 3, 25)
  }

  // Interest clarity
  score += Math.min(interests.length * 3, 20)

  return Math.min(score, 100)
}

// Helper functions

function mapHashtagToInterest(hashtag: string): string | null {
  const mapping: Record<string, string> = {
    photography: 'photography',
    photo: 'photography',
    fitness: 'fitness',
    gym: 'fitness',
    workout: 'fitness',
    food: 'cooking',
    cooking: 'cooking',
    recipe: 'cooking',
    travel: 'travel',
    wanderlust: 'travel',
    art: 'art',
    design: 'design',
    fashion: 'fashion',
    style: 'fashion',
    book: 'reading',
    reading: 'reading',
    gaming: 'gaming',
    gamer: 'gaming',
    music: 'music',
    tech: 'tech',
    technology: 'tech',
  }

  for (const [key, value] of Object.entries(mapping)) {
    if (hashtag.includes(key)) return value
  }

  return null
}

function mapBoardNameToInterest(boardName: string): string | null {
  const name = boardName.toLowerCase()
  if (name.includes('home') || name.includes('decor')) return 'home_decor'
  if (name.includes('fashion') || name.includes('style')) return 'fashion'
  if (name.includes('recipe') || name.includes('food')) return 'cooking'
  if (name.includes('travel')) return 'travel'
  if (name.includes('art') || name.includes('design')) return 'art'
  return null
}

function extractInterestsFromText(text: string, interests: Set<string>): void {
  const keywords = {
    photography: ['camera', 'photo', 'photography', 'lens'],
    fitness: ['gym', 'workout', 'fitness', 'exercise', 'training'],
    cooking: ['recipe', 'cooking', 'food', 'chef', 'kitchen'],
    gaming: ['game', 'gaming', 'console', 'pc'],
    reading: ['book', 'reading', 'novel', 'author'],
    music: ['music', 'concert', 'song', 'artist', 'band'],
    travel: ['travel', 'trip', 'vacation', 'explore'],
    art: ['art', 'painting', 'drawing', 'creative'],
    tech: ['tech', 'gadget', 'app', 'software'],
  }

  for (const [interest, words] of Object.entries(keywords)) {
    if (words.some((word) => text.includes(word))) {
      interests.add(interest)
    }
  }
}

function inferMusicGenre(songName: string): string | null {
  // Simplified - would need music API in production
  const name = songName.toLowerCase()
  if (name.includes('hip hop') || name.includes('rap')) return 'hip_hop'
  if (name.includes('rock') || name.includes('metal')) return 'rock'
  if (name.includes('pop')) return 'pop'
  if (name.includes('country')) return 'country'
  if (name.includes('jazz')) return 'jazz'
  return null
}

function extractBrandNames(text: string): string[] {
  // Simplified brand extraction - would use NER in production
  const commonBrands = [
    'Nike',
    'Adidas',
    'Apple',
    'Sony',
    'Canon',
    'Nikon',
    'Lululemon',
    'Patagonia',
    'Nintendo',
    'PlayStation',
    'IKEA',
    'West Elm',
  ]

  const found: string[] = []
  const lower = text.toLowerCase()

  for (const brand of commonBrands) {
    if (lower.includes(brand.toLowerCase())) {
      found.push(brand)
    }
  }

  return found
}
