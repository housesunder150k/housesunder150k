# HousesUnder150K.com — POC Build Status
*Last updated: July 25, 2026*

---

## Project Overview

**Domain:** housesunder150k.com (registered on Cloudflare, ~$9.77/yr)
**Platform:** Webflow (Basic plan needed, $14/mo — not yet upgraded)
**GitHub:** github.com/housesunder150k/housesunder150k
**Webflow Site ID:** `6a650a7eb2639262c4b6adb7`
**Webflow Designer:** https://housesunder150k.design.webflow.com

**Concept:** Automated real estate content platform surfacing listings under $150K. Discovers listings via API, scores them editorially, generates AI narrative content, publishes to website and social media. Monetizes via affiliate links (Realtor.com, loan partners), email subscriptions, and display advertising at scale.

---

## Current Build State

### ✅ Complete

#### Webflow — Homepage (`6a650a80b2639262c4b6adba`)
- Nav — house SVG logo + "Houses" white + "Under 150K" cyan, links, Subscribe button (cyan)
- Hero section — "REAL HOMES. REAL DEALS." large serif headline, subtext, "See Today's Deals →" CTA
- Latest Deals section — "Latest Deals" heading with cyan left border accent
- CMS Collection List — native Webflow, bound to Listings collection, filtered `Status = Active`, limit 12, newest first, responsive 3/2/1 column grid
- Card template inside collection — location display (cyan caps), image placeholder, short summary, "View Listing →" CTA link to listing page
- Subscribe section — "Get Deals First." with email capture form
- Footer
- Mobile responsive — headline scales correctly across breakpoints (120px → 72px → 52px → 44px)

#### Webflow — Listing Template Page (`6a650bab14666c3157f2761e`)
- Full native Webflow element build — zero WHTML, all elements CMS-bindable
- Nav — matching homepage logo, links, Subscribe button
- Hero section — full-width image slot (480px desktop, 300px mobile), gradient overlay, price overlay bottom-left
- Price display — `$` in cyan (42px) + formatted number in white (72px), Space Mono font, flex row aligned to baseline
- Content area — max-width 800px, centered, 48px top padding
- "← Back to Latest Deals" nav link
- Meta bar — Location Display (cyan uppercase) + Address (white) left, Beds/Baths/Sqft/Year Built specs right
- H1 headline — bound to Name field
- Rich text narrative body — bound to Narrative Body field
- CTA block — dark card, "VIEW ON REALTOR.COM" label, "See Photos, Map & Full Details" heading, "View Full Listing →" cyan button bound to Affiliate URL
- Footer — logo left, copyright right
- Mobile responsive — hero 300px, price scales to 36/48px, content padding reduces

#### CMS — Listings Collection (`6a650bab14666c3157f27618`)

| Field | Type | Slug | Field ID | Notes |
|---|---|---|---|---|
| Name | PlainText | `name` | `2d0b39c8706c5aeb8a5d10eb7c7b0ba5` | Listing headline |
| Slug | PlainText | `slug` | `3eff577466e8ac4d1f5673c6ba5067f0` | URL slug |
| Price | Number | `price` | `e3e0fbae7e82729a2d40cfd88b8553ad` | Raw number for filtering |
| Price Display | PlainText | `price-display` | `f1701f816e4213ef8979d44f2a9f4ec4` | "105,000" — no $ symbol |
| Location Display | PlainText | `location-display` | `dcbe16cd4151eaab2df0d79d0343ad5e` | "Milwaukee, Wisconsin" |
| Address | PlainText | `address` | `2370642ad45dce9c5cbbf8d6122515dc` | Street address only |
| City | PlainText | `city` | `ab84ae63bb81f7bfe33ccb50cfe9bc25` | City name |
| State | PlainText | `state` | `59074a866f1a7d4bffb208b1a63cd827` | Two-letter abbreviation |
| Year Built | Number | `year-built` | `e16726678f8f43f844c78f4fd226e47c` | |
| Bedrooms | Number | `bedrooms` | `72df5c8c23726e9849fa1520abe59b11` | |
| Bathrooms | Number | `bathrooms` | `ad78567827bc5cc5dbcdbf93379f2c06` | |
| Square Feet | Number | `square-feet` | `326895e4a7b08fc72b760740045e9e8d` | |
| Hero Image | Image | `hero-image` | `c2021ed9588e45e46c85ff883a558c02` | From listing API photos[0] |
| Narrative Body | RichText | `narrative-body` | `fbfb92acd8aeee91d64209f2e905fc5a` | AI-generated, 300-400 words |
| Short Summary | PlainText | `short-summary` | `aec9319d65a89b54b50001e13af0b8c7` | Under 30 words, card preview |
| Listing URL | Link | `listing-url` | `4d428fda04c2feb9db89ef1423343895` | Source listing URL |
| Affiliate URL | Link | `affiliate-url` | `2b37c2a126d49592bd34aa91ed798c26` | Tracking link, CTA target |
| Social Caption | PlainText | `social-caption` | `68cdd4fdfa9a3a1ce86836aaa3617950` | Under 60 words, no hashtags |
| Status | Option | `status` | `6b58bbdff6c0c0e31e17c04e4188f8be` | Active/Pending/Sold/Expired |
| Deal of the Day | Switch | `deal-of-the-day` | TBD — add in Session 2 | Boolean, only one true at a time |

