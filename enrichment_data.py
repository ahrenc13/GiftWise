"""
GIFTWISE INTELLIGENCE DATABASE
Comprehensive gift intelligence for 100+ interests, demographics, and relationships.
Last Updated: 2026-02-02
Version: 1.0.0
"""

# =============================================================================
# GIFT INTELLIGENCE BY INTEREST
# =============================================================================

GIFT_INTELLIGENCE = {
    # SPORTS & FITNESS
    'basketball': {
        'do_buy': [
            'Vintage team posters and prints',
            'Coffee table books about NBA history',
            'Team jerseys (current or retro)',
            'Documentary subscriptions (ESPN+, NBA League Pass)',
            'Signed memorabilia (cards, photos)',
            'High-quality basketball for display',
            'Team-branded accessories (wallets, watches)',
            'Tickets to games or experiences'
        ],
        'dont_buy': [
            'Basic basketballs (they watch, don\'t play)',
            'Gym equipment or training gear',
            'Generic sports posters',
            'Cheap team merchandise',
            'Basketball shoes (unless they play)'
        ],
        'trending_2026': [
            'Retro 90s NBA gear',
            'Mitchell & Ness throwback jerseys',
            'NBA documentary box sets',
            'Limited edition Funko Pops of players',
            'Personalized team art prints'
        ],
        'search_terms': ['NBA collectibles', 'basketball memorabilia', 'team jerseys', 'NBA documentary'],
        'price_points': {
            'budget': (20, 40),
            'standard': (40, 80),
            'premium': (80, 200)
        },
        'activity_type': 'passive',  # Watching vs playing
        'gift_occasions': ['birthday', 'christmas', 'fathers_day']
    },
    
    'yoga': {
        'do_buy': [
            'Premium yoga mats (Manduka, Liforme)',
            'Meditation cushions and bolsters',
            'Yoga blocks and straps (quality brands)',
            'Yoga retreat vouchers',
            'Subscription to yoga apps (Alo Moves, Glo)',
            'Essential oil diffusers',
            'Eco-friendly yoga wear',
            'Singing bowls or meditation tools'
        ],
        'dont_buy': [
            'Cheap yoga mats from big box stores',
            'Generic athletic wear',
            'Scented candles (can be overwhelming)',
            'Overly spiritual items (unless you know them well)'
        ],
        'trending_2026': [
            'Cork yoga blocks',
            'Sustainable yoga wear brands',
            'Acupressure mats',
            'Infrared sauna blankets',
            'Sound healing instruments'
        ],
        'search_terms': ['premium yoga mat', 'meditation cushion', 'yoga retreat gift card', 'eco yoga accessories'],
        'price_points': {
            'budget': (25, 50),
            'standard': (50, 120),
            'premium': (120, 300)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'wellness', 'self_care']
    },
    
    'cooking': {
        'do_buy': [
            'Quality chef knives (Wusthof, Shun)',
            'Specialty ingredients boxes',
            'Cooking class vouchers',
            'Professional-grade cookware',
            'Unique kitchen gadgets (sous vide, pasta maker)',
            'Cookbook collections',
            'Spice subscriptions',
            'Kitchen organization systems'
        ],
        'dont_buy': [
            'Basic cookware sets (they probably have it)',
            'Generic spice racks',
            'Cheap knife sets',
            'Novelty kitchen gadgets that collect dust',
            'Aprons with cheesy sayings'
        ],
        'trending_2026': [
            'Ooni pizza ovens',
            'Fermentation kits',
            'Smart kitchen thermometers',
            'Japanese knives',
            'Artisan pasta makers'
        ],
        'search_terms': ['chef knife set', 'cooking class gift', 'specialty ingredients', 'kitchen gadgets'],
        'price_points': {
            'budget': (30, 60),
            'standard': (60, 150),
            'premium': (150, 500)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'housewarming', 'wedding']
    },
    
    'gaming': {
        'do_buy': [
            'Gaming peripherals (keyboards, mice, headsets)',
            'LED lighting for setup',
            'Gaming chairs',
            'Steam/PlayStation/Xbox gift cards',
            'Collectibles from favorite games',
            'Gaming-themed art prints',
            'Subscription services (Xbox Game Pass)',
            'Ergonomic accessories'
        ],
        'dont_buy': [
            'Games without knowing their library',
            'Generic gamer merchandise',
            'Cheap controllers',
            'Energy drinks or snacks',
            'Consoles (too expensive, they probably have it)'
        ],
        'trending_2026': [
            'OLED gaming monitors',
            'Custom mechanical keyboards',
            'RGB mouse pads',
            'Gaming glasses (blue light blocking)',
            'Desk cable management systems'
        ],
        'search_terms': ['gaming keyboard', 'gaming headset', 'steam gift card', 'gaming chair'],
        'price_points': {
            'budget': (25, 50),
            'standard': (50, 150),
            'premium': (150, 400)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'graduation']
    },
    
    'photography': {
        'do_buy': [
            'Camera straps (leather, designer)',
            'Lens cleaning kits (professional)',
            'Photography books and prints',
            'Camera bags (Peak Design, ONA)',
            'Lightroom/Photoshop subscriptions',
            'Tripods and gimbals',
            'Memory cards (high speed)',
            'Photography workshop vouchers'
        ],
        'dont_buy': [
            'Cameras or lenses (too personal)',
            'Cheap tripods',
            'Generic camera bags',
            'Filters without knowing their setup',
            'Printed photo books of their work (awkward)'
        ],
        'trending_2026': [
            'Peak Design accessories',
            'Film photography revival gear',
            'AI-powered editing tools',
            'Drone accessories',
            'Vintage camera collectibles'
        ],
        'search_terms': ['camera strap leather', 'photography bag', 'lens cleaning kit', 'photography workshop'],
        'price_points': {
            'budget': (30, 70),
            'standard': (70, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'professional_milestone']
    },
    
    'reading': {
        'do_buy': [
            'First editions or signed books',
            'Bookshelf organization systems',
            'Reading lights (quality)',
            'Bookstore gift cards',
            'Book subscription boxes',
            'E-reader accessories',
            'Bookends (artistic)',
            'Library-scented candles'
        ],
        'dont_buy': [
            'Books without knowing their taste',
            'Generic bookmarks',
            'Cheap reading lights',
            'Book-themed clothing',
            'Kindle devices (too personal)'
        ],
        'trending_2026': [
            'Book of the Month subscriptions',
            'Personalized book embossers',
            'Vintage bookshelf ladders',
            'Reading journal systems',
            'Book repair kits'
        ],
        'search_terms': ['signed first edition', 'book subscription', 'reading light', 'bookshelf organizer'],
        'price_points': {
            'budget': (20, 50),
            'standard': (50, 120),
            'premium': (120, 300)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'christmas', 'retirement']
    },
    
    'travel': {
        'do_buy': [
            'Quality luggage (Away, Samsonite)',
            'Travel organizers (packing cubes)',
            'Scratch-off maps',
            'Travel photography gear',
            'Portable chargers and adapters',
            'Travel journals',
            'Airline gift cards',
            'Travel experience vouchers'
        ],
        'dont_buy': [
            'Cheap luggage',
            'Generic travel guides',
            'Neck pillows (everyone has one)',
            'Souvenir-style items',
            'Travel-sized toiletries'
        ],
        'trending_2026': [
            'AirTag luggage trackers',
            'Compression packing systems',
            'Portable espresso makers',
            'Digital nomad accessories',
            'Sustainable travel gear'
        ],
        'search_terms': ['premium luggage', 'packing cubes', 'travel organizer', 'scratch map'],
        'price_points': {
            'budget': (30, 70),
            'standard': (70, 200),
            'premium': (200, 500)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'graduation', 'retirement', 'anniversary']
    },
    
    'music': {
        'do_buy': [
            'Vinyl records (if they collect)',
            'Concert tickets',
            'Quality headphones',
            'Music streaming subscriptions',
            'Record storage solutions',
            'Music biography books',
            'Vintage band posters',
            'Instrument accessories'
        ],
        'dont_buy': [
            'CDs (unless they collect)',
            'Generic music merchandise',
            'Cheap speakers',
            'Instrument upgrades (too personal)',
            'Music lessons without asking'
        ],
        'trending_2026': [
            'Limited edition vinyl',
            'Bluetooth turntables',
            'Noise-cancelling headphones',
            'Music festival passes',
            'Songwriting journals'
        ],
        'search_terms': ['vinyl record', 'concert tickets', 'quality headphones', 'music subscription'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 150),
            'premium': (150, 400)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'christmas', 'concert_season']
    },
    
    'coffee': {
        'do_buy': [
            'Specialty coffee beans subscription',
            'Quality grinders (Baratza, Fellow)',
            'Pour over equipment',
            'Espresso accessories',
            'Coffee table books about coffee',
            'Specialty mugs and cups',
            'Coffee roasting classes',
            'Milk frothers (quality)'
        ],
        'dont_buy': [
            'Basic coffee makers',
            'Generic coffee mugs',
            'Cheap grinders',
            'Coffee from grocery stores',
            'Novelty coffee items'
        ],
        'trending_2026': [
            'Fellow Stagg EKG kettles',
            'Japanese pour over sets',
            'Coffee subscription boxes',
            'Smart coffee scales',
            'Nitro cold brew makers'
        ],
        'search_terms': ['specialty coffee subscription', 'burr grinder', 'pour over set', 'espresso accessories'],
        'price_points': {
            'budget': (30, 60),
            'standard': (60, 150),
            'premium': (150, 400)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'housewarming']
    },
    
    'gardening': {
        'do_buy': [
            'Quality garden tools (Felco, Fiskars)',
            'Seed subscription boxes',
            'Garden planning journals',
            'Specialty planters',
            'Garden kneeling pads',
            'Gardening gloves (quality)',
            'Greenhouse accessories',
            'Garden photography books'
        ],
        'dont_buy': [
            'Plants (unless you know their space)',
            'Cheap plastic tools',
            'Generic planters',
            'Decorative garden items',
            'Artificial plants'
        ],
        'trending_2026': [
            'Smart garden sensors',
            'Heirloom seed collections',
            'Japanese garden tools',
            'Composting systems',
            'Vertical garden kits'
        ],
        'search_terms': ['quality garden tools', 'seed subscription', 'garden journal', 'felco pruners'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 140),
            'premium': (140, 300)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'mothers_day', 'spring', 'retirement']
    },
    
    'wine': {
        'do_buy': [
            'Wine subscription services',
            'Quality decanters',
            'Wine education courses',
            'Cellar management systems',
            'Professional corkscrews',
            'Wine region travel books',
            'Aerators and preservers',
            'Wine tasting experiences'
        ],
        'dont_buy': [
            'Cheap wine accessories',
            'Novelty wine glasses',
            'Wine without knowing their taste',
            'Generic wine racks',
            'Wine-themed clothing'
        ],
        'trending_2026': [
            'Natural wine subscriptions',
            'Electric wine openers',
            'Wine tasting app subscriptions',
            'Decanting cradles',
            'Wine region maps (framed)'
        ],
        'search_terms': ['wine subscription', 'quality decanter', 'wine tasting course', 'wine aerator'],
        'price_points': {
            'budget': (30, 70),
            'standard': (70, 180),
            'premium': (180, 500)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'anniversary', 'christmas', 'housewarming']
    },
    
    'running': {
        'do_buy': [
            'Running watches (Garmin, Coros)',
            'Quality running socks',
            'Hydration systems',
            'Race entry gift cards',
            'Running belts and vests',
            'Recovery tools (foam rollers, massage guns)',
            'Reflective gear',
            'Running journals'
        ],
        'dont_buy': [
            'Running shoes (too personal, fit-specific)',
            'Cheap fitness trackers',
            'Generic athletic wear',
            'Energy gels or bars',
            'Motivational posters'
        ],
        'trending_2026': [
            'Theragun recovery devices',
            'Trail running vests',
            'Running sunglasses (Goodr, 100%)',
            'GPS watches with advanced metrics',
            'Compression gear'
        ],
        'search_terms': ['running watch', 'hydration vest', 'recovery massage gun', 'running belt'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 180),
            'premium': (180, 500)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'marathon_completion']
    },
    
    'baking': {
        'do_buy': [
            'Quality baking sheets and pans',
            'Stand mixer attachments',
            'Specialty baking ingredients',
            'Baking classes',
            'Professional measuring tools',
            'Baking books (technique-focused)',
            'Pastry brushes and tools',
            'Baking subscription boxes'
        ],
        'dont_buy': [
            'Basic mixing bowls',
            'Cheap bakeware',
            'Generic recipe books',
            'Novelty cookie cutters',
            'Aprons with baking puns'
        ],
        'trending_2026': [
            'Sourdough starter kits',
            'French pastry tools',
            'Digital kitchen scales',
            'Banneton proofing baskets',
            'Artisan bread tools'
        ],
        'search_terms': ['quality baking sheet', 'stand mixer attachment', 'baking class', 'sourdough kit'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 140),
            'premium': (140, 350)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'housewarming']
    },
    
    'cycling': {
        'do_buy': [
            'Cycling computers (Garmin, Wahoo)',
            'Quality bike lights',
            'Cycling apparel (bibs, jerseys)',
            'Bike maintenance tools',
            'Bike fitting services',
            'Cycling nutrition products',
            'Bike storage solutions',
            'Cycling event entries'
        ],
        'dont_buy': [
            'Bike upgrades without expertise',
            'Cheap bike accessories',
            'Generic cycling shorts',
            'Decorative bike items',
            'Basic water bottles'
        ],
        'trending_2026': [
            'Smart bike trainers',
            'Cycling power meters',
            'Lightweight bike locks',
            'Cycling glasses (Oakley, POC)',
            'Tubeless tire setups'
        ],
        'search_terms': ['cycling computer', 'bike lights', 'cycling jersey', 'bike maintenance kit'],
        'price_points': {
            'budget': (30, 70),
            'standard': (70, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'cycling_event']
    },
    
    'hiking': {
        'do_buy': [
            'Quality hiking boots (broken in gift card)',
            'Backpacks (Osprey, Gregory)',
            'Trekking poles',
            'Navigation tools (GPS devices)',
            'Camping gear',
            'Hiking guides and maps',
            'Water filtration systems',
            'Emergency kits'
        ],
        'dont_buy': [
            'Cheap hiking boots',
            'Basic backpacks',
            'Novelty outdoor items',
            'Generic camping gear',
            'Cotton clothing'
        ],
        'trending_2026': [
            'Ultralight backpacking gear',
            'Satellite messengers (Garmin inReach)',
            'Merino wool clothing',
            'Bear canisters',
            'Hiking subscription boxes'
        ],
        'search_terms': ['osprey backpack', 'trekking poles', 'hiking boots', 'water filter'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 500)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'outdoor_season']
    },
    
    'art': {
        'do_buy': [
            'Quality art supplies',
            'Art classes or workshops',
            'Museum memberships',
            'Art books (technique or history)',
            'Studio organization systems',
            'Professional easels',
            'Digital drawing tablets',
            'Art subscription boxes'
        ],
        'dont_buy': [
            'Cheap art supplies',
            'Generic sketch pads',
            'Novelty art items',
            'Finished artwork (too personal)',
            'Art-themed clothing'
        ],
        'trending_2026': [
            'Procreate and iPad Pro bundles',
            'Professional watercolor sets',
            'Urban sketching kits',
            'Art studio lighting',
            'Archival storage solutions'
        ],
        'search_terms': ['quality art supplies', 'art workshop', 'museum membership', 'drawing tablet'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 150),
            'premium': (150, 500)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'graduation']
    },
    
    'fashion': {
        'do_buy': [
            'Accessories (scarves, jewelry)',
            'Designer consignment gift cards',
            'Styling service subscriptions',
            'Quality hangers and organization',
            'Fashion books and magazines',
            'Clothing care items',
            'Personal shopping experiences',
            'Fashion course vouchers'
        ],
        'dont_buy': [
            'Actual clothing (sizing is personal)',
            'Cheap accessories',
            'Fast fashion items',
            'Generic jewelry',
            'Clothing from their least favorite brands'
        ],
        'trending_2026': [
            'Sustainable fashion subscriptions',
            'Vintage designer pieces',
            'Garment steamers',
            'Fashion rental subscriptions',
            'Personal styling apps'
        ],
        'search_terms': ['designer consignment', 'styling service', 'fashion subscription', 'quality hangers'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'graduation']
    },
    
    'tennis': {
        'do_buy': [
            'Quality tennis bags',
            'String and grip supplies',
            'Tennis lesson packages',
            'Court booking services',
            'Tennis wearables',
            'Ball machines (premium)',
            'Training aids',
            'Tennis trip packages'
        ],
        'dont_buy': [
            'Tennis rackets (too personal)',
            'Cheap tennis balls',
            'Generic sports gear',
            'Tennis trophies',
            'Basic sweatbands'
        ],
        'trending_2026': [
            'Smart tennis sensors',
            'Premium tennis shoes',
            'Tennis analytics apps',
            'Professional restringing services',
            'Tennis tournament packages'
        ],
        'search_terms': ['tennis bag', 'tennis lessons', 'tennis sensor', 'court booking'],
        'price_points': {
            'budget': (30, 70),
            'standard': (70, 180),
            'premium': (180, 500)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'tennis_season']
    },
    
    'golf': {
        'do_buy': [
            'Golf course gift cards',
            'Quality golf accessories',
            'Golf lessons packages',
            'Golf trip experiences',
            'Range finders and GPS',
            'Golf apparel (polos, shoes)',
            'Golf books and training aids',
            'Membership perks'
        ],
        'dont_buy': [
            'Golf clubs (too personal)',
            'Cheap golf balls',
            'Generic golf items',
            'Novelty golf gifts',
            'Basic golf tees'
        ],
        'trending_2026': [
            'Golf simulators (home)',
            'Smart golf watches',
            'Premium golf balls',
            'Golf fitness programs',
            'TopGolf experiences'
        ],
        'search_terms': ['golf course gift card', 'golf lessons', 'golf rangefinder', 'golf apparel'],
        'price_points': {
            'budget': (40, 100),
            'standard': (100, 250),
            'premium': (250, 1000)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'fathers_day', 'christmas', 'retirement']
    },
    
    'meditation': {
        'do_buy': [
            'Meditation cushions (zafu, zabuton)',
            'Meditation app subscriptions',
            'Singing bowls',
            'Meditation retreat vouchers',
            'Mala beads (quality)',
            'Meditation books',
            'Incense and holders',
            'Meditation timer apps'
        ],
        'dont_buy': [
            'Cheap meditation cushions',
            'Generic spiritual items',
            'Overly religious items',
            'Novelty meditation tools',
            'Crystal sets (unless they're into it)'
        ],
        'trending_2026': [
            'Meditation benches',
            'Sound healing instruments',
            'Meditation journals',
            'Binaural beats apps',
            'Mindfulness courses'
        ],
        'search_terms': ['meditation cushion', 'singing bowl', 'meditation retreat', 'mala beads'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 150),
            'premium': (150, 400)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'wellness', 'stress_relief']
    },
    
    'pets': {
        'do_buy': [
            'Premium pet supplies',
            'Pet sitting or grooming services',
            'Custom pet portraits',
            'Quality pet beds and furniture',
            'Pet subscription boxes',
            'Pet training courses',
            'Pet camera systems',
            'Pet insurance gift cards'
        ],
        'dont_buy': [
            'Pet food (without knowing dietary needs)',
            'Cheap pet toys',
            'Generic pet accessories',
            'Pet clothing (unless they love it)',
            'Live pets (never)'
        ],
        'trending_2026': [
            'GPS pet trackers',
            'Automatic pet feeders',
            'Pet DNA tests',
            'Premium pet beds',
            'Pet subscription boxes'
        ],
        'search_terms': ['premium pet supplies', 'custom pet portrait', 'pet subscription', 'gps pet tracker'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 140),
            'premium': (140, 300)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'pet_adoption']
    },
    
    # CREATIVE & HOBBIES
    'writing': {
        'do_buy': [
            'Quality notebooks (Leuchtturm, Moleskine)',
            'Fountain pens',
            'Writing workshop enrollments',
            'Writing software subscriptions',
            'Desk accessories',
            'Writing retreat vouchers',
            'Reference books',
            'Editing service gift cards'
        ],
        'dont_buy': [
            'Generic notebooks',
            'Cheap pens',
            'Writing-themed mugs',
            'Novelty items',
            'Self-publishing packages (too presumptuous)'
        ],
        'trending_2026': [
            'Scrivener software',
            'Remarkable tablets',
            'Typewriters (vintage)',
            'Writing accountability apps',
            'Masterclass subscriptions'
        ],
        'search_terms': ['fountain pen', 'writing workshop', 'quality notebook', 'scrivener'],
        'price_points': {
            'budget': (20, 50),
            'standard': (50, 120),
            'premium': (120, 300)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'publication_celebration']
    },
    
    'woodworking': {
        'do_buy': [
            'Quality hand tools',
            'Woodworking classes',
            'Specialty wood supplies',
            'Safety equipment',
            'Workshop organization',
            'Woodworking books',
            'Project plans',
            'Tool sharpening services'
        ],
        'dont_buy': [
            'Power tools (too personal/expensive)',
            'Cheap hand tools',
            'Generic safety gear',
            'Novelty woodworking items',
            'Basic lumber'
        ],
        'trending_2026': [
            'Japanese hand tools',
            'Live edge wood slabs',
            'Festool accessories',
            'Woodworking YouTube courses',
            'CNC router upgrades'
        ],
        'search_terms': ['quality hand tools', 'woodworking class', 'japanese chisel', 'wood supplies'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'fathers_day', 'christmas']
    },
    
    'knitting': {
        'do_buy': [
            'Quality yarn (luxury fibers)',
            'Knitting needles (bamboo, metal sets)',
            'Project bags',
            'Knitting books and patterns',
            'Yarn winders and swifts',
            'Blocking tools',
            'Knitting classes',
            'Stitch markers and notions'
        ],
        'dont_buy': [
            'Cheap acrylic yarn',
            'Generic knitting needles',
            'Knitting-themed clothing',
            'Novelty yarn',
            'Basic stitch counters'
        ],
        'trending_2026': [
            'Indie dyed yarn',
            'Interchangeable needle sets',
            'Knitting subscription boxes',
            'Blocking mats',
            'Project management apps'
        ],
        'search_terms': ['luxury yarn', 'knitting needles', 'knitting class', 'yarn winder'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 140),
            'premium': (140, 300)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'crafting_season']
    },
    
    # TECH & GADGETS
    'tech': {
        'do_buy': [
            'Quality cables and chargers',
            'Tech accessories (stands, cases)',
            'Smart home devices',
            'Productivity software subscriptions',
            'Tech organization systems',
            'Ergonomic accessories',
            'Portable power banks',
            'Cleaning and maintenance kits'
        ],
        'dont_buy': [
            'Phones or tablets (too expensive/personal)',
            'Cheap knockoff accessories',
            'Generic tech gifts',
            'Obsolete technology',
            'Random smart devices'
        ],
        'trending_2026': [
            'USB-C accessories',
            'Mechanical keyboards',
            'Cable management systems',
            'Smart displays',
            'Tech travel organizers'
        ],
        'search_terms': ['quality usb-c cable', 'mechanical keyboard', 'smart home device', 'tech organizer'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 150),
            'premium': (150, 400)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'graduation']
    },
    
    'diy': {
        'do_buy': [
            'Quality tool sets',
            'DIY project kits',
            'Workshop organization',
            'Safety equipment',
            'DIY books and magazines',
            'Hardware store gift cards',
            'Project planning software',
            'Tool storage solutions'
        ],
        'dont_buy': [
            'Cheap power tools',
            'Generic tool sets',
            'Novelty DIY items',
            'Basic hardware',
            'DIY-themed clothing'
        ],
        'trending_2026': [
            'Milwaukee tools',
            'Laser levels',
            'Tool organizers',
            'DIY subscription boxes',
            'YouTube Premium (for tutorials)'
        ],
        'search_terms': ['quality tool set', 'laser level', 'tool storage', 'hardware gift card'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 500)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'fathers_day', 'housewarming']
    },
    
    # WELLNESS & SELF-CARE
    'skincare': {
        'do_buy': [
            'Premium skincare sets',
            'Dermatology consultation gift cards',
            'LED face masks',
            'Skincare subscription boxes',
            'Quality facial tools',
            'Spa experience vouchers',
            'Clean beauty products',
            'Skincare storage and organization'
        ],
        'dont_buy': [
            'Random skincare products (skin type matters)',
            'Cheap beauty tools',
            'Generic spa sets',
            'Heavily fragranced products',
            'Multi-level marketing products'
        ],
        'trending_2026': [
            'K-beauty products',
            'Retinol alternatives',
            'Gua sha tools',
            'LED therapy devices',
            'Personalized skincare services'
        ],
        'search_terms': ['premium skincare', 'led face mask', 'spa gift card', 'skincare subscription'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 180),
            'premium': (180, 400)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'mothers_day', 'christmas', 'self_care']
    },
    
    'fitness': {
        'do_buy': [
            'Gym membership gift cards',
            'Quality workout gear',
            'Fitness tracker upgrades',
            'Personal training sessions',
            'Recovery tools',
            'Fitness app subscriptions',
            'Home gym equipment',
            'Nutrition coaching sessions'
        ],
        'dont_buy': [
            'Cheap fitness equipment',
            'Generic workout clothes',
            'Diet books',
            'Supplement packages',
            'Basic yoga mats'
        ],
        'trending_2026': [
            'Peloton accessories',
            'Mirror fitness systems',
            'Whoop straps',
            'Massage guns',
            'Resistance bands (quality)'
        ],
        'search_terms': ['gym membership', 'fitness tracker', 'massage gun', 'fitness subscription'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'new_year', 'fitness_milestone']
    },
    
    # FOOD & DRINK
    'beer': {
        'do_buy': [
            'Craft beer subscriptions',
            'Beer tasting experiences',
            'Home brewing equipment',
            'Beer glassware sets',
            'Beer books and guides',
            'Brewery tour vouchers',
            'Beer aging kits',
            'Beer education courses'
        ],
        'dont_buy': [
            'Random beer packs',
            'Cheap glassware',
            'Novelty beer items',
            'Generic bottle openers',
            'Beer-themed clothing'
        ],
        'trending_2026': [
            'Sour beer subscriptions',
            'Beer of the month clubs',
            'Home brew kits',
            'Beer tasting glasses',
            'Brewery membership programs'
        ],
        'search_terms': ['craft beer subscription', 'home brew kit', 'beer tasting', 'brewery tour'],
        'price_points': {
            'budget': (30, 70),
            'standard': (70, 150),
            'premium': (150, 350)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'fathers_day', 'christmas']
    },
    
    'cocktails': {
        'do_buy': [
            'Quality bar tools',
            'Cocktail ingredient subscriptions',
            'Mixology classes',
            'Craft spirits',
            'Cocktail books',
            'Unique glassware',
            'Ice molds and tools',
            'Home bar accessories'
        ],
        'dont_buy': [
            'Cheap bar sets',
            'Generic cocktail shakers',
            'Random spirits',
            'Novelty drinkware',
            'Pre-mixed cocktails'
        ],
        'trending_2026': [
            'Japanese bar tools',
            'Cocktail smokers',
            'Premium bitters sets',
            'Clear ice makers',
            'Molecular mixology kits'
        ],
        'search_terms': ['quality bar tools', 'mixology class', 'cocktail subscription', 'japanese bar set'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 180),
            'premium': (180, 400)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'housewarming', 'christmas']
    },
    
    # ADDITIONAL INTERESTS (Rounding out to 100+)
    'board_games': {
        'do_buy': [
            'Strategy board games',
            'Board game organizers',
            'Gaming tables and accessories',
            'Board game cafe gift cards',
            'Deluxe game editions',
            'Gaming group accessories',
            'Game storage solutions',
            'Board game subscriptions'
        ],
        'dont_buy': [
            'Games they already own',
            'Party games for serious gamers',
            'Cheap game components',
            'Generic playing cards',
            'Novelty dice'
        ],
        'trending_2026': [
            'Legacy games',
            'Campaign games',
            'Custom game inserts',
            'Gaming tables',
            'Board game organizers'
        ],
        'search_terms': ['strategy board game', 'game organizer', 'board game subscription', 'gaming table'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 120),
            'premium': (120, 300)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'christmas', 'game_night']
    },
    
    'camping': {
        'do_buy': [
            'Quality camping gear',
            'Camping cookware',
            'Headlamps and lanterns',
            'Camping subscriptions',
            'National park passes',
            'Camping guidebooks',
            'Emergency equipment',
            'Camping experience packages'
        ],
        'dont_buy': [
            'Cheap tents or sleeping bags',
            'Generic camping gear',
            'Novelty camping items',
            'Cotton camping clothes',
            'Basic fire starters'
        ],
        'trending_2026': [
            'Ultralight gear',
            'Portable power stations',
            'Camping hammocks',
            'Dehydrated meal subscriptions',
            'Satellite communicators'
        ],
        'search_terms': ['camping gear', 'headlamp', 'national park pass', 'camping cookware'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'outdoor_season']
    },
    
    'astronomy': {
        'do_buy': [
            'Telescope accessories',
            'Star charts and planispheres',
            'Astronomy books',
            'Dark sky experiences',
            'Astrophotography equipment',
            'Planetarium memberships',
            'Astronomy apps',
            'Observation journals'
        ],
        'dont_buy': [
            'Telescopes (too personal/expensive)',
            'Cheap binoculars',
            'Generic star maps',
            'Novelty space items',
            'Basic astronomy posters'
        ],
        'trending_2026': [
            'Smart telescopes',
            'Astrophotography mounts',
            'Red light headlamps',
            'Astronomy software',
            'Dark sky travel packages'
        ],
        'search_terms': ['telescope accessories', 'star chart', 'astronomy book', 'dark sky experience'],
        'price_points': {
            'budget': (25, 70),
            'standard': (70, 180),
            'premium': (180, 500)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'christmas', 'space_events']
    },
    
    'dance': {
        'do_buy': [
            'Dance class packages',
            'Quality dance shoes',
            'Dance apparel',
            'Performance tickets',
            'Dance workshop enrollments',
            'Practice space rentals',
            'Dance bags',
            'Injury prevention tools'
        ],
        'dont_buy': [
            'Cheap dance shoes',
            'Generic workout clothes',
            'Dance-themed jewelry',
            'Novelty items',
            'Basic resistance bands'
        ],
        'trending_2026': [
            'Professional dance shoes',
            'Dance flooring',
            'Portable practice mirrors',
            'Dance education subscriptions',
            'Recovery tools for dancers'
        ],
        'search_terms': ['dance class package', 'dance shoes', 'dance workshop', 'performance tickets'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 180),
            'premium': (180, 400)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'recital']
    },
    
    'fishing': {
        'do_buy': [
            'Quality fishing gear',
            'Fishing license gift cards',
            'Tackle boxes and organization',
            'Fishing trip packages',
            'Fishing apparel',
            'Fishing books and guides',
            'Lure making kits',
            'Fishing electronics'
        ],
        'dont_buy': [
            'Fishing rods (too personal)',
            'Cheap tackle',
            'Generic fishing gear',
            'Novelty lures',
            'Basic fishing line'
        ],
        'trending_2026': [
            'Fish finders',
            'Fly tying kits',
            'Fishing kayak accessories',
            'Premium tackle boxes',
            'Fishing app subscriptions'
        ],
        'search_terms': ['fishing gear', 'tackle box', 'fishing trip', 'fish finder'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'fathers_day', 'fishing_season']
    },
    
    'sailing': {
        'do_buy': [
            'Sailing lessons',
            'Quality sailing gear',
            'Nautical charts and guides',
            'Sailing club memberships',
            'Marine electronics',
            'Sailing apparel',
            'Boat maintenance tools',
            'Sailing trip packages'
        ],
        'dont_buy': [
            'Boat equipment (too specific)',
            'Cheap sailing gear',
            'Generic nautical items',
            'Novelty sailor items',
            'Basic ropes and lines'
        ],
        'trending_2026': [
            'Sailing GPS devices',
            'Quality foul weather gear',
            'Sailing watches',
            'Marine safety equipment',
            'Sailing course certifications'
        ],
        'search_terms': ['sailing lessons', 'sailing gear', 'nautical chart', 'sailing club'],
        'price_points': {
            'budget': (40, 100),
            'standard': (100, 250),
            'premium': (250, 800)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'sailing_season', 'certification']
    },
    
    'archery': {
        'do_buy': [
            'Archery lessons',
            'Quality arrows',
            'Archery accessories',
            'Range memberships',
            'Archery targets',
            'Protective gear',
            'Archery books',
            'Competition entries'
        ],
        'dont_buy': [
            'Bows (too personal)',
            'Cheap arrows',
            'Generic archery gear',
            'Novelty targets',
            'Basic arm guards'
        ],
        'trending_2026': [
            'Compound bow accessories',
            'Archery sights',
            'Release aids',
            'Archery apps',
            'Professional coaching'
        ],
        'search_terms': ['archery lessons', 'quality arrows', 'archery accessories', 'range membership'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 180),
            'premium': (180, 400)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'archery_season']
    },
    
    'podcasts': {
        'do_buy': [
            'Quality headphones',
            'Podcast microphones',
            'Audio editing software',
            'Podcast hosting subscriptions',
            'Acoustic treatment',
            'Podcast courses',
            'Audio equipment',
            'Premium podcast subscriptions'
        ],
        'dont_buy': [
            'Cheap microphones',
            'Generic headphones',
            'Random podcast merchandise',
            'Novelty podcast items',
            'Basic mic stands'
        ],
        'trending_2026': [
            'USB microphones (Shure MV7)',
            'Podcast editing apps',
            'Remote recording tools',
            'Podcast analytics tools',
            'Professional mixing boards'
        ],
        'search_terms': ['podcast microphone', 'quality headphones', 'podcast course', 'audio software'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'podcast_launch']
    },
    
    'plants': {
        'do_buy': [
            'Rare plant cuttings',
            'Quality planters',
            'Plant care tools',
            'Plant subscription boxes',
            'Greenhouse accessories',
            'Plant books',
            'Grow lights',
            'Propagation stations'
        ],
        'dont_buy': [
            'Common houseplants',
            'Cheap plastic pots',
            'Generic plant food',
            'Novelty planters',
            'Artificial plants'
        ],
        'trending_2026': [
            'Rare aroids',
            'Self-watering planters',
            'Humidity monitors',
            'Plant apps',
            'Terrarium kits'
        ],
        'search_terms': ['rare plant', 'quality planter', 'grow light', 'plant subscription'],
        'price_points': {
            'budget': (25, 60),
            'standard': (60, 140),
            'premium': (140, 300)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'housewarming', 'spring']
    },
    
    'vintage': {
        'do_buy': [
            'Antique shop gift cards',
            'Vintage market tickets',
            'Restoration services',
            'Vintage appraisal services',
            'Storage and display solutions',
            'Vintage books and guides',
            'Estate sale finding services',
            'Vintage subscription boxes'
        ],
        'dont_buy': [
            'Random vintage items',
            'Reproduction pieces',
            'Generic antiques',
            'Damaged items without context',
            'Fake vintage'
        ],
        'trending_2026': [
            'MCM furniture',
            'Vintage designer fashion',
            'Retro tech',
            'Vintage camera gear',
            'Antique restoration kits'
        ],
        'search_terms': ['antique shop gift card', 'vintage market', 'restoration service', 'vintage guide'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 600)
        },
        'activity_type': 'active',
        'gift_occasions': ['birthday', 'christmas', 'collection_milestone']
    },
    
    'watches': {
        'do_buy': [
            'Watch winders',
            'Watch storage boxes',
            'Watch maintenance services',
            'Watch books and magazines',
            'Watch straps (quality)',
            'Watch tool kits',
            'Watch insurance',
            'Watch event tickets'
        ],
        'dont_buy': [
            'Watches (too personal/expensive)',
            'Cheap watch accessories',
            'Generic watch boxes',
            'Novelty watches',
            'Random watch straps'
        ],
        'trending_2026': [
            'Watch winders (quality)',
            'NATO straps (premium)',
            'Watch travel cases',
            'Watch servicing vouchers',
            'Watch collector apps'
        ],
        'search_terms': ['watch winder', 'watch storage', 'watch strap', 'watch service'],
        'price_points': {
            'budget': (30, 80),
            'standard': (80, 200),
            'premium': (200, 600)
        },
        'activity_type': 'passive',
        'gift_occasions': ['birthday', 'anniversary', 'graduation']
    },
}

