'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Sparkles } from 'lucide-react'

export default function StartRecommendationButton({ 
  creditsRemaining 
}: { 
  creditsRemaining: number 
}) {
  const [isStarting, setIsStarting] = useState(false)
  const [recipientName, setRecipientName] = useState('')
  const [relationship, setRelationship] = useState('')
  const [budgetMin, setBudgetMin] = useState('')
  const [budgetMax, setBudgetMax] = useState('')
  const [showForm, setShowForm] = useState(false)
  const router = useRouter()

  const handleStart = async () => {
    if (!showForm) {
      setShowForm(true)
      return
    }

    if (!recipientName.trim()) {
      alert('Please enter the recipient\'s name')
      return
    }

    if (creditsRemaining <= 0) {
      alert('You have no credits remaining. Please upgrade your plan.')
      router.push('/pricing')
      return
    }

    setIsStarting(true)
    console.log('[v0] Starting recommendation session')

    try {
      const supabase = createClient()
      
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) throw new Error('Not authenticated')

      // Create social profile
      const { data: socialProfile, error: profileError } = await supabase
        .from('social_profiles')
        .insert({
          user_id: user.id,
          recipient_name: recipientName,
          raw_data: {
            relationship,
            budget_min: budgetMin ? parseFloat(budgetMin) : null,
            budget_max: budgetMax ? parseFloat(budgetMax) : null,
          }
        })
        .select()
        .single()

      if (profileError) throw profileError

      // Create recommendation session
      const { data: session, error: sessionError } = await supabase
        .from('recommendation_sessions')
        .insert({
          user_id: user.id,
          social_profile_id: socialProfile.id,
          status: 'processing'
        })
        .select()
        .single()

      if (sessionError) throw sessionError

      console.log('[v0] Session created, starting AI recommendation')
      
      // Trigger AI recommendation generation
      const response = await fetch('/api/generate-recommendations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: session.id })
      })

      if (!response.ok) throw new Error('Failed to generate recommendations')

      // Deduct credit
      const { error: creditError } = await supabase
        .from('profiles')
        .update({ credits_remaining: creditsRemaining - 1 })
        .eq('id', user.id)

      if (creditError) throw creditError

      router.push(`/recommendations/${session.id}`)
    } catch (error) {
      console.error('[v0] Error starting recommendation:', error)
      alert('Failed to start recommendation. Please try again.')
      setIsStarting(false)
    }
  }

  if (!showForm) {
    return (
      <button
        onClick={handleStart}
        className="inline-flex items-center justify-center rounded-full bg-primary px-8 py-4 font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
      >
        <Sparkles className="w-5 h-5 mr-2" />
        Start New Recommendation
      </button>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2">Recipient's Name *</label>
        <input
          type="text"
          value={recipientName}
          onChange={(e) => setRecipientName(e.target.value)}
          placeholder="e.g., Sarah"
          className="w-full px-4 py-3 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={isStarting}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Your Relationship</label>
        <input
          type="text"
          value={relationship}
          onChange={(e) => setRelationship(e.target.value)}
          placeholder="e.g., girlfriend, best friend, sister"
          className="w-full px-4 py-3 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={isStarting}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Min Budget ($)</label>
          <input
            type="number"
            value={budgetMin}
            onChange={(e) => setBudgetMin(e.target.value)}
            placeholder="50"
            className="w-full px-4 py-3 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={isStarting}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Max Budget ($)</label>
          <input
            type="number"
            value={budgetMax}
            onChange={(e) => setBudgetMax(e.target.value)}
            placeholder="200"
            className="w-full px-4 py-3 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={isStarting}
          />
        </div>
      </div>

      <button
        onClick={handleStart}
        disabled={isStarting}
        className="w-full inline-flex items-center justify-center rounded-full bg-primary px-8 py-4 font-semibold text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
      >
        {isStarting ? (
          'Generating Recommendations...'
        ) : (
          <>
            <Sparkles className="w-5 h-5 mr-2" />
            Generate Gift Ideas
          </>
        )}
      </button>
    </div>
  )
}
