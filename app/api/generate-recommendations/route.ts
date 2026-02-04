import { createClient } from '@/lib/supabase/server'
import { NextRequest, NextResponse } from 'next/server'
import Anthropic from '@anthropic-ai/sdk'
import { enrichSocialProfile } from '@/lib/enrichment-engine'

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
})

export async function POST(request: NextRequest) {
  try {
    const { sessionId } = await request.json()
    console.log('[v0] Starting recommendation generation for session:', sessionId)

    const supabase = await createClient()
    
    // Get session and related data
    const { data: session } = await supabase
      .from('recommendation_sessions')
      .select(`
        *,
        social_profiles (*)
      `)
      .eq('id', sessionId)
      .single()

    if (!session) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 })
    }

    // Get connected social platforms
    const { data: connections } = await supabase
      .from('oauth_connections')
      .select('*')
      .eq('user_id', session.user_id)
      .eq('is_active', true)

    // Get scraped social data
    const { data: scrapedProfiles } = await supabase
      .from('social_profiles')
      .select('*')
      .eq('user_id', session.user_id)

    // Build enriched profile with intelligence layer
    const profileContext = await buildEnrichedProfileContext(
      session,
      connections || [],
      scrapedProfiles || []
    )
    
    console.log('[v0] Enriched profile context built, calling Claude for catalog generation')

    // STEP 1: Generate catalog of 30 gift products
    const catalogPrompt = `You are an expert gift curator. Based on the profile below, generate a catalog of 30 real, buyable gift products that would be perfect for this person.

PROFILE:
${profileContext}

REQUIREMENTS:
- Each gift must be a REAL product that exists and can be purchased
- Include the exact product name, brand, estimated price, and a brief description
- Vary the price range (some budget-friendly, some mid-range, some premium)
- Include diverse categories: fashion, tech, experiences, books, home goods, food/drink, hobby items, etc.
- Be specific - don't say "a nice watch", say "Timex Weekender 40mm Silver Watch"
- Consider their interests, style, and personality
- Avoid generic gifts - make them feel personal and thoughtful

Format your response as a JSON array with this structure:
[
  {
    "title": "Product Name",
    "brand": "Brand Name",
    "price": 49.99,
    "description": "Brief description of the product",
    "category": "category name",
    "retailer": "Amazon/Etsy/etc",
    "reasoning": "Why this fits their profile"
  }
]`

    const catalogResponse = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4000,
      messages: [{
        role: 'user',
        content: catalogPrompt
      }]
    })

    const catalogText = catalogResponse.content[0].type === 'text' 
      ? catalogResponse.content[0].text 
      : ''
    
    // Extract JSON from response
    const catalogJsonMatch = catalogText.match(/\[[\s\S]*\]/)
    if (!catalogJsonMatch) {
      throw new Error('Failed to parse catalog JSON')
    }
    
    const catalog = JSON.parse(catalogJsonMatch[0])
    console.log('[v0] Generated catalog of', catalog.length, 'products')

    // STEP 2: Have Claude select the best 8-10 gifts
    const selectionPrompt = `You are an expert gift curator. From this catalog of 30 products, select the 8-10 BEST gifts for this person.

PROFILE:
${profileContext}

CATALOG:
${JSON.stringify(catalog, null, 2)}

REQUIREMENTS:
- Choose 8-10 gifts that are most thoughtful and personalized
- Vary price points and categories
- Prioritize uniqueness and personal relevance
- Avoid generic or obvious choices unless they're perfect
- Consider the emotional impact and thoughtfulness of each gift

Respond with:
1. An array of the selected product titles
2. A brief explanation of your reasoning for each

Format as JSON:
{
  "selected": ["Product Title 1", "Product Title 2", ...],
  "reasoning": "Your overall reasoning for these selections"
}`

    const selectionResponse = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2000,
      messages: [{
        role: 'user',
        content: selectionPrompt
      }]
    })

    const selectionText = selectionResponse.content[0].type === 'text'
      ? selectionResponse.content[0].text
      : ''
    
    const selectionJsonMatch = selectionText.match(/\{[\s\S]*\}/)
    if (!selectionJsonMatch) {
      throw new Error('Failed to parse selection JSON')
    }
    
    const selection = JSON.parse(selectionJsonMatch[0])
    
    // Filter catalog to selected gifts
    const selectedGifts = catalog.filter((product: any) => 
      selection.selected.includes(product.title)
    )

    console.log('[v0] Selected', selectedGifts.length, 'final gifts')

    // STEP 3: Generate bespoke experience packages
    const packagesPrompt = `Create 2-3 unique "bespoke experience packages" - curated combinations of gifts and experiences that tell a story and create a memorable moment.

PROFILE:
${profileContext}

SELECTED GIFTS:
${JSON.stringify(selectedGifts, null, 2)}

REQUIREMENTS:
- Each package should combine 2-4 items/experiences into a cohesive theme
- Include both physical gifts and experiential components
- Consider their location for local experiences
- Make it feel like a thoughtfully planned day or special moment
- Be creative and personal - not generic

Example: "Cozy Coffee Date Package: Artisan coffee beans + ceramic mug + gift card to local cafe + handwritten note template"

Format as JSON array:
[
  {
    "title": "Package Name",
    "description": "Detailed description of the experience",
    "components": ["Item 1", "Item 2", "Experience 1"],
    "totalPrice": 150,
    "why": "Why this package is perfect for them"
  }
]`

    const packagesResponse = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2000,
      messages: [{
        role: 'user',
        content: packagesPrompt
      }]
    })

    const packagesText = packagesResponse.content[0].type === 'text'
      ? packagesResponse.content[0].text
      : ''
    
    const packagesJsonMatch = packagesText.match(/\[[\s\S]*\]/)
    const bespokePackages = packagesJsonMatch ? JSON.parse(packagesJsonMatch[0]) : []

    console.log('[v0] Generated', bespokePackages.length, 'bespoke packages')

    // Update session with results
    const { error: updateError } = await supabase
      .from('recommendation_sessions')
      .update({
        status: 'completed',
        catalog: catalog,
        selected_gifts: selectedGifts,
        bespoke_packages: bespokePackages,
        ai_reasoning: selection.reasoning,
        completed_at: new Date().toISOString()
      })
      .eq('id', sessionId)

    if (updateError) {
      console.error('[v0] Error updating session:', updateError)
      throw updateError
    }

    console.log('[v0] Recommendation generation complete')

    return NextResponse.json({
      success: true,
      selectedGifts,
      bespokePackages
    })

  } catch (error) {
    console.error('[v0] Error generating recommendations:', error)
    return NextResponse.json(
      { error: 'Failed to generate recommendations' },
      { status: 500 }
    )
  }
}

