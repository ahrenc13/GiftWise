"""
Interactive review for A/B comparison results.

Walks the user through each fixture's control vs treatment output, prints
them side by side in the terminal, captures a blind human pick + a free-text
note, then writes one markdown artifact that contains:

  - run config
  - per-fixture scores (v1 + v2 judge dimensions, deltas)
  - per-fixture full outputs (portrait, through-lines, picks)
  - the human pick + note captured during review
  - aggregate judge lift and human-pick distribution
  - a "share this file with Claude" footer

The markdown file is the artifact the user shares with Claude after review.
No copy-paste of JSON, no toggling between windows.

Usage is via run_curation_ab.py --review or --review-only PATH.
"""

import json
import os
import sys
from datetime import datetime


# Terminal colors — degrade gracefully if not a TTY
def _supports_color():
    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


if _supports_color():
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    RESET = "\033[0m"
else:
    BOLD = DIM = CYAN = YELLOW = GREEN = RED = RESET = ""


V1_DIMS = ["specificity", "evidence_grounding", "splurge_integrity", "ownership_avoidance", "diversity"]
V2_DIMS = ["synthesis", "composition_shape", "surprise_in_retrospect", "restraint", "portrait_coherence"]
ALL_DIMS = V1_DIMS + V2_DIMS


def _hr(char="-", n=96):
    return char * n


def _box(title: str, body: str, color=CYAN):
    print(f"{color}{BOLD}{title}{RESET}")
    print(f"{color}{_hr('-')}{RESET}")
    print(body)
    print()


def _format_concepts(items, with_slot=False):
    if not items:
        return "  (none)"
    lines = []
    for i, c in enumerate(items, 1):
        slot = f" [{c.get('slot', '?')}]" if with_slot else ""
        lines.append(f"  {i:>2}.{slot} {c.get('name', '(unnamed)')}")
        why = c.get("why_perfect", "")
        if why:
            lines.append(f"      {DIM}{why[:160]}{RESET}")
    return "\n".join(lines)


def _format_splurge(s):
    if not s:
        return "  (no splurge)"
    return (
        f"  {s.get('name', '(unnamed)')}  ({s.get('price_range', '?')})\n"
        f"  {DIM}{s.get('why_perfect', '')[:200]}{RESET}"
    )


def _format_through_lines(tls):
    if not tls:
        return "  (none)"
    out = []
    for t in tls:
        out.append(f"  - {BOLD}{t.get('phrase', '?')}{RESET}: binds {t.get('binds', [])}")
        if t.get("why"):
            out.append(f"    {DIM}{t['why'][:160]}{RESET}")
    return "\n".join(out)


def _format_restraint(r):
    if not r:
        return "  (none stated)"
    return "\n".join(
        f"  - {x.get('signal', '?')}: {DIM}{x.get('why_held_back', '')[:140]}{RESET}"
        for x in r
    )


def _delta_str(c, t):
    if c is None or t is None:
        return ""
    d = t - c
    if d > 0:
        return f"{GREEN}+{d}{RESET}"
    if d < 0:
        return f"{RED}{d}{RESET}"
    return f"{DIM}0{RESET}"


def _print_scorecard(rec: dict):
    print(f"  {'dimension':<25} {'control':>10} {'treatment':>12} {'delta':>10}")
    print(f"  {_hr('-', 60)}")
    for dim in ALL_DIMS:
        c = rec.get("control_scores", {}).get(dim, {}).get("score")
        t = rec.get("treatment_scores", {}).get(dim, {}).get("score")
        c_s = f"{c}/5" if c is not None else "  -  "
        t_s = f"{t}/5" if t is not None else "  -  "
        marker = ""
        if dim in ("portrait_coherence", "surprise_in_retrospect"):
            marker = f" {YELLOW}*{RESET}"
        print(f"  {dim:<25} {c_s:>10} {t_s:>12} {_delta_str(c, t):>15}{marker}")
    co = rec.get("control_overall")
    to = rec.get("treatment_overall")
    co_s = f"{co}/5" if co is not None else "  -  "
    to_s = f"{to}/5" if to is not None else "  -  "
    print(f"  {_hr('-', 60)}")
    print(f"  {'OVERALL':<25} {co_s:>10} {to_s:>12} {_delta_str(co, to):>15}")
    print(f"  {DIM}* = headline metrics for the architectural bet{RESET}")


def _prompt_choice(prompt: str, choices: dict, default=None):
    """choices = {key: label}. Returns the key chosen."""
    keys = "/".join(f"[{k}]{v[0]}" if v else f"[{k}]" for k, v in choices.items())
    suffix = f" (default {default})" if default else ""
    while True:
        try:
            raw = input(f"{prompt} {keys}{suffix}: ").strip().lower()
        except EOFError:
            return default
        if not raw and default:
            return default
        if raw in choices:
            return raw
        print(f"  please pick one of: {', '.join(choices.keys())}")


