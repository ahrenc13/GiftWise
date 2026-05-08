"""
Partner admin UI — bare-bones Flask app on port 5002.

Standalone (does NOT import giftwise_app, so the Windows fcntl issue doesn't
affect it). Lets you create / list / edit / delete partners that the v2
embed wedge will use.

Pages:
  /                — list partners + create button
  /new             — create form
  /<slug>/edit     — edit form
  /<slug>/delete   — POST: delete with confirm
  /<slug>          — read-only view

Auth: gated by ADMIN_DASHBOARD_KEY env var if set; otherwise open. Set the
env var when running anywhere other than localhost.

Usage:
    python partner_admin.py
    open http://localhost:5002
"""

import json
import logging
import os
import sys
from functools import wraps

from flask import Flask, render_template_string, request, redirect, url_for, abort

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partner_config as pc

ADMIN_KEY = os.environ.get("ADMIN_DASHBOARD_KEY", "")

KNOWN_RETAILERS = ["amazon", "ebay", "cj", "awin", "etsy", "rakuten", "impact", "flexoffers"]

app = Flask(__name__)


# ---------- auth ----------

def require_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if ADMIN_KEY:
            provided = request.args.get("key") or request.cookies.get("admin_key")
            if provided != ADMIN_KEY:
                return "unauthorized — append ?key=<ADMIN_DASHBOARD_KEY>", 401
        return f(*args, **kwargs)
    return wrapper


# ---------- shared CSS / chrome ----------

BASE_HEAD = """
<style>
  body { font: 15px/1.5 -apple-system, Segoe UI, sans-serif; max-width: 980px; margin: 32px auto; padding: 0 16px; color: #222; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  h2 { font-size: 16px; margin-top: 24px; }
  .sub { color: #666; margin-bottom: 24px; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
  th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #eee; vertical-align: top; }
  th { background: #fafafa; font-size: 12px; text-transform: uppercase; letter-spacing: .5px; color: #888; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
  .pill-draft { background: #f1f1f1; color: #888; }
  .pill-live { background: #e6f4ea; color: #1e7a3a; }
  .pill-paused { background: #fff4e0; color: #b86e00; }
  button, .btn { font: inherit; padding: 6px 14px; border: 1px solid #ccc; border-radius: 6px; background: white; cursor: pointer; text-decoration: none; color: #222; display: inline-block; }
  button.primary, .btn.primary { background: #2c5cff; color: white; border-color: #2c5cff; }
  button.danger { background: #b3261e; color: white; border-color: #b3261e; }
  form.stacked label { display: block; margin-top: 14px; font-weight: 600; font-size: 13px; }
  form.stacked label span.help { display: block; font-weight: normal; color: #888; font-size: 12px; margin-top: 2px; }
  form.stacked input[type=text], form.stacked input[type=number], form.stacked textarea, form.stacked select { width: 100%; padding: 8px; font: inherit; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; margin-top: 4px; }
  form.stacked textarea { min-height: 70px; }
  .voice-slider-row { display: flex; align-items: center; gap: 12px; margin-top: 6px; }
  .voice-slider-row input[type=range] { flex: 1; }
  .voice-axis-label { font-weight: 600; min-width: 130px; text-align: right; font-size: 13px; }
  .axis-ends { display: flex; justify-content: space-between; font-size: 12px; color: #888; margin-top: 2px; }
  .actions { margin-top: 24px; display: flex; gap: 8px; flex-wrap: wrap; }
  .key-value { display: grid; grid-template-columns: 200px 1fr; gap: 6px 16px; margin-top: 12px; font-size: 14px; }
  .key-value dt { color: #888; font-weight: 600; }
  .key-value dd { margin: 0; }
  code { background: #f5f5f7; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
  .nav { font-size: 13px; color: #888; margin-bottom: 16px; }
  .nav a { color: #2c5cff; text-decoration: none; }
  .err { background: #fde7e7; color: #b3261e; padding: 10px 14px; border-radius: 6px; margin: 12px 0; font-size: 14px; }
  .checkbox-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px 16px; margin-top: 6px; }
  .checkbox-grid label { font-weight: normal; }
</style>
"""


def _key_qs():
    return f"?key={ADMIN_KEY}" if ADMIN_KEY else ""


# ---------- pages ----------