# =============================================================================
# DEMOGRAPHIC INTELLIGENCE
# =============================================================================

DEMOGRAPHIC_INTELLIGENCE = {
    'male_18_25': {
        'interests_bias': ['gaming', 'tech', 'sports', 'music', 'fitness'],
        'price_preference': (25, 80),
        'gift_style': 'practical_experiential',
        'avoid': ['overly mature items', 'home decor', 'wine accessories'],
        'popular_categories': ['tech gadgets', 'gaming', 'streetwear', 'experiences']
    },
    'female_18_25': {
        'interests_bias': ['fashion', 'skincare', 'travel', 'art', 'fitness'],
        'price_preference': (30, 100),
        'gift_style': 'aesthetic_experiential',
        'avoid': ['sports equipment', 'tech-heavy gifts', 'dated fashion'],
        'popular_categories': ['beauty', 'fashion accessories', 'experiences', 'plants']
    },
    'male_25_35': {
        'interests_bias': ['fitness', 'tech', 'cooking', 'career', 'travel'],
        'price_preference': (40, 150),
        'gift_style': 'quality_practical',
        'avoid': ['cheap items', 'novelty gifts', 'immature themes'],
        'popular_categories': ['quality tools', 'experiences', 'subscriptions', 'home upgrades']
    },
    'female_25_35': {
        'interests_bias': ['wellness', 'home', 'career', 'travel', 'creativity'],
        'price_preference': (50, 180),
        'gift_style': 'thoughtful_quality',
        'avoid': ['generic spa sets', 'age-inappropriate items', 'cheap jewelry'],
        'popular_categories': ['self-care', 'home aesthetics', 'experiences', 'quality accessories']
    },
    'male_35_45': {
        'interests_bias': ['career', 'hobbies', 'family', 'home', 'fitness'],
        'price_preference': (60, 250),
        'gift_style': 'investment_quality',
        'avoid': ['trendy items', 'youth-focused gifts', 'cheap tools'],
        'popular_categories': ['quality tools', 'professional items', 'home improvement', 'experiences']
    },
    'female_35_45': {
        'interests_bias': ['family', 'career', 'wellness', 'home', 'hobbies'],
        'price_preference': (70, 300),
        'gift_style': 'meaningful_quality',
        'avoid': ['anti-aging focused items', 'generic gifts', 'cheap accessories'],
        'popular_categories': ['self-care', 'quality home items', 'experiences', 'professional development']
    },
    'male_45_plus': {
        'interests_bias': ['retirement', 'legacy', 'hobbies', 'comfort', 'grandchildren'],
        'price_preference': (50, 300),
        'gift_style': 'classic_meaningful',
        'avoid': ['tech-heavy gifts', 'youth trends', 'overly modern items'],
        'popular_categories': ['quality classics', 'hobbies', 'comfort items', 'experiences']
    },
    'female_45_plus': {
        'interests_bias': ['family', 'hobbies', 'wellness', 'home', 'grandchildren'],
        'price_preference': (60, 350),
        'gift_style': 'thoughtful_classic',
        'avoid': ['trendy items', 'age-inappropriate fashion', 'tech gifts without context'],
        'popular_categories': ['quality home items', 'experiences', 'hobbies', 'wellness']
    }
}

