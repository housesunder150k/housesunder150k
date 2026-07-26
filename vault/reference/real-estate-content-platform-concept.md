# Real Estate Content Platform — Concept Document
*Draft v0.1 — July 2026*

---

## Vision

An automated, multi-theme content platform that discovers real estate listings, generates narrative-driven content around them, and publishes across social media, websites, and email — at scale, with minimal human intervention.

The model mirrors what successful Facebook real estate pages already do manually: find compelling listings, write an engaging story around them, tease it on social, and drive traffic back to a site for the full content. This platform automates every step of that process and runs it across multiple themed channels simultaneously from a single command center dashboard.

---

## The Business Model

### How It Works

1. A real-time listing feed surfaces new properties matching defined criteria (price, age, location, keywords)
2. AI generates original narrative content around each listing — written in the voice of the channel's theme
3. Content is reviewed and approved via a curation dashboard (the human-in-the-loop step)
4. Approved content publishes automatically to: a theme website, social media accounts, and an email list
5. All outbound links point back to the original listing on Zillow, Realtor.com, or similar — via affiliate tracking URLs

### What Makes It Defensible

- **Volume at quality** — automated pipelines can sustain 10–15 posts/day + 5–7 video reels per theme, a pace no manual operator can match
- **Theme differentiation** — each channel has a distinct voice, niche, and audience rather than generic listing aggregation
- **Cross-platform presence** — Facebook, Instagram, TikTok, and website simultaneously from a single content generation event
- **Email list ownership** — unlike social followers, the email list is a direct, owned audience asset

---

## Revenue Streams

### 1. Affiliate Revenue

Affiliate revenue runs as a layered stack — not a single program. Every piece of content carries a primary listing link plus secondary affiliate placements matched to the theme's audience. This significantly increases revenue per visitor without adding friction.

**Important note on Zillow:** Zillow does not have an active public affiliate program that pays publishers. Their monetization model is agent-facing (Zillow Premier Agent). Primary listing links should point to Realtor.com, which has an active affiliate program, or Redfin.

**Layer 1 — Primary listing link (every post, every platform)**
Realtor.com affiliate — $5 per lead, 30-day cookie. Every social post, reel, email, and website page links here. High volume, low friction, consistent baseline revenue.

**Layer 2 — Financing affiliates (website + email, theme-matched)**
- New Silver (hard money loans) — $50 per lead + 0.5% of closed loan. One $200K fixer-upper referral = $1,050. Direct fit for Deals Under $150K and Fixer Upper themes.
- LendingTree / Credible (mortgage) — $20–50 per lead. Broader first-time buyer fit.

**Layer 3 — Investment platform affiliates (website sidebar + email)**
- Fundrise — $50–100 per referral, 30-day cookie. $10 minimum investment keeps conversion friction low. Strong fit for deals and land themes.
- EquityMultiple — $250+ per qualified signup via Impact. Accredited investors only — narrow but extremely high per-conversion value.

**Layer 4 — Recurring SaaS affiliates (email + website)**
- Buildium (property management) — 25% recurring monthly commission. Every cheap property purchase creates a potential landlord.
- DealCheck (investment analysis) — 30% recurring commission. Natural fit for investors analyzing purchases.

**Layer 5 — Education affiliates (email + website)**
- Colibri Real Estate (licensing courses) — 25% commission. Deal hunters frequently want to become agents.
- BiggerPockets Pro — $75 per signup. Largest real estate investing community.

**Revenue math at volume:**
A single New Silver loan referral closing at $150K = $800 ($50 lead + $750 loan commission). That one conversion outearns 160 Realtor.com leads. Strategy: volume on Layer 1 (Realtor.com) + high-value conversion optimization on Layers 2–3 for the investor audience.

### 2. Website Ad Revenue
Social content drives traffic back to theme websites for the "full story." Real estate is a high-CPM niche — advertisers pay premium rates for this audience. Premium ad networks (e.g., Mediavine) become accessible once traffic thresholds are reached.

### 3. Social Platform Monetization
Facebook Reels, TikTok Creator Fund, Instagram Reels bonuses, and YouTube Shorts (if cross-posted) all pay based on views. The content is being created anyway — platform monetization is pure upside once accounts qualify.

### 4. Email Subscriptions
Each theme runs a paid email list ($1–5/month) delivering curated listings directly to subscribers' inboxes. Secondary monetization through the list includes sponsorships, featured listings, and affiliate offers from adjacent services (mortgage lenders, home inspectors, moving companies).

### 5. Platform Access (Later Stage)
The command center infrastructure itself becomes a sellable product — either as a white-label SaaS or as a licensed tool for others who want to run their own themed channels.

---

## Theme Model

Each "theme" is an independent content channel with its own:
- Niche angle and target audience
- Content voice and narrative style
- Website and domain
- Social media account set (Facebook, Instagram, TikTok)
- Email list
- Listing filter criteria

### Example Theme Concepts

**Deals Under $150K** — Pure value/investor angle. Punchy, data-forward copy. Audience: first-time buyers, investors, flippers. $150K threshold chosen deliberately — captures 3-4x more inventory than $100K while retaining the "deals most people don't know about" hook. Performs across all US markets including mid-cost metros where sub-$100K is nearly nonexistent.

**Historic & Forgotten Homes** — Narrative-heavy. Research into original builders, notable owners, architectural history. Audience: history enthusiasts, preservationists, unique home seekers.

**Small Town America** — Emotional/nostalgic framing around rural and small-town properties. Audience: people dreaming of leaving cities, retirees, remote workers.

**Fixer Upper Finds** — Potential-focused framing. Before/after imagination, renovation cost estimates. Audience: DIY community, HGTV crowd, house flippers.

**Dirt Cheap Land** — Vacant lots, rural acreage, off-grid potential under $50K. Audience: preppers, homesteaders, land banking investors.

*Each theme is the same pipeline with a different filter set and content template applied.*

---

## Consumer Product Layer

In addition to the operator-facing command center, the platform exposes a consumer-facing product — a website and iOS/Android app — that serves generated content directly to end users.

### Two-Tier User Model

**Free Tier**
- Access to listings and narrative content
- 48-hour delay on new listings vs. premium users
- Ad-supported (in-app and website advertising)
- Email digest opt-in

**Premium Tier ($5/month)**
- Listings surfaced immediately when approved — 48 hours before free users
- Ad-free experience
- Push notifications for new listings matching saved filters
- Priority access to new themes and features

### Consumer App
- iOS and Android (single codebase — React Native or Flutter)
- Browse listings by theme, filter by price/location/property type
- Save favorites, set listing alerts
- In-app subscription management
- Push notifications for premium users
- Reads entirely from the central content database via API

### Consumer Website
- Theme-specific sites (e.g., dealsunder100k.com, historichomefinds.com)
- Full narrative content per listing — the "full story" that social posts tease
- Ad placements for free/anonymous visitors
- Email capture and subscription upsell
- SEO-optimized — each listing page is a crawlable, indexable content asset
- Reads entirely from the central content database via API

### The Flywheel
```
Social reels/posts → app downloads + website visits
App users → email subscribers
Email subscribers → premium conversions ($5/mo)
Premium users → word of mouth → more downloads
More users → higher ad CPM → more ad revenue
Larger audience → better affiliate click volume → more affiliate revenue
```

