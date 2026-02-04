export interface Product {
  id: string
  name: string
  description: string
  priceInCents: number
  credits?: number
  features: string[]
  tier: 'free' | 'basic' | 'premium'
}

export const PRODUCTS: Product[] = [
  {
    id: 'giftwise-basic',
    name: 'Basic',
    description: 'Perfect for regular gift givers',
    priceInCents: 900, // $9/month
    credits: 10,
    tier: 'basic',
    features: [
      '10 recommendations per month',
      'All social integrations',
      'Premium product catalog',
      'Custom experience packages',
      'Priority support',
    ],
  },
  {
    id: 'giftwise-premium',
    name: 'Premium',
    description: 'For the ultimate gifter',
    priceInCents: 1900, // $19/month
    credits: 999, // Unlimited (represented as high number)
    tier: 'premium',
    features: [
      'Unlimited recommendations',
      'All social integrations',
      'Premium product catalog',
      'Luxury experience packages',
      'White-glove support',
      'Early access to features',
    ],
  },
]