**Status option IDs:**
- Active: `3b41185e9af84f92d8da092965308a2d`
- Pending: `001257c77d3ccd4477d620ac135a4afd`
- Sold: `541de6b6934cd79d6a76c98d91610063`
- Expired: `e630110b6993074e3f7299e8dbb7fdc1`

#### First Real Listing
- **ID:** `6a651620c18a35f707eecb62`
- **Title:** Brand-New Construction in Milwaukee for $105,000
- **Slug:** `brand-new-construction-milwaukee-105000`
- **Address:** 3125 N 24th Pl, Milwaukee, WI 53206
- **Source:** https://www.realtor.com/realestateandhomes-detail/3125-N-24th-Pl_Milwaukee_WI_53206_M99132-09453
- **Status:** Active
- **All fields populated** — narrative, social caption, short summary, price-display, location-display
- **Missing:** hero-image (pending API), affiliate-url (pending affiliate signup)
- **State:** Queued to publish (site not yet published)

#### Concept & Strategy Document
- **File:** `/mnt/user-data/outputs/real-estate-content-platform-concept.md`
- Contains: full business model, editorial philosophy, scoring prompt, content generation prompt, pipeline architecture, revenue model, site structure, sold listing handling, POC success criteria
- **Push to GitHub:** `/docs/concept.md`

---

### ⬜ Not Yet Built

#### Site Pages
- About page (`/about`) — simple one-pager, brand story
- States index page (`/states`) — browse all 50 states
- State pages (`/states/[state]`) — all listings in a given state (SEO + passive affiliate)

#### Listing Template — Additional States
- Sold listing page state — shows "This property has sold. See more in [State] →" when Status = Sold
- Pending badge — "Under Contract" label overlay for Status = Pending

#### Homepage Card Styling
- Price display not visible on card — needs style applied or $ prefix added to price-display binding
- Image placeholder needs defined height and background color
- Card spacing and border-radius polish pass needed

#### Infrastructure
- Webflow Basic plan upgrade ($14/mo) — required for custom domain
- Cloudflare DNS → Webflow (two CNAME records)
- Site publish — currently "Queued to publish"

---

## Design System Reference

### Colors
```
Background:     #0D0D0D  (site bg, near black)
Surface:        #111111  (nav, CTA block bg)
Surface 2:      #1A1A1A  (cards, hero placeholder)
Border:         #2A2A2A  (all dividers and card borders)
Text Primary:   #F5F5F5  (headings, primary content)
Text Secondary: #CCCCCC  (narrative body copy)
Text Muted:     #999999  (nav links, secondary labels)
Text Faint:     #666666  (specs labels, tertiary info)
Text Disabled:  #555555  (footer copy, affiliate note)
Accent Cyan:    #00D4FF  (price $, location, CTA buttons, borders, logo)
CTA Background: #00D4FF  (Subscribe button, View Full Listing button)
CTA Text:       #0D0D0D  (text on cyan buttons)
```

### Typography
```
Body / UI:      Inter, sans-serif
Price display:  Space Mono, monospace (hero price number)
Headline:       System serif (renders as the large editorial serif on homepage hero)
```

### Type Scale
```
Homepage hero:    120px (desktop) → 72px (tablet) → 52px (mobile L) → 44px (mobile P)
Price hero:       $42px cyan / 105,000 72px white (desktop) → 36px/48px (mobile)
Narrative title:  36px (desktop) → 26px (mobile)
Section heading:  28-36px Inter 700
Card location:    13px uppercase, 2px letter-spacing, cyan
Card price:       24px Space Mono cyan
Body narrative:   17px Inter, 1.8 line-height, #CCCCCC
Spec value:       22px Inter 700 white
Spec label:       11px uppercase, 1px letter-spacing, #666666
Nav links:        14px Inter 500, #999999
```

### Style Class Prefixes
```
hu150-*   Homepage elements (hero, nav, deals section, cards, subscribe, footer)
lp-*      Listing template page elements (nav, hero, content, meta, specs, CTA, footer)
```