---

## System Architecture (Reference — Not Committed)

> **Note:** The tooling space for AI content generation, video creation, and social publishing is moving extremely fast. The components below represent one viable architecture based on research at time of writing. Before building, each layer should be evaluated against current open-source alternatives on GitHub and the broader market. Reducing third-party dependencies where possible improves margin and control.

### Core Principle: Database as Source of Truth

The central content database owns every piece of content in the system. No consumption layer generates, transforms, or stores its own copy of content. Every layer — app, website, social publishing, email, Claude generation — reads from and writes back to the same database through a shared API.

This means:
- Content is consistent everywhere by definition
- Analytics are unified — every view, click, and conversion writes back to the same record
- The 48-hour tier gate is a single timestamp field, enforced at the API layer
- Adding a new consumption layer (e.g., YouTube, a new app platform) requires no content changes — just a new reader

### Architecture Overview

```
Real Estate Listing API (webhook)
            ↓
    ┌───────────────────────────────┐
    │     CENTRAL CONTENT DATABASE  │
    │                               │
    │  Listing record lifecycle:    │
    │  ingested → generating →      │
    │  pending_approval →           │
    │  scheduled → published        │
    │                               │
    │  Every record owns:           │
    │  - Raw listing data           │
    │  - All generated content      │
    │  - Theme + voice applied      │
    │  - Tier timestamps            │
    │  - Per-platform pub status    │
    │  - Engagement metrics         │
    └───────────────────────────────┘
         ↑                  ↓
   Claude API          Job Queue
   (writes generated   (orchestrates all
    content back)       async work)
         ↑                  ↓
    ┌─────────────────────────────────────────┐
    ↓          ↓          ↓          ↓         ↓
Consumer    Consumer   Command    Social    Email
   App      Website    Center    Publisher  Sender
(reads API) (reads API)(reads API)(reads API)(reads API)
    ↓           ↓                    ↓          ↓
 [ads +      [ads +               [FB/IG/   [subscriptions
 $5/mo sub]  affiliate]           TikTok]   + affiliate]
```

### Content Record Lifecycle

Each listing that enters the system follows a defined state machine:

```
ingested        — raw listing data saved, awaiting generation job
generating      — Claude job running, content being written
pending_review  — content ready, awaiting human approval
scheduled       — approved, queued for publish at defined times
published       — live across all assigned channels
archived        — expired, sold, or manually removed
rejected        — removed from queue by curator
```

### Tier-Gating Logic (lives entirely in the database)

```
premium_available_at  =  ingested_at + 0h   (immediate on approval)
public_available_at   =  ingested_at + 48h  (delayed for free users)
```

Every API endpoint that serves content to the app or website checks the requesting user's tier against these timestamps. No special logic anywhere else in the system.

### Layer-by-Layer

**Listing Data**
Needs: Real-time or near-real-time feed of new MLS listings, filterable by price, property age, geography, and keywords. Webhook support preferred over polling.
Example candidate: Repliers (unified MLS API, US + Canada, webhook support)
Investigate: Open-source MLS connectors, RETS feed tools, RapidAPI real estate options

**Content Generation**
Needs: LLM with structured prompting, theme-aware templates, consistent voice per channel, historical research capability (for history-angle themes).
Example candidate: Claude API (Anthropic)
Investigate: Self-hosted open-source LLMs for cost reduction at volume

**Video Reel Generation**
Needs: Programmatic video creation from listing photos + AI voiceover script. Output formatted for vertical short-form (9:16). Batch API support.
Example candidates: HeyGen API, Runway, fal.ai, Replicate-hosted models
Investigate: Open-source video generation pipelines (e.g., MoviePy + TTS + ffmpeg), self-hosted alternatives that eliminate per-video costs

**Social Publishing**
Needs: Multi-account, multi-platform publishing API. Facebook, Instagram, TikTok at minimum. Scheduling, reel/video upload, no per-profile pricing at scale.
Example candidates: SocialAPI.ai, bundle.social, PostEverywhere, Ayrshare
Investigate: Direct platform API integrations (Meta Graph API, TikTok Content Posting API) to eliminate middleware cost

**Email**
Needs: Subscriber management, paid subscription support, API access for automated sends, list segmentation per theme.
Example candidates: Beehiiv, Resend + custom list management
Investigate: Self-hosted options (Listmonk is open-source, free, self-hosted)

**Command Center Dashboard**
Needs: Multi-theme management, content approval queue, scheduling calendar, account management, analytics aggregation, revenue tracking.
Build custom — this is the core proprietary asset. No off-the-shelf tool does exactly this.

**Consumer App**
Needs: iOS + Android, single codebase, listing browsing by theme/filter/location, push notifications, in-app subscription management, ad integration for free tier.
Example candidates: React Native, Flutter
Investigate: Expo (React Native) for faster iteration and OTA updates

**Subscription & Billing (Mobile)**
Needs: In-app purchase management across App Store and Google Play, subscription state sync to database, webhook handling for renewals/cancellations.
Example candidates: RevenueCat (standard for mobile subscription management)
Note: Web subscriptions handled separately via Stripe

**In-App Advertising**
Needs: Ad network integration for free tier on both app and website.
Example candidates: Google AdMob (app), Google AdSense / Mediavine (website)
Note: Real estate is a high-CPM niche — premium ad networks become accessible at traffic thresholds (~50K sessions/month for Mediavine)

**Database & Backend**
Needs: Multi-tenant data model (themes, accounts, listings, content, subscribers as first-class objects). Job queue for async content generation and publishing.
Example candidates: Supabase (already in use), PostgreSQL + BullMQ or similar queue
Investigate: Whether existing ShowFlyer infrastructure can be shared or adapted

**Hosting**
Example candidates: Vercel (dashboard + theme sites), Railway, Fly.io
Investigate: Self-hosted options once scale justifies it

---

## Automation Target

**95% automated.** The human role in steady-state operation:

- 30–60 minutes/day in the curation dashboard reviewing and approving queued content
- Periodic theme strategy decisions (new themes, content angle adjustments)
- Exception handling (API outages, platform policy changes, unusual listings)

Everything else — discovery, generation, scheduling, publishing, email delivery, affiliate linking — runs without human involvement.

---

## Content Volume Per Theme (Target)

| Content Type | Daily Volume | Platforms |
|---|---|---|
| Text/image posts | 10–15 | Facebook, Instagram |
| Video reels | 5–7 | Facebook, Instagram, TikTok |
| Email digest | 1 (daily or 3x/week) | Email list |
| Website posts | 10–15 | Theme website |

At 5 themes: ~75 posts/day, ~30 reels/day across all platforms.

---

## Rough Cost Model (Illustrative — Pre-Tool-Selection)

| Layer | Estimated Monthly Cost |
|---|---|
| Listing data API | $150–200 |
| AI content generation | $30–75 |
| Video generation | $100–200 per theme |
| Social publishing | $30–150 |
| Email platform | $0–50 |
| Hosting & infrastructure | $25–75 |
| **Total (1 theme)** | **~$350–750/mo** |
| **Total (5 themes)** | **~$1,000–2,000/mo** |

