---
project: HousesUnder150K
entity: HousesUnder150K.com — housesunder150k@gmail.com
updated: 2026-07-26
phase: Site build 80% complete — pipeline locked — awaiting Session 2
next_action: Session 2 — fix card styling, Deal of the Day, About, States, publish subdomain
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
- CMS schema — 20 fields including Status and Price Display/Location Display
- First real listing — Milwaukee $105K, all fields populated, queued to publish
- Pipeline architecture — two-prompt system, scoring tiers, content prompts documented
- GitHub repo — connected, VS Code configured at C:\Users\jerem\OneDrive\Desktop\Houses Under 150K
- Webflow Premium — paid ($300/yr)

### Not Done
- Homepage card price display — bound but not visible
- Deal of the Day nav tab, CMS field, and page
- About page, States index page, State template pages
- Sold listing page state on template
- Domain DNS connection (Cloudflare to Webflow)
- Site not yet published
- API integration (Repliers), Pipeline automation (Cowork), Social (Facebook)

---

## Session Protocol

### Session Start
1. Read this primer
2. Read vault/status/_build_status.md — field IDs, style classes, element IDs
3. Confirm Webflow MCP connected in Claude Desktop
4. Confirm which page you are on in designer before any element operations
5. Never assume element IDs, field IDs, or option IDs from memory — check build_status.md

### Session End
1. Update vault/status/_build_status.md
2. Update this primer — phase, next_action, new decisions
3. Write session report to session_reports/YYYY-MM-DD_[description].md
4. git add . && git commit -m "session: [desc]" && git push origin main
5. Run mempalace sync if significant new docs written

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

**Page IDs:**
- Homepage: 6a650a80b2639262c4b6adba
- Listing Template: 6a650bab14666c3157f2761e
- Deal of the Day: TBD Session 2
- About: TBD Session 2
- States Index: TBD Session 2

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
deal-of-the-day TBD — add Session 2

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
- Sort direction: ascending / descending (not asc/desc)
- New CMS fields show null in designer preview until tab refresh — data IS correct

**Pipeline writes via:**
POST https://api.webflow.com/v2/collections/{collection_id}/items
Authorization: Bearer {WEBFLOW_API_TOKEN}
Then publish: POST .../items/publish

**Bandwidth:** 50GB Premium. Images from Cloudflare CDN not Webflow. Effective ~15-20GB/mo at 180K visits.

---

### CLOUDFLARE
**Role — DNS:** housesunder150k.com registered and managed on Cloudflare. Two CNAMEs to go live:
  CNAME @   proxy.webflow.com
  CNAME www proxy.webflow.com
Add in Cloudflare DNS dashboard (Session 3).

**Role — Images:** Cloudflare Images ($5/mo) hosts all hero photos permanently. MLS photo URLs die when listings sell. Cloudflare URLs are permanent. Pipeline uploads on ingestion, stores Cloudflare URL in CMS hero-image field.

**Account:** housesunder150k@gmail.com
**Domain:** housesunder150k.com ~$10/yr
**Cloudflare Images:** $5/mo flat ~100,000 images

**Image URL format:** https://imagedelivery.net/[account-hash]/[image-id]/public

**Pipeline image logic:**
  if hero_image_url starts with "imagedelivery.net": skip (already cached)
  else: fetch from MLS > upload to Cloudflare API > store returned URL in CMS

**No database needed.** hero-image field IS the index. One conditional check.
**Cloudflare Images API:** POST https://api.cloudflare.com/client/v4/accounts/{id}/images/v1
Upload multipart/form-data. Returns result.variants[0] as permanent URL.

---

### REPLIERS (Listing API)
**Role:** Primary listing data source. Real-time MLS. Returns specs, photos, agent descriptions, status. Pipeline fetches 3x/day filtered price <= $150K and status = active. photos[0] is the hero image source URL.

**Account:** TBD — free trial at repliers.io — start before Session 4
**Cost:** $199/mo

