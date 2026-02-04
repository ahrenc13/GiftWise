/**
 * Additional Platform Scrapers
 * YouTube, Goodreads, Last.fm - Public data only
 */

interface YouTubeData {
  channels: string[]
  playlists: { name: string; videos: string[] }[]
  recentComments: { video: string; comment: string }[]
  interests: string[]
}

interface GoodreadsData {
  currentlyReading: { title: string; author: string; rating?: number }[]
  read: { title: string; author: string; rating: number }[]
  toRead: { title: string; author: string }[]
  genres: string[]
  shelves: string[]
}

interface LastFmData {
  topArtists: { name: string; playcount: number }[]
  topTracks: { name: string; artist: string; playcount: number }[]
  topAlbums: { name: string; artist: string; playcount: number }[]
  recentTracks: { name: string; artist: string }[]
  genres: string[]
}

/**
 * Scrape YouTube channel data via public API
 * Requires YOUTUBE_API_KEY environment variable
 */
export async function scrapeYouTube(username: string): Promise<YouTubeData> {
  const apiKey = process.env.YOUTUBE_API_KEY
  
  if (!apiKey) {
    console.log('[v0] YouTube API key not set, skipping YouTube scraping')
    return { channels: [], playlists: [], recentComments: [], interests: [] }
  }

  try {
    // Search for user's channel
    const searchUrl = `https://www.googleapis.com/youtube/v3/search?part=snippet&type=channel&q=${encodeURIComponent(username)}&key=${apiKey}&maxResults=1`
    const searchRes = await fetch(searchUrl)
    const searchData = await searchRes.json()

    if (!searchData.items || searchData.items.length === 0) {
      return { channels: [], playlists: [], recentComments: [], interests: [] }
    }

    const channelId = searchData.items[0].id.channelId

    // Get channel subscriptions (if public)
    const subsUrl = `https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&channelId=${channelId}&key=${apiKey}&maxResults=50`
    const subsRes = await fetch(subsUrl)
    const subsData = await subsRes.json()

    const channels = subsData.items?.map((item: any) => item.snippet.title) || []

    // Get public playlists
    const playlistsUrl = `https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId=${channelId}&key=${apiKey}&maxResults=10`
    const playlistsRes = await fetch(playlistsUrl)
    const playlistsData = await playlistsRes.json()

    const playlists = playlistsData.items?.map((item: any) => ({
      name: item.snippet.title,
      videos: []
    })) || []

    // Extract interest categories from subscriptions
    const interests = extractYouTubeInterests(channels)

    return {
      channels,
      playlists,
      recentComments: [], // Comments API requires OAuth
      interests,
    }
  } catch (error) {
    console.error('[v0] YouTube scraping error:', error)
    return { channels: [], playlists: [], recentComments: [], interests: [] }
  }
}

/**
 * Scrape Goodreads profile (public shelves only)
 * Uses Goodreads API or web scraping
 */
export async function scrapeGoodreads(username: string): Promise<GoodreadsData> {
  try {
    // Note: Goodreads retired their public API in 2020
    // We'll need to scrape the public profile page
    const profileUrl = `https://www.goodreads.com/user/show/${username}`
    
    // In production, you'd use a proper HTML parser
    // For now, returning structure for when scraping is implemented
    console.log('[v0] Goodreads scraping not fully implemented - would scrape:', profileUrl)
    
    return {
      currentlyReading: [],
      read: [],
      toRead: [],
      genres: [],
      shelves: []
    }
    
    // Future implementation would:
    // 1. Fetch profile page
    // 2. Parse HTML for public shelves
    // 3. Extract book titles, authors, ratings
    // 4. Identify favorite genres
  } catch (error) {
    console.error('[v0] Goodreads scraping error:', error)
    return {
      currentlyReading: [],
      read: [],
      toRead: [],
      genres: [],
      shelves: []
    }
  }
}

/**
 * Scrape Last.fm listening history (public data)
 * Last.fm API is free and public-friendly
 */
