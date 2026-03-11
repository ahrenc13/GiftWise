# GiftWise — Testing

## Quick Validation (Run Before Committing)

```bash
# Core service tests (78 total)
for module in storage_service.py search_query_utils.py config_service.py product_schema.py api_client.py auth_service.py base_searcher.py image_fetcher.py; do
    echo "Testing $module..."
    python3 $module || exit 1
done
echo "All service tests passed"

# Syntax check critical files
python3 -m py_compile giftwise_app.py recommendation_service.py
```

## Local Testing

```bash
python giftwise_app.py
# http://localhost:5000/demo          — fake data, no API calls
# http://localhost:5000/demo?admin=true — real pipeline with @chadahren
```

**Verify:** Homepage loads, demo works, at least 1 guide loads, 1 blog post loads, no 500 errors.

## Full Pipeline Checklist

- [ ] Profile built (interests extracted)
- [ ] Products found from multiple retailers
- [ ] Gifts curated with `why_perfect` descriptions
- [ ] Material links work
- [ ] Images load (not all placeholders)
- [ ] Experience cards show Book/Plan badges

## Pre-Deploy Checklist

1. Run service tests (above)
2. Syntax check critical files
3. Test locally with `/demo`
4. Push to feature branch first
5. Test Railway preview deployment
6. Merge to `main` via PR (triggers auto-deploy)
7. Smoke test at giftwise.fit

## Railway Preview Deploys

1. Railway dashboard → your project → service → Deployments
2. Deploy → Deploy from branch → pick feature branch
3. Railway gives temporary URL
4. Test at that URL
5. If good, merge branch to main on GitHub

## Rollback

Railway → Deployments → find last working deployment → click Redeploy. ~60 seconds.
