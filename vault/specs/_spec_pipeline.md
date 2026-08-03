---
project: HousesUnder150K
file: spec_pipeline
type: living — update when ingest.py changes
last_updated: 2026-08-03
script: scripts/ingest.py
---

<!-- HousesUnder150K spec_pipeline -->

# HousesUnder150K — Pipeline Spec

This HousesUnder150K pipeline spec defines the ingest.py discovery and publishing pipeline. Load for any session touching ingest.py, the cron schedule, scoring flow, Webflow writes, or Supabase dedup.

<!-- HousesUnder150K spec_pipeline -->

## HousesUnder150K Pipeline Spec — Overview

`ingest.py` is the main discovery and publishing pipeline. It runs as a Railway cron worker 6 times per day, fetches listings from RealtyAPI, scores them with Claude, generates content for qualifying listings, uploads images to Cloudflare, publishes to Webflow CMS, and records all state to Supabase.

**Railway service:** `housesunder150k` (ID: `15ca3583-43d1-4823-bf3d-5740976e439c`)
**Cron:** `0 13,17,21,1,5,9 * * *` — 6 runs/day, 4-hour intervals (CT: 8am/1pm/6pm/8pm CT ≈ UTC offset)
**Procfile:** `worker: python scripts/ingest.py`
**Daily publish limit:** `DAILY_PUBLISH_LIMIT=10` Railway env var — change without deploy

---

<!-- HousesUnder150K spec_pipeline -->

## HousesUnder150K Pipeline Spec — Pipeline Flow

```
1. INSERT pipeline_runs row (started_at)

2. Check CT daily count from published_listings
   → if count >= DAILY_PUBLISH_LIMIT: log and exit (zero API calls made)

3. fetch_listings()
   → Shuffle US_STATES list (24 states in rotation)
   → For each state:
       GET /search/bylocation (50 results)
       For each result: GET /details/byid (description + year_built)
       normalize_listing() → standard dict
       Collect 1 listing per state (state_published flag)
   → Target: 50 total listings across states

4. For each listing:
   a. Check published_listings by slug → skip if already published
   b. Check seen_listings by mls_number (7-day window) → skip if seen recently
   c. score_listing() → upsert to seen_listings regardless of score
   d. If score <= 5: skip
   e. generate_content()
   f. If HEADLINE or NARRATIVE empty: skip (empty content guard)
   g. upload_image() → Cloudflare Images
   h. write_webflow() → POST to Webflow v2 CMS API
   i. publish_webflow() → item-level publish (staging push)
   j. db_insert_published() → record in published_listings
   k. Check if daily limit now hit → break loop

5. UPDATE pipeline_runs row (completed_at, all stats, est_cost_usd)

6. If published_this_run > 0: publish_site() (full site to both custom domain IDs)
```

---

<!-- HousesUnder150K spec_pipeline -->

## HousesUnder150K Pipeline Spec — Functions

### fetch_listings()
- Shuffles `US_STATES` list for geographic diversity
- For each state: `GET /search/bylocation` with standard params
- For each result: `GET /details/byid` for description and year_built
- `state_published` flag ensures 1 listing collected per state per run
- Returns list of normalized listing dicts

### normalize_listing()
- Maps RealtyAPI response fields to standard internal dict
- Computes `slug` from address + city + state abbreviation (e.g. `409-n-davis-ave-oakland-ne`)
- Extracts `is_pending` flag — ⚠ pending listings not yet skipped before scoring
- Sets `listingHref` from search result `href` field (used as affiliate_url)

### score_listing(listing)
- Claude Call 1
- Sends listing data + description to scoring prompt
- Strips markdown formatting from response (`**bold**`, `#`, `---`)
- Returns `(score_data_dict, cost_usd)`
- `score_data_dict` contains: SCORE, TIER, CATEGORY, KEY_HOOKS, REASON, DEAL_OF_DAY_CANDIDATE

### generate_content(listing, score_data)
- Claude Call 2 — only runs if score >= 6
- Sends listing data + CATEGORY + KEY_HOOKS from score_data
- Strips markdown formatting from response
- Returns `(content_dict, cost_usd)`
- `content_dict` contains: HEADLINE, NARRATIVE, SOCIAL_CAPTION, SHORT_SUMMARY

### upload_image(listing)
- Fetches `photos[0]` URL from listing
- Prepends `https://cdn.repliers.io/` if path is relative (does not start with `http`)
- POSTs to Cloudflare Images API as multipart form
- Returns permanent Cloudflare Images delivery URL

### write_webflow(listing, content, score_data, is_hero)
- `slug` built from `make_slug(address, city, state_abbr)` — address+city+state format
- POSTs to `POST /v2/collections/{collection_id}/items`
- `is_hero` passed in explicitly — determines `deal-of-the-day` field value
- If `is_hero = True`: calls `unset_deal_of_the_day()` first to clear any previous holder
- Writes all fieldData using field slugs as keys
- `hero-image` format: `{"url": "cloudflare_url", "alt": headline}`
- `narrative-body` format: `"<p>para</p><p>para</p>"`
- `status` field: Active option ID `3b41185e9af84f92d8da092965308a2d`
- `us-state` field: looked up from `STATE_TO_WEBFLOW_ITEM_ID` dict by state abbreviation
- `state-page-url` field: computed from `STATE_TO_SLUG` dict
- Returns Webflow item ID

### publish_webflow(item_id)
- `POST /v2/collections/{collection_id}/items/{item_id}/live`
- Pushes item to Webflow staging