*Costs shift significantly based on tool selection. Open-source alternatives (self-hosted video pipeline, self-hosted email, direct platform APIs) could reduce this by 40–60%.*

---

## Revenue Potential (Conservative / Realistic at 5 themes, 12 months)

| Stream | Conservative | Realistic |
|---|---|---|
| Affiliate clicks | $500/mo | $2,000/mo |
| Social platform pay | $300/mo | $1,500/mo |
| Website ad revenue | $800/mo | $3,500/mo |
| Email subscriptions | $500/mo | $2,500/mo |
| App subscriptions ($5/mo) | $250/mo | $2,000/mo |
| **Content platform total** | **$2,350/mo** | **$11,500/mo** |
| Analytics data licensing | $0 (building) | $5,000+/mo |
| Analytics API access | $0 (building) | $2,000+/mo |
| **Combined total** | **$2,350/mo** | **$18,500+/mo** |

*Does not include sponsorship revenue, featured listing placements, platform SaaS licensing, or white-label analytics deals. Analytics revenue is a later-stage event — it requires meaningful user base depth before approaching data buyers.*

---

## Three Distinct Business Models

This platform is not one business — it is three, each independently valuable:

**1. Content & Media Business**
Ad revenue, affiliate clicks, app and email subscriptions. Scales with audience size. Each theme is a separately monetized and sellable media property.

**2. SaaS Platform**
The command center infrastructure licensed to others who want to run their own themed content channels. Recurring B2B revenue, higher margins than media.

**3. Data Business**
The analytics service and the behavioral dataset it accumulates. Licensable to PropTech companies, real estate platforms, brokerages, and financial institutions. This is the highest-margin, most defensible business of the three — and the one that appreciates in value as the user base grows, independent of content revenue.

The three businesses share the same infrastructure cost base and the same user acquisition engine (social media). That is the compounding advantage.

---

## Asset Value

Each theme channel, once established with a proven audience and email list, is an independently sellable media asset. Niche content properties with monetized audiences typically sell for 24–36x monthly revenue. The platform infrastructure itself carries additional value as a licensable or white-label product.

---

## Proof of Concept — Phase 0

Before any platform infrastructure is built, a fully automated single-theme POC proves the revenue loop works. Once the POC is generating consistent revenue it funds and informs the full platform build.

### POC Scope
**Theme:** Deals Under $150K
**Goal:** Automated content pipeline running lights-out, generating affiliate revenue within 30 days
**Stack:** Entirely AI-native — no custom code, no servers, no dashboard

### POC Architecture

```
Cowork Scheduled Task (3x/day, cloud-executed)
        ↓
Web search → Realtor.com filtered under $150K
        ↓
Claude reviews listings → selects 2-3 best candidates
        ↓
Claude generates: headline + narrative post + social caption
        + Realtor.com affiliate links injected automatically
        ↓
WordPress MCP Adapter → publishes post to self-hosted site
        ↓
n8n workflow → detects new post → publishes to Facebook page
        ↓
Phone notification → tap to approve → live
```

### Why This Stack

**Cowork Scheduled Tasks** run entirely in the cloud as of July 2026 — no device needs to be on. Tasks fire on schedule, execute, and notify you on your phone when a decision is needed. Doubled usage limits run through August 5, 2026 — ideal timing to start.

**Mobile oversight** means the "curation step" is a 30-second phone tap from anywhere. Claude pings when posts are ready to approve. Nothing publishes without confirmation. This is the human-in-the-loop without the desk commitment.

**WordPress MCP Adapter** (ships with WordPress 6.9) gives Claude direct write access to a self-hosted WordPress site — create posts, set categories, inject affiliate links, publish. No API wrangling required.

**GitHub** tracks every post as a commit — simple record of what was published, when, and what listing it referenced. No database needed for the POC.

**n8n** (open source, self-hosted free on Railway) bridges WordPress to Facebook — detects new published posts and auto-posts the social caption with the website link. One setup, runs forever.

### POC Setup Sequence

1. Register domain (~$12)
2. Spin up self-hosted WordPress on SiteGround or similar (~$5/mo)
3. Install WordPress 6.9 + MCP Adapter
4. Connect WordPress MCP to Claude Desktop
5. Set up Facebook page for the brand
6. Set up n8n on Railway (free tier) — WordPress → Facebook workflow
7. Apply for Realtor.com affiliate (Commission Junction) + New Silver (FlexOffers)
8. Write and test the Cowork prompt template with 3 real listings
9. Set up Cowork Scheduled Task — 3x/day
10. Confirm full loop end-to-end before scheduling

**Estimated setup time: 2-3 days**
**Ongoing time commitment: 30-second phone approval, 3x/day**
**Monthly cost: ~$17 (domain + hosting)**

### Editorial Philosophy — What Gets Featured

The brand's value is curation, not aggregation. Anyone can filter Realtor.com for `price < $150K`. What makes HousesUnder150K worth following is that something looked at that list and surfaced the ones worth stopping for.

**The single editorial question every listing must answer:**

> "Would someone stop scrolling for this?"

Not "is this affordable?" Not "is this a good deal mathematically?" Those are table stakes. The question is whether this listing makes someone *feel* something — possibility, surprise, longing, disbelief. The listings that drive follows, shares, email signups, and affiliate clicks are the ones that sell a feeling, not just a price.

**The feeling we're selling:**

That different life is actually possible. The farmhouse on 3 acres with a barn and chicken coop in rural Southern Illinois isn't just a house — it's an answer to a question millions of people are quietly asking: *what if I just... left?* The 1890s brick Victorian with original stained glass for $94K isn't just affordable — it's proof that beauty and craftsmanship still exist at prices real people can reach. The brand new construction at $105K in Milwaukee isn't just new — it's the thing that makes someone say "wait, that's actually possible?"

**Featured listing categories:**

**"What If" Listings — lifestyle fantasy**
The ones that sell a completely different way of life. Rural properties with acreage, outbuildings, working farms, lakefront cottages, mountain cabins. The viewer isn't necessarily buying — they're imagining. And they'll share it because their friend needs to see this exists.
- Farmhouses with land (1+ acres)
- Properties with barns, workshops, carriage houses, chicken coops
- Rural settings that communicate escape
- Waterfront or mountain properties at impossible prices

**"Too Good To Be True" Listings — exceptional value**
The ones where the math seems wrong. New construction at $105K. 5 bedrooms for $67K. 2 acres with a house for less than a used car. These generate disbelief, which generates shares.
- New construction under $150K
- Unusually large homes (4+ BR, 2000+ sqft) for the price
- Properties with significant land at low per-acre cost
- Price per sqft dramatically below local market

**"Time Machine" Listings — historical character**
The ones where original craftsmanship survived. Pre-1900 homes with intact architectural details that would cost six figures to recreate today. These appeal to people who understand what's been lost and what it means to find it intact.
- Pre-1900 construction with original details
- Brick construction, original hardwood, ornate staircases
- Stained glass windows, original built-ins, pocket doors
- Historic district properties or documented community history
- Wraparound porches, turrets, Victorian millwork

