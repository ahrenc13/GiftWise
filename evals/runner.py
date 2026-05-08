"""
Eval runner — calls ideate_gifts on each fixture without Flask context.

Mirrors what recommendation_service._generate_concept_recommendations() does:
  1. Enrich profile with ontology briefing (zero cost)
  2. Call ideate_gifts with the enriched profile
  3. Return raw ideated output for judging
"""

import logging
import sys
import os

logger = logging.getLogger(__name__)


def run_fixture(fixture: dict, claude_client, model: str) -> dict:
    """
    Run ideate_gifts on a single fixture profile.

    Returns:
        {
            "fixture_name": str,
            "output": ideate_gifts result dict (product_gifts, splurge_item, portrait),
            "error": str | None
        }
    """
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from gift_ideator import ideate_gifts
    except ImportError as e:
        return {"fixture_name": fixture["name"], "output": None, "error": f"Import failed: {e}"}

    profile = fixture["profile"]

    # Ontology enrichment — mirrors what _generate_concept_recommendations does
    ontology_briefing = None
    try:
        from interest_ontology import enrich_profile_with_ontology
        result = enrich_profile_with_ontology(profile)
        ontology_briefing = result.get("curator_briefing", "")
        logger.info(f"[{fixture['name']}] Ontology briefing: {len(ontology_briefing)} chars")
    except Exception as e:
        logger.warning(f"[{fixture['name']}] Ontology unavailable ({e}), continuing without")

    try:
        logger.info(f"[{fixture['name']}] Calling ideate_gifts...")
        output = ideate_gifts(
            profile=profile,
            recipient_type=fixture["recipient_type"],
            relationship=fixture["relationship"],
            claude_client=claude_client,
            rec_count=10,
            ontology_briefing=ontology_briefing,
            model=model,
        )
        logger.info(
            f"[{fixture['name']}] Got {len(output.get('product_gifts', []))} concepts, "
            f"splurge={'yes' if output.get('splurge_item') else 'no'}"
        )
        return {"fixture_name": fixture["name"], "output": output, "error": None}
    except Exception as e:
        logger.error(f"[{fixture['name']}] ideate_gifts failed: {e}")
        return {"fixture_name": fixture["name"], "output": None, "error": str(e)}
