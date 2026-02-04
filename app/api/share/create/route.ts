import { createClient } from '@/lib/supabase/server'
import { NextRequest, NextResponse } from 'next/server'
import { createShareableLink } from '@/lib/viral-system'

export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient()

    // Check authentication
    const {
      data: { user },
    } = await supabase.auth.getUser()

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { sessionId } = await request.json()

    if (!sessionId) {
      return NextResponse.json({ error: 'Session ID required' }, { status: 400 })
    }

    // Verify session belongs to user
    const { data: session } = await supabase
      .from('recommendation_sessions')
      .select('id')
      .eq('id', sessionId)
      .eq('user_id', user.id)
      .single()

    if (!session) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 })
    }

    // Create shareable link
    const shareData = await createShareableLink(sessionId, user.id)

    return NextResponse.json(shareData)
  } catch (error) {
    console.error('[v0] Error creating share:', error)
    return NextResponse.json({ error: 'Failed to create share' }, { status: 500 })
  }
}