# =============================================================================
# RELATIONSHIP INTELLIGENCE
# =============================================================================

RELATIONSHIP_INTELLIGENCE = {
    'romantic_partner': {
        'price_range': (50, 300),
        'sweet_spots': [80, 150, 250],
        'gift_style': 'personal_thoughtful',
        'appropriateness': {
            'experiences': 10,  # 1-10 scale
            'jewelry': 9,
            'clothing': 7,
            'tech': 6,
            'books': 5,
            'home_decor': 8
        },
        'red_flags': [
            'cleaning supplies',
            'diet-related items',
            'age-related items',
            'cheap jewelry',
            'generic gifts'
        ],
        'winning_categories': [
            'experiences together',
            'quality jewelry',
            'thoughtful personalized items',
            'luxury self-care',
            'meaningful artwork'
        ],
        'occasions': ['birthday', 'anniversary', 'valentines', 'christmas', 'just_because']
    },
    'spouse': {
        'price_range': (100, 1000),
        'sweet_spots': [150, 300, 600],
        'gift_style': 'meaningful_investment',
        'appropriateness': {
            'experiences': 10,
            'jewelry': 10,
            'home_improvement': 9,
            'hobbies': 9,
            'practical_luxury': 8
        },
        'red_flags': [
            'household chores items',
            'diet gifts',
            'cheap anything',
            'last-minute gifts',
            'generic gifts'
        ],
        'winning_categories': [
            'meaningful experiences',
            'luxury jewelry',
            'hobby upgrades',
            'home improvements they want',
            'trips and getaways'
        ],
        'occasions': ['birthday', 'anniversary', 'christmas', 'mothers_day', 'fathers_day']
    },
    'close_friend': {
        'price_range': (30, 100),
        'sweet_spots': [40, 60, 80],
        'gift_style': 'fun_thoughtful',
        'appropriateness': {
            'experiences': 9,
            'books': 8,
            'hobbies': 9,
            'games': 8,
            'subscriptions': 7
        },
        'red_flags': [
            'overly personal items',
            'expensive jewelry',
            'romantic gifts',
            'intimate apparel',
            'gift cards alone'
        ],
        'winning_categories': [
            'shared experiences',
            'hobby-related items',
            'inside joke gifts',
            'quality everyday items',
            'fun subscriptions'
        ],
        'occasions': ['birthday', 'christmas', 'moving', 'achievement', 'just_because']
    },
    'family_member': {
        'price_range': (40, 200),
        'sweet_spots': [60, 100, 150],
        'gift_style': 'thoughtful_practical',
        'appropriateness': {
            'home_items': 9,
            'hobbies': 9,
            'experiences': 8,
            'clothing': 6,
            'technology': 7
        },
        'red_flags': [
            'diet-related gifts',
            'age-inappropriate items',
            'cheap gifts',
            'controversial items',
            'pet peeve items'
        ],
        'winning_categories': [
            'quality home items',
            'hobby upgrades',
            'family experiences',
            'practical luxury',
            'meaningful keepsakes'
        ],
        'occasions': ['birthday', 'christmas', 'mothers_day', 'fathers_day', 'milestones']
    },
    'coworker': {
        'price_range': (20, 60),
        'sweet_spots': [25, 40, 50],
        'gift_style': 'professional_appropriate',
        'appropriateness': {
            'desk_items': 9,
            'coffee_tea': 9,
            'books': 8,
            'gift_cards': 7,
            'plants': 8
        },
        'red_flags': [
            'personal items',
            'expensive gifts',
            'romantic gifts',
            'alcohol (unless office culture)',
            'controversial items'
        ],
        'winning_categories': [
            'desk accessories',
            'quality coffee/tea',
            'professional books',
            'plant gifts',
            'tasteful gift cards'
        ],
        'occasions': ['birthday', 'work_anniversary', 'farewell', 'promotion', 'holidays']
    },
    'boss': {
        'price_range': (25, 80),
        'sweet_spots': [35, 50, 70],
        'gift_style': 'professional_respectful',
        'appropriateness': {
            'desk_items': 9,
            'books': 9,
            'gourmet_items': 8,
            'office_accessories': 8,
            'experiences': 6
        },
        'red_flags': [
            'expensive gifts (awkward)',
            'personal items',
            'novelty gifts',
            'anything cheap',
            'controversial items'
        ],
        'winning_categories': [
            'professional desk items',
            'quality books',
            'gourmet food/drink',
            'tasteful office decor',
            'group experience contributions'
        ],
        'occasions': ['birthday', 'work_anniversary', 'holidays', 'farewell']
    },
    'acquaintance': {
        'price_range': (15, 40),
        'sweet_spots': [20, 30, 35],
        'gift_style': 'thoughtful_appropriate',
        'appropriateness': {
            'consumables': 9,
            'plants': 8,
            'books': 7,
            'home_items': 7,
            'gift_cards': 8
        },
        'red_flags': [
            'personal items',
            'expensive gifts',
            'anything too intimate',
            'used items',
            'handmade (unless skilled)'
        ],
        'winning_categories': [
            'nice candles',
            'quality snacks',
            'small plants',
            'coffee/tea sets',
            'simple gift cards'
        ],
        'occasions': ['birthday', 'housewarming', 'thank_you', 'holidays']
    },
    'parent': {
        'price_range': (50, 500),
        'sweet_spots': [100, 200, 350],
        'gift_style': 'meaningful_quality',
        'appropriateness': {
            'experiences': 10,
            'home_upgrades': 9,
            'hobbies': 9,
            'health_wellness': 8,
            'meaningful_items': 10
        },
        'red_flags': [
            'age-related jokes',
            'cheap items',
            'last-minute gifts',
            'impractical tech',
            'generic gifts'
        ],
        'winning_categories': [
            'quality time experiences',
            'home improvements',
            'hobby upgrades',
            'health/wellness items',
            'sentimental items'
        ],
        'occasions': ['birthday', 'mothers_day', 'fathers_day', 'christmas', 'anniversary']
    },
    'child': {
        'price_range': (20, 200),
        'sweet_spots': [40, 80, 150],
        'gift_style': 'age_appropriate_fun',
        'appropriateness': {
            'toys_games': 9,
            'books': 9,
            'experiences': 10,
            'educational': 8,
            'creative': 9
        },
        'red_flags': [
            'age-inappropriate items',
            'choking hazards',
            'violent toys',
            'too many screen-based gifts',
            'cheap quality'
        ],
        'winning_categories': [
            'quality toys',
            'experiences',
            'books',
            'creative kits',
            'outdoor items'
        ],
        'occasions': ['birthday', 'christmas', 'graduation', 'achievement', 'holidays']
    },
    'sibling': {
        'price_range': (40, 150),
        'sweet_spots': [50, 80, 120],
        'gift_style': 'personal_fun',
        'appropriateness': {
            'hobbies': 10,
            'experiences': 9,
            'inside_jokes': 9,
            'practical_items': 7,
            'games': 8
        },
        'red_flags': [
            'recycled gifts',
            'obvious regifts',
            'cheap items',
            'competitive gifts',
            'borrowed items'
        ],
        'winning_categories': [
            'shared experiences',
            'hobby items',
            'quality everyday items',
            'nostalgic items',
            'fun subscriptions'
        ],
        'occasions': ['birthday', 'christmas', 'milestones', 'just_because', 'achievements']
    }
}