### publish_site()
- `POST /v2/sites/{site_id}/publish`
- Body: `{"customDomains": ["6a661987994ab168be06566b", "6a661986994ab168be065664"]}`
- Pushes to housesunder150k.com and www.housesunder150k.com
- Called once per run after all items published, not per-item

### db_count_published_today()
- `SELECT COUNT(*) FROM published_listings WHERE published_date_ct = today_ct`
- Returns integer count for CT calendar day

### db_slug_published(slug)
- `SELECT 1 FROM published_listings WHERE slug = ?`
- Returns bool

### db_mls_seen_recently(mls_number)
- `SELECT 1 FROM seen_listings WHERE mls_number = ? AND last_seen_at > now() - interval '7 days'`
- Returns bool

### db_upsert_seen(listing, score_data)
- INSERT or UPDATE `seen_listings` — runs for every scored listing regardless of score
- Updates `last_seen_at` and `times_seen` on repeat

### db_insert_published(listing, content, score_data, webflow_item_id, hero_image_url)
- INSERT into `published_listings`
- Sets `published_date_ct` from CT calendar day
- Sets `is_deal_of_day` based on `is_hero`

### db_insert_run() / db_update_run()
- Creates pipeline_runs row at start
- Updates with final stats, cost, and `daily_limit_hit` flag at end

### db_deal_of_day_chosen_today()
- Checks if any listing already has `is_deal_of_day = true` for today's CT date
- Returns bool

### db_get_active_deal_of_day()
- Returns slug of current deal-of-the-day holder

### unset_deal_of_the_day(slug)
- Sets `deal-of-the-day = false` on the previous holder in Webflow CMS
- Sets `is_deal_of_day = false` in Supabase for the previous holder
- Called by `write_webflow()` before writing a new hero listing

### get_today_ct()
- Returns today's date in `America/Chicago` timezone via pytz
- Correct for both CST and CDT

---

<!-- HousesUnder150K spec_pipeline -->

## HousesUnder150K Pipeline Spec — Deal of the Day Logic

A listing qualifies as Deal of the Day if:
- `score_data["DEAL_OF_DAY_CANDIDATE"] == "YES"` (score 9-10 from Claude)
- No deal-of-the-day has been set yet for today's CT calendar day

If both conditions are met, `is_hero = True` is passed to `write_webflow()`, which:
1. Calls `unset_deal_of_the_day()` to clear any previous holder
2. Writes the new item with `deal-of-the-day: True`
3. Calls `db_insert_published()` with `is_deal_of_day=True`

The Deal of the Day resets naturally at CT midnight — `db_deal_of_day_chosen_today()` is date-scoped, same mechanism as the daily publish limit counter.

---

<!-- HousesUnder150K spec_pipeline -->

## HousesUnder150K Pipeline Spec — Content Parser (Markdown Strip)

Claude occasionally wraps output labels in markdown formatting. The parser strips:
- `**bold**` → removes `**` markers
- `#` hash prefixes from label lines
- `---` separator lines

Applied before parsing SCORE, HEADLINE, NARRATIVE, etc. from both Claude responses.

---

## HousesUnder150K Pipeline Spec — Known Gaps (as of Session 8)

1. **`is_pending` check not implemented.** Pending listings (`flags.is_pending == true`) are currently scored and consume a token. Should be skipped before `score_listing()` is called.
2. **`REPLIERS_API_KEY` still in Railway.** Unused since pivot to RealtyAPI. Should be removed.
3. **Realtor.com image relative path prepend** — confirmed needed with test data; verify behavior with live data if image upload failures occur.

---

<!-- HousesUnder150K spec_pipeline -->

## HousesUnder150K Pipeline Spec — Environment Variables (ingest.py)

| Variable | Notes |
|----------|-------|
| `ANTHROPIC_API_KEY` | |
| `CLOUDFLARE_ACCOUNT_ID` | `af60f586464675e914119c0743898631` |
| `CLOUDFLARE_API_TOKEN` | |
| `DAILY_PUBLISH_LIMIT` | `=10` — change without deploy |
| `REALTYAPI_KEY` | |
| `REPLIERS_API_KEY` | ⚠ unused — remove |
| `SOVRN_AFFILIATE_URL` | test link until approval |
| `SUPABASE_KEY` | service role key |
| `SUPABASE_URL` | `https://krzpkaxvbmpdeluqzkka.supabase.co` |
| `WEBFLOW_API_TOKEN` | site-level token only |
| `WEBFLOW_COLLECTION_ID` | `6a650bab14666c3157f27618` |

---

## HousesUnder150K Pipeline Spec — Cron Overlap Warning

Railway does not skip overlapping cron runs. If a run is in progress when the next cron fires, two containers run simultaneously causing:
- Race conditions on `db_count_published_today()`
- Duplicate Webflow item writes
- Empty Webflow items (both containers try to publish the same listing)

**Never use `*/5` cron in production.** Use Railway MCP redeploy for manual triggers. Always wait for `=== Pipeline complete ===` in logs before triggering again.

---

<!-- HousesUnder150K spec_pipeline -->

## HousesUnder150K Pipeline Spec — Seen Suppression Constants

```python
SEEN_SUPPRESSION_DAYS = 7   # hardcoded in script
```

`DAILY_PUBLISH_LIMIT` is an env var. `SEEN_SUPPRESSION_DAYS` is hardcoded. If suppression window needs changing, it requires a code change and redeploy.
