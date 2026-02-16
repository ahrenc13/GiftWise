"""
REGIONAL CULTURE INTELLIGENCE - Local norms, preferences, and cultural context for gift recommendations

Makes bespoke experiences truly intelligent by incorporating:
- Regional gift-giving norms (Midwest practicality vs South personalization)
- Local culture and preferences (Austin live music vs Indianapolis sports)
- Things to avoid by region (NYC touristy crap, Boston Yankees gear)
- Preferred local retailers and experiences
- Demographic + geographic synthesis (25F Austin ≠ 25F Indianapolis)

NEIGHBORHOOD GRANULARITY (Phase 1.5 enhancement):
- Indianapolis: Single city profile (culturally homogeneous)
- NYC: 20+ neighborhood profiles (massive cultural diversity)
- Chicago: 15+ neighborhood profiles (North/South/West divide)
- LA: 15+ neighborhood profiles (Westside/Valley/Beach splits)

For other cities: Single city profile sufficient (Nashville, Seattle, etc.)

This is the intelligence layer that makes someone go "oh wow, this AI actually GETS my city."

Author: Chad + Claude
Date: February 2026
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ================================================================================
# REGIONAL PROFILES - Deep cultural context by region
# ================================================================================

REGIONAL_PROFILES = {
    'midwest': {
        'states': ['indiana', 'illinois', 'ohio', 'michigan', 'wisconsin', 'minnesota', 'iowa', 'missouri', 'kansas', 'nebraska', 'south dakota', 'north dakota'],
        'gift_norms': {
            'practical_appreciated': True,
            'personalization_preference': 'moderate',
            'experience_vs_thing': 'balanced',
            'budget_consciousness': 'high',
            'quality_over_flash': True,
            'description': 'Midwesterners appreciate practical gifts that will actually be used. Functional beats flashy. Quality brands like Carhartt, Coleman, and North Face resonate. Experiences are growing but physical gifts still dominant.'
        },
        'cultural_traits': [
            'Humble, no-nonsense approach to luxury',
            'Value longevity and durability over trends',
            'Appreciate local/regional brands',
            'Community-oriented (group experiences popular)',
            'Seasonal activities deeply ingrained (ice fishing, tailgating)',
        ],
        'avoid': [
            'Overtly flashy designer items without function',
            'Overly trendy items that scream coastal',
            'Anything that looks like it\'s trying too hard',
            'West Coast wellness fads (adapt carefully)',
        ],
        'preferred_retailers': ['Target', 'Menards', 'Fleet Farm', 'Meijer', 'local specialty shops'],
        'style_notes': 'Practical comfort over fashion-forward. Plaid, denim, functional outerwear. Carhartt is a love language here.'
    },

    'south': {
        'states': ['texas', 'oklahoma', 'arkansas', 'louisiana', 'mississippi', 'alabama', 'tennessee', 'kentucky', 'georgia', 'florida', 'south carolina', 'north carolina', 'virginia', 'west virginia'],
        'gift_norms': {
            'practical_appreciated': False,
            'personalization_preference': 'very high',
            'experience_vs_thing': 'things',
            'budget_consciousness': 'moderate',
            'quality_over_flash': False,
            'description': 'Southerners LOVE personalized gifts. Monograms, custom items, engraving - it\'s a whole culture. Hospitality-focused (serving pieces, barware). Presentation matters (pretty wrapping, thoughtful notes).'
        },
        'cultural_traits': [
            'Monograms and personalization are HUGE',
            'Hospitality culture (serving pieces, entertaining)',
            'College sports loyalty (SEC pride)',
            'Beauty and grooming culture strong',
            'Faith and family prominent (but don\'t assume)',
        ],
        'avoid': [
            'Generic impersonal items',
            'Anything that could be seen as "cheap"',
            'Political/religious assumptions',
            'Rival SEC team gear (verify first)',
        ],
        'preferred_retailers': ['Dillard\'s', 'Belk', 'local boutiques', 'Monogrammed items shops', 'Things Remembered'],
        'style_notes': 'Preppy Southern style: Vineyard Vines, Lilly Pulitzer, pearls, monograms. Beauty culture strong (Sephora, Ulta popular).'
    },

    'west_coast': {
        'states': ['california', 'oregon', 'washington', 'nevada', 'hawaii', 'alaska'],
        'gift_norms': {
            'practical_appreciated': True,
            'personalization_preference': 'low',
            'experience_vs_thing': 'experiences',
            'budget_consciousness': 'low',
            'quality_over_flash': True,
            'description': 'West Coast strongly prefers experiences over things. Sustainability matters. Wellness culture (yoga, hiking, organic). Tech-forward (gadgets welcome). Higher price tolerance for "investment pieces."'
        },
        'cultural_traits': [
            'Experience gifts >>> physical gifts',
            'Sustainability and eco-consciousness valued',
            'Wellness culture (yoga, meditation, organic)',
            'Tech-savvy and early adopter',
            'Outdoor recreation is lifestyle, not hobby',
            'Food culture sophisticated (farm-to-table, artisanal)',
        ],
        'avoid': [
            'Fast fashion (sustainability concerns)',
            'Generic mass-market brands',
            'Anything overly traditional or conservative',
            'Items that aren\'t eco-friendly (packaging matters)',
        ],
        'preferred_retailers': ['REI', 'Patagonia', 'Whole Foods', 'local artisan shops', 'farmers markets'],
        'style_notes': 'Athleisure dominant. Lululemon, Allbirds, Patagonia. Effortless cool over try-hard. Natural fibers, earth tones.'
    },

    'northeast': {
        'states': ['new york', 'pennsylvania', 'new jersey', 'massachusetts', 'connecticut', 'rhode island', 'maine', 'new hampshire', 'vermont', 'delaware', 'maryland'],
        'gift_norms': {
            'practical_appreciated': True,
            'personalization_preference': 'moderate',
            'experience_vs_thing': 'experiences',
            'budget_consciousness': 'moderate',
            'quality_over_flash': True,
            'description': 'Northeasterners appreciate thoughtfulness over price tag. Cultural experiences (theater, museums, dining) highly valued. Quality and authenticity matter more than trends. NYC drives luxury, but rest of region more practical.'
        },
        'cultural_traits': [
            'Cultural sophistication valued',
            'Experience gifts popular (shows, dining, museums)',
            'Sports loyalty INTENSE (team gear must be verified)',
            'Food culture strong (craft, artisanal, ethnic)',
            'Education and intellectualism respected',
            'Seasonal traditions deep (fall foliage, winter sports)',
        ],
        'avoid': [
            'Touristy NYC crap ("I ❤️ NY" shirts)',
            'Rival sports team gear (Yankees/Red Sox rivalry is REAL)',
            'Generic mall brands',
            'Anything that could be seen as unsophisticated',
        ],
        'preferred_retailers': ['local bookstores', 'boutique shops', 'farmers markets', 'specialty food shops'],
        'style_notes': 'NYC = fashion-forward, polished. Rest of region = preppy, classic (J.Crew, LL Bean). Urban vs rural divide significant.'
    },
}


# ================================================================================
# CITY-SPECIFIC INTELLIGENCE - Deep local knowledge
# ================================================================================

CITY_PROFILES = {
    # MIDWEST CITIES
    'indianapolis': {
        'region': 'midwest',
        'state': 'indiana',
        'vibe': 'Midwest friendly, sports-focused, understated',
        'signature_experiences': [
            'Indianapolis 500 (May)',
            'Mass Ave dining and theater',
            'Pacers games (NBA)',
            'Colts games (NFL)',
            'Indianapolis Motor Speedway Museum',
            'Newfields (art museum with gardens)',
            'Broad Ripple nightlife',
            'Fountain Square arts district',
        ],
        'local_culture': {
            'sports': 'Huge. Pacers, Colts, Indy 500 are religion. Racing culture runs deep.',
            'food': 'Farm-to-table growing. Comfort food strong. Craft beer scene solid.',
            'arts': 'Underrated theater scene. Mass Ave cultural district thriving.',
            'outdoor': 'Parks and trails popular. Monon Trail, White River State Park.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Broad Ripple/Fountain Square scene. Yoga studios, boutique fitness, brunch culture. Not as coastal as Austin but growing wellness scene.',
            'young_male_25_35': 'Sports bars, craft breweries, Pacers/Colts games. Racing culture.',
            'female_35_50': 'Carmel/Fishers suburbs. Book clubs, boutique shopping, wine culture.',
            'male_35_50': 'Golf, racing, bourbon, grilling culture.',
        },
        'avoid': [
            'Generic racing merch (they\'ve seen it all)',
            'Touristy Indy 500 stuff unless they\'re genuinely into racing',
            'Chicago sports gear',
        ],
        'preferred_local': ['Silver in the City (boutique)', 'Mass Ave shops', 'Farmers markets', 'Local breweries'],
    },

    'chicago': {
        'region': 'midwest',
        'state': 'illinois',
        'vibe': 'Big city energy, Midwest roots, deep cultural pride',
        'signature_experiences': [
            'Cubs/White Sox games (know which side they\'re on)',
            'Bulls/Blackhawks games',
            'Chicago Symphony Orchestra',
            'Second City comedy',
            'Architecture boat tour',
            'Deep-dish pizza tour (Lou Malnati\'s, Pequod\'s)',
            'Art Institute of Chicago',
            'Riverwalk dining',
        ],
        'local_culture': {
            'sports': 'INTENSE team loyalty. Cubs vs Sox is a lifestyle divide. Bears, Bulls, Blackhawks all passionate.',
            'food': 'World-class. Deep dish, Italian beef, hot dogs (NO KETCHUP). Michelin-starred scene.',
            'arts': 'Major cultural hub. Theater, comedy, museums, music.',
            'outdoor': 'Lakefront culture. Beaches, bike paths, winter sports.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Wicker Park/Logan Square vibes. Brunch, boutique fitness, music venues, artisan coffee.',
            'young_male_25_35': 'Sports bars, craft beer, live music, Cubs games.',
            'female_35_50': 'Suburban North Shore or city sophisticate. Cultural events, fine dining, shopping.',
            'male_35_50': 'Golf, sports loyalty, bourbon/whiskey culture, grilling.',
        },
        'avoid': [
            'Green Bay Packers gear (mortal enemy)',
            'St. Louis Cardinals gear (Cubs fans)',
            'White Sox gear if they\'re Cubs fans (and vice versa)',
            'Deep dish from tourist traps',
        ],
        'preferred_local': ['Local boutiques on Armitage', 'Randolph Street Market', 'Chicago Athletic Association', 'Binny\'s (liquor)'],

        # NEIGHBORHOOD GRANULARITY - Chicago has massive North/South/West cultural divides
        'neighborhoods': {
            # NORTH SIDE
            'lincoln_park': {
                'area': 'north_side',
                'vibe': 'Affluent young professionals, lakefront, zoo, DePaul area',
                'demographics': 'Young professionals, DePaul students, wealthy families',
                'best_for': ['lakefront dining', 'wine bars', 'boutique shopping on Armitage', 'zoo memberships'],
                'avoid': 'Anything too grungy or South Side, budget gifts',
                'gift_style': 'Upscale casual, lakefront lifestyle, trendy but refined',
                'price_point': '$$$',
            },
            'wicker_park': {
                'area': 'north_side',
                'vibe': 'Hipster central, vintage shops, live music, craft cocktails',
                'demographics': 'Artists, musicians, creative professionals, 25-35',
                'best_for': ['live music venues', 'vintage shopping', 'craft cocktail bars', 'record stores'],
                'avoid': 'Corporate chains, anything too mainstream',
                'gift_style': 'Artisan, indie, vinyl culture, vintage aesthetic',
                'price_point': '$$-$$$',
            },
            'logan_square': {
                'area': 'north_side',
                'vibe': 'Arts scene, breweries, Boulevard culture, hipster overflow',
                'demographics': 'Young creatives, artists, brewery enthusiasts',
                'best_for': ['brewery tours', 'art gallery events', 'Boulevard dining', 'live music'],
                'avoid': 'Anything too polished or corporate',
                'gift_style': 'Artisan beer culture, local art, creative community',
                'price_point': '$$',
            },
            'lakeview': {
                'area': 'north_side',
                'vibe': 'Cubs territory, sports bars, young professionals, Boystown LGBTQ+',
                'demographics': 'Young professionals, Cubs fans, LGBTQ+ community',
                'best_for': ['Cubs tickets', 'sports bar vouchers', 'nightlife experiences', 'Pride events'],
                'avoid': 'White Sox gear, anything anti-sports',
                'gift_style': 'Sports-focused, nightlife, LGBTQ+ inclusive',
                'price_point': '$$-$$$',
            },
            'wrigleyville': {
                'area': 'north_side',
                'vibe': 'Cubs central, sports bars, game day culture',
                'demographics': 'Cubs superfans, young sports enthusiasts',
                'best_for': ['Cubs tickets', 'sports bar crawls', 'game day experiences'],
                'avoid': 'White Sox gear (mortal enemy territory)',
                'gift_style': 'Cubs-centric, sports bar culture, game day',
                'price_point': '$$',
            },
            'andersonville': {
                'area': 'north_side',
                'vibe': 'Swedish heritage, LGBTQ+ friendly, indie shops, cozy cafes',
                'demographics': 'LGBTQ+ community, Scandinavian heritage, indie shop lovers',
                'best_for': ['indie bookstores', 'Swedish bakeries', 'boutique shopping', 'theater'],
                'avoid': 'Corporate chains, anything too mainstream',
                'gift_style': 'Independent, community-oriented, Scandinavian touches',
                'price_point': '$$',
            },

            # DOWNTOWN/CENTRAL
            'the_loop': {
                'area': 'downtown',
                'vibe': 'Business district, theater, architecture, avoid for gift experiences',
                'demographics': 'Office workers, tourists, theater-goers',
                'best_for': ['theater tickets', 'architecture tours', 'Symphony Center'],
                'avoid': 'Assumes they hang out here (they don\'t, they work here)',
                'gift_style': 'Cultural experiences only, not lifestyle gifts',
                'price_point': '$$$',
            },
            'river_north': {
                'area': 'downtown',
                'vibe': 'Galleries, upscale dining, nightlife, young professionals',
                'demographics': 'Affluent young professionals, art collectors, foodies',
                'best_for': ['gallery hopping', 'Michelin dining', 'nightlife', 'trendy restaurants'],
                'avoid': 'Anything too casual or budget',
                'gift_style': 'Upscale, art-focused, fine dining experiences',
                'price_point': '$$$$',
            },
            'west_loop': {
                'area': 'downtown',
                'vibe': 'Restaurant row, Michelin stars, trendy, converted warehouses',
                'demographics': 'Foodies, young professionals, culinary enthusiasts',
                'best_for': ['Michelin restaurant vouchers', 'food tours', 'cooking classes', 'trendy brunch'],
                'avoid': 'Chain restaurants, anything not food-focused',
                'gift_style': 'Culinary-centric, foodie culture, Michelin-level',
                'price_point': '$$$$',
            },

            # SOUTH SIDE
            'hyde_park': {
                'area': 'south_side',
                'vibe': 'University of Chicago, intellectual, Museum of Science, historic',
                'demographics': 'Academics, students, museum-goers, intellectuals',
                'best_for': ['Museum of Science passes', 'bookstore gift cards', 'university events', 'intellectual talks'],
                'avoid': 'Anything anti-intellectual, sports bar culture',
                'gift_style': 'Academic, museum culture, thoughtful/intellectual',
                'price_point': '$$',
            },
            'pilsen': {
                'area': 'south_side',
                'vibe': 'Mexican culture, murals, arts district, gentrifying',
                'demographics': 'Mexican-American community, artists, young creatives',
                'best_for': ['mural tours', 'Mexican cultural events', 'art galleries', 'authentic Mexican dining'],
                'avoid': 'Gentrification-coded gifts, corporate chains',
                'gift_style': 'Authentic Mexican culture, street art, community art',
                'price_point': '$-$$',
            },
            'bronzeville': {
                'area': 'south_side',
                'vibe': 'Historic Black neighborhood, jazz history, cultural renaissance',
                'demographics': 'African-American community, jazz enthusiasts, history buffs',
                'best_for': ['jazz club experiences', 'historic tours', 'soul food dining', 'cultural events'],
                'avoid': 'Gentrification insensitivity, ignoring cultural history',
                'gift_style': 'Jazz culture, historic Black heritage, soul food',
                'price_point': '$$',
            },

            # WEST SIDE
            'humboldt_park': {
                'area': 'west_side',
                'vibe': 'Puerto Rican culture, Paseo Boricua, community-oriented',
                'demographics': 'Puerto Rican community, families, artists',
                'best_for': ['Puerto Rican cultural events', 'local festivals', 'authentic dining'],
                'avoid': 'Gentrification insensitivity, ignoring cultural roots',
                'gift_style': 'Puerto Rican culture, community events, authentic',
                'price_point': '$-$$',
            },
            'ukrainian_village': {
                'area': 'west_side',
                'vibe': 'Hipster overlap with Wicker Park, vintage shops, dive bars',
                'demographics': 'Young creatives, artists, Ukrainian heritage community',
                'best_for': ['vintage shopping', 'dive bars', 'ethnic restaurants', 'indie culture'],
                'avoid': 'Corporate chains, anything too polished',
                'gift_style': 'Vintage, dive bar culture, indie aesthetic',
                'price_point': '$$',
            },
        },
    },

    # SOUTH CITIES
    'austin': {
        'region': 'south',
        'state': 'texas',
        'vibe': 'Keep Austin Weird - creative, liberal oasis in Texas, music-obsessed',
        'signature_experiences': [
            'Live music (6th Street, Rainey Street, ACL Live)',
            'Austin City Limits Music Festival (October)',
            'SXSW (March)',
            'UT football games',
            'Barton Springs Pool',
            'Food truck culture',
            'Lady Bird Lake kayaking/paddleboarding',
            'Zilker Park',
            'Texas Hill Country wine tours',
        ],
        'local_culture': {
            'music': 'THE defining trait. Live music every night. "Live Music Capital of the World."',
            'food': 'Tacos, BBQ, food trucks. Breakfast tacos are life. Queso is a food group.',
            'outdoor': 'Year-round outdoor lifestyle. Hiking, swimming, paddleboarding.',
            'tech': 'Major tech hub. Startup culture. Young, educated population.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Yoga/pilates, live music, food trucks, outdoor fitness, brunching. West Coast vibes with Texas warmth.',
            'young_male_25_35': 'Live music, craft beer, BBQ, outdoor sports, tech culture.',
            'female_35_50': 'Hill Country wine tours, farm-to-table dining, boutique shopping, wellness.',
            'male_35_50': 'Golf, BBQ, UT sports, bourbon, lake life.',
        },
        'avoid': [
            'Generic Texas stereotypes (not everyone wears cowboy boots)',
            'Overly corporate/traditional gifts (this is "Keep Austin Weird")',
            'Houston/Dallas sports gear',
        ],
        'preferred_local': ['South Congress boutiques', 'Whole Foods flagship', 'Local coffee roasters', 'Farmers markets', 'Allens Boots'],
    },

    'nashville': {
        'region': 'south',
        'state': 'tennessee',
        'vibe': 'Music City - country music heritage, bachelorette party central, Southern hospitality',
        'signature_experiences': [
            'Country music venues (Grand Ole Opry, Ryman Auditorium, Bluebird Cafe)',
            'Broadway honky-tonks',
            'Whiskey tastings (Jack Daniel\'s, George Dickel)',
            'Predators games (NHL)',
            'Titans games (NFL)',
            'Franklin/Brentwood boutique shopping',
            'Hot chicken tour (Hattie B\'s, Prince\'s)',
            'Percy Warner Park hiking',
        ],
        'local_culture': {
            'music': 'Country music history runs deep. Live music nightly. Songwriters culture.',
            'food': 'Hot chicken, meat-and-three, Southern comfort. Food scene exploding.',
            'sports': 'Predators fanbase passionate. Titans growing.',
            'growth': 'Massive influx of young professionals. Bachelorette party capital.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Broadway scene, rooftop bars, boutique shopping (12 South), barre/yoga studios, brunch.',
            'young_male_25_35': 'Honky-tonks, whiskey, Predators/Titans games, golf, BBQ.',
            'female_35_50': 'Franklin boutiques, wine culture, country music, Southern hospitality.',
            'male_35_50': 'Golf, whiskey, BBQ, country music, Titans/Predators.',
        },
        'avoid': [
            'Pop/rock music without country connection (read the room)',
            'Anything that disrespects country music heritage',
            'Memphis BBQ claims (different styles)',
        ],
        'preferred_local': ['Imogene + Willie (denim)', '12 South boutiques', 'Franklin shops', 'Local hot chicken joints'],
    },

    # WEST COAST CITIES
    'los_angeles': {
        'region': 'west_coast',
        'state': 'california',
        'vibe': 'Entertainment capital, health-conscious, status-aware, sprawling diversity',
        'signature_experiences': [
            'Hollywood Bowl concerts',
            'Lakers/Clippers/Dodgers games',
            'Beach clubs (Malibu, Venice, Santa Monica)',
            'Hiking (Runyon Canyon, Griffith Observatory)',
            'Food scene (Korean BBQ, taco trucks, omakase)',
            'Getty Center/LACMA',
            'Comedy clubs',
            'Disneyland',
        ],
        'local_culture': {
            'entertainment': 'Industry town. Screenings, premieres, celebrity sightings normal.',
            'health': 'Wellness culture STRONG. Juice bars, yoga studios, pilates everywhere.',
            'food': 'Insanely diverse. Every cuisine imaginable. Food trucks to Michelin stars.',
            'outdoor': 'Year-round outdoor lifestyle. Beaches, hiking, biking.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Yoga/pilates, smoothie bowls, beach days, boutique fitness (SoulCycle), influencer culture.',
            'young_male_25_35': 'Surfing, hiking, craft beer, Lakers games, entertainment industry.',
            'female_35_50': 'Wellness retreats, wine culture, fine dining, boutique shopping (Melrose, Abbott Kinney).',
            'male_35_50': 'Golf, wine, Lakers/Dodgers, grilling, tech/entertainment.',
        },
        'avoid': [
            'Touristy Hollywood stuff (Walk of Fame is for tourists)',
            'Anaheim/San Francisco sports gear',
            'Anything not health-conscious (optics matter here)',
        ],
        'preferred_local': ['Erewhon (luxury grocery)', 'Melrose boutiques', 'Abbott Kinney shops', 'Rose Bowl Flea Market'],

        # NEIGHBORHOOD GRANULARITY - LA is massive with distinct Westside/Valley/Beach/East splits
        'neighborhoods': {
            # WESTSIDE
            'santa_monica': {
                'area': 'westside',
                'vibe': 'Beach culture, pier, tourist-friendly, active lifestyle, wellness',
                'demographics': 'Health-conscious professionals, beach lovers, tourists',
                'best_for': ['beach activities', 'pier experiences', 'yoga classes', 'farmers market', 'bike rentals'],
                'avoid': 'Anything sedentary, indoor-only experiences',
                'gift_style': 'Active lifestyle, wellness, beach culture, outdoor fitness',
                'price_point': '$$$',
            },
            'venice': {
                'area': 'westside',
                'vibe': 'Bohemian, beach, skate culture, artsy, cannabis-friendly, eclectic',
                'demographics': 'Artists, skaters, bohemian creatives, beach enthusiasts',
                'best_for': ['skate experiences', 'boardwalk culture', 'art galleries', 'Abbot Kinney shopping', 'beach yoga'],
                'avoid': 'Corporate gifts, anything too buttoned-up',
                'gift_style': 'Bohemian, skate culture, art-focused, cannabis-friendly',
                'price_point': '$$-$$$',
            },
            'brentwood': {
                'area': 'westside',
                'vibe': 'Affluent, quiet, farmers market, family-oriented, celebrities',
                'demographics': 'Wealthy families, celebrities, health-conscious professionals',
                'best_for': ['farmers market vouchers', 'upscale dining', 'wellness retreats', 'family experiences'],
                'avoid': 'Anything too flashy, paparazzi-attracting',
                'gift_style': 'Understated luxury, wellness, family-friendly, organic',
                'price_point': '$$$$',
            },
            'culver_city': {
                'area': 'westside',
                'vibe': 'Arts district, galleries, studio adjacent, revitalized downtown',
                'demographics': 'Entertainment industry workers, artists, young professionals',
                'best_for': ['gallery hopping', 'indie dining', 'Platform shopping', 'art house cinema'],
                'avoid': 'Anything too mainstream',
                'gift_style': 'Arts-focused, indie culture, entertainment industry adjacent',
                'price_point': '$$$',
            },

            # CENTRAL
            'silver_lake': {
                'area': 'central',
                'vibe': 'Hipster, indie music, coffee culture, LGBTQ+ friendly, creative',
                'demographics': 'Musicians, artists, LGBTQ+ community, creatives 25-40',
                'best_for': ['indie music venues', 'coffee shops', 'vintage shopping', 'Reservoir hikes', 'record stores'],
                'avoid': 'Corporate chains, anything too mainstream',
                'gift_style': 'Indie music, artisan coffee, vintage aesthetic, LGBTQ+ inclusive',
                'price_point': '$$-$$$',
            },
            'echo_park': {
                'area': 'central',
                'vibe': 'Hipster overflow from Silver Lake, gentrifying, lake culture, tacos',
                'demographics': 'Young creatives, gentrifiers, Latino community, artists',
                'best_for': ['Echo Park Lake activities', 'taco tours', 'dive bars', 'indie music'],
                'avoid': 'Gentrification insensitivity, corporate gifts',
                'gift_style': 'Hipster-adjacent, taco culture, lake life, indie',
                'price_point': '$-$$',
            },
            'los_feliz': {
                'area': 'central',
                'vibe': 'Chill, Griffith Observatory area, indie theaters, relaxed cool',
                'demographics': 'Creative professionals, film enthusiasts, dog owners',
                'best_for': ['Griffith Observatory', 'indie theaters', 'Vermont Ave dining', 'hiking trails'],
                'avoid': 'Anything too try-hard or corporate',
                'gift_style': 'Effortless cool, film culture, outdoor lifestyle, chill',
                'price_point': '$$-$$$',
            },
            'downtown_la': {
                'area': 'central',
                'vibe': 'Arts District, breweries, lofts, Grand Central Market, revitalized',
                'demographics': 'Young professionals, artists, loft dwellers, foodies',
                'best_for': ['Grand Central Market', 'Arts District galleries', 'brewery tours', 'rooftop bars'],
                'avoid': 'Assumes they avoid it (many live here now)',
                'gift_style': 'Urban revival, arts-focused, brewery culture, loft lifestyle',
                'price_point': '$$-$$$',
            },

            # HOLLYWOOD/MID-CITY
            'hollywood': {
                'area': 'hollywood',
                'vibe': 'Tourist avoid zone, but historic theaters okay, industry adjacent',
                'demographics': 'Industry workers, tourists (locals avoid Walk of Fame)',
                'best_for': ['Hollywood Bowl', 'historic theaters', 'industry events'],
                'avoid': 'Walk of Fame tourist traps, generic Hollywood merch',
                'gift_style': 'Entertainment industry experiences only, avoid tourist crap',
                'price_point': '$$$',
            },
            'west_hollywood': {
                'area': 'hollywood',
                'vibe': 'LGBTQ+ culture, nightlife, design district, trendy restaurants',
                'demographics': 'LGBTQ+ community, nightlife enthusiasts, design lovers',
                'best_for': ['nightlife experiences', 'design district shopping', 'LGBTQ+ events', 'trendy dining'],
                'avoid': 'Conservative gifts, anything not LGBTQ+ inclusive',
                'gift_style': 'LGBTQ+ culture, nightlife, design-forward, trendy',
                'price_point': '$$$-$$$$',
            },
            'fairfax': {
                'area': 'mid_city',
                'vibe': 'Jewish community, streetwear culture, The Grove, Canter\'s Deli',
                'demographics': 'Streetwear enthusiasts, Jewish community, young shoppers',
                'best_for': ['streetwear shopping', 'The Grove', 'Canter\'s Deli', 'Fairfax flea market'],
                'avoid': 'Ignoring cultural significance, corporate chains',
                'gift_style': 'Streetwear culture, Jewish heritage, shopping district',
                'price_point': '$$-$$$',
            },

            # VALLEY
            'studio_city': {
                'area': 'valley',
                'vibe': 'Suburban, family-friendly, less hip than Westside, studio adjacent',
                'demographics': 'Families, entertainment industry workers, suburban professionals',
                'best_for': ['family dining', 'studio tours', 'Ventura Blvd shopping', 'golf'],
                'avoid': 'Assuming they\'re as hip as Westside (different vibe)',
                'gift_style': 'Family-oriented, suburban comfort, less trendy',
                'price_point': '$$',
            },
            'sherman_oaks': {
                'area': 'valley',
                'vibe': 'Affluent Valley, malls, family-oriented, suburban luxury',
                'demographics': 'Affluent families, suburban professionals',
                'best_for': ['Westfield Fashion Square', 'Ventura Blvd dining', 'golf', 'family activities'],
                'avoid': 'Westside snobbery (Valley pride is real)',
                'gift_style': 'Suburban luxury, family-friendly, mall culture',
                'price_point': '$$$',
            },

            # SOUTH BAY
            'manhattan_beach': {
                'area': 'south_bay',
                'vibe': 'Beach volleyball, upscale, athletic culture, laid-back luxury',
                'demographics': 'Athletic professionals, beach volleyball players, wealthy beach lovers',
                'best_for': ['beach volleyball', 'upscale beach dining', 'Strand bike rides', 'beach clubs'],
                'avoid': 'Sedentary gifts, anything not beach-focused',
                'gift_style': 'Athletic beach culture, upscale casual, volleyball',
                'price_point': '$$$$',
            },
            'hermosa_beach': {
                'area': 'south_bay',
                'vibe': 'Younger beach crowd, bars, volleyball, more casual than Manhattan',
                'demographics': 'Young professionals, beach party crowd, surfers',
                'best_for': ['beach bars', 'volleyball', 'pier activities', 'nightlife'],
                'avoid': 'Family-oriented gifts (younger party vibe)',
                'gift_style': 'Beach party culture, volleyball, casual bars',
                'price_point': '$$$',
            },

            # EAST LA
            'pasadena': {
                'area': 'east_la',
                'vibe': 'Old money, Rose Bowl, museums, conservative, historic',
                'demographics': 'Wealthy families, museum-goers, Rose Bowl fans, retirees',
                'best_for': ['Norton Simon Museum', 'Rose Bowl events', 'Old Town Pasadena', 'Huntington Library'],
                'avoid': 'Anything too edgy or nightlife-focused',
                'gift_style': 'Traditional, cultural institutions, family-friendly, historic',
                'price_point': '$$$-$$$$',
            },
            'highland_park': {
                'area': 'east_la',
                'vibe': 'Gentrifying, hipster, craftsman homes, artisan shops, York Blvd',
                'demographics': 'Gentrifiers, artists, young creatives, Latino community',
                'best_for': ['York Blvd shopping', 'coffee shops', 'vintage stores', 'arts scene'],
                'avoid': 'Gentrification insensitivity, corporate chains',
                'gift_style': 'Artisan, gentrification-aware, vintage, coffee culture',
                'price_point': '$$',
            },
        },
    },

    'san_francisco': {
        'region': 'west_coast',
        'state': 'california',
        'vibe': 'Tech hub, progressive, foodie culture, expensive, fog',
        'signature_experiences': [
            'Warriors games (NBA)',
            '49ers games (NFL)',
            'Wine country tours (Napa, Sonoma)',
            'Ferry Building farmers market',
            'Michelin-starred dining scene',
            'Mission murals and food',
            'Alcatraz tours',
            'Hiking (Marin Headlands, Mt. Tam)',
        ],
        'local_culture': {
            'tech': 'Silicon Valley influence massive. Startup culture. High earners.',
            'food': 'World-class. Farm-to-table pioneer. Wine culture sophisticated.',
            'progressive': 'Very liberal. Social consciousness high.',
            'outdoor': 'Despite fog, outdoor culture strong. Hiking, biking, sailing.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Yoga, matcha lattes, farmers markets, hiking, boutique fitness, sustainability-focused.',
            'young_male_25_35': 'Tech culture, craft beer, Warriors games, cycling, startup scene.',
            'female_35_50': 'Wine country, fine dining, yoga retreats, boutique shopping, wellness.',
            'male_35_50': 'Wine, golf, Warriors/49ers, sailing, tech.',
        },
        'avoid': [
            'LA/Oakland sports gear',
            'Anything not sustainable/eco-friendly',
            'Fast fashion or mass-market brands',
            'Political conservatism',
        ],
        'preferred_local': ['Ferry Building shops', 'Hayes Valley boutiques', 'Mission artisan shops', 'Bi-Rite Market'],
    },

    'seattle': {
        'region': 'west_coast',
        'state': 'washington',
        'vibe': 'Coffee culture, tech-forward, outdoorsy despite rain, grunge heritage',
        'signature_experiences': [
            'Pike Place Market',
            'Seahawks games (12th Man culture)',
            'Mariners games',
            'Coffee culture (origin of Starbucks but way beyond that)',
            'Hiking (Cascades, Olympics, Mt. Rainier)',
            'San Juan Islands',
            'Music scene (grunge history, indie venues)',
            'Capitol Hill nightlife',
        ],
        'local_culture': {
            'coffee': 'Coffee is SERIOUS. Third-wave roasters everywhere. Don\'t mention Starbucks.',
            'tech': 'Amazon, Microsoft headquarters. Tech wealth.',
            'outdoor': 'Despite rain, outdoor culture HUGE. REI started here. Hiking, skiing, kayaking.',
            'music': 'Grunge heritage (Nirvana, Pearl Jam). Indie scene strong.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Coffee culture, hiking, yoga, farmers markets, indie music, sustainability.',
            'young_male_25_35': 'Craft beer, hiking, Seahawks games, tech culture, coffee.',
            'female_35_50': 'Wine (Woodinville), outdoor adventures, farm-to-table dining, yoga.',
            'male_35_50': 'Seahawks, golf, wine, hiking, tech, fishing.',
        },
        'avoid': [
            'Starbucks gift cards (locals are coffee snobs)',
            '49ers/Rams gear (NFC West rivals)',
            'Anything flashy or showy (Seattle Freeze is real)',
        ],
        'preferred_local': ['Pike Place Market', 'Capitol Hill boutiques', 'REI flagship', 'Local coffee roasters'],
    },

    # NORTHEAST CITIES
    'new_york': {
        'region': 'northeast',
        'state': 'new york',
        'vibe': 'Fast-paced, culturally diverse, sophisticated, expensive, never sleeps',
        'signature_experiences': [
            'Broadway shows',
            'Yankees/Mets games (know which side)',
            'Knicks/Nets/Rangers games',
            'Metropolitan Museum, MoMA, Whitney',
            'Restaurant Week and Michelin dining',
            'Jazz clubs (Village Vanguard, Blue Note)',
            'Comedy clubs',
            'Central Park activities',
        ],
        'local_culture': {
            'culture': 'Unparalleled. Theater, museums, music, food - all world-class.',
            'food': 'Every cuisine. From $1 pizza to Per Se. Food IS culture here.',
            'pace': 'Fast. Efficient. Don\'t waste time.',
            'diversity': 'Every culture represented. Massive range of experiences.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Brunch culture, Broadway, boutique fitness (SoulCycle, Barry\'s), rooftop bars, museums.',
            'young_male_25_35': 'Sports bars, craft cocktails, Yankees/Knicks games, food scene, nightlife.',
            'female_35_50': 'Theater, fine dining, museums, shopping (SoHo, Madison Ave), wine culture.',
            'male_35_50': 'Yankees/Knicks, fine dining, jazz clubs, whiskey, golf.',
        },
        'avoid': [
            'Touristy Times Square crap ("I ❤️ NY" shirts)',
            'Boston Red Sox gear (rivalry is DEEP)',
            'Mets gear if they\'re Yankees fans (and vice versa)',
            'Chain restaurants',
        ],
        'preferred_local': ['SoHo boutiques', 'Chelsea Market', 'Brooklyn artisan shops', 'Union Square Greenmarket'],

        # NEIGHBORHOOD GRANULARITY - NYC is too diverse for single city treatment
        'neighborhoods': {
            # MANHATTAN
            'upper_west_side': {
                'borough': 'manhattan',
                'vibe': 'Family-friendly, intellectual, museum culture, Lincoln Center',
                'demographics': 'Families, affluent professionals, retirees',
                'best_for': ['museum memberships', 'Lincoln Center shows', 'Zabar\'s gourmet food', 'bookstore gift cards'],
                'avoid': 'Anything too edgy or nightlife-focused',
                'gift_style': 'Thoughtful, cultured, educational, family-oriented',
                'price_point': '$$$',
            },
            'upper_east_side': {
                'borough': 'manhattan',
                'vibe': 'Affluent, traditional, Met Museum, gallery hopping, old money',
                'demographics': 'Wealthy professionals, old money families, museum members',
                'best_for': ['gallery experiences', 'Madison Ave shopping', 'fine dining', 'museum fundraiser events'],
                'avoid': 'Anything too casual, downtown hipster aesthetic',
                'gift_style': 'Classic, refined, luxury brands, traditional elegance',
                'price_point': '$$$$',
            },
            'midtown': {
                'borough': 'manhattan',
                'vibe': 'Tourist zone, corporate, avoid for locals except Theater District',
                'demographics': 'Office workers, tourists (locals avoid)',
                'best_for': ['Broadway shows', 'rockefeller center experiences'],
                'avoid': 'Generic tourist gifts, chain restaurants',
                'gift_style': 'Theater/culture experiences only, otherwise avoid',
                'price_point': '$$$',
            },
            'chelsea': {
                'borough': 'manhattan',
                'vibe': 'Art galleries, High Line, LGBTQ+ culture, nightlife, trendy',
                'demographics': 'Young professionals, LGBTQ+ community, art lovers',
                'best_for': ['gallery tours', 'High Line experiences', 'nightlife vouchers', 'contemporary art'],
                'avoid': 'Conservative or traditional gifts',
                'gift_style': 'Modern, artistic, inclusive, nightlife-oriented',
                'price_point': '$$$',
            },
            'west_village': {
                'borough': 'manhattan',
                'vibe': 'Bohemian history, jazz clubs, intimate dining, charming streets',
                'demographics': 'Affluent creatives, music lovers, foodies',
                'best_for': ['jazz club tickets', 'intimate restaurant vouchers', 'record shop gift cards', 'indie bookstores'],
                'avoid': 'Corporate chains, anything too mainstream',
                'gift_style': 'Artistic, cultured, intimate, vintage-inspired',
                'price_point': '$$$$',
            },
            'greenwich_village': {
                'borough': 'manhattan',
                'vibe': 'Bohemian, NYU students, comedy clubs, historic counterculture',
                'demographics': 'Students, artists, comedy fans, historic bohemians',
                'best_for': ['comedy club tickets', 'record stores', 'vintage shops', 'indie theater'],
                'avoid': 'Corporate or overly polished gifts',
                'gift_style': 'Eclectic, vintage, countercultural, artistic',
                'price_point': '$$',
            },
            'east_village': {
                'borough': 'manhattan',
                'vibe': 'Edgy, dive bars, music venues, young creative, punk history',
                'demographics': 'Young creatives, musicians, artists, nightlife crowd',
                'best_for': ['live music venues', 'dive bar crawls', 'vintage clothing', 'tattoo vouchers'],
                'avoid': 'Anything corporate, uptown polish, chain stores',
                'gift_style': 'Edgy, alternative, DIY aesthetic, music-focused',
                'price_point': '$$',
            },
            'soho': {
                'borough': 'manhattan',
                'vibe': 'Shopping mecca, upscale dining, trendy, cast-iron architecture',
                'demographics': 'Shoppers, fashion-forward professionals, tourists',
                'best_for': ['boutique shopping', 'trendy restaurants', 'designer brands', 'art galleries'],
                'avoid': 'Anything too casual or budget',
                'gift_style': 'Fashion-forward, trendy, designer, Instagram-worthy',
                'price_point': '$$$$',
            },
            'tribeca': {
                'borough': 'manhattan',
                'vibe': 'Family-friendly luxury, celebrities, film festival culture',
                'demographics': 'Wealthy families, celebrities, finance professionals',
                'best_for': ['upscale dining', 'film screenings', 'luxury home goods', 'kids\' experiences'],
                'avoid': 'Anything too casual or downtown gritty',
                'gift_style': 'Understated luxury, family-oriented, cultured',
                'price_point': '$$$$',
            },
            'lower_east_side': {
                'borough': 'manhattan',
                'vibe': 'Hipster evolution, cocktail bars, vintage shopping, music venues, immigrant history',
                'demographics': 'Young professionals, nightlife crowd, vintage enthusiasts',
                'best_for': ['craft cocktail bars', 'vintage shopping', 'music venues', 'food tours'],
                'avoid': 'Generic or corporate gifts',
                'gift_style': 'Artisan, craft-focused, vintage, nightlife experiences',
                'price_point': '$$$',
            },

            # BROOKLYN
            'williamsburg': {
                'borough': 'brooklyn',
                'vibe': 'Hipster central, artisan everything, peak gentrification, rooftop bars',
                'demographics': 'Young creative professionals, 25-35, tech workers',
                'best_for': ['live music', 'craft cocktails', 'vintage shopping', 'rooftop bars', 'artisan goods'],
                'avoid': 'Anything corporate or mainstream, chain stores',
                'gift_style': 'Artisan, handmade, locally-made, indie brands, vinyl records',
                'price_point': '$$$',
            },
            'dumbo': {
                'borough': 'brooklyn',
                'vibe': 'Waterfront dining, art galleries, Instagram-worthy views, luxury condos',
                'demographics': 'Affluent young professionals, photographers, foodies',
                'best_for': ['waterfront dining', 'photo experiences', 'art galleries', 'Brooklyn Bridge Park'],
                'avoid': 'Anything too casual or grungy',
                'gift_style': 'Upscale, Instagram-worthy, experience-focused',
                'price_point': '$$$$',
            },
            'park_slope': {
                'borough': 'brooklyn',
                'vibe': 'Young families, farmer\'s markets, brownstone culture, progressive',
                'demographics': 'Families with kids, progressive professionals',
                'best_for': ['farmer\'s market vouchers', 'kids\' activities', 'bookstore gift cards', 'family dining'],
                'avoid': 'Singles nightlife, anything too edgy',
                'gift_style': 'Family-oriented, eco-conscious, educational, local',
                'price_point': '$$$',
            },
            'bushwick': {
                'borough': 'brooklyn',
                'vibe': 'Street art, warehouse parties, DIY music scene, artists',
                'demographics': 'Artists, musicians, young creatives, warehouse dwellers',
                'best_for': ['warehouse party tickets', 'art supplies', 'DIY music venues', 'street art tours'],
                'avoid': 'Corporate gifts, anything too polished',
                'gift_style': 'Raw, DIY, artistic, underground music',
                'price_point': '$',
            },
            'brooklyn_heights': {
                'borough': 'brooklyn',
                'vibe': 'Affluent, quiet, promenade, family-oriented, old Brooklyn',
                'demographics': 'Wealthy families, professionals, retirees',
                'best_for': ['fine dining', 'family experiences', 'historic tours', 'classical music'],
                'avoid': 'Nightlife-focused gifts, anything too trendy',
                'gift_style': 'Classic, family-friendly, refined, traditional',
                'price_point': '$$$$',
            },

            # QUEENS
            'astoria': {
                'borough': 'queens',
                'vibe': 'Greek food, diverse, Queens Night Market, young professionals',
                'demographics': 'Diverse young professionals, Greek community, foodies',
                'best_for': ['ethnic food tours', 'Queens Night Market', 'beer gardens', 'local tavernas'],
                'avoid': 'Generic Manhattan-style gifts',
                'gift_style': 'Authentic, diverse, food-focused, community-oriented',
                'price_point': '$$',
            },
            'long_island_city': {
                'borough': 'queens',
                'vibe': 'Waterfront development, breweries, MoMA PS1, industrial-chic',
                'demographics': 'Young professionals, art lovers, beer enthusiasts',
                'best_for': ['brewery tours', 'MoMA PS1 events', 'waterfront dining', 'art exhibitions'],
                'avoid': 'Anything too traditional',
                'gift_style': 'Modern, industrial-chic, brewery culture, contemporary art',
                'price_point': '$$$',
            },

            # THE BRONX
            'bronx': {
                'borough': 'the bronx',
                'vibe': 'Yankees Stadium, Bronx Zoo, Botanical Gardens, diverse working-class',
                'demographics': 'Working-class families, Yankees fans, nature lovers',
                'best_for': ['Yankees tickets', 'Bronx Zoo passes', 'Botanical Garden memberships', 'Arthur Ave Italian food'],
                'avoid': 'Gentrification-coded gifts, Mets gear',
                'gift_style': 'Sports-focused, family experiences, authentic local',
                'price_point': '$$',
            },
        },
    },

    'boston': {
        'region': 'northeast',
        'state': 'massachusetts',
        'vibe': 'Academic, historic, sports-obsessed, Irish culture, wicked smaht',
        'signature_experiences': [
            'Red Sox games (Fenway Park)',
            'Celtics/Bruins games',
            'Patriots games (Gillette)',
            'Freedom Trail',
            'Harvard/MIT lectures and events',
            'Boston Marathon (spectating/running)',
            'North End Italian food',
            'Cape Cod/Nantucket day trips',
        ],
        'local_culture': {
            'sports': 'INTENSE. Red Sox, Patriots, Celtics, Bruins. Championship culture.',
            'education': 'Academic hub. Harvard, MIT, BU, BC. Intellectual culture.',
            'history': 'Revolutionary War heritage. History matters.',
            'irish': 'Strong Irish-American culture. Pubs, St. Patrick\'s Day.',
        },
        'demographics_notes': {
            'young_female_25_35': 'Newbury Street shopping, brunch (South End), SoulCycle/yoga, Red Sox games, Cape weekends.',
            'young_male_25_35': 'Sports bars, Red Sox/Pats/Bruins, craft beer, sailing, college sports.',
            'female_35_50': 'Cape Cod, wine culture, theater, fine dining, boutique shopping.',
            'male_35_50': 'Red Sox/Pats season tickets, golf, sailing, whiskey, clam bakes.',
        },
        'avoid': [
            'Yankees gear (MORTAL ENEMY)',
            'Lakers/LeBron gear (Celtics fans)',
            'Anything disrespecting local sports teams',
            'Overly trendy West Coast stuff',
        ],
        'preferred_local': ['Newbury Street boutiques', 'North End markets', 'SoWa Market', 'Harvard Bookstore'],
    },
}


# ================================================================================
# SYNTHESIS FUNCTIONS - Combine region + city + demographics
# ================================================================================

def get_regional_context(
    city: Optional[str] = None,
    state: Optional[str] = None,
    neighborhood: Optional[str] = None,  # NEW: Neighborhood granularity for NYC/Chicago/LA
    age: Optional[int] = None,
    gender: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive regional cultural context for gift recommendations.

    Synthesizes:
    - City-specific culture (if city is known)
    - Neighborhood-specific culture (for NYC, Chicago, LA - culturally diverse cities)
    - Regional norms (Midwest, South, West Coast, Northeast)
    - Demographic preferences by region (25F Austin ≠ 25F Indianapolis)

    Args:
        city: City name (e.g., "Indianapolis", "Austin", "New York")
        state: State name (e.g., "Indiana", "Texas", "New York")
        neighborhood: Neighborhood name (e.g., "Williamsburg", "Wicker Park", "Silver Lake")
                     Only used for cities with neighborhood data (NYC, Chicago, LA)
        age: Recipient age
        gender: Recipient gender ("M", "F", or None)

    Returns:
        Dict with regional intelligence:
        {
            'region_name': 'midwest',
            'city_name': 'indianapolis',
            'neighborhood_name': 'williamsburg',  # if neighborhood provided
            'neighborhood_data': {...},  # if neighborhood found
            'gift_norms': {...},
            'local_experiences': [...],
            'avoid': [...],
            'demographic_synthesis': 'Young female in Indianapolis...',
            'experience_suggestions': [...],
        }
    """

    # Normalize inputs
    city_lower = city.lower().strip() if city else None
    state_lower = state.lower().strip() if state else None
    neighborhood_lower = neighborhood.lower().strip().replace(' ', '_') if neighborhood else None

    # Try to find city profile
    city_profile = None
    if city_lower:
        city_profile = CITY_PROFILES.get(city_lower.replace(' ', '_'))

    # Determine region
    region = None
    if city_profile:
        region = city_profile['region']
    elif state_lower:
        # Find region by state
        for region_name, region_data in REGIONAL_PROFILES.items():
            if state_lower in region_data['states']:
                region = region_name
                break

    # Build context
    context = {
        'has_data': bool(city_profile or region),
        'city_name': city,
        'state_name': state,
        'region_name': region,
    }

    if not (city_profile or region):
        logger.info(f"No regional context for city='{city}', state='{state}'")
        return context

    # Add regional gift norms
    if region:
        region_data = REGIONAL_PROFILES[region]
        context['gift_norms'] = region_data['gift_norms']
        context['cultural_traits'] = region_data['cultural_traits']
        context['regional_avoid'] = region_data['avoid']
        context['preferred_retailers'] = region_data['preferred_retailers']
        context['style_notes'] = region_data['style_notes']

    # Add city-specific data
    if city_profile:
        context['city_vibe'] = city_profile['vibe']
        context['signature_experiences'] = city_profile['signature_experiences']
        context['local_culture'] = city_profile['local_culture']
        context['city_avoid'] = city_profile['avoid']
        context['preferred_local'] = city_profile['preferred_local']

        # Demographic synthesis (city-level)
        demo_key = _get_demographic_key(age, gender)
        if demo_key and demo_key in city_profile.get('demographics_notes', {}):
            context['demographic_synthesis'] = city_profile['demographics_notes'][demo_key]

        # NEIGHBORHOOD GRANULARITY - Check if city has neighborhood data
        if 'neighborhoods' in city_profile and neighborhood_lower:
            if neighborhood_lower in city_profile['neighborhoods']:
                neighborhood_data = city_profile['neighborhoods'][neighborhood_lower]
                context['neighborhood_name'] = neighborhood
                context['neighborhood_data'] = neighborhood_data

                # Override city-level data with neighborhood specifics
                context['neighborhood_vibe'] = neighborhood_data['vibe']
                context['neighborhood_best_for'] = neighborhood_data['best_for']
                context['neighborhood_avoid'] = neighborhood_data['avoid']
                context['neighborhood_gift_style'] = neighborhood_data['gift_style']
                context['neighborhood_price_point'] = neighborhood_data['price_point']

                logger.info(f"Neighborhood context loaded: {city} / {neighborhood} ({neighborhood_data.get('borough') or neighborhood_data.get('area')})")
            else:
                logger.info(f"Neighborhood '{neighborhood}' not found in {city} profiles")

    # Generate experience suggestions based on region + demographics + neighborhood
    context['experience_suggestions'] = _generate_experience_suggestions(
        city_profile, region, age, gender, neighborhood_lower
    )

    logger.info(f"Regional context loaded: {region or 'unknown'} / {city or 'unknown'}")

    return context


