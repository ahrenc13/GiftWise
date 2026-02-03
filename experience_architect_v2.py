"""
EXPERIENCE ARCHITECT - DYNAMIC GENERATION
Creates bespoke experience packages for ANY interest using intelligence data.
Generates experiences dynamically from enrichment_data.py (50+ interests).
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from enrichment_data import GIFT_INTELLIGENCE

class ExperienceArchitect:
    """
    Builds complete experience packages from interests and context.
    
    Each experience includes:
    - Title and description
    - Reservation/booking links
    - Shopping list (required + optional items)
    - Step-by-step booking guide
    - Logistics (parking, timing, what to bring)
    - Pro tips from community wisdom
    """
    
    def __init__(self):
        """Initialize experience architect."""
        self.experience_templates = self._load_experience_templates()
    
    def create_experience(
        self,
        interest: str,
        location: str,
        budget: tuple,
        profile_context: Dict,
        relationship: str = 'close_friend'
    ) -> Dict:
        """
        Create a complete experience package dynamically from intelligence data.
        
        Args:
            interest: Core interest (e.g., 'cooking', 'golf', 'wine', 'basketball')
            location: City/region (e.g., 'Indianapolis, IN')
            budget: (min, max) price range
            profile_context: Additional context from recipient profile
            relationship: Relationship to recipient
            
        Returns:
            Complete experience package with all details
        """
        
        # Check if we have a premium template for this interest
        template = self._match_template(interest, profile_context)
        
        if template:
            # Use detailed template for common experiences
            return self._build_from_template(template, interest, location, budget, profile_context, relationship)
        else:
            # Dynamically generate from intelligence data for ALL other interests
            return self._create_dynamic_experience(interest, location, budget, profile_context, relationship)
    
    def _load_experience_templates(self) -> Dict:
        """
        Load experience templates.
        Comprehensive library of experience types.
        """
        return {
            'cooking_class': {
                'title': 'Couples Cooking Class: {cuisine} Cuisine',
                'subtitle': 'Master new recipes together',
                'interest_match': ['cooking', 'food', 'culinary'],
                'cost_range': (100, 200),
                'cost_breakdown': {
                    'class_fee': (80, 150),
                    'shopping_items': (20, 50)
                },
                'booking_steps': [
                    "Visit local cooking school website or Sur La Table",
                    "Browse couples classes in {cuisine} cuisine",
                    "Select date (weekends recommended)",
                    "Book online or call to reserve",
                    "Receive confirmation email with details"
                ],
                'logistics': {
                    'duration': '2-3 hours',
                    'what_to_bring': ['Apron (usually provided)', 'Camera for photos', 'Appetite!'],
                    'what_to_wear': 'Comfortable clothes, closed-toe shoes',
                    'parking': 'Check venue website',
                    'arrive_early': '15 minutes before start'
                },
                'shopping_list_template': {
                    'required': [
                        {'item': 'Quality apron set', 'why': 'For practicing at home', 'price_range': (20, 40)},
                        {'item': "Chef's knife", 'why': 'Essential cooking tool', 'price_range': (40, 80)}
                    ],
                    'optional': [
                        {'item': 'Recipe journal', 'why': 'Document new recipes', 'price_range': (15, 25)},
                        {'item': 'Wine pairing book', 'why': 'Enhance the meals', 'price_range': (20, 30)}
                    ]
                },
                'reservation_sources': {
                    'national': ['https://www.surlatable.com/classes', 'https://www.williams-sonoma.com/classes'],
                    'search_terms': ['{location} cooking classes', 'couples cooking class {location}', '{cuisine} cooking class {location}']
                },
                'pro_tips': [
                    "Weekend classes book up fast - reserve 2-3 weeks ahead",
                    "Ask about private classes for more intimate experience",
                    "Bring containers if you want to take food home",
                    "Most classes include wine/beverages"
                ],
                'best_for': ['date night', 'anniversary', 'foodie couples'],
                'season': 'Year-round',
                'duration': '2-3 hours',
                'image_url': 'cooking_class'
            },
            
            'golf_experience': {
                'title': 'Premium Golf Experience at {venue}',
                'subtitle': 'Play a championship course',
                'interest_match': ['golf', 'golfing', 'golfer'],
                'cost_range': (150, 400),
                'cost_breakdown': {
                    'green_fees': (80, 200),
                    'cart_rental': (30, 50),
                    'equipment': (40, 150)
                },
                'booking_steps': [
                    "Find premium courses on GolfNow or TeeOff.com",
                    "Check availability for desired date",
                    "Book tee time online",
                    "Add cart rental if needed",
                    "Receive confirmation with course details"
                ],
                'logistics': {
                    'duration': '4-5 hours',
                    'what_to_bring': ['Golf clubs', 'Golf shoes', 'Sunscreen', 'Hat/visor'],
                    'what_to_wear': 'Golf attire (collared shirt, khakis/shorts)',
                    'parking': 'Usually free at course',
                    'arrive_early': '30 minutes for warm-up'
                },
                'shopping_list_template': {
                    'required': [
                        {'item': 'Premium golf balls (dozen)', 'why': 'For the round', 'price_range': (30, 60)},
                        {'item': 'Golf glove', 'why': 'Better grip', 'price_range': (15, 30)}
                    ],
                    'optional': [
                        {'item': 'Rangefinder', 'why': 'Accurate distances', 'price_range': (150, 300)},
                        {'item': 'Golf GPS watch', 'why': 'Course management', 'price_range': (100, 300)}
                    ]
                },
                'reservation_sources': {
                    'national': ['https://www.golfnow.com', 'https://www.teeoff.com', 'https://www.supremegolf.com'],
                    'search_terms': ['{location} golf courses', 'best golf courses {location}', 'championship golf {location}']
                },
                'pro_tips': [
                    "Book twilight rates for 30-50% discount",
                    "Check if course requires handicap card",
                    "Call pro shop for course conditions",
                    "Some courses offer first-time visitor specials"
                ],
                'best_for': ['golf enthusiasts', 'father\'s day', 'business gift'],
                'season': 'Spring-Fall (weather dependent)',
                'duration': '4-5 hours',
                'image_url': 'golf_course'
            },
            
            'wine_tasting': {
                'title': 'Wine Country Day Trip',
                'subtitle': 'Visit local wineries and vineyards',
                'interest_match': ['wine', 'winery', 'vineyard'],
                'cost_range': (80, 250),
                'cost_breakdown': {
                    'tastings': (50, 150),
                    'lunch': (30, 80),
                    'transportation': (0, 20)
                },
                'booking_steps': [
                    "Research wineries in {location} region",
                    "Book tasting reservations online",
                    "Plan 2-3 wineries for the day",
                    "Consider transportation (uber/designated driver)",
                    "Make lunch reservation at winery restaurant"
                ],
                'logistics': {
                    'duration': '4-6 hours',
                    'what_to_bring': ['Water bottle', 'Sunscreen', 'Comfortable shoes', 'Cooler for wine purchases'],
                    'what_to_wear': 'Casual comfortable clothes',
                    'parking': 'Free at most wineries',
                    'arrive_early': 'For first tasting'
                },
                'shopping_list_template': {
                    'required': [
                        {'item': 'Wine tote bag', 'why': 'Carry purchases safely', 'price_range': (15, 30)},
                        {'item': 'Water bottle', 'why': 'Stay hydrated', 'price_range': (10, 25)}
                    ],
                    'optional': [
                        {'item': 'Wine journal', 'why': 'Record favorites', 'price_range': (15, 30)},
                        {'item': 'Cheese knife set', 'why': 'Picnic at vineyard', 'price_range': (20, 40)}
                    ]
                },
                'reservation_sources': {
                    'national': ['https://www.opentable.com', 'https://www.tripadvisor.com/wineries'],
                    'search_terms': ['wineries near {location}', 'wine tasting {location}', 'vineyard tours {location}']
                },
                'pro_tips': [
                    "Book tastings in advance, especially weekends",
                    "Start with lighter wines, progress to reds",
                    "Pace yourself - 2-3 wineries is plenty",
                    "Many wineries offer food pairings",
                    "Ask about wine club benefits"
                ],
                'best_for': ['wine lovers', 'romantic date', 'weekend getaway'],
                'season': 'Spring-Fall (harvest season best)',
                'duration': '4-6 hours',
                'image_url': 'wine_tasting'
            },
            
            'spa_day': {
                'title': 'Luxury Spa Day Package',
                'subtitle': 'Complete relaxation and pampering',
                'interest_match': ['wellness', 'relaxation', 'self-care', 'spa'],
                'cost_range': (150, 400),
                'cost_breakdown': {
                    'spa_package': (120, 300),
                    'extras': (30, 100)
                },
                'booking_steps': [
                    "Research luxury spas in {location}",
                    "Browse package deals online",
                    "Select services (massage, facial, etc.)",
                    "Book online or call for availability",
                    "Arrive early to enjoy amenities"
                ],
                'logistics': {
                    'duration': '3-4 hours',
                    'what_to_bring': ['Robe provided', 'Swimsuit if pool/hot tub', 'Book or tablet', 'Hair tie'],
                    'what_to_wear': 'Comfortable clothes to change into',
                    'parking': 'Valet or self-parking available',
                    'arrive_early': '30 minutes to check in and relax'
                },
                'shopping_list_template': {
                    'required': [
                        {'item': 'Plush robe', 'why': 'Relaxation at home', 'price_range': (40, 80)},
                        {'item': 'Spa slippers', 'why': 'Complete the experience', 'price_range': (15, 30)}
                    ],
                    'optional': [
                        {'item': 'Essential oil diffuser', 'why': 'Create spa atmosphere', 'price_range': (25, 60)},
                        {'item': 'Spa music playlist', 'why': 'Relaxing ambiance', 'price_range': (0, 15)}
                    ]
                },
                'reservation_sources': {
                    'national': ['https://www.spafinder.com', 'https://www.spaindex.com'],
                    'search_terms': ['luxury spa {location}', 'spa packages {location}', 'day spa {location}']
                },
                'pro_tips': [
                    "Weekday appointments often less crowded",
                    "Book couples packages for discount",
                    "Arrive hydrated and avoid alcohol before",
                    "Turn off phone during experience",
                    "Ask about monthly spa membership deals"
                ],
                'best_for': ['wellness enthusiasts', 'mothers day', 'stress relief'],
                'season': 'Year-round',
                'duration': '3-4 hours',
                'image_url': 'spa_day'
            },
            
            'concert_experience': {
                'title': 'Premium Concert Experience',
                'subtitle': 'See favorite artist live with VIP treatment',
                'interest_match': ['music', 'concerts', 'live music'],
                'cost_range': (100, 500),
                'cost_breakdown': {
                    'tickets': (80, 400),
                    'parking': (10, 30),
                    'pre_show_dinner': (40, 100)
                },
                'booking_steps': [
                    "Check artist tour dates on Ticketmaster/AXS",
                    "Compare prices and seating options",
                    "Purchase tickets early for best seats",
                    "Book pre-show dinner reservation",
                    "Plan transportation and parking"
                ],
                'logistics': {
                    'duration': '4-5 hours (including dinner)',
                    'what_to_bring': ['Tickets (phone or printed)', 'ID', 'Light jacket', 'Portable charger'],
                    'what_to_wear': 'Comfortable shoes, venue-appropriate attire',
                    'parking': 'Book ahead or use rideshare',
                    'arrive_early': '30-60 minutes for food/drinks'
                },
                'shopping_list_template': {
                    'required': [
                        {'item': 'Portable phone charger', 'why': 'For photos/videos', 'price_range': (15, 40)},
                        {'item': 'Concert merch budget', 'why': 'Band t-shirt or poster', 'price_range': (30, 60)}
                    ],
                    'optional': [
                        {'item': 'Concert earplugs', 'why': 'Protect hearing', 'price_range': (15, 30)},
                        {'item': 'Binoculars', 'why': 'Better view from far seats', 'price_range': (20, 50)}
                    ]
                },
                'reservation_sources': {
                    'national': ['https://www.ticketmaster.com', 'https://www.stubhub.com', 'https://www.axs.com'],
                    'search_terms': ['{artist} tour dates', 'concerts {location}', 'live music {location}']
                },
                'pro_tips': [
                    "Sign up for presale codes from venue/artist",
                    "Check resale market day-of for deals",
                    "Some venues allow seat upgrades at box office",
                    "VIP packages include perks like early entry",
                    "Take rideshare to avoid parking hassle"
                ],
                'best_for': ['music lovers', 'birthday gift', 'special occasion'],
                'season': 'Year-round',
                'duration': '4-5 hours',
                'image_url': 'concert'
            },
            
            'pottery_class': {
                'title': 'Pottery Wheel Class',
                'subtitle': 'Create handmade ceramics',
                'interest_match': ['art', 'pottery', 'ceramics', 'crafts'],
                'cost_range': (60, 150),
                'cost_breakdown': {
                    'class_fee': (50, 120),
                    'materials': (10, 30)
                },
                'booking_steps': [
                    "Find local pottery studios online",
                    "Check beginner class schedules",
                    "Book intro to wheel throwing class",
                    "Read studio policies on glazing/firing",
                    "Receive confirmation with what to bring"
                ],
                'logistics': {
                    'duration': '2-3 hours',
                    'what_to_bring': ['Old clothes/apron', 'Towel', 'Water bottle', 'Hair tie'],
                    'what_to_wear': 'Clothes that can get messy',
                    'parking': 'Check studio location',
                    'arrive_early': '10 minutes for check-in'
                },
                'shopping_list_template': {
                    'required': [
                        {'item': 'Pottery apron', 'why': 'Keep clothes clean', 'price_range': (15, 30)},
                        {'item': 'Clay tools set', 'why': 'For future projects', 'price_range': (20, 40)}
                    ],
                    'optional': [
                        {'item': 'Pottery books', 'why': 'Learn techniques', 'price_range': (20, 35)},
                        {'item': 'Storage for pieces', 'why': 'Display finished work', 'price_range': (15, 40)}
                    ]
                },
                'reservation_sources': {
                    'national': [],
                    'search_terms': ['pottery class {location}', 'wheel throwing {location}', 'ceramics studio {location}']
                },
                'pro_tips': [
                    "Pieces need 2-3 weeks to fire and glaze",
                    "Bring a friend for more fun",
                    "Ask about open studio time for practice",
                    "Take photos of process for memories",
                    "Most studios provide clay and tools"
                ],
                'best_for': ['artistic people', 'creative dates', 'unique experience'],
                'season': 'Year-round',
                'duration': '2-3 hours',
                'image_url': 'pottery'
            },
            
            'hot_air_balloon': {
                'title': 'Hot Air Balloon Ride at Sunrise',
                'subtitle': 'Breathtaking aerial adventure',
                'interest_match': ['adventure', 'travel', 'photography', 'outdoors'],
                'cost_range': (200, 350),
                'cost_breakdown': {
                    'balloon_ride': (180, 300),
                    'champagne_toast': (20, 50)
                },
                'booking_steps': [
                    "Research balloon companies in {location}",
                    "Book sunrise flight (best conditions)",
                    "Provide passenger weight (required for safety)",
                    "Confirm weather-dependent booking",
                    "Get pick-up location details"
                ],
                'logistics': {
                    'duration': '3-4 hours total (1 hour flight)',
                    'what_to_bring': ['Camera', 'Layers (cooler at altitude)', 'Hat', 'Closed-toe shoes'],
                    'what_to_wear': 'Comfortable athletic clothes',
                    'parking': 'Meet at launch site',
                    'arrive_early': 'Dawn flights start very early!'
                },
                'shopping_list_template': {
                    'required': [
                        {'item': 'Action camera', 'why': 'Capture the flight', 'price_range': (100, 300)},
                        {'item': 'Warm layers', 'why': 'Temperature drops', 'price_range': (30, 80)}
                    ],
                    'optional': [
                        {'item': 'Polarized sunglasses', 'why': 'Sun glare at altitude', 'price_range': (20, 100)},
                        {'item': 'Motion sickness meds', 'why': 'Just in case', 'price_range': (10, 15)}
                    ]
                },
                'reservation_sources': {
                    'national': [],
                    'search_terms': ['hot air balloon {location}', 'balloon ride {location}', 'sunrise balloon {location}']
                },
                'pro_tips': [
                    "Book well in advance (weather cancellations common)",
                    "Sunrise flights have calmest conditions",
                    "Flight may be rescheduled due to weather",
                    "Champagne toast is traditional after landing",
                    "Wear sturdy shoes (landing can be bumpy)"
                ],
                'best_for': ['adventure seekers', 'special occasions', 'bucket list'],
                'season': 'Spring-Fall',
                'duration': '3-4 hours',
                'image_url': 'hot_air_balloon'
            }
        }
    
    def _create_dynamic_experience(self, interest: str, location: str, budget: tuple, profile_context: Dict, relationship: str) -> Dict:
        """
        Dynamically generate experience from intelligence data.
        Works for ANY interest in enrichment_data.py.
        """
        interest_key = interest.lower().replace(' ', '_')
        
        # Get intelligence data for this interest
        intel = GIFT_INTELLIGENCE.get(interest_key, {})
        
        if not intel:
            # Fallback for truly unknown interests
            return self._create_fallback_experience(interest, location, budget)
        
        # Extract data from intelligence
        do_buy = intel.get('do_buy', [])
        search_terms = intel.get('search_terms', [])
        activity_type = intel.get('activity_type', 'unknown')
        trending = intel.get('trending_2026', [])
        
        # Determine experience type based on activity_type
        if activity_type == 'active':
            # Active interests → participation experiences
            experience_type = 'class_or_lesson'
            title_template = f"{interest.title()} Class or Workshop"
            subtitle = "Hands-on learning experience"
        else:
            # Passive interests → spectator/appreciation experiences
            experience_type = 'event_or_visit'
            title_template = f"{interest.title()} Experience"
            subtitle = "Immersive appreciation event"
        
        # Build shopping list from "do_buy" recommendations
        shopping_list = self._build_dynamic_shopping_list(do_buy[:5], budget)
        
        # Generate booking steps
        how_to_book = self._generate_booking_steps(interest, location, search_terms)
        
        # Generate logistics
        logistics = self._generate_logistics(activity_type, interest)
        
        # Generate pro tips
        pro_tips = self._generate_pro_tips(intel, activity_type)
        
        # Build complete experience
        experience = {
            'experience_id': self._generate_id(interest, location),
            'interest': interest,
            'title': title_template,
            'subtitle': subtitle,
            'why_perfect': self._explain_fit(interest, profile_context),
            'total_cost': f"${budget[0]}-${budget[1]}",
            'cost_breakdown': {
                'main_experience': ((budget[0] + budget[1]) // 2 * 0.7, 'Experience or class fee'),
                'shopping_items': ((budget[0] + budget[1]) // 2 * 0.3, 'Related items and supplies')
            },
            'reservation_links': self._generate_reservation_links(interest, location, search_terms),
            'shopping_list': shopping_list,
            'how_to_book': how_to_book,
            'logistics': logistics,
            'pro_tips': pro_tips,
            'best_for': intel.get('gift_occasions', ['birthday', 'special occasion']),
            'duration': self._estimate_duration(activity_type),
            'season': 'Year-round',
            'relationship_appropriate': {
                'appropriate': True,
                'best_for': intel.get('gift_occasions', []),
                'note': 'Great choice!'
            },
            'image_url': interest_key,
            'created_at': datetime.now().isoformat(),
            'generation_method': 'dynamic_from_intelligence'
        }
        
        return experience
    
    def _build_dynamic_shopping_list(self, do_buy_items: List[str], budget: tuple) -> Dict:
        """Build shopping list from intelligence "do_buy" recommendations."""
        shopping_list = {
            'required': [],
            'optional': [],
            'total_required': 0,
            'total_optional': 0
        }
        
        # Split items into required (first 2-3) and optional (rest)
        required_items = do_buy_items[:3]
        optional_items = do_buy_items[3:5]
        
        for item_name in required_items:
            # Estimate price (30% of budget divided by number of items)
            est_price = int((budget[0] + budget[1]) / 2 * 0.3 / len(required_items))
            
            shopping_item = {
                'item': item_name,
                'why_needed': 'Essential for the experience',
                'estimated_price': est_price,
                'price_range': f"${int(est_price * 0.7)}-${int(est_price * 1.3)}",
                'shop_link': f"https://www.amazon.com/s?k={item_name.replace(' ', '+')}",
                'alternative_sources': ['Amazon', 'Target', 'Local retailers']
            }
            shopping_list['required'].append(shopping_item)
            shopping_list['total_required'] += est_price
        
        for item_name in optional_items:
            est_price = int((budget[0] + budget[1]) / 2 * 0.15 / max(len(optional_items), 1))
            
            shopping_item = {
                'item': item_name,
                'why_needed': 'Enhances the experience',
                'estimated_price': est_price,
                'price_range': f"${int(est_price * 0.7)}-${int(est_price * 1.3)}",
                'shop_link': f"https://www.amazon.com/s?k={item_name.replace(' ', '+')}",
                'alternative_sources': ['Amazon', 'Target', 'Local specialty shops']
            }
            shopping_list['optional'].append(shopping_item)
            shopping_list['total_optional'] += est_price
        
        return shopping_list
    
    def _generate_booking_steps(self, interest: str, location: str, search_terms: List[str]) -> List[str]:
        """Generate booking steps from search terms."""
        steps = [
            f"Search for '{search_terms[0] if search_terms else interest} {location}' online",
            "Compare reviews and ratings on Google, Yelp, or TripAdvisor",
            "Check availability and pricing",
            "Book online or call to reserve",
            "Receive confirmation with details and directions"
        ]
        return steps
    
    def _generate_logistics(self, activity_type: str, interest: str) -> Dict:
        """Generate appropriate logistics based on activity type."""
        if activity_type == 'active':
            return {
                'duration': '2-4 hours',
                'what_to_bring': ['Comfortable clothes', 'Water bottle', 'Enthusiasm'],
                'what_to_wear': 'Comfortable, activity-appropriate attire',
                'parking': 'Check venue website for details',
                'arrive_early': '10-15 minutes before start time'
            }
        else:
            return {
                'duration': '2-3 hours',
                'what_to_bring': ['Camera', 'Comfortable shoes', 'Open mind'],
                'what_to_wear': 'Casual comfortable clothes',
                'parking': 'Available at most venues',
                'arrive_early': '15 minutes recommended'
            }
    
    def _generate_pro_tips(self, intel: Dict, activity_type: str) -> List[str]:
        """Generate pro tips from intelligence data."""
        tips = []
        
        # Add don't buy items as warnings
        dont_buy = intel.get('dont_buy', [])
        if dont_buy and len(dont_buy) > 0:
            tips.append(f"Note: {dont_buy[0]}")  # Convert to pro tip
        
        # Add generic tips based on activity type
        if activity_type == 'active':
            tips.extend([
                "Book in advance for best availability",
                "Read recent reviews before selecting provider",
                "Ask about group discounts for couples or friends"
            ])
        else:
            tips.extend([
                "Weekday experiences often less crowded",
                "Check for seasonal availability",
                "Take photos to remember the experience"
            ])
        
        return tips[:4]  # Limit to 4 tips
    
    def _estimate_duration(self, activity_type: str) -> str:
        """Estimate experience duration."""
        if activity_type == 'active':
            return '2-4 hours'
        else:
            return '2-3 hours'
    
    def _generate_reservation_links(self, interest: str, location: str, search_terms: List[str]) -> Dict:
        """Generate relevant reservation/search links."""
        links = {
            'primary': None,
            'alternatives': [],
            'search_links': []
        }
        
        # Generate Google search links from search terms
        for term in search_terms[:3]:
            search_query = f"{term} {location}".replace(' ', '+')
            google_link = f"https://www.google.com/search?q={search_query}"
            links['search_links'].append({
                'label': f"Find {term} near {location}",
                'url': google_link
            })
        
        # Add generic experience platforms
        experience_query = f"{interest} experience {location}".replace(' ', '+')
        links['alternatives'] = [
            f"https://www.tripadvisor.com/Search?q={experience_query}",
            f"https://www.yelp.com/search?find_desc={experience_query}",
            f"https://www.eventbrite.com/d/{location.split(',')[0].strip().lower()}/{interest}/"
        ]
        
        return links
    
    def _create_fallback_experience(self, interest: str, location: str, budget: tuple) -> Dict:
        """Fallback for completely unknown interests."""
        return {
            'experience_id': self._generate_id(interest, location),
            'interest': interest,
            'title': f'{interest.title()} Experience in {location}',
            'subtitle': f'Explore your passion for {interest}',
            'why_perfect': f'Tailored to your love of {interest}',
            'total_cost': f"${budget[0]}-${budget[1]}",
            'reservation_links': {
                'search_links': [{
                    'label': f'{interest} activities near {location}',
                    'url': f"https://www.google.com/search?q={interest.replace(' ', '+')}+{location.replace(' ', '+')}"
                }]
            },
            'shopping_list': {'required': [], 'optional': [], 'total_required': 0, 'total_optional': 0},
            'how_to_book': ['Search for local providers', 'Compare reviews and prices', 'Book directly online'],
            'logistics': {'duration': 'Varies', 'check_venue': True},
            'pro_tips': ['Research thoroughly', 'Book in advance', 'Read recent reviews'],
            'relationship_appropriate': {'appropriate': True, 'best_for': [], 'note': 'Universal gift'},
            'created_at': datetime.now().isoformat(),
            'generation_method': 'fallback'
        }
    
    def _build_from_template(self, template: Dict, interest: str, location: str, budget: tuple, profile_context: Dict, relationship: str) -> Dict:
        """Find best matching experience template for interest."""
        interest_lower = interest.lower()
        
        for template_id, template in self.experience_templates.items():
            interest_matches = template.get('interest_match', [])
            for match in interest_matches:
                if match in interest_lower or interest_lower in match:
                    return template
        
        return None
    
    def _personalize_title(self, title_template: str, profile_context: Dict) -> str:
        """Personalize experience title based on context."""
        # Extract specific interests from context
        specific_interests = profile_context.get('specific_interests', {})
        
        # Replace placeholders
        if '{cuisine}' in title_template:
            cuisine = specific_interests.get('favorite_cuisine', 'Italian')
            title_template = title_template.replace('{cuisine}', cuisine)
        
        if '{venue}' in title_template:
            venue = 'Local Premium Course'
            title_template = title_template.replace('{venue}', venue)
        
        return title_template
    
    def _explain_fit(self, interest: str, profile_context: Dict) -> str:
        """Explain why this experience is perfect for them."""
        reasons = []
        
        # Base reason
        reasons.append(f"Matches their passion for {interest}")
        
        # Add context-specific reasons
        if 'recent_activities' in profile_context:
            recent = profile_context['recent_activities'][:2]
            if recent:
                reasons.append(f"Builds on recent interest in {', '.join(recent)}")
        
        if 'skill_level' in profile_context:
            level = profile_context['skill_level']
            reasons.append(f"Perfect for {level} level")
        
        return ". ".join(reasons) + "."
    
    def _calculate_cost(self, template: Dict, budget: tuple) -> str:
        """Calculate total cost range for experience."""
        cost_range = template.get('cost_range', (0, 0))
        
        # Ensure within budget
        min_cost = max(cost_range[0], budget[0])
        max_cost = min(cost_range[1], budget[1])
        
        if min_cost == max_cost:
            return f"${min_cost}"
        else:
            return f"${min_cost}-${max_cost}"
    
    def _find_reservation_links(self, template: Dict, location: str) -> Dict:
        """Find relevant reservation/booking links for location."""
        sources = template.get('reservation_sources', {})
        
        links = {
            'primary': None,
            'alternatives': [],
            'search_links': []
        }
        
        # National platforms (work everywhere)
        national_links = sources.get('national', [])
        if national_links:
            links['primary'] = national_links[0]
            links['alternatives'] = national_links[1:3]
        
        # Generate Google search links
        search_terms = sources.get('search_terms', [])
        for term in search_terms[:2]:
            search_term = term.replace('{location}', location)
            google_link = f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
            links['search_links'].append({
                'label': search_term,
                'url': google_link
            })
        
        return links
    
    def _build_shopping_list(self, template: Dict, budget: tuple) -> Dict:
        """Build shopping list with actual product links."""
        list_template = template.get('shopping_list_template', {})
        
        shopping_list = {
            'required': [],
            'optional': [],
            'total_required': 0,
            'total_optional': 0
        }
        
        # Process required items
        for item_template in list_template.get('required', []):
            item = self._create_shopping_item(item_template, budget)
            shopping_list['required'].append(item)
            shopping_list['total_required'] += item['estimated_price']
        
        # Process optional items
        for item_template in list_template.get('optional', []):
            item = self._create_shopping_item(item_template, budget)
            shopping_list['optional'].append(item)
            shopping_list['total_optional'] += item['estimated_price']
        
        return shopping_list
    
    def _create_shopping_item(self, item_template: Dict, budget: tuple) -> Dict:
        """Create shopping item with search link."""
        item_name = item_template['item']
        price_range = item_template.get('price_range', (0, 100))
        
        # Calculate estimated price (midpoint of range)
        estimated_price = (price_range[0] + price_range[1]) // 2
        
        # Generate Amazon search link
        search_query = item_name.replace(' ', '+')
        amazon_link = f"https://www.amazon.com/s?k={search_query}"
        
        return {
            'item': item_name,
            'why_needed': item_template.get('why', ''),
            'estimated_price': estimated_price,
            'price_range': f"${price_range[0]}-${price_range[1]}",
            'shop_link': amazon_link,
            'alternative_sources': ['Target', 'Best Buy', 'Local retailers']
        }
    
    def _build_logistics(self, template: Dict, location: str) -> Dict:
        """Build logistics information."""
        logistics_template = template.get('logistics', {})
        
        # Replace location placeholders
        logistics = {}
        for key, value in logistics_template.items():
            if isinstance(value, str):
                logistics[key] = value.replace('{location}', location)
            else:
                logistics[key] = value
        
        return logistics
    
    def _check_appropriateness(self, template: Dict, relationship: str) -> Dict:
        """Check if experience is appropriate for relationship."""
        best_for = template.get('best_for', [])
        relationship_lower = relationship.lower().replace('_', ' ')
        
        # Check if relationship mentioned in best_for
        appropriate = any(rel_type in relationship_lower or relationship_lower in rel_type 
                         for rel_type in best_for)
        
        return {
            'appropriate': appropriate or len(best_for) == 0,
            'best_for': best_for,
            'note': 'Great choice!' if appropriate else f'Also consider for: {", ".join(best_for)}'
        }
    
    def _generate_id(self, interest: str, location: str) -> str:
        """Generate unique experience ID."""
        import hashlib
        combined = f"{interest}_{location}_{datetime.now().isoformat()}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
    def _create_generic_experience(self, interest: str, location: str, budget: tuple) -> Dict:
        """Create generic experience when no template matches."""
        return {
            'experience_id': self._generate_id(interest, location),
            'interest': interest,
            'title': f'{interest.title()} Experience in {location}',
            'subtitle': f'Explore your passion for {interest}',
            'why_perfect': f'Tailored to your love of {interest}',
            'total_cost': f"${budget[0]}-${budget[1]}",
            'reservation_links': {
                'search_links': [{
                    'label': f'{interest} activities near {location}',
                    'url': f"https://www.google.com/search?q={interest.replace(' ', '+')}+{location.replace(' ', '+')}"
                }]
            },
            'shopping_list': {'required': [], 'optional': [], 'total_required': 0, 'total_optional': 0},
            'how_to_book': ['Search for local providers', 'Compare reviews and prices', 'Book directly online'],
            'logistics': {'duration': 'Varies', 'check_venue': True},
            'pro_tips': ['Research thoroughly', 'Book in advance', 'Read recent reviews'],
            'relationship_appropriate': {'appropriate': True, 'best_for': [], 'note': 'Universal gift'},
            'created_at': datetime.now().isoformat()
        }


# =============================================================================
# HELPER FUNCTIONS FOR INTEGRATION
# =============================================================================

def create_experience_simple(
    interest: str,
    location: str = "Indianapolis, IN",
    budget: tuple = (100, 300),
    relationship: str = 'close_friend'
) -> Dict:
    """
    Simple interface for creating experiences.
    
    Example usage:
        experience = create_experience_simple(
            interest='cooking',
            location='Indianapolis, IN',
            budget=(100, 200),
            relationship='romantic_partner'
        )
    """
    architect = ExperienceArchitect()
    return architect.create_experience(
        interest=interest,
        location=location,
        budget=budget,
        profile_context={},
        relationship=relationship
    )


def create_multiple_experiences(
    interests: List[str],
    location: str,
    budget: tuple,
    relationship: str,
    max_experiences: int = 3
) -> List[Dict]:
    """
    Create multiple experiences from interest list.
    
    Example usage:
        experiences = create_multiple_experiences(
            interests=['cooking', 'wine', 'golf'],
            location='Indianapolis, IN',
            budget=(100, 250),
            relationship='spouse',
            max_experiences=3
        )
    """
    architect = ExperienceArchitect()
    experiences = []
    
    for interest in interests[:max_experiences]:
        experience = architect.create_experience(
            interest=interest,
            location=location,
            budget=budget,
            profile_context={},
            relationship=relationship
        )
        experiences.append(experience)
    
    return experiences


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    # Test experience creation
    architect = ExperienceArchitect()
    
    # Create cooking class experience
    experience = architect.create_experience(
        interest='cooking',
        location='Indianapolis, IN',
        budget=(100, 200),
        profile_context={'specific_interests': {'favorite_cuisine': 'Thai'}},
        relationship='romantic_partner'
    )
    
    print("\n" + "="*70)
    print("EXPERIENCE PACKAGE")
    print("="*70 + "\n")
    print(f"Title: {experience['title']}")
    print(f"Subtitle: {experience['subtitle']}")
    print(f"\nWhy Perfect: {experience['why_perfect']}")
    print(f"Total Cost: {experience['total_cost']}")
    
    print(f"\nREQUIRED ITEMS ({len(experience['shopping_list']['required'])}):")
    for item in experience['shopping_list']['required']:
        print(f"  • {item['item']} - {item['price_range']}")
        print(f"    Why: {item['why_needed']}")
        print(f"    Shop: {item['shop_link']}")
    
    print(f"\nHOW TO BOOK:")
    for i, step in enumerate(experience['how_to_book'], 1):
        print(f"  {i}. {step}")
    
    print(f"\nPRO TIPS:")
    for tip in experience['pro_tips']:
        print(f"  • {tip}")
    
    print("\n" + "="*70)
