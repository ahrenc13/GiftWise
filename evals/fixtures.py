"""
Synthetic profile fixtures for GiftWise evals.

Each fixture is designed to stress a specific failure mode:
  passionate_fly_fisher  — ownership avoidance + specificity under gear saturation
  tech_luxury            — splurge gate integrity + ownership avoidance (Apple ecosystem)
  aspiring_wine          — rising signal handling + aspirational vs current balance
  outdoor_budget         — experience/physical mix at tight price points
  ceramics_artist        — concept specificity for hands-on creative hobby + amalgam quality
"""

FIXTURES = [
    {
        "name": "passionate_fly_fisher",
        "description": "Gear-saturated angler. Owns the basics. Should get creative, not just more tackle.",
        "failure_modes": ["generic fishing gear", "duplicate owned items"],
        "recipient_type": "other",
        "relationship": "close_friend",
        "profile": {
            "interests": [
                {
                    "name": "fly fishing",
                    "evidence": "Posts daily from the Gallatin River. Ties his own flies. Follows Orvis and RIO Products.",
                    "description": "Serious fly angler, primarily trout in Montana rivers",
                    "intensity": "passionate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "high",
                    "signal_quotes": ["day 47 on the Gallatin", "finally nailed the elk hair caddis tie"],
                    "signal_momentum": "stable"
                },
                {
                    "name": "outdoor photography",
                    "evidence": "Posts river and mountain shots. Uses a Canon mirrorless.",
                    "description": "Documents fishing trips and landscapes",
                    "intensity": "casual",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "medium",
                    "signal_quotes": [],
                    "signal_momentum": "stable"
                }
            ],
            "location_context": {
                "city_region": "Bozeman, Montana",
                "specific_places": ["Gallatin River", "Madison River"],
                "geographic_constraints": "rural Montana, outdoor access is easy"
            },
            "ownership_signals": [
                "Orvis Clearwater fly rod (9ft 5wt)",
                "Simms waders",
                "Fishpond vest",
                "fly tying vise and materials",
                "Abel reel",
                "Canon EOS R mirrorless camera"
            ],
            "style_preferences": {
                "visual_style": "functional outdoor, utilitarian",
                "aesthetic_summary": "Values performance gear over aesthetics. Orvis and Patagonia loyalist.",
                "colors": ["olive", "tan", "earth tones"],
                "brands": ["Orvis", "Simms", "Patagonia", "RIO Products", "Fishpond"],
                "quality_level": "premium"
            },
            "price_signals": {
                "estimated_range": "$75-200",
                "budget_category": "moderate",
                "notes": "Willing to spend on quality gear, already owns the big-ticket items"
            },
            "aspirational_vs_current": {
                "aspirational": ["guided trip to a remote watershed", "Sage rod upgrade"],
                "current": ["active angler 3-4x per week in season"],
                "gaps": [
                    "wants access to private water",
                    "interested in steelhead fishing but hasn't tried it"
                ]
            },
            "gift_avoid": ["beginner gear", "generic 'fisherman' novelty items", "anything already owned"],
            "specific_venues": [],
            "gift_relationship_guidance": {
                "appropriate_types": ["experiences", "specialty consumables", "niche accessories"],
                "boundaries": "don't duplicate gear he already owns",
                "intimacy_level": "close friend — can get specific and personal"
            }
        }
    },
    {
        "name": "tech_luxury",
        "description": "Apple ecosystem completionist, luxury budget. Splurge gate should be earned, not just expensive.",
        "failure_modes": ["splurge = just expensive Apple accessory", "recommending owned gear"],
        "recipient_type": "other",
        "relationship": "romantic_partner",
        "profile": {
            "interests": [
                {
                    "name": "technology and software",
                    "evidence": "Works in product at a SF startup. Posts about AI tools, dev productivity. Follows WWDC keynotes.",
                    "description": "Deep Apple ecosystem user, follows tech broadly",
                    "intensity": "passionate",
                    "type": "current",
                    "is_work": True,
                    "activity_type": "both",
                    "confidence": "high",
                    "signal_quotes": ["shipping this week", "obsessed with the new M4 chip benchmarks"],
                    "signal_momentum": "stable"
                },
                {
                    "name": "specialty coffee",
                    "evidence": "Posts latte art, visits Blue Bottle and Ritual. Has a Fellow kettle.",
                    "description": "Daily ritual, appreciates process and quality",
                    "intensity": "moderate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "high",
                    "signal_quotes": ["finally dialed in the pour-over ratio"],
                    "signal_momentum": "stable"
                },
                {
                    "name": "mechanical keyboards",
                    "evidence": "Has a custom 65% keyboard. Posts about switches and keycaps.",
                    "description": "Enthusiast-level hobby, values craft and tactility",
                    "intensity": "moderate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "medium",
                    "signal_quotes": [],
                    "signal_momentum": "rising"
                }
            ],
            "location_context": {
                "city_region": "San Francisco, CA",
                "specific_places": ["Blue Bottle Coffee", "Ritual Coffee"],
                "geographic_constraints": "urban, dense options"
            },
            "ownership_signals": [
                "MacBook Pro M3 Max",
                "iPhone 15 Pro",
                "AirPods Pro 2nd gen",
                "Apple Watch Ultra 2",
                "Fellow Stagg EKG kettle",
                "custom 65% mechanical keyboard (Gateron Yellow switches)"
            ],
            "style_preferences": {
                "visual_style": "minimal, dark mode everything",
                "aesthetic_summary": "Precision and restraint. Loves things that are deeply considered and slightly nerdy.",
                "colors": ["black", "space gray", "midnight"],
                "brands": ["Apple", "Fellow", "Keychron", "Analogue", "Teenage Engineering"],
                "quality_level": "luxury"
            },
            "price_signals": {
                "estimated_range": "$200-600",
                "budget_category": "luxury",
                "notes": "High disposable income, will spend on things that matter"
            },
            "aspirational_vs_current": {
                "aspirational": ["Teenage Engineering OP-1 Field", "Analogue Pocket"],
                "current": ["fully kitted out workspace"],
                "gaps": [
                    "wants more creative outlets outside of work",
                    "interested in music production but hasn't started"
                ]
            },
            "gift_avoid": ["generic tech accessories", "anything already owned", "low-quality gadgets"],
            "specific_venues": [],
            "gift_relationship_guidance": {
                "appropriate_types": ["premium experiences", "niche hobby gear", "considered objects"],
                "boundaries": "very high bar — they own everything obvious",
                "intimacy_level": "romantic partner — can be personal and aspirational"
            }
        }
    },
    {
        "name": "aspiring_wine",
        "description": "Rising wine interest, aspirational learner. Should get education + access, not just bottles.",
        "failure_modes": ["recommending bottles they already have", "too basic (wine glass set)"],
        "recipient_type": "other",
        "relationship": "family_member",
        "profile": {
            "interests": [
                {
                    "name": "wine",
                    "evidence": "Started posting about wine 6 months ago. Visiting wineries, taking notes. Follows wine educators on IG.",
                    "description": "Rapidly growing enthusiasm, moving from casual to serious",
                    "intensity": "moderate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "both",
                    "confidence": "high",
                    "signal_quotes": ["finally understanding terroir", "this Burgundy is teaching me everything"],
                    "signal_momentum": "rising"
                },
                {
                    "name": "cooking and food",
                    "evidence": "Cooks most nights, shares pairings. Follows chefs on social.",
                    "description": "Home cook who sees wine and food as inseparable",
                    "intensity": "moderate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "medium",
                    "signal_quotes": [],
                    "signal_momentum": "stable"
                }
            ],
            "location_context": {
                "city_region": "Chicago, IL",
                "specific_places": ["Eataly Chicago", "Binny's Beverage Depot"],
                "geographic_constraints": "urban, good retail and dining access"
            },
            "ownership_signals": [
                "basic wine glasses (not Riedel)",
                "a few bottles of Burgundy and Barolo",
                "wine journal"
            ],
            "style_preferences": {
                "visual_style": "warm, European-influenced home aesthetic",
                "aesthetic_summary": "Appreciates provenance and story. Gravitates toward old-world over new-world.",
                "colors": ["warm neutrals", "burgundy", "deep green"],
                "brands": ["Burgundy producers", "Coravin", "Riedel"],
                "quality_level": "premium"
            },
            "price_signals": {
                "estimated_range": "$100-250",
                "budget_category": "premium",
                "notes": "Family member, willing to spend meaningfully"
            },
            "aspirational_vs_current": {
                "aspirational": ["WSET Level 2 certification", "visiting Burgundy someday"],
                "current": ["self-taught, visiting local wineries"],
                "gaps": [
                    "wants structured education, not just casual drinking",
                    "interested in building a small cellar but doesn't know where to start"
                ]
            },
            "gift_avoid": ["cheap wine accessories", "novelty wine gadgets", "anything they already own"],
            "specific_venues": [],
            "gift_relationship_guidance": {
                "appropriate_types": ["education", "experiences", "considered tools"],
                "boundaries": "family member — generous but not extravagant",
                "intimacy_level": "family — knows their interests well"
            }
        }
    },
    {
        "name": "outdoor_budget",
        "description": "Passionate hiker/camper on a budget. Should get experiences and smart accessories, not gear they have.",
        "failure_modes": ["recommending gear they own", "ignoring budget ceiling", "no experience options"],
        "recipient_type": "other",
        "relationship": "close_friend",
        "profile": {
            "interests": [
                {
                    "name": "hiking",
                    "evidence": "Completes a 14er most weekends in summer. Follows hiking accounts in Colorado.",
                    "description": "Serious hiker, does multi-day trips and peak bagging",
                    "intensity": "passionate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "high",
                    "signal_quotes": ["16th 14er done", "nothing like a 5am summit"],
                    "signal_momentum": "stable"
                },
                {
                    "name": "camping and backpacking",
                    "evidence": "Does solo and group trips. Posts camp cooking setups.",
                    "description": "Backpacker who cares about weight and efficiency",
                    "intensity": "passionate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "high",
                    "signal_quotes": ["ultralight kit finally under 20 lbs"],
                    "signal_momentum": "stable"
                },
                {
                    "name": "trail running",
                    "evidence": "Starting to run trails, just signed up for a local race.",
                    "description": "Newer interest, cross-training from hiking",
                    "intensity": "casual",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "medium",
                    "signal_quotes": [],
                    "signal_momentum": "rising"
                }
            ],
            "location_context": {
                "city_region": "Denver, Colorado",
                "specific_places": ["Rocky Mountain National Park", "Maroon Bells"],
                "geographic_constraints": "Colorado front range, mountain access easy"
            },
            "ownership_signals": [
                "Salomon hiking boots",
                "Black Diamond trekking poles",
                "REI tent (2-person)",
                "Osprey 50L backpack",
                "Jetboil camp stove",
                "basic sleeping bag (20°F)"
            ],
            "style_preferences": {
                "visual_style": "functional outdoor",
                "aesthetic_summary": "Ultralight-minded, values performance per dollar over brand names.",
                "colors": ["earth tones", "bright safety colors for alpine"],
                "brands": ["Black Diamond", "Salomon", "Patagonia", "REI", "Osprey"],
                "quality_level": "mid-range"
            },
            "price_signals": {
                "estimated_range": "$25-75",
                "budget_category": "budget",
                "notes": "College age, genuine budget constraint"
            },
            "aspirational_vs_current": {
                "aspirational": ["hut-to-hut trip in the Alps", "completing all Colorado 14ers"],
                "current": ["active every weekend in summer, less in winter"],
                "gaps": [
                    "wants better cold-weather sleeping system",
                    "interested in navigation skills beyond GPS"
                ]
            },
            "gift_avoid": ["heavy gear", "anything over $75", "gear already owned"],
            "specific_venues": [],
            "gift_relationship_guidance": {
                "appropriate_types": ["consumables", "small accessories", "experiences"],
                "boundaries": "close friend, genuine budget limit is real",
                "intimacy_level": "close friend — knows their kit well"
            }
        }
    },
    {
        "name": "ceramics_artist",
        "description": "Serious ceramicist with a home studio. Should get unexpected angles, not more clay.",
        "failure_modes": ["recommending tools they own", "generic 'art supplies'", "weak amalgam if generated"],
        "recipient_type": "other",
        "relationship": "romantic_partner",
        "profile": {
            "interests": [
                {
                    "name": "ceramics and pottery",
                    "evidence": "Has a home studio setup. Sells pieces on Etsy. Posts wheel-throwing and glaze experiments.",
                    "description": "Serious studio practice, functional and sculptural work",
                    "intensity": "passionate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "active",
                    "confidence": "high",
                    "signal_quotes": ["finally got the celadon glaze right", "sold out of mugs in 20 minutes"],
                    "signal_momentum": "stable"
                },
                {
                    "name": "interior design and home aesthetics",
                    "evidence": "Curates her home around her own ceramics and vintage finds. Follows design accounts.",
                    "description": "Thoughtful home editor, ceramics inform the space",
                    "intensity": "moderate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "passive",
                    "confidence": "medium",
                    "signal_quotes": [],
                    "signal_momentum": "stable"
                },
                {
                    "name": "Japanese craft and aesthetics",
                    "evidence": "Posts about wabi-sabi, follows Japanese ceramic artists. Has visited Japan.",
                    "description": "Deep influence on her work and taste",
                    "intensity": "moderate",
                    "type": "current",
                    "is_work": False,
                    "activity_type": "passive",
                    "confidence": "medium",
                    "signal_quotes": ["this yunomi changed how I think about form"],
                    "signal_momentum": "stable"
                }
            ],
            "location_context": {
                "city_region": "Portland, Oregon",
                "specific_places": ["Bullseye Glass", "local ceramics galleries"],
                "geographic_constraints": "urban, good arts community"
            },
            "ownership_signals": [
                "Brent pottery wheel",
                "electric kiln",
                "full set of Kemper trimming tools",
                "various glazes and underglazes",
                "wedging table",
                "wire clay cutter and basic tools"
            ],
            "style_preferences": {
                "visual_style": "wabi-sabi, Japanese-influenced, organic forms",
                "aesthetic_summary": "Drawn to imperfection, texture, and quiet beauty. Earthy palette. Anti-maximalist.",
                "colors": ["celadon", "ash", "iron oxide tones", "matte neutrals"],
                "brands": ["Skutt", "Amaco", "Laguna Clay", "local pottery suppliers"],
                "quality_level": "mid-range"
            },
            "price_signals": {
                "estimated_range": "$75-200",
                "budget_category": "moderate",
                "notes": "Romantic partner, meaningful gift budget"
            },
            "aspirational_vs_current": {
                "aspirational": ["residency at a Japanese pottery village", "wood-fire kiln experience"],
                "current": ["active studio practice, selling work"],
                "gaps": [
                    "wants to experience traditional Japanese firing techniques",
                    "interested in natural ash glazes but hasn't learned the chemistry"
                ]
            },
            "gift_avoid": ["basic pottery tools already owned", "generic art gift cards", "anything mass-produced"],
            "specific_venues": [],
            "gift_relationship_guidance": {
                "appropriate_types": ["experiences", "rare materials", "education", "considered objects"],
                "boundaries": "romantic partner — can be personal and aspirational",
                "intimacy_level": "intimate — knows her work and taste deeply"
            }
        }
    }
]
