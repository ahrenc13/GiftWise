import Link from 'next/link'
import { Sparkles, Heart, Gift, Zap, Instagram, Music, TrendingUp } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-border/40 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Gift className="w-6 h-6 text-primary" />
            <span className="font-serif text-xl font-semibold text-foreground">GiftWise</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="#how-it-works" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              How it Works
            </Link>
            <Link href="#pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Pricing
            </Link>
            <Link 
              href="/auth/sign-up"
              className="inline-flex items-center justify-center rounded-full bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-muted/30 to-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full text-sm font-medium mb-6">
              <Sparkles className="w-4 h-4" />
              Perfect for Valentine's Day
            </div>
            <h1 className="text-5xl lg:text-6xl font-serif font-bold text-balance mb-6 leading-tight">
              Find the Perfect Gift, <span className="text-primary">Every Time</span>
            </h1>
            <p className="text-lg text-muted-foreground text-balance mb-10 leading-relaxed">
              Stop guessing. Start gifting with confidence. We analyze social profiles to discover thoughtful, personalized gifts that show you truly care.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link 
                href="/auth/sign-up"
                className="inline-flex items-center justify-center rounded-full bg-primary px-8 py-4 text-base font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-lg hover:shadow-xl"
              >
                Start Finding Gifts
                <Heart className="ml-2 w-5 h-5" />
              </Link>
              <Link 
                href="#how-it-works"
                className="inline-flex items-center justify-center rounded-full border-2 border-border px-8 py-4 text-base font-semibold text-foreground hover:bg-muted/50 transition-colors"
              >
                See How It Works
              </Link>
            </div>
            <p className="text-sm text-muted-foreground mt-6">
              3 free recommendations • No credit card required
            </p>
          </div>
        </div>
        
        {/* Decorative gradient orbs */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl -z-10" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-secondary/5 rounded-full blur-3xl -z-10" />
      </section>

      {/* Social Proof */}
      <section className="border-y border-border/40 bg-muted/20 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="flex items-center gap-3">
              <div className="flex -space-x-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-secondary border-2 border-background" />
                ))}
              </div>
              <div>
                <p className="font-semibold text-foreground">500+ happy gift givers</p>
                <p className="text-sm text-muted-foreground">Finding perfect gifts daily</p>
              </div>
            </div>
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2">
                <Instagram className="w-5 h-5 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Instagram</span>
              </div>
              <div className="flex items-center gap-2">
                <Music className="w-5 h-5 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Spotify</span>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">TikTok</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-4xl font-serif font-bold mb-4">How GiftWise Works</h2>
            <p className="text-lg text-muted-foreground text-balance">
              Three simple steps to discover gifts that truly resonate
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '1',
                title: 'Connect Their Profiles',
                description: 'Link Instagram, Spotify, TikTok, or Pinterest accounts. We analyze interests, style, and personality.',
                icon: Sparkles,
              },
              {
                step: '2',
                title: 'AI Curates 30 Real Gifts',
                description: 'Our AI searches across retailers to find actual, buyable products that match their unique profile.',
                icon: Zap,
              },
              {
                step: '3',
                title: 'Get Personalized Picks',
                description: 'Receive curated recommendations plus bespoke experience packages tailored to their location and interests.',
                icon: Gift,
              },
            ].map((item) => (
              <div key={item.step} className="relative">
                <div className="absolute -top-4 -left-4 w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-xl font-serif font-bold text-primary">{item.step}</span>
                </div>
                <div className="border border-border rounded-2xl p-8 bg-card hover:shadow-lg transition-shadow">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
                    <item.icon className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="text-xl font-serif font-semibold mb-3">{item.title}</h3>
                  <p className="text-muted-foreground leading-relaxed">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 bg-muted/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-4xl font-serif font-bold mb-4">Simple, Transparent Pricing</h2>
            <p className="text-lg text-muted-foreground text-balance">
              Start free, upgrade when you need more
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              {
                name: 'Free Trial',
                price: '$0',
                description: 'Perfect to try it out',
                features: [
                  '3 gift recommendations',
                  'Connect social accounts',
                  'AI-curated products',
                  'Basic bespoke packages',
                ],
                cta: 'Start Free',
                highlighted: false,
              },
              {
                name: 'Basic',
                price: '$9',
                period: '/month',
                description: 'For regular gift givers',
                features: [
                  '10 recommendations/month',
                  'All social integrations',
                  'Premium product catalog',
                  'Custom experience packages',
                  'Priority support',
                ],
                cta: 'Get Basic',
                highlighted: true,
              },
              {
                name: 'Premium',
                price: '$19',
                period: '/month',
                description: 'For the ultimate gifter',
                features: [
                  'Unlimited recommendations',
                  'All social integrations',
                  'Premium product catalog',
                  'Luxury experience packages',
                  'White-glove support',
                  'Early access to features',
                ],
                cta: 'Get Premium',
                highlighted: false,
              },
            ].map((plan) => (
              <div 
                key={plan.name} 
                className={`relative border rounded-2xl p-8 bg-card ${
                  plan.highlighted 
                    ? 'border-primary shadow-xl scale-105' 
                    : 'border-border hover:shadow-lg'
                } transition-all`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground px-4 py-1 rounded-full text-sm font-medium">
                    Most Popular
                  </div>
                )}
                <div className="text-center mb-6">
                  <h3 className="text-xl font-serif font-semibold mb-2">{plan.name}</h3>
                  <p className="text-sm text-muted-foreground mb-4">{plan.description}</p>
                  <div className="flex items-end justify-center gap-1">
                    <span className="text-4xl font-serif font-bold">{plan.price}</span>
                    {plan.period && <span className="text-muted-foreground mb-1">{plan.period}</span>}
                  </div>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <Heart className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  href="/auth/sign-up"
                  className={`block w-full text-center rounded-full py-3 font-semibold transition-colors ${
                    plan.highlighted
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                      : 'bg-muted text-foreground hover:bg-muted/80'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-primary/10 via-accent/5 to-secondary/10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl lg:text-5xl font-serif font-bold mb-6 text-balance">
            Ready to Give the Perfect Gift?
          </h2>
          <p className="text-lg text-muted-foreground mb-10 text-balance leading-relaxed">
            Join hundreds of thoughtful gift givers who trust GiftWise to find meaningful presents that truly resonate.
          </p>
          <Link 
            href="/auth/sign-up"
            className="inline-flex items-center justify-center rounded-full bg-primary px-10 py-4 text-lg font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-lg hover:shadow-xl"
          >
            Get 3 Free Recommendations
            <Sparkles className="ml-2 w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 bg-muted/20 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Gift className="w-5 h-5 text-primary" />
              <span className="font-serif font-semibold">GiftWise</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2024 GiftWise. Find the perfect gift, every time.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
