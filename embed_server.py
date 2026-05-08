"""
Embed server — partner-facing curator surface (phase 3 of v2 rebuild).

Standalone Flask app on port 5003. Streaming reveal: portrait writes itself
character-by-character, through-lines fade in, picks slide up sequentially.

Pages:
  /                              — admin landing
  /<slug>                        — themed intake page for the visitor
  /<slug>/start                  — POST: save intake, redirect to results
  /<slug>/results/<session_id>   — streaming results page (SSE-driven reveal)
  /<slug>/stream/<session_id>    — SSE endpoint serving the curator output

Refreshing the results page is safe — once a session has curator_output saved,
the stream replays from disk instead of re-calling the API.

Run with:
    python embed_server.py
Open http://localhost:5003.
"""

import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime

from flask import Flask, Response, render_template_string, request, redirect, url_for, abort

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import partner_config as pc
from intake_analyzer import analyze_intake, VALID_RELATIONSHIPS, VALID_BUDGETS
from evals.portrait_ideator import (
    _SYSTEM as CURATOR_SYSTEM,
    _PROMPT as CURATOR_PROMPT,
    _build_voice_block,
    _build_ownership_block,
    _build_avoid_block,
    _strip_fences,
)

PORTRAIT_MODEL = os.environ.get("PORTRAIT_MODEL", "claude-opus-4-7")
INTAKE_MODEL = os.environ.get("INTAKE_MODEL", "claude-sonnet-4-6")
SESSIONS_DIR = "data/embed_sessions"


def _client():
    from claude_meter import make_client
    return make_client(tag="embed_server")


