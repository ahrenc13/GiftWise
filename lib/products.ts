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
    description: 'Perfect for thoughtful gift giving',
    priceInCents: 799, // $7.99/month
    credits: 5,
    tier: 'basic',
    features: [
      '5 recommendations per month',
      'All social integrations',
      'AI-curated gift catalog',
      'Custom experience packages',
      'Email support',
    ],
  },
  {
    id: 'giftwise-premium',
    name: 'Unlimited',
    description: 'For the ultimate gifter',
    priceInCents: 1499, // $14.99/month
    credits: 999, // Unlimited (represented as high number)
    tier: 'premium',
    features: [
      'Unlimited recommendations',
      'All social integrations',
      'Premium product catalog',
      'Luxury experience packages',
      'Priority support',
      'Early access to features',
    ],
  },
  {
    id: 'giftwise-annual',
    name: 'Annual',
    description: 'Best value - save 55%',
    priceInCents: 7999, // $79.99/year
    credits: 999,
    tier: 'premium',
    features: [
      'Unlimited recommendations',
      'All social integrations',
      'Premium product catalog',
      'Luxury experience packages',
      'Priority support',
      'Early access to features',
      'Gift reminder calendar',
    ],
  },
]