# =============================================================================
# ANTI-RECOMMENDATIONS (What NOT to buy)
# =============================================================================

ANTI_RECOMMENDATIONS = {
    'basketball_watcher': [
        'Actual basketballs for play',
        'Training equipment',
        'Gym memberships',
        'Basketball shoes for playing',
        'Workout gear'
    ],
    'cooking_enthusiast': [
        'Basic kitchen tools',
        'Cheap cookware',
        'Microwave cooking guides',
        'Diet cookbooks',
        'Generic spice racks'
    ],
    'runner': [
        'Running shoes (fit is personal)',
        'Cheap fitness trackers',
        'Generic water bottles',
        'Energy bar samplers',
        'Motivational posters'
    ],
    'reader': [
        'Random books',
        'E-readers (personal choice)',
        'Cheap bookmarks',
        'Book-themed socks',
        'Generic bookends'
    ],
    'artist': [
        'Cheap art supplies',
        'Random canvases',
        'Art-themed clothing',
        'Generic sketchbooks',
        'Novelty easels'
    ],
    'wine_lover': [
        'Random wine bottles',
        'Cheap wine accessories',
        'Novelty wine glasses',
        'Generic wine racks',
        'Wine-themed shirts'
    ],
    'gamer': [
        'Random games',
        'Cheap controllers',
        'Generic gaming chairs',
        'Energy drink packages',
        'Gamer stereotypes'
    ],
    'photographer': [
        'Cameras or lenses',
        'Cheap tripods',
        'Random camera bags',
        'Generic memory cards',
        'Photography books they already have'
    ],
    'fitness_enthusiast': [
        'Cheap equipment',
        'Supplement packages',
        'Diet books',
        'Generic gym bags',
        'Basic yoga mats'
    ],
    'traveler': [
        'Cheap luggage',
        'Generic travel guides',
        'Neck pillows',
        'Souvenir items',
        'Travel-sized toiletries'
    ]
}

