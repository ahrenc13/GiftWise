import { createClient } from '@/lib/supabase/server'
import { NextRequest, NextResponse } from 'next/server'
import Anthropic from '@anthropic-ai/sdk'

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

    // Build profile context from connected platforms
    const profileContext = buildProfileContext(session.social_profiles, connections || [])
    
    console.log('[v0] Profile context built, calling Claude for catalog generation')

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

function buildProfileContext(socialProfile: any, connections: any[]): string {
  const connectedPlatforms = connections.map(c => c.platform).join(', ')
  
  let context = `RECIPIENT: ${socialProfile.recipient_name}\n`
  
  if (socialProfile.raw_data?.relationship) {
    context += `RELATIONSHIP: ${socialProfile.raw_data.relationship}\n`
  }
  
  if (socialProfile.location) {
    context += `LOCATION: ${socialProfile.location}\n`
  }
  
  if (socialProfile.raw_data?.budget_min || socialProfile.raw_data?.budget_max) {
    context += `BUDGET: $${socialProfile.raw_data.budget_min || 0} - $${socialProfile.raw_data.budget_max || 500}\n`
  }
  
  context += `CONNECTED PLATFORMS: ${connectedPlatforms}\n`
  
  if (connections.length > 0) {
    context += '\nSOCIAL INSIGHTS:\n'
    connections.forEach(conn => {
      context += `- ${conn.platform}: @${conn.platform_username}\n`
    })
    context += '\nNote: Use the connected usernames to infer interests, style preferences, music taste, and personality traits.\n'
  }
  
  return context
}