**Key field mappings:**
  listPrice           > price
  address.full        > address
  address.city        > city
  address.state       > state (two-letter)
  details.numBedrooms > bedrooms
  details.numBathrooms > bathrooms
  details.sqft        > square-feet
  details.yearBuilt   > year-built
  photos[0]           > hero image source URL
  mlsNumber           > internal dedup reference
  listingUrl          > listing-url
  remarks             > agent description (both prompts)
  features[]          > tags for scoring

**Tips:**
- Scrape full listing page for agent description if remarks is truncated
- Full agent description is the primary narrative raw material — never skip this
- Store mlsNumber for dedup and sold checks
- Test API response shape carefully before writing ingestion script

---

### ANTHROPIC API (Claude)
**Role:** Powers the two-call pipeline. Call 1 scores and routes. Call 2 generates all content. This IS the content engine.

**Model:** claude-sonnet-4-6
**Max tokens:** 1000 per call
**Endpoint:** https://api.anthropic.com/v1/messages

**Call 1 — Scoring (every listing ~200 tokens):**
  Prompt: /prompts/scoring-prompt.md
  Input: listing data + agent description
  Output: SCORE, FEATURED, CATEGORY, REASON, KEY HOOKS

**Call 2 — Content Generation (score 6+ only ~800 tokens):**
  Prompt: /prompts/deals-under-150k.md
  Input: listing data + CATEGORY + KEY HOOKS + affiliate URL
  Output: HEADLINE, NARRATIVE (300-400 words), SOCIAL CAPTION (<60 words), SHORT SUMMARY (<30 words)

**Scoring tiers:**
  8-10: Hero / Deal of the Day — 2-3/day
  6-7:  Standard Featured — 5-7/day
  4-5:  Archive only — unlimited
  1-3:  Skip — rare

**Voice — Michelle Bowers / The Old House Life:**
- Short genuine reaction first (1-3 sentences of real enthusiasm)
- Key facts in natural flowing sentences — not a spec list
- Agent description rewritten in enthusiastic conversational voice
- Simple CTA last
- Zero real estate language — no nestled, rare find, motivated seller, open concept
- Specific proper nouns always — name the town, trail, river, feature
- Second person present tense — "you wake up to the lake"

Bad: "This stunning waterfront home offers incredible lakeside living at an unbeatable price."
Good: "Waterfront. Circa 1927. Minnesota. $289,000. There's a dock. There's a boathouse."

**Cost at scale:** ~$6.50/month per site

---

### COWORK (Automation)
**Role:** Runs pipeline on schedule. Cloud-based. No laptop needed.

**Three scheduled tasks:**

1. Main pipeline (8am, 1pm, 6pm CT daily):
   Fetch listings from Repliers > scrape agent description > score Call 1 >
   generate content for 6+ Call 2 > upload image to Cloudflare > write to
   Webflow CMS > publish > log to /posts/[slug].json > flag Deal of the Day

2. Sold check (9am CT daily):
   Fetch all Active CMS listings > check each via Repliers > update status to
   Sold for any removed > clear deal-of-the-day flag if that listing sold

3. Social post (triggered by pipeline):
   Featured listing published > fire social post via bundle.social or n8n >
   Deal of the Day posts at 7-8pm CT

**Status:** Not yet set up — Session 5
**Tips:**
- Build and test ingestion script locally first (Session 4)
- Single test run of full loop before scheduling
- Log all pipeline runs to /posts/ for audit trail and dedup

---

### GITHUB
**Role:** Version control for pipeline code, prompts, and per-listing JSON records. Prompts directory is editorial source of truth.

**Account:** housesunder150k (separate GitHub account)
**Repo:** github.com/housesunder150k/housesunder150k
**Local:** C:\Users\jerem\OneDrive\Desktop\Houses Under 150K
**Remote:** https://github.com/housesunder150k/housesunder150k.git
**Git config:** user.name=housesunder150k / user.email=housesunder150k@gmail.com

**Repo structure:**
  /docs/build_status.md and concept.md
  /prompts/scoring-prompt.md and deals-under-150k.md
  /posts/[slug].json — one per published listing
  /scripts/ingest.js — pipeline ingestion (Session 4)

**Standard commit:**
  git add . && git commit -m "session: [desc]" && git push origin main

