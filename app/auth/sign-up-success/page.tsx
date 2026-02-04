import Link from 'next/link'
import { Gift, Mail, Sparkles } from 'lucide-react'

export default function SignUpSuccessPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-secondary/5 flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <Link href="/" className="inline-flex items-center gap-2 mb-8">
          <Gift className="w-8 h-8 text-primary" />
          <span className="font-serif text-2xl font-semibold">GiftWise</span>
        </Link>

        <div className="border border-border rounded-2xl p-8 bg-card shadow-xl">
          <div className="w-16 h-16 rounded-full bg-secondary/10 flex items-center justify-center mx-auto mb-6">
            <Mail className="w-8 h-8 text-secondary" />
          </div>

          <h1 className="text-3xl font-serif font-bold mb-4">
            Check Your Email
          </h1>
          <p className="text-muted-foreground leading-relaxed mb-8">
            We've sent you a confirmation email. Click the link in the email to activate your account and start finding perfect gifts.
          </p>

          <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 mb-6">
            <div className="flex items-center gap-2 text-sm text-primary font-medium mb-2">
              <Sparkles className="w-4 h-4" />
              <span>What's Next?</span>
            </div>
            <ul className="text-sm text-muted-foreground text-left space-y-2">
              <li>1. Check your email inbox</li>
              <li>2. Click the confirmation link</li>
              <li>3. Start connecting social profiles</li>
              <li>4. Get 3 free gift recommendations</li>
            </ul>
          </div>

          <Link
            href="/auth/login"
            className="inline-block text-primary font-medium hover:underline"
          >
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  )
}