**"Hidden Gem" Listings — character in unexpected places**
Solid, charming homes that punch above their price. Not run-down properties in declining neighborhoods — the opposite. The well-maintained brick bungalow in a working-class neighborhood with good bones and real character. The craftsman cottage that needs cosmetic work but has the kind of quality that doesn't get built anymore.
- Brick construction at any price
- Solid bones with cosmetic upside
- Unusual architectural features (pools, large garages, outbuildings)
- Community character (historic main street town, lake community, college town)

**What does NOT get featured on homepage/social (but still gets archived):**

- Generic suburban tract homes with no distinguishing characteristics
- Cookie-cutter 1980s-2000s construction with no character or story
- Properties where the only notable thing is the price

**What gets skipped entirely (rare):**

- Condemned or structurally uninhabitable properties
- Listings with missing/corrupt data (no address, no price, etc.)
- Clear duplicates

Everything else gets at minimum an archive listing page that builds the state search index and SEO footprint. The distinction is what gets the social and homepage treatment — not whether it gets published at all.

**Three layers, three revenue paths:**

**Layer 1 — Archive (all listings under $150K)**
Every qualifying listing gets a published page regardless of score. This is the utility layer and the SEO engine. At scale, thousands of unique listing pages create a massive long-tail search footprint. Someone searching "cheap homes in Dayton Ohio" lands on the site, not Realtor.com. They click the affiliate link. Revenue without any social effort.

Each state gets its own indexed page (`/states/ohio`, `/states/tennessee`) listing all current inventory. Pure utility, pure SEO, compounding passive affiliate revenue over time.

**Layer 2 — Standard Featured (score 6-7)**
Gets the full narrative treatment and a social text post. Drives engaged traffic back to the site. Higher intent than archive visitors — they came because something caught their eye.

**Layer 3 — Hero Featured (score 8-10)**
The wow listings. Gets the reel, the email send, the homepage carousel hero slot. Drives follows, shares, and signups. These build the audience that makes everything else more valuable over time.

Users discover the archive through Google search. They discover the brand through featured content. These are different jobs served by the same infrastructure. Never post or feature a listing unless it meets the scoring criteria — but publish everything to the archive.

---

### Editorial Scoring Prompt

This runs as a fast, lightweight first pass on every listing before content generation. It is a **routing system, not a gatekeeper** — the goal is 8-10 published posts per day across all tiers. Almost every listing gets published somewhere. The score determines where.

Stored in `/prompts/scoring-prompt.md` in the GitHub repo.

```
You are the editorial curator for HousesUnder150K.com.

We are NOT a listing aggregator. We are a media brand that 
surfaces the listings worth stopping for — the ones that make 
someone say "wait, that's actually possible?" We feature homes 
that sell a feeling: possibility, escape, disbelief at the value, 
or appreciation for craftsmanship that doesn't exist at this price 
anymore.

We do NOT feature: generic suburban tract homes, cookie-cutter 
1980s-2000s construction with no character, or properties whose 
only notable quality is being cheap.

Score this listing 1-10. Be generous — the goal is volume 
AND quality. Most listings should score 4 or above. Only truly 
unusable listings (bad data, condemned, no story whatsoever) score 1-2.

10 = Stop everything. Pre-1900 brick Victorian with original 
     stained glass on 2 acres for $89K. People will share this.
8-9 = Wow listing. Strong character, lifestyle appeal, compelling 
      story. Gets the reel treatment and email feature.
6-7 = Solid listing worth a full post and social. Good value, some 
      character, interesting enough to cover. This is the STANDARD 
      — most listings that get published land here.
4-5 = Decent but unremarkable. Gets a basic listing page and goes 
      into the state search archive. No social post.
1-3 = Genuinely unusable — bad/missing data, condemned property, 
      or truly no story to tell. Skip entirely. Use sparingly.

FEATURED LISTING SIGNALS (any combination elevates the score):
- Rural property with acreage, farmland, or lifestyle appeal
- Outbuildings: barn, workshop, carriage house, chicken coop
- Pre-1940 construction with surviving original details
- Brick construction
- Stained glass, ornate staircase, original millwork, pocket doors
- Wraparound porch, turret, Victorian or craftsman details
- New construction at a price that seems impossible
- Unusually large (4+ BR or 2000+ sqft) for the price
- Significant land (1+ acre) at low per-acre cost
- Pool, large garage, or unusual amenity at this price point
- Waterfront, mountain, or highly desirable natural setting
- Historic district or documented community/American history
- Price per sqft dramatically below comparable market
- The kind of home that makes someone imagine a different life

DESCRIPTION QUALITY (affects score in both directions):
The agent description is the raw material for the narrative. A rich description
with specific features, named amenities, local context, or historical detail
produces a materially better post — score it higher. A bare-bones or missing
description produces a thinner post regardless of the property's actual quality —
score it lower, not because the home is worse, but because we can't write the
story it deserves without the details.

Rich description signals (elevate score 1-2 points):
- Named local amenities, landmarks, towns, bodies of water
- Specific renovation details ("roof replaced 2023", "original hardwood refinished")
- Historical context or provenance ("built by the town's first mayor")
- Lifestyle details ("walking distance to the farmers market", "canoe included")
- Interior specifics that paint a scene ("bar for chatting over while the cook finishes")

Thin description signals (lower score 1 point):
- Three sentences or fewer with no specific detail
- Pure spec sheet ("3BR 1BA 1200 sqft good condition")
- No mention of neighborhood, surroundings, or lifestyle context
- Missing description entirely

AUTOMATIC DISQUALIFIERS (lower score significantly):
- Visibly declining neighborhood with no redemptive narrative
- Generic tract home, no architectural character
- Property description reads as purely transactional with no story
- Condition appears to require major structural work with no upside

Listing data:
ADDRESS: [address]
CITY/STATE: [city, state]  
PRICE: [price]
BEDS: [beds] | BATHS: [baths] | SQFT: [sqft] | YEAR BUILT: [year]
LOT SIZE: [lot_size]
PROPERTY TYPE: [type]
FEATURES/TAGS: [features]

AGENT DESCRIPTION (for research — never quote directly):
[agent_description]

Respond in exactly this format:
SCORE: [1-10]
FEATURED: [YES/NO]
CATEGORY: [What If / Too Good To Be True / Time Machine / Hidden Gem / Skip]
REASON: [One sentence on why this listing does or doesn't make the cut]
KEY HOOKS: [Comma-separated list of the 3-5 most compelling things 
            about this listing to emphasize in the narrative]
```

**How the score routes the pipeline — targeting 8-10 posts/day:**

| Score | Tier | Action | Target volume |
|---|---|---|---|
| 8-10 | Hero Featured | Homepage carousel + social reel + email send | 2-3/day |
| 6-7 | Standard Featured | Homepage grid + social text post | 5-7/day |
| 4-5 | Archive | Listed on site, state search only, no social | Unlimited |
| 1-3 | Skip | Not published | Rare |

**Volume calibration:** The API pulls 50-100+ new listings/day nationally under $150K. Scoring 6+ captures enough to sustain 8-10 daily posts while maintaining quality. If daily volume drops below target, the score floor can be lowered to 5+ without meaningfully impacting brand quality — a 5 is still a legitimate listing worth covering.