LIST_HTML = (
    "<!doctype html><html><head><title>Partners — GiftWise admin</title>" + BASE_HEAD + "</head><body>"
    "<h1>Partner config</h1>"
    "<div class='sub'>Creator/publisher partners for the v2 embed wedge. Storage: <code>data/partners.db</code></div>"
    "<a class='btn primary' href='/new{{key}}'>+ New partner</a>"
    "<table>"
    "<tr><th>slug</th><th>name</th><th>status</th><th>voice</th><th>retailers</th><th>updated</th><th></th></tr>"
    "{% for p in partners %}"
    "<tr>"
    "<td><code>{{p.slug}}</code></td>"
    "<td><b>{{p.name}}</b>{% if p.notes %}<div style='color:#888;font-size:12px;'>{{p.notes[:80]}}</div>{% endif %}</td>"
    "<td><span class='pill pill-{{p.status}}'>{{p.status}}</span></td>"
    "<td>{{ '%.2f' % p.voice_axis }} <span style='color:#888;font-size:12px;'>({{voice_label(p.voice_axis)}})</span></td>"
    "<td style='font-size:12px;color:#666;'>{{ p.retailer_allowlist | join(', ') }}</td>"
    "<td style='font-size:12px;color:#888;'>{{p.updated_at[:10]}}</td>"
    "<td>"
    "<a class='btn' href='/{{p.slug}}{{key}}'>view</a>"
    " <a class='btn' href='/{{p.slug}}/edit{{key}}'>edit</a>"
    "</td>"
    "</tr>"
    "{% else %}"
    "<tr><td colspan='7' style='text-align:center;color:#888;padding:32px;'>No partners yet. <a href='/new{{key}}'>Create the first one →</a></td></tr>"
    "{% endfor %}"
    "</table>"
    "</body></html>"
)


FORM_HTML = (
    "<!doctype html><html><head><title>{{ 'Edit' if partner else 'New' }} partner</title>" + BASE_HEAD + "</head><body>"
    "<div class='nav'><a href='/{{key}}'>← all partners</a></div>"
    "<h1>{{ 'Edit ' + partner.name if partner else 'New partner' }}</h1>"
    "{% if error %}<div class='err'>{{error}}</div>{% endif %}"
    "<form class='stacked' method='post' action='{{ form_action }}{{ key }}'>"

    "<label>Slug<span class='help'>URL-safe id. lowercase, hyphens, e.g. <code>weeknight-wines</code>. Cannot be changed after creation.</span>"
    "{% if partner %}<input type='text' value='{{partner.slug}}' disabled>{% else %}"
    "<input type='text' name='slug' required pattern='[a-z0-9][a-z0-9\\-]*[a-z0-9]' placeholder='weeknight-wines' value='{{form.slug or \"\"}}'>{% endif %}"
    "</label>"

    "<label>Name<span class='help'>Display name shown to the partner's audience.</span>"
    "<input type='text' name='name' required value='{{ (partner.name if partner else form.name) or \"\" }}' placeholder='Weeknight Wines'>"
    "</label>"

    "<label>Status"
    "<select name='status'>"
    "{% for s in ['draft', 'live', 'paused'] %}"
    "<option value='{{s}}' {% if (partner.status if partner else form.status or 'draft') == s %}selected{% endif %}>{{s}}</option>"
    "{% endfor %}"
    "</select>"
    "</label>"

    "<label>Voice axis<span class='help'>Where this partner's curator sits between practical (on-signal, actionable) and taste-edited (aspirational, synthesized).</span>"
    "<div class='voice-slider-row'>"
    "<input type='range' name='voice_axis' min='0' max='1' step='0.05' value='{{ (partner.voice_axis if partner else form.voice_axis) or 0.5 }}' oninput=\"document.getElementById('vaval').textContent = parseFloat(this.value).toFixed(2) + ' (' + voiceLabel(this.value) + ')'\">"
    "<span class='voice-axis-label' id='vaval'>{{ '%.2f' % (partner.voice_axis if partner else (form.voice_axis or 0.5)) }} ({{ voice_label((partner.voice_axis if partner else (form.voice_axis or 0.5))) }})</span>"
    "</div>"
    "<div class='axis-ends'><span>0.0 — practical</span><span>balanced</span><span>1.0 — taste-edited</span></div>"
    "</label>"

    "<label>Theme — primary color"
    "<input type='text' name='theme_primary_color' value='{{ (partner.theme_primary_color if partner else form.theme_primary_color) or \"#2c5cff\" }}' placeholder='#2c5cff'>"
    "</label>"

    "<label>Theme — accent color"
    "<input type='text' name='theme_accent_color' value='{{ (partner.theme_accent_color if partner else form.theme_accent_color) or \"#1e7a3a\" }}' placeholder='#1e7a3a'>"
    "</label>"

    "<label>Retailer allowlist<span class='help'>Which retailers' affiliate links this partner's audience can be sent to. Leave default unless the partner has specific affiliate constraints.</span>"
    "<div class='checkbox-grid'>"
    "{% for r in known_retailers %}"
    "<label><input type='checkbox' name='retailer_allowlist' value='{{r}}'"
    "{% if r in (partner.retailer_allowlist if partner else (form.retailer_allowlist or default_retailers)) %} checked{% endif %}> {{r}}</label>"
    "{% endfor %}"
    "</div>"
    "</label>"

    "<label>Commission split — partner %<span class='help'>Percent of affiliate commission going to this partner. The remainder stays with GiftWise.</span>"
    "<input type='number' name='commission_split_partner_pct' min='0' max='100' step='0.5' value='{{ (partner.commission_split_partner_pct if partner else form.commission_split_partner_pct) or 50 }}'>"
    "</label>"

    "<label>Affiliate inventory source<span class='help'>URL or local path to the partner's own affiliate feed (CSV, API, etc.). Optional. The agent retrieves from this in addition to GiftWise's base catalog.</span>"
    "<input type='text' name='affiliate_inventory_source' value='{{ (partner.affiliate_inventory_source if partner else form.affiliate_inventory_source) or \"\" }}' placeholder='https://... or data/...'>"
    "</label>"

    "<label>Custom intake questions (JSON)<span class='help'>Optional. JSON array of <code>{question, optional}</code> objects shown in the embed intake. Leave empty for default questions.</span>"
    "<textarea name='custom_intake_questions' placeholder='[]'>{{ custom_questions_json }}</textarea>"
    "</label>"

    "<label>Internal notes<span class='help'>Not shown to the partner or audience.</span>"
    "<textarea name='notes' placeholder='context, commission deals, contact, etc.'>{{ (partner.notes if partner else form.notes) or \"\" }}</textarea>"
    "</label>"

    "<div class='actions'>"
    "<button class='primary' type='submit'>{{ 'Save changes' if partner else 'Create partner' }}</button>"
    "<a class='btn' href='/{{key}}'>Cancel</a>"
    "{% if partner %}<form method='post' action='/{{partner.slug}}/delete{{key}}' style='display:inline;margin-left:auto;' onsubmit=\"return confirm('Delete partner {{partner.slug}}? This cannot be undone.');\">"
    "<button class='danger' type='submit'>Delete</button>"
    "</form>{% endif %}"
    "</div>"

    "</form>"

    "<script>"
    "function voiceLabel(v) {"
    "  v = parseFloat(v);"
    "  if (v <= 0.2) return 'practical';"
    "  if (v <= 0.4) return 'leans practical';"
    "  if (v <= 0.6) return 'balanced';"
    "  if (v <= 0.8) return 'leans taste-edited';"
    "  return 'taste-edited';"
    "}"
    "</script>"
    "</body></html>"
)


