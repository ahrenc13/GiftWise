#!/usr/bin/env bash
# run_tests.sh — local mirror of .github/workflows/test.yml
# Usage: ./run_tests.sh [--smoke]
#   --smoke  also starts Flask and hits /demo (requires ANTHROPIC_API_KEY set)

set -euo pipefail

SMOKE=false
for arg in "$@"; do
  [[ "$arg" == "--smoke" ]] && SMOKE=true
done

PASS=0
FAIL=0

pass() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

echo ""
echo "============================================"
echo "  GiftWise Local Test Suite"
echo "============================================"
echo ""

# ── Syntax checks ──────────────────────────────
echo "[ Syntax checks ]"
SYNTAX_FILES=(
  giftwise_app.py
  recommendation_service.py
  post_curation_cleanup.py
  gift_curator.py
  profile_analyzer.py
  multi_retailer_searcher.py
  awin_searcher.py
  cj_searcher.py
  ebay_searcher.py
  rapidapi_amazon_searcher.py
  smart_filters.py
  interest_ontology.py
  revenue_optimizer.py
  storage_service.py
  search_query_utils.py
  product_schema.py
  config_service.py
  database.py
  site_stats.py
  share_manager.py
)

for f in "${SYNTAX_FILES[@]}"; do
  if python3 -m py_compile "$f" 2>/dev/null; then
    pass "$f"
  else
    fail "$f  ← SYNTAX ERROR"
  fi
done

echo ""

# ── Unit tests (assert-based) ──────────────────
echo "[ Unit tests ]"

if python3 storage_service.py > /tmp/gw_storage.log 2>&1; then
  pass "storage_service.py"
else
  fail "storage_service.py"
  cat /tmp/gw_storage.log
fi

if python3 search_query_utils.py > /tmp/gw_query.log 2>&1; then
  pass "search_query_utils.py"
else
  fail "search_query_utils.py"
  cat /tmp/gw_query.log
fi

if python3 product_schema.py > /tmp/gw_schema.log 2>&1; then
  pass "product_schema.py"
else
  fail "product_schema.py"
  cat /tmp/gw_schema.log
fi

if ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-dummy-key-for-local}" python3 config_service.py > /tmp/gw_config.log 2>&1; then
  pass "config_service.py"
else
  fail "config_service.py"
  cat /tmp/gw_config.log
fi

echo ""

# ── Smoke test (optional) ──────────────────────
if $SMOKE; then
  echo "[ Smoke test ]"
  if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "  ⚠️  ANTHROPIC_API_KEY not set — skipping smoke test"
  else
    python3 giftwise_app.py &
    FLASK_PID=$!
    sleep 3
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/demo)
    kill $FLASK_PID 2>/dev/null
    if [[ "$HTTP" == "200" ]]; then
      pass "/demo returned HTTP 200"
    else
      fail "/demo returned HTTP $HTTP"
    fi
  fi
  echo ""
fi

# ── Summary ────────────────────────────────────
echo "============================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "============================================"
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo "Fix the failures above before pushing."
  exit 1
fi

echo "All checks passed. Safe to push."
