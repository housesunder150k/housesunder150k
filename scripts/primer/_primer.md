---
project: HousesUnder150K
entity: HousesUnder150K.com — housesunder150k@gmail.com
updated: 2026-07-26 — Session 4 complete
phase: Pipeline live on Railway — 7 test listings on site — awaiting Session 5
next_action: Session 5 — persistent dedup (Supabase), clear test data, subscribe Repliers live key, first real run
session_objective: cleared
---

## What This Project Is

HousesUnder150K.com is POC Site 1 of a planned 10-site media holding company built on automated content pipelines. Real estate content platform surfacing listings under $150K, scoring them editorially, generating AI narrative in the voice of Michelle Bowers (theoldhouselife.com), publishing to website and social, monetizing via display ads, affiliate links, and email subscriptions.

**The only metric that matters right now: $1,000/month within 90 days of launch.**

---

## Current Build State

### Done
- Homepage — nav, hero, CMS collection list (Active, responsive grid), subscribe, footer
- Listing template — fully native Webflow, all CMS fields bound, price display, mobile responsive
- Homepage card — price displays as $105,000 below image, card link wired to Current listing (permanent, all future items inherit)
- CMS schema — 21 fields including Status, Price Display/Location Display, Deal of the Day switch
- Deal of the Day — nav tab (cyan), CMS Switch field, /deal-of-the-day page (CMS-bound, mirrors listing template)
- About page — /about, static, brand story + subscribe CTA
- States index — /states, all 50 states linked to /states/[slug]
- First real listing — Milwaukee $105K, published and live at /listings/brand-new-construction-milwaukee-105000
- Pipeline architecture — two-prompt system, scoring tiers, content prompts documented
- GitHub repo — connected, VS Code configured at C:\Users\jerem\OneDrive\Desktop\Houses Under 150K
- Webflow Premium — paid ($300/yr)
- Domain — housesunder150k.com live, DNS on Cloudflare (A + CNAME + TXT), SSL active
- Repliers account created — Test API Key in hand (Sample Data MLS, SAMPLE-DATA, #110, VOW)
- Cloudflare Images — active ($5/mo Starter), pipeline uploading and serving images
- **scripts/ingest.py — written, deployed, running on Railway**
- **All 5 API integrations confirmed working: Repliers → Claude → Cloudflare → Webflow write → publish**
- **Railway cron set: `0 13,18,23 * * *` (8am/1pm/6pm CT) — activates on next deploy**
- **7 test listings live on housesunder150k.com with images**
- Sovrn affiliate — test link live on Milwaukee listing, approval in progress

### Not Done
- **Persistent dedup** — posts/[slug].json resets on Railway deploy — Supabase fix needed (Session 5 #1)
- **Live Repliers key** — still on test/sample data (Session 5)
- State template pages /states/[state] — state index links 404 until built
- Sold listing page state on template
- Sold check pipeline
- Social (Facebook), Beehiiv email (Session 6)

---

## Session Protocol

### Session Start
1. Read this primer
2. Read vault/status/build_status.md — field IDs, style classes, element IDs
3. Confirm Webflow MCP connected in Claude Desktop
4. Confirm Railway MCP connected
5. Never assume element IDs, field IDs, or option IDs from memory — check build_status.md

### Session End
1. Update vault/status/build_status.md
2. Update this primer — phase, next_action, new decisions
3. Write session report to vault/sessions/YYYY-MM-DD_[description].md
4. git add . && git commit -m "session: [desc]" && git push origin main

---

## Stack — Full Reference

---

### WEBFLOW
**Role:** Website platform. Hosts all pages, CMS, published content. Serves HTML/CSS/JS. Images served externally via Cloudflare Images. CMS Collection pages auto-render listing template for every item. Pipeline writes to Webflow CMS via API — Webflow is the publishing endpoint.

**Account:** housesunder150k@gmail.com
**Plan:** Premium $25/mo billed yearly — $300/yr paid 2026-07-26
**Site ID:** 6a650a7eb2639262c4b6adb7
**Designer:** https://housesunder150k.design.webflow.com
**MCP link:** https://housesunder150k.design.webflow.com?app=dc8209c65e3ec02254d15275ca056539c89f6d15741893a0adf29ad6f381eb99

**API Token:** Site-level token (Site Settings → Integrations → API Access) — NOT workspace token
  Required scopes: CMS read/write + Sites read/write
  WARNING: Workspace tokens do NOT have cms:write scope regardless of plan — always use site token

**Page IDs:**
- Homepage: 6a650a80b2639262c4b6adba
- Listing Template: 6a650bab14666c3157f2761e
- Deal of the Day: 6a6612c009d35063c09f9ac3
- About: 6a6612c0d157d1643e103769
- States Index: 6a6612c171f470cf8a437d71

**CMS Collection Listings:** 6a650bab14666c3157f27618

**CMS Field IDs:**
name            2d0b39c8706c5aeb8a5d10eb7c7b0ba5
slug            3eff577466e8ac4d1f5673c6ba5067f0
price           e3e0fbae7e82729a2d40cfd88b8553ad
price-display   f1701f816e4213ef8979d44f2a9f4ec4
location-display dcbe16cd4151eaab2df0d79d0343ad5e
address         2370642ad45dce9c5cbbf8d6122515dc
city            ab84ae63bb81f7bfe33ccb50cfe9bc25
state           59074a866f1a7d4bffb208b1a63cd827
year-built      e16726678f8f43f844c78f4fd226e47c
bedrooms        72df5c8c23726e9849fa1520abe59b11
bathrooms       ad78567827bc5cc5dbcdbf93379f2c06
square-feet     326895e4a7b08fc72b760740045e9e8d
hero-image      c2021ed9588e45e46c85ff883a558c02
narrative-body  fbfb92acd8aeee91d64209f2e905fc5a
short-summary   aec9319d65a89b54b50001e13af0b8c7
listing-url     4d428fda04c2feb9db89ef1423343895
affiliate-url   2b37c2a126d49592bd34aa91ed798c26
social-caption  68cdd4fdfa9a3a1ce86836aaa3617950
status          6b58bbdff6c0c0e31e17c04e4188f8be
deal-of-the-day 3e20ffd4c8781f4b215bf2aa02b01542

**Status Option IDs:**
Active:   3b41185e9af84f92d8da092965308a2d
Pending:  001257c77d3ccd4477d620ac135a4afd
Sold:     541de6b6934cd79d6a76c98d91610063
Expired:  e630110b6993074e3f7299e8dbb7fdc1

**MCP v2.0 Rules:**
- Bridge NOT required for most operations
- Bridge still needed for: snapshots, canvas navigation, image-from-URL upload
- CMS text binding key: text (NOT textContent)
- Image binding key: assetId — Link: link — RichText: richText
- Always create elements first, bind in SECOND PASS — inline bindings fail
- CMSCollection auto-creates DynamoWrapper > DynamoList > DynamoItem
- Cannot use CMSCollectionList or CMSCollectionItem as child types in element builder
- Option field filter operators: equals / doesNotEqual / isSet / isNotSet
- Switch field filter operators: isOn / isOff (NOT isSet — confirmed from API)
- Sort direction: ascending / descending (not asc/desc)
- New CMS fields show null in designer preview until tab refresh — data IS correct

**Pipeline writes via:**
POST https://api.webflow.com/v2/collections/{collection_id}/items
Authorization: Bearer {WEBFLOW_API_TOKEN}  ← must be site-level token
Then publish: POST .../items/publish

**fieldData uses field slugs as keys** (e.g. "price-display") NOT field IDs
**hero-image format:** {"url": "https://imagedelivery.net/..."}
**narrative-body format:** HTML string "<p>paragraph</p><p>paragraph</p>"
**status value:** option ID string "3b41185e9af84f92d8da092965308a2d" (Active)

**Bandwidth:** 50GB Premium. Images from Cloudflare CDN not Webflow. Effective ~15-20GB/mo at 180K visits.

---

### CLOUDFLARE
**Role — DNS:** housesunder150k.com registered and managed on Cloudflare. DNS live and connected to Webflow.
  A record:    @ → 198.202.211.1 (DNS only)
  CNAME:       www → cdn.webflow.com (DNS only)
  TXT:         _webflow → one-time-verification=da944f51-6e25-4bde-afa4-81d1dae93c9c

**Role — Images:** Cloudflare Images ($5/mo) hosts all hero photos permanently. MLS photo URLs die when listings sell. Cloudflare URLs are permanent. Pipeline uploads on ingestion, stores Cloudflare URL in CMS hero-image field.

**Account:** housesunder150k@gmail.com
**Domain:** housesunder150k.com ~$10/yr
**Cloudflare Images:** $5/mo Starter Bundle — ACTIVE — 100,000 images / 500,000 delivered per month

**Cloudflare Images credentials:**
**Account ID:**     af60f586464675e914119c0743898631
**Account hash:**   VbqNe4WDJ-oPFPFAkDRv_w
**Image Delivery URL:** https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w/{image_id}/public
**API token:** stored in Railway as CLOUDFLARE_API_TOKEN

**Pipeline image logic:**
  if hero_image_url contains "imagedelivery.net": skip (already on Cloudflare)
  elif image_url doesn't start with "http": prepend https://cdn.repliers.io/
  then: fetch from URL > upload to Cloudflare API > store returned URL in CMS

**Repliers image field:** images[] — test data returns relative paths (e.g. sample/IMG-xxx.jpg)
  Live MLS data returns full CDN URLs — prepend logic handles both cases

**Cloudflare Images API:** POST https://api.cloudflare.com/client/v4/accounts/{id}/images/v1
Upload multipart/form-data. Returns result.variants[0] as permanent URL.

**Why keep Cloudflare even though Repliers Standard includes CDN:**
- Permanent URLs independent of Repliers — images survive if listing is removed from MLS
- No dependency on Repliers CDN uptime
- Consistent imagedelivery.net URL format across all listings
- $5/month is worth the insurance

---

### REPLIERS (Listing API)
**Role:** Primary listing data source. Real-time MLS. Returns specs, photos, agent descriptions, status. Pipeline fetches 3x/day filtered price <= $150K and status = active.

**Account:** housesunder150k@gmail.com
**API Key type:** Test API Key — Sample Data MLS (SAMPLE-DATA, #110, VOW tier)
**Auth header:** REPLIERS-API-KEY (NOT Authorization Bearer)
**Base URL:** https://api.repliers.io
**Repliers CDN:** https://cdn.repliers.io (prepend to relative image paths)
**Cost:** $199/mo Standard (monthly, no annual discount worth taking) — subscribe in Session 5

**Pricing research (Session 4):** $199/mo Repliers Standard is the correct and only practical option for nationwide US MLS data without a real estate license. SimplyRETS requires existing MLS credentials. RealEstateAPI.com is property records, not live listings. No cheaper alternative exists.

**What the test key gives you:**
- Sample/synthetic listing data — fixed pool, stale, same 50 listings every run
- Text fields scrambled, "Sample Data" watermarks on images
- Full API response shape confirmed correct
- DO NOT subscribe to live key until dedup fix (Supabase) is in place

**CONFIRMED field mappings:**
  listPrice                    > price (string "5961.00" — parse to float then int)
  address.streetNumber +
  address.streetName +
  address.streetSuffix         > address (concatenate)
  address.city                 > city
  address.state                > state abbreviation (Repliers returns full name — use lookup table)
                                 location-display = "City, FullStateName"
  address.zip                  > used in make_realtor_url()
  details.numBedrooms          > bedrooms (integer)
  details.numBathrooms         > bathrooms (integer)
  details.sqft                 > square-feet (string range "1000-1100" — parse to midpoint int)
  details.yearBuilt            > year-built (string — parse to integer)
  images[]                     > hero-image source (relative paths — prepend cdn.repliers.io)
  details.description          > agent description for both prompts
  details.propertyType         > scoring input
  details.style                > scoring input
  details.exteriorConstruction1> scoring input
  details.swimmingPool         > scoring input (Y/N)
  details.waterfront           > scoring input (Y/N)
  lot.acres                    > scoring input
  nearby.amenities[]           > scoring context
  mlsNumber                    > internal reference
  status                       > "A" = active, "U" = unavailable
  daysOnMarket                 > scoring signal
  lastStatus                   > "New" = just listed, "Pc" = price cut
  lastPriceChangeType          > "decrease" = price reduction

**Pipeline query:**
  GET https://api.repliers.io/listings
    ?status=A&maxPrice=150000&resultsPerPage=50&sortBy=updatedOnDesc

**Sold check query (future):**
  GET https://api.repliers.io/listings?mlsNumber=[id]&status=U

---

### ANTHROPIC API (Claude)
**Role:** Powers the two-call pipeline. Call 1 scores and routes. Call 2 generates all content.

**Model:** claude-sonnet-4-6
**Max tokens:** 1000 per call
**Endpoint:** https://api.anthropic.com/v1/messages
**Auth:** x-api-key header (not Authorization Bearer)

**Call 1 — Scoring (every listing):**
  Prompt: SCORING_PROMPT embedded in scripts/ingest.py (trimmed to ~650 tokens)
  Input: ~400-500 tokens of listing data
  Total input: ~1,000-1,200 tokens
  Output: ~100-160 tokens
  Cost: ~$0.005/call
  Output: SCORE, TIER, CATEGORY, KEY_HOOKS, REASON, DEAL_OF_DAY_CANDIDATE

**Call 2 — Content Generation (score 6+ only):**
  Prompt: CONTENT_PROMPT_TEMPLATE embedded in scripts/ingest.py
  Input: ~970-1,130 tokens
  Output: ~410-480 tokens
  Cost: ~$0.010/call
  Output: HEADLINE, NARRATIVE, SOCIAL_CAPTION, SHORT_SUMMARY

**Scoring tiers:**
  1-5:  DISCARD — not published
  6:    PUBLISH — listing page + homepage grid
  7-8:  FEATURED — all above + social + paid email
  9-10: HERO — all channels + Deal of the Day

**Score threshold: discard ≤ 5, publish ≥ 6**

**Content prompt voice — Michelle Bowers / The Old House Life:**
- Short genuine reaction (2-4 sentences) — thing that stops the scroll
- Key facts in natural flowing sentences — not a spec list
- Agent description rewritten in enthusiastic conversational voice
- End cleanly — NO CTA line (site CTA block handles it)
- Zero real estate language — no nestled, rare find, motivated seller, open concept
- Specific proper nouns always — name the town, trail, river, feature
- Short sentences. Real numbers.

**Confirmed cost at scale:** ~$15-18/month at 3 runs/day, 50 listings/run
  (Previously estimated $6.50/mo — that was wrong. Actual confirmed in Session 4.)

**Anthropic account:** No auto-recharge set — manual monitoring until live costs validated.
  Current balance: ~$20. At ~$0.005/scoring call, ~4,000 calls before lockout.
  At 150 calls/day: ~26 days of runway.

---

### RAILWAY (Pipeline Hosting)
**Role:** Runs the ingestion pipeline on a cron schedule in the cloud. Python script deployed from GitHub, runs 3x/day for new listings.

**Account:** housesunder150k@gmail.com
**Plan:** Hobby — $5/mo flat (includes $5 usage credit — pipeline uses ~$0.03/mo compute)
**Project:** housesunder150k
**Project ID:** 586f6dd5-1930-4301-8262-d5562a3119e7
**Service ID:** 15ca3583-43d1-4823-bf3d-5740976e439c
**GitHub:** Connected to github.com/housesunder150k/housesunder150k — auto-deploys on push to main
**Environment:** production (ID: b1c99e6e-a528-42e0-b8f0-503860d53355)

**Cron schedule (SET via MCP):**
  Main pipeline: `0 13,18,23 * * *` — 8am, 1pm, 6pm CT (UTC offset — CT is UTC-5/UTC-4)
  Sold check: not yet configured — Session 5

**Env vars (all set):**
  ANTHROPIC_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN,
  REPLIERS_API_KEY (test key — swap for live in Session 5),
  SOVRN_AFFILIATE_URL (test link — swap when Sovrn approves),
  WEBFLOW_API_TOKEN (site-level token), WEBFLOW_COLLECTION_ID

**Script:** /scripts/ingest.py
**Language:** Python 3
**Dependencies:** requests==2.31.0, anthropic==0.20.0
**Procfile:** `worker: python scripts/ingest.py`

**Pipeline run stats (confirmed Session 4):**
  ~50 listings/run, ~5-6 minutes runtime, ~5 published per run on test data
  ~9 hours/month execution — well within Hobby plan

**WARNING — Dedup resets on deploy:**
  posts/[slug].json lives in container filesystem. Every new Railway deploy loses dedup history.
  DO NOT push code until Supabase dedup fix is in place (Session 5 #1).
  Pushing code = new deploy = dedup reset = duplicate listings on site.

---

### GITHUB
**Role:** Version control for pipeline code and per-listing JSON dedup records.

**Account:** housesunder150k (separate GitHub account)
**Repo:** github.com/housesunder150k/housesunder150k
**Local:** C:\Users\jerem\OneDrive\Desktop\Houses Under 150K
**Remote:** https://github.com/housesunder150k/housesunder150k.git
**Git config:** user.name=housesunder150k / user.email=housesunder150k@gmail.com

**Repo structure:**
  /scripts/ingest.py — main pipeline
  /posts/[slug].json — one per published listing (dedup layer — temporary until Supabase)
  /prompts/ — (empty — prompts embedded in ingest.py)
  /requirements.txt
  /Procfile

**Standard commit:**
  git add . && git commit -m "session: [desc]" && git push origin main

---

### BEEHIIV (Email)
**Role:** Email platform. Native free/paid subscriber tiers. Deal of the Day email to all subs daily.

**Account:** TBD — Session 6
**Cost:** Free tier available; ~$42/mo at scale

**Tiers:**
  Free     > Deal of the Day email daily (acquisition hook)
  $1/month > All Listings Early Access 24-48hrs early (volume investors)
  $2/month > Featured + Deal of the Day curated only (serious investors)

---

### SOCIAL (Facebook)
**Role:** Primary traffic driver before SEO compounds.

**Facebook page:** TBD — Session 6
**Posting tool:** bundle.social or n8n on Railway — TBD Session 6
**Peak post time:** 7-8pm CT

---

### SOVRN / REALTOR.COM
**Role:** Primary monetization from day one.

**Network:** Sovrn (sovrn.com) — Realtor.com affiliate program
**Commission:** $5/lead, 30-day cookie
**Account:** housesunder150k@gmail.com — approval in progress
**Test link:** https://sovrn.co/1qedjsn — live on Milwaukee listing

**Current affiliate-url field behavior:**
  Pipeline writes per-listing Realtor.com address search URL to affiliate-url field.
  Format: https://www.realtor.com/realestateandhomes-search/{street}_{city}_{state}_{zip}
  This lands user near the listing on Realtor.com. Sovrn tracking integration deferred to Session 6.

**VERIFY IN SESSION 5:** Realtor.com URL construction works correctly with real Repliers data.
  Test data had incomplete address fields (some missing streetNumber/streetName).
  make_realtor_url() function is correct — just needs real address data to confirm.

**At Sovrn approval:** swap SOVRN_AFFILIATE_URL in Railway + update Milwaukee listing manually.

---

### NEW SILVER / FLEXOFFERS
**Role:** Secondary affiliate. Hard money loans for investors.
**Status:** Not yet applied — Session 6

---

### AD NETWORKS
  Launch:    Google AdSense ($3-12 RPM, no minimum)
  Month 2-3: Ezoic ($8-20 RPM, 10K sessions)
  Month 3-4: Mediavine ($15-40 RPM, 50K sessions)
  Month 6+:  Raptive ($18-50 RPM, 100K pageviews)

---

## Design System

**Colors:**
  Background #0D0D0D / Surface #111111 / Surface2 #1A1A1A / Border #2A2A2A
  Text Primary #F5F5F5 / Body #CCCCCC / Muted #999999 / Faint #666666
  Accent Cyan #00D4FF / CTA BG #00D4FF / CTA Text #0D0D0D

**Typography:**
  Body/UI: Inter sans-serif
  Price: Space Mono monospace
  Headline: System serif — DO NOT CHANGE

**Style prefixes:** hu150-* (homepage) / lp-* (listing template)

---

## Site Structure
  / — Homepage: Deal of the Day hero + featured grid
  /deal-of-the-day/ — Today's best listing
  /listings/[slug] — Individual listing
  /states/ — State index
  /states/[state] — State listings (404 until built)
  /about/ — About

---

## Pipeline

**Slug format:** {city-slug}-{price} e.g. milwaukee-105000

**Score threshold:** discard ≤ 5, publish ≥ 6

**Fields written per listing:**
  name:             AI-generated headline (or fallback "City, State — $price")
  slug:             {city-slug}-{price}
  price:            integer
  price-display:    "105,000" — comma formatted, NO dollar symbol
  location-display: "Milwaukee, Wisconsin" — FULL STATE NAME always
  address:          street address string
  city:             city string
  state:            two-letter abbreviation
  year-built:       integer
  bedrooms:         integer
  bathrooms:        integer
  square-feet:      integer
  hero-image:       {"url": "https://imagedelivery.net/..."}
  narrative-body:   HTML richtext "<p>...</p>"
  short-summary:    plain text, under 30 words
  listing-url:      https://housesunder150k.com/listings/{slug}
  affiliate-url:    Realtor.com address search URL
  social-caption:   plain text, under 60 words
  status:           "3b41185e9af84f92d8da092965308a2d" (Active option ID)
  deal-of-the-day:  boolean

**Dedup:** posts/[slug].json — WARNING: resets on Railway deploy (Supabase fix Session 5)

**Token logging format (every call):**
  [TOKENS] scoring | in=1050 out=130 | est_cost=$0.00505

---

## Deal of the Day
  One per day — highest scorer (DEAL_OF_DAY_CANDIDATE=YES)
  CMS switch field — only ONE true at a time
  Future: pipeline clears previous before setting new

---

## Revenue
  90 days 1 site: $567/mo / 6 months: $2,528/mo / 12 months: $18,240/mo
  5 sites at 12 months: $40,296/mo

---

## Monthly Cost at Scale (confirmed Session 4)
  Repliers Standard:    $199/mo
  Claude API:           ~$15-18/mo
  Railway Hobby:        $5/mo
  Cloudflare Images:    $5/mo
  Webflow Premium:      $25/mo (billed annually)
  Cloudflare domain:    ~$1/mo
  **Total: ~$250/mo**

  Break-even: ~51 Sovrn leads/month at $5/lead

---

## Session History
  1: Initial setup — Webflow site, CMS schema, design system
  2: Site finish — cards, DoD, About, States, publish subdomain ✔
  3: Domain — Cloudflare DNS > live at housesunder150k.com ✔
  4: Pipeline — ingest.py built, all APIs confirmed, deployed to Railway, cron set ✔
  5: Go live — Supabase dedup, clear test data, live Repliers key, first real run
  6: Social + money — Facebook, posting tool, Sovrn real URL, Beehiiv

---

## Key Decisions
  1.  Native Webflow only — no WHTML for CMS-bound content
  2.  Two-prompt pipeline — scoring routes, content generates
  3.  Score ≤ 5 = discard, score ≥ 6 = publish (not archive)
  4.  Price Display PlainText + Price Number — display vs filter
  5.  Location Display PlainText — full state name always
  6.  Agent description (details.description) from Repliers — primary raw material
  7.  Michelle Bowers voice — curator not journalist
  8.  Deal of the Day — anchor feature, all-channel hero
  9.  Email tiers: free/1/2 per month
  10. Beehiiv — native tiers, recommendation network
  11. Sold = this-sold page not 404
  12. Score 4-5 = discard — only score 6+ published
  13. Cloudflare Images — permanent URLs, no MLS dependency
  14. Webflow Premium paid for year
  15. Dedup via posts/[slug].json — temporary, Supabase migration Session 5
  16. Repliers test key for dev — live key after dedup fix
  17. images[] not photos[] — confirmed Repliers field name
  18. details.description not remarks — confirmed Repliers field
  19. status=A not status=active — confirmed Repliers filter value
  20. Sovrn replaces Commission Junction — Realtor.com moved affiliate program
  21. affiliate-url = per-listing Realtor.com address search URL (not Sovrn link)
  22. Card link = Current listing in Webflow Designer — one-time, permanent
  23. Cloudflare DNS = A @ 198.202.211.1 + CNAME www cdn.webflow.com + TXT _webflow
  24. MCP publish only hits Webflow subdomain — custom domain publish via Designer
  25. Site head custom CSS — visited link fix + card color overrides
  26. Card styles are global classes — all changes apply to every card
  27. Cloudflare Images API: POST multipart/form-data, returns result.variants[0]
  28. Card color spec: $ cyan / price number white / location cyan / summary #CCCCCC
  29. Webflow site-level token required — workspace token lacks cms:write
  30. Repliers image paths are relative — prepend https://cdn.repliers.io/
  31. No CTA line in narrative — site CTA block handles it
  32. affiliate-url = per-listing Realtor.com address search URL
  33. Sovrn link NOT written per-listing — Realtor.com URL used, Sovrn integration Session 6
  34. Dedup = filesystem posts/[slug].json — Supabase migration Session 5
  35. Scoring prompt trimmed ~65% — all rules intact, cost ~45% lower
  36. Cloudflare Images kept despite Repliers CDN — permanent URLs + independence worth $5/mo
  37. Repliers Standard $199/mo monthly — no cheaper alternative for nationwide MLS without license
  38. Railway Hobby $5/mo flat — pipeline uses ~$0.03/mo compute, well within plan
  39. Railway cron `0 13,18,23 * * *` (UTC) = 8am/1pm/6pm CT — set via Railway MCP

---

## Session 5 Start Prompt

"Read the primer at houses-under-150k/vault/primer/_primer.md before doing anything else. This is Session 5 of the HousesUnder150K.com build. Session 5 objective: fix persistent dedup with Supabase, clear test data from Webflow CMS, subscribe to Repliers live MLS key, run first live pipeline, validate content quality and token costs."