### Key Style Classes — Homepage (`hu150-*`)
```
hu150-site          Body wrapper, #0D0D0D bg
hu150-nav           Sticky nav, #111111 bg, border-bottom #2A2A2A
hu150-nav-inner     Max-width 1280px, 64px height, flex space-between
hu150-logo          Flex row, gap 10px, no text-decoration
hu150-hero          Full viewport, centered, #0D0D0D bg
hu150-hero-headline 120px serif, line-height 0.92, letter-spacing 2px
hu150-deals         Section, padding 80px 24px
hu150-deals-inner   Max-width 1280px, centered
hu150-cms-list      CSS grid, 3 cols desktop / 2 tablet / 1 mobile, gap 24px
hu150-card          Dark card, #1A1A1A bg, #2A2A2A border, 10px radius, LinkBlock
hu150-card-img-wrap Position relative
hu150-card-img      Width 100%, height 220px, object-fit cover
hu150-card-price    Absolute, bottom-left, Space Mono, 24px, cyan
hu150-card-body     Padding 20px
hu150-card-location 13px, cyan, uppercase, 1.5px letter-spacing
hu150-card-summary  14px, #BBBBBB, 1.6 line-height
hu150-card-cta      13px, cyan, 600 weight
hu150-subscribe     Section, dark bg, centered, padding 96px 24px
```

### Key Style Classes — Listing Template (`lp-*`)
```
lp-site             Min-height 100vh, #0D0D0D bg, Inter font
lp-nav              Sticky, z-index 100, #111111 bg, #2A2A2A border-bottom
lp-nav-inner        Max-width 1280px, 64px height, flex space-between
lp-hero             Height 480px (desktop) / 300px (mobile), relative, overflow hidden
lp-hero-img         Width/height 100%, object-fit cover
lp-hero-overlay     Absolute inset, gradient top-to-bottom rgba(13,13,13,0.92→0.1)
lp-hero-price       Absolute, left 40px / bottom 32px, flex row, align flex-end, gap 4px
lp-price-dollar     42px Space Mono, #00D4FF, inline-block, vertical-align bottom
lp-price-number     72px Space Mono, #F5F5F5, inline-block
lp-content          Max-width 800px, margin auto, padding 48px 24px 80px
lp-back             Inline-flex, #666666, 14px, no underline
lp-meta             Flex, space-between, border-bottom #2A2A2A, margin-bottom 32px
lp-location         13px, #00D4FF, uppercase, 2px letter-spacing
lp-address          18px, #F5F5F5, 600 weight
lp-specs            Flex, gap 20px, flex-wrap
lp-spec             Text-align center
lp-spec-value       22px, #F5F5F5, 700 weight, display block
lp-spec-label       11px, #666666, uppercase, 1px letter-spacing
lp-narrative-title  36px, #F5F5F5, 700, line-height 1.2, margin-bottom 24px
lp-narrative        17px, #CCCCCC, line-height 1.8, margin-bottom 48px
lp-cta-block        #111111 bg, #2A2A2A border, 12px radius, padding 32px, text-center
lp-cta-label        12px, #00D4FF, uppercase, 3px letter-spacing
lp-cta-title        24px, #F5F5F5, 700
lp-cta-sub          15px, #999999
lp-cta-btn          #00D4FF bg, #0D0D0D text, 16px, 700, 8px radius, padding 15px 36px
lp-affiliate-note   12px, #555555
lp-footer           #0D0D0D bg, #2A2A2A border-top, padding 32px 24px
lp-footer-inner     Max-width 1280px, flex space-between
```

---

## Pipeline Architecture

### Two-Call Content Generation

**Call 1 — Scoring (lightweight, runs on every listing):**
```
Input:  listing data + agent description (scraped from listing URL)
Output: SCORE (1-10), FEATURED (YES/NO), CATEGORY, REASON, KEY HOOKS
Prompt: /prompts/scoring-prompt.md
```

**Call 2 — Content Generation (featured listings only):**
```
Input:  listing data + CATEGORY + KEY HOOKS from Call 1 + affiliate URL
Output: HEADLINE, NARRATIVE POST (300-400 words), SOCIAL CAPTION (<60 words), SHORT SUMMARY (<30 words)
Prompt: /prompts/deals-under-150k.md
```

### Voice & Tone Reference — The Old House Life (theoldhouselife.com)

This site is the editorial benchmark. Study it before writing any prompt refinements.

**What she does that works:**

- **Second person, present tense throughout** — "you'll have," "you can," "settle into."
  The reader is already the owner. Not "the new owner will enjoy" — "you will enjoy."

- **Specific proper nouns, always** — Not "outdoor recreation nearby" but "mountain bike
  at Acadia, play pickleball in Brewer." Specificity builds trust and makes the place real.

- **Sensory and tactile details** — "bar for chatting over while the cook finishes boiling
  up the lobster." You hear it, smell it, feel it. Not a spec sheet — a scene.

- **Earns the lifestyle sell** — Details and specifics come first. The dream comes after.
  Credibility precedes aspiration.

- **Zero real estate language** — No "motivated seller," no "open concept," no "move-in
  ready," no "nestled." She writes like a travel magazine, not an MLS sheet.

