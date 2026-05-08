"""
A/B comparison: current pipeline vs portrait-shaped curator.

For each fixture:
  1. Run current pipeline (gift_ideator.ideate_gifts) — control
  2. Run portrait curator (evals.portrait_ideator.ideate_gifts_portrait) — treatment
  3. Score both with judge v1 (existing dimensions)
  4. Score both with judge v2 (new portrait/synthesis dimensions)
  5. Print side-by-side scorecard

This is experiment #3 from the validation plan: "Curation-quality blind
taste test." If portrait beats current on portrait_coherence and
surprise_in_retrospect by a meaningful margin, the architectural bet is
real and we proceed with the agent-shape rebuild. If not, we rethink.

Usage:
  python run_curation_ab.py
  python run_curation_ab.py --fixture passionate_fly_fisher
  python run_curation_ab.py --control-only       # skip portrait, baseline run
  python run_curation_ab.py --treatment-only     # skip current, prototype run
  python run_curation_ab.py --portrait-model claude-sonnet-4-6  # cheaper test

Cost estimate per fixture (with Opus portrait + Sonnet control + Sonnet judges):
  ~$0.05-0.10. Five fixtures: ~$0.25-0.50. Acceptable for a validation test.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _client():
    from claude_meter import make_client
    return make_client(tag="run_curation_ab")


V1_DIMS = ["specificity", "evidence_grounding", "splurge_integrity", "ownership_avoidance", "diversity"]
V2_DIMS = ["synthesis", "composition_shape", "surprise_in_retrospect", "restraint", "portrait_coherence"]


def _fmt_score(s):
    if s is None:
        return "  -  "
    return f"{s}/5"


def _scorecard(results: list, mode: str):
    """mode: 'both' | 'control_only' | 'treatment_only'"""
    print()
    print("=" * 96)
    print(f"  Curation A/B  -  {datetime.now().strftime('%Y-%m-%d %H:%M')}  -  mode={mode}")
    print("=" * 96)

    for r in results:
        name = r["fixture_name"]
        print(f"\n  Fixture: {name}")

        if r.get("control_error"):
            print(f"    CONTROL ERROR: {r['control_error']}")
        if r.get("treatment_error"):
            print(f"    TREATMENT ERROR: {r['treatment_error']}")

        all_dims = V1_DIMS + V2_DIMS
        col_w = 22
        print(f"    {'dimension':<{col_w}} {'control':>10} {'treatment':>12} {'delta':>8}")
        print(f"    {'-'*col_w} {'-'*10:>10} {'-'*12:>12} {'-'*8:>8}")

        for dim in all_dims:
            c = r.get("control_scores", {}).get(dim, {}).get("score")
            t = r.get("treatment_scores", {}).get(dim, {}).get("score")
            delta = ""
            if c is not None and t is not None:
                d = t - c
                if d > 0:
                    delta = f"+{d}"
                else:
                    delta = str(d)
            print(f"    {dim:<{col_w}} {_fmt_score(c):>10} {_fmt_score(t):>12} {delta:>8}")

        # overall
        co = r.get("control_overall")
        to = r.get("treatment_overall")
        print(f"    {'OVERALL':<{col_w}} {_fmt_score(co):>10} {_fmt_score(to):>12}")

    print()
    print("=" * 96)
    # aggregate
    if mode == "both":
        ctotal, ttotal, n = 0.0, 0.0, 0
        for r in results:
            if r.get("control_overall") is not None and r.get("treatment_overall") is not None:
                ctotal += r["control_overall"]
                ttotal += r["treatment_overall"]
                n += 1
        if n:
            print(f"  AGGREGATE  control avg: {ctotal/n:.2f}    treatment avg: {ttotal/n:.2f}    "
                  f"lift: {(ttotal-ctotal)/n:+.2f}")
            print("=" * 96)
    print()


def _run_control(fixture, client, model):
    from evals.runner import run_fixture
    res = run_fixture(fixture, client, model)
    return res.get("output"), res.get("error")


def _run_treatment(fixture, client, model, voice_axis: float = 0.5):
    from evals.portrait_ideator import ideate_gifts_portrait
    try:
        out = ideate_gifts_portrait(
            profile=fixture["profile"],
            recipient_type=fixture["recipient_type"],
            relationship=fixture["relationship"],
            claude_client=client,
            rec_count=10,
            model=model,
            voice_axis=voice_axis,
        )
        if out.get("_parse_error"):
            return None, f"parse error: {out['_parse_error']}"
        return out, None
    except Exception as e:
        logger.exception("treatment failed")
        return None, str(e)


def _judge(fixture, output, client, judge_model):
    from evals.judge import score_output
    from evals.judge_v2 import score_output_v2
    v1 = score_output(fixture, output, client, judge_model)
    v2 = score_output_v2(fixture, output, client, judge_model)
    merged_scores = {**v1.get("scores", {}), **v2.get("scores", {})}
    numeric = [v["score"] for v in merged_scores.values()
               if isinstance(v.get("score"), (int, float))]
    overall = round(sum(numeric) / len(numeric), 2) if numeric else None
    return merged_scores, overall, (v1.get("error") or v2.get("error"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", help="run only this fixture")
    p.add_argument("--control-only", action="store_true")
    p.add_argument("--treatment-only", action="store_true")
    p.add_argument("--control-model", default=os.environ.get("CLAUDE_CURATOR_MODEL", "claude-sonnet-4-6"))
    p.add_argument("--portrait-model", default="claude-opus-4-7")
    p.add_argument("--judge-model", default="claude-sonnet-4-6")
    args = p.parse_args()

    from evals.fixtures import FIXTURES
    fixtures = FIXTURES
    if args.fixture:
        fixtures = [f for f in FIXTURES if f["name"] == args.fixture]
        if not fixtures:
            logger.error(f"No fixture named {args.fixture!r}")
            sys.exit(1)

    mode = "both"
    if args.control_only:
        mode = "control_only"
    elif args.treatment_only:
        mode = "treatment_only"

    client = _client()
    logger.info(f"control={args.control_model}  portrait={args.portrait_model}  judge={args.judge_model}  mode={mode}")

    results = []
    for fx in fixtures:
        logger.info(f"--- {fx['name']} ---")
        rec = {"fixture_name": fx["name"]}

        if mode != "treatment_only":
            logger.info("  control...")
            c_out, c_err = _run_control(fx, client, args.control_model)
            rec["control_error"] = c_err
            rec["control_output"] = c_out
            if c_out:
                scores, overall, jerr = _judge(fx, c_out, client, args.judge_model)
                rec["control_scores"] = scores
                rec["control_overall"] = overall
                if jerr:
                    rec["control_error"] = (rec.get("control_error") or "") + f" judge:{jerr}"

        if mode != "control_only":
            logger.info("  treatment (portrait)...")
            t_out, t_err = _run_treatment(fx, client, args.portrait_model)
            rec["treatment_error"] = t_err
            rec["treatment_output"] = t_out
            if t_out:
                scores, overall, jerr = _judge(fx, t_out, client, args.judge_model)
                rec["treatment_scores"] = scores
                rec["treatment_overall"] = overall
                if jerr:
                    rec["treatment_error"] = (rec.get("treatment_error") or "") + f" judge:{jerr}"

        results.append(rec)

    os.makedirs("evals/results", exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = f"evals/results/ab_{ts}.json"
    with open(out_path, "w") as f:
        slim = []
        for r in results:
            s = {k: v for k, v in r.items() if k not in ("control_output", "treatment_output")}
            s["control_summary"] = _summarize(r.get("control_output"))
            s["treatment_summary"] = _summarize(r.get("treatment_output"))
            slim.append(s)
        json.dump(slim, f, indent=2)
    logger.info(f"saved {out_path}")

    _scorecard(results, mode)


def _summarize(out):
    if not out:
        return None
    return {
        "concept_count": len(out.get("product_gifts", [])),
        "concept_names": [c.get("name") for c in out.get("product_gifts", [])],
        "splurge_name": out.get("splurge_item", {}).get("name") if out.get("splurge_item") else None,
        "has_portrait_prose": bool(out.get("portrait_prose")),
        "through_line_count": len(out.get("through_lines", [])),
        "restraint_count": len(out.get("restraint_omitted", [])),
    }


if __name__ == "__main__":
    main()