def _get_demographic_key(age: Optional[int], gender: Optional[str]) -> Optional[str]:
    """Convert age + gender into demographic lookup key."""
    if not age or not gender:
        return None

    gender_lower = gender.lower()[0] if gender else None

    if 25 <= age <= 35:
        if gender_lower == 'f':
            return 'young_female_25_35'
        elif gender_lower == 'm':
            return 'young_male_25_35'
    elif 35 <= age <= 50:
        if gender_lower == 'f':
            return 'female_35_50'
        elif gender_lower == 'm':
            return 'male_35_50'

    return None


def _generate_experience_suggestions(
    city_profile: Optional[Dict],
    region: Optional[str],
    age: Optional[int],
    gender: Optional[str],
    neighborhood_lower: Optional[str] = None
) -> List[str]:
    """Generate smart experience suggestions based on location + demographics + neighborhood."""

    suggestions = []

    # NEIGHBORHOOD-SPECIFIC EXPERIENCES (highest priority for NYC/Chicago/LA)
    if city_profile and 'neighborhoods' in city_profile and neighborhood_lower:
        if neighborhood_lower in city_profile['neighborhoods']:
            neighborhood_data = city_profile['neighborhoods'][neighborhood_lower]
            best_for = neighborhood_data.get('best_for', [])
            suggestions.extend(best_for[:3])  # Top 3 neighborhood experiences

    # City-specific experiences
    if city_profile and 'signature_experiences' in city_profile:
        # Add top 3 signature experiences
        suggestions.extend(city_profile['signature_experiences'][:3])

    # Regional experiences based on demographics
    demo_key = _get_demographic_key(age, gender)

    if region == 'midwest':
        if 'young_female' in (demo_key or ''):
            suggestions.extend(['Boutique fitness class', 'Farmers market brunch', 'Local brewery tour'])
        elif 'young_male' in (demo_key or ''):
            suggestions.extend(['Sports bar experience', 'Craft brewery tour', 'Golf outing'])

    elif region == 'south':
        if 'young_female' in (demo_key or ''):
            suggestions.extend(['Wine tasting', 'Personalized jewelry making class', 'Southern cooking class'])
        elif 'young_male' in (demo_key or ''):
            suggestions.extend(['Whiskey tasting', 'BBQ tour', 'College football game'])

    elif region == 'west_coast':
        if 'young_female' in (demo_key or ''):
            suggestions.extend(['Yoga retreat', 'Farm-to-table dining', 'Hiking adventure'])
        elif 'young_male' in (demo_key or ''):
            suggestions.extend(['Surfing lesson', 'Wine country tour', 'Rock climbing'])

    elif region == 'northeast':
        if 'young_female' in (demo_key or ''):
            suggestions.extend(['Broadway show', 'Museum membership', 'Boutique shopping tour'])
        elif 'young_male' in (demo_key or ''):
            suggestions.extend(['Sports game tickets', 'Jazz club experience', 'Whiskey tasting'])

    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique_suggestions.append(s)

    return unique_suggestions[:6]  # Max 6 suggestions


