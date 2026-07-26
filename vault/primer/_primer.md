---
project: HousesUnder150K
entity: HousesUnder150K.com — housesunder150k@gmail.com
updated: 2026-07-27 — Session 6 complete
phase: Pipeline live on Realtor.com via RealtyAPI. 7 real listings on site. Scoring, content, publishing all working.
next_action: Session 7 — Deal of the Day page, gallery field wiring, hero image fix, pending status check on ingest
---

## What This Project Is

HousesUnder150K.com is POC Site 1 of a planned 10-site media holding company built on automated content pipelines. Real estate content platform surfacing listings under $150K, scoring them editorially, generating AI narrative in the voice of Michelle Bowers (theoldhouselife.com), publishing to website and social, monetizing via display ads, affiliate links, and email subscriptions.

**The only metric that matters right now: $1,000/month within 90 days of launch.**

---

## CRITICAL: Data Source

**Repliers API — DEAD END. Do not pursue. MLS license required.**

**RealtyAPI (realtyapi.io) — CURRENT DATA SOURCE**
- Endpoint: `https://realtor.realtyapi.io` (Realtor.com)
- PRO plan: $20/mo, 20,000 requests/month
- Railway env var: `REALTYAPI_KEY`
- MCP: https://mcp.realtyapi.io/mcp (reconnect if key errors)
- 1,969+ results per state — full nationwide coverage

**Key Realtor.com API response fields (confirmed live):**
- Search: `searchResults[]` — `property_id`, `listing_id`, `list_price`, `beds`, `baths`, `sqft`, `lot_sqft`, `address.line/city/state_code/postal_code`, `primary_photo` (string URL), `photos[]` (string URLs), `href` (direct listing URL), `flags.is_pending`
- Detail (`/details/byid?property_id=X`): response root is `detail` — description at `detail.details.text`, year built at `detail.details.year_built`, status at `detail.status`, pending at `detail.flags.is_pending`

---

## Current Build State

### LIVE AND WORKING
- housesunder150k.com — SSL active, Webflow Premium
- Pipeline: RealtyAPI → Claude scoring → content gen → Cloudflare Images → Webflow CMS → auto site publish
- Railway cron: `0 13,17,21,1,5,9 * * *` = 6 runs/day, 4-hour intervals CT
- Daily publish limit: 10/day via DAILY_PUBLISH_LIMIT env var
- Supabase: 3 tables (published_listings, seen_listings, pipeline_runs) — live
- 7-day seen listing suppression
- 7 real listings live on site (Realtor.com data)
- Affiliate URLs: direct Realtor.com property page links
- Homepage: hero → Deal of the Day section → Latest Deals grid → subscribe
- Deal of the Day section: static (Wheeling WV) — needs CMS binding next session
- Latest Deals grid: filtered to exclude deal-of-the-day listings
- Nav: Search by State | Deal of the Day | About | Subscribe
- gallery-images MultiImage field added to CMS — not yet wired to template

### 7 LIVE LISTINGS
| Slug | Headline | Score | Notes |
|---|---|---|---|
| wheeling-100000 | Castle House. Road Bricks. Marble Floors. $100,000. | 9 | DEAL OF THE DAY — manually entered |
| andover-100000 | 1890 Ohio Farmhouse. 12 Acres. Auction Opens at $100K. | 7 | FEATURED |
| johnstown-82500 | 1900 Johnstown Home. Sauna Steam Shower. $82,500. | 6 | |
| greenbrier-149900 | Brand New Build in Arkansas. $149,900. Furnished. | 6 | |
| woodville-149000 | (latest pipeline run) | 6 | |
| russellville-146900 | New HVAC, 2-Car Garage, Two Lots. $146,900. | 6 | |
| indianapolis-145000 | One Acre in Indianapolis. Three Bedrooms. $145,000. | 6 | |

### PENDING NEXT SESSION
1. Build Deal of the Day page (`/deal-of-the-day`)
2. Wire gallery-images MultiImage field on listing template (needs Designer)
3. Fix hero image stretching on listing detail page
4. Add pending status check to ingest pipeline (skip `is_pending: true`)
5. Build maintenance job — daily check of published listings for sold/pending removal
6. Commit all local ingest.py changes
7. Sovrn approval — swap affiliate URL when approved

---

## Session Protocol

### Session Start
1. Read this primer
2. Read vault/status/build_status.md
3. Confirm Webflow MCP, Railway MCP, Supabase MCP, RealtyAPI MCP all connected
4. Never assume field IDs, option IDs, or API schemas from memory
5. Check Supabase published_listings and Railway logs before touching anything

