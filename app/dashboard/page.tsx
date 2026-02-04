import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import { Gift, Instagram, Music, TrendingUp, Sparkles } from 'lucide-react'
import Link from 'next/link'
import ConnectPlatformButton from '@/components/connect-platform-button'
import StartRecommendationButton from '@/components/start-recommendation-button'
import { FEATURES } from '@/lib/feature-flags'

export default async function DashboardPage() {
  const supabase = await createClient()
  
  const { data: { user }, error } = await supabase.auth.getUser()
  
  if (error || !user) {
    redirect('/auth/login')
  }

  // Fetch user profile
  const { data: profile } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', user.id)
    .single()

  // Fetch connected platforms
  const { data: connections } = await supabase
    .from('oauth_connections')
    .select('*')
    .eq('user_id', user.id)
    .eq('is_active', true)

  // Fetch recent sessions
  const { data: sessions } = await supabase
    .from('recommendation_sessions')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(5)

  const connectedPlatforms = new Set(connections?.map(c => c.platform) || [])
  const hasAnyConnection = connections && connections.length > 0
  const creditsRemaining = profile?.credits_remaining ?? 3

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Gift className="w-6 h-6 text-primary" />
            <span className="font-serif text-xl font-semibold">GiftWise</span>
          </Link>
          <div className="flex items-center gap-4">
            <div className="text-sm">
              <span className="text-muted-foreground">Credits: </span>
              <span className="font-semibold">{creditsRemaining}</span>
            </div>
            <form action="/auth/signout" method="post">
              <button className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Sign Out
              </button>
            </form>
          </div>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Testing Mode Banner */}
        {!FEATURES.PAYMENTS_ENABLED && (
          <div className="mb-8 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-2 border-green-500/30 rounded-xl p-6">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
              <div>
                <h3 className="font-semibold text-lg mb-1">Testing Mode Active</h3>
                <p className="text-sm text-muted-foreground">
                  Payments are disabled. All features are free and unlimited for testing. 
                  <span className="text-green-600 font-medium ml-1">Generate as many recommendations as you want!</span>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Welcome Section */}
        <div className="mb-12">
          <h1 className="text-4xl font-serif font-bold mb-2">
            Welcome back, {profile?.full_name || 'Gift Giver'}
          </h1>
          <p className="text-lg text-muted-foreground">
            {hasAnyConnection 
              ? "Ready to find the perfect gift? Start a new recommendation below." 
              : "Connect social accounts to start finding thoughtful gifts."}
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Connect Platforms */}
            <section className="border border-border rounded-2xl p-8 bg-card">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-2xl font-serif font-semibold">Connect Platforms</h2>
                  <p className="text-sm text-muted-foreground">
                    Add their public profiles - perfect for surprise gifts!
                  </p>
                </div>
              </div>

              {/* Info callout */}
              <div className="bg-accent/10 border border-accent/20 rounded-xl p-4 mb-6">
                <div className="flex gap-3">
                  <Gift className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-muted-foreground">
                    <p className="font-medium text-foreground mb-1">Surprise Gift Mode</p>
                    <p>
                      Just enter their public usernames - no login required! We analyze what they post, 
                      like, and share to find gifts they'll love. They'll never know you're using this.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4 mb-6">
                {[
                  { platform: 'instagram', name: 'Instagram', icon: Instagram, color: 'from-purple-500 to-pink-500' },
                  { platform: 'tiktok', name: 'TikTok', icon: TrendingUp, color: 'from-black to-red-500' },
                  { platform: 'pinterest', name: 'Pinterest', icon: Sparkles, color: 'from-red-500 to-rose-500' },
                  { platform: 'spotify', name: 'Spotify', icon: Music, color: 'from-green-500 to-emerald-500', disabled: true, note: 'Coming soon' },
                ].map((item) => {
                  const isConnected = connectedPlatforms.has(item.platform)
                  return (
                    <div
                      key={item.platform}
                      className={`relative border rounded-xl p-6 transition-all ${
                        isConnected
                          ? 'border-primary bg-primary/5'
                          : 'border-border bg-card hover:shadow-md'
                      }`}
                    >
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center mb-4`}>
                        <item.icon className="w-6 h-6 text-white" />
                      </div>
                      <h3 className="font-semibold mb-2">{item.name}</h3>
                      {isConnected ? (
                        <div className="flex items-center gap-2 text-sm text-primary">
                          <div className="w-2 h-2 rounded-full bg-primary" />
                          <span>Connected</span>
                        </div>
                      ) : item.disabled ? (
                        <p className="text-sm text-muted-foreground">{item.note}</p>
                      ) : (
                        <ConnectPlatformButton platform={item.platform} name={item.name} />
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Additional Platforms */}
              <details className="group">
                <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground flex items-center gap-2 mb-4">
                  <span>Additional Platforms (Optional)</span>
                  <TrendingUp className="w-4 h-4 transition-transform group-open:rotate-90" />
                </summary>
                <div className="grid sm:grid-cols-3 gap-3">
                  {[
                    { platform: 'youtube', name: 'YouTube', color: 'from-red-500 to-red-600', active: true },
                    { platform: 'goodreads', name: 'Goodreads', color: 'from-yellow-600 to-amber-600', active: true },
                    { platform: 'lastfm', name: 'Last.fm', color: 'from-red-600 to-red-700', active: true },
                    { platform: 'letterboxd', name: 'Letterboxd', color: 'from-blue-500 to-cyan-500', note: 'Coming soon' },
                    { platform: 'strava', name: 'Strava', color: 'from-orange-600 to-red-500', note: 'Coming soon' },
                    { platform: 'reddit', name: 'Reddit', color: 'from-orange-500 to-orange-600', note: 'Coming soon' },
                  ].map((item) => {
                    const isConnected = connections?.some(c => c.platform === item.platform)
                    
                    return (
                      <div
                        key={item.platform}
                        className="relative border border-border rounded-lg p-4 bg-muted/30"
                      >
                        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${item.color} mb-2`} />
                        <h4 className="text-sm font-medium mb-1">{item.name}</h4>
                        {isConnected ? (
                          <div className="flex items-center gap-1 text-xs text-primary">
                            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                            <span>Connected</span>
                          </div>
                        ) : item.active ? (
                          <ConnectPlatformButton platform={item.platform} name={item.name} />
                        ) : (
                          <p className="text-xs text-muted-foreground">{item.note}</p>
                        )}
                      </div>
                    )
                  })}
                </div>
              </details>
            </section>

            {/* Start New Recommendation */}
            {hasAnyConnection && (
              <section className="border border-primary/20 rounded-2xl p-8 bg-gradient-to-br from-primary/5 to-accent/5">
                <h2 className="text-2xl font-serif font-semibold mb-4">Ready to Find a Gift?</h2>
                <p className="text-muted-foreground mb-6 leading-relaxed">
                  Start a new recommendation session. We'll analyze the connected profiles and curate personalized gift options.
                </p>
                <StartRecommendationButton creditsRemaining={creditsRemaining} />
              </section>
            )}

            {/* Recent Sessions */}
            {sessions && sessions.length > 0 && (
              <section className="border border-border rounded-2xl p-8 bg-card">
                <h2 className="text-2xl font-serif font-semibold mb-6">Recent Recommendations</h2>
                <div className="space-y-4">
                  {sessions.map((session) => (
                    <Link
                      key={session.id}
                      href={`/recommendations/${session.id}`}
                      className="block border border-border rounded-xl p-4 hover:shadow-md transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">
                            {session.status === 'completed' ? 'Completed' : 'Processing'}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {new Date(session.created_at).toLocaleDateString('en-US', {
                              month: 'long',
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </p>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                          session.status === 'completed' 
                            ? 'bg-secondary/10 text-secondary' 
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          {session.status}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Credits Card */}
            <div className="border border-border rounded-2xl p-6 bg-card">
              <h3 className="font-serif font-semibold mb-4">Your Plan</h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Subscription</p>
                  <p className="text-lg font-semibold capitalize">{profile?.subscription_tier || 'Free'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Credits Remaining</p>
                  <p className="text-3xl font-serif font-bold">{creditsRemaining}</p>
                </div>
                {creditsRemaining === 0 && (
                  <Link
                    href="/pricing"
                    className="block w-full text-center bg-primary text-primary-foreground rounded-full py-3 font-semibold hover:bg-primary/90 transition-colors"
                  >
                    Upgrade Plan
                  </Link>
                )}
              </div>
            </div>

            {/* Tips Card */}
            <div className="border border-border rounded-2xl p-6 bg-gradient-to-br from-secondary/5 to-accent/5">
              <h3 className="font-serif font-semibold mb-4">Pro Tips</h3>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li className="flex gap-2">
                  <span className="text-primary mt-0.5">•</span>
                  <span>Connect multiple platforms for better recommendations</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-primary mt-0.5">•</span>
                  <span>More profile data = more personalized gifts</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-primary mt-0.5">•</span>
                  <span>Check out bespoke packages for unique experiences</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