/**
 * Build enriched profile context using scraped data + enrichment intelligence
 */
async function buildEnrichedProfileContext(
  session: any,
  connections: any[],
  scrapedProfiles: any[]
): Promise<string> {
  // Organize scraped data by platform
  const socialData: any = {}
  for (const profile of scrapedProfiles) {
    if (profile.profile_data) {
      if (profile.platform === 'instagram') {
        socialData.instagram = {
          hashtags: profile.profile_data.hashtags || {},
          captions: profile.profile_data.captions || [],
          mentions: profile.profile_data.mentions || [],
        }
      } else if (profile.platform === 'tiktok') {
        socialData.tiktok = {
          hashtags: profile.profile_data.hashtags || {},
          music: profile.profile_data.music || [],
          captions: profile.profile_data.captions || [],
        }
      } else if (profile.platform === 'pinterest') {
        socialData.pinterest = {
          boards: profile.profile_data.boards || [],
        }
      }
    }
  }

  // Run enrichment engine
  const enriched = await enrichSocialProfile(socialData, {
    name: session.recipient_name || 'Recipient',
    age: session.recipient_age,
    location: session.recipient_location,
    relationship: session.relationship || 'friend',
    gender: session.recipient_gender,
  })

  // Build detailed context for Claude
  let context = `RECIPIENT PROFILE:\n`
  context += `Name: ${session.recipient_name || 'Recipient'}\n`
  
  if (session.recipient_age) context += `Age: ${session.recipient_age}\n`
  if (session.recipient_location) context += `Location: ${session.recipient_location}\n`
  if (session.relationship) context += `Relationship: ${session.relationship}\n`
  
  context += `\nCORE INTERESTS (${enriched.coreInterests.length}):\n`
  enriched.coreInterests.forEach((interest, i) => {
    context += `${i + 1}. ${interest}\n`
  })

  if (enriched.aestheticPreferences.length > 0) {
    context += `\nAESTHETIC PREFERENCES:\n`
    enriched.aestheticPreferences.forEach(aesthetic => {
      context += `- ${aesthetic}\n`
    })
  }

  if (enriched.lifestyleSignals.length > 0) {
    context += `\nLIFESTYLE SIGNALS:\n`
    enriched.lifestyleSignals.forEach(signal => {
      context += `- ${signal.replace(/_/g, ' ')}\n`
    })
  }

  if (enriched.deepSignals.current_investments && enriched.deepSignals.current_investments.length > 0) {
    context += `\nCURRENT BRANDS/INVESTMENTS:\n`
    enriched.deepSignals.current_investments.forEach(brand => {
      context += `- ${brand}\n`
    })
    context += `(Avoid duplicating items they already own from these brands)\n`
  }

  if (enriched.deepSignals.aspirational && enriched.deepSignals.aspirational.length > 0) {
    context += `\nASPIRATIONAL INTERESTS (from Pinterest):\n`
    enriched.deepSignals.aspirational.forEach(item => {
      context += `- ${item}\n`
    })
  }

  if (enriched.demographicTrends.length > 0) {
    context += `\nRELEVANT TRENDS FOR THEIR DEMOGRAPHIC:\n`
    enriched.demographicTrends.slice(0, 10).forEach(trend => {
      context += `- ${trend}\n`
    })
  }

  if (enriched.trendingProducts && enriched.trendingProducts.length > 0) {
    context += `\nTRENDING PRODUCTS IN THEIR INTEREST AREAS (Real-time data):\n`
    enriched.trendingProducts.slice(0, 15).forEach(product => {
      context += `- ${product}\n`
    })
  }

  if (enriched.redditCommunities && enriched.redditCommunities.length > 0) {
    context += `\nRELEVANT REDDIT COMMUNITIES:\n`
    enriched.redditCommunities.forEach(community => {
      context += `- ${community} (check for popular recommendations)\n`
    })
  }

  if (enriched.categoryBestsellers && enriched.categoryBestsellers.length > 0) {
    context += `\nCATEGORY BESTSELLERS:\n`
    enriched.categoryBestsellers.slice(0, 10).forEach(bestseller => {
      context += `- ${bestseller}\n`
    })
  }

  context += `\nDATA CONFIDENCE: ${enriched.confidence}%\n`
  
  const platformNames = connections.map(c => c.platform).join(', ')
  context += `CONNECTED PLATFORMS: ${platformNames}\n`

  return context
}
