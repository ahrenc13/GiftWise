"""
claude_meter — wraps anthropic.Anthropic so every messages.create() and
messages.stream() call is logged with timestamp, model, token counts, latency,
and estimated USD cost.

Distinct from usage_tracker.py (which is the production app's
shelve-based telemetry). This is dev-time observability for the v2 rebuild.

Log format: JSON Lines at data/api_usage.jsonl. Each line is one call.

Usage:
    from claude_meter import make_client
    client = make_client(tag="embed_server")
    # client.messages.create(...) and client.messages.stream(...) work as usual.

Pricing in PRICING is best-effort; update as Anthropic changes prices. The
dashboard surfaces both token counts and the USD estimate so a stale price
doesn't quietly mislead.
"""

import json
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)

LOG_PATH = os.environ.get("CLAUDE_USAGE_LOG", "data/api_usage.jsonl")


# USD per 1M tokens. Update if Anthropic changes pricing.
PRICING = {
    "claude-opus-4-7":    {"input": 15.0, "output": 75.0},
    "claude-opus-4-6":    {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6":  {"input": 3.0,  "output": 15.0},
    "claude-sonnet-4-5":  {"input": 3.0,  "output": 15.0},
    "claude-haiku-4-5":   {"input": 0.80, "output": 4.0},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING.get(model)
    if not p:
        for k, v in PRICING.items():
            if model.startswith(k):
                p = v
                break
    if not p:
        return 0.0
    return (input_tokens / 1_000_000) * p["input"] + (output_tokens / 1_000_000) * p["output"]


def _log_call(record: dict):
    os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.error(f"claude_meter log write failed: {e}")


class _TrackedMessages:
    def __init__(self, real_messages, tag: str):
        self._real = real_messages
        self._tag = tag

    def create(self, **kwargs):
        start = time.time()
        errored = False
        try:
            response = self._real.create(**kwargs)
        except Exception:
            errored = True
            elapsed = time.time() - start
            _log_call({
                "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
                "tag": self._tag,
                "model": kwargs.get("model", ""),
                "type": "create",
                "input_tokens": 0,
                "output_tokens": 0,
                "elapsed_seconds": round(elapsed, 2),
                "cost_usd": 0.0,
                "errored": True,
            })
            raise
        elapsed = time.time() - start
        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "input_tokens", 0) if usage else 0
        out_tok = getattr(usage, "output_tokens", 0) if usage else 0
        model = kwargs.get("model", "")
        cost = estimate_cost(model, in_tok, out_tok)
        _log_call({
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "tag": self._tag,
            "model": model,
            "type": "create",
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "elapsed_seconds": round(elapsed, 2),
            "cost_usd": round(cost, 5),
            "errored": False,
        })
        return response

    def stream(self, **kwargs):
        return _TrackedStreamCtx(self._real.stream(**kwargs), kwargs.get("model", ""), self._tag)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _TrackedStreamCtx:
    """Wraps the SDK's stream() context manager. Reads the final message
    on exit to capture usage tokens."""

    def __init__(self, real_ctx, model: str, tag: str):
        self._real_ctx = real_ctx
        self._model = model
        self._tag = tag
        self._start = None
        self._stream_obj = None

    def __enter__(self):
        self._start = time.time()
        self._stream_obj = self._real_ctx.__enter__()
        return self._stream_obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - (self._start or time.time())
        in_tok = 0
        out_tok = 0
        try:
            final = self._stream_obj.get_final_message()
            usage = getattr(final, "usage", None)
            if usage:
                in_tok = getattr(usage, "input_tokens", 0)
                out_tok = getattr(usage, "output_tokens", 0)
        except Exception as e:
            logger.warning(f"claude_meter could not read stream final message: {e}")

        cost = estimate_cost(self._model, in_tok, out_tok)
        _log_call({
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "tag": self._tag,
            "model": self._model,
            "type": "stream",
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "elapsed_seconds": round(elapsed, 2),
            "cost_usd": round(cost, 5),
            "errored": exc_type is not None,
        })
        return self._real_ctx.__exit__(exc_type, exc_val, exc_tb)


class TrackedClient:
    """Drop-in for anthropic.Anthropic — proxies everything but instruments
    .messages.create() and .messages.stream()."""

    def __init__(self, real_client=None, tag: str = ""):
        if real_client is None:
            import anthropic
            real_client = anthropic.Anthropic()
        self._real = real_client
        self._tag = tag
        self.messages = _TrackedMessages(real_client.messages, tag=tag)

    def __getattr__(self, name):
        return getattr(self._real, name)


def make_client(tag: str = "") -> TrackedClient:
    return TrackedClient(tag=tag)


def read_log(limit: int = None) -> list:
    """Read the JSONL log. Optionally take the last `limit` records."""
    if not os.path.exists(LOG_PATH):
        return []
    records = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if limit is not None:
        return records[-limit:]
    return records
