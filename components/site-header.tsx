import Link from 'next/link'
import { Gift, User, LogOut } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'

export async function SiteHeader() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  return (
    <header className="border-b border-border/40 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center transform group-hover:scale-110 transition-transform">
            <Gift className="w-5 h-5 text-white" />
          </div>
          <span className="font-serif text-xl font-semibold">GiftWise</span>
        </Link>

        <div className="flex items-center gap-6">
          {user ? (
            <>
              <Link
                href="/dashboard"
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Dashboard
              </Link>
              <Link
                href="/pricing"
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Pricing
              </Link>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-full">
                  <User className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    {user.email?.split('@')[0]}
                  </span>
                </div>
                <form action="/auth/signout" method="post">
                  <button
                    type="submit"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </form>
              </div>
            </>
          ) : (
            <>
              <Link
                href="/pricing"
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Pricing
              </Link>
              <Link
                href="/auth/login"
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Log in
              </Link>
              <Link
                href="/auth/sign-up"
                className="inline-flex items-center justify-center rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