### Session End
1. Update vault/status/build_status.md
2. Update this primer
3. Write session report to vault/sessions/YYYY-MM-DD_[description].md
4. git add . && git commit -m "session: [desc]" && git push origin main

---

## Stack — Full Reference

---

### WEBFLOW
**Account:** housesunder150k@gmail.com
**Plan:** Premium $25/mo billed yearly
**Site ID:** 6a650a7eb2639262c4b6adb7
**Designer:** https://housesunder150k.design.webflow.com
**API Token:** Site-level token (Site Settings → Integrations → API Access)
  WARNING: Workspace tokens do NOT have cms:write scope

**Page IDs:**
- Homepage: 6a650a80b2639262c4b6adba
- Listing Template: 6a650bab14666c3157f2761e
- Deal of the Day: 6a6612c009d35063c09f9ac3
- About: 6a6612c0d157d1643e103769
- States Index: 6a6612c171f470cf8a437d71

**Custom Domain IDs (for publish_site API calls):**
- housesunder150k.com: 6a661987994ab168be06566b
- www.housesunder150k.com: 6a661986994ab168be065664

**CMS Collection Listings:** 6a650bab14666c3157f27618

**CMS Fields (slug → field ID):**
- name, slug, price, price-display, location-display, address, city, state
- year-built, bedrooms, bathrooms, square-feet
- hero-image, gallery-images (MultiImage — added Session 6, not yet wired)
- narrative-body, short-summary, listing-url, affiliate-url, social-caption
- status, deal-of-the-day
- gallery-images field ID: ffcf9ac5d5ea6fd3cea7765bf596ea1d

**Status Option IDs:**
Active:   3b41185e9af84f92d8da092965308a2d
Pending:  001257c77d3ccd4477d620ac135a4afd
Sold:     541de6b6934cd79d6a76c98d91610063
Expired:  e630110b6993074e3f7299e8dbb7fdc1

**Pipeline writes via:**
POST https://api.webflow.com/v2/collections/{collection_id}/items
Authorization: Bearer {WEBFLOW_API_TOKEN} ← site-level token only
Then: POST .../items/publish (item-level, pushes to staging)
Then: POST https://api.webflow.com/v2/sites/{site_id}/publish (full site, pushes to custom domain)
fieldData uses field slugs as keys (NOT field IDs)
hero-image format: {"url": "https://imagedelivery.net/..."}
narrative-body format: "<p>paragraph</p><p>paragraph</p>"
affiliate-url: direct Realtor.com listing href from search result

**Full site publish (required after each pipeline run):**
POST /v2/sites/6a650a7eb2639262c4b6adb7/publish
body: {"customDomains": ["6a661987994ab168be06566b", "6a661986994ab168be065664"]}

---

### CLOUDFLARE
**DNS:** housesunder150k.com
**Images:** $5/mo Starter Bundle — ACTIVE
**Account ID:** af60f586464675e914119c0743898631
**Account hash:** VbqNe4WDJ-oPFPFAkDRv_w
**Delivery URL:** https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w/{image_id}/public
**API:** POST https://api.cloudflare.com/client/v4/accounts/{id}/images/v1
**Auth:** Bearer token in Railway as CLOUDFLARE_API_TOKEN

---

### REALTYAPI
**URL:** realtyapi.io
**Active endpoint:** `https://realtor.realtyapi.io` (Realtor.com)
**Plan:** PRO — $20/mo, 20,000 requests/month
**Railway env var:** REALTYAPI_KEY
**MCP:** https://mcp.realtyapi.io/mcp

**Search params (confirmed working):**
```
GET /search/bylocation
location: "Kentucky" (state name)
priceRange: "max:150000"
searchType: "For_Sale"
propertyType: "House,Townhome"
sortOrder: "Newest"
hasPhotos: true
seniorCommunity: false
resultCount: 50
```
Response: `searchResults[]`

**Detail params:**
```
GET /details/byid?property_id=X
```
Response root: `detail` — description at `detail.details.text`, year_built at `detail.details.year_built`

**Coverage:** 1,969+ results per state. All states return 50 results.

---

### ANTHROPIC API (Claude)
**Model:** claude-sonnet-4-6
**Max tokens:** 1000 per call
**Endpoint:** https://api.anthropic.com/v1/messages

**Call 1 — Scoring:** ~$0.005/call
**Call 2 — Content Gen (score ≥ 6 only):** ~$0.010/call
**Score threshold:** ≤ 5 discard, ≥ 6 publish