- **Conversational asides** — "read (or write) a novel." Intimate, human, surprising.
  Makes the reader feel like a friend told them about this place, not a marketer.

- **She makes you feel late** — urgency without hype. The place is real, the price is real,
  and somehow you feel like you're already behind on calling about it.

**The difference in practice:**

Bad (what to avoid):
> "This 1927 waterfront home offers stunning lake views and original character throughout.
> A rare find at this price point in today's market."

Good (the target voice):
> "Wake up to the lake. Make coffee. Decide whether to take the canoe out before or after
> breakfast. This is the question a 1927 Minnesota waterfront home for $289,000 puts in
> front of you every single morning."

**Apply this to every listing category:**

- What If listings → write the specific Saturday morning. What are you doing? Where are
  you going? What does the light look like at 7am on that porch?

- Time Machine listings → put the reader inside the craftsmanship. "The staircase took
  someone months to build. It would cost six figures to recreate today. It's yours."

- Too Good To Be True → make them do the math out loud with you. Walk them through it.
  "Brand new. Never lived in. $105,000. In Milwaukee. We know."

- Hidden Gem → the discovery feeling. "Most people drove past this one."

**The actual Old House Life format (from reading her posts directly):**

Michelle Bowers' posts are simpler than expected — and that simplicity is the point.

Real example (1934 Tudor, 6 acres, NC, $365K):
> "Such a unique house! And that price seems great! This home was built in 1934.
> It is located on 6.13 acres in Clinton, North Carolina. This Tudor style home
> originally started as a log cabin..."
> [then the Zillow description, lightly or directly]
> "Let them know you saw it on Old House Life!"

**The format:**
1. Short genuine reaction — 1-3 sentences of real enthusiasm
2. Key facts in natural sentences — not a spec list
3. Agent description rewritten in her voice
4. Simple CTA

**Update the content generation prompt with this instruction:**
> Write like Michelle Bowers at The Old House Life — not a journalist, a curator.
> Short genuine reaction first (1-3 sentences). Then the key facts in natural
> sentences. Then the agent description rewritten in an enthusiastic conversational
> voice. Specific numbers, specific nouns, zero real estate language. Short sentences.
> Let the house be the content. Get out of the way. End with a clear CTA line.

### Agent Description — The Raw Material

The agent description is where almost all the good content comes from. Kate Devries at
The Old House Life is doing exactly this — taking what the agent wrote and rewriting it
in a voice that makes people feel something.

**Example of the transformation:**

Agent wrote:
> "Ownership includes membership access to the Lucerne Beach Club and a slot on the
> shore for the included Old Town Canoe."

She wrote:
> "a slot on the shore for the Old Town Canoe that comes with the cabin."

Same fact. The canoe isn't a feature — it's already yours. That's the entire job.

**Description quality affects scoring:**

A rich agent description produces a great post. A bare-bones description produces a
thin one — regardless of what the property actually is. The scoring prompt accounts
for this:

Rich description (elevates score 1-2 points):
- Named local amenities, landmarks, towns, water
- Specific renovation details with years ("roof 2023")
- Historical context or provenance
- Lifestyle details, included items, named features
- Interior specifics that paint a scene

Thin description (lowers score 1 point):
- Three sentences or fewer, no specific detail
- Pure spec sheet, no context
- No mention of neighborhood, surroundings, lifestyle
- Missing entirely

**Implication for the pipeline:**
When the Repliers API returns a listing, the pipeline should also scrape the full
agent description from the listing URL before scoring. A listing with a rich
Realtor.com description will consistently outperform one with bare MLS data.
Scraping the description is as important as scraping the specs.

### Scoring Tiers
| Score | Tier | Action | Target Volume |
|---|---|---|---|
| 8-10 | Hero Featured | Homepage carousel + social reel + email | 2-3/day |
| 6-7 | Standard Featured | Homepage grid + social text post | 5-7/day |
| 4-5 | Archive Only | Listing page + state search, no social | Unlimited |
| 1-3 | Skip | Not published | Rare |

### CMS Fields Written Per Listing by Pipeline
```
name            → AI headline
slug            → generated from headline (lowercase, hyphens)
price           → raw number (e.g. 105000)
price-display   → comma-formatted (e.g. "105,000") — no $ symbol
location-display → "City, StateName" full state name (e.g. "Milwaukee, Wisconsin")
address         → street address
city            → city name
state           → two-letter abbreviation
year-built      → integer
bedrooms        → integer
bathrooms       → integer (or decimal e.g. 1.5)
square-feet     → integer
hero-image      → URL from listing API photos[0]
narrative-body  → AI rich text, 300-400 words
short-summary   → AI plaintext, under 30 words
listing-url     → source listing URL
affiliate-url   → Realtor.com tracking link
social-caption  → AI plaintext, under 60 words, no hashtags
status          → "3b41185e9af84f92d8da092965308a2d" (Active option ID)
```