The KEY HOOKS output passes directly into the content generation prompt, telling it what angles to emphasize. Scoring and hook extraction happen in a single lightweight call — only Hero and Standard listings trigger the full content generation call.

---

### Content Generation Prompt Template

The Cowork prompt is the core intellectual property of the pipeline. It runs for every listing and produces all content variants in a single pass. Stored and version-controlled in `/prompts/deals-under-150k.md` in the GitHub repo.

**Input the prompt receives for each listing:**
- Address, city, state, location display (e.g. "Milwaukee, Wisconsin")
- Price (raw number), price display (e.g. "105,000"), year built
- Bedrooms, bathrooms, square footage, lot size
- Listing URL, affiliate tracking URL
- Agent's listing description (scraped from the listing page)
- **CATEGORY** from the scoring pass (What If / Too Good To Be True / Time Machine / Hidden Gem)
- **KEY HOOKS** from the scoring pass — the 3-5 most compelling angles to emphasize

**How the scoring output shapes the narrative:**

The CATEGORY tells the writer what kind of story this is. The KEY HOOKS tell it what to emphasize. A "What If" listing leads with the lifestyle fantasy. A "Time Machine" listing leads with the architectural details. A "Too Good To Be True" listing leads with the disbelief at the value. The KEY HOOKS ensure the most interesting things about each listing are front and center, not buried.

**How the agent description is used:**

The agent's description is treated as research material only — never quoted directly. It is read for factual hints: specific renovations, neighborhood context, unique features, urgency signals. Claude extracts the interesting facts and rewrites everything in the site's voice. This mirrors standard journalistic practice (reading a press release, writing your own story) and keeps all generated content fully original.

**The prompt:**

```
You are a writer for HousesUnder150K.com — a site that finds incredible 
real estate deals under $150,000 that most people never see. Your voice 
is enthusiastic but credible, like a knowledgeable friend who spotted an 
amazing deal and can't wait to tell you about it. Never hype, never fluff 
— just honest, specific, compelling storytelling about why this property 
is worth attention.

You have been given the following listing data:

ADDRESS: [address]
CITY/STATE: [city], [state_full] (e.g. Milwaukee, Wisconsin)
PRICE DISPLAY: $[price_display] (e.g. $105,000)
BEDS: [beds] | BATHS: [baths] | SQFT: [sqft] | YEAR BUILT: [year]
LOT SIZE: [lot_size]
LISTING URL: [url]
AFFILIATE LINK: [affiliate_url]

EDITORIAL CATEGORY: [category from scoring pass]
(What If = lifestyle fantasy / Too Good To Be True = impossible value /
Time Machine = historic character / Hidden Gem = underrated charm)

KEY HOOKS (the most compelling things about this listing — lead with these):
[key_hooks from scoring pass]

AGENT DESCRIPTION (for research only — extract facts, never quote directly):
[agent_description]

Your job is to make someone stop scrolling. Not because this is cheap —
because this is the kind of thing people forward to their friends and say
"can you believe this exists?" Let the KEY HOOKS drive the narrative angle.
A What If listing leads with the life someone could live here. A Time Machine
listing leads with what survived that shouldn't have at this price. A Too Good
To Be True listing leads with the disbelief. A Hidden Gem leads with what makes
this place worth more than it costs.

Produce the following four outputs:

---

1. HEADLINE
One punchy headline under 10 words. Lead with the hook from KEY HOOKS —
never the address. Make someone want to click before they've read anything else.
Examples: "A 4BR Farmhouse on 3 Acres. $94,000." or "1891 Brick Victorian.
Original Stained Glass. $87K." or "Brand New Construction in Milwaukee: $105,000."

2. NARRATIVE POST (300-400 words)
Tell the story. Structure:
- Opening hook (1-2 sentences) — the thing that stops the scroll. Lead with
  the most surprising or compelling element from KEY HOOKS.
- The property details — woven into narrative, never a spec sheet. Make the
  reader see it.
- Location context — what is this place, what's the life here like
- The angle — who is this for and why does it matter to them
- Closing — honest urgency, never manufactured hype
End with exactly: "See the full listing here → [AFFILIATE_LINK]"

3. SOCIAL CAPTION (under 60 words)
Written for Facebook. The first line must stop the scroll — it's the only
line most people will read. Lead with the most surprising fact. Include price
and location. End with a reason to click to the website. Never use hashtags.
Write like a person, not a brand.

4. SHORT SUMMARY (1-2 sentences, under 30 words)
Used as the listing card preview on the website homepage carousel.
Lead with the single most compelling thing. Make someone want to read more.

---

Return all four outputs clearly labeled. Nothing else.
```

### Voice & Tone — The Editorial Benchmark

**Reference site:** theoldhouselife.com by Michelle Bowers

This is the editorial voice standard for all content generation. Study it. The site gets enormous Facebook traffic and following because the writing makes people feel something — not informed, not convinced, but *there*.

**What her actual posts look like — the real format:**

After reading her posts directly, her voice is simpler and more honest than expected.
She writes like she's texting a friend about a house she found. Short reaction at the top,
then the listing details, then the agent description lightly rewritten or sometimes quoted
directly from the source.

Example from a real post (1934 Tudor on 6 acres, North Carolina, $365,000):
> "Such a unique house! And that price seems great! This home was built in 1934.
> It is located on 6.13 acres in Clinton, North Carolina. This Tudor style home
> originally started as a log cabin. The home has an additional 550 square feet
> in the guest quarters. There are hardwood floors, exposed beams and multiple
> fireplaces. There is a double car garage, courtyard and the property is surrounded
> by a brick privacy wall. Three bedrooms, two bathrooms and 3,361 square feet."
>
> Then: "From the Zillow listing:" followed by the agent description verbatim.
> Then: "Let them know you saw it on Old House Life!"

**What this reveals:**

The writing is NOT a 400-word crafted essay. It is:
1. A short, genuine, enthusiastic reaction (2-4 sentences)
2. The key facts woven together naturally (not a spec list)
3. The agent description — rewritten in her voice OR quoted directly with attribution
4. A simple CTA

The magic isn't elaborate prose. It's **genuine enthusiasm + specific facts + the right
listing.** The house does most of the work. Her job is to get out of the way and let it.

**Voice principles that actually apply:**

- **Genuine excitement, briefly expressed.** "Such a unique house!" reads as real because
  it IS real. She actually loves these houses. That authenticity is not replicable by
  formula — but it can be approximated by writing short and letting the facts lead.

- **Conversational, not editorial.** She's not a journalist writing a feature. She's a
  person who found something and wants to show you. That register — discovery, sharing,
  informal — is what drives the Facebook following.

- **The listing details ARE the narrative.** She doesn't invent lifestyle scenes. She
  surfaces the most interesting facts from the listing and presents them clearly. The
  1934 log cabin that became a Tudor is interesting. She just has to say that.

- **Short sentences. Specifics. Real numbers.** "6.13 acres." Not "over six acres."
  The precision signals she actually looked at this.

- **Zero inflation.** She doesn't oversell. "That price seems great!" is honest hedging,
  not superlatives. The understatement makes the reader trust her more.

**What this means for our content prompt:**

