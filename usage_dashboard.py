"""
Usage dashboard — live view of Claude API spending across all dev apps.

Reads claude_meter's JSONL log at data/api_usage.jsonl and shows:
  - cost + token totals for last hour, today, last 7 days, all-time
  - call breakdown by model and by tag (which app made the call)
  - last 25 calls with timestamps, latency, cost
  - rolling burn rate (USD/hour over last hour)
  - error count

Auto-refreshes every 5 seconds. Open in VSCode's Simple Browser
(Ctrl+Shift+P → "Simple Browser: Show" → http://localhost:5004) to keep
it visible while working.

Run:
    python usage_dashboard.py
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask import Flask, render_template_string

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claude_meter import read_log, LOG_PATH


app = Flask(__name__)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_ts(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return _now()


def _aggregate(records: list) -> dict:
    now = _now()
    today = now.date().isoformat()
    last_hour = now - timedelta(hours=1)
    last_7d = now - timedelta(days=7)

    totals = {"all": _z(), "today": _z(), "last_hour": _z(), "last_7d": _z()}
    by_model = defaultdict(_z)
    by_tag = defaultdict(_z)
    error_count = 0

    for r in records:
        ts = _parse_ts(r.get("timestamp", ""))
        cost = r.get("cost_usd", 0) or 0
        in_tok = r.get("input_tokens", 0) or 0
        out_tok = r.get("output_tokens", 0) or 0

        _add(totals["all"], cost, in_tok, out_tok)
        if ts.date().isoformat() == today:
            _add(totals["today"], cost, in_tok, out_tok)
        if ts >= last_hour:
            _add(totals["last_hour"], cost, in_tok, out_tok)
        if ts >= last_7d:
            _add(totals["last_7d"], cost, in_tok, out_tok)

        m = r.get("model") or "(none)"
        _add(by_model[m], cost, in_tok, out_tok)

        t = r.get("tag") or "(untagged)"
        _add(by_tag[t], cost, in_tok, out_tok)

        if r.get("errored"):
            error_count += 1

    return {
        "totals": totals,
        "by_model": dict(by_model),
        "by_tag": dict(by_tag),
        "error_count": error_count,
        "all_count": len(records),
    }


def _z():
    return {"cost": 0.0, "input": 0, "output": 0, "calls": 0}


def _add(bucket: dict, cost: float, in_tok: int, out_tok: int):
    bucket["cost"] += cost
    bucket["input"] += in_tok
    bucket["output"] += out_tok
    bucket["calls"] += 1


HTML = """
<!doctype html><html><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>Claude meter · GiftWise</title>
<style>
  :root {
    --bg: #0e0e10;
    --panel: #17171a;
    --rule: #2a2a2e;
    --text: #e8e6e0;
    --text-soft: #9a988f;
    --text-muted: #5e5c55;
    --accent: #5cffa9;
    --warn: #ffc857;
    --danger: #ff6b6b;
    --highlight: #4d8fff;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 20px;
    font-size: 13px;
    line-height: 1.5;
  }
  .wrap { max-width: 1100px; margin: 0 auto; }
  h1 {
    font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-soft);
    letter-spacing: 0.05em;
    margin: 0 0 4px;
    text-transform: uppercase;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--rule);
  }
  .header .meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
  }
  .header .meta b { color: var(--text-soft); }
  .grid-totals {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  .card {
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: 6px;
    padding: 16px 18px;
  }
  .card .label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 6px;
    font-weight: 600;
  }
  .card .value {
    font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
    font-size: 26px;
    font-weight: 500;
    color: var(--text);
    letter-spacing: -0.01em;
  }
  .card .value.cost::before {
    content: "$";
    color: var(--accent);
    margin-right: 1px;
  }
  .card .sub {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
  }
  .card.warn .value { color: var(--warn); }
  .card.warn .value.cost::before { color: var(--warn); }
  .section { margin-bottom: 28px; }
  .section h2 {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    font-weight: 700;
    margin: 0 0 10px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: 6px;
    overflow: hidden;
    font-size: 12px;
  }
  th, td {
    text-align: left;
    padding: 8px 12px;
    border-bottom: 1px solid var(--rule);
  }
  th {
    background: #1c1c20;
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 10px;
  }
  tr:last-child td { border-bottom: none; }
  td.mono, th.mono {
    font-family: 'JetBrains Mono', monospace;
    font-variant-numeric: tabular-nums;
  }
  td.right { text-align: right; }
  .empty {
    color: var(--text-muted);
    padding: 20px;
    text-align: center;
    border: 1px dashed var(--rule);
    border-radius: 6px;
    font-size: 12px;
  }
  .errored { color: var(--danger); }
  .pill-tag {
    display: inline-block;
    background: var(--rule);
    color: var(--text-soft);
    padding: 1px 7px;
    border-radius: 8px;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
  }
  .ago {
    color: var(--text-muted);
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
  }
  .row-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 700px) {
    .grid-totals { grid-template-columns: repeat(2, 1fr); }
    .row-grid { grid-template-columns: 1fr; }
  }
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
<div class="wrap">