def _save_session(session_id: str, payload: dict):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    with open(os.path.join(SESSIONS_DIR, f"{session_id}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _load_session(session_id: str):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _voice_label(v: float) -> str:
    return pc.voice_axis_label(v)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


_JSON_ESCAPES = {"\\\"": "\"", "\\n": "\n", "\\t": "\t", "\\r": "\r", "\\\\": "\\", "\\/": "/"}


def _unescape_json_string(s: str) -> str:
    """Convert JSON-escaped string content to plain text. Best-effort, used
    for showing in-progress portrait_prose while the JSON is still streaming."""
    out = s
    for k, v in _JSON_ESCAPES.items():
        out = out.replace(k, v)
    # Strip any trailing partial escape that would render as garbage
    if out.endswith("\\"):
        out = out[:-1]
    return out


# ---------- shared CSS (editorial, theme-driven) ----------

_CSS_BASE = """
*, *::before, *::after { box-sizing: border-box; }
:root {
  --primary: __PRIMARY__;
  --accent: __ACCENT__;
  --bg: #fdfcf8;
  --paper: #fffefa;
  --text: #22211f;
  --text-soft: #5a5852;
  --text-muted: #8a8780;
  --rule: #e8e4dc;
  --rule-soft: #f0ece4;
}
html, body { background: var(--bg); }
body {
  font-family: 'Source Serif 4', 'Charter', 'Iowan Old Style', 'Apple Garamond', Georgia, serif;
  font-feature-settings: "liga", "dlig", "kern";
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 17px;
  line-height: 1.6;
  color: var(--text);
  margin: 0;
  padding: 56px 24px 96px;
}
.wrap { max-width: 680px; margin: 0 auto; }
.partner-tag {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 8px;
  font-weight: 500;
}
.partner-tag strong { color: var(--primary); font-weight: 600; }
h1 {
  font-family: 'Source Serif 4', serif;
  font-weight: 400;
  font-size: 38px;
  line-height: 1.15;
  letter-spacing: -0.015em;
  margin: 0 0 8px;
  color: var(--text);
}
h2 {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 56px 0 18px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--rule);
}
.lede {
  font-size: 19px;
  line-height: 1.55;
  color: var(--text-soft);
  margin: 0 0 32px;
  font-style: italic;
  font-weight: 300;
}
form { display: flex; flex-direction: column; gap: 20px; }
form label {
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: 0.02em;
}
form label .help {
  display: block;
  font-weight: 400;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
  margin-top: 3px;
}
textarea, select, input[type=text] {
  width: 100%;
  padding: 12px 14px;
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 16px;
  line-height: 1.5;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--paper);
  color: var(--text);
  margin-top: 6px;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}
textarea {
  min-height: 160px;
  resize: vertical;
}
textarea::placeholder, input::placeholder { color: var(--text-muted); font-style: italic; }
textarea:focus, select:focus, input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary) 14%, transparent);
}
select {
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3e%3cpath fill='none' stroke='%238a8780' stroke-width='1.5' d='M1 1l5 5 5-5'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 14px center;
  padding-right: 36px;
}
button.primary {
  background: var(--text);
  color: var(--paper);
  border: none;
  padding: 14px 28px;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.03em;
  border-radius: 4px;
  cursor: pointer;
  align-self: flex-start;
  transition: background 200ms ease;
}
button.primary:hover { background: var(--primary); }
.err {
  background: color-mix(in srgb, #b3261e 8%, var(--paper));
  color: #b3261e;
  border-left: 3px solid #b3261e;
  padding: 12px 16px;
  margin-bottom: 18px;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  border-radius: 0 4px 4px 0;
}
footer {
  margin-top: 64px;
  padding-top: 18px;
  border-top: 1px solid var(--rule);
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}
footer a { color: var(--text-muted); text-decoration: underline; text-decoration-color: var(--rule); text-underline-offset: 3px; }
footer a:hover { color: var(--primary); text-decoration-color: var(--primary); }

/* ---- Portrait reveal ---- */
.portrait-section {
  position: relative;
  margin: 8px 0 0;
  padding: 12px 0 12px 24px;
  border-left: 2px solid var(--accent);
  min-height: 80px;
}
.portrait {
  font-size: 19px;
  line-height: 1.65;
  color: var(--text);
  font-weight: 380;
  margin: 0;
  letter-spacing: -0.005em;
}
.portrait::first-letter {
  font-family: 'Source Serif 4', serif;
  font-size: 3.4em;
  line-height: 0.85;
  padding-right: 6px;
  padding-top: 4px;
  float: left;
  color: var(--accent);
  font-weight: 600;
}
.portrait .cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--accent);
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 1.05s step-end infinite;
  transform: translateY(2px);
}
.portrait.complete .cursor { animation: fade-out 600ms forwards; }
@keyframes blink { 50% { opacity: 0.2; } }
@keyframes fade-out { to { opacity: 0; width: 0; margin: 0; } }

.status-line {
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 0 16px;
}
.status-line .dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  margin-right: 8px;
  animation: pulse 1.4s ease-in-out infinite;
  vertical-align: middle;
}
.status-line.done .dot { animation: none; opacity: 0.3; }
@keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }

/* ---- Through-lines ---- */
.through-lines { margin: 8px 0 0; padding: 0; list-style: none; }
.through-line {
  padding: 10px 0;
  border-bottom: 1px solid var(--rule-soft);
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 500ms cubic-bezier(0.2, 0.6, 0.2, 1), transform 500ms cubic-bezier(0.2, 0.6, 0.2, 1);
}
.through-line:last-child { border-bottom: none; }
.through-line.in { opacity: 1; transform: none; }
.through-line .phrase {
  font-family: 'Source Serif 4', serif;
  font-style: italic;
  font-size: 17px;
  color: var(--text);
}
.through-line .why {
  font-family: 'Source Serif 4', serif;
  font-size: 15px;
  line-height: 1.55;
  color: var(--text-soft);
  margin-top: 3px;
}

/* ---- Picks ---- */
.picks { margin: 0; padding: 0; list-style: none; counter-reset: pick-counter; }
.pick {
  position: relative;
  padding: 22px 0 22px 56px;
  border-bottom: 1px solid var(--rule-soft);
  counter-increment: pick-counter;
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 550ms cubic-bezier(0.2, 0.6, 0.2, 1), transform 550ms cubic-bezier(0.2, 0.6, 0.2, 1);
}
.pick:last-child { border-bottom: none; }
.pick.in { opacity: 1; transform: none; }
.pick::before {
  content: counter(pick-counter, decimal-leading-zero);
  position: absolute;
  left: 0;
  top: 24px;
  font-family: 'Inter', sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}
.pick .slot {
  display: inline-block;
  font-family: 'Inter', sans-serif;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 6px;
}
.pick .name {
  font-family: 'Source Serif 4', serif;
  font-weight: 500;
  font-size: 19px;
  line-height: 1.3;
  letter-spacing: -0.005em;
  color: var(--text);
  margin: 0 0 4px;
}
.pick .description {
  font-size: 15px;
  line-height: 1.55;
  color: var(--text-soft);
  margin: 6px 0 0;
}
.pick .why {
  font-size: 15px;
  line-height: 1.55;
  color: var(--text);
  margin: 10px 0 0;
  font-style: italic;
}
.pick .price {
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-top: 10px;
}

/* ---- Splurge ---- */
.splurge {
  position: relative;
  margin-top: 12px;
  padding: 28px 28px 26px;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-top: 3px solid var(--accent);
  border-radius: 4px;
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 700ms cubic-bezier(0.2, 0.6, 0.2, 1), transform 700ms cubic-bezier(0.2, 0.6, 0.2, 1);
}
.splurge.in { opacity: 1; transform: none; }
.splurge .tag {
  font-family: 'Inter', sans-serif;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 6px;
}
.splurge .name {
  font-family: 'Source Serif 4', serif;
  font-weight: 500;
  font-size: 22px;
  line-height: 1.25;
  letter-spacing: -0.01em;
  margin: 0 0 6px;
  color: var(--text);
}
.splurge .description {
  font-size: 16px;
  line-height: 1.55;
  color: var(--text-soft);
  margin: 6px 0 0;
}
.splurge .why {
  font-size: 16px;
  line-height: 1.55;
  margin: 14px 0 0;
  font-style: italic;
}
.splurge .price {
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-top: 12px;
}

@media (max-width: 480px) {
  body { padding: 32px 18px 64px; }
  h1 { font-size: 30px; }
  .lede { font-size: 17px; }
  .pick { padding-left: 40px; }
  .splurge { padding: 22px 22px 20px; }
}
"""


def _theme_css(partner: dict) -> str:
    primary = partner.get("theme_primary_color") or "#2c5cff"
    accent = partner.get("theme_accent_color") or "#1e7a3a"
    return _CSS_BASE.replace("__PRIMARY__", primary).replace("__ACCENT__", accent)


_FONT_LINK = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,300..700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
"""


# ---------- pages ----------

ADMIN_HOME = """
<!doctype html><html><head><title>GiftWise embed — partners</title>
""" + _FONT_LINK + """
<style>
  body { font-family: 'Inter', system-ui, sans-serif; max-width: 720px; margin: 56px auto; padding: 0 24px; color: #22211f; background: #fdfcf8; }
  h1 { font-family: 'Source Serif 4', serif; font-weight: 400; font-size: 30px; letter-spacing: -0.01em; }
  .sub { color: #8a8780; font-size: 13px; margin-bottom: 32px; }
  ul { list-style: none; padding: 0; }
  li { border-bottom: 1px solid #e8e4dc; padding: 18px 0; }
  li b { font-family: 'Source Serif 4', serif; font-weight: 500; font-size: 18px; }
  li .meta { color: #8a8780; font-size: 12px; margin-top: 4px; letter-spacing: 0.02em; }
  a { color: #22211f; text-decoration: underline; text-decoration-color: #d4d4d8; text-underline-offset: 3px; }
  a:hover { text-decoration-color: currentColor; }
  .pill { display: inline-block; padding: 1px 8px; border-radius: 9px; font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; margin-left: 6px; }
  .pill-draft { background: #f1f1f1; color: #888; }
  .pill-live { background: #e6f4ea; color: #1e7a3a; }
  .pill-paused { background: #fff4e0; color: #b86e00; }
</style></head>
<body>
<h1>GiftWise — embed targets</h1>
<div class="sub">Partner-facing curator demos. Pick one to view its themed intake page.</div>
{% if not partners %}<p class="sub">No partners yet. Create one in <a href="http://localhost:5002/">partner_admin</a>.</p>{% endif %}
<ul>
{% for p in partners %}
<li>
  <b>{{p.name}}</b><span class="pill pill-{{p.status}}">{{p.status}}</span><br>
  <span class="meta">slug: {{p.slug}} · voice {{ '%.2f' % p.voice_axis }} ({{voice_label(p.voice_axis)}})</span><br>
  <span style="margin-top:8px;display:inline-block;"><a href="/{{p.slug}}">→ open embed</a> &nbsp;·&nbsp; <a href="http://localhost:5002/{{p.slug}}">view in admin</a></span>
</li>
{% endfor %}
</ul>
</body></html>
"""


INTAKE_HTML = """
<!doctype html><html><head><title>{{intake_heading}} · {{partner.name}}</title>
""" + _FONT_LINK + """
<style>{{css}}</style></head>
<body>
<div class="wrap">
<div class="partner-tag">presented by <strong>{{partner.name}}</strong></div>
<h1>{{intake_heading}}</h1>
<p class="lede">{{intake_intro}}</p>

{% if error %}<div class="err">{{error}}</div>{% endif %}

<form method="post" action="/{{partner.slug}}/start">
  <label>
    Tell me about them.
    <span class="help">What are they into right now? Recent obsessions, what they've been talking about, the texture of their life. The more you say, the better the picks.</span>
    <textarea name="intake_text" required minlength="20" placeholder="She's been getting really into pottery — set up a wheel in the basement, sells mugs on Etsy. Reads a lot about Japanese craft. We're celebrating our anniversary in May...">{{ form.intake_text or '' }}</textarea>
  </label>

  <label>
    Who are you shopping for?
    <select name="relationship" required>
      <option value="" disabled {% if not form.relationship %}selected{% endif %}>Pick one</option>
      <option value="romantic_partner" {% if form.relationship == 'romantic_partner' %}selected{% endif %}>Romantic partner</option>
      <option value="close_friend" {% if form.relationship == 'close_friend' %}selected{% endif %}>Close friend</option>
      <option value="family_member" {% if form.relationship == 'family_member' %}selected{% endif %}>Family member</option>
      <option value="colleague" {% if form.relationship == 'colleague' %}selected{% endif %}>Colleague</option>
      <option value="other" {% if form.relationship == 'other' %}selected{% endif %}>Other</option>
    </select>
  </label>

  <label>
    What's the budget?
    <select name="budget_category" required>
      <option value="" disabled {% if not form.budget_category %}selected{% endif %}>Pick one</option>
      <option value="budget" {% if form.budget_category == 'budget' %}selected{% endif %}>Budget — under $75</option>
      <option value="moderate" {% if form.budget_category == 'moderate' %}selected{% endif %}>Moderate — $75 to $200</option>
      <option value="premium" {% if form.budget_category == 'premium' %}selected{% endif %}>Premium — $200 to $500</option>
      <option value="luxury" {% if form.budget_category == 'luxury' %}selected{% endif %}>Luxury — $500+</option>
    </select>
  </label>

  <label>
    Their name or initial (optional)
    <span class="help">Just helps the curator address them naturally.</span>
    <input type="text" name="recipient_name" maxlength="40" placeholder="M, Sara, etc." value="{{ form.recipient_name or '' }}">
  </label>

  <button class="primary" type="submit">Build the list</button>
</form>

<footer>Powered by GiftWise · <span style="color:var(--text-muted)">curator voice: {{voice_label(partner.voice_axis)}}</span></footer>
</div>
</body></html>
"""


# Streaming results page. The shell is empty; SSE drives the reveal.
RESULTS_HTML = """
<!doctype html><html><head><title>Their gift list · {{partner.name}}</title>
""" + _FONT_LINK + """
<style>{{css}}</style></head>
<body>
<div class="wrap">
<div class="partner-tag">presented by <strong>{{partner.name}}</strong></div>
<h1>{{results_heading}}</h1>

<p class="status-line" id="status"><span class="dot"></span><span class="status-text">Reading the person…</span></p>

<div class="portrait-section">
  <p class="portrait" id="portrait"><span class="cursor"></span></p>
</div>

<h2 id="threads-head" style="display:none;">Threads I noticed</h2>
<ul class="through-lines" id="through-lines"></ul>

<h2 id="picks-head" style="display:none;">Gift ideas</h2>
<ol class="picks" id="picks"></ol>

<h2 id="splurge-head" style="display:none;">If you want to go bigger</h2>
<div id="splurge"></div>

<footer style="margin-top:64px;">
  Powered by GiftWise · <a href="/{{partner.slug}}">Start over</a>
</footer>
</div>

<script>
(function() {
  const portraitEl = document.getElementById('portrait');
  const cursorEl = portraitEl.querySelector('.cursor');
  const statusEl = document.getElementById('status');
  const statusText = statusEl.querySelector('.status-text');
  const threadsHead = document.getElementById('threads-head');
  const threadsList = document.getElementById('through-lines');
  const picksHead = document.getElementById('picks-head');
  const picksList = document.getElementById('picks');
  const splurgeHead = document.getElementById('splurge-head');
  const splurgeEl = document.getElementById('splurge');

  const es = new EventSource('/{{partner.slug}}/stream/{{session_id}}');

  function setStatus(text, done) {
    statusText.textContent = text;
    if (done) statusEl.classList.add('done');
  }

  function setPortraitText(text, complete) {
    // Insert text before the cursor
    while (portraitEl.firstChild && portraitEl.firstChild !== cursorEl) {
      portraitEl.removeChild(portraitEl.firstChild);
    }
    const node = document.createTextNode(text);
    portraitEl.insertBefore(node, cursorEl);
    if (complete) {
      portraitEl.classList.add('complete');
    }
  }

  let threadIndex = 0;
  function appendThreadLine(tl) {
    if (threadsHead.style.display === 'none') threadsHead.style.display = '';
    const li = document.createElement('li');
    li.className = 'through-line';
    const phrase = document.createElement('div');
    phrase.className = 'phrase';
    phrase.textContent = tl.phrase || '';
    const why = document.createElement('div');
    why.className = 'why';
    why.textContent = tl.why || '';
    li.appendChild(phrase);
    li.appendChild(why);
    threadsList.appendChild(li);
    setTimeout(function() { li.classList.add('in'); }, 60 + threadIndex * 90);
    threadIndex++;
  }

  let pickIndex = 0;
  function appendPick(p) {
    if (picksHead.style.display === 'none') picksHead.style.display = '';
    const li = document.createElement('li');
    li.className = 'pick';
    if (p.slot) {
      const slot = document.createElement('div');
      slot.className = 'slot';
      slot.textContent = p.slot;
      li.appendChild(slot);
    }
    const name = document.createElement('div');
    name.className = 'name';
    name.textContent = p.name || '';
    li.appendChild(name);
    if (p.description) {
      const d = document.createElement('div');
      d.className = 'description';
      d.textContent = p.description;
      li.appendChild(d);
    }
    if (p.why_perfect) {
      const w = document.createElement('div');
      w.className = 'why';
      w.textContent = p.why_perfect;
      li.appendChild(w);
    }
    if (p.price_range) {
      const pr = document.createElement('div');
      pr.className = 'price';
      pr.textContent = p.price_range;
      li.appendChild(pr);
    }
    picksList.appendChild(li);
    setTimeout(function() { li.classList.add('in'); }, 60 + pickIndex * 90);
    pickIndex++;
  }

  function showSplurge(s) {
    splurgeHead.style.display = '';
    const card = document.createElement('div');
    card.className = 'splurge';
    card.innerHTML = '';
    const tag = document.createElement('div'); tag.className = 'tag'; tag.textContent = 'splurge'; card.appendChild(tag);
    const name = document.createElement('div'); name.className = 'name'; name.textContent = s.name || ''; card.appendChild(name);
    if (s.description) { const d = document.createElement('div'); d.className = 'description'; d.textContent = s.description; card.appendChild(d); }
    if (s.why_perfect) { const w = document.createElement('div'); w.className = 'why'; w.textContent = s.why_perfect; card.appendChild(w); }
    if (s.price_range) { const pr = document.createElement('div'); pr.className = 'price'; pr.textContent = s.price_range; card.appendChild(pr); }
    splurgeEl.appendChild(card);
    setTimeout(function() { card.classList.add('in'); }, 200);
  }

  es.addEventListener('status', function(e) {
    try { const d = JSON.parse(e.data); setStatus(d.message); } catch(_) {}
  });
  es.addEventListener('portrait', function(e) {
    try {
      const d = JSON.parse(e.data);
      setPortraitText(d.text || '', !!d.complete);
    } catch(_) {}
  });
  es.addEventListener('through_line', function(e) {
    try { appendThreadLine(JSON.parse(e.data)); } catch(_) {}
  });
  es.addEventListener('pick', function(e) {
    try { appendPick(JSON.parse(e.data)); } catch(_) {}
  });
  es.addEventListener('splurge', function(e) {
    try { showSplurge(JSON.parse(e.data)); } catch(_) {}
  });
  es.addEventListener('done', function() {
    setStatus('Composed', true);
    es.close();
  });
  es.addEventListener('error', function(e) {
    if (e.data) {
      try { const d = JSON.parse(e.data); setStatus('Error: ' + (d.message || 'unknown'), true); }
      catch(_) { setStatus('Connection lost', true); }
    } else {
      // Browser auto-retry — don't change UI
    }
  });
})();
</script>
</body></html>
"""


# ---------- intake copy by voice ----------

def _intake_copy(partner):
    voice = partner.get("voice_axis", 0.5)
    heading = "Find a gift they'll actually love."
    if voice <= 0.3:
        intro = "Tell me who you're shopping for. I'll suggest the gifts a thoughtful friend would land on — useful, well-chosen, right for them."
    elif voice >= 0.7:
        intro = "Tell me who you're shopping for. I'll read them carefully and put together a list with taste — gifts that say I see you."
    else:
        intro = "Tell me who you're shopping for. I'll build a curated list — a mix of obvious-and-perfect, surprising, and aspirational picks."
    return heading, intro


# ---------- routes ----------

app = Flask(__name__)


@app.route("/")
def admin_home():
    partners = pc.list_partners()
    return render_template_string(ADMIN_HOME, partners=partners, voice_label=_voice_label)


@app.route("/<slug>")
def intake(slug):
    partner = pc.get_partner_by_slug(slug)
    if not partner:
        abort(404)
    heading, intro = _intake_copy(partner)
    return render_template_string(
        INTAKE_HTML,
        partner=partner,
        css=_theme_css(partner),
        intake_heading=heading,
        intake_intro=intro,
        form={},
        error=None,
        voice_label=_voice_label,
    )


@app.route("/<slug>/start", methods=["POST"])
def start(slug):
    partner = pc.get_partner_by_slug(slug)
    if not partner:
        abort(404)

    intake_text = request.form.get("intake_text", "").strip()
    relationship = request.form.get("relationship", "").strip()
    budget_category = request.form.get("budget_category", "").strip()
    recipient_name = request.form.get("recipient_name", "").strip() or None

    error = None
    if len(intake_text) < 20:
        error = "Please tell me a bit more — at least a couple of sentences about them."
    elif relationship not in VALID_RELATIONSHIPS:
        error = "Please pick a relationship."
    elif budget_category not in VALID_BUDGETS:
        error = "Please pick a budget."

    if error:
        heading, intro = _intake_copy(partner)
        return render_template_string(
            INTAKE_HTML,
            partner=partner, css=_theme_css(partner),
            intake_heading=heading, intake_intro=intro,
            form={"intake_text": intake_text, "relationship": relationship, "budget_category": budget_category, "recipient_name": recipient_name or ""},
            error=error, voice_label=_voice_label,
        )

    session_id = uuid.uuid4().hex[:12]
    _save_session(session_id, {
        "session_id": session_id,
        "partner_slug": slug,
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
        "intake": {"intake_text": intake_text, "relationship": relationship, "budget_category": budget_category, "recipient_name": recipient_name},
        "profile": None,
        "curator_output": None,
        "voice_axis_used": partner.get("voice_axis", 0.5),
    })
    logger.info(f"[{slug}] intake saved as session {session_id}; redirecting to results")
    return redirect(url_for("results", slug=slug, session_id=session_id))


@app.route("/<slug>/results/<session_id>")
def results(slug, session_id):
    partner = pc.get_partner_by_slug(slug)
    if not partner:
        abort(404)
    session = _load_session(session_id)
    if not session or session.get("partner_slug") != slug:
        abort(404)
    intake = session.get("intake") or {}
    name = intake.get("recipient_name")
    heading = f"For {name}" if name else "Their gift list"
    return render_template_string(
        RESULTS_HTML,
        partner=partner,
        css=_theme_css(partner),
        results_heading=heading,
        session_id=session_id,
    )


# ---------- streaming endpoint ----------

# Regex matching everything between the opening quote of portrait_prose and
# the next unescaped quote. Used to extract in-progress portrait text from a
# streaming JSON response.
_PORTRAIT_PROGRESS_RE = re.compile(
    r'"portrait_prose"\s*:\s*"((?:\\.|[^"\\])*)',
    re.DOTALL,
)
# Same but anchored to the closing quote — fires once portrait_prose is done.
_PORTRAIT_COMPLETE_RE = re.compile(
    r'"portrait_prose"\s*:\s*"((?:\\.|[^"\\])*)"',
    re.DOTALL,
)


def _replay_session_events(session: dict):
    """Generator that emits the SSE events for an already-completed session
    (in case the user reloads the results page after streaming finished)."""
    out = session.get("curator_output") or {}
    yield _sse("status", {"message": "Loading saved list…"})
    portrait = out.get("portrait_prose") or ""
    if portrait:
        yield _sse("portrait", {"text": portrait, "complete": True})
    for tl in out.get("through_lines", []):
        yield _sse("through_line", tl)
    for p in out.get("product_gifts", []):
        yield _sse("pick", p)
    if out.get("splurge_item"):
        yield _sse("splurge", out["splurge_item"])
    yield _sse("done", {"session_id": session.get("session_id")})


def _build_curator_prompt(profile: dict, recipient_type: str, relationship: str, rec_count: int, voice_axis: float) -> str:
    profile_for_prompt = {
        k: v for k, v in profile.items()
        if k in ("interests", "location_context", "style_preferences",
                 "price_signals", "aspirational_vs_current", "gift_relationship_guidance")
    }
    return CURATOR_PROMPT.format(
        rec_count=rec_count,
        profile_json=json.dumps(profile_for_prompt, indent=2),
        recipient_type=recipient_type,
        relationship=relationship,
        ownership_block=_build_ownership_block(profile),
        avoid_block=_build_avoid_block(profile),
        voice_block=_build_voice_block(voice_axis),
    )


@app.route("/<slug>/stream/<session_id>")
def stream(slug, session_id):
    partner = pc.get_partner_by_slug(slug)
    if not partner:
        abort(404)
    session = _load_session(session_id)
    if not session or session.get("partner_slug") != slug:
        abort(404)

    # Refresh-safe replay
    if session.get("curator_output"):
        return Response(_replay_session_events(session), mimetype="text/event-stream")

    intake = session["intake"]
    voice_axis = partner.get("voice_axis", 0.5)

    def event_stream():
        try:
            client = _client()
            yield _sse("status", {"message": "Reading the person…"})

            try:
                profile = analyze_intake(
                    intake_text=intake["intake_text"],
                    relationship=intake["relationship"],
                    budget_category=intake["budget_category"],
                    recipient_name_or_initial=intake.get("recipient_name"),
                    claude_client=client,
                    model=INTAKE_MODEL,
                )
            except Exception as e:
                logger.exception("intake analyzer failed")
                yield _sse("error", {"message": f"intake analyzer failed: {e}"})
                return

            session["profile"] = profile
            _save_session(session_id, session)

            yield _sse("status", {"message": "Composing the list…"})

            prompt = _build_curator_prompt(
                profile=profile,
                recipient_type="other",
                relationship=intake["relationship"],
                rec_count=10,
                voice_axis=voice_axis,
            )
            logger.info(f"[{slug}] {session_id} starting Opus stream (voice_axis={voice_axis:.2f})")

            buffer = ""
            portrait_complete = False

            with client.messages.stream(
                model=PORTRAIT_MODEL,
                max_tokens=4000,
                system=CURATOR_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            ) as stream_handle:
                for delta in stream_handle.text_stream:
                    if not delta:
                        continue
                    buffer += delta

                    if not portrait_complete:
                        m_complete = _PORTRAIT_COMPLETE_RE.search(buffer)
                        if m_complete:
                            text = _unescape_json_string(m_complete.group(1))
                            yield _sse("portrait", {"text": text, "complete": True})
                            portrait_complete = True
                        else:
                            m_progress = _PORTRAIT_PROGRESS_RE.search(buffer)
                            if m_progress:
                                text = _unescape_json_string(m_progress.group(1))
                                if text:
                                    yield _sse("portrait", {"text": text, "complete": False})

            # Stream complete — parse final JSON
            try:
                parsed = json.loads(_strip_fences(buffer))
            except json.JSONDecodeError as e:
                logger.error(f"[{slug}] {session_id} JSON parse failed: {e}")
                logger.error(f"[{slug}] raw[:500]={buffer[:500]}")
                yield _sse("error", {"message": f"curator returned unparseable JSON: {e}"})
                return

            curator_output = {
                "portrait_prose": parsed.get("portrait_prose"),
                "through_lines": parsed.get("through_lines", []),
                "product_gifts": parsed.get("product_gifts", []),
                "splurge_item": parsed.get("splurge_item"),
                "restraint_omitted": parsed.get("restraint_omitted", []),
                "experience_gifts": [],
            }
            session["curator_output"] = curator_output
            _save_session(session_id, session)
            logger.info(f"[{slug}] {session_id} saved with {len(curator_output['product_gifts'])} picks")

            # In case the regex didn't fire (rare), force a final portrait
            if not portrait_complete and curator_output.get("portrait_prose"):
                yield _sse("portrait", {"text": curator_output["portrait_prose"], "complete": True})

            for tl in curator_output["through_lines"]:
                yield _sse("through_line", tl)
            for p in curator_output["product_gifts"]:
                yield _sse("pick", p)
            if curator_output["splurge_item"]:
                yield _sse("splurge", curator_output["splurge_item"])

            yield _sse("done", {"session_id": session_id})

        except Exception as e:
            logger.exception("stream failed")
            yield _sse("error", {"message": str(e)})

    return Response(event_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    pc.init_db()
    print()
    print("  GiftWise Embed Server (streaming)")
    print(f"  intake model: {INTAKE_MODEL}")
    print(f"  portrait model: {PORTRAIT_MODEL}")
    print(f"  sessions: {SESSIONS_DIR}/")
    print(f"  open http://localhost:5003")
    print()
    app.run(host="127.0.0.1", port=5003, debug=False, threaded=True)