The prompt should NOT try to generate long-form lifestyle essays. It should generate:
- 2-4 sentence genuine reaction that highlights the single most interesting thing
- The key facts in natural flowing sentences (not a bullet list)
- A lightly rewritten version of the agent description in first-person enthusiastic voice
- A clear CTA line

Shorter is better. The house is the content. The writer is the curator.

**Voice applied by category:**

*What If listings:*
Lead with the life detail that makes it feel real. "Six acres and a barn in Southern
Illinois. $94,000." Then the facts. Let the image do the rest.

*Time Machine listings:*
Lead with what survived. "The original hardwood floors. The pocket doors. The staircase
someone spent months building. Still here. 1891." Then the facts.

*Too Good To Be True listings:*
Lead with the disbelief. "Brand new. $105,000. Milwaukee. Yes, really." Then the facts.

*Hidden Gem listings:*
Lead with the discovery. "Not sure how this one is still available." Then the facts.

**What to avoid:**

Bad:
> "This stunning 1927 waterfront home offers an incredible opportunity to experience
> lakeside living at an unbeatable price point in today's competitive market."

Good:
> "Waterfront. Circa 1927. Minnesota. $289,000. There's a dock. There's a boathouse.
> This one has been sitting in my saved searches for a week."

---

**Key principles baked into the prompt:**
- CATEGORY and KEY HOOKS from the scoring pass shape every narrative — no generic content
- Voice is second person present tense — the reader is already the owner
- Specific proper nouns always — name the town, the river, the trail, the feature
- Zero real estate language — no "nestled," no "rare find," no "move-in ready"
- Earn the lifestyle sell — specifics before aspiration, credibility before dream
- Agent description is research material only — extract facts, never quote directly
- Four outputs in one pass — headline, narrative, social caption, and card summary
- State written in full ("Wisconsin" not "WI") for warmth and SEO
- "Write like a friend who found this" — not a brand, not a marketer, not an algorithm
- "Never use hashtags" — posts that look human get more organic reach
- Affiliate link injected directly into narrative — no post-processing needed

### Listing Lifecycle — Sold Property Handling

A sold listing that still appears on the site destroys trust. Users clicking through to a listing that's already gone don't come back. Removing sold listings promptly is as important as adding new ones.

**CMS Status field — four states:**

| Status | Homepage | State page | Listing page | Social |
|---|---|---|---|---|
| Active | ✅ Shown | ✅ Shown | ✅ Full listing | ✅ Eligible |
| Pending | ✅ Shown (flagged) | ✅ Shown | ✅ With "Under Contract" badge | ❌ No new posts |
| Sold | ❌ Removed | ❌ Removed | ✅ "This property has sold" page | ❌ |
| Expired | ❌ Removed | ❌ Removed | ❌ Unpublished | ❌ |

**The sold listing page — don't 404, redirect the intent:**

When a listing sells, the page doesn't disappear — it converts:

```
"This property has sold.

It went fast — that's what happens with deals like this.

See more homes under $150K in Wisconsin →"
[Link to /states/wisconsin]
```

The user came looking for deals in Wisconsin. Give them more Wisconsin deals. A sold listing page becomes a funnel back into the site rather than a dead end. Keeps the SEO juice, doesn't strand the visitor.

**Automated removal — how it works in the pipeline:**

**POC (before API integration):**
A Cowork scheduled task runs once daily alongside the posting pipeline. It takes the list of all Active listing URLs, checks each one on Realtor.com, and updates the CMS status if the listing shows as sold, pending, or removed. Simple web fetch + status check.

**Full platform (after API integration):**
Repliers fires a webhook when a listing status changes. Cowork receives it, matches it to the CMS item by MLS number or address, updates status immediately. Near real-time removal — typically within hours of a sale.

**Pipeline rule — absolute:**
No listing with Status = Sold or Expired ever appears in homepage carousel, state pages, or social posts. The Cowork content generation task filters on `status = Active` before selecting listings to feature. This is enforced at the query level, not left to judgment.

---

### Site Structure

```
housesunder150k.com/                    Homepage — Deal of the Day hero + featured grid
housesunder150k.com/deal-of-the-day/   Today's single best listing — changes daily
housesunder150k.com/listings/[slug]    Individual listing page (all listings)
housesunder150k.com/states/            State index — browse all 50 states
housesunder150k.com/states/[state]     State page — all listings in that state
housesunder150k.com/about/             About page
```

**Revenue by page type:**

| Page | Traffic source | Revenue |
|---|---|---|
| Homepage | Social + direct | Email signups + affiliate clicks |
| Deal of the Day | Social reel + email + direct | Highest affiliate conversion — most motivated visitors |
| Listing pages | Google search (long-tail) | Affiliate clicks (passive) |
| State pages | Google search ("homes under 150k in X") | Affiliate clicks (passive) |
| About | Direct | Trust building |

State pages are the sleeper revenue driver. A state page for Ohio with 200 current listings under $150K, updated daily, will rank for high-intent search terms over time with zero additional effort.

### Email Subscription Tiers

Managed via Beehiiv. Free and paid tiers handled natively. The recommendation
network grows the list organically across similar newsletters.

**Tier structure:**
```
Free — no signup
    Browse the site. No email needed.

$1/month — All Listings Early Access ("The Full List")
    Every listing 24-48 hours early. Volume investors.
    Too cheap to cancel — extremely low churn.

$2/month — Featured + Deal of the Day ("The Deals List")  
    Curated signal only. Serious investors and homebuyers.
    Consider raising to $5/month at scale.
```

**Why this works:**
The $2 tier is actually more valuable than the $1 tier to serious investors.
They do not want to sort through everything — they want the pre-screened best.
Pricing it higher than the full-list tier is correct and defensible.

At 1,000 paid subscribers at $2/month: $2,000/month recurring, zero marginal cost,
completely independent of ad rates and traffic fluctuations.

### Deal of the Day Feature

One listing per day. The single highest-scoring listing from the pipeline run.
Gets the full hero treatment across every channel simultaneously.

**Why this is the anchor feature:**
Michelle Bowers at The Old House Life built her entire following around this concept.
It gives people a reason to come back daily. It gives the social algorithm a
consistent posting pattern to reward. It gives email subscribers a daily hook that
justifies the subscription.

**Pipeline behavior:**
- Scoring prompt flags the highest-scoring listing of the day (score 9-10)
- Pipeline sets `deal-of-the-day: true` on that CMS item
- Previous day's Deal of the Day flag is cleared
- Only one listing has this flag true at any time

**Distribution:**
- Dedicated page `/deal-of-the-day` — always shows current deal
- Homepage hero slot #1
- Social reel + text post at peak time (7-8pm CT)
- Email to ALL subscribers including free tier — the daily hook that drives signups

**The free email hook:**
The Deal of the Day email goes to everyone including free subscribers. It is the
reason people sign up. The paid tiers get early access and the full list. The free
tier gets the daily best — which is enough to grow the list and convert some to paid.

---

### POC Success Criteria

- **30 days:** 60+ posts live, first affiliate clicks registering, Facebook page growing organically
- **60 days:** Consistent affiliate revenue, data on which listing types convert best
- **90 days:** $200-500/mo affiliate revenue, ready to automate Facebook video reels, add second theme

