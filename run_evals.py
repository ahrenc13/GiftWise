"""
GiftWise eval runner — CLI entry point.

Usage:
  python run_evals.py                        # run all fixtures
  python run_evals.py --fixture ceramics_artist  # run one fixture
  python run_evals.py --no-judge             # run pipeline only, skip scoring

Results written to evals/results/YYYY-MM-DD_HH-MM.json and evals/results/latest.json

Model selection:
  Pipeline uses CLAUDE_CURATOR_MODEL env var (default: claude-sonnet-4-6)
  Judge always uses claude-sonnet-4-6 (cost-efficient, adequate for scoring)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Add project root to path so we can import giftwise modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _get_client():
    try:
        import anthropic
        return anthropic.Anthropic()
    except ImportError:
        logger.error("anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to init Anthropic client: {e}")
        sys.exit(1)


def _print_scorecard(results: list):
    PASS = "\033[92m✓\033[0m"
    FLAG = "\033[93m⚠\033[0m"
    FAIL = "\033[91m✗\033[0m"
    DIMS = ["specificity", "evidence_grounding", "splurge_integrity", "ownership_avoidance", "diversity"]

    print()
    print("=" * 70)
    print("  GiftWise Eval Report —", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 70)

    passed = 0
    flagged = 0
    errored = 0

    for r in results:
        name = r["fixture_name"]
        error = r.get("run_error") or r.get("judge_error")

        if error:
            print(f"\n  {FAIL}  {name}")
            print(f"       ERROR: {error}")
            errored += 1
            continue

        scores = r.get("scores", {})
        overall = r.get("overall")
        flags = r.get("flags", [])

        status = PASS if not flags else FLAG
        overall_str = f"{overall}/5" if overall is not None else "n/a"
        print(f"\n  {status}  {name}  (overall: {overall_str})")

        for dim in DIMS:
            if dim not in scores:
                continue
            s = scores[dim]["score"]
            note = scores[dim].get("note", "")
            if s is None:
                bar = "  —  "
                indicator = " "
            else:
                bar = f"  {s}/5"
                indicator = "⚠ " if s < 3 else "  "
            dim_label = dim.replace("_", " ").ljust(22)
            print(f"       {indicator}{dim_label}{bar}  {note[:60]}")

        if flags:
            flagged += 1
        else:
            passed += 1

    print()
    print("-" * 70)
    print(f"  {passed} passed  |  {flagged} flagged  |  {errored} errored  "
          f"|  {len(results)} total")
    print("=" * 70)
    print()


def main():
    parser = argparse.ArgumentParser(description="Run GiftWise concept quality evals")
    parser.add_argument("--fixture", help="Run only this fixture by name")
    parser.add_argument("--no-judge", action="store_true", help="Skip judge scoring (pipeline only)")
    args = parser.parse_args()

    from evals.fixtures import FIXTURES
    from evals.runner import run_fixture
    from evals.judge import score_output

    fixtures = FIXTURES
    if args.fixture:
        fixtures = [f for f in FIXTURES if f["name"] == args.fixture]
        if not fixtures:
            logger.error(f"No fixture named '{args.fixture}'. Available: {[f['name'] for f in FIXTURES]}")
            sys.exit(1)

    pipeline_model = os.environ.get("CLAUDE_CURATOR_MODEL", "claude-sonnet-4-6")
    judge_model = "claude-sonnet-4-6"

    client = _get_client()

    logger.info(f"Running {len(fixtures)} fixture(s) with model={pipeline_model}")

    results = []
    for fixture in fixtures:
        logger.info(f"--- Fixture: {fixture['name']} ---")

        run_result = run_fixture(fixture, client, pipeline_model)
        output = run_result.get("output")
        run_error = run_result.get("error")

        record = {
            "fixture_name": fixture["name"],
            "description": fixture["description"],
            "failure_modes": fixture["failure_modes"],
            "run_error": run_error,
            "output_summary": None,
            "scores": {},
            "overall": None,
            "flags": [],
            "judge_error": None,
            "full_output": output,
        }

        if output:
            record["output_summary"] = {
                "concept_count": len(output.get("product_gifts", [])),
                "has_splurge": bool(output.get("splurge_item")),
                "has_portrait": bool(output.get("portrait")),
                "concept_names": [c.get("name") for c in output.get("product_gifts", [])],
                "splurge_name": output.get("splurge_item", {}).get("name") if output.get("splurge_item") else None,
            }

        if not args.no_judge and output:
            judge_result = score_output(fixture, output, client, judge_model)
            record["scores"] = judge_result.get("scores", {})
            record["overall"] = judge_result.get("overall")
            record["flags"] = judge_result.get("flags", [])
            record["judge_error"] = judge_result.get("error")

        results.append(record)

    # Write results
    os.makedirs("evals/results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = f"evals/results/{timestamp}.json"
    latest_path = "evals/results/latest.json"

    # Strip full_output from saved file to keep it readable (keep summary)
    save_results = [{k: v for k, v in r.items() if k != "full_output"} for r in results]
    with open(out_path, "w") as f:
        json.dump(save_results, f, indent=2)
    with open(latest_path, "w") as f:
        json.dump(save_results, f, indent=2)

    logger.info(f"Results saved to {out_path}")

    if not args.no_judge:
        _print_scorecard(results)
    else:
        print("\nPipeline-only run complete (no judge). Check logs above for concept names.")
        for r in results:
            summary = r.get("output_summary") or {}
            print(f"  {r['fixture_name']}: {summary.get('concept_count', 0)} concepts, "
                  f"splurge={'yes' if summary.get('has_splurge') else 'no'}")

    # Exit non-zero if any fixture flagged or errored
    any_bad = any(r.get("flags") or r.get("run_error") or r.get("judge_error") for r in results)
    sys.exit(1 if any_bad else 0)


if __name__ == "__main__":
    main()
