import { Suspense } from 'react'
import Link from 'next/link'
import { Gift, Sparkles, CheckCircle } from 'lucide-react'
import { verifyCheckoutSession } from '@/app/actions/stripe'

async function SuccessContent({ sessionId }: { sessionId: string }) {
  try {
    const { status } = await verifyCheckoutSession(sessionId)

    if (status === 'paid') {
      return (
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-secondary/10 flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-secondary" />
          </div>
          <h1 className="text-4xl font-serif font-bold mb-4">
            Welcome to Premium!
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-md mx-auto">
            Your subscription is now active. Start finding perfect gifts with your new credits and features.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-full bg-primary px-8 py-4 font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Sparkles className="w-5 h-5 mr-2" />
            Go to Dashboard
          </Link>
        </div>
      )
    }

    return (
      <div className="text-center">
        <p className="text-muted-foreground mb-4">Processing your payment...</p>
        <Link href="/dashboard" className="text-primary hover:underline">
          Return to Dashboard
        </Link>
      </div>
    )
  } catch (error) {
    return (
      <div className="text-center">
        <p className="text-destructive mb-4">Something went wrong</p>
        <Link href="/pricing" className="text-primary hover:underline">
          Back to Pricing
        </Link>
      </div>
    )
  }
}

export default async function SuccessPage({
  searchParams,
}: {
  searchParams: Promise<{ session_id?: string }>
}) {
  const { session_id } = await searchParams

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-secondary/5">
      <header className="border-b border-border/40 bg-white/80 backdrop-blur-sm">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Gift className="w-6 h-6 text-primary" />
            <span className="font-serif text-xl font-semibold">GiftWise</span>
          </Link>
        </nav>
      </header>

      <main className="flex items-center justify-center min-h-[calc(100vh-4rem)] px-4">
        <div className="w-full max-w-md">
          <Suspense
            fallback={
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
              </div>
            }
          >
            {session_id ? (
              <SuccessContent sessionId={session_id} />
            ) : (
              <div className="text-center">
                <p className="text-muted-foreground mb-4">Invalid session</p>
                <Link href="/pricing" className="text-primary hover:underline">
                  Back to Pricing
                </Link>
              </div>
            )}
          </Suspense>
        </div>
      </main>
    </div>
  )
}
