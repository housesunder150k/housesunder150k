# HousesUnder150K.com — Build Status
*Last updated: July 26, 2026 — Session 4 complete (pipeline live, test data running)*

---

## Project Overview

**Domain:** housesunder150k.com — LIVE
**Platform:** Webflow Premium ($25/mo billed yearly — $300/yr paid 2026-07-26)
**GitHub:** github.com/housesunder150k/housesunder150k
**Webflow Site ID:** `6a650a7eb2639262c4b6adb7`
**Webflow Designer:** https://housesunder150k.design.webflow.com

---

## Infrastructure

### Webflow
- **Plan:** Premium — custom domains, 50GB bandwidth, CMS
- **Subdomain:** housesunder150k.webflow.io (staging)
- **Custom domain:** housesunder150k.com (live)
- **SSL:** Active on www.housesunder150k.com, active on housesunder150k.com
- **API token:** Site-level token (Site Settings → Integrations → API Access) — scopes: CMS read/write + Sites read/write

### Cloudflare DNS (housesunder150k.com)
| Type | Name | Value | Proxy |
|---|---|---|---|
| A | @ | 198.202.211.1 | DNS only |
| CNAME | www | cdn.webflow.com | DNS only |
| TXT | _webflow | one-time-verification=da944f51-6e25-4bde-afa4-81d1dae93c9c | DNS only |

### Cloudflare Images
- **Plan:** Starter Bundle — $5/mo — ACTIVE
- **Account ID:** af60f586464675e914119c0743898631
- **Account hash:** VbqNe4WDJ-oPFPFAkDRv_w
- **Image Delivery URL:** https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w/{image_id}/public
- **API upload endpoint:** POST https://api.cloudflare.com/client/v4/accounts/af60f586464675e914119c0743898631/images/v1
- **Auth:** Bearer token — stored in Railway as CLOUDFLARE_API_TOKEN
- **Capacity:** 100,000 images stored / 500,000 delivered per month

### Railway
- **Project:** housesunder150k (ID: 586f6dd5-1930-4301-8262-d5562a3119e7)
- **Plan:** Hobby — $5/mo
- **Deploy:** Auto-deploys from github.com/housesunder150k/housesunder150k on push to main
- **Cron — main pipeline:** `0 8,13,18 * * *` — 8am, 1pm, 6pm CT — NOT YET CONFIGURED in dashboard
- **Cron — sold check:** `0 9 * * *` — 9am CT daily (future — Session 5)
- **All env vars set:** ANTHROPIC_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, REPLIERS_API_KEY, SOVRN_AFFILIATE_URL, WEBFLOW_API_TOKEN, WEBFLOW_COLLECTION_ID

### Sovrn (Affiliate)
- **Program:** Realtor.com via Sovrn (moved from Commission Junction)
- **Commission:** $5/lead, 30-day cookie
- **Account:** housesunder150k@gmail.com — under review (triggered by first click on site)
- **Test link:** https://sovrn.co/1qedjsn — live on Milwaukee listing
- **Tracking:** One URL for all listings — Sovrn auto-tracks per click, no per-listing URL needed
- **Current affiliate-url field:** Realtor.com address search URL constructed per listing (see Pipeline notes)

---

## Page IDs

| Page | Slug | ID |
|---|---|---|
| Homepage | / | 6a650a80b2639262c4b6adba |
| Listing Template | /listings/[slug] | 6a650bab14666c3157f2761e |
| Deal of the Day | /deal-of-the-day | 6a6612c009d35063c09f9ac3 |
| About | /about | 6a6612c0d157d1643e103769 |
| States Index | /states | 6a6612c171f470cf8a437d71 |

---

## CMS Collection — Listings
**Collection ID:** `6a650bab14666c3157f27618`

