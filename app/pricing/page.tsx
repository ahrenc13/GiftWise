import Link from 'next/link'
import { Gift, Heart, Sparkles } from 'lucide-react'
import { PRODUCTS } from '@/lib/products'
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function PricingPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/sign-up')
  }

  const { data: profile } = await supabase
    .from('profiles')
    .select('subscription_tier')
    .eq('id', user.id)
    .single()

  const currentTier = profile?.subscription_tier || 'free'

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

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full text-sm font-medium mb-4">
            <Sparkles className="w-4 h-4" />
            Upgrade Your Plan
          </div>
          <h1 className="text-5xl font-serif font-bold mb-6">
            Choose Your Plan
          </h1>
          <p className="text-lg text-muted-foreground text-balance">
            Unlock more recommendations and premium features
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {PRODUCTS.map((product) => {
            const isCurrentPlan = currentTier === product.tier
            
            return (
              <div
                key={product.id}
                className={`relative border rounded-2xl p-8 bg-card ${
                  product.tier === 'premium'
                    ? 'border-primary shadow-xl scale-105'
                    : 'border-border hover:shadow-lg'
                } transition-all`}
              >
                {product.tier === 'premium' && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground px-4 py-1 rounded-full text-sm font-medium">
                    Most Popular
                  </div>
                )}
                {isCurrentPlan && (
                  <div className="absolute -top-4 right-4 bg-secondary text-secondary-foreground px-4 py-1 rounded-full text-sm font-medium">
                    Current Plan
                  </div>
                )}
                
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-serif font-semibold mb-2">
                    {product.name}
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    {product.description}
                  </p>
                  <div className="flex items-end justify-center gap-1">
                    <span className="text-4xl font-serif font-bold">
                      ${product.priceInCents / 100}
                    </span>
                    <span className="text-muted-foreground mb-1">/month</span>
                  </div>
                </div>

                <ul className="space-y-3 mb-8">
                  {product.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <Heart className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>

                {isCurrentPlan ? (
                  <div className="w-full text-center rounded-full py-3 bg-muted text-muted-foreground font-semibold">
                    Current Plan
                  </div>
                ) : (
                  <Link
                    href={`/pricing/checkout?product=${product.id}`}
                    className={`block w-full text-center rounded-full py-3 font-semibold transition-colors ${
                      product.tier === 'premium'
                        ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                        : 'bg-muted text-foreground hover:bg-muted/80'
                    }`}
                  >
                    Upgrade to {product.name}
                  </Link>
                )}
              </div>
            )
          })}
        </div>

        {/* FAQ Section */}
        <div className="mt-24 max-w-3xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-center mb-12">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div className="border border-border rounded-xl p-6 bg-card">
              <h3 className="font-semibold mb-2">Can I cancel anytime?</h3>
              <p className="text-sm text-muted-foreground">
                Yes! You can cancel your subscription at any time. You'll retain access until the end of your billing period.
              </p>
            </div>
            <div className="border border-border rounded-xl p-6 bg-card">
              <h3 className="font-semibold mb-2">What happens to unused credits?</h3>
              <p className="text-sm text-muted-foreground">
                Credits reset monthly and don't roll over. Premium users get unlimited recommendations so there's never a worry about running out.
              </p>
            </div>
            <div className="border border-border rounded-xl p-6 bg-card">
              <h3 className="font-semibold mb-2">How are recommendations generated?</h3>
              <p className="text-sm text-muted-foreground">
                We use advanced AI to analyze connected social profiles and curate real, buyable products from trusted retailers that match the recipient's interests and style.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