### POC → Full Platform

Once the POC is profitable, revenue funds the full platform build — central content database, consumer app, analytics service, video pipeline, multi-theme command center. Nothing from the POC is wasted: the WordPress site becomes Theme 1, the Cowork prompt becomes the content generation template, the n8n workflow becomes the social publishing layer.

---

## Build Phases

**Phase 1 — Foundation & Validate (Months 1–2)**
Build the central content database and API with the full final schema — users, tiers, listings, themes, content records, timestamps — even though only a fraction will be used yet. Single theme. Listings flowing, content generating, website live, one social account set active. Cowork Scheduled Tasks handle generation and publishing. Mobile oversight via phone notifications. Goal: prove content quality and engagement before scaling anything.

**Phase 2 — Revenue Validation (Months 3–4)**
Affiliate links active across all content. Email list live and growing. Website ad revenue beginning. Identify which content formats and themes drive the most clicks, page views, and conversions. Optimize before cloning. Subscription billing infrastructure (Stripe for web) integrated and tested.

**Phase 3 — Consumer App & Video (Months 5–6)**
Consumer iOS/Android app launched — reads from the same database already live. Free and premium tiers active. RevenueCat integrated for mobile subscriptions. Video reel pipeline comes online. 2–3 additional themes launched from the same infrastructure. Command center dashboard matures.

**Phase 4 — Scale (Months 7–10)**
5+ themes running. Full automation at target posting volume. All revenue streams active and compounding. App store presence established with reviews and ratings accumulating.

**Phase 5 — Platform (Months 11–12)**
Infrastructure mature enough to evaluate white-label or SaaS licensing. Revenue covering costs with meaningful margin. Asset value of individual themes assessable if any are candidates for sale.

---

## Analytics Backend — Separate Service

### Overview

The analytics layer is architecturally independent from the content platform. It is designed from day one to be a standalone, sellable data product — not an internal reporting tool that happens to be extractable later.

The analytics service has its own database, its own API, and its own query surface. It does not reach into the content platform database. It only knows what the content platform tells it, delivered through a structured event pipeline.

This separation means:
- The analytics service can be sold, licensed, or white-labeled independently
- A buyer gets a complete, self-contained data product with a defined ingest spec
- The event pipeline spec is the contract between the two systems — any platform that emits compliant events can feed the analytics service
- The content platform's internal database schema can evolve without breaking the analytics layer

---

### The Event Pipeline

The content platform emits structured, typed events at every meaningful user interaction. The analytics service consumes these events asynchronously — the content platform fires and forgets, the analytics service processes and stores.

**Event structure (every event shares this envelope):**

```json
{
  "event_id": "uuid",
  "event_type": "listing_saved",
  "emitted_at": "ISO8601 timestamp",
  "platform": "app_ios | app_android | web",
  "session_id": "uuid",
  "user_context": {
    "user_id": "anonymized identifier",
    "tier": "free | premium",
    "account_age_days": 14,
    "geography": "state/region — not PII"
  },
  "listing_context": {
    "listing_id": "internal ID",
    "price": 87500,
    "year_built": 1923,
    "property_type": "single_family",
    "state": "OH",
    "market": "midwest_rural",
    "theme": "deals_under_100k"
  },
  "event_payload": {
    // event-type specific fields
  }
}
```

**Event taxonomy — what gets tracked:**

| Event | Payload |
|---|---|
| `listing_viewed` | dwell_time_seconds, scroll_depth_pct, source (social/email/direct/search) |
| `listing_saved` | — |
| `listing_shared` | platform shared to |
| `affiliate_click` | destination (zillow/realtor/other) |
| `email_opened` | theme, subject_line_variant |
| `email_clicked` | link_type, listing_id |
| `social_post_engaged` | platform, post_type (reel/image/text), action (like/share/comment/click) |
| `app_search_performed` | filters applied (price range, location, property type) |
| `filter_saved` | filter definition |
| `subscription_started` | plan, acquisition_source |
| `subscription_cancelled` | tenure_days, cancellation_reason if provided |
| `push_notification_opened` | listing_id, time_since_sent |
| `content_rated` | rating, listing_id |

Every event is enriched at emission time with user and listing context — so the analytics service never needs to join back to the content database to answer questions.

---

### Analytics Database Design

Separate from the content database. Optimized for analytical queries, not transactional reads. High write volume, low-latency batch reads.

**Candidate approaches (to evaluate):**
- Columnar store for event data (ClickHouse — open source, self-hostable, extremely fast for aggregations)
- TimescaleDB (PostgreSQL extension — familiar if already on Supabase)
- BigQuery or Snowflake for fully managed option

**Core tables:**

```
events          — every raw event, partitioned by date
listings_dim    — listing attribute snapshot at time of event (slowly changing dimension)
users_dim       — anonymized user attribute snapshot (tier, geography, cohort)
sessions        — session-level aggregations
daily_rollups   — pre-aggregated metrics by theme/market/property_type/date
```

Raw events are immutable. Rollups are computed on schedule and cached for fast API response.

---

### What the Data Captures (Market Value)

This dataset is valuable because it is **behavioral and intent-based**, not transactional. Zillow has transaction data. They do not have engagement and intent signals from a curated deal-hunting audience. That is a complementary, differentiated signal.

**Signals with real market value:**