### Sold Listing Handling
- Daily Cowork task checks all Active listing URLs
- If sold/removed: update `status` to Sold option ID `541de6b6934cd79d6a76c98d91610063`
- Sold listings: removed from homepage grid and state pages automatically (filter enforced)
- Sold listing page: shows "This property has sold. See more deals in [State] →" — links to state page
- Never 404 — preserve SEO value, redirect intent to state page

---

## Site Structure
```
housesunder150k.com/                    Homepage — hero + featured grid
housesunder150k.com/listings/[slug]     Individual listing (all listings)
housesunder150k.com/states/             State index — browse all 50 states
housesunder150k.com/states/[state]      State page — all active listings in that state
housesunder150k.com/about/             About page
```

### Revenue by Page Type
| Page | Traffic Source | Revenue Mechanism |
|---|---|---|
| Homepage | Social + direct + email | Email signups + affiliate clicks |
| Listing pages | Google long-tail search | Affiliate clicks (passive) |
| State pages | Google ("homes under 150k in ohio") | Affiliate clicks (passive) |
| About | Direct | Trust building |

---

## Affiliate Stack
| Program | Commission | Network | Status |
|---|---|---|---|
| Realtor.com | $5/lead | Commission Junction | Not yet applied |
| New Silver (hard money loans) | $50/lead + 0.5% closed | FlexOffers | Not yet applied |
| Fundrise | $50-100/referral | Direct | Not yet applied |
| Buildium (property mgmt) | 25% recurring | Direct | Future |

---

## GitHub Repository
**URL:** github.com/housesunder150k/housesunder150k

**Structure:**
```
/
├── README.md
├── docs/
│   └── concept.md          ← Full concept doc (copy from outputs)
├── prompts/
│   ├── scoring-prompt.md   ← Call 1: editorial scoring
│   └── deals-under-150k.md ← Call 2: content generation
├── posts/
│   └── [slug].json         ← One file per published listing
└── scripts/
    └── (future pipeline scripts)
```

**Pre-session setup required:** Connect Claude Desktop / Cowork to GitHub before Session 2.

---

## Strategic Context — The Bigger Picture

### The Holdco Model

HousesUnder150K.com is not the goal. It is the proof of concept for a media holding
company built on automated content pipelines. The goal is 10 properties running on
autopilot within 12 months, generating $15-25K/month combined, funding full-time
independence and SaaS development.

```
HoldCo
├── HousesUnder150K.com     ← POC, building now
├── Property 2              ← Same pipeline, different vertical
├── Property 3
├── ...
└── Property 10
```

Each property runs the same two-prompt pipeline with different scoring criteria,
voice, and affiliate stack. Setup time per new property decreases with each one
built — the first takes weeks, the fifth takes days.

### The Compounding Effect

Every listing page published is a permanent SEO asset. Running at 8 posts/day:

```
Month 1:   ~240 pages indexed
Month 3:   ~720 pages
Month 6:   ~1,440 pages
Month 12:  ~2,920 pages
```

Traffic at month 12 is not 12x month 1 — it is 40-50x because domain authority,
social following, email list, and indexed pages all compound simultaneously and
feed each other. The pipeline runs the same whether you have 100 pages or 3,000.

### Revenue Trajectory

| Milestone | Timeline | Monthly Revenue |
|---|---|---|
| POC live, first affiliate clicks | Month 1-2 | $0-200 |
| Ezoic/AdSense + early affiliates | Month 2-3 | $200-500 |
| **$1K/month confirmed** | **Month 3** | **$1,000** |
| Mediavine eligible (50K sessions) | Month 4-5 | $1,500-2,500 |
| Sites 2 + 3 live | Month 4-6 | $3,000-5,000 |
| Self-employed threshold crossed | Month 6 | $4,000+ |
| Sites 4-7 running | Month 9 | $8,000-15,000 |
| 10 sites running | Month 12 | $15,000-25,000 |
| SaaS MVP | Month 14-18 | + recurring SaaS |

### The SaaS Play

Once the pipeline is proven across multiple niches, the system itself becomes a
product. Other people want to build automated content media businesses. They cannot
build the pipeline. You will have built it 10 times and know every edge case.

```
Pipeline-as-a-Service
├── Scoring prompt engine (editorial layer)
├── Content generation engine (voice layer)
├── CMS auto-publish (Webflow or WordPress)
├── Social distribution layer
├── Sold/expired monitoring
└── Analytics dashboard
```

This is a SaaS product with a proven customer — yourself — and a clear value
proposition: automated content media with genuine editorial standards, not AI slop.

### The Staffing Model at Scale

At 10 properties, three employees monitor quality and build audience. The pipeline
runs itself. The staff ensures it stays on brand.

