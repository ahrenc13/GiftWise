'use client'

import { useState, useEffect } from 'react'
import { Heart, Gift, Sparkles, ExternalLink } from 'lucide-react'

interface BespokePackage {
  id: string
  name: string
  theme: string
  experience_title: string
  experience_description: string
  experience_price: number
  gifts: Array<{
    title: string
    description: string
    estimatedPrice: number
    buyUrl: string
  }>
  total_price: number
  why_perfect: string
}

export function BespokePackages({ sessionId }: { sessionId: string }) {
  const [packages, setPackages] = useState<BespokePackage[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPackage, setSelectedPackage] = useState<string | null>(null)

  useEffect(() => {
    async function loadPackages() {
      try {
        const res = await fetch('/api/generate-bespoke-packages', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sessionId }),
        })
        const data = await res.json()
        if (data.packages) {
          setPackages(data.packages)
        }
      } catch (error) {
        console.error('[v0] Failed to load bespoke packages:', error)
      } finally {
        setLoading(false)
      }
    }
    loadPackages()
  }, [sessionId])

  if (loading) {
    return (
      <section className="py-16 bg-gradient-to-br from-rose-50 to-pink-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-rose-100 text-rose-700 rounded-full text-sm font-medium mb-4">
              <Sparkles className="w-4 h-4" />
              Curating something special...
            </div>
            <h2 className="text-4xl font-serif font-bold text-gray-900 mb-4">
              Bespoke Experience Packages
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Combining experiences with thoughtfully selected gifts
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-2xl p-8 shadow-sm animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-5/6"></div>
              </div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  if (packages.length === 0) return null

  return (
    <section className="py-16 bg-gradient-to-br from-rose-50 to-pink-50">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-rose-100 text-rose-700 rounded-full text-sm font-medium mb-4">
            <Sparkles className="w-4 h-4" />
            Curated Just for Them
          </div>
          <h2 className="text-4xl font-serif font-bold text-gray-900 mb-4">
            Bespoke Experience Packages
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Give more than a gift — give an unforgettable experience paired with thoughtful presents
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-7xl mx-auto">
          {packages.map((pkg) => (
            <div
              key={pkg.id}
              className={`bg-white rounded-2xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-300 cursor-pointer transform hover:-translate-y-1 ${
                selectedPackage === pkg.id ? 'ring-2 ring-rose-500' : ''
              }`}
              onClick={() => setSelectedPackage(selectedPackage === pkg.id ? null : pkg.id)}
            >
              <div className="bg-gradient-to-br from-rose-500 to-pink-600 p-6 text-white">
                <div className="flex items-start justify-between mb-3">
                  <Gift className="w-8 h-8" />
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedPackage(selectedPackage === pkg.id ? null : pkg.id)
                    }}
                    className="text-white/80 hover:text-white"
                  >
                    <Heart className="w-6 h-6" />
                  </button>
                </div>
                <h3 className="text-2xl font-bold mb-2">{pkg.name}</h3>
                <p className="text-rose-100 text-sm leading-relaxed">{pkg.theme}</p>
              </div>

              <div className="p-6">
                {/* Experience */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-900">The Experience</h4>
                    <span className="text-rose-600 font-medium">${pkg.experience_price}</span>
                  </div>
                  <p className="text-sm font-medium text-gray-800 mb-1">{pkg.experience_title}</p>
                  <p className="text-sm text-gray-600 leading-relaxed">{pkg.experience_description}</p>
                </div>

                {/* Gifts */}
                <div className="mb-6">
                  <h4 className="font-semibold text-gray-900 mb-3">Plus These Gifts</h4>
                  <div className="space-y-3">
                    {pkg.gifts.map((gift, idx) => (
                      <div key={idx} className="border-l-2 border-rose-200 pl-3">
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-sm font-medium text-gray-800">{gift.title}</p>
                          <span className="text-sm text-gray-600">${gift.estimatedPrice}</span>
                        </div>
                        <p className="text-xs text-gray-600 mb-1">{gift.description}</p>
                        <a
                          href={gift.buyUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-rose-600 hover:text-rose-700 inline-flex items-center gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Find it <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Why Perfect */}
                <div className="pt-4 border-t border-gray-100">
                  <p className="text-sm text-gray-700 leading-relaxed italic">"{pkg.why_perfect}"</p>
                </div>

                {/* Total */}
                <div className="mt-6 pt-4 border-t border-gray-200 flex items-center justify-between">
                  <span className="font-semibold text-gray-900">Total Package</span>
                  <span className="text-2xl font-bold text-rose-600">${pkg.total_price}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
