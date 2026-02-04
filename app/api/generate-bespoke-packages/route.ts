'use server'

import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { sessionId } = await request.json()
    const supabase = await createClient()

    // Get session and profile data
    const { data: session } = await supabase
      .from('recommendation_sessions')
      .select('*, social_profiles(*)')
      .eq('id', sessionId)
      .single()

    if (!session) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 })
    }

    // Get the recommended products for context
    const { data: products } = await supabase
      .from('gift_products')
      .select('*')
      .eq('session_id', sessionId)
      .order('rank', { ascending: true })
      .limit(10)

    // Call Claude to generate bespoke packages
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY!,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 4000,
        messages: [
          {
            role: 'user',
            content: `You are a thoughtful gift curator creating bespoke experience packages. Based on the recipient's profile and recommended gifts, create 3 unique package ideas that combine experiences with physical gifts.

RECIPIENT PROFILE:
${JSON.stringify(session.social_profiles, null, 2)}

RECOMMENDED GIFTS (for context):
${JSON.stringify(products?.slice(0, 10), null, 2)}

Create 3 bespoke packages. Each package should:
- Combine an experience (dinner, concert, class, trip, activity) with 2-3 complementary physical gifts
- Be personalized to their location, interests, and personality
- Have a cohesive theme that tells a story
- Include realistic pricing (experience + gifts)
- Feel special and thoughtful, not generic

Format each package as JSON with this structure:
{
  "name": "Creative, memorable package name",
  "theme": "The story/theme connecting everything",
  "experience": {
    "title": "Specific experience name",
    "description": "What they'll do and why it's perfect for them",
    "estimatedPrice": 150
  },
  "gifts": [
    {
      "title": "Gift name",
      "description": "Why it complements the experience",
      "estimatedPrice": 45,
      "buyUrl": "amazon.com search url or specific product if you know it"
    }
  ],
  "totalPrice": 240,
  "whyPerfect": "Personal explanation of why this package suits them"
}

Return ONLY a JSON array of 3 packages, no other text.`,
          },
        ],
      }),
    })

    const data = await response.json()
    const packagesText = data.content[0].text

    // Parse the JSON response
    let packages
    try {
      packages = JSON.parse(packagesText)
    } catch (e) {
      // If Claude wrapped it in markdown, extract the JSON
      const jsonMatch = packagesText.match(/\[[\s\S]*\]/)
      if (jsonMatch) {
        packages = JSON.parse(jsonMatch[0])
      } else {
        throw new Error('Failed to parse packages')
      }
    }

    // Store packages in database
    const packagesData = packages.map((pkg: any) => ({
      session_id: sessionId,
      user_id: session.user_id,
      name: pkg.name,
      theme: pkg.theme,
      experience_title: pkg.experience.title,
      experience_description: pkg.experience.description,
      experience_price: pkg.experience.estimatedPrice,
      gifts: pkg.gifts,
      total_price: pkg.totalPrice,
      why_perfect: pkg.whyPerfect,
    }))

    const { data: savedPackages, error } = await supabase
      .from('bespoke_packages')
      .insert(packagesData)
      .select()

    if (error) throw error

    return NextResponse.json({ packages: savedPackages })
  } catch (error: any) {
    console.error('[v0] Error generating bespoke packages:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to generate packages' },
      { status: 500 }
    )
  }
}