| Field | Type | Slug | Field ID |
|---|---|---|---|
| Name | PlainText | `name` | `2d0b39c8706c5aeb8a5d10eb7c7b0ba5` |
| Slug | PlainText | `slug` | `3eff577466e8ac4d1f5673c6ba5067f0` |
| Price | Number | `price` | `e3e0fbae7e82729a2d40cfd88b8553ad` |
| Price Display | PlainText | `price-display` | `f1701f816e4213ef8979d44f2a9f4ec4` |
| Location Display | PlainText | `location-display` | `dcbe16cd4151eaab2df0d79d0343ad5e` |
| Address | PlainText | `address` | `2370642ad45dce9c5cbbf8d6122515dc` |
| City | PlainText | `city` | `ab84ae63bb81f7bfe33ccb50cfe9bc25` |
| State | PlainText | `state` | `59074a866f1a7d4bffb208b1a63cd827` |
| Year Built | Number | `year-built` | `e16726678f8f43f844c78f4fd226e47c` |
| Bedrooms | Number | `bedrooms` | `72df5c8c23726e9849fa1520abe59b11` |
| Bathrooms | Number | `bathrooms` | `ad78567827bc5cc5dbcdbf93379f2c06` |
| Square Feet | Number | `square-feet` | `326895e4a7b08fc72b760740045e9e8d` |
| Hero Image | Image | `hero-image` | `c2021ed9588e45e46c85ff883a558c02` |
| Narrative Body | RichText | `narrative-body` | `fbfb92acd8aeee91d64209f2e905fc5a` |
| Short Summary | PlainText | `short-summary` | `aec9319d65a89b54b50001e13af0b8c7` |
| Listing URL | Link | `listing-url` | `4d428fda04c2feb9db89ef1423343895` |
| Affiliate URL | Link | `affiliate-url` | `2b37c2a126d49592bd34aa91ed798c26` |
| Social Caption | PlainText | `social-caption` | `68cdd4fdfa9a3a1ce86836aaa3617950` |
| Status | Option | `status` | `6b58bbdff6c0c0e31e17c04e4188f8be` |
| Deal of the Day | Switch | `deal-of-the-day` | `3e20ffd4c8781f4b215bf2aa02b01542` |

**Status Option IDs:**
- Active: `3b41185e9af84f92d8da092965308a2d`
- Pending: `001257c77d3ccd4477d620ac135a4afd`
- Sold: `541de6b6934cd79d6a76c98d91610063`
- Expired: `e630110b6993074e3f7299e8dbb7fdc1`

---

## Pipeline — scripts/ingest.py

**Location in repo:** `/scripts/ingest.py`
**Dependencies:** `requirements.txt` (requests==2.31.0, anthropic==0.20.0)
**Railway config:** `Procfile` — `worker: python scripts/ingest.py`

