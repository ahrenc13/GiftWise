import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import { Gift, Heart, ExternalLink, Sparkles, Package } from 'lucide-react'
import Link from 'next/link'
import Image from 'next/image'
import { BespokePackages } from '@/components/bespoke-packages'

export default async function RecommendationsPage({ 
  params 
}: { 
  params: Promise<{ sessionId: string }> 
}) {
  const { sessionId } = await params
  const supabase = await createClient()
  
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  
  if (authError || !user) {
    redirect('/auth/login')
  }

  // Fetch session with social profile
  const { data: session } = await supabase
    .from('recommendation_sessions')
    .select(`
      *,
      social_profiles (*)
    `)
    .eq('id', sessionId)
    .eq('user_id', user.id)
    .single()

  if (!session) {
    redirect('/dashboard')
  }

  const isProcessing = session.status === 'processing'
  const selectedGifts = session.selected_gifts || []
  const bespokePackages = session.bespoke_packages || []
  const recipientName = session.social_profiles?.recipient_name || 'them'

  if (isProcessing) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center max-w-md px-4">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6 animate-pulse">
            <Sparkles className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-serif font-bold mb-3">
            Finding the Perfect Gifts...
          </h1>
          <p className="text-lg text-muted-foreground mb-8">
            Our AI is analyzing profiles and curating personalized recommendations for {recipientName}
          </p>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>✓ Analyzing social profiles</p>
            <p>✓ Searching product catalogs</p>
            <p className="animate-pulse">⋯ Selecting perfect matches</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Gift className="w-6 h-6 text-primary" />
            <span className="font-serif text-xl font-semibold">GiftWise</span>
          </Link>
          <Link 
            href="/dashboard"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Back to Dashboard
          </Link>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header Section */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 bg-secondary/10 text-secondary px-4 py-2 rounded-full text-sm font-medium mb-4">
            <Heart className="w-4 h-4" />
            Personalized for {recipientName}
          </div>
          <h1 className="text-5xl font-serif font-bold mb-4 text-balance">
            Your Curated Gift Recommendations
          </h1>
          <p className="text-lg text-muted-foreground text-balance leading-relaxed">
            We analyzed their profile and found {selectedGifts.length} thoughtful gifts that match their unique style and interests.
          </p>
        </div>

        {/* AI Reasoning */}
        {session.ai_reasoning && (
          <div className="mb-12 max-w-4xl mx-auto">
            <div className="border border-border rounded-2xl p-6 bg-gradient-to-br from-primary/5 to-secondary/5">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                  <Sparkles className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <h3 className="font-serif font-semibold mb-2">Why These Gifts?</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {session.ai_reasoning}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Gift Grid */}
        <section className="mb-20">
          <h2 className="text-3xl font-serif font-bold mb-8">Recommended Gifts</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {selectedGifts.map((gift: any, index: number) => (
              <div 
                key={index}
                className="group border border-border rounded-2xl overflow-hidden bg-card hover:shadow-xl transition-all"
              >
                {/* Product Image Placeholder */}
                <div className="aspect-square bg-gradient-to-br from-muted to-muted/50 relative overflow-hidden">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Gift className="w-16 h-16 text-muted-foreground/30" />
                  </div>
                  {gift.price && (
                    <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full">
                      <span className="font-semibold text-sm">${gift.price}</span>
                    </div>
                  )}
                </div>
                
                <div className="p-6">
                  <div className="mb-3">
                    {gift.category && (
                      <span className="text-xs text-primary font-medium uppercase tracking-wide">
                        {gift.category}
                      </span>
                    )}
                  </div>
                  <h3 className="font-serif font-semibold text-lg mb-2 group-hover:text-primary transition-colors">
                    {gift.title}
                  </h3>
                  {gift.brand && (
                    <p className="text-sm text-muted-foreground mb-3">{gift.brand}</p>
                  )}
                  <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                    {gift.description}
                  </p>
                  {gift.reasoning && (
                    <div className="bg-accent/5 rounded-lg p-3 mb-4">
                      <p className="text-xs text-muted-foreground italic">
                        "{gift.reasoning}"
                      </p>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      {gift.retailer || 'Available Online'}
                    </span>
                    <button className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
                      View Product
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Bespoke Packages Section */}
        <BespokePackages sessionId={sessionId} />

        {/* CTA Section */}
        <section className="text-center py-16 px-4 bg-gradient-to-br from-primary/10 via-accent/5 to-secondary/10 rounded-3xl">
          <h2 className="text-3xl font-serif font-bold mb-4">
            Love These Recommendations?
          </h2>
          <p className="text-lg text-muted-foreground mb-8 text-balance max-w-2xl mx-auto">
            Find more perfect gifts for the special people in your life
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-full bg-primary px-8 py-4 font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Sparkles className="w-5 h-5 mr-2" />
            Create Another Recommendation
          </Link>
        </section>
      </main>
    </div>
  )
}
