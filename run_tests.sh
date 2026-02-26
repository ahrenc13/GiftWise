#!/bin/bash
# GiftWise local test runner
# Mirrors what GitHub Actions CI runs, so you can catch failures before pushing.
#
# Usage:
#   ./run_tests.sh           # syntax check + service tests
#   ./run_tests.sh --smoke   # also starts Flask and hits /demo (requires API keys)

set -e

PASS=0
FAIL=0
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── helpers ────────────────────────────────────────────────────────────────
ok()   { echo "  ✓ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }

section() {
  echo ""
  echo "── $1 ──────────────────────────────────────────────────────────────"
}

# ── 1. Syntax checks ───────────────────────────────────────────────────────
section "Syntax check: pipeline files"

PIPELINE_FILES=(
  giftwise_app.py
  recommendation_service.py
  profile_analyzer.py
  gift_curator.py
  post_curation_cleanup.py
  multi_retailer_searcher.py
  rapidapi_amazon_searcher.py
  ebay_searcher.py
  awin_searcher.py
  cj_searcher.py
  skimlinks_searcher.py
  etsy_searcher.py
)

for f in "${PIPELINE_FILES[@]}"; do
  if [ -f "$f" ]; then
    if python3 -m py_compile "$f" 2>/dev/null; then
      ok "$f"
    else
      fail "$f — syntax error:"
      python3 -m py_compile "$f"   # print the actual error
    fi
  else
    echo "  – $f (not found, skipping)"
  fi
done

section "Syntax check: service modules"

SERVICE_FILES=(
  storage_service.py
  config_service.py
  product_schema.py
  search_query_utils.py
  smart_filters.py
  interest_ontology.py
  revenue_optimizer.py
  site_stats.py
)

for f in "${SERVICE_FILES[@]}"; do
  if [ -f "$f" ]; then
    if python3 -m py_compile "$f" 2>/dev/null; then
      ok "$f"
    else
      fail "$f — syntax error:"
      python3 -m py_compile "$f"
    fi
  else
    echo "  – $f (not found, skipping)"
  fi
done

# ── 2. Service module tests ────────────────────────────────────────────────
section "Service tests"

# storage_service has real assert statements — a failure here is a real bug
echo "  Running storage_service.py..."
if python3 storage_service.py > /tmp/gw_storage_test.log 2>&1; then
  ok "storage_service (assertions passed)"
else
  fail "storage_service"
  cat /tmp/gw_storage_test.log
fi

echo "  Running search_query_utils.py..."
if python3 search_query_utils.py > /tmp/gw_query_test.log 2>&1; then
  ok "search_query_utils"
else
  fail "search_query_utils"
  cat /tmp/gw_query_test.log
fi

echo "  Running product_schema.py..."
if python3 product_schema.py > /tmp/gw_schema_test.log 2>&1; then
  ok "product_schema"
else
  fail "product_schema"
  cat /tmp/gw_schema_test.log
fi

echo "  Running config_service.py (informational)..."
if python3 config_service.py > /tmp/gw_config_test.log 2>&1; then
  ok "config_service"
else
  # config_service failures are informational — missing API keys are expected locally
  echo "  ~ config_service reported issues (likely missing env vars — OK for local):"
  grep -E "error|Error|MISSING|not set" /tmp/gw_config_test.log | head -5 || true
fi

# ── 3. Optional smoke test ─────────────────────────────────────────────────
if [[ "$1" == "--smoke" ]]; then
  section "Smoke test: Flask /demo"

  if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "  ⚠ ANTHROPIC_API_KEY not set — skipping smoke test"
    echo "  Set it first: export ANTHROPIC_API_KEY=your_key"
  else
    echo "  Starting Flask on port 5099..."
    python3 giftwise_app.py &
    FLASK_PID=$!
    sleep 3

    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5099/demo 2>/dev/null || echo "000")

    kill $FLASK_PID 2>/dev/null || true

    if [[ "$HTTP_STATUS" == "200" ]]; then
      ok "/demo returned HTTP 200"
    else
      fail "/demo returned HTTP $HTTP_STATUS (expected 200)"
    fi
  fi
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
if [ $FAIL -eq 0 ]; then
  echo "  ✅ All checks passed — safe to push"
  exit 0
else
  echo "  ❌ $FAIL check(s) failed — fix before pushing"
  exit 1
fi