**Tips:**
- /posts/[slug].json = pipeline dedup layer — slug exists = already processed
- Prompt files are most important files in repo — version every change
- Claude cannot push commits — requires manual terminal or GitHub Desktop

---

### BEEHIIV (Email)
**Role:** Email platform. Native free/paid subscriber tiers. Deal of the Day email to all subs daily — primary audience growth mechanism. Paid tiers = recurring revenue independent of traffic.

**Account:** TBD — Session 6
**Cost:** Free tier available; ~$42/mo at scale

**Tiers:**
  Free     > Deal of the Day email daily (acquisition hook)
  $1/month > All Listings Early Access 24-48hrs early (volume investors)
  $2/month > Featured + Deal of the Day curated only (serious investors)

**Tips:**
- Deal of the Day to free subs IS the product that drives signups — not giving it away
- Connect Webflow subscribe embed directly to Beehiiv list
- Raise to $5/month once list exceeds 1,000 subscribers
- Recommendation network cross-promotes similar newsletters — organic list growth

---

### SOCIAL (Facebook / bundle.social)
**Role:** Primary traffic driver before SEO compounds. Facebook dominates this niche. Each Featured listing gets a social post. Deal of the Day gets peak-time reel.

**Facebook page:** TBD — create before Session 6
**Posting tool:** bundle.social (flat per-brand) or n8n on Railway
**Status:** Not yet set up — Session 6
**Peak post time:** 7-8pm CT

**Caption rules:**
- Under 60 words, no hashtags, hook in first line, price and location always
- Write like a person not a brand — human posts get more organic reach
- Captions pre-written by pipeline — no manual copywriting

**Tips:**
- Budget $50-100 to boost first Deal of the Day post per new site
- First 500 followers hardest — after that algorithm compounds
- Deal of the Day reel is highest-converting format

---

### COMMISSION JUNCTION / REALTOR.COM
**Role:** Primary monetization from day one. Every listing CTA links to Realtor.com via affiliate tracking URL. $5 per qualified lead.

**Network:** Commission Junction (cj.com)
**Commission:** $5/lead, 30-day cookie
**Account:** TBD — housesunder150k@gmail.com — applied, pending 1-3 weeks
**Apply:** cj.com > Join as Publisher > search Realtor.com

**Tips:**
- Apply day one — do not let approval wait and block launch
- Same CJ account across all sites, different tracking IDs per site
- Affiliate URL in CMS affiliate-url field — pipeline writes it automatically

---

### NEW SILVER / FLEXOFFERS
**Role:** Secondary affiliate. Hard money loans for investors. $50/lead + 0.5% closed loans.
**Network:** FlexOffers — **Status:** Not yet applied — Session 6

---

### AD NETWORKS
**Role:** Display revenue. Scales with traffic.
  Launch:    Google AdSense ($3-12 RPM, no minimum)
  Month 2-3: Ezoic ($8-20 RPM, 10K sessions)
  Month 3-4: Mediavine ($15-40 RPM, 50K sessions) — first real step change
  Month 6+:  Raptive ($18-50 RPM, 100K pageviews)

Q4 RPMs run 40-80% higher. Ad scripts served from network CDN — no Webflow bandwidth impact.

---

## Design System

**Colors:**
  Background #0D0D0D / Surface #111111 / Surface2 #1A1A1A / Border #2A2A2A
  Text Primary #F5F5F5 / Body #CCCCCC / Muted #999999 / Faint #666666
  Accent Cyan #00D4FF / CTA BG #00D4FF / CTA Text #0D0D0D

**Typography:**
  Body/UI: Inter sans-serif
  Price: Space Mono monospace
  Headline: System serif — DO NOT CHANGE — looks great as-is

**Type scale:**
  Homepage hero: 120px > 72px > 52px > 44px (across breakpoints)
  Price: $ 42px cyan / number 72px white / Space Mono / flex row baseline
  H1: 36px Inter 700 / Section: 28-36px / Card location: 13px cyan uppercase
  Body: 17px 1.8 line-height #CCCCCC / Spec value: 22px 700 / Nav: 14px #999999

**Style prefixes:** hu150-* (homepage) / lp-* (listing template)

---