VIEW_HTML = (
    "<!doctype html><html><head><title>{{partner.name}} — GiftWise admin</title>" + BASE_HEAD + "</head><body>"
    "<div class='nav'><a href='/{{key}}'>← all partners</a></div>"
    "<h1>{{partner.name}} <span class='pill pill-{{partner.status}}'>{{partner.status}}</span></h1>"
    "<div class='sub'>slug: <code>{{partner.slug}}</code> · created {{partner.created_at[:10]}} · updated {{partner.updated_at[:10]}}</div>"

    "<a class='btn primary' href='/{{partner.slug}}/edit{{key}}'>Edit</a>"

    "<dl class='key-value'>"
    "<dt>voice_axis</dt><dd>{{ '%.2f' % partner.voice_axis }} <span style='color:#888'>({{voice_label(partner.voice_axis)}})</span></dd>"
    "<dt>theme</dt><dd>"
    "<span style='display:inline-block;width:18px;height:18px;background:{{partner.theme_primary_color}};border:1px solid #ccc;border-radius:3px;vertical-align:middle;'></span>"
    " <code>{{partner.theme_primary_color}}</code>"
    " &nbsp; "
    "<span style='display:inline-block;width:18px;height:18px;background:{{partner.theme_accent_color}};border:1px solid #ccc;border-radius:3px;vertical-align:middle;'></span>"
    " <code>{{partner.theme_accent_color}}</code>"
    "</dd>"
    "<dt>retailer_allowlist</dt><dd>{{ partner.retailer_allowlist | join(', ') or '(none)' }}</dd>"
    "<dt>commission_split_partner_pct</dt><dd>{{partner.commission_split_partner_pct}}%</dd>"
    "<dt>affiliate_inventory_source</dt><dd>{{partner.affiliate_inventory_source or '(none)'}}</dd>"
    "<dt>custom_intake_questions</dt><dd>"
    "{% if partner.custom_intake_questions %}<pre style='font-size:12px;background:#f5f5f7;padding:8px;border-radius:4px;'>{{ partner.custom_intake_questions | tojson(indent=2) }}</pre>"
    "{% else %}(default questions){% endif %}"
    "</dd>"
    "<dt>notes</dt><dd>{{partner.notes or '(none)'}}</dd>"
    "</dl>"

    "</body></html>"
)