<div class="header">
  <div>
    <h1>Claude meter</h1>
    <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted);">
      log: {{log_path}} · {{all_count}} calls recorded
    </div>
  </div>
  <div class="meta">
    refreshed <b>{{now}}</b> · auto-refresh 5s
  </div>
</div>

<div class="grid-totals">
  <div class="card{% if totals.last_hour.cost > 1.0 %} warn{% endif %}">
    <div class="label">last hour</div>
    <div class="value cost">{{ '%.4f' % totals.last_hour.cost }}</div>
    <div class="sub">{{totals.last_hour.calls}} calls · {{ '{:,}'.format(totals.last_hour.input + totals.last_hour.output) }} tok</div>
  </div>
  <div class="card">
    <div class="label">today (utc)</div>
    <div class="value cost">{{ '%.4f' % totals.today.cost }}</div>
    <div class="sub">{{totals.today.calls}} calls · {{ '{:,}'.format(totals.today.input + totals.today.output) }} tok</div>
  </div>
  <div class="card">
    <div class="label">last 7 days</div>
    <div class="value cost">{{ '%.2f' % totals.last_7d.cost }}</div>
    <div class="sub">{{totals.last_7d.calls}} calls · {{ '{:,}'.format(totals.last_7d.input + totals.last_7d.output) }} tok</div>
  </div>
  <div class="card">
    <div class="label">all time</div>
    <div class="value cost">{{ '%.2f' % totals.all.cost }}</div>
    <div class="sub">{{totals.all.calls}} calls{% if error_count %} · <span class="errored">{{error_count}} errored</span>{% endif %}</div>
  </div>
</div>

<div class="row-grid">
  <div class="section">
    <h2>By model</h2>
    {% if by_model %}
    <table>
      <tr><th>model</th><th class="right">calls</th><th class="right mono">in tok</th><th class="right mono">out tok</th><th class="right mono">cost</th></tr>
      {% for m, b in by_model_sorted %}
      <tr>
        <td class="mono" style="font-size:11px;">{{m}}</td>
        <td class="right mono">{{b.calls}}</td>
        <td class="right mono">{{ '{:,}'.format(b.input) }}</td>
        <td class="right mono">{{ '{:,}'.format(b.output) }}</td>
        <td class="right mono">${{ '%.4f' % b.cost }}</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}<div class="empty">no calls yet</div>{% endif %}
  </div>

  <div class="section">
    <h2>By app (tag)</h2>
    {% if by_tag %}
    <table>
      <tr><th>tag</th><th class="right">calls</th><th class="right mono">cost</th></tr>
      {% for t, b in by_tag_sorted %}
      <tr>
        <td><span class="pill-tag">{{t}}</span></td>
        <td class="right mono">{{b.calls}}</td>
        <td class="right mono">${{ '%.4f' % b.cost }}</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}<div class="empty">no calls yet</div>{% endif %}
  </div>