def get_neighborhood_recommendations(city: str, neighborhood: str) -> Dict[str, Any]:
    """
    Get neighborhood-specific gift recommendations.
    Convenience function for when you know the specific neighborhood.

    Args:
        city: City name (e.g., "New York", "Chicago", "Los Angeles")
        neighborhood: Neighborhood name (e.g., "Williamsburg", "Wicker Park", "Silver Lake")

    Returns:
        Dict with neighborhood-specific data or empty dict if not found
    """
    city_lower = city.lower().strip().replace(' ', '_')
    neighborhood_lower = neighborhood.lower().strip().replace(' ', '_')

    city_profile = CITY_PROFILES.get(city_lower)
    if not city_profile or 'neighborhoods' not in city_profile:
        logger.warning(f"No neighborhood data for city '{city}'")
        return {}

    if neighborhood_lower not in city_profile['neighborhoods']:
        logger.warning(f"Neighborhood '{neighborhood}' not found in {city}")
        return {}

    return city_profile['neighborhoods'][neighborhood_lower]


def get_gift_guidance_for_region(region_context: Dict[str, Any]) -> str:
    """
    Generate human-readable gift guidance based on regional context.

    Returns a concise string describing regional gift preferences.
    Useful for feeding to gift curator as additional context.
    """

    if not region_context.get('has_data'):
        return ''

    parts = []

    # City + neighborhood + region intro
    city = region_context.get('city_name')
    neighborhood = region_context.get('neighborhood_name')
    region = region_context.get('region_name', '').replace('_', ' ').title()

    if neighborhood and city:
        parts.append(f"Gift recipient is in {neighborhood}, {city}.")
        # Add neighborhood vibe
        neighborhood_vibe = region_context.get('neighborhood_vibe')
        if neighborhood_vibe:
            parts.append(f"Neighborhood vibe: {neighborhood_vibe}")
    elif city and region:
        parts.append(f"Gift recipient is in {city} ({region}).")
    elif region:
        parts.append(f"Gift recipient is in the {region}.")

    # Gift norms (neighborhood overrides city/region if available)
    neighborhood_gift_style = region_context.get('neighborhood_gift_style')
    if neighborhood_gift_style:
        parts.append(f"Gift style: {neighborhood_gift_style}")
    else:
        gift_norms = region_context.get('gift_norms', {})
        if gift_norms:
            desc = gift_norms.get('description', '')
            if desc:
                parts.append(desc)

    # Demographic synthesis
    demo = region_context.get('demographic_synthesis')
    if demo:
        parts.append(f"Demographic insight: {demo}")

    # Things to avoid (neighborhood-specific first, then city, then region)
    avoid = (region_context.get('neighborhood_avoid') or
             region_context.get('city_avoid') or
             region_context.get('regional_avoid', []))
    if avoid:
        if isinstance(avoid, list):
            avoid_text = ', '.join(avoid[:3])
        else:
            avoid_text = avoid
        parts.append(f"Avoid: {avoid_text}.")

    return ' '.join(parts)


