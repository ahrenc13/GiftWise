"""
REGIONAL CULTURE INTELLIGENCE - Local norms, preferences, and cultural context for gift recommendations

Makes bespoke experiences truly intelligent by incorporating:
- Regional gift-giving norms (Midwest practicality vs South personalization)
- Local culture and preferences (Austin live music vs Indianapolis sports)
- Things to avoid by region (NYC touristy crap, Boston Yankees gear)
- Preferred local retailers and experiences
- Demographic + geographic synthesis (25F Austin ≠ 25F Indianapolis)

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
    age: Optional[int] = None,
    gender: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive regional cultural context for gift recommendations.

    Synthesizes:
    - City-specific culture (if city is known)
    - Regional norms (Midwest, South, West Coast, Northeast)
    - Demographic preferences by region (25F Austin ≠ 25F Indianapolis)

    Args:
        city: City name (e.g., "Indianapolis", "Austin")
        state: State name (e.g., "Indiana", "Texas")
        age: Recipient age
        gender: Recipient gender ("M", "F", or None)

    Returns:
        Dict with regional intelligence:
        {
            'region_name': 'midwest',
            'city_name': 'indianapolis',
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

        # Demographic synthesis
        demo_key = _get_demographic_key(age, gender)
        if demo_key and demo_key in city_profile.get('demographics_notes', {}):
            context['demographic_synthesis'] = city_profile['demographics_notes'][demo_key]

    # Generate experience suggestions based on region + demographics
    context['experience_suggestions'] = _generate_experience_suggestions(
        city_profile, region, age, gender
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
    gender: Optional[str]
) -> List[str]:
    """Generate smart experience suggestions based on location + demographics."""

    suggestions = []

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


def get_gift_guidance_for_region(region_context: Dict[str, Any]) -> str:
    """
    Generate human-readable gift guidance based on regional context.

    Returns a concise string describing regional gift preferences.
    Useful for feeding to gift curator as additional context.
    """

    if not region_context.get('has_data'):
        return ''

    parts = []

    # City + region intro
    city = region_context.get('city_name')
    region = region_context.get('region_name', '').replace('_', ' ').title()

    if city and region:
        parts.append(f"Gift recipient is in {city} ({region}).")
    elif region:
        parts.append(f"Gift recipient is in the {region}.")

    # Gift norms
    gift_norms = region_context.get('gift_norms', {})
    if gift_norms:
        desc = gift_norms.get('description', '')
        if desc:
            parts.append(desc)

    # Demographic synthesis
    demo = region_context.get('demographic_synthesis')
    if demo:
        parts.append(f"Demographic insight: {demo}")

    # Things to avoid
    avoid = region_context.get('city_avoid') or region_context.get('regional_avoid', [])
    if avoid:
        avoid_text = ', '.join(avoid[:3])
        parts.append(f"Avoid: {avoid_text}.")

    return ' '.join(parts)


# ================================================================================
# TESTING
# ================================================================================

if __name__ == '__main__':
    # Test 1: 25F in Austin
    print("=" * 80)
    print("TEST 1: 25F in Austin, Texas")
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

    # Test 2: 25F in Indianapolis
    print("\n" + "=" * 80)
    print("TEST 2: 25F in Indianapolis, Indiana")
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

    # Test 3: 30M in Boston
    print("\n" + "=" * 80)
    print("TEST 3: 30M in Boston, Massachusetts")
    print("=" * 80)
    context = get_regional_context(city='Boston', state='Massachusetts', age=30, gender='M')
    print(f"Region: {context.get('region_name')}")
    print(f"City vibe: {context.get('city_vibe')}")
    print(f"\nDemographic synthesis:")
    print(f"  {context.get('demographic_synthesis')}")
    print(f"\nExperience suggestions:")
    for exp in context.get('experience_suggestions', []):
        print(f"  - {exp}")
    print(f"\nAvoid:")
    for item in context.get('city_avoid', []):
        print(f"  - {item}")

    # Test 4: Unknown city (state only)
    print("\n" + "=" * 80)
    print("TEST 4: Unknown city in California")
    print("=" * 80)
    context = get_regional_context(city=None, state='California', age=28, gender='F')
    print(f"Region: {context.get('region_name')}")
    print(f"Has city data: {context.get('city_vibe') is not None}")
    print(f"\nGift norms:")
    print(f"  {context.get('gift_norms', {}).get('description')}")
    print(f"\nCultural traits:")
    for trait in context.get('cultural_traits', [])[:3]:
        print(f"  - {trait}")