## Site Structure
  / — Homepage: Deal of the Day hero + featured grid
  /deal-of-the-day/ — Today's best listing
  /listings/[slug] — Individual listing (all scores)
  /states/ — State index
  /states/[state] — State listings
  /about/ — About

---

## Pipeline

**Two calls per listing:**
  Call 1 Scoring: every listing, fast, routes to tier
  Call 2 Content: score 6+ only, generates headline/narrative/caption/summary

**Scoring tiers:**
  8-10: Hero/Deal of Day — homepage hero + social reel + email all — 2-3/day
  6-7:  Standard — homepage grid + social post + email paid — 5-7/day
  4-5:  Archive — listing page + state search only
  1-3:  Skip — rare, bad data only

**Fields written per listing:**
  price-display: "105,000" comma formatted NO dollar symbol
  location-display: "Milwaukee, Wisconsin" FULL STATE NAME always
  hero-image: Cloudflare URL (imagedelivery.net/...)
  status: Active option ID 3b41185e9af84f92d8da092965308a2d
  deal-of-the-day: true for daily best, false all others

**Sold handling:** Daily check > status to Sold > vanishes from homepage/states >
  listing page shows "This property has sold. See more in [State] >" > never 404

---

## Deal of the Day
  One per day — highest scorer > /deal-of-the-day page + homepage hero slot 1
  + social reel + email ALL subs > 7-8pm CT peak post
  CMS switch field — only ONE true at a time — pipeline clears previous

---

## Revenue
  90 days 1 site: $567/mo / 6 months: $2,528/mo / 12 months: $18,240/mo
  5 sites at 12 months: $40,296/mo

---

## Open Items Session 2
  [ ] Fix homepage card price display and image placeholder height
  [ ] Add Deal of the Day nav tab
  [ ] Add deal-of-the-day Switch field to CMS
  [ ] Build /deal-of-the-day page
  [ ] Build /about page
  [ ] Build /states/ index page
  [ ] Add sold listing page state to template
  [ ] Connect Cloudflare DNS two CNAMEs to Webflow
  [ ] Publish to Webflow subdomain

## Pre-Session 2 Checklist
  [x] Webflow Premium paid
  [x] GitHub repo connected, VS Code configured
  [x] build_status.md and concept doc written
  [ ] Commission Junction application submitted
  [ ] Repliers free trial started (repliers.io)
  [ ] Cloudflare Images account created ($5/mo)
  [ ] Docs pushed to GitHub

## Session 2 Start Prompt
  "Read the primer at houses-under-150k/vault/primer/_primer.md — Session 2 of
  HousesUnder150K.com Webflow build. Fix homepage card styling, add Deal of the
  Day nav tab and CMS field, build Deal of the Day page, About page, States index,
  publish to subdomain. Site ID: 6a650a7eb2639262c4b6adb7.
  Homepage: 6a650a80b2639262c4b6adba.
  Listing Template: 6a650bab14666c3157f2761e."

## Session Plan
  2: Site finish — cards, DoD, About, States, publish subdomain
  3: Domain — Cloudflare DNS > live at housesunder150k.com
  4: API + images — Repliers, field mapping, Cloudflare Images pipeline
  5: Automation — Cowork tasks, full loop end-to-end test
  6: Social + money — Facebook, posting tool, affiliates, Beehiiv

## Key Decisions
  1.  Native Webflow only — no WHTML for CMS-bound content
  2.  Two-prompt pipeline — scoring routes, content generates
  3.  Scoring is routing not gating — 8-10 posts/day
  4.  Price Display PlainText + Price Number — display vs filter
  5.  Location Display PlainText — full state name always
  6.  Agent description scraped from listing URL — primary raw material
  7.  Michelle Bowers voice — curator not journalist
  8.  Deal of the Day — anchor feature, all-channel hero
  9.  Email tiers: free/1/2 per month
  10. Beehiiv — native tiers, recommendation network
  11. Sold = this-sold page not 404
  12. Everything to archive regardless of score
  13. Cloudflare Images — permanent URLs, no MLS dependency
  14. Webflow Premium paid for year
  15. No extra database — CMS hero-image field IS the index
