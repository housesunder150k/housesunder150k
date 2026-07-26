# Session 4 Report — Ingestion Pipeline
**Date:** 2026-07-26
**Duration:** ~4 hours
**Status:** Complete

---

## Objective

Write the ingestion pipeline script, test it end-to-end against the Repliers test API key, and deploy it to Railway.

---

## What Was Built

### scripts/ingest.py
Full Python ingestion pipeline. Functions:
- `fetch_listings()` — GET Repliers /listings?status=A&maxPrice=150000
- `score_listing()` — Claude Call 1, scoring prompt, returns SCORE/TIER/CATEGORY/KEY_HOOKS/REASON/DEAL_OF_DAY_CANDIDATE
- `generate_content()` — Claude Call 2, content prompt, returns HEADLINE/NARRATIVE/SOCIAL_CAPTION/SHORT_SUMMARY
- `upload_image()` — fetches images[0] from Repliers CDN, uploads to Cloudflare Images, returns permanent URL
- `write_webflow()` — POST to Webflow v2 CMS API
- `publish_webflow()` — POST to Webflow publish endpoint
- `write_post_record()` — writes posts/[slug].json for dedup
- `log_tokens()` — logs input tokens, output tokens, estimated cost after every Claude call
- `make_realtor_url()` — constructs per-listing Realtor.com address search URL for affiliate-url field
- `run_pipeline()` — main loop, stats summary

### requirements.txt
```
requests==2.31.0
anthropic==0.20.0
```

### Procfile
```
worker: python scripts/ingest.py
```

---

## Issues Encountered and Resolved

### 1. REPLIERS_API_KEY had leading whitespace
First deployment crashed with `Invalid leading whitespace in header value`. Fixed by editing the Railway variable to remove the leading space.

### 2. Webflow workspace token missing cms:write scope
Workspace tokens (Workspace Settings → Integrations) do NOT have cms:write regardless of plan. Fix: generate a site-level token (Site Settings → Integrations → API Access). Site tokens have CMS read/write + Sites read/write scopes available.

### 3. Repliers image URLs are relative paths
Test data returns `sample/IMG-NWM2145873_0.jpg` not a full URL. Fix: prepend `https://cdn.repliers.io/` to any image path that doesn't start with `http`. Confirmed from Repliers docs — production images from live MLS key will be full CDN URLs.

### 4. Narrative body had duplicate affiliate link
Content prompt instructed Claude to end narrative with `See the full listing here → {affiliate_url}`. This produced a plain text URL below the narrative on the listing page, duplicating the "View Full Listing" CTA button. Fix: removed the CTA instruction from the content prompt. Narrative now ends on the story.

### 5. Realtor.com affiliate URL was zip-only
`make_realtor_url()` was falling through to zip-only path on some test data records because `streetNumber` and `streetName` fields were empty in sample data. Function logic is correct — verified in isolation. Will confirm with real Repliers MLS data in Session 5. Test data limitation only.

### 6. Dedup resets on Railway deploy
`posts/[slug].json` lives in the Railway container filesystem. Every new deploy loses the dedup history, causing re-publication of already-seen listings. Produced duplicates during Session 4. Fix: manually deleted duplicates via Webflow MCP. Permanent fix: move dedup to Supabase table — Session 5 first item.

### 7. Tulalip listing stray separator
Content prompt produced `---` separator in the listing name and narrative body. Cleaned via Webflow MCP `update_collection_items` + `publish_collection_items`. Prompt fix in place prevents recurrence.

### 8. Duplicate no-image Tulalip listing
First successful run published Tulalip without an image (image URL fix not yet deployed). Second run republished with image. Deleted the no-image version via Webflow MCP `unpublish_collection_items` + `delete_collection_items`.

---

## Pipeline Performance (Confirmed Session 4)

### Token costs (actual, not estimated)
| Call | Input tokens | Output tokens | Cost/call |
|---|---|---|---|
| Scoring (original prompt) | ~2,100–2,300 | ~110–200 | ~$0.009 |
| Scoring (trimmed prompt) | ~990–1,180 | ~100–160 | ~$0.005 |
| Content generation | ~970–1,130 | ~410–480 | ~$0.010 |

**Scoring prompt trimmed ~65%** — from ~1,800 tokens to ~650 tokens of instructions. All rules intact. Estimated monthly cost at steady state: ~$15–18/month.

### Run statistics (final run of session)
- 50 listings fetched (9,586 total available in test pool)
- 5 published, 45 discarded, 0 errors
- Run time: ~319 seconds (~5.3 minutes)
- Railway Hobby plan impact: ~9 hours/month execution — well within $5/month flat fee

---

## All APIs Confirmed Working