def _prompt_line(prompt: str) -> str:
    try:
        return input(f"{prompt}: ").strip()
    except EOFError:
        return ""


def review_session(records: list, run_config: dict, results_dir: str = "evals/results") -> str:
    """
    Walk the user through each record, capture a human pick + note, and
    write a markdown artifact. Returns the path to the artifact.

    records: the list returned by run_curation_ab._run_all() — each item
             has fixture_name, control_*, treatment_*, and full outputs.
    """
    print()
    print(f"{BOLD}{CYAN}{_hr('=')}{RESET}")
    print(f"{BOLD}  GiftWise A/B Review — interactive{RESET}")
    print(f"{BOLD}{CYAN}{_hr('=')}{RESET}")
    print()
    print(f"For each fixture you will see:")
    print(f"  - the {BOLD}treatment{RESET} (portrait curator) outputs in full")
    print(f"  - the {BOLD}control{RESET} (current pipeline) concept names")
    print(f"  - judge scores from both v1 and v2 dimensions")
    print()
    print(f"You will be asked to pick blind which list reads more like")
    print(f"a person curated it, and to leave a one-line note.")
    print()
    print(f"{DIM}Tip: the human pick matters more than the judge scores.{RESET}")
    print()
    try:
        input("Press Enter to begin...")
    except EOFError:
        pass

    reviewed = []
    overall_notes = []

    for idx, rec in enumerate(records, 1):
        print()
        print(f"{BOLD}{CYAN}{_hr('=')}{RESET}")
        print(f"{BOLD}  Fixture {idx}/{len(records)}: {rec['fixture_name']}{RESET}")
        print(f"{BOLD}{CYAN}{_hr('=')}{RESET}")
        print()

        if rec.get("control_error"):
            print(f"  {RED}control error: {rec['control_error']}{RESET}")
        if rec.get("treatment_error"):
            print(f"  {RED}treatment error: {rec['treatment_error']}{RESET}")

        # Randomize which side is shown as "List A" vs "List B" so the
        # human pick is genuinely blind to which is treatment.
        # We use idx parity for reproducibility instead of random.
        flip = (idx % 2 == 0)
        a_label, b_label = ("control", "treatment") if not flip else ("treatment", "control")
        a_out = rec.get(f"{a_label}_output")
        b_out = rec.get(f"{b_label}_output")

        # Show treatment-specific fields (portrait, through-lines, restraint)
        # *under* both lists so the human can see the synthesis material
        # without knowing which side it came from. Actually — to keep the
        # pick truly blind, only show portrait/through-lines AFTER the pick.
        # Below, we show concept names + why_perfect first.

        if a_out:
            _box(f"List A — concept names",
                 _format_concepts(a_out.get("product_gifts", []), with_slot=False))
            _box(f"List A — splurge",
                 _format_splurge(a_out.get("splurge_item")))
        if b_out:
            _box(f"List B — concept names",
                 _format_concepts(b_out.get("product_gifts", []), with_slot=False))
            _box(f"List B — splurge",
                 _format_splurge(b_out.get("splurge_item")))

        if not a_out and not b_out:
            print(f"  {RED}both arms failed — skipping{RESET}")
            reviewed.append({**rec, "human_pick": None, "human_note": "both arms failed", "shown_as": {}})
            continue

        # Capture the blind pick
        print(f"{BOLD}  Which list reads more like a person curated it?{RESET}")
        pick = _prompt_choice(
            "  pick",
            {"a": "List A", "b": "List B", "s": "same / can't tell", "k": "skip"},
            default="k",
        )
        note = _prompt_line("  one-line note (or empty)")

        # Reveal which was which
        a_was = a_label
        b_was = b_label
        print()
        print(f"  {DIM}reveal: List A = {a_was}, List B = {b_was}{RESET}")
        if pick in ("a", "b"):
            picked_arm = a_was if pick == "a" else b_was
            print(f"  {GREEN}you picked: {picked_arm}{RESET}")
        elif pick == "s":
            picked_arm = "same"
        else:
            picked_arm = None

        # Now show treatment portrait + through-lines + restraint (the
        # synthesis material) and judge scores
        t_out = rec.get("treatment_output")
        if t_out:
            print()
            print(f"{BOLD}  Treatment metadata (only the portrait curator produces these){RESET}")
            print()
            _box("portrait_prose",
                 "  " + (t_out.get("portrait_prose") or "(none)").replace("\n", "\n  "))
            _box("through_lines", _format_through_lines(t_out.get("through_lines", [])))
            _box("restraint_omitted", _format_restraint(t_out.get("restraint_omitted", [])))

        print(f"{BOLD}  Judge scores{RESET}")
        print()
        _print_scorecard(rec)
        print()

        # Optional: did the judge agree with you?
        agreement = None
        if picked_arm in ("control", "treatment"):
            judge_pick = None
            co = rec.get("control_overall")
            to = rec.get("treatment_overall")
            if co is not None and to is not None:
                if to > co:
                    judge_pick = "treatment"
                elif co > to:
                    judge_pick = "control"
                else:
                    judge_pick = "tie"
            if judge_pick:
                if judge_pick == picked_arm:
                    print(f"  {GREEN}judge agrees with you ({judge_pick}){RESET}")
                    agreement = "agree"
                elif judge_pick == "tie":
                    print(f"  {YELLOW}judge sees a tie; you picked {picked_arm}{RESET}")
                    agreement = "tie"
                else:
                    print(f"  {YELLOW}judge picked {judge_pick}; you picked {picked_arm}{RESET}")
                    agreement = "disagree"

        reviewed.append({
            **rec,
            "human_pick": picked_arm,
            "human_note": note,
            "shown_as": {"A": a_was, "B": b_was},
            "judge_human_agreement": agreement,
        })

    print()
    print(f"{BOLD}{CYAN}{_hr('=')}{RESET}")
    print(f"{BOLD}  Wrap-up{RESET}")
    print(f"{BOLD}{CYAN}{_hr('=')}{RESET}")
    overall = _prompt_line("  overall reaction in 1-3 sentences (or empty)")

    # Write markdown artifact
    os.makedirs(results_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = os.path.join(results_dir, f"session_{ts}.md")
    latest_path = os.path.join(results_dir, "latest_session.md")
    md = _render_markdown(reviewed, run_config, overall, ts)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(md)

    print()
    print(f"  {GREEN}saved review:{RESET} {out_path}")
    print(f"  {GREEN}also at:    {RESET} {latest_path}")
    print()
    print(f"  Share with Claude by saying:")
    print(f"    {BOLD}\"read evals/results/latest_session.md\"{RESET}")
    print()
    return out_path


def _render_markdown(reviewed: list, run_config: dict, overall: str, ts: str) -> str:
    lines = []
    lines.append(f"# GiftWise A/B Review Session — {ts}\n")
    lines.append("## Run config\n")
    for k, v in run_config.items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append("")

    # Aggregate
    human_picks = [r.get("human_pick") for r in reviewed]
    human_treatment = sum(1 for p in human_picks if p == "treatment")
    human_control = sum(1 for p in human_picks if p == "control")
    human_same = sum(1 for p in human_picks if p == "same")
    human_skip = sum(1 for p in human_picks if p in (None,))

    lines.append("## Aggregate\n")
    lines.append("### Human picks (blind)\n")
    lines.append(f"- treatment: **{human_treatment}**")
    lines.append(f"- control: **{human_control}**")
    lines.append(f"- same / can't tell: **{human_same}**")
    lines.append(f"- skipped / errored: **{human_skip}**")
    lines.append("")

    # judge averages
    c_overalls = [r.get("control_overall") for r in reviewed if r.get("control_overall") is not None]
    t_overalls = [r.get("treatment_overall") for r in reviewed if r.get("treatment_overall") is not None]
    if c_overalls and t_overalls:
        c_avg = sum(c_overalls) / len(c_overalls)
        t_avg = sum(t_overalls) / len(t_overalls)
        lines.append("### Judge overall averages\n")
        lines.append(f"- control avg: **{c_avg:.2f}/5**")
        lines.append(f"- treatment avg: **{t_avg:.2f}/5**")
        lines.append(f"- lift: **{t_avg - c_avg:+.2f}**")
        lines.append("")

    # Headline dim deltas
    lines.append("### Headline dimension averages (the architectural bet)\n")
    for dim in ("portrait_coherence", "surprise_in_retrospect"):
        c_scores = [r.get("control_scores", {}).get(dim, {}).get("score") for r in reviewed]
        c_scores = [s for s in c_scores if isinstance(s, (int, float))]
        t_scores = [r.get("treatment_scores", {}).get(dim, {}).get("score") for r in reviewed]
        t_scores = [s for s in t_scores if isinstance(s, (int, float))]
        if c_scores and t_scores:
            ca = sum(c_scores) / len(c_scores)
            ta = sum(t_scores) / len(t_scores)
            lines.append(f"- **{dim}**: control {ca:.2f} -> treatment {ta:.2f}  (lift {ta - ca:+.2f})")
    lines.append("")
    lines.append("### Decision-rule check\n")
    lines.append("From the validation plan:")
    lines.append("- portrait_coherence lift >= 1.0 AND surprise_in_retrospect lift >= 0.5 -> **bet is real**")
    lines.append("- mixed -> iterate prompt")
    lines.append("- no lift -> re-plan agent shape")
    lines.append("")

    if overall:
        lines.append("## Overall human reaction\n")
        lines.append(f"> {overall}\n")

    # Per-fixture
    lines.append("## Per-fixture detail\n")
    for r in reviewed:
        lines.append(f"### {r['fixture_name']}\n")
        if r.get("human_pick"):
            lines.append(f"**Human blind pick:** `{r['human_pick']}`")
        if r.get("human_note"):
            lines.append(f"**Human note:** {r['human_note']}")
        if r.get("judge_human_agreement"):
            lines.append(f"**Judge/human agreement:** `{r['judge_human_agreement']}`")
        lines.append("")

        # scorecard
        lines.append("| dimension | control | treatment | delta |")
        lines.append("|---|---|---|---|")
        for dim in ALL_DIMS:
            c = r.get("control_scores", {}).get(dim, {}).get("score")
            t = r.get("treatment_scores", {}).get(dim, {}).get("score")
            cs = f"{c}/5" if c is not None else "—"
            ts_ = f"{t}/5" if t is not None else "—"
            d = ""
            if c is not None and t is not None:
                d_n = t - c
                d = f"{d_n:+d}"
            star = " ⭐" if dim in ("portrait_coherence", "surprise_in_retrospect") else ""
            lines.append(f"| `{dim}`{star} | {cs} | {ts_} | {d} |")
        co = r.get("control_overall")
        to = r.get("treatment_overall")
        cs = f"{co:.2f}" if co is not None else "—"
        ts_ = f"{to:.2f}" if to is not None else "—"
        d = ""
        if co is not None and to is not None:
            d = f"{to - co:+.2f}"
        lines.append(f"| **OVERALL** | **{cs}** | **{ts_}** | **{d}** |")
        lines.append("")

        # Concepts side by side
        c_out = r.get("control_output")
        t_out = r.get("treatment_output")
        if c_out:
            lines.append("**Control concepts:**")
            for i, c in enumerate(c_out.get("product_gifts", []), 1):
                lines.append(f"{i}. {c.get('name', '?')} — _{(c.get('why_perfect') or '')[:160]}_")
            sp = c_out.get("splurge_item")
            if sp:
                lines.append(f"- **splurge:** {sp.get('name', '?')} ({sp.get('price_range', '?')}) — _{(sp.get('why_perfect') or '')[:160]}_")
            lines.append("")
        if t_out:
            lines.append("**Treatment concepts:**")
            for i, c in enumerate(t_out.get("product_gifts", []), 1):
                slot = f" `[{c.get('slot', '?')}]`" if c.get("slot") else ""
                lines.append(f"{i}.{slot} {c.get('name', '?')} — _{(c.get('why_perfect') or '')[:160]}_")
            sp = t_out.get("splurge_item")
            if sp:
                lines.append(f"- **splurge:** {sp.get('name', '?')} ({sp.get('price_range', '?')}) — _{(sp.get('why_perfect') or '')[:160]}_")
            lines.append("")

            # Treatment metadata
            if t_out.get("portrait_prose"):
                lines.append("**Portrait prose:**")
                lines.append(f"> {t_out['portrait_prose']}")
                lines.append("")
            if t_out.get("through_lines"):
                lines.append("**Through-lines:**")
                for tl in t_out["through_lines"]:
                    binds = ", ".join(tl.get("binds", []))
                    lines.append(f"- **{tl.get('phrase', '?')}** (binds: {binds}) — _{tl.get('why', '')}_")
                lines.append("")
            if t_out.get("restraint_omitted"):
                lines.append("**Restraint (signals deliberately not made literal):**")
                for ro in t_out["restraint_omitted"]:
                    lines.append(f"- **{ro.get('signal', '?')}** — _{ro.get('why_held_back', '')}_")
                lines.append("")

        # judge notes
        notes_lines = []
        for dim in ALL_DIMS:
            for arm in ("control", "treatment"):
                n = r.get(f"{arm}_scores", {}).get(dim, {}).get("note")
                if n:
                    notes_lines.append(f"- `{arm}.{dim}`: {n}")
        if notes_lines:
            lines.append("<details><summary>judge notes per dimension</summary>")
            lines.append("")
            lines.extend(notes_lines)
            lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_This file is the artifact for sharing with Claude. Reference it as_ `evals/results/latest_session.md`.")
    return "\n".join(lines)
