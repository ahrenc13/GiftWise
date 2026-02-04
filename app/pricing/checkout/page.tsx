import { Suspense } from 'react'
import Link from 'next/link'
import { Gift } from 'lucide-react'
import Checkout from '@/components/checkout'
import { PRODUCTS } from '@/lib/products'

export default async function CheckoutPage({
  searchParams,
}: {
  searchParams: Promise<{ product?: string }>
}) {
  const { product: productId } = await searchParams
  
  if (!productId) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Invalid product</p>
          <Link href="/pricing" className="text-primary hover:underline">
            Back to Pricing
          </Link>
        </div>
      </div>
    )
  }

  const product = PRODUCTS.find((p) => p.id === productId)

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/40 bg-white/80 backdrop-blur-sm">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Gift className="w-6 h-6 text-primary" />
            <span className="font-serif text-xl font-semibold">GiftWise</span>
          </Link>
        </nav>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {product && (
          <div className="text-center mb-8">
            <h1 className="text-3xl font-serif font-bold mb-2">
              Subscribe to {product.name}
            </h1>
            <p className="text-muted-foreground">{product.description}</p>
          </div>
        )}

        <Suspense
          fallback={
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          }
        >
          <Checkout productId={productId} />
        </Suspense>
      </main>
    </div>
  )
}
