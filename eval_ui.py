"""
Bare-bones web UI for the curation A/B review.

Standalone Flask app on port 5001. Does NOT import giftwise_app (which
hits a Windows fcntl issue). Imports only the eval modules.

Pages:
  /                    — fixture list, run buttons, status, save button
  /run/<fixture>       — POST: runs A/B for one fixture (blocks ~30s), redirects
  /review/<fixture>    — blind side-by-side, pick + note form
  /pick/<fixture>      — POST: stores pick + note, redirects to /reveal
  /reveal/<fixture>    — reveal + scores + treatment metadata + next button
  /save                — POST: writes evals/results/latest_session.md and shows path

State persists in evals/results/ui_state.json so refreshes are safe.

Run with:
  python eval_ui.py
Then open http://localhost:5001
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime

from flask import Flask, render_template_string, request, redirect, url_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evals.fixtures import FIXTURES
from run_curation_ab import _run_control, _run_treatment, _judge, V1_DIMS, V2_DIMS

ALL_DIMS = V1_DIMS + V2_DIMS
STATE_PATH = "evals/results/ui_state.json"
LATEST_MD = "evals/results/latest_session.md"
RESULTS_DIR = "evals/results"

CONTROL_MODEL = os.environ.get("CLAUDE_CURATOR_MODEL", "claude-sonnet-4-6")
PORTRAIT_MODEL = os.environ.get("PORTRAIT_MODEL", "claude-opus-4-7")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-6")


def _voice_label(v: float) -> str:
    if v <= 0.2: return "practical"
    if v <= 0.4: return "leans practical"
    if v <= 0.6: return "balanced"
    if v <= 0.8: return "leans taste-edited"
    return "taste-edited"


def _client():
    from claude_meter import make_client
    return make_client(tag="eval_ui")


def _load_state():
    if not os.path.exists(STATE_PATH):
        return {"fixtures": {}, "overall_note": ""}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_state(state):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _blind_flip(name: str) -> bool:
    """Deterministic per-fixture: True means swap A and B (treatment shown as A)."""
    h = hashlib.md5(name.encode()).hexdigest()
    return int(h, 16) % 2 == 1


def _sides(fixture_name: str):
    """Return ((label_for_A, arm_A), (label_for_B, arm_B))."""
    if _blind_flip(fixture_name):
        return ("A", "treatment"), ("B", "control")
    return ("A", "control"), ("B", "treatment")


def _delta(c, t):
    if c is None or t is None:
        return ""
    d = t - c
    return f"{d:+d}" if isinstance(d, int) else f"{d:+.2f}"


app = Flask(__name__)


# ---------- pages ----------

HOME_HTML = """
<!doctype html>
<html><head><title>GiftWise eval</title>
<style>
  body { font: 15px/1.5 -apple-system, Segoe UI, sans-serif; max-width: 880px; margin: 32px auto; padding: 0 16px; color: #222; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  .sub { color: #666; margin-bottom: 24px; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; }
  th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #eee; vertical-align: top; }
  th { background: #fafafa; font-size: 12px; text-transform: uppercase; letter-spacing: .5px; color: #888; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
  .pill-pending { background: #f1f1f1; color: #888; }
  .pill-done { background: #e6f4ea; color: #1e7a3a; }
  .pill-err { background: #fde7e7; color: #b3261e; }
  button, .btn { font: inherit; padding: 6px 14px; border: 1px solid #ccc; border-radius: 6px; background: white; cursor: pointer; text-decoration: none; color: #222; display: inline-block; }
  button.primary, .btn.primary { background: #2c5cff; color: white; border-color: #2c5cff; }
  .config { background: #f8f8fa; padding: 12px 14px; border-radius: 6px; font-size: 13px; color: #444; margin-bottom: 16px; }
  .agg { display: flex; gap: 24px; margin-top: 24px; padding: 16px; background: #fafafa; border-radius: 8px; font-size: 14px; }
  .agg div b { display: block; font-size: 22px; color: #222; }
  .agg div span { color: #666; font-size: 12px; }
  .save { margin-top: 32px; padding-top: 24px; border-top: 1px solid #eee; }
</style></head>
<body>
<h1>GiftWise — Curation A/B</h1>
<div class="sub">Experiment #3: portrait-shaped curator vs current pipeline. Run each fixture, blind-pick, save.</div>

<div class="config">
  <b>Models:</b> control=<code>{{control_model}}</code> · portrait=<code>{{portrait_model}}</code> · judge=<code>{{judge_model}}</code>
  <br><span style="color:#888;font-size:12px;">Set <code>PORTRAIT_MODEL</code> / <code>CLAUDE_CURATOR_MODEL</code> / <code>JUDGE_MODEL</code> env vars to change.</span>
  <form action="/toggle-blind" method="post" style="margin-top:10px;">
    <label style="cursor:pointer;">
      <input type="checkbox" name="blind" {% if judge_blind %}checked{% endif %} onchange="this.form.submit()">
      <b>Judge-blind mode</b> — hide portrait_prose, through_lines, restraint_omitted from the judge so it scores picks alone.
      Currently: <b>{% if judge_blind %}ON{% else %}OFF{% endif %}</b>.
    </label>
    <br><span style="color:#888;font-size:12px;">Re-run any fixture after changing this; previous scores are kept until then.</span>
  </form>
  <form action="/set-voice" method="post" style="margin-top:14px; padding-top:10px; border-top: 1px dashed #ddd;">
    <label style="cursor:pointer;">
      <b>Voice axis</b> — current curator voice for treatment runs.
      Currently: <b>{{ '%.2f' % voice_axis }} ({{ voice_label }})</b>
    </label>
    <div style="display:flex;align-items:center;gap:10px;margin-top:6px;">
      <input type="range" name="voice_axis" min="0" max="1" step="0.05" value="{{voice_axis}}" style="flex:1;" oninput="document.getElementById('vlabel').textContent = parseFloat(this.value).toFixed(2)">
      <span id="vlabel" style="font-family:monospace;min-width:40px;">{{ '%.2f' % voice_axis }}</span>
      <button type="submit">Set</button>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#888;margin-top:2px;">
      <span>0.00 — practical</span><span>balanced</span><span>1.00 — taste-edited</span>
    </div>
    <span style="color:#888;font-size:12px;display:block;margin-top:6px;">Re-run any fixture after changing voice. Treatment metadata (portrait, through-lines, restraint) stays in all modes; only pick selection shifts.</span>
  </form>
</div>

<table>
<tr><th>Fixture</th><th>Status</th><th>Your pick</th><th>Judge pick</th><th>Action</th></tr>
{% for f in fixtures %}
  {% set s = state.fixtures.get(f.name, {}) %}
  <tr>
    <td>
      <b>{{f.name}}</b>
      <div style="color:#888;font-size:12px;">{{f.description}}</div>
    </td>
    <td>
      {% if s.get('control_error') or s.get('treatment_error') %}
        <span class="pill pill-err">error</span>
      {% elif s.get('control_overall') is not none and s.get('treatment_overall') is not none %}
        <span class="pill pill-done">scored</span>
      {% elif s.get('control_output') or s.get('treatment_output') %}
        <span class="pill pill-pending">partial</span>
      {% else %}
        <span class="pill pill-pending">not run</span>
      {% endif %}
      {% if s.get('judge_blind_used') %}<br><span style="font-size:11px;color:#888;">judge-blind</span>{% endif %}
    </td>
    <td>
      {% if s.get('human_pick') %}<code>{{s.human_pick}}</code>{% else %}—{% endif %}
    </td>
    <td>
      {% set co = s.get('control_overall') %}{% set to = s.get('treatment_overall') %}
      {% if co is not none and to is not none %}
        {% if to > co %}treatment (+{{ '%.2f' % (to - co) }}){% elif co > to %}control (+{{ '%.2f' % (co - to) }}){% else %}tie{% endif %}
      {% else %}—{% endif %}
    </td>
    <td>
      <form action="/run/{{f.name}}" method="post" style="display:inline">
        <button>{% if s.get('control_overall') %}Re-run{% else %}Run{% endif %}</button>
      </form>
      {% if s.get('control_output') and s.get('treatment_output') and not s.get('human_pick') %}
        <a class="btn primary" href="/review/{{f.name}}">Review</a>
      {% elif s.get('human_pick') %}
        <a class="btn" href="/reveal/{{f.name}}">View</a>
      {% endif %}
    </td>
  </tr>
{% endfor %}
</table>

{% if any_done %}
<div class="agg">
  <div><b>{{ human_treatment }}</b><span>human → treatment</span></div>
  <div><b>{{ human_control }}</b><span>human → control</span></div>
  <div><b>{{ human_same }}</b><span>same / can't tell</span></div>
  {% if avg_lift is not none %}
    <div><b>{{ '%+.2f' % avg_lift }}</b><span>judge avg lift</span></div>
  {% endif %}
  {% if pc_lift is not none %}
    <div><b>{{ '%+.2f' % pc_lift }}</b><span>portrait_coherence lift</span></div>
  {% endif %}
  {% if sir_lift is not none %}
    <div><b>{{ '%+.2f' % sir_lift }}</b><span>surprise_in_retrospect lift</span></div>
  {% endif %}
</div>
{% endif %}

<div class="save">
  <form action="/save" method="post">
    <label>Overall reaction (1–3 sentences, optional):</label><br>
    <textarea name="overall_note" rows="3" style="width:100%;font:inherit;padding:8px;margin-top:6px;">{{state.overall_note or ''}}</textarea><br>
    <button class="primary" style="margin-top:8px;">Save session → markdown</button>
  </form>
  {% if last_saved %}<div style="color:#1e7a3a;margin-top:8px;font-size:13px;">Saved to <code>{{last_saved}}</code></div>{% endif %}
</div>

</body></html>
"""


REVIEW_HTML = """
<!doctype html>
<html><head><title>Review · {{fixture_name}}</title>
<style>
  body { font: 15px/1.5 -apple-system, Segoe UI, sans-serif; max-width: 1100px; margin: 32px auto; padding: 0 16px; color: #222; }
  h1 { font-size: 20px; }
  .sub { color: #666; font-size: 13px; margin-bottom: 16px; }
  .cols { display: flex; gap: 16px; }
  .col { flex: 1; border: 1px solid #e5e5e5; border-radius: 8px; padding: 16px; background: white; }
  .col h2 { margin: 0 0 12px; font-size: 16px; }
  ol { padding-left: 24px; margin: 0; }
  ol li { margin-bottom: 10px; }
  .why { color: #555; font-size: 13px; margin-top: 4px; line-height: 1.45; }
  .splurge { margin-top: 16px; padding: 12px; background: #fff8e1; border-radius: 6px; font-size: 14px; }
  form.pick { margin-top: 24px; padding: 16px; background: #f8f8fa; border-radius: 8px; }
  form.pick label { display: inline-block; margin-right: 16px; cursor: pointer; }
  textarea { width: 100%; padding: 8px; font: inherit; margin-top: 8px; }
  button.primary { background: #2c5cff; color: white; border: 1px solid #2c5cff; padding: 8px 16px; border-radius: 6px; font: inherit; cursor: pointer; }
  a { color: #2c5cff; }
</style></head>
<body>
<h1>{{fixture_name}}</h1>
<div class="sub">{{fixture.description}}</div>
<div class="sub"><a href="/">← back to all fixtures</a></div>

<p><b>Read both lists. Which one reads more like a person curated it for {{relationship_phrase}}?</b><br>
<span style="color:#888;font-size:13px;">A and B are randomized — you don't know which is the new portrait curator and which is the current pipeline.</span></p>

<div class="cols">
  <div class="col">
    <h2>List {{a_label}}</h2>
    <ol>
    {% for c in a_concepts %}
      <li>{{c.name}}<div class="why">{{c.why_perfect or ''}}</div></li>
    {% endfor %}
    </ol>
    {% if a_splurge %}
      <div class="splurge"><b>splurge ({{a_splurge.price_range}}):</b> {{a_splurge.name}}<div class="why">{{a_splurge.why_perfect or ''}}</div></div>
    {% endif %}
  </div>
  <div class="col">
    <h2>List {{b_label}}</h2>
    <ol>
    {% for c in b_concepts %}
      <li>{{c.name}}<div class="why">{{c.why_perfect or ''}}</div></li>
    {% endfor %}
    </ol>
    {% if b_splurge %}
      <div class="splurge"><b>splurge ({{b_splurge.price_range}}):</b> {{b_splurge.name}}<div class="why">{{b_splurge.why_perfect or ''}}</div></div>
    {% endif %}
  </div>
</div>

<form class="pick" action="/pick/{{fixture_name}}" method="post">
  <div><b>Which list?</b></div>
  <div style="margin-top:8px;">
    <label><input type="radio" name="pick" value="A" required> A</label>
    <label><input type="radio" name="pick" value="B"> B</label>
    <label><input type="radio" name="pick" value="same"> same / can't tell</label>
  </div>
  <label style="display:block;margin-top:14px;">One-line note (what tipped it for you, optional):
    <textarea name="note" rows="2"></textarea>
  </label>
  <button class="primary" style="margin-top:8px;">Submit pick → see reveal</button>
</form>

</body></html>
"""


REVEAL_HTML = """
<!doctype html>
<html><head><title>Reveal · {{fixture_name}}</title>
<style>
  body { font: 15px/1.5 -apple-system, Segoe UI, sans-serif; max-width: 1100px; margin: 32px auto; padding: 0 16px; color: #222; }
  h1 { font-size: 20px; }
  .sub { color: #666; font-size: 13px; margin-bottom: 16px; }
  .reveal { padding: 14px; background: #e6f4ea; border-radius: 8px; margin: 16px 0; font-size: 15px; }
  .reveal.disagree { background: #fff4e0; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
  th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; }
  th { background: #fafafa; font-size: 12px; text-transform: uppercase; color: #888; }
  td.dim-headline { font-weight: bold; }
  .delta-pos { color: #1e7a3a; font-weight: 600; }
  .delta-neg { color: #b3261e; font-weight: 600; }
  .delta-zero { color: #888; }
  .meta { padding: 14px; background: #f5f3ff; border-radius: 8px; margin: 12px 0; font-size: 14px; }
  .meta h3 { margin: 4px 0 8px; font-size: 14px; }
  .actions { margin-top: 24px; display: flex; gap: 12px; }
  .btn { font: inherit; padding: 8px 14px; border: 1px solid #ccc; border-radius: 6px; background: white; cursor: pointer; text-decoration: none; color: #222; display: inline-block; }
  .btn.primary { background: #2c5cff; color: white; border-color: #2c5cff; }
  details { margin: 8px 0; }
  summary { cursor: pointer; color: #2c5cff; font-size: 13px; }
</style></head>
<body>
<h1>{{fixture_name}} — reveal</h1>
<div class="sub"><a href="/">← back to all fixtures</a></div>

<div class="reveal {{ 'disagree' if disagreement else '' }}">
  <b>List A was {{ a_arm }}, List B was {{ b_arm }}.</b><br>
  You picked: <code>{{ human_pick }}</code>{% if note %} · note: <i>{{note}}</i>{% endif %}<br>
  Judge picked: <code>{{ judge_pick }}</code> · {{ agreement_text }}
</div>

<h2 style="font-size:16px;">Judge scores</h2>
<table>
<tr><th>dimension</th><th>control</th><th>treatment</th><th>delta</th><th style="width:50%;">judge note</th></tr>
{% for row in score_rows %}
  <tr>
    <td class="{{ 'dim-headline' if row.headline else '' }}">{{row.dim}}{% if row.headline %} ⭐{% endif %}</td>
    <td>{{row.c_str}}</td>
    <td>{{row.t_str}}</td>
    <td class="{{row.delta_class}}">{{row.delta}}</td>
    <td style="font-size:13px;color:#555;">{{row.note}}</td>
  </tr>
{% endfor %}
<tr style="border-top:2px solid #ccc;"><td><b>OVERALL</b></td><td><b>{{ '%.2f' % control_overall if control_overall is not none else '—' }}</b></td><td><b>{{ '%.2f' % treatment_overall if treatment_overall is not none else '—' }}</b></td><td class="{{overall_delta_class}}"><b>{{overall_delta}}</b></td><td></td></tr>
</table>

{% if portrait_prose or through_lines or restraint %}
<div class="meta">
  <h3>Treatment-only metadata (the portrait curator's reasoning)</h3>
  {% if portrait_prose %}
    <p><b>portrait_prose:</b><br>{{portrait_prose}}</p>
  {% endif %}
  {% if through_lines %}
    <b>through_lines:</b>
    <ul>{% for tl in through_lines %}<li><b>{{tl.phrase}}</b> (binds: {{', '.join(tl.binds or [])}}) — {{tl.why}}</li>{% endfor %}</ul>
  {% endif %}
  {% if restraint %}
    <b>restraint_omitted:</b>
    <ul>{% for r in restraint %}<li><b>{{r.signal}}</b> — {{r.why_held_back}}</li>{% endfor %}</ul>
  {% endif %}
</div>
{% endif %}

<details>
<summary>Show full concept lists with why_perfect</summary>
<div style="display:flex;gap:16px;margin-top:12px;">
  <div style="flex:1;"><h4>Control</h4>
  <ol>{% for c in control_concepts %}<li>{{c.name}}<div style="color:#666;font-size:12px;">{{c.why_perfect}}</div></li>{% endfor %}</ol>
  </div>
  <div style="flex:1;"><h4>Treatment</h4>
  <ol>{% for c in treatment_concepts %}<li>{% if c.slot %}<code style="font-size:11px;color:#888;">[{{c.slot}}]</code> {% endif %}{{c.name}}<div style="color:#666;font-size:12px;">{{c.why_perfect}}</div></li>{% endfor %}</ol>
  </div>
</div>
</details>

<div class="actions">
  <a class="btn" href="/">← all fixtures</a>
  {% if next_fixture %}<a class="btn primary" href="/review/{{next_fixture}}">Next: {{next_fixture}} →</a>{% else %}<a class="btn primary" href="/">Done — back to home</a>{% endif %}
</div>

</body></html>
"""


# ---------- helpers ----------

def _aggregate(state):
    fxs = state.get("fixtures", {})
    human_picks = [s.get("human_pick") for s in fxs.values()]
    human_treatment = sum(1 for p in human_picks if p == "treatment")
    human_control = sum(1 for p in human_picks if p == "control")
    human_same = sum(1 for p in human_picks if p == "same")

    cs = [s.get("control_overall") for s in fxs.values() if s.get("control_overall") is not None]
    ts = [s.get("treatment_overall") for s in fxs.values() if s.get("treatment_overall") is not None]
    avg_lift = (sum(ts) / len(ts) - sum(cs) / len(cs)) if cs and ts else None

    def _dim_lift(dim):
        cs_ = [s.get("control_scores", {}).get(dim, {}).get("score") for s in fxs.values()]
        ts_ = [s.get("treatment_scores", {}).get(dim, {}).get("score") for s in fxs.values()]
        cs_ = [x for x in cs_ if isinstance(x, (int, float))]
        ts_ = [x for x in ts_ if isinstance(x, (int, float))]
        if not cs_ or not ts_:
            return None
        return sum(ts_) / len(ts_) - sum(cs_) / len(cs_)

    return {
        "human_treatment": human_treatment,
        "human_control": human_control,
        "human_same": human_same,
        "avg_lift": avg_lift,
        "pc_lift": _dim_lift("portrait_coherence"),
        "sir_lift": _dim_lift("surprise_in_retrospect"),
        "any_done": bool(cs and ts),
    }


def _next_fixture(current_name):
    names = [f["name"] for f in FIXTURES]
    try:
        idx = names.index(current_name)
        return names[idx + 1] if idx + 1 < len(names) else None
    except ValueError:
        return None


# ---------- routes ----------

@app.route("/")
def home():
    state = _load_state()
    agg = _aggregate(state)
    voice_axis = state.get("voice_axis", 0.5)
    return render_template_string(
        HOME_HTML,
        fixtures=FIXTURES,
        state=state,
        control_model=CONTROL_MODEL,
        portrait_model=PORTRAIT_MODEL,
        judge_model=JUDGE_MODEL,
        last_saved=state.get("last_saved"),
        judge_blind=state.get("judge_blind", False),
        voice_axis=voice_axis,
        voice_label=_voice_label(voice_axis),
        **agg,
    )


@app.route("/toggle-blind", methods=["POST"])
def toggle_blind():
    state = _load_state()
    state["judge_blind"] = bool(request.form.get("blind"))
    _save_state(state)
    return redirect(url_for("home"))


@app.route("/set-voice", methods=["POST"])
def set_voice():
    state = _load_state()
    try:
        v = float(request.form.get("voice_axis", 0.5))
        v = max(0.0, min(1.0, v))
    except (TypeError, ValueError):
        v = 0.5
    state["voice_axis"] = v
    _save_state(state)
    return redirect(url_for("home"))


@app.route("/run/<fixture_name>", methods=["POST"])
def run_one(fixture_name):
    fixture = next((f for f in FIXTURES if f["name"] == fixture_name), None)
    if not fixture:
        return f"unknown fixture: {fixture_name}", 404

    state = _load_state()
    state.setdefault("fixtures", {})

    client = _client()
    voice_axis = state.get("voice_axis", 0.5)
    logger.info(f"[{fixture_name}] running control with {CONTROL_MODEL}")
    c_out, c_err = _run_control(fixture, client, CONTROL_MODEL)
    logger.info(f"[{fixture_name}] running treatment with {PORTRAIT_MODEL} (voice_axis={voice_axis:.2f})")
    t_out, t_err = _run_treatment(fixture, client, PORTRAIT_MODEL, voice_axis=voice_axis)

    rec = {
        "fixture_name": fixture_name,
        "control_output": c_out,
        "control_error": c_err,
        "treatment_output": t_out,
        "treatment_error": t_err,
    }

    judge_blind = state.get("judge_blind", False)
    rec["judge_blind_used"] = judge_blind
    rec["voice_axis_used"] = state.get("voice_axis", 0.5)

    if c_out:
        scores, overall, jerr = _judge(fixture, c_out, client, JUDGE_MODEL)
        rec["control_scores"] = scores
        rec["control_overall"] = overall
        if jerr:
            rec["control_error"] = (rec.get("control_error") or "") + f" judge:{jerr}"
    if t_out:
        # Judge-blind: hide treatment-only metadata (portrait, through_lines,
        # restraint) from the judge so it scores the picks alone, not the
        # synthesis material the architecture was designed to produce.
        if judge_blind:
            t_for_judge = dict(t_out)
            t_for_judge["portrait_prose"] = None
            t_for_judge["through_lines"] = []
            t_for_judge["restraint_omitted"] = []
            for c in t_for_judge.get("product_gifts", []):
                c.pop("slot", None)
                c.pop("signals_engaged", None)
        else:
            t_for_judge = t_out
        scores, overall, jerr = _judge(fixture, t_for_judge, client, JUDGE_MODEL)
        rec["treatment_scores"] = scores
        rec["treatment_overall"] = overall
        if jerr:
            rec["treatment_error"] = (rec.get("treatment_error") or "") + f" judge:{jerr}"

    # Re-runs produce new lists, so the prior human pick no longer applies
    # to the content being shown. Clear it; the user re-reviews.
    rec["human_pick"] = None
    rec["human_note"] = None

    state["fixtures"][fixture_name] = rec
    _save_state(state)

    # Send to review whenever at least one side has concepts — if the other
    # side errored, the review page will show what we have plus the error.
    has_content = bool(
        (c_out and c_out.get("product_gifts")) or
        (t_out and t_out.get("product_gifts"))
    )
    if has_content:
        return redirect(url_for("review", fixture_name=fixture_name))
    return redirect(url_for("home"))


@app.route("/review/<fixture_name>")
def review(fixture_name):
    state = _load_state()
    fixture = next((f for f in FIXTURES if f["name"] == fixture_name), None)
    rec = state.get("fixtures", {}).get(fixture_name)
    if not fixture or not rec:
        return redirect(url_for("home"))

    a_label, a_arm = _sides(fixture_name)[0]
    b_label, b_arm = _sides(fixture_name)[1]
    a_out = rec.get(f"{a_arm}_output") or {}
    b_out = rec.get(f"{b_arm}_output") or {}

    relationship_phrase = {
        "close_friend": "a close friend",
        "romantic_partner": "their romantic partner",
        "family_member": "a family member",
    }.get(fixture.get("relationship", ""), "this person")

    return render_template_string(
        REVIEW_HTML,
        fixture_name=fixture_name,
        fixture=fixture,
        a_label="A", b_label="B",
        a_concepts=a_out.get("product_gifts", []),
        b_concepts=b_out.get("product_gifts", []),
        a_splurge=a_out.get("splurge_item"),
        b_splurge=b_out.get("splurge_item"),
        relationship_phrase=relationship_phrase,
    )


@app.route("/pick/<fixture_name>", methods=["POST"])
def pick(fixture_name):
    state = _load_state()
    rec = state.get("fixtures", {}).get(fixture_name)
    if not rec:
        return redirect(url_for("home"))

    raw_pick = request.form.get("pick", "").strip()
    note = request.form.get("note", "").strip()

    a_arm = _sides(fixture_name)[0][1]
    b_arm = _sides(fixture_name)[1][1]
    if raw_pick == "A":
        human_pick = a_arm
    elif raw_pick == "B":
        human_pick = b_arm
    elif raw_pick == "same":
        human_pick = "same"
    else:
        human_pick = None

    rec["human_pick"] = human_pick
    rec["human_note"] = note
    state["fixtures"][fixture_name] = rec
    _save_state(state)
    return redirect(url_for("reveal", fixture_name=fixture_name))


@app.route("/reveal/<fixture_name>")
def reveal(fixture_name):
    state = _load_state()
    rec = state.get("fixtures", {}).get(fixture_name)
    if not rec:
        return redirect(url_for("home"))

    a_arm = _sides(fixture_name)[0][1]
    b_arm = _sides(fixture_name)[1][1]
    co = rec.get("control_overall")
    to = rec.get("treatment_overall")
    if co is not None and to is not None:
        if to > co:
            judge_pick = "treatment"
        elif co > to:
            judge_pick = "control"
        else:
            judge_pick = "tie"
    else:
        judge_pick = "—"

    human = rec.get("human_pick")
    if human in ("control", "treatment") and judge_pick in ("control", "treatment"):
        if human == judge_pick:
            agreement_text = "you agree"
            disagreement = False
        else:
            agreement_text = "you disagree"
            disagreement = True
    elif human == "same" and judge_pick == "tie":
        agreement_text = "both saw a tie"
        disagreement = False
    else:
        agreement_text = "—"
        disagreement = False

    score_rows = []
    for dim in ALL_DIMS:
        c_score = rec.get("control_scores", {}).get(dim, {}).get("score")
        t_score = rec.get("treatment_scores", {}).get(dim, {}).get("score")
        c_note = rec.get("control_scores", {}).get(dim, {}).get("note", "")
        t_note = rec.get("treatment_scores", {}).get(dim, {}).get("note", "")
        note = ""
        if c_note and t_note:
            note = f"control: {c_note[:80]} · treatment: {t_note[:80]}"
        elif t_note:
            note = t_note[:160]
        d = ""
        d_class = "delta-zero"
        if c_score is not None and t_score is not None:
            d_n = t_score - c_score
            d = f"{d_n:+d}" if isinstance(d_n, int) else f"{d_n:+.2f}"
            if d_n > 0:
                d_class = "delta-pos"
            elif d_n < 0:
                d_class = "delta-neg"
        score_rows.append({
            "dim": dim,
            "c_str": f"{c_score}/5" if c_score is not None else "—",
            "t_str": f"{t_score}/5" if t_score is not None else "—",
            "delta": d,
            "delta_class": d_class,
            "note": note,
            "headline": dim in ("portrait_coherence", "surprise_in_retrospect"),
        })

    overall_delta = ""
    overall_delta_class = "delta-zero"
    if co is not None and to is not None:
        d = to - co
        overall_delta = f"{d:+.2f}"
        if d > 0: overall_delta_class = "delta-pos"
        elif d < 0: overall_delta_class = "delta-neg"

    t_out = rec.get("treatment_output", {}) or {}

    return render_template_string(
        REVEAL_HTML,
        fixture_name=fixture_name,
        a_arm=a_arm,
        b_arm=b_arm,
        human_pick=human or "—",
        note=rec.get("human_note", ""),
        judge_pick=judge_pick,
        agreement_text=agreement_text,
        disagreement=disagreement,
        score_rows=score_rows,
        control_overall=co,
        treatment_overall=to,
        overall_delta=overall_delta,
        overall_delta_class=overall_delta_class,
        portrait_prose=t_out.get("portrait_prose"),
        through_lines=t_out.get("through_lines", []),
        restraint=t_out.get("restraint_omitted", []),
        control_concepts=(rec.get("control_output") or {}).get("product_gifts", []),
        treatment_concepts=t_out.get("product_gifts", []),
        next_fixture=_next_fixture(fixture_name),
    )


@app.route("/save", methods=["POST"])
def save():
    state = _load_state()
    state["overall_note"] = request.form.get("overall_note", "").strip()
    md_path = _write_markdown(state)
    state["last_saved"] = md_path
    _save_state(state)
    return redirect(url_for("home"))


def _write_markdown(state) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = os.path.join(RESULTS_DIR, f"session_{ts}.md")
    agg = _aggregate(state)

    lines = [f"# GiftWise A/B Review Session — {ts}\n",
             "## Run config\n",
             f"- control model: `{CONTROL_MODEL}`",
             f"- portrait model: `{PORTRAIT_MODEL}`",
             f"- judge model: `{JUDGE_MODEL}`",
             ""]

    lines.append("## Aggregate\n")
    lines.append("### Human picks (blind)\n")
    lines.append(f"- treatment: **{agg['human_treatment']}**")
    lines.append(f"- control: **{agg['human_control']}**")
    lines.append(f"- same / can't tell: **{agg['human_same']}**")
    lines.append("")
    if agg["avg_lift"] is not None:
        lines.append("### Judge averages\n")
        lines.append(f"- overall lift: **{agg['avg_lift']:+.2f}**")
    if agg["pc_lift"] is not None:
        lines.append(f"- `portrait_coherence` lift: **{agg['pc_lift']:+.2f}**")
    if agg["sir_lift"] is not None:
        lines.append(f"- `surprise_in_retrospect` lift: **{agg['sir_lift']:+.2f}**")
    lines.append("")
    lines.append("### Decision rule\n")
    lines.append("- portrait_coherence lift ≥ 1.0 AND surprise_in_retrospect lift ≥ 0.5 → **bet is real**")
    lines.append("- mixed → iterate prompt")
    lines.append("- no lift → re-plan agent shape\n")

    if state.get("overall_note"):
        lines.append("## Overall human reaction\n")
        lines.append(f"> {state['overall_note']}\n")

    lines.append("## Per-fixture detail\n")
    for fx in FIXTURES:
        rec = state.get("fixtures", {}).get(fx["name"])
        if not rec:
            continue
        lines.append(f"### {fx['name']}\n")
        if rec.get("judge_blind_used"):
            lines.append(f"**Judge mode:** `blind` (treatment metadata hidden from judge)")
        if "voice_axis_used" in rec:
            v = rec["voice_axis_used"]
            lines.append(f"**Voice axis:** `{v:.2f}` ({_voice_label(v)})")
        if rec.get("human_pick"):
            lines.append(f"**Human blind pick:** `{rec['human_pick']}`")
        if rec.get("human_note"):
            lines.append(f"**Human note:** {rec['human_note']}")
        lines.append("")

        lines.append("| dimension | control | treatment | delta |")
        lines.append("|---|---|---|---|")
        for dim in ALL_DIMS:
            c = rec.get("control_scores", {}).get(dim, {}).get("score")
            t = rec.get("treatment_scores", {}).get(dim, {}).get("score")
            cs = f"{c}/5" if c is not None else "—"
            tsx = f"{t}/5" if t is not None else "—"
            d = ""
            if c is not None and t is not None:
                d = f"{t - c:+d}"
            star = " ⭐" if dim in ("portrait_coherence", "surprise_in_retrospect") else ""
            lines.append(f"| `{dim}`{star} | {cs} | {tsx} | {d} |")
        co = rec.get("control_overall"); to = rec.get("treatment_overall")
        cs = f"{co:.2f}" if co is not None else "—"
        tsx = f"{to:.2f}" if to is not None else "—"
        d = f"{to - co:+.2f}" if (co is not None and to is not None) else ""
        lines.append(f"| **OVERALL** | **{cs}** | **{tsx}** | **{d}** |")
        lines.append("")

        c_out = rec.get("control_output") or {}
        t_out = rec.get("treatment_output") or {}
        if c_out.get("product_gifts"):
            lines.append("**Control concepts:**")
            for i, c in enumerate(c_out["product_gifts"], 1):
                lines.append(f"{i}. {c.get('name', '?')} — _{(c.get('why_perfect') or '')[:160]}_")
            sp = c_out.get("splurge_item")
            if sp:
                lines.append(f"- **splurge:** {sp.get('name', '?')} ({sp.get('price_range', '?')})")
            lines.append("")
        if t_out.get("product_gifts"):
            lines.append("**Treatment concepts:**")
            for i, c in enumerate(t_out["product_gifts"], 1):
                slot = f" `[{c.get('slot', '?')}]`" if c.get("slot") else ""
                lines.append(f"{i}.{slot} {c.get('name', '?')} — _{(c.get('why_perfect') or '')[:160]}_")
            sp = t_out.get("splurge_item")
            if sp:
                lines.append(f"- **splurge:** {sp.get('name', '?')} ({sp.get('price_range', '?')})")
            lines.append("")
            if t_out.get("portrait_prose"):
                lines.append(f"**Portrait prose:**\n> {t_out['portrait_prose']}\n")
            if t_out.get("through_lines"):
                lines.append("**Through-lines:**")
                for tl in t_out["through_lines"]:
                    lines.append(f"- **{tl.get('phrase', '?')}** (binds: {', '.join(tl.get('binds', []))}) — _{tl.get('why', '')}_")
                lines.append("")
            if t_out.get("restraint_omitted"):
                lines.append("**Restraint:**")
                for r in t_out["restraint_omitted"]:
                    lines.append(f"- **{r.get('signal', '?')}** — _{r.get('why_held_back', '')}_")
                lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_Share with Claude as_ `evals/results/latest_session.md`.")

    md = "\n".join(lines)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(LATEST_MD, "w", encoding="utf-8") as f:
        f.write(md)
    return out_path


if __name__ == "__main__":
    print()
    print("  GiftWise eval UI")
    print(f"  control={CONTROL_MODEL}  portrait={PORTRAIT_MODEL}  judge={JUDGE_MODEL}")
    print("  open http://localhost:5001")
    print()
    app.run(host="127.0.0.1", port=5001, debug=False)