export async function scrapeLastFm(username: string): Promise<LastFmData> {
  const apiKey = process.env.LASTFM_API_KEY
  
  if (!apiKey) {
    console.log('[v0] Last.fm API key not set, skipping Last.fm scraping')
    return { topArtists: [], topTracks: [], topAlbums: [], recentTracks: [], genres: [] }
  }

  try {
    const baseUrl = 'http://ws.audioscrobbler.com/2.0/'
    
    // Get top artists
    const artistsUrl = `${baseUrl}?method=user.gettopartists&user=${username}&api_key=${apiKey}&format=json&limit=20&period=overall`
    const artistsRes = await fetch(artistsUrl)
    const artistsData = await artistsRes.json()
    
    const topArtists = artistsData.topartists?.artist?.map((a: any) => ({
      name: a.name,
      playcount: parseInt(a.playcount)
    })) || []

    // Get top tracks
    const tracksUrl = `${baseUrl}?method=user.gettoptracks&user=${username}&api_key=${apiKey}&format=json&limit=20&period=overall`
    const tracksRes = await fetch(tracksUrl)
    const tracksData = await tracksRes.json()
    
    const topTracks = tracksData.toptracks?.track?.map((t: any) => ({
      name: t.name,
      artist: t.artist.name,
      playcount: parseInt(t.playcount)
    })) || []

    // Get top albums
    const albumsUrl = `${baseUrl}?method=user.gettopalbums&user=${username}&api_key=${apiKey}&format=json&limit=20&period=overall`
    const albumsRes = await fetch(albumsUrl)
    const albumsData = await albumsRes.json()
    
    const topAlbums = albumsData.topalbums?.album?.map((a: any) => ({
      name: a.name,
      artist: a.artist.name,
      playcount: parseInt(a.playcount)
    })) || []

    // Get recent tracks
    const recentUrl = `${baseUrl}?method=user.getrecenttracks&user=${username}&api_key=${apiKey}&format=json&limit=10`
    const recentRes = await fetch(recentUrl)
    const recentData = await recentRes.json()
    
    const recentTracks = recentData.recenttracks?.track?.map((t: any) => ({
      name: t.name,
      artist: t.artist['#text'] || t.artist.name
    })) || []

    // Extract genre signals from artists
    const genres = extractMusicGenres(topArtists)

    return {
      topArtists,
      topTracks,
      topAlbums,
      recentTracks,
      genres
    }
  } catch (error) {
    console.error('[v0] Last.fm scraping error:', error)
    return { topArtists: [], topTracks: [], topAlbums: [], recentTracks: [], genres: [] }
  }
}

/**
 * Extract interest categories from YouTube channel subscriptions
 */
function extractYouTubeInterests(channels: string[]): string[] {
  const interests: Set<string> = new Set()
  
  const interestMap: { [key: string]: string } = {
    'tech': 'Technology',
    'gaming': 'Gaming',
    'cooking': 'Cooking',
    'fitness': 'Fitness',
    'travel': 'Travel',
    'beauty': 'Beauty',
    'fashion': 'Fashion',
    'music': 'Music',
    'comedy': 'Comedy',
    'education': 'Education',
    'science': 'Science',
    'diy': 'DIY & Crafts',
    'vlog': 'Lifestyle',
    'review': 'Product Reviews',
    'photography': 'Photography',
    'art': 'Art',
    'sports': 'Sports',
    'finance': 'Finance',
    'business': 'Business',
  }

  channels.forEach(channel => {
    const lower = channel.toLowerCase()
    Object.entries(interestMap).forEach(([keyword, interest]) => {
      if (lower.includes(keyword)) {
        interests.add(interest)
      }
    })
  })

  return Array.from(interests)
}

/**
 * Extract genre signals from music listening data
 */
function extractMusicGenres(artists: { name: string }[]): string[] {
  // This is simplified - in production you'd use Last.fm's artist.getInfo
  // to get actual genre tags for each artist
  const genres: Set<string> = new Set()
  
  // For now, return placeholder that indicates music taste analysis
  if (artists.length > 0) {
    genres.add('Music Enthusiast')
  }
  
  return Array.from(genres)
}

export type { YouTubeData, GoodreadsData, LastFmData }