```
You — Owner/Architect
├── Pipeline maintenance and improvement
├── New property spinups
├── SaaS development
└── Strategic decisions

Employee 1 — Content Quality Monitor
├── Reviews daily output across 3-4 sites
├── Flags scoring misses and data errors
└── ~4 hours/day, part time to start

Employee 2 — Community & Social
├── Responds to Facebook comments
├── Manages email lists
└── Builds the audience relationship the algorithm cannot fake

Employee 3 — SEO & Analytics
├── Monitors rankings and traffic trends
├── Identifies content gaps by state/market
└── Reports what is working across all properties
```

Three people watching 10 automated pipelines. Most media companies at this revenue
level run 8-12 employees. The pipeline is the leverage.

### Email Subscription Model

Managed via **Beehiiv** — handles free/paid tiers natively, newsletter analytics,
and a recommendation network that grows the list organically.

```
Free tier — no signup required
    Browse the site. See what's live. No email needed.

$1/month — All Listings Early Access ("The Full List")
    Every listing published, 24-48 hours before it hits the site.
    Targeted at volume investors who want first look at everything.
    High churn resistance — too cheap to bother canceling.

$2/month — Featured + Deal of the Day ("The Deals List")
    Only the curated picks — score 6+ listings and the daily Deal of the Day.
    Pre-screened signal, not noise. Homebuyers and serious investors.
    Consider $5/month at scale — 1,000 subscribers = $5,000/month recurring.
```

**Revenue math on email alone:**
| Subscribers | Tier | Monthly |
|---|---|---|
| 500 | $1/month mix | $500 |
| 1,000 | $2/month mix | $2,000 |
| 2,000 | $2/month mix | $4,000 |
| 5,000 | $3 blended | $15,000 |

Email revenue is completely independent of traffic and ad rates. It compounds
with the audience, doesn't decay, and has near-zero marginal cost to deliver.

**Beehiiv integration:**
- Subscribe button on homepage connects to Beehiiv
- Pipeline writes social caption and short summary per listing
- Beehiiv daily digest pulls Featured listings automatically via RSS or API
- Deal of the Day gets its own dedicated send at 8am

### Deal of the Day

Michelle Bowers' highest-traffic feature. One listing per day — the absolute
best score from the pipeline — gets the full hero treatment.

**CMS addition needed:**
- Add `deal-of-the-day` Switch field (Boolean) to Listings collection
- Pipeline sets this true for the single highest-scoring listing each day
- Only one listing has this flag true at any time — pipeline clears previous

**Site additions needed:**
- `/deal-of-the-day` page — dedicated page, always shows current deal
- Nav tab — "Deal of the Day" prominently in nav (between Latest Deals and About)
- Homepage hero — Deal of the Day gets slot #1 in the carousel
- Social — dedicated reel/post at peak time (7-8pm CT for real estate content)
- Email — sent to all subscribers (free and paid) as the daily hook

**Content hierarchy:**
```
Deal of the Day (score 9-10, 1/day)
    → /deal-of-the-day dedicated page
    → Homepage hero slot #1
    → Social reel + text post
    → Email to ALL subscribers (free + paid) — the daily hook

Featured Listings (score 6-8, 5-7/day)
    → Homepage grid
    → Social text post
    → Email to paid subscribers only

Archive (score 4-5, unlimited)
    → /listings/[slug] page
    → State pages
    → No social, no email
```

### 12-Week Portfolio Buildout Plan

**Target: 5 sites live and running by week 12.**

Each site after the first is a template duplication + reconfiguration.
The pipeline, CMS schema, Webflow structure, and prompt architecture are
identical. Only the price filter, editorial focus, and branding change.

```
Week 1-2:   HousesUnder150K.com     ← $0-150K, all types, national (building now)
Week 3-4:   HousesUnder100K.com     ← $0-100K, tighter, more dramatic finds
Week 5-6:   OldHousesUnder150K.com  ← pre-1950 filter, historic/character focus
Week 7-8:   FarmhousesUnder150K.com ← rural/acreage filter, lifestyle angle
Week 9-10:  NewHomesUnder150K.com   ← new construction only, investor angle
Week 11-12: Buffer — finish, polish, all 5 confirmed running
```

**Setup time per site decreases sharply:**
```
Site 1: Build everything from scratch     → 2 weeks
Site 2: Duplicate + reconfigure           → 1 week
Site 3: Duplicate + reconfigure           → 3-4 days
Site 4: Pure configuration                → 2 days
Site 5: Pure configuration                → 2 days
```

**Three variables that determine timeline:**

1. API approval — Repliers free trial is instant. Apply day one.
2. Affiliate approval — Commission Junction takes 1-3 weeks. Apply immediately,
   do not wait until the site is live. Parallel path, not sequential.
3. Facebook traction — First 500 followers are hardest. Budget $50-100 to boost
   the first Deal of the Day post on each new site. Seeds the algorithm.

