import { createClient } from '@/lib/supabase/server'
import { notFound, redirect } from 'next/navigation'
import { trackShareEvent } from '@/lib/viral-system'
import { Gift, Heart, ExternalLink, Sparkles } from 'lucide-react'
import Image from 'next/image'
import Link from 'link'

interface SharePageProps {
  params: Promise<{ shareId: string }>
}

export default async function SharePage({ params }: SharePageProps) {
  const { shareId } = await params
  const supabase = await createClient()

  // Get share data
  const { data: share } = await supabase
    .from('shared_recommendations')
    .select(`
      *,
      session:recommendation_sessions(
        selected_gifts,
        bespoke_packages
      ),
      profile:profiles(full_name)
    `)
    .eq('share_id', shareId)
    .eq('is_public', true)
    .single()

  if (!share) {
    notFound()
  }

  // Track view
  await trackShareEvent(shareId, 'view')

  const gifts = share.session?.selected_gifts || []
  const packages = share.session?.bespoke_packages || []
  const sharerName = share.profile?.full_name || 'Someone'

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/5">
      <div className="max-w-6xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium mb-4">
            <Gift className="w-4 h-4" />
            Shared Gift Ideas
          </div>
          <h1 className="text-4xl md:text-5xl font-serif font-bold mb-4">
            {sharerName} wants your opinion!
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Help pick the perfect gift. Which one would you choose?
          </p>
        </div>

        {/* Gifts Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
          {gifts.map((gift: any, index: number) => (
            <div
              key={index}
              className="group border-2 border-border rounded-2xl p-6 bg-card hover:shadow-xl hover:border-primary/30 transition-all"
            >
              {gift.imageUrl && (
                <div className="aspect-square rounded-xl overflow-hidden mb-4 bg-muted relative">
                  <Image
                    src={gift.imageUrl}
                    alt={gift.title}
                    fill
                    className="object-cover group-hover:scale-105 transition-transform"
                  />
                </div>
              )}

              <h3 className="font-serif font-bold text-xl mb-2 line-clamp-2">{gift.title}</h3>

              {gift.price && (
                <div className="text-2xl font-serif font-bold text-primary mb-3">{gift.price}</div>
              )}

              {gift.reasoning && (
                <p className="text-sm text-muted-foreground mb-4 line-clamp-3">{gift.reasoning}</p>
              )}

              {gift.url && (
                <a
                  href={gift.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
                  onClick={() => trackShareEvent(shareId, 'click', { productIndex: index })}
                >
                  View Product
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="bg-gradient-to-br from-primary/10 to-accent/10 border-2 border-primary/20 rounded-2xl p-8 md:p-12 text-center">
          <Sparkles className="w-12 h-12 text-primary mx-auto mb-4" />
          <h2 className="text-3xl font-serif font-bold mb-4">Want personalized gift ideas too?</h2>
          <p className="text-lg text-muted-foreground mb-6 max-w-2xl mx-auto">
            Get AI-powered recommendations based on social media insights. Perfect for finding
            thoughtful gifts for anyone.
          </p>
          <Link
            href={`/auth/sign-up?ref=${shareId}`}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-8 py-3 rounded-full font-semibold hover:bg-primary/90 transition-colors"
            onClick={() => trackShareEvent(shareId, 'conversion')}
          >
            Try GiftWise Free
          </Link>
        </div>
      </div>
    </div>
  )
}