| Integration | Status | Notes |
|---|---|---|
| Repliers → ingest.py | ✅ | Fetches 50 listings, all fields parse correctly |
| Claude scoring | ✅ | Correct scores, token logging working |
| Claude content gen | ✅ | Headlines, narratives, captions, summaries all correct voice |
| Cloudflare Images | ✅ | Images uploading, permanent URLs returned, showing on site |
| Webflow CMS write | ✅ | Site-level token required (not workspace token) |
| Webflow publish | ✅ | Items go live immediately after write |
| Dedup (filesystem) | ✅ (temporary) | Works within a deploy — resets on redeploy — Supabase fix needed |

---

## Live Listings at Session End

7 listings live on housesunder150k.com:

| Slug | Title |
|---|---|
| `brand-new-construction-milwaukee-105000` | Brand-New Construction in Milwaukee for $105,000 (manual) |
| `tulalip-70000` | Puget Sound Waterfront Cabin. 1940. $70,000. |
| `mound-city-135000` | 1900 Kansas Farmhouse. New Shell. You Finish the Inside. $135K. |
| `kansas-city-135000` | 1904 Kansas City Stone House. All New Systems. $135K. |
| `kansas-city-150000` | 2,208 Square Feet in Kansas City. Two Fireplaces. $150K. |
| `longton-20000` | 1870 Kansas Church. Stained Glass Intact. $20,000. |
| `topeka-138750` | 1900 Stone Four-Plex Near Washburn University. $138,750. |

All have hero images via Cloudflare Images. All have per-listing Realtor.com address search URLs in affiliate-url field.

---

## Railway Configuration

- **Service ID:** 15ca3583-43d1-4823-bf3d-5740976e439c
- **Cron:** `0 13,18,23 * * *` (8am, 1pm, 6pm CT expressed in UTC) — set via MCP
- **Procfile:** `worker: python scripts/ingest.py`
- **All 7 env vars confirmed present in Railway service**

---

## Key Decisions Made This Session

| # | Decision |
|---|---|
| 29 | Webflow site-level token required for cms:write — workspace token does NOT have this scope |
| 30 | Repliers image paths are relative — prepend https://cdn.repliers.io/ |
| 31 | No CTA line in narrative — site CTA block handles it, plain text URL was duplicate |
| 32 | affiliate-url field = per-listing Realtor.com address search URL, not Sovrn link |
| 33 | Sovrn link removed from per-listing affiliate-url — Realtor.com address URL used instead. Sovrn tracking integration deferred until approval and Session 6 |
| 34 | Dedup = filesystem posts/[slug].json for now — Supabase migration in Session 5 |
| 35 | Scoring prompt trimmed ~65% — all rules intact, cost reduced ~45% |
| 36 | Cloudflare Images kept in pipeline despite Repliers Standard plan including CDN — permanent URLs + no dependency on Repliers CDN uptime worth $5/month |
| 37 | Repliers Standard ($199/mo monthly) is correct tier — no cheaper alternative exists for nationwide US MLS without license requirement |
| 38 | Railway Hobby plan ($5/mo flat) is sufficient — cron pipeline uses ~9 hours/month, no overage risk |
| 39 | Railway cron set to `0 13,18,23 * * *` (UTC) = 8am/1pm/6pm CT — set via Railway MCP |

---

## Open Items for Session 5

1. **Persistent dedup** — replace posts/[slug].json with Supabase table. Critical before going live — every Railway deploy currently resets dedup history.
2. **Clear test data** — delete all current test listings from Webflow CMS before live key activation.
3. **Subscribe to Repliers Standard** ($199/mo) — confirmed no cheaper alternative exists.
4. **Verify Realtor.com URL construction** — `make_realtor_url()` confirmed correct in isolation but test data has incomplete address fields. Verify streetNumber/streetName/streetSuffix/zip all populate correctly with real MLS data.
5. **Validate token costs** — first live run will establish real cost per published listing. Monitor Anthropic console.
6. **Tune scoring threshold** if publish volume too high or too low on real data.
7. **Swap SOVRN_AFFILIATE_URL** to real tracking URL when Sovrn approval comes through.
8. **Railway cron activates on next deploy** — will fire automatically once Session 5 code is pushed.

---

## Repliers Alternatives Research

Conducted during Session 4. Conclusion: Repliers at $199/month is the correct and only practical option for nationwide US MLS data without a real estate license. SimplyRETS ($49-99/mo) requires existing MLS membership/credentials. RealEstateAPI.com ($599+) is a property records platform, not live listings. No viable alternative exists at lower cost for this use case.

---

## Session 5 Start Prompt

"Read the primer at houses-under-150k/vault/primer/_primer.md before doing anything else. This is Session 5 of the HousesUnder150K.com build. Session 5 objective: fix persistent dedup with Supabase, clear test data from Webflow, subscribe to Repliers live MLS key, run first live pipeline, validate content quality and token costs."