# ================================================================================
# TESTING
# ================================================================================

if __name__ == '__main__':
    # Test 1: 25F in Austin (single city profile - no neighborhoods)
    print("=" * 80)
    print("TEST 1: 25F in Austin, Texas (city-level only)")
    print("=" * 80)
    context = get_regional_context(city='Austin', state='Texas', age=27, gender='F')
    print(f"Region: {context.get('region_name')}")
    print(f"City vibe: {context.get('city_vibe')}")
    print(f"\nDemographic synthesis:")
    print(f"  {context.get('demographic_synthesis')}")
    print(f"\nExperience suggestions:")
    for exp in context.get('experience_suggestions', []):
        print(f"  - {exp}")
    print(f"\nGift guidance:")
    print(f"  {get_gift_guidance_for_region(context)}")

    # Test 2: 25F in Indianapolis (single city profile - culturally homogeneous)
    print("\n" + "=" * 80)
    print("TEST 2: 25F in Indianapolis, Indiana (city-level only)")
    print("=" * 80)
    context = get_regional_context(city='Indianapolis', state='Indiana', age=27, gender='F')
    print(f"Region: {context.get('region_name')}")
    print(f"City vibe: {context.get('city_vibe')}")
    print(f"\nDemographic synthesis:")
    print(f"  {context.get('demographic_synthesis')}")
    print(f"\nExperience suggestions:")
    for exp in context.get('experience_suggestions', []):
        print(f"  - {exp}")
    print(f"\nGift guidance:")
    print(f"  {get_gift_guidance_for_region(context)}")

    # Test 3: NYC Neighborhood - Williamsburg, Brooklyn
    print("\n" + "=" * 80)
    print("TEST 3: 28F in Williamsburg, Brooklyn (neighborhood-level)")
    print("=" * 80)
    context = get_regional_context(city='New York', state='NY', neighborhood='Williamsburg', age=28, gender='F')
    print(f"Region: {context.get('region_name')}")
    print(f"City: {context.get('city_name')}")
    print(f"Neighborhood: {context.get('neighborhood_name')}")
    print(f"\nNeighborhood vibe: {context.get('neighborhood_vibe')}")
    print(f"Gift style: {context.get('neighborhood_gift_style')}")
    print(f"Price point: {context.get('neighborhood_price_point')}")
    print(f"\nNeighborhood best for:")
    for item in context.get('neighborhood_best_for', []):
        print(f"  - {item}")
    print(f"\nAvoid: {context.get('neighborhood_avoid')}")
    print(f"\nExperience suggestions:")
    for exp in context.get('experience_suggestions', []):
        print(f"  - {exp}")
    print(f"\nGift guidance:")
    print(f"  {get_gift_guidance_for_region(context)}")

    # Test 4: NYC Neighborhood - Upper East Side (very different vibe)
    print("\n" + "=" * 80)
    print("TEST 4: 35F in Upper East Side, Manhattan (neighborhood-level)")
    print("=" * 80)
    context = get_regional_context(city='New York', state='NY', neighborhood='Upper East Side', age=35, gender='F')
    print(f"Neighborhood: {context.get('neighborhood_name')}")
    print(f"Neighborhood vibe: {context.get('neighborhood_vibe')}")
    print(f"Gift style: {context.get('neighborhood_gift_style')}")
    print(f"Price point: {context.get('neighborhood_price_point')}")
    print(f"\nGift guidance:")
    print(f"  {get_gift_guidance_for_region(context)}")

    # Test 5: Chicago Neighborhood - Wicker Park
    print("\n" + "=" * 80)
    print("TEST 5: 30M in Wicker Park, Chicago (neighborhood-level)")
    print("=" * 80)
    context = get_regional_context(city='Chicago', state='IL', neighborhood='Wicker Park', age=30, gender='M')
    print(f"Neighborhood: {context.get('neighborhood_name')}")
    print(f"Neighborhood vibe: {context.get('neighborhood_vibe')}")
    print(f"Gift style: {context.get('neighborhood_gift_style')}")
    print(f"\nNeighborhood best for:")
    for item in context.get('neighborhood_best_for', []):
        print(f"  - {item}")
    print(f"\nGift guidance:")
    print(f"  {get_gift_guidance_for_region(context)}")

    # Test 6: Chicago Neighborhood - Lincoln Park (very different from Wicker Park)
    print("\n" + "=" * 80)
    print("TEST 6: 30M in Lincoln Park, Chicago (neighborhood-level)")
    print("=" * 80)
    context = get_regional_context(city='Chicago', state='IL', neighborhood='Lincoln Park', age=30, gender='M')
    print(f"Neighborhood: {context.get('neighborhood_name')}")
    print(f"Neighborhood vibe: {context.get('neighborhood_vibe')}")
    print(f"Gift style: {context.get('neighborhood_gift_style')}")
    print(f"Price point: {context.get('neighborhood_price_point')}")
    print(f"\nGift guidance:")
    print(f"  {get_gift_guidance_for_region(context)}")

    # Test 7: LA Neighborhood - Silver Lake
    print("\n" + "=" * 80)
    print("TEST 7: 27F in Silver Lake, Los Angeles (neighborhood-level)")
    print("=" * 80)
    context = get_regional_context(city='Los Angeles', state='CA', neighborhood='Silver Lake', age=27, gender='F')
    print(f"Neighborhood: {context.get('neighborhood_name')}")
    print(f"Neighborhood vibe: {context.get('neighborhood_vibe')}")
    print(f"Gift style: {context.get('neighborhood_gift_style')}")
    print(f"\nNeighborhood best for:")
    for item in context.get('neighborhood_best_for', []):
        print(f"  - {item}")
    print(f"\nGift guidance:")
    print(f"  {get_gift_guidance_for_region(context)}")

    # Test 8: LA Neighborhood - Brentwood (very different from Silver Lake)
    print("\n" + "=" * 80)
    print("TEST 8: 40F in Brentwood, Los Angeles (neighborhood-level)")
    print("=" * 80)
    context = get_regional_context(city='Los Angeles', state='CA', neighborhood='Brentwood', age=40, gender='F')
    print(f"Neighborhood: {context.get('neighborhood_name')}")
    print(f"Neighborhood vibe: {context.get('neighborhood_vibe')}")
    print(f"Gift style: {context.get('neighborhood_gift_style')}")
    print(f"Price point: {context.get('neighborhood_price_point')}")
    print(f"\nGift guidance:")
    print(f"  {get_gift_guidance_for_region(context)}")

    # Test 9: Convenience function test
    print("\n" + "=" * 80)
    print("TEST 9: Convenience function - get_neighborhood_recommendations()")
    print("=" * 80)
    williamsburg = get_neighborhood_recommendations('New York', 'Williamsburg')
    print(f"Williamsburg data: {williamsburg.get('vibe')}")
    print(f"Best for: {williamsburg.get('best_for')}")

    wicker = get_neighborhood_recommendations('Chicago', 'Wicker Park')
    print(f"\nWicker Park data: {wicker.get('vibe')}")
    print(f"Gift style: {wicker.get('gift_style')}")

    # Test 10: Unknown city (state only)
    print("\n" + "=" * 80)
    print("TEST 10: Unknown city in California (state-level only)")
    print("=" * 80)
    context = get_regional_context(city=None, state='California', age=28, gender='F')
    print(f"Region: {context.get('region_name')}")
    print(f"Has city data: {context.get('city_vibe') is not None}")
    print(f"\nGift norms:")
    print(f"  {context.get('gift_norms', {}).get('description')}")
    print(f"\nCultural traits:")
    for trait in context.get('cultural_traits', [])[:3]:
        print(f"  - {trait}")