**What each site needs at launch (checklist):**
- [ ] Domain registered (Cloudflare, ~$10)
- [ ] Webflow site duplicated from Site 1 template
- [ ] Branding updated (name, colors if different, logo)
- [ ] CMS price filter updated in pipeline config
- [ ] Scoring prompt criteria adjusted for niche
- [ ] Beehiiv account + free/paid tiers configured
- [ ] Facebook page created
- [ ] Realtor.com affiliate link (same CJ account, different tracking ID)
- [ ] Webflow upgraded + domain connected
- [ ] First 10 listings manually seeded before pipeline launches

### Pipeline-Compatible Verticals

The same two-prompt pipeline transfers to any niche with a listing API and an
audience that browses by price and location:

```
Real estate (same MLS infrastructure — same Repliers API, different filters):
├── HousesUnder150K.com     ← building now
├── HousesUnder100K.com     ← tighter inventory, more dramatic finds
├── OldHousesUnder150K.com  ← pre-1950 filter, historic focus
├── FarmhousesUnder150K.com ← acreage + rural filter
└── NewHomesUnder150K.com   ← new construction filter, investor angle

Adjacent verticals (different APIs, same pipeline architecture):
├── ClassicCarsUnder20K.com ← vehicle listing APIs exist
├── BoatsUnder50K.com       ← marine listing data available
└── VintageRVsUnder30K.com  ← massive Facebook audience

Content verticals (no listing API needed):
└── SmallTownLife.com       ← relocation/lifestyle, programmatic revenue
```

### The Only Number That Matters Right Now

**$1,000/month from HousesUnder150K.com.**

Everything downstream — the holdco, the staff, the SaaS, the 10 sites — is
contingent on proving the model works once. Finish the site. Connect the pipeline.
Get it publishing. The rest is a future problem.

---

## Phased Execution — Remaining Sessions

---

### Session 2 — Site Finish & Subdomain Publish
**Goal:** Complete all site pages, fix card styling, publish to Webflow subdomain for first live preview.

**Prerequisites:** None (no GitHub needed for this session)

**Tasks:**
1. **Fix homepage card styling**
   - Add price display to card (currently bound but not visible — likely needs `$` prefix + styled price-display binding)
   - Set `hu150-card-img` style: height 220px, background #2A2A2A, width 100%
   - Review card spacing, border-radius, body padding
   - Take screenshot at desktop and mobile

2. **About page**
   - Create static page at `/about`
   - Simple one-pager: brand story, editorial mission, "We find the listings most people never see"
   - Same nav and footer as other pages
   - No CMS needed

3. **States index page**
   - Static page at `/states`
   - Grid of all 50 states as links → `/states/[state-slug]`
   - Simple, clean, SEO-focused

4. **State page template** (if time permits)
   - CMS Collection page filtered by `state` field
   - Lists all Active listings for that state
   - Passive SEO + affiliate revenue layer

5. **Sold listing page state**
   - Add conditional visibility to listing template
   - When Status = Sold: show "This property has sold" message + link to state page
   - When Status = Active: show normal listing content

6. **Publish to Webflow subdomain**
   - Publish site (no custom domain yet — uses .webflow.io subdomain)
   - Test all pages live
   - Verify CMS binding renders correctly on published URL

**Session start prompt:**
> "We're building HousesUnder150K.com on Webflow. The site is mostly built — homepage with CMS-bound listing grid, listing template with all fields bound. We need to fix the card styling on the homepage (price display missing, image placeholder needs height), build an About page, a States index page, and publish to the Webflow subdomain. Webflow Site ID: 6a650a7eb2639262c4b6adb7. Homepage page ID: 6a650a80b2639262c4b6adba. Start by reading /mnt/user-data/outputs/build_status.md for full context."

---

### Session 3 — Domain Launch
**Goal:** Upgrade Webflow, connect domain, go fully live.

**Prerequisites:** Credit card for Webflow Basic ($14/mo)

**Tasks:**
1. Upgrade Webflow site to Basic plan
2. Add custom domain `housesunder150k.com` in Webflow site settings
3. In Cloudflare DNS: add two CNAME records pointing to Webflow
4. Verify SSL certificate issued
5. Test live site at housesunder150k.com
6. Verify listing template renders at housesunder150k.com/listings/brand-new-construction-milwaukee-105000
7. Apply for Realtor.com affiliate (Commission Junction)
8. Apply for New Silver affiliate (FlexOffers)

---

### Session 4 — API Integration
**Goal:** Connect Repliers listing API, map fields to CMS schema, test ingestion of real listings.

**Prerequisites:**
- Repliers account (free trial available)
- GitHub connected to Claude Desktop / Cowork