</div>

<div class="section">
  <h2>Last {{recent|length}} calls</h2>
  {% if recent %}
  <table>
    <tr>
      <th class="mono">time</th><th>tag</th><th class="mono">model</th><th>type</th>
      <th class="right mono">in</th><th class="right mono">out</th>
      <th class="right mono">elapsed</th><th class="right mono">cost</th>
    </tr>
    {% for r in recent %}
    <tr{% if r.errored %} class="errored"{% endif %}>
      <td class="mono"><span class="ago">{{r.ago}}</span></td>
      <td><span class="pill-tag">{{ r.tag or '(untagged)' }}</span></td>
      <td class="mono" style="font-size:11px;">{{r.model}}</td>
      <td class="mono" style="font-size:11px;color:var(--text-muted);">{{r.type}}{% if r.errored %} · err{% endif %}</td>
      <td class="right mono">{{ '{:,}'.format(r.input_tokens) }}</td>
      <td class="right mono">{{ '{:,}'.format(r.output_tokens) }}</td>
      <td class="right mono">{{ '%.1fs' % r.elapsed_seconds }}</td>
      <td class="right mono">${{ '%.4f' % r.cost_usd }}</td>
    </tr>
    {% endfor %}
  </table>
  {% else %}<div class="empty">no calls yet — run something that hits Claude and refresh</div>{% endif %}
</div>

<div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-muted);margin-top:32px;text-align:center;">
  pricing in claude_meter.PRICING (USD per 1M tokens) · cost is estimate, check console.anthropic.com for billing of record
</div>

</div></body></html>
"""


def _format_ago(ts_str: str, now: datetime) -> str:
    try:
        ts = datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return ts_str
    delta = now - ts
    secs = delta.total_seconds()
    if secs < 60:
        return f"{int(secs)}s ago"
    if secs < 3600:
        return f"{int(secs/60)}m ago"
    if secs < 86400:
        return f"{int(secs/3600)}h ago"
    return f"{int(secs/86400)}d ago"


@app.route("/")
def dashboard():
    records = read_log()
    agg = _aggregate(records)
    now = _now()

    by_model_sorted = sorted(agg["by_model"].items(), key=lambda kv: -kv[1]["cost"])
    by_tag_sorted = sorted(agg["by_tag"].items(), key=lambda kv: -kv[1]["cost"])

    recent_raw = list(reversed(records[-25:]))
    recent = []
    for r in recent_raw:
        recent.append({
            **r,
            "ago": _format_ago(r.get("timestamp", ""), now),
            "input_tokens": r.get("input_tokens", 0),
            "output_tokens": r.get("output_tokens", 0),
            "elapsed_seconds": r.get("elapsed_seconds", 0.0),
            "cost_usd": r.get("cost_usd", 0.0),
            "model": r.get("model", "?"),
            "tag": r.get("tag", "(untagged)"),
            "type": r.get("type", "?"),
            "errored": bool(r.get("errored")),
        })

    return render_template_string(
        HTML,
        log_path=LOG_PATH,
        now=now.strftime("%H:%M:%S UTC"),
        totals=agg["totals"],
        by_model=agg["by_model"],
        by_model_sorted=by_model_sorted,
        by_tag=agg["by_tag"],
        by_tag_sorted=by_tag_sorted,
        recent=recent,
        error_count=agg["error_count"],
        all_count=agg["all_count"],
    )


if __name__ == "__main__":
    print()
    print("  Claude meter dashboard")
    print(f"  log: {LOG_PATH}")
    print(f"  open http://localhost:5004")
    print(f"  (or in VSCode: Ctrl+Shift+P -> 'Simple Browser: Show' -> that URL)")
    print()
    app.run(host="127.0.0.1", port=5004, debug=False)