- **Search intent by geography** — which markets are generating disproportionate attention before it shows up in price or volume data
- **Price sensitivity thresholds** — which price points generate engagement spikes (the market's psychological anchors)
- **Property attribute engagement** — which characteristics (age, style, condition, lot size) drive saves, shares, and affiliate clicks
- **Deal recognition patterns** — how quickly users engage with underpriced listings vs. market-rate listings
- **Audience segmentation** — behavioral clusters within the user base (flipper vs. primary buyer vs. curious browser)
- **Content format performance** — which narrative angles and post formats drive the highest affiliate conversion by market
- **Premium conversion signals** — what behavior in the free tier predicts subscription conversion

---

### Analytics API

The analytics service exposes its own API — separate from the content platform API. This is what data buyers license.

**Query surfaces:**

- **Aggregate trend endpoints** — "what markets saw the biggest engagement spike last 30 days"
- **Property attribute affinity** — "which property characteristics correlate with highest affiliate click rate"
- **Audience segment profiles** — anonymized behavioral cohort definitions
- **Time-series feeds** — rolling metrics exportable for external modeling
- **Custom report builder** — configurable queries within defined parameters (for enterprise data buyers)

All responses are aggregated and anonymized. No individual user data is ever exposed. Minimum cohort sizes enforced on every query (e.g., never return data for fewer than 100 users — prevents re-identification).

---

### Data Monetization Model

**1. Direct Data Licensing**
Sell aggregated behavioral datasets to PropTech companies, real estate platforms (Zillow, Realtor.com, CoStar), brokerages, and hedge funds on a subscription basis. Quarterly or annual contracts.

**2. Market Intelligence Reports**
Publish periodic "what's getting attention" reports — which markets, price points, and property types are trending in engagement — as a premium standalone product.

**3. Analytics API Access**
Tiered API subscription for data buyers who want to query directly rather than receive static datasets. Higher margin, lower operational overhead than custom reports.

**4. Audience Targeting Segments**
Package behavioral segments (e.g., "actively searching sub-$100K in Midwest") as targetable audiences for real estate advertisers. Sell access to reach these segments on your own platforms.

**5. White-Label Analytics**
License the analytics service + event pipeline spec to other real estate content operators who want the same insight layer on their own platforms. Feeds your dataset while generating licensing revenue.

---

### Privacy & Compliance Architecture

This must be correct from day one — it cannot be retrofitted after users are onboarded.

- **Anonymization at emission** — user_id in events is a one-way hashed identifier, never the raw account ID. The mapping exists only in the content platform and is never sent to the analytics service.
- **No PII in the event pipeline** — names, emails, phone numbers, and precise addresses never enter the analytics database
- **Aggregation thresholds** — all API responses enforce a minimum cohort size (100+ users) to prevent re-identification
- **Consent language** — Terms of Service and Privacy Policy must explicitly disclose behavioral analytics and data product usage before any user account is created
- **Data residency** — analytics database hosted in US; evaluate whether EU expansion requires a separate instance for GDPR
- **CCPA compliance** — deletion requests from the content platform must propagate to the analytics service via a separate deletion event that purges or anonymizes that user's event history
- **Retention policy** — raw events retained for defined window (e.g., 24 months), then rolled up and purged

---

### How the Two Systems Connect

```
CONTENT PLATFORM                    ANALYTICS SERVICE
─────────────────                   ─────────────────
User interacts with app/site
        ↓
Event emitted to queue ──────────→  Queue consumer picks up event
(fire and forget)                           ↓
                                    Validate against event schema
                                            ↓
                                    Enrich if needed (lookup listing
                                    attributes from events_dim cache)
                                            ↓
                                    Write to events table
                                            ↓
                                    Rollup jobs aggregate on schedule
                                            ↓
                                    Analytics API serves buyers
```

The queue is the only coupling point between the two systems. If the analytics service goes down, the content platform is unaffected — events queue and are processed when the service recovers. If the content platform changes its internal schema, only the event emission layer needs to be updated, not the analytics service.

---

## Supplementary Free & Open APIs

Beyond the core paid infrastructure, a layer of free public APIs can reduce costs and power specific features. These do not replace the core listing data feed but add significant value on top of it.

**Geocoding & Location Enrichment (free)**
Multiple free geocoding APIs (Geocode.xyz, GeoJS, ip-api) can convert listing addresses to coordinates, neighborhood context, and reverse geocoding. Powers map features in the consumer app and enriches analytics events with geographic metadata at zero cost.

**US Government APIs (free) — High Value for Historical & Narrative Themes**
A single Data.gov API key unlocks a network of federal data sources including Census.gov, USGS, Smithsonian, National Park Service, USDA, EPA, and more. Specific uses per theme:

- Census.gov: demographic data by address, neighborhood characteristics, housing stock age by census tract — automatic "what is this neighborhood" narrative context
- USGS: land records, surveys, topographic and historical map data — feeds rural, land, and small town themes
- EPA: environmental data per location — relevant for land, acreage, and off-grid themes
- Smithsonian / National Park Service: historical context for properties near landmarks or in historically significant areas

This is the free data layer that powers the "this 1887 Victorian was built by a railroad baron" content angle without paying anyone. It is a meaningful competitive differentiator — most competing pages don't use it.

**Video Delivery & Transcoding — Cloudinary (free tier)**
Cloudinary handles upload, storage, encoding, and CDN delivery of video. It is not an AI video generator, but it is a strong candidate for the delivery layer between AI-generated video and social platforms — handling format conversion and resizing for different aspect ratios (9:16 for TikTok/Reels, 1:1 for feed posts). Free tier is generous. Reduces dependence on social platform upload APIs.

**Social Engagement Data — SharedCount (free tier)**
Returns social engagement metrics (shares, likes) per URL. Useful for the analytics layer to passively measure content performance across platforms without scraping, at no cost.

**Text Analysis / NLP (free tiers)**
Free NLP APIs for entity extraction and keyword analysis can auto-tag listings by theme affinity — helping the filter engine route listings to the right themes automatically based on property description text.

**Notable Candidate — RealEstateAPI.com**
Offers MLS listings, property valuations, demographics, mapping, skip tracing, address verification, and an MCP server integration — meaning it can potentially connect directly into a Claude-based pipeline. Worth evaluating alongside Repliers as the core listing feed. Caveat: independent reviews note data accuracy issues at scale (incorrect property types, inconsistent county recording data). Requires hands-on testing before committing.

**What free APIs do NOT cover**
Social media publishing automation, production-quality video generation, and the core MLS listing feed all remain paid layers. No viable free path exists for these at production quality and volume.

---

## Open Questions & Investigation Items

---

**Data & Listings**
- Which listing API offers the best coverage, filtering, and webhook support at the lowest cost?
- Are there viable open-source MLS connectors or RETS feed tools worth evaluating before committing to a paid API?
- What are the exact current terms and payout structures of Zillow and Realtor.com affiliate programs?

**Content Generation**
- What is the most cost-effective video generation pipeline at volume? Is a self-hosted ffmpeg + open-source TTS + slideshow approach sufficient quality for reels, or is commercial AI video worth the cost?
- Are there open-source LLM options viable for narrative generation at volume to reduce Claude API costs at scale?

**Social Publishing**
- Can direct Meta Graph API + TikTok Content Posting API integrations replace a social publishing middleware service entirely, eliminating that cost layer?
- How does platform algorithm behavior differ between automated and manual posting? Risk of throttling or shadowbanning at volume?

**Email**
- What open-source email list tools (e.g., Listmonk — self-hosted, free) are viable at scale vs. managed services?

**App & Website**
- React Native (Expo) vs. Flutter for the consumer app — which better fits the team's existing skills and the deployment target?
- Theme site infrastructure: shared Next.js app with subdomain/domain routing, or independently deployed sites managed by the platform?
- How does RevenueCat handle subscription state sync edge cases (refunds, family sharing, grace periods)?

**Database & API**
- What job queue system best fits the content generation workload — BullMQ, Inngest, Trigger.dev, or a simpler cron-based approach for early stages?
- Can the ShowFlyer Supabase instance be shared or should this be a separate project from the start?

**Analytics Service**
- ClickHouse vs. TimescaleDB vs. managed options (BigQuery/Snowflake) — what is the right analytical store given self-hostability, cost, and query performance requirements?
- What message queue is best suited for the event pipeline — Kafka, Redis Streams, or a lighter option like Inngest for early stages?
- What minimum user base size makes the analytics data commercially interesting to a data buyer like Zillow or a PropTech firm?
- How do CCPA deletion propagation requirements affect event storage — partial anonymization vs. full purge?
- What does a data licensing agreement with a buyer like Zillow or Realtor.com actually look like — are there existing frameworks or does this require custom legal work?

**Business**
- What does the App Store and Google Play review process look like for a real estate content app with in-app subscriptions?
- At what audience size does each social platform's monetization program become accessible?
- At what point does the analytics dataset have enough depth and breadth to approach data buyers?

---

*This document is a concept snapshot. Stack decisions are illustrative and subject to change based on further research, open-source discovery, and cost modeling before development begins.*