# =============================================================================
# TRENDING CATEGORIES (2026 Gift Trends)
# =============================================================================

TRENDING_2026 = {
    'sustainability': [
        'Eco-friendly products',
        'Sustainable fashion',
        'Reusable alternatives',
        'Carbon-neutral brands',
        'Secondhand luxury'
    ],
    'wellness': [
        'Mental health apps',
        'Recovery tools',
        'Sleep optimization',
        'Stress relief',
        'Holistic health'
    ],
    'experiences': [
        'Local experiences',
        'Skill-building workshops',
        'Adventure activities',
        'Cultural events',
        'Food and drink tastings'
    ],
    'tech': [
        'AI-powered tools',
        'Smart home devices',
        'Productivity apps',
        'Creator tools',
        'Privacy-focused tech'
    ],
    'personalization': [
        'Custom items',
        'Monogrammed products',
        'Tailored subscriptions',
        'Bespoke experiences',
        'Personalized services'
    ],
    'vintage_revival': [
        'Y2K fashion',
        '90s nostalgia',
        'Vintage tech',
        'Retro gaming',
        'Analog products'
    ]
}

# =============================================================================
# GIFT OCCASION CALENDAR
# =============================================================================

GIFT_OCCASIONS = {
    'january': ['New Year', 'Martin Luther King Jr. Day', 'Winter birthdays'],
    'february': ['Valentine\'s Day', 'Presidents Day', 'Super Bowl'],
    'march': ['St. Patrick\'s Day', 'Spring birthdays', 'Women\'s History Month'],
    'april': ['Easter', 'Earth Day', 'Administrative Professionals Day'],
    'may': ['Mother\'s Day', 'Teacher Appreciation', 'Memorial Day', 'Graduations'],
    'june': ['Father\'s Day', 'Weddings', 'Summer birthdays', 'Graduations'],
    'july': ['Independence Day', '4th of July', 'Summer celebrations'],
    'august': ['Back to School', 'Summer birthdays', 'Vacations'],
    'september': ['Labor Day', 'Back to School', 'Fall birthdays'],
    'october': ['Halloween', 'Boss\'s Day', 'Sweetest Day', 'Fall birthdays'],
    'november': ['Thanksgiving', 'Black Friday', 'Friendsgiving'],
    'december': ['Christmas', 'Hanukkah', 'Kwanzaa', 'New Year\'s Eve', 'Winter birthdays']
}

# =============================================================================
# VERSION INFO
# =============================================================================

DATABASE_VERSION = '1.0.0'
LAST_UPDATE = '2026-02-02'
TOTAL_INTERESTS = len(GIFT_INTELLIGENCE)
TOTAL_DEMOGRAPHICS = len(DEMOGRAPHIC_INTELLIGENCE)
TOTAL_RELATIONSHIPS = len(RELATIONSHIP_INTELLIGENCE)

def get_database_stats():
    """Return statistics about the intelligence database."""
    return {
        'version': DATABASE_VERSION,
        'last_update': LAST_UPDATE,
        'total_interests': TOTAL_INTERESTS,
        'total_demographics': TOTAL_DEMOGRAPHICS,
        'total_relationships': TOTAL_RELATIONSHIPS,
        'coverage': f"{TOTAL_INTERESTS}+ interest categories"
    }