**Pipeline flow:**
1. `fetch_listings()` — GET Repliers /listings?status=A&maxPrice=150000
2. For each listing: dedup check via posts/[slug].json
3. `score_listing()` — Claude Call 1 (SCORING_PROMPT embedded in script, trimmed to ~650 tokens)
4. Score ≤ 5: discard. Score ≥ 6: continue.
5. `generate_content()` — Claude Call 2 (CONTENT_PROMPT_TEMPLATE embedded in script)
6. `upload_image()` — fetch images[0] from Repliers CDN (https://cdn.repliers.io/), upload to Cloudflare Images
7. `write_webflow()` — POST /v2/collections/{id}/items with fieldData
8. `publish_webflow()` — POST .../items/publish
9. `write_post_record()` — write posts/[slug].json for dedup
10. Token usage logged after every Claude call: input, output, est_cost

**Webflow fieldData key:** field slugs (e.g. "price-display"), NOT field IDs
**hero-image format:** `{"url": "https://imagedelivery.net/..."}`
**narrative-body format:** HTML string `<p>paragraph</p><p>paragraph</p>`
**status value:** option ID string `3b41185e9af84f92d8da092965308a2d` (Active)
**affiliate-url:** Realtor.com address search URL — `make_realtor_url(addr)` constructs from streetNumber + streetName + streetSuffix + city + state + zip

**Slug format:** `{city-slug}-{price}` e.g. `milwaukee-105000`
**Dedup:** posts/[slug].json exists = skip — WARNING: resets on Railway deploy (see Known Issues)
**Score threshold:** discard ≤ 5, publish ≥ 6

**Token costs (confirmed Session 4):**
- Scoring call: ~1,000–1,200 input | ~100–160 output | ~$0.0045–0.006 per call (after prompt trim)
- Content gen call: ~970–1,130 input | ~410–480 output | ~$0.009–0.011 per call
- Estimated steady state: ~$15–18/month at 3 runs/day, 50 listings/run

**Repliers image field:** `images[]` — relative paths, prepend `https://cdn.repliers.io/` to get full URL

---

## Token Cost History
| Session | Scoring input tokens | Cost/call | Notes |
|---|---|---|---|
| Session 4 initial | ~2,100–2,300 | ~$0.009 | Original long prompt |
| Session 4 trimmed | ~1,000–1,200 | ~$0.005 | Prompt trimmed ~65% |

---

## Live Listings (as of Session 4 end)

Pipeline has published test data listings. All will be replaced when live Repliers key is activated in Session 5.

| Slug | Title | Status |
|---|---|---|
| `brand-new-construction-milwaukee-105000` | Brand-New Construction in Milwaukee for $105,000 | Active / Published (manual) |
| `tulalip-70000` | Puget Sound Waterfront Cabin. 1940. $70,000. | Active / Published (with image) |
| `mound-city-135000` | 1900 Kansas Farmhouse. New Shell. You Finish the Inside. $135K. | Active / Published |
| `kansas-city-135000` | 1904 Kansas City Stone House. All New Systems. $135K. | Active / Published |
| `kansas-city-150000` | 2,208 Square Feet in Kansas City. Two Fireplaces. $150K. | Active / Published |
| `longton-20000` | 1870 Kansas Church. Stained Glass Intact. $20,000. | Active / Published |

---

## Build State

### ✅ Complete

**Site & Domain**
- housesunder150k.com live with SSL
- Webflow Premium active
- Cloudflare DNS configured (A + CNAME + TXT)
- Cloudflare Images active ($5/mo Starter)

**Pages**
- Homepage — nav, hero, CMS listing grid, subscribe section, footer
- Listing Template — hero image, price overlay, meta bar, specs, H1, narrative, CTA block — all CMS-bound
- Deal of the Day — CMS collection filtered to deal-of-the-day=isOn, limit 1, mirrors listing template
- About — static brand story, subscribe CTA
- States Index — all 50 states linked to /states/[slug]

**CMS**
- 21-field Listings collection, all fields confirmed and documented
- deal-of-the-day Switch field added (Session 2)
- Milwaukee listing published and live

**Pipeline (Session 4)**
- scripts/ingest.py — full pipeline deployed and running on Railway
- All 5 API integrations confirmed working: Repliers → Claude → Cloudflare Images → Webflow write → Webflow publish
- Images flowing: Repliers CDN → Cloudflare Images → Webflow hero-image field → site
- Token logging confirmed working
- Scoring prompt trimmed ~65% — cost reduced from ~$0.009 to ~$0.005 per scoring call
- Narrative CTA line removed — no duplicate affiliate link in narrative body
- affiliate-url field: per-listing Realtor.com address search URL (see Known Issues for test data caveat)
- Webflow site-level API token confirmed working with cms:write + sites:read/write scopes

### ⬜ Not Yet Done

- **Railway cron** — `0 8,13,18 * * *` not yet configured in Railway dashboard — pipeline only runs on deploy trigger currently
- **Persistent dedup** — posts/[slug].json resets on every Railway deploy — needs Supabase table (Session 5)
- **Live Repliers key** — still on test key with sample data (Session 5)
- **Realtor.com affiliate URL** — address-based URL construction works in code but test data has incomplete address fields (streetNumber/streetName missing in some sample records) — verify with live MLS data in Session 5
- **Sovrn real tracking URL** — pending approval, swap test link when approved
- State template pages `/states/[state]` — all /states/[state] links 404 until built
- Sold listing page state on listing template
- Sold check pipeline (Session 5)
- Social — Facebook page + posting tool (Session 6)
- Beehiiv email (Session 6)

---

## Session 5 Checklist

- [ ] Fix persistent dedup — add Supabase table, replace posts/[slug].json filesystem check
- [ ] Configure Railway cron — `0 8,13,18 * * *` in dashboard
- [ ] Swap REPLIERS_API_KEY from test key to live MLS key
- [ ] Watch first real listings run — confirm scoring quality and publish rate
- [ ] Verify Realtor.com address URL construction with real Repliers address data (streetNumber, streetName, streetSuffix, zip all populated)
- [ ] Tune scoring threshold if publish volume too high or too low
- [ ] Swap SOVRN_AFFILIATE_URL to real tracking URL if approved
- [ ] Clear test data listings from Webflow CMS before going live

---

## Known Issues & Notes

- **Dedup resets on deploy** — posts/[slug].json lives in Railway container filesystem. Every new deploy loses the dedup history. Fix: move to Supabase table. Until then, re-deploys will re-publish already-seen listings.
- **Realtor.com URL on test data** — `make_realtor_url()` constructs `https://www.realtor.com/realestateandhomes-search/{street}_{city}_{state}_{zip}` but Repliers sample data has incomplete address fields (some records missing streetNumber/streetName), so fallback produces zip-only URL. Function is correct — verify with live data in Session 5.
- **Webflow MCP publish** — MCP publish only reaches Webflow subdomain. Use Designer Publish button to push to housesunder150k.com after bulk changes.
- **Webflow workspace token** — does NOT have cms:write scope. Must use site-level token (Site Settings → Integrations → API Access).
- `hu150-card-price-1` — legacy duplicate style in stylesheet, not applied anywhere, safe to delete
- State template pages not built — all /states/[state] links 404 until built
- Site head has custom CSS block (set_site_freeform_code) — handles visited link color fix and card color overrides

---

## Design System

### Colors
```
Background:     #0D0D0D
Surface:        #111111  (nav, CTA block)
Surface 2:      #1A1A1A  (cards)
Border:         #2A2A2A
Text Primary:   #F5F5F5
Text Body:      #CCCCCC
Text Muted:     #999999
Text Faint:     #666666
Text Disabled:  #555555
Accent Cyan:    #00D4FF
CTA Background: #00D4FF
CTA Text:       #0D0D0D
```

### Typography
```
Body / UI:    Inter, sans-serif
Price:        Space Mono, monospace
Headline:     System serif (homepage hero — do not change)
```

### Style Class Prefixes
```
hu150-*   Homepage
lp-*      Listing template
about-*   About page
states-*  States index page
dod-*     Deal of the Day page
```

### Key Homepage Styles (`hu150-*`)
```
hu150-card              LinkBlock — dark card, set to "Current listing"
hu150-card-img          220px, object-fit cover, #2A2A2A bg
hu150-card-price        Flex row, Space Mono, cyan — wraps $ + number
hu150-card-price-dollar Static "$" — 16px Space Mono cyan
hu150-card-price-number CMS-bound price-display — 22px Space Mono cyan
hu150-card-body         Padding 20px
hu150-card-location     CMS-bound location-display — 13px cyan uppercase
hu150-card-summary      CMS-bound short-summary — 14px #BBBBBB
hu150-card-cta          "View Listing →" — 13px cyan
hu150-nav-link-dod      Combo on hu150-nav-link — color: #00D4FF (DoD tab accent)
```

## Card Style Spec (confirmed live)
```
hu150-card-price-dollar   22px Space Mono #00D4FF
hu150-card-price-number   22px Space Mono #F5F5F5
hu150-card-location       15px uppercase #00D4FF
hu150-card-summary        16px #CCCCCC
hu150-card-cta            15px #00D4FF (View Listing →)
```