# ---------- routes ----------

@app.route("/")
@require_key
def list_view():
    partners = pc.list_partners()
    return render_template_string(
        LIST_HTML, partners=partners, voice_label=pc.voice_axis_label, key=_key_qs()
    )


def _form_payload(form):
    """Parse form data into kwargs suitable for create/update_partner."""
    retailers = form.getlist("retailer_allowlist")
    raw_questions = (form.get("custom_intake_questions") or "").strip()
    try:
        questions = json.loads(raw_questions) if raw_questions else []
    except json.JSONDecodeError as e:
        raise ValueError(f"custom_intake_questions: invalid JSON ({e})")
    if not isinstance(questions, list):
        raise ValueError("custom_intake_questions must be a JSON array")

    return {
        "name": form.get("name", "").strip(),
        "status": form.get("status", "draft"),
        "voice_axis": float(form.get("voice_axis", 0.5)),
        "theme_primary_color": form.get("theme_primary_color", "#2c5cff").strip(),
        "theme_accent_color": form.get("theme_accent_color", "#1e7a3a").strip(),
        "retailer_allowlist": retailers,
        "commission_split_partner_pct": float(form.get("commission_split_partner_pct", 50)),
        "custom_intake_questions": questions,
        "affiliate_inventory_source": (form.get("affiliate_inventory_source", "").strip() or None),
        "notes": (form.get("notes", "").strip() or None),
    }


@app.route("/new", methods=["GET", "POST"])
@require_key
def new_partner():
    error = None
    form_data = {}
    if request.method == "POST":
        try:
            kwargs = _form_payload(request.form)
            slug = request.form.get("slug", "").strip()
            partner = pc.create_partner(slug=slug, **kwargs)
            return redirect(url_for("view_partner", slug=partner["slug"]) + _key_qs())
        except (ValueError, KeyError) as e:
            error = str(e)
            form_data = dict(request.form)
            form_data["retailer_allowlist"] = request.form.getlist("retailer_allowlist")

    return render_template_string(
        FORM_HTML,
        partner=None,
        form=form_data,
        form_action="/new",
        error=error,
        custom_questions_json=form_data.get("custom_intake_questions", ""),
        voice_label=pc.voice_axis_label,
        known_retailers=KNOWN_RETAILERS,
        default_retailers=pc.DEFAULT_RETAILERS,
        key=_key_qs(),
    )


@app.route("/<slug>")
@require_key
def view_partner(slug):
    partner = pc.get_partner_by_slug(slug)
    if not partner:
        abort(404)
    return render_template_string(
        VIEW_HTML, partner=partner, voice_label=pc.voice_axis_label, key=_key_qs()
    )


@app.route("/<slug>/edit", methods=["GET", "POST"])
@require_key
def edit_partner(slug):
    partner = pc.get_partner_by_slug(slug)
    if not partner:
        abort(404)
    error = None
    if request.method == "POST":
        try:
            kwargs = _form_payload(request.form)
            pc.update_partner(partner["id"], **kwargs)
            return redirect(url_for("view_partner", slug=slug) + _key_qs())
        except ValueError as e:
            error = str(e)

    custom_q_str = json.dumps(partner.get("custom_intake_questions", []), indent=2) if partner.get("custom_intake_questions") else ""

    return render_template_string(
        FORM_HTML,
        partner=partner,
        form={},
        form_action=f"/{slug}/edit",
        error=error,
        custom_questions_json=custom_q_str,
        voice_label=pc.voice_axis_label,
        known_retailers=KNOWN_RETAILERS,
        default_retailers=pc.DEFAULT_RETAILERS,
        key=_key_qs(),
    )


@app.route("/<slug>/delete", methods=["POST"])
@require_key
def delete_partner_route(slug):
    partner = pc.get_partner_by_slug(slug)
    if not partner:
        abort(404)
    pc.delete_partner(partner["id"])
    return redirect(url_for("list_view") + _key_qs())


if __name__ == "__main__":
    pc.init_db()
    print()
    print("  GiftWise Partner Admin")
    print(f"  DB: {pc.DB_PATH}")
    if ADMIN_KEY:
        print(f"  AUTH: required (set ADMIN_DASHBOARD_KEY env var)")
    else:
        print(f"  AUTH: open (no ADMIN_DASHBOARD_KEY set)")
    print(f"  open http://localhost:5002")
    print()
    app.run(host="127.0.0.1", port=5002, debug=False)