**Content parser fix (Session 6):** strips `**bold**`, `#` hashes, and `---` separators from label lines before matching — fixes Claude occasionally wrapping labels in markdown formatting.

**Scoring key rules:**
- Manufactured/mobile/modular: -3
- Condo in multi-family: -2 (ignore acreage — it's the complex parcel)
- Cash-only/as-is AND no floor qualifier: -2
- Audience check: regular person with mortgage must be able to buy and live here — if no, max score = 4
- As-is is fine if property has historic significance, acreage, waterfront, or architectural value

---

### RAILWAY
**Project ID:** 586f6dd5-1930-4301-8262-d5562a3119e7
**Service ID:** 15ca3583-43d1-4823-bf3d-5740976e439c
**Environment ID:** b1c99e6e-a528-42e0-b8f0-503860d53355
**Plan:** Hobby — $5/mo flat
**Cron:** `0 13,17,21,1,5,9 * * *` = 6 runs/day, 4-hour intervals, CT
**GitHub:** auto-deploys on push to main

**CRITICAL — cron overlap warning:**
Railway does not skip overlapping cron runs. If a run is in progress when the next cron fires, two containers run simultaneously causing race conditions, duplicate writes, and empty Webflow items. Never use `*/5` cron for testing. Use Railway MCP redeploy for manual triggers. Always wait for `=== Pipeline complete ===` before redeploying.

**Env vars (11):**
ANTHROPIC_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN,
DAILY_PUBLISH_LIMIT (=10), REALTYAPI_KEY, REPLIERS_API_KEY (remove — unused),
SOVRN_AFFILIATE_URL, SUPABASE_KEY, SUPABASE_URL, WEBFLOW_API_TOKEN, WEBFLOW_COLLECTION_ID

---

### SUPABASE
**Project ID:** krzpkaxvbmpdeluqzkka
**URL:** https://krzpkaxvbmpdeluqzkka.supabase.co
**Plan:** Free tier

**Tables:**
- published_listings: slug, mls_number, webflow_item_id, score, tier, category, headline, hero_image_url, published_at, published_date_ct
- seen_listings: mls_number, slug, score, tier, last_seen_at, times_seen
- pipeline_runs: started_at, completed_at, listings_fetched, published, errors, est_cost_usd, daily_limit_hit

**Daily limit:** CT calendar day, resets at CT midnight
**Seen suppression:** 7 days
**mls_number for Realtor.com listings:** stored as property_id

---

### GITHUB
**Repo:** github.com/housesunder150k/housesunder150k
**Local:** C:\Users\jerem\OneDrive\Desktop\Houses Under 150K
**Script:** scripts/ingest.py

---

### SOVRN / REALTOR.COM
**Commission:** $5/lead, 30-day cookie
**Account:** housesunder150k@gmail.com — approval pending
**Current affiliate-url:** direct Realtor.com property href from API response
**At approval:** update pipeline to wrap Realtor.com URL in Sovrn redirect format

---

## Pipeline Flow (ingest.py — current)

```
1. Insert pipeline_runs row
2. Check CT daily count → if ≥ DAILY_PUBLISH_LIMIT: exit
3. fetch_listings():
   - Shuffle US_STATES (24 states)
   - For each state: GET /search/bylocation (50 results)
   - For each result: GET /details/byid (description + year_built)
   - normalize_listing() → standard dict
   - 1 listing collected per state (state_published flag) for geographic diversity
   - Target: 50 total listings
4. For each listing:
   - Check published_listings slug dedup
   - Check seen_listings 7-day MLS suppression
   - score_listing() → upsert seen_listings
   - If score ≤ 5: skip
   - If HEADLINE or NARRATIVE empty after content gen: skip (no empty Webflow writes)
   - generate_content()
   - upload_image() → Cloudflare
   - write_webflow() + publish_webflow() (item-level)
   - db_insert_published()
   - Check daily limit → break if hit
5. Update pipeline_runs row
6. If published_this_run > 0: publish_site() (full site to custom domain)
```

**Affiliate URL:** uses `listing.get("listingHref")` from search result `href` field — direct Realtor.com property page

---

## Scoring Prompt — Key Rules

**AUTOMATIC 6+ FLOOR (any one qualifies):**
Waterfront, lake/river/ocean view, acreage ≥ 0.5 acres, in-ground pool, wooded lot, new construction (≤ 2 years), historic pre-1950 with character details

**NEGATIVE MODIFIERS:**
- Manufactured/mobile/modular: -3
- Condo/multi-family complex: -2 (lot size = complex parcel, ignore acreage)
- Cash-only/as-is AND no floor qualifier: -2
- Needs major work, no renovation history: -1
- No photos: -1
- Under 700 sqft: -1

**AUDIENCE CHECK:** Can a regular person with a mortgage buy and live here? If no, max score = 4.
**AS-IS EXCEPTION:** As-is is fine if property has historic significance, acreage, waterfront, or architectural value.

**SCORE BANDS:** 1-3 skip | 4-5 below threshold | 6 publish | 7-8 featured | 9-10 hero

---

## Manual Entry Process (Deal of the Day)

To manually add a listing:
1. Get Realtor.com property URL → extract property_id from URL (`_M{digits}` → strip hyphens)
2. Call RealtyAPI `/details/byid?property_id=X` for full data
3. Upload hero photo to Cloudflare Images, get delivery URL
4. Call Webflow CMS create_collection_items with all fields, `deal-of-the-day: true`
5. Publish item, then publish site
6. Insert into Supabase published_listings manually
7. Update Deal of the Day section on homepage with static content (until CMS binding is wired)

---

## Homepage Structure

```
Nav: Logo | Search by State | Deal of the Day | About | [Subscribe button]
Hero: headline + subtext + "See Today's Deals →" button (links to /deal-of-the-day)
Deal of the Day section: ⭐ DEAL OF THE DAY label | image | location/title/summary/price/CTA
  - Currently static (Wheeling WV) — needs CMS binding next session
Latest Deals grid: collection list, filtered to deal-of-the-day=false, limit 12
Subscribe section
Footer
```

---

## Design System

**Colors:**
  Background #0D0D0D / Surface #111111 / Surface2 #1A1A1A / Border #2A2A2A
  Text Primary #F5F5F5 / Body #CCCCCC / Muted #999999
  Accent Cyan #00D4FF / CTA BG #00D4FF / CTA Text #0D0D0D

**Typography:**
  Body/UI: Inter sans-serif
  Price: Space Mono monospace
  Headline: System serif — DO NOT CHANGE

**Style prefixes:** hu150-* (homepage) / lp-* (listing template) / hu150-dod-* (Deal of the Day section)

---

## Monthly Cost Stack

| Service | Cost |
|---|---|
| RealtyAPI PRO | $20/mo |
| Claude API | ~$25-38/mo |
| Railway | $5/mo |
| Cloudflare Images | $5/mo |
| Webflow | $25/mo |
| Domain | ~$1/mo |
| **Total** | **~$56-74/mo** |

Break-even: ~12-15 Sovrn leads/month at $5/lead

---

## Key Decisions (Sessions 1-6)

1-47: [See previous session reports]
48. RealtyAPI selected — Realtor.com endpoint, full nationwide coverage
49. Redfin endpoint abandoned — thin rural coverage
50. Realtor.com `searchResults` key confirmed (not `data.results`)
51. Description at `detail.details.text` in detail response
52. Year built at `detail.details.year_built`
53. Affiliate URL = direct `href` from search result (not constructed zip search)
54. 1 listing per state per run — geographic diversity
55. Daily publish limit = 10, 6 runs/day (4-hour intervals)
56. Content parser: strips `**`, `#`, `---` before label matching — fixes markdown formatting edge case
57. Empty content guard: skip Webflow write if HEADLINE or NARRATIVE empty
58. Full site publish via API after each run (domain IDs hardcoded in publish_site())
59. Cron overlap is dangerous — never use */5 in production, use Railway MCP redeploy for testing
60. gallery-images MultiImage field added to CMS — needs template wiring
61. Latest Deals grid filtered: deal-of-the-day=isOff
62. Deal of the Day homepage section built — static for now, CMS binding next session
63. Manual listing entry process established — via Claude + MCP connectors directly
64. Pending listings (is_pending=true) should be skipped in ingest — not yet implemented
65. Maintenance job needed: daily poll published listings for sold/pending status

---

## Session 7 Start Prompt

"Read the primer at houses-under-150k/vault/primer/_primer.md before doing anything else. This is Session 7. Pipeline is live, 7 real listings on site, Deal of the Day section working on homepage. Commit all local ingest.py changes before starting. Then: (1) Build Deal of the Day page at /deal-of-the-day, (2) Wire gallery-images MultiImage field on listing template in Designer, (3) Fix hero image stretching on listing detail page, (4) Add is_pending check to ingest pipeline, (5) Add gallery images to Wheeling WV listing. Check Supabase and Railway logs before touching anything."
