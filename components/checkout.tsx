'use client'

import { useState, useEffect } from 'react'
import { loadStripe } from '@stripe/stripe-js'
import {
  EmbeddedCheckoutProvider,
  EmbeddedCheckout,
} from '@stripe/react-stripe-js'
import { startCheckout } from '@/app/actions/stripe'

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!)

export default function Checkout({ productId }: { productId: string }) {
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    startCheckout(productId)
      .then((data) => {
        if (data.clientSecret) {
          setClientSecret(data.clientSecret)
        }
      })
      .catch((err) => {
        console.error('Error starting checkout:', err)
        setError('Failed to start checkout. Please try again.')
      })
  }, [productId])

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive mb-4">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="text-primary hover:underline"
        >
          Try Again
        </button>
      </div>
    )
  }

  if (!clientSecret) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <EmbeddedCheckoutProvider stripe={stripePromise} options={{ clientSecret }}>
      <EmbeddedCheckout />
    </EmbeddedCheckoutProvider>
  )
}