**Tasks:**
1. Sign up for Repliers at repliers.io
2. Test API: `GET /listings?price_max=150000&status=active&limit=10`
3. Map Repliers response fields to CMS schema (document the field map)
4. Identify photo URL structure from API response
5. Write ingestion script in `/scripts/ingest.js` or Python
6. Test creating one CMS item via Webflow API from Repliers data
7. Verify image URL from API renders in hero-image field
8. Push script to GitHub

**Key API mappings to establish:**
```
Repliers field          → Webflow CMS field
listPrice               → price
address.street          → address
address.city            → city
address.state           → state (abbreviation)
details.numBedrooms     → bedrooms
details.numBathrooms    → bathrooms
details.sqft            → square-feet
details.yearBuilt       → year-built
photos[0]               → hero-image
mlsNumber               → (for sold check later)
```

---

### Session 5 — Pipeline Automation
**Goal:** Full automated pipeline running 3x/day. Listings come in, get scored, get written, get published.

**Prerequisites:**
- Session 4 complete (API working)
- Cowork Scheduled Tasks available
- Prompts finalized in GitHub

**Tasks:**
1. Finalize scoring prompt at `/prompts/scoring-prompt.md`
2. Finalize content generation prompt at `/prompts/deals-under-150k.md`
3. Build Cowork Scheduled Task — main pipeline:
   - Fetch new listings from Repliers (last 8 hours)
   - For each: run scoring prompt (Call 1)
   - If score ≥ 6: run content generation prompt (Call 2)
   - Write to Webflow CMS via API
   - Publish new CMS items
   - Log to `/posts/[slug].json` in GitHub
4. Build Cowork Scheduled Task — sold check:
   - Fetch all Active listings from CMS
   - Check each listing URL for sold/removed status
   - Update CMS status field for any that have sold
5. Test full loop end-to-end with 3 real listings
6. Set schedules: pipeline 3x/day (8am, 1pm, 6pm CT), sold check 1x/day (9am CT)
7. Verify homepage populates automatically after pipeline run

---

### Session 6 — Social & Monetization
**Goal:** Social posting live, affiliate links active, first revenue.

**Prerequisites:**
- Facebook page created for HousesUnder150K
- Session 5 complete (pipeline running)
- Affiliate approvals received

**Tasks:**
1. Set up Facebook page — HousesUnder150K
2. Evaluate social posting tool (bundle.social or n8n on Railway)
3. Connect social posting to pipeline — when Featured listing published, auto-post social caption to Facebook
4. Add affiliate tracking links to pipeline — replace placeholder affiliate-url with real Commission Junction tracking link
5. Verify affiliate click tracking in Commission Junction dashboard
6. Test: listing goes in → social post goes out → user clicks → lands on listing page → clicks View Full Listing → affiliate conversion tracked
7. Set up basic analytics (Webflow Insights or Google Analytics)
8. Monitor first 7 days: post engagement, site traffic, affiliate clicks

---

## Pre-Session 2 Checklist
- [ ] Connect Claude Desktop / Cowork to GitHub repo (github.com/housesunder150k/housesunder150k)
- [ ] Push concept doc to GitHub: copy `/mnt/user-data/outputs/real-estate-content-platform-concept.md` → `/docs/concept.md`
- [ ] Create `/prompts/scoring-prompt.md` in repo (copy from concept doc)
- [ ] Create `/prompts/deals-under-150k.md` in repo (copy from concept doc)
- [ ] Confirm Webflow MCP is connected in Claude Desktop (not required for bridge app in MCP 2.0)
- [ ] Have `build_status.md` accessible at start of next session

---

## Known Issues & Notes

**Webflow MCP 2.0 (as of July 21, 2026)**
- Most operations work WITHOUT the Bridge app
- Bridge app still required for: element snapshots, canvas navigation, uploading image from URL
- Correct binding key for text elements: `text` (not `textContent`)
- Create elements first, bind in second pass — inline settings bindings at creation time fail for CMS bindings
- CMSCollection inner structure: `DynamoWrapper → DynamoList → DynamoItem` — cannot pass CMSCollectionList/CMSCollectionItem as child types in element builder
- Collection filter operators for option fields: `equals` / `doesNotEqual` / `isSet` / `isNotSet`
- Collection sort direction: `ascending` / `descending`

**CMS Binding Notes**
- Text binding key: `text`
- Image binding key: `assetId`
- Link binding key: `link`
- RichText binding key: `richText`
- Always bind in a separate pass AFTER element creation
- Newly added CMS fields may show null in designer preview until designer tab is refreshed — data is correct in CMS, will render live

**Designer Link (requires Bridge app for canvas nav)**
https://housesunder150k.design.webflow.com?app=dc8209c65e3ec02254d15275ca056539c89f6d15741893a0adf29ad6f381eb99

---

*Document maintained in: `/mnt/user-data/outputs/build_status.md`*
*Push to GitHub: `/docs/build_status.md`*
