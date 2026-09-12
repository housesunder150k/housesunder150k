"""
HousesUnder150K.com — Ingestion Pipeline
Runs on Railway 6x/day: 8am, 1pm, 6pm, 8pm, midnight, 4am CT
Fetches listings from RealtyAPI (Realtor.com), scores, generates content, publishes to Webflow.
Dedup, daily limit, and seen-listing suppression via Supabase.
Data source: RealtyAPI (realtyapi.io) — Realtor.com endpoint

Changes (2026-07-28):
- pending=False added to search params — filters pending listings at source
- Gallery photos: uploads photos[1-3] to Cloudflare, writes to gallery-images MultiImage field
- gallery_image_ids stored in Supabase for maintenance job cleanup on status change
- Address key replaces property_id as dedup/suppression identifier — stable across
  RealtyAPI id drift. Format: "{street}|{city}|{state}" normalized to lowercase.

Changes (2026-07-29):
- HEADLINE prompt updated: search-friendly title format replacing period-separated headline style.
  New format: "[Year] [City] [Property Type] with [Key Feature] — $[Price]"
  Example: "1931 Detroit Home with Double Lot and French Doors — $150,000"
- Tags field added: up to 5 tags derived from CATEGORY, KEY_HOOKS, and listing data.
  No extra Claude call — tags generated in generate_tags() from existing scored data.
  Written to new Webflow "tags" PlainText field as comma-separated string.

Changes (2026-08-17):
- list_date captured from RealtyAPI search result and stored in Supabase at ingest time.
  Used by maintenance job to calculate days_on_market when a listing sells.

Changes (2026-09-01):
- short_summary, social_caption, city, state added to db_insert_published and published_listings
  Supabase table. These fields are required by the LinkedIn pipeline to generate listing posts.
  Previously the LinkedIn job queried for these columns but they didn't exist, causing a 400
  on every run. Columns are nullable; existing rows retain NULL values.

Changes (2026-09-12 — Session 40):
- Scoring model v2.0: five-category weighted composite score (Property Merit 50%, Condition 25%,
  Price/SqFt 15%, Price vs Market 5%, Market Conditions 5%).
- Redfin market data injected before scoring: /housingMarketTrends (median price, homes sold,
  DOM, sale-to-list, price drops) + /recentlySold (zip median $/sqft from pricePerSqFt values).
- Both Redfin calls cached per zip per run (2 credits/zip, ~14,200/month worst case).
- Three data reliability states: reliable / thin / null. True null skips publishing.
- Thin market: homes_sold < 10, MoM median variance > 20%, or fewer than 10 valid psf values.
- 12 new fields output by scoring prompt: composite_score, 5 category scores, 5 detail lines,
  thin_market boolean. All written to Webflow CMS and Supabase.
- has-score written LAST to Webflow — score table stays hidden if any upstream step fails.
- price_per_sqft calculated in pipeline (listing_price / sqft).
- Content prompt updated: narrative explains score rationale, not just property description.
- pipeline_runs tracking: redfin_null_skips, redfin_thin_market_count, redfin_api_credits_used.

Changes (2026-08-29):
- Image alt text overhauled to target GSC impression queries.
  New make_image_alt() generates varied keyword patterns matching real search queries:
  "[city] [state] house under 150000", "affordable home under 150K [city] [state]", etc.
  City is always present in every template — no state-only patterns.
  Hero and all gallery images use GSC-aligned alt text instead of listing headline
  or slug-based placeholder. Deterministic per slug+photo_index — stable across deploys.
"""

import os
import re
import time
import logging
import random
from datetime import datetime, timezone, date, timedelta

import requests
import pytz

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config — all values from environment, nothing hardcoded
# ---------------------------------------------------------------------------

REALTYAPI_KEY          = os.environ["REALTYAPI_KEY"]
ANTHROPIC_API_KEY      = os.environ["ANTHROPIC_API_KEY"]
CLOUDFLARE_API_TOKEN   = os.environ["CLOUDFLARE_API_TOKEN"]
CLOUDFLARE_ACCOUNT_ID  = os.environ["CLOUDFLARE_ACCOUNT_ID"]
WEBFLOW_API_TOKEN      = os.environ["WEBFLOW_API_TOKEN"]
WEBFLOW_COLLECTION_ID  = os.environ["WEBFLOW_COLLECTION_ID"]
SOVRN_AFFILIATE_URL    = os.environ["SOVRN_AFFILIATE_URL"]
SUPABASE_URL           = os.environ["SUPABASE_URL"]
SUPABASE_KEY           = os.environ["SUPABASE_KEY"]
DAILY_PUBLISH_LIMIT    = int(os.environ.get("DAILY_PUBLISH_LIMIT", "10"))

CLAUDE_MODEL                = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS_SCORING   = 500
CLAUDE_MAX_TOKENS_CONTENT   = 900
REALTYAPI_REALTOR_BASE = "https://realtor.realtyapi.io"
REALTYAPI_REDFIN_BASE  = "https://redfin.realtyapi.io"
ANTHROPIC_BASE         = "https://api.anthropic.com/v1/messages"
CF_IMAGES_BASE         = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1"
CF_DELIVERY_BASE       = "https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w"
WEBFLOW_BASE           = "https://api.webflow.com/v2"

SEEN_SUPPRESSION_DAYS  = 14
CT_TZ                  = pytz.timezone("America/Chicago")
GALLERY_PHOTO_COUNT    = 3  # number of additional gallery photos (indices 1-3 of photos[])

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma",
    "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]

REALTYAPI_SORT_ORDERS = ["Newest", "Relevant", "Price_Low", "Price_High"]

WF_STATUS_ACTIVE = "3b41185e9af84f92d8da092965308a2d"

STATE_TO_WEBFLOW_ITEM_ID = {
    "AL": "6a67c49e081d8375c4744785", "AK": "6a67c49e081d8375c4744787",
    "AZ": "6a67c49e081d8375c4744789", "AR": "6a67c49e081d8375c474478b",
    "CA": "6a67c49e081d8375c474478d", "CO": "6a67c49e081d8375c474478f",
    "CT": "6a67c49e081d8375c4744791", "DE": "6a67c49e081d8375c4744793",
    "FL": "6a67c49e081d8375c4744795", "GA": "6a67c49e081d8375c4744797",
    "HI": "6a67c49e081d8375c4744799", "ID": "6a67c49e081d8375c474479b",
    "IL": "6a67c49e081d8375c474479d", "IN": "6a67c49e081d8375c474479f",
    "IA": "6a67c49e081d8375c47447a1", "KS": "6a67c49e081d8375c47447a3",
    "KY": "6a67c49e081d8375c47447a5", "LA": "6a67c49e081d8375c47447a7",
    "ME": "6a67c49e081d8375c47447a9", "MD": "6a67c49e081d8375c47447ab",
    "MA": "6a67c49e081d8375c47447ad", "MI": "6a67c49e081d8375c47447af",
    "MN": "6a67c49e081d8375c47447b1", "MS": "6a67c49e081d8375c47447b3",
    "MO": "6a67c49e081d8375c47447b5", "MT": "6a67c49e081d8375c47447b7",
    "NE": "6a67c49e081d8375c47447b9", "NV": "6a67c49e081d8375c47447bb",
    "NH": "6a67c49e081d8375c47447bd", "NJ": "6a67c49e081d8375c47447bf",
    "NM": "6a67c49e081d8375c47447c1", "NY": "6a67c49e081d8375c47447c3",
    "NC": "6a67c49e081d8375c47447c5", "ND": "6a67c49e081d8375c47447c7",
    "OH": "6a67c49e081d8375c47447c9", "OK": "6a67c49e081d8375c47447cb",
    "OR": "6a67c49e081d8375c47447cd", "PA": "6a67c49e081d8375c47447cf",
    "RI": "6a67c49e081d8375c47447d1", "SC": "6a67c49e081d8375c47447d3",
    "SD": "6a67c49e081d8375c47447d5", "TN": "6a67c49e081d8375c47447d7",
    "TX": "6a67c49e081d8375c47447d9", "UT": "6a67c49e081d8375c47447db",
    "VT": "6a67c49e081d8375c47447dd", "VA": "6a67c49e081d8375c47447df",
    "WA": "6a67c49e081d8375c47447e1", "WV": "6a67c49e081d8375c47447e3",
    "WI": "6a67c49e081d8375c47447e5", "WY": "6a67c49e081d8375c47447e7",
}

COST_PER_1K_INPUT  = 0.003
COST_PER_1K_OUTPUT = 0.015

STATE_FULL_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

STATE_TO_SLUG = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
    "FL": "florida", "GA": "georgia", "HI": "hawaii", "ID": "idaho",
    "IL": "illinois", "IN": "indiana", "IA": "iowa", "KS": "kansas",
    "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi",
    "MO": "missouri", "MT": "montana", "NE": "nebraska", "NV": "nevada",
    "NH": "new-hampshire", "NJ": "new-jersey", "NM": "new-mexico", "NY": "new-york",
    "NC": "north-carolina", "ND": "north-dakota", "OH": "ohio", "OK": "oklahoma",
    "OR": "oregon", "PA": "pennsylvania", "RI": "rhode-island", "SC": "south-carolina",
    "SD": "south-dakota", "TN": "tennessee", "TX": "texas", "UT": "utah",
    "VT": "vermont", "VA": "virginia", "WA": "washington", "WV": "west-virginia",
    "WI": "wisconsin", "WY": "wyoming",
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SCORING_PROMPT = """Score this residential listing for HousesUnder150K.com. You will receive property data and Redfin zip market data. Produce a five-category weighted composite score (1-10 scale, one decimal). Be strict — most listings score 4 or below. Only genuinely interesting listings score 6+. Low price alone is never enough.

SCORING WEIGHTS: Property Merit (50%) + Condition (25%) + Price per Sq Ft (15%) + Price vs Market (5%) + Market Conditions (5%) = composite.

PRICE PER SQ FT SCORING (compare LISTING_PSF to ZIP_MEDIAN_PSF):
- More than 40% below zip median: 9-10
- 20-40% below zip median: 7-8
- 0-20% below zip median: 5-6
- 0-20% above zip median: 3-4
- More than 20% above zip median: 1-2
- If zip median $/sqft unavailable: score 5 (neutral), detail = "insufficient zip $/sqft data"

PRICE VS MARKET SCORING (listing price vs ZIP_MEDIAN_SALE_PRICE):
- More than 50% below median: 9-10
- 30-50% below median: 7-8
- 10-30% below median: 5-6
- Within 10% of median: 3-4
- Above median: 1-2
- Caution: if zip median appears driven by acreage/land sales rather than comparable homes, note this.

MARKET CONDITIONS SCORING (ZIP_MEDIAN_DOM, ZIP_SALE_TO_LIST, ZIP_PRICE_DROPS_PCT — weight equally):
- Long DOM + sale-to-list <97% + price drops >25% = strong buyer's market = 8-10
- Mixed signals = 5-7
- Short DOM + sale-to-list >100% + price drops <10% = competitive seller's market = 1-4

CONDITION SCORING:
- Move-in ready / renovated with specific system dates (roof, HVAC, windows): 8-10
- Cosmetic work only, structure and systems sound: 5-7
- Major renovation required: 2-4
- Unknown / as-is without floor qualifier: 3-5 (lean lower with investor language)
- AS-IS EXCEPTION: historic / acreage / waterfront / architectural value = 4-5 even as-is
- Specificity bonus: named years for updates ("roof 2022") = +0.5 above range midpoint

AUDIENCE: First-time buyers, remote workers, retirees — people with conventional financing and modest savings. They are dreamers who want to believe affordable homeownership is still possible. The listing must be something a regular person with a standard mortgage can actually buy and live in. If it requires cash, contractor skills, or investor experience to be viable, maximum score is 4 regardless of other signals.

EDITORIAL STANDARD: We are a curated media site, not a listing aggregator. Every published listing must have a story — a reason a reader would stop scrolling and say "wait, tell me more." Price alone is not a story. Square footage alone is not a story. A 1920 farmhouse on 3 acres with original hardwood floors and a creek running through the back — that's a story. Ask yourself: would a knowledgeable friend text this to someone they care about?

AUTOMATIC 6+ FLOOR (any one qualifies):
- Waterfront / lake / river / ocean / creek
- Lake view or mountain view
- Acreage 0.5+ acres
- In-ground pool
- Wooded lot
- New construction (built within 2 years)
- Historic home pre-1950 with character details

POSITIVE SIGNALS (accumulate to reach 6 without a floor qualifier):
- Recent renovation or major system update (roof/HVAC/windows) with specifics
- Sqft: <800 = -1 | 800-1100 = neutral | 1100-1400 = +0.5 | 1400-1800 = +1 | 1800+ = +1.5
- Beds: 4 = +0.5 | 5+ = +1
- Garage, outbuildings, barn, workshop
- Character features: stained glass, exposed beams, hardwood, wraparound porch, clawfoot tub, built-ins, tin ceilings, wainscoting, fireplace, crown molding, original doors
- Finished basement
- Named nearby amenities, trails, parks, charming town, university, lake access
- Price reduction signal in description — someone motivated to sell
- High days on market + low price — hidden gem potential
- Rich agent description with specifics: +0.5 to +1
- Unusual or distinctive architecture: castle, craftsman, Victorian, Tudor, log cabin, stone construction
- Price-per-sqft under $50: notable value signal worth mentioning
- Income potential: legal accessory dwelling, rental history, Airbnb suitability in described location

NEGATIVE MODIFIERS:
- Manufactured/mobile/modular: -3
- Condo/unit in multi-family complex: -2 (lot size reflects complex parcel, not buyer's land — ignore any acreage signal)
- Cash only / sold as-is AND no floor qualifier (no acreage, waterfront, historic character, views, or architectural value): -2 (distressed dump with no story for our audience)
- Needs major work, no renovation history: -1
- No photos: -1
- Under 700 sqft: -1
- HOA with high fees: -0.5
- Sparse description (3 sentences or fewer): -1
- Investor/flipper language ("bring your vision", "investor special", "as-is opportunity"): -1
- Flood zone AE (required flood insurance — affects mortgage qualification): -0.5
- DAYS_ON_MARKET 180-364: -0.5 (market has passed on this multiple times)
- DAYS_ON_MARKET 365+: listings this stale are prefiltered and will not reach scoring

AS-IS EXCEPTION: As-is is fine when the property has historic significance, significant acreage, waterfront access, or genuine architectural value. A 130-year-old stone farmhouse on 10 acres sold as-is is still a 7. A 1973 ranch with no description sold as-is is a 2.

SCORING PRECISION NOTES:
- Read descriptions carefully for hidden signals. "Motivated seller" = price flexibility. "Estate sale" = potential underpricing. "Original details throughout" = character. "Needs TLC" without specifics = deduct.
- Year built matters: pre-1900 = likely character details even if not described. 1950-1975 = solid bones, nothing distinctive. Post-2000 = check for updates.
- Location context matters even without description. A $60K house in a college town is more interesting than the same house in an industrial suburb.
- Photos count. A listing with 25+ photos is telling you more than one with 3.

SCORING BANDS:
1-3: Skip — no story, bad data, manufactured home, investor dump
4-5: Below threshold — decent home, nothing editorial. Do not publish.
6: Publish — one floor qualifier OR compelling accumulation of positives
7-8: Featured — strong floor qualifier + good description + clear story
9-10: Hero / Deal of Day — exceptional on multiple dimensions, stops the scroll

OUTPUT (exactly this format, no other text):
SCORE: [composite 1-10, one decimal e.g. 7.4]
TIER: [SKIP / BELOW_THRESHOLD / PUBLISH / FEATURED / HERO]
CATEGORY: [NEW_CONSTRUCTION / WATERFRONT / ACREAGE / HISTORIC / RENOVATED / CHARACTER / HIDDEN_GEM / TOO_GOOD_TO_BE_TRUE / WHAT_IF]
KEY_HOOKS: [2-4 specific compelling facts, comma separated]
REASON: [1-2 sentences]
DEAL_OF_DAY_CANDIDATE: [YES / NO]
SCORE_PROPERTY_MERIT: [1-10, one decimal]
SCORE_CONDITION: [1-10, one decimal]
SCORE_PRICE_PER_SQFT: [1-10, one decimal]
SCORE_PRICE_VS_MARKET: [1-10, one decimal]
SCORE_MARKET_CONDITIONS: [1-10, one decimal]
DETAIL_PROPERTY_MERIT: [one line, ≤15 words, factual — key physical signals that drove score]
DETAIL_CONDITION: [one line, ≤15 words, factual — condition state and evidence]
DETAIL_PRICE_PER_SQFT: [one line, ≤15 words — listing $/sqft and zip median if available]
DETAIL_PRICE_VS_MARKET: [one line, ≤15 words — % vs zip median, note thin market if applies]
DETAIL_MARKET_CONDITIONS: [one line, ≤15 words — DOM, sale-to-list, price drops]
THIN_MARKET: [true / false]

TIER MAP: 1-3=SKIP | 4-5=BELOW_THRESHOLD | 6=PUBLISH | 7-8=FEATURED | 9-10=HERO
CATEGORIES: NEW_CONSTRUCTION=built within 2yr | WATERFRONT=any water | ACREAGE=land is story | HISTORIC=pre-1950 character | RENOVATED=updated systems | CHARACTER=unique details | HIDDEN_GEM=underrated value | TOO_GOOD_TO_BE_TRUE=price seems wrong | WHAT_IF=lifestyle/land fantasy"""


CONTENT_PROMPT_TEMPLATE = """You looked at a house. Tell someone what you saw.

The listing data includes score context — use it as background awareness, not as a structure to follow. Do not explain the scores. Do not reference the scores. Do not advise the reader on what the scores mean for them. The score table is already visible above your words — the reader does not need you to narrate it.

FRAMING:
- Open with what makes this listing remarkable relative to its market. Not the property in isolation — why this price, this size, this location is unusual for where it is. Give the reader the context that makes the number land.
- Name the opportunity in human terms. Room for a family. Space to expand. Land to grow into. A historic house they can make their own. Say what a person could actually do here, not what the listing "offers."
- The downside gets one paragraph. Name it plainly and move on. Do not soften it, but do not end on it. End on what the price makes possible — or what the property makes possible at this price.

You are not a copywriter. You are not a real estate agent. You are someone with taste and a point of view who actually looked at this property and is describing it honestly to a friend who asked. You notice things. You have opinions. You say what something is like, not what someone should feel about it.

VOICE:
- Write the way you talk. Vary sentence length naturally.
- Use "you" where it fits. Not on every sentence.
- You can say something is pretty, big, small, old, rough, or nice when it actually is. Use adjectives that are accurate and earned.
- Do not reach for a bigger word than the thing deserves. A nice porch is a nice porch. It is not a stunning wraparound sanctuary. A large kitchen is large. It is not a breathtaking culinary space.
- If something genuinely stands out, say so and say why. If something is ordinary, say it plainly.
- Do not comment on the act of describing. Just say the thing.
  ❌ "That's the first thing worth saying."
  ❌ "That's worth noting."
  ❌ "That's meaningful."
- Do not fabricate local knowledge. If you don't have a specific fact from the listing data, don't claim to know it. Generic small town descriptions that could apply anywhere are padding.
  ❌ "Caney lots tend to have room to them, so that tracks."
  ❌ "It's the kind of town where you know your neighbors."
- No exclamation points.
- No dashes of any kind used as connectors.
- Never use "is not," "are not," "was not," "does not," "don't," "isn't," "aren't," or "wasn't" to reassure the reader or frame something positively. Say what it is directly.
  ❌ "That is not a small line item."
  ❌ "This is not a remote situation."
  ✅ State what it is. Move on.

ADJECTIVE SCALE:
Use words that match reality. Big, pretty, old, rough, solid, tight, wide, steep, dark, bright, worn, clean — these are honest words. Breathtaking, stunning, gorgeous, vast, exceptional, remarkable, incredible, unbelievable — these are inflation. The reader can feel the difference and loses trust when everything is superlative.

BANNED WORDS: nestled, charming, cozy, stunning, turnkey, move-in ready, open concept, perfect for, don't miss, rare find, won't last, priced to sell, boasts, features, sits on, offers, located in, versatile, endless possibilities, bones, good bones, opportunity, motivated seller, character-filled, genuinely, really, truly, actually, leverage, underscore, reflect, breathtaking, exceptional, remarkable, incredible, unbelievable, masterpiece, captivating, timeless, exquisite

FACTS:
- Every fact from the listing data only. Never invent.
- Specific numbers always.
- Name the town, the feature, the year work was done.
- If the agent description is thin, say so plainly rather than padding.
- The agent description is real estate marketing copy written to sell the property. Its tone, structure, and phrasing are examples of exactly what not to do. Extract facts from it only. Do not let its language influence how you write.

The listing data will be provided in the user message. Produce exactly these four outputs, clearly labeled:

---

HEADLINE
Under 12 words. Lead with the most interesting fact. Price goes last after " — ". No real estate language. If year built is pre-1980, lead with it.
Example: "1908 Alliance Bungalow with Pool, Porch, and Garage — $119,900"

NARRATIVE
300 to 400 words. No template. Let the property dictate the shape. Move through it the way you would walk it. Have a point of view. Do not open with the year built, the address, or the square footage. Start with whatever is most interesting about this specific property — the thing that made you stop and look. Those other facts can go anywhere in the piece.

SOCIAL_CAPTION
Under 60 words. Same voice. No dashes of any kind. Lead with the thing that stops the scroll.

SHORT_SUMMARY
One or two sentences, under 30 words. The single most interesting thing about this listing.

---

Return all four outputs with those exact labels. Nothing else."""


REVIEW_PROMPT = """You are a copy editor. You have received four outputs from a writer describing a house listing: HEADLINE, NARRATIVE, SOCIAL_CAPTION, and SHORT_SUMMARY.

Your job is to check each output against the rules below and rewrite any sentence that violates them. Do not rewrite sentences that are clean. Do not change facts, tone, or structure unless a rule requires it. Return all four outputs with the same labels whether or not changes were made.

RULES:

No dashes of any kind in NARRATIVE, SOCIAL_CAPTION, or SHORT_SUMMARY. Em dash, en dash, or hyphen used as a connector are all prohibited. Rewrite the sentence without the dash.
\u274c "The kitchen works — updated island, new cabinetry — without fighting the house's age."
\u2705 "The kitchen has an updated island and new cabinetry."

No corrective negation. Do not establish what something isn't before saying what it is. Includes positive-framed versions.
\u274c "This isn't a flipper special. It's a house someone actually lived in."
\u274c "You don't find layouts like this in anything built recently."
\u2705 State what it is directly.

No antithesis. Do not balance opposing ideas for effect.
\u274c "It doesn't fight the age of the house, it works alongside it."

No summary beats. Do not close a paragraph by summarizing what you just wrote.
\u274c "For a 116-year-old house in a small Ohio city, that's an unusual amount of infrastructure."

No landing sentences. Do not end a paragraph with a sentence that editorializes on what you just described.
\u274c "A hundred years is a long time without knowing the maintenance history."

No setup/payoff. Do not build toward a reveal or conclusion.
\u274c "The wraparound porch alone is worth stopping for. It runs the full front of the house."

No rhetorical crutches. Do not use constructions that exist to create emphasis rather than convey information.
\u274c "The wraparound porch alone is worth stopping for."

No paragraph pinning. Do not open a paragraph by restating what the previous paragraph established.
\u274c [Para 1 ends on the porch] [Para 2 opens: "That porch sets the tone for everything inside."]

No parataxis. Do not stack short declarative sentences as a stylistic device.
\u274c "Wood floors. Dark trim. A fireplace. 1908."

No parallel sentence structures within a paragraph. Do not let two or more consecutive sentences follow the same grammatical shape.
\u274c "The kitchen has an oversized island. The dining room has a bay window. The great room has a fireplace."

No stacked noun phrases.
\u274c "Wood floors, dark trim, ornate mantel, bay window, jetted tub."

No rule of three. Do not list exactly three items for rhythmic effect.
\u274c "A pool, a garage, and a wraparound porch."

No contrasting pairs.
\u274c "Small town, big lot."

No negative parallelisms.
\u274c "Layouts like this don't exist in new construction. You have to find them in houses like this."

No negative anaphoras.
\u274c "No updates needed. No contractor required. No surprises waiting."

No throat-clearing openers.
\u274c "What makes this listing worth a look is the price relative to what you're getting."

No filler intensifiers: genuinely, really, truly, actually.

No corporate-register verbs: leverage, underscore, reflect, offer, feature, boast.

No nominalization. Use the verb, not the noun made from it.
\u274c "a replacement of the roof" \u2192 \u2705 "the roof was replaced"

No hedging qualifiers.
\u274c "The photos suggest the floors may be original hardwood."

No performed enthusiasm. No exclamation points.

BANNED WORDS: nestled, charming, cozy, stunning, turnkey, move-in ready, open concept, perfect for, don't miss, rare find, won't last, priced to sell, boasts, features, sits on, offers, located in, versatile, endless possibilities, bones, good bones, opportunity, motivated seller, character-filled

Return all four outputs with the exact same labels. Nothing else."""


# ---------------------------------------------------------------------------
# Tag generation — derived from scored data, no extra Claude call
# ---------------------------------------------------------------------------

TAG_MAP = {
    # Category-based tags
    "WATERFRONT":      "Waterfront",
    "ACREAGE":         "Acreage",
    "HISTORIC":        "Historic",
    "RENOVATED":       "Renovated",
    "NEW_CONSTRUCTION": "New Construction",
    "CHARACTER":       "Character Home",
    "HIDDEN_GEM":      "Hidden Gem",
    # Key hook signal tags
    "pool":            "Pool",
    "barn":            "Barn",
    "garage":          "Garage",
    "basement":        "Finished Basement",
    "fireplace":       "Fireplace",
    "acreage":         "Acreage",
    "waterfront":      "Waterfront",
    "lake":            "Lake Access",
    "creek":           "Creek",
    "wooded":          "Wooded Lot",
    "farmhouse":       "Farmhouse",
    "victorian":       "Victorian",
    "craftsman":       "Craftsman",
    "log cabin":       "Log Cabin",
    "stone":           "Stone Construction",
    "new roof":        "New Roof",
    "new hvac":        "Updated HVAC",
    "rental":          "Income Potential",
    "airbnb":          "Income Potential",
    "income":          "Income Potential",
}


def generate_tags(score_data: dict, listing: dict) -> str:
    """Derive up to 5 tags from category, key hooks, and listing data. No Claude call."""
    tags = []
    seen = set()

    def add(tag: str):
        if tag not in seen and len(tags) < 5:
            tags.append(tag)
            seen.add(tag)

    # 1. Primary category tag
    category = score_data.get("CATEGORY", "").upper()
    if category in TAG_MAP:
        add(TAG_MAP[category])

    # 2. Scan key hooks for signal tags
    hooks_raw = score_data.get("KEY_HOOKS", "").lower()
    for signal, tag in TAG_MAP.items():
        if signal.lower() in hooks_raw:
            add(tag)

    # 3. Scan listing details directly
    details = listing.get("details", {})
    desc_lower = (details.get("description", "") or "").lower()

    if details.get("waterfront") and "Waterfront" not in seen:
        add("Waterfront")
    if details.get("pool") and "Pool" not in seen:
        add("Pool")
    lot_acres = details.get("lotAcres")
    if lot_acres and lot_acres >= 0.5 and "Acreage" not in seen:
        add("Acreage")
    year_built = parse_int(details.get("yearBuilt"))
    if 0 < year_built <= 1950 and "Historic" not in seen:
        add("Historic")

    # 4. Description signal scan for remaining slots
    for signal, tag in TAG_MAP.items():
        if len(tags) >= 5:
            break
        if signal.lower() in desc_lower:
            add(tag)

    return ", ".join(tags)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_today_ct() -> date:
    return datetime.now(CT_TZ).date()


def parse_int(raw) -> int:
    try:
        return int(float(str(raw))) if raw is not None else 0
    except (ValueError, TypeError):
        return 0


def make_slug(street: str, city: str, state: str) -> str:
    def slugify(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    parts = [p for p in [slugify(street), slugify(city), state.lower()] if p]
    return "-".join(parts)


def make_price_display(price: int) -> str:
    return f"{price:,}"


def format_richtext(text: str) -> str:
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paragraphs)


def make_realtor_url(street: str, city: str, state: str, zip_code: str) -> str:
    def slugify(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")
    if street:
        parts = [slugify(street), slugify(city), state]
        if zip_code:
            parts.append(zip_code)
        path = "_".join(parts)
    else:
        path = f"{slugify(city)}_{state}"
    return f"https://www.realtor.com/realestateandhomes-search/{path}"


def make_address_key(street: str, city: str, state: str) -> str:
    """Stable dedup key using property address — immune to RealtyAPI property_id drift.
    Format: "{street}|{city}|{state}" normalized to lowercase and stripped.
    Example: "113 gaines st|mount hope|wv"
    """
    return f"{street.strip().lower()}|{city.strip().lower()}|{state.strip().lower()}"


def parse_list_date(raw: str | None) -> str | None:
    """Extract ISO date string (YYYY-MM-DD) from RealtyAPI list_date field.
    RealtyAPI returns list_date as ISO 8601 datetime e.g. '2026-06-23T00:08:11Z'.
    Returns None if not parseable.
    """
    if not raw:
        return None
    try:
        return raw[:10]  # slice YYYY-MM-DD from datetime string
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Image alt text — GSC-aligned keyword variations
# ---------------------------------------------------------------------------

# Template slots — mixed to maximize variation across images on the same page.
# All variations mirror real GSC impression queries: "[city] [state] house under 150000",
# "[city] [state] home under 150K", "affordable housing [city] [state]", etc.
# City is always present in every template — no state-only patterns.
# photo_index 0 = hero, 1-3 = gallery photos.

_ALT_PRICE_FORMATS = ["under 150K", "under 150,000", "under $150,000", "under 150000"]
_ALT_NOUNS = ["house", "home", "property", "housing"]
_ALT_MODIFIERS = ["affordable", "budget", "cheap", ""]  # "" = no modifier

# 16 deterministic templates — city present in every one.
# Slug hash selects entry; photo_index offsets within pool so all four images
# on one page get different patterns.
_ALT_TEMPLATES = [
    "{modifier} {noun} {price} in {city} {state}",
    "{city} {state} {noun} {price}",
    "{price} {noun} in {city} {state}",
    "{modifier} {noun} in {city} {state} {price}",
    "{state} {noun} {price} {city}",
    "{modifier} {city} {state} {noun} {price}",
    "{price} {modifier} {noun} {city} {state}",
    "{city} {state} {modifier} {noun} {price}",
    "{modifier} {noun} {price} {city} {state}",
    "{city} {state} {price} {noun}",
    "{noun} {price} in {city} {state}",
    "{modifier} {price} {noun} {city} {state}",
    "{city} {noun} {price} {state}",
    "{price} {noun} {modifier} {city} {state}",
    "{modifier} housing {price} {city} {state}",
    "{city} {state} {modifier} housing {price}",
]


def make_image_alt(city: str, state_full: str, photo_index: int, slug: str) -> str:
    """Return a GSC-keyword-aligned alt text string for a listing image.

    photo_index: 0 = hero, 1 = gallery photo 2, 2 = gallery photo 3, 3 = gallery photo 4.
    Uses slug hash for deterministic but varied selection — same listing always
    gets the same alt texts across deploys, different listings get different patterns.
    City is always present — no state-only patterns.
    """
    # Derive a stable base offset from the slug so each listing cycles differently
    slug_hash = sum(ord(c) for c in slug)

    template_idx = (slug_hash + photo_index * 3) % len(_ALT_TEMPLATES)
    price_idx    = (slug_hash + photo_index * 5) % len(_ALT_PRICE_FORMATS)
    noun_idx     = (slug_hash + photo_index * 7) % len(_ALT_NOUNS)
    modifier_idx = (slug_hash + photo_index * 11) % len(_ALT_MODIFIERS)

    template = _ALT_TEMPLATES[template_idx]
    price    = _ALT_PRICE_FORMATS[price_idx]
    noun     = _ALT_NOUNS[noun_idx]
    modifier = _ALT_MODIFIERS[modifier_idx]

    alt = template.format(
        modifier=modifier,
        noun=noun,
        price=price,
        city=city,
        state=state_full,
    )

    # Clean up double spaces left by empty modifier slot
    alt = " ".join(alt.split())
    return alt.strip()


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def db_count_published_today(today_ct: date) -> int:
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"select": "slug", "published_date_ct": f"eq.{today_ct.isoformat()}"}
    headers = _sb_headers()
    headers["Prefer"] = "count=exact"
    headers["Range-Unit"] = "items"
    headers["Range"] = "0-0"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        total = r.headers.get("Content-Range", "0/0").split("/")[-1]
        return int(total) if total != "*" else 0
    except Exception as e:
        log.error(f"Supabase count_published_today error: {e}")
        return 0


def db_slug_published(slug: str) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"select": "slug", "slug": f"eq.{slug}", "limit": 1}
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return len(r.json()) > 0
    except Exception as e:
        log.error(f"Supabase slug_published error: {e}")
        return False


def db_mls_seen_recently(address_key: str) -> dict | None:
    """Check if this address was seen within the suppression window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_SUPPRESSION_DAYS)).isoformat()
    url = f"{SUPABASE_URL}/rest/v1/seen_listings"
    params = {
        "select": "*",
        "mls_number": f"eq.{address_key}",
        "last_seen_at": f"gte.{cutoff}",
        "limit": 1,
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None
    except Exception as e:
        log.error(f"Supabase mls_seen_recently error: {e}")
        return None


def db_batch_seen_recently(address_keys: list[str]) -> set[str]:
    """Return set of address keys seen within suppression window."""
    if not address_keys:
        return set()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_SUPPRESSION_DAYS)).isoformat()
    url = f"{SUPABASE_URL}/rest/v1/seen_listings"
    params = {
        "select": "mls_number",
        "last_seen_at": f"gte.{cutoff}",
    }
    headers = _sb_headers()
    headers["Prefer"] = "return=representation"
    try:
        quoted = ",".join(f'"{k}"' for k in address_keys)
        params["mls_number"] = f"in.({quoted})"
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return {row["mls_number"] for row in r.json()}
    except Exception as e:
        log.error(f"Supabase batch_seen error: {e}")
        return set()


def db_upsert_seen(address_key: str, slug: str, score: int | float, tier: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/seen_listings"
    headers = _sb_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    payload = {
        "mls_number": address_key,
        "slug": slug,
        "score": int(round(score)),  # seen_listings.score is INTEGER — composite is now float
        "tier": tier,
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase upsert_seen error: {e}")


def db_insert_published(
    slug: str, mls_number: str, webflow_item_id: str,
    score: float, tier: str, category: str, headline: str,
    hero_image_url: str, today_ct: date, price: int = 0,
    is_deal_of_day: bool = False,
    gallery_image_ids: list[str] | None = None,
    list_date: str | None = None,
    short_summary: str | None = None,
    social_caption: str | None = None,
    city: str | None = None,
    state: str | None = None,
    # Scoring v2.0 fields
    composite_score: float | None = None,
    score_property_merit: float | None = None,
    score_condition: float | None = None,
    score_price_per_sqft: float | None = None,
    score_price_vs_market: float | None = None,
    score_market_conditions: float | None = None,
    detail_property_merit: str | None = None,
    detail_condition: str | None = None,
    detail_price_per_sqft: str | None = None,
    detail_price_vs_market: str | None = None,
    detail_market_conditions: str | None = None,
    price_per_sqft: float | None = None,
    thin_market_flag: bool | None = None,
    redfin_data_state: str | None = None,
    redfin_median_price: float | None = None,
    redfin_homes_sold: int | None = None,
    redfin_median_dom: float | None = None,
    redfin_sale_to_list: float | None = None,
    redfin_price_drops_pct: float | None = None,
    has_score: bool = False,
) -> None:
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    payload = {
        "slug": slug, "mls_number": mls_number, "webflow_item_id": webflow_item_id,
        "score": int(round(score)),  # published_listings.score is INTEGER — composite is now float
        "tier": tier, "category": category, "headline": headline,
        "hero_image_url": hero_image_url,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_date_ct": today_ct.isoformat(),
        "price": price,
        "is_deal_of_day": is_deal_of_day,
        "gallery_image_ids": gallery_image_ids or [],
        "list_date": list_date,
        "short_summary": short_summary,
        "social_caption": social_caption,
        "city": city,
        "state": state,
        # Scoring v2.0
        "composite_score": composite_score,
        "score_property_merit": score_property_merit,
        "score_condition": score_condition,
        "score_price_per_sqft": score_price_per_sqft,
        "score_price_vs_market": score_price_vs_market,
        "score_market_conditions": score_market_conditions,
        "detail_property_merit": detail_property_merit,
        "detail_condition": detail_condition,
        "detail_price_per_sqft": detail_price_per_sqft,
        "detail_price_vs_market": detail_price_vs_market,
        "detail_market_conditions": detail_market_conditions,
        "price_per_sqft": price_per_sqft,
        "thin_market_flag": thin_market_flag,
        "redfin_data_state": redfin_data_state,
        "redfin_median_price": redfin_median_price,
        "redfin_homes_sold": redfin_homes_sold,
        "redfin_median_dom": redfin_median_dom,
        "redfin_sale_to_list": redfin_sale_to_list,
        "redfin_price_drops_pct": redfin_price_drops_pct,
        "has_score": has_score,
    }
    try:
        r = requests.post(url, headers=_sb_headers(), json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase insert_published error: {e}")


def db_deal_of_day_chosen_today(today_ct: date) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug",
        "published_date_ct": f"eq.{today_ct.isoformat()}",
        "is_deal_of_day": "eq.true",
        "limit": 1,
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return len(r.json()) > 0
    except Exception as e:
        log.error(f"Supabase deal_of_day_chosen_today error: {e}")
        return False


def db_get_active_deal_of_day() -> dict | None:
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"select": "slug,webflow_item_id", "is_deal_of_day": "eq.true", "limit": 1}
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None
    except Exception as e:
        log.error(f"Supabase get_active_deal_of_day error: {e}")
        return None


def db_unset_deal_of_day(slug: str) -> None:
    """Set is_deal_of_day = false in Supabase for the outgoing Deal of the Day."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"slug": f"eq.{slug}"}
    try:
        r = requests.patch(url, headers=_sb_headers(), params=params,
                           json={"is_deal_of_day": False}, timeout=10)
        r.raise_for_status()
        log.info(f"Supabase: cleared is_deal_of_day for {slug}")
    except Exception as e:
        log.error(f"Supabase unset_deal_of_day error ({slug}): {e}")


def db_insert_run(run_data: dict) -> int | None:
    url = f"{SUPABASE_URL}/rest/v1/pipeline_runs"
    headers = _sb_headers()
    headers["Prefer"] = "return=representation"
    try:
        r = requests.post(url, headers=headers, json=run_data, timeout=10)
        r.raise_for_status()
        rows = r.json()
        return rows[0]["id"] if rows else None
    except Exception as e:
        log.error(f"Supabase insert_run error: {e}")
        return None


def db_update_run(run_id: int, update_data: dict) -> None:
    url = f"{SUPABASE_URL}/rest/v1/pipeline_runs"
    params = {"id": f"eq.{run_id}"}
    try:
        r = requests.patch(url, headers=_sb_headers(), params=params, json=update_data, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase update_run error: {e}")


# ---------------------------------------------------------------------------
# Token logging
# ---------------------------------------------------------------------------

def log_tokens(call_name: str, input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + \
           (output_tokens / 1000 * COST_PER_1K_OUTPUT)
    log.info(f"[TOKENS] {call_name} | in={input_tokens} out={output_tokens} | est_cost=${cost:.5f}")
    return cost


# ---------------------------------------------------------------------------
# RealtyAPI — Redfin market data
# ---------------------------------------------------------------------------

def _ra_headers() -> dict:
    return {"x-realtyapi-key": REALTYAPI_KEY}


def fetch_redfin_market_data(zip_code: str) -> dict | None:
    """Fetch /housingMarketTrends for a zip. Returns structured dict or None on true null."""
    try:
        r = requests.get(
            f"{REALTYAPI_REDFIN_BASE}/housingMarketTrends",
            headers=_ra_headers(),
            params={"location": zip_code},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        log.error(f"Redfin /housingMarketTrends failed [{zip_code}]: {e}")
        return None

    sections = data.get("sections", [])
    if not sections:
        log.info(f"Redfin null zip: {zip_code} — no sections returned")
        return None

    result = {
        "median_sale_price": 0,
        "homes_sold": 0,
        "median_dom": 0.0,
        "sale_to_list": 0.0,
        "price_drops_pct": 0.0,
        "aggregate_price_data": [],  # list of {"date": ..., "value": ...} newest first
    }
    found_any = False

    for section in sections:
        if section.get("error"):
            continue
        for metric in section.get("metrics", []):
            label = metric.get("label", "")
            raw_val = metric.get("value", "")
            agg = metric.get("aggregateData", [])

            if label == "Median Sale Price":
                try:
                    result["median_sale_price"] = int(float(str(raw_val).replace("$", "").replace(",", "")))
                    result["aggregate_price_data"] = agg
                    found_any = True
                except (ValueError, TypeError):
                    pass
            elif label == "# of Homes Sold":
                try:
                    result["homes_sold"] = int(float(str(raw_val)))
                    found_any = True
                except (ValueError, TypeError):
                    pass
            elif label == "Median Days on Market":
                try:
                    result["median_dom"] = float(str(raw_val))
                    found_any = True
                except (ValueError, TypeError):
                    pass
            elif label == "Sale-to-List Price":
                # value is a display string like "94.7%" — parse as ratio
                try:
                    raw_str = str(raw_val).replace("%", "").strip()
                    result["sale_to_list"] = float(raw_str) / 100.0
                    found_any = True
                except (ValueError, TypeError):
                    pass
            elif label == "Homes with Price Drops":
                # value is a display string like "40.8%"
                try:
                    raw_str = str(raw_val).replace("%", "").strip()
                    result["price_drops_pct"] = float(raw_str) / 100.0
                    found_any = True
                except (ValueError, TypeError):
                    pass

    if not found_any:
        log.info(f"Redfin null zip: {zip_code} — no usable metric data")
        return None

    log.info(
        f"Redfin [{zip_code}]: median=${result['median_sale_price']:,} "
        f"sold={result['homes_sold']} dom={result['median_dom']:.0f} "
        f"s2l={result['sale_to_list']*100:.1f}% drops={result['price_drops_pct']*100:.1f}%"
    )
    return result


def fetch_redfin_psf_data(zip_code: str) -> tuple[float | None, int]:
    """Fetch /recentlySold for a zip and return (median pricePerSqFt, comp_count).
    Returns (None, 0) on fetch failure. Returns (median, count) regardless of count —
    caller uses count to assess reliability; thin market flag set if count < 10.
    """
    try:
        r = requests.get(
            f"{REALTYAPI_REDFIN_BASE}/recentlySold",
            headers=_ra_headers(),
            params={"location": zip_code, "count": 50},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        log.error(f"Redfin /recentlySold failed [{zip_code}]: {e}")
        return None, 0

    homes = (data.get("homes") or {}).get("homes", [])
    psf_values = []
    for home in homes:
        psf = (home.get("pricePerSqFt") or {}).get("value")
        if psf and isinstance(psf, (int, float)) and psf > 0:
            psf_values.append(float(psf))

    count = len(psf_values)
    if count == 0:
        log.info(f"Redfin [{zip_code}]: 0 valid PSF values — no median available")
        return None, 0

    psf_values.sort()
    mid = count // 2
    if count % 2 == 0:
        median_psf = (psf_values[mid - 1] + psf_values[mid]) / 2.0
    else:
        median_psf = psf_values[mid]

    reliability = "thin" if count < 10 else "reliable"
    log.info(f"Redfin [{zip_code}]: zip median PSF=${median_psf:.0f} ({count} comps, {reliability})")
    return round(median_psf, 1), count


def is_thin_market(homes_sold: int, aggregate_price_data: list, psf_count: int) -> bool:
    """Return True if any thin-market condition applies."""
    if homes_sold < 10:
        return True
    if psf_count < 10:
        return True
    # Check MoM variance in trailing 6 months of median prices
    recent_vals = []
    for entry in aggregate_price_data[:6]:
        try:
            recent_vals.append(float(entry["value"]))
        except (KeyError, ValueError, TypeError):
            continue
    if len(recent_vals) < 2:
        return True  # insufficient history
    for i in range(len(recent_vals) - 1):
        current = recent_vals[i]
        prior = recent_vals[i + 1]
        if prior > 0 and abs(current - prior) / prior > 0.20:
            return True
    return False


# ---------------------------------------------------------------------------
# RealtyAPI — fetch listings + details
# ---------------------------------------------------------------------------


def fetch_search_results(state_name: str, result_count: int = 50, sort_order: str = "Newest") -> list[dict]:
    """Fetch active, non-pending for-sale listings under $150K in a given state."""
    params = {
        "location": state_name,
        "priceRange": "max:150000",
        "searchType": "For_Sale",
        "propertyType": "House,Townhome",
        "sortOrder": sort_order,
        "hasPhotos": True,
        "seniorCommunity": False,
        "pending": False,
        "resultCount": result_count,
    }
    try:
        r = requests.get(
            f"{REALTYAPI_REALTOR_BASE}/search/bylocation",
            headers=_ra_headers(),
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("searchResults", [])
        log.info(f"Realtor.com [{state_name}]: {len(results)} results")
        return results
    except requests.RequestException as e:
        log.error(f"Realtor.com search failed [{state_name}]: {e}")
        return []


def fetch_listing_details(property_id: str) -> dict | None:
    try:
        r = requests.get(
            f"{REALTYAPI_REALTOR_BASE}/details/byid",
            headers=_ra_headers(),
            params={"property_id": property_id},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        log.error(f"Realtor.com details failed [property {property_id}]: {e}")
        return None


def extract_description(details: dict | None) -> str:
    if not details:
        return ""
    detail = details.get("detail") or details
    inner = detail.get("details") or {}
    candidates = [
        inner.get("text", ""),
        detail.get("description", ""),
        detail.get("remarks", ""),
        detail.get("publicRemarks", ""),
    ]
    return next((c for c in candidates if isinstance(c, str) and len(c) > 10), "")


def extract_year_built(details: dict | None) -> int:
    if not details:
        return 0
    detail = details.get("detail") or details
    inner = detail.get("details") or {}
    return parse_int(inner.get("year_built") or 0)


def normalize_listing(result: dict, description: str) -> dict | None:
    prop = result.get("property_id", "")
    listing_id = result.get("listing_id", "")

    if not prop:
        return None

    address = result.get("address", {}) or {}
    street = address.get("line", "") or ""
    city = address.get("city", "") or ""
    state_abbr = address.get("state_code", "") or ""
    zip_code = address.get("postal_code", "") or ""
    state_full = STATE_FULL_NAME.get(state_abbr, state_abbr)

    # Use address as the stable dedup key — property_id can drift on RealtyAPI refreshes
    address_key = make_address_key(street, city, state_abbr)

    list_price = parse_int(result.get("list_price") or 0)
    beds = parse_int(result.get("beds") or 0)
    baths = parse_int(result.get("baths") or 0)
    sqft = parse_int(result.get("sqft") or 0)
    lot_sqft = parse_int(result.get("lot_sqft") or 0)
    lot_acres = round(lot_sqft / 43560, 2) if lot_sqft else None
    year_built = 0
    listing_href = result.get("href", "")

    # Capture list_date from RealtyAPI — stored in Supabase for DOM calculation at sale
    list_date = parse_list_date(result.get("list_date"))

    photos = []
    primary = result.get("primary_photo", "")
    if isinstance(primary, str) and primary:
        photos.append(primary)
    elif isinstance(primary, dict) and primary.get("href"):
        photos.append(primary["href"])
    for photo in (result.get("photos") or []):
        url = photo if isinstance(photo, str) else (photo.get("href", "") if isinstance(photo, dict) else "")
        if url and url not in photos:
            photos.append(url)

    desc_lower = description.lower()
    waterfront = any(w in desc_lower for w in [
        "waterfront", "water front", "lakefront", "lake front",
        "riverfront", "river front", "oceanfront", "pond",
    ])
    pool = "pool" in desc_lower

    return {
        "mlsNumber": address_key,   # stable address-based dedup key
        "propertyId": prop,         # retained for detail fetches only
        "listingId": listing_id,
        "listingHref": listing_href,
        "listPrice": list_price,
        "listDate": list_date,      # ISO date string YYYY-MM-DD or None
        "address": {
            "formattedStreetLine": street,
            "city": city,
            "state": state_abbr,
            "stateFull": state_full,
            "zip": zip_code,
        },
        "details": {
            "numBedrooms": beds,
            "numBathrooms": baths,
            "sqft": sqft,
            "yearBuilt": year_built,
            "description": description,
            "lotAcres": lot_acres,
            "waterfront": waterfront,
            "pool": pool,
        },
        "images": photos,
    }


def fetch_listings() -> list[dict]:
    target = 50
    collected = []
    seen_address_keys = set()  # in-run dedup by address key

    states = random.sample(US_STATES, min(20, len(US_STATES)))

    sort_order = random.choice(REALTYAPI_SORT_ORDERS)
    log.info(f"Sort order this run: {sort_order}")

    for state in states:
        if len(collected) >= target:
            break

        results = fetch_search_results(state, result_count=50, sort_order=sort_order)
        if not results:
            continue

        random.shuffle(results)

        # Build address keys for batch suppression check
        address_keys_this_state = []
        result_to_key = {}
        for r in results:
            addr = r.get("address", {}) or {}
            key = make_address_key(
                addr.get("line", "") or "",
                addr.get("city", "") or "",
                addr.get("state_code", "") or "",
            )
            address_keys_this_state.append(key)
            result_to_key[r.get("property_id", "")] = key

        seen_keys = db_batch_seen_recently(address_keys_this_state)
        log.info(f"[{state}] {len(seen_keys)}/{len(address_keys_this_state)} already seen")

        for result in results:
            if len(collected) >= target:
                break

            prop_id = result.get("property_id", "")
            if not prop_id:
                continue

            address_key = result_to_key.get(prop_id, "")
            if not address_key or address_key in seen_address_keys:
                continue

            if address_key in seen_keys:
                continue

            details = fetch_listing_details(prop_id)
            time.sleep(0.2)

            description = extract_description(details)
            year_built = extract_year_built(details)

            listing = normalize_listing(result, description)
            if not listing:
                continue

            listing["details"]["yearBuilt"] = year_built
            listing["_state"] = state

            if listing["listPrice"] <= 0:
                continue

            seen_address_keys.add(address_key)
            collected.append(listing)
            break

    log.info(f"Fetched {len(collected)} total listings")
    return collected


# ---------------------------------------------------------------------------
# Claude API
# ---------------------------------------------------------------------------

def call_claude(system: str, user: str, call_name: str, max_tokens: int = CLAUDE_MAX_TOKENS_SCORING) -> tuple[str | None, float]:
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "prompt-caching-2024-07-31",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": user}],
    }
    try:
        r = requests.post(ANTHROPIC_BASE, headers=headers, json=body, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Claude API error ({call_name}): {e}")
        return None, 0.0

    data = r.json()
    usage = data.get("usage", {})
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    if cache_read or cache_write:
        log.info(f"[CACHE] {call_name} | read={cache_read} write={cache_write}")
    cost = log_tokens(call_name, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
    content_blocks = data.get("content", [])
    text_blocks = [b["text"] for b in content_blocks if b.get("type") == "text"]
    return "\n".join(text_blocks).strip() if text_blocks else None, cost


# ---------------------------------------------------------------------------
# Call 1 — Scoring
# ---------------------------------------------------------------------------

def build_scoring_input(
    listing: dict,
    redfin_market: dict | None,
    zip_median_psf: float | None,
    price_per_sqft: float | None,
    days_listed: int | None = None,
) -> str:
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    price      = parse_int(listing.get("listPrice", 0))
    address    = addr.get("formattedStreetLine", "")
    city       = addr.get("city", "")
    state      = addr.get("state", "")
    zip_code   = addr.get("zip", "unknown")
    beds       = parse_int(details.get("numBedrooms"))
    baths      = parse_int(details.get("numBathrooms"))
    sqft       = parse_int(details.get("sqft"))
    year       = parse_int(details.get("yearBuilt"))
    lot_acres  = details.get("lotAcres")
    if lot_acres and beds <= 2 and sqft < 900:
        lot_acres = None
    acreage    = str(lot_acres) if lot_acres else "null"
    waterfront = "Y" if details.get("waterfront") else "N"
    pool       = "Y" if details.get("pool") else "N"
    description = details.get("description", "") or "(no description)"

    psf_str     = f"${price_per_sqft:.0f}/sqft" if price_per_sqft else "null (sqft unavailable)"

    # List age signal
    if days_listed is not None and days_listed >= 180:
        list_age_str = f"{days_listed} days on market — approaching stale territory, market has passed on this repeatedly"
    elif days_listed is not None and days_listed >= 90:
        list_age_str = f"{days_listed} days on market"
    elif days_listed is not None:
        list_age_str = f"{days_listed} days on market"
    else:
        list_age_str = "unknown"

    if redfin_market:
        median_price   = redfin_market.get("median_sale_price", 0)
        homes_sold     = redfin_market.get("homes_sold", 0)
        median_dom     = redfin_market.get("median_dom", 0.0)
        sale_to_list   = redfin_market.get("sale_to_list", 0.0)
        price_drops    = redfin_market.get("price_drops_pct", 0.0)
        thin           = redfin_market.get("thin_market", False)
        psf_count      = redfin_market.get("psf_comp_count", 0)
        if zip_median_psf and psf_count < 10:
            zip_psf_str = f"${zip_median_psf:.0f}/sqft ({psf_count} comps, thin — treat as directional)"
        elif zip_median_psf:
            zip_psf_str = f"${zip_median_psf:.0f}/sqft ({psf_count} comps)"
        else:
            zip_psf_str = "unavailable"
        market_block = (
            f"ZIP_MEDIAN_SALE_PRICE: ${median_price:,}\n"
            f"ZIP_HOMES_SOLD_LAST_MONTH: {homes_sold}\n"
            f"ZIP_MEDIAN_DOM: {median_dom:.0f} days\n"
            f"ZIP_SALE_TO_LIST: {sale_to_list * 100:.1f}%\n"
            f"ZIP_PRICE_DROPS_PCT: {price_drops * 100:.1f}%\n"
            f"ZIP_MEDIAN_PSF: {zip_psf_str}\n"
            f"MARKET_DATA_STATE: {'thin' if thin else 'reliable'}"
        )
    else:
        zip_psf_str = "unavailable"
        market_block = "MARKET_DATA_STATE: null (no Redfin data available for this zip)"

    return f"""PRICE: {price}
ADDRESS: {address}
CITY: {city}
STATE: {state}
BEDROOMS: {beds}
BATHROOMS: {baths}
SQFT: {sqft}
YEAR_BUILT: {year}
ACREAGE: {acreage}
POOL: {pool}
WATERFRONT: {waterfront}
LISTING_PSF: {psf_str}
DAYS_ON_MARKET: {list_age_str}

REDFIN MARKET DATA (zip {zip_code}):
{market_block}

DESCRIPTION: {description}"""


def parse_scoring_output(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()

    # Parse THIN_MARKET boolean
    thin_raw = result.get("THIN_MARKET", "false").lower()
    result["THIN_MARKET"] = thin_raw in ("true", "yes", "1")

    # Parse float category score fields (default 5.0 if missing/malformed)
    for field in ("SCORE_PROPERTY_MERIT", "SCORE_CONDITION", "SCORE_PRICE_PER_SQFT",
                  "SCORE_PRICE_VS_MARKET", "SCORE_MARKET_CONDITIONS"):
        try:
            result[field] = round(float(result.get(field, "5")), 1)
        except (ValueError, TypeError):
            result[field] = 5.0

    return result


def prefilter_listing(listing: dict) -> bool:
    details = listing.get("details", {})
    description = details.get("description", "") or ""
    desc_lower = description.lower()
    beds = parse_int(details.get("numBedrooms"))
    sqft = parse_int(details.get("sqft"))
    lot_acres = details.get("lotAcres")
    year_built = parse_int(details.get("yearBuilt"))
    waterfront = details.get("waterfront", False)
    pool = details.get("pool", False)

    has_floor = (
        waterfront
        or pool
        or (lot_acres and lot_acres >= 0.5 and not (beds <= 2 and sqft < 900))
        or year_built > 0 and year_built <= 1950
        or any(w in desc_lower for w in ["waterfront", "lakefront", "riverfront", "lake view", "mountain view", "wooded"])
    )
    if has_floor:
        return True

    if len(description.strip()) < 30:
        log.info(f"[PREFILTER] Skipping — no description, no floor qualifier")
        return False

    flipper_signals = ["bring your vision", "investor special", "blank canvas", "as-is", "cash only", "cash-only"]
    character_signals = ["hardwood", "original", "fireplace", "porch", "beams", "stained glass", "victorian",
                         "craftsman", "bungalow", "farmhouse", "barn", "garage", "basement", "renovated",
                         "updated", "new roof", "new hvac", "new windows", "pool", "acre", "lake", "creek"]
    flipper_count = sum(1 for s in flipper_signals if s in desc_lower)
    character_count = sum(1 for s in character_signals if s in desc_lower)
    if flipper_count >= 2 and character_count == 0:
        log.info(f"[PREFILTER] Skipping — investor language, no character signals")
        return False

    if any(w in desc_lower for w in ["manufactured", "mobile home", "modular", "double wide", "doublewide", "single wide"]):
        log.info(f"[PREFILTER] Skipping — manufactured/mobile home")
        return False

    if beds == 0 or baths == 0:
        log.info(f"[PREFILTER] Skipping — beds={beds} baths={baths} — not a liveable home")
        return False

    return True


def score_listing(
    listing: dict,
    redfin_market: dict | None,
    zip_median_psf: float | None,
    price_per_sqft: float | None,
    days_listed: int | None = None,
) -> tuple[dict | None, float]:
    scoring_input = build_scoring_input(listing, redfin_market, zip_median_psf, price_per_sqft, days_listed)
    raw, cost = call_claude(SCORING_PROMPT, scoring_input, "scoring")
    if not raw:
        return None, cost
    parsed = parse_scoring_output(raw)
    # SCORE is the composite — parse as float (one decimal)
    try:
        score_val = round(float(parsed.get("SCORE", "0")), 1)
    except (ValueError, TypeError):
        score_val = 0.0
    parsed["SCORE"] = score_val
    log.info(
        f"Score: {score_val} | Tier: {parsed.get('TIER')} | "
        f"Category: {parsed.get('CATEGORY')} | {parsed.get('REASON', '')[:80]}"
    )
    return parsed, cost


# ---------------------------------------------------------------------------
# Call 2 — Content generation
# ---------------------------------------------------------------------------

CLAUDE_MAX_TOKENS_REVIEW = 900


def generate_content(listing: dict, score_data: dict) -> tuple[dict | None, float]:
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    composite = score_data.get("SCORE", 0)
    listing_data = (
        f"ADDRESS: {addr.get('formattedStreetLine', '')}\n"
        f"CITY: {addr.get('city', '')}\n"
        f"STATE: {addr.get('stateFull', addr.get('state', ''))}\n"
        f"PRICE: ${make_price_display(parse_int(listing.get('listPrice', 0)))}\n"
        f"BEDS: {parse_int(details.get('numBedrooms'))} | "
        f"BATHS: {parse_int(details.get('numBathrooms'))} | "
        f"SQFT: {parse_int(details.get('sqft'))} | "
        f"YEAR BUILT: {parse_int(details.get('yearBuilt'))}\n"
        f"COMPOSITE SCORE: {composite}/10\n"
        f"SCORE_PROPERTY_MERIT: {score_data.get('SCORE_PROPERTY_MERIT', '')} | "
        f"SCORE_CONDITION: {score_data.get('SCORE_CONDITION', '')} | "
        f"SCORE_PRICE_PER_SQFT: {score_data.get('SCORE_PRICE_PER_SQFT', '')} | "
        f"SCORE_PRICE_VS_MARKET: {score_data.get('SCORE_PRICE_VS_MARKET', '')} | "
        f"SCORE_MARKET_CONDITIONS: {score_data.get('SCORE_MARKET_CONDITIONS', '')}\n"
        f"DETAIL_PROPERTY_MERIT: {score_data.get('DETAIL_PROPERTY_MERIT', '')}\n"
        f"DETAIL_CONDITION: {score_data.get('DETAIL_CONDITION', '')}\n"
        f"DETAIL_PRICE_PER_SQFT: {score_data.get('DETAIL_PRICE_PER_SQFT', '')}\n"
        f"DETAIL_PRICE_VS_MARKET: {score_data.get('DETAIL_PRICE_VS_MARKET', '')}\n"
        f"DETAIL_MARKET_CONDITIONS: {score_data.get('DETAIL_MARKET_CONDITIONS', '')}\n"
        f"EDITORIAL CATEGORY: {score_data.get('CATEGORY', '')}\n"
        f"KEY HOOKS: {score_data.get('KEY_HOOKS', '')}\n\n"
        f"AGENT DESCRIPTION — this is real estate marketing copy written to sell the property. "
        f"Its tone, structure, sentence patterns, and phrasing are examples of exactly what not to do. "
        f"Extract facts only. Do not let any of it influence how you write:\n"
        f"{details.get('description', '') or '(no description)'}"
    )
    raw, content_cost = call_claude(CONTENT_PROMPT_TEMPLATE, listing_data, "content_gen", max_tokens=CLAUDE_MAX_TOKENS_CONTENT)
    if not raw:
        return None, content_cost

    return parse_content_output(raw), content_cost


def parse_content_output(text: str) -> dict:
    result = {"HEADLINE": "", "NARRATIVE": "", "SOCIAL_CAPTION": "", "SHORT_SUMMARY": ""}
    labels = list(result.keys())
    current_label = None
    current_lines = []

    for line in text.splitlines():
        stripped = line.strip().lstrip('#').strip().replace('**', '').strip()
        if stripped in ("---", "----"):
            continue
        matched_label = next((l for l in labels if stripped == l or stripped == f"{l}:"), None)
        if matched_label:
            if current_label and current_lines:
                result[current_label] = "\n".join(current_lines).strip()
            current_label = matched_label
            current_lines = []
        elif current_label:
            current_lines.append(line)

    if current_label and current_lines:
        result[current_label] = "\n".join(current_lines).strip()

    if not result["HEADLINE"] or not result["NARRATIVE"]:
        log.warning(f"[CONTENT] parse_content_output missing fields — raw text snippet: {text[:200]}")

    return result


# ---------------------------------------------------------------------------
# Cloudflare Images
# ---------------------------------------------------------------------------

def upload_image(image_url: str, slug: str) -> tuple[str | None, str | None]:
    """Upload one image to Cloudflare. Returns (delivery_url, image_id) or (None, None) on failure."""
    if "imagedelivery.net" in image_url:
        parts = image_url.rstrip("/").split("/")
        image_id = parts[-2] if len(parts) >= 3 else None
        return image_url, image_id

    if not image_url.startswith("http"):
        image_url = f"https://cdn.repliers.io/{image_url}"

    log.info(f"Fetching image: {image_url}")
    try:
        img_r = requests.get(image_url, timeout=30)
        img_r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to fetch image: {e}")
        return None, None

    log.info(f"Uploading to Cloudflare ({len(img_r.content)} bytes)...")
    try:
        cf_r = requests.post(
            CF_IMAGES_BASE,
            headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
            files={"file": (f"{slug}.jpg", img_r.content, img_r.headers.get("content-type", "image/jpeg"))},
            timeout=60,
        )
        cf_r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Cloudflare upload failed: {e}")
        return None, None

    cf_data = cf_r.json()
    if not cf_data.get("success"):
        log.error(f"Cloudflare error: {cf_data.get('errors')}")
        return None, None

    image_id = cf_data.get("result", {}).get("id")
    variants = cf_data.get("result", {}).get("variants", [])

    if variants:
        delivery_url = variants[0]
    elif image_id:
        delivery_url = f"{CF_DELIVERY_BASE}/{image_id}/public"
    else:
        return None, None

    log.info(f"Cloudflare upload OK: {delivery_url}")
    return delivery_url, image_id


def upload_gallery_images(
    images: list[str], slug: str, city: str, state_full: str
) -> tuple[list[dict], list[str]]:
    """Upload up to GALLERY_PHOTO_COUNT photos (indices 1 onward, skipping hero at index 0)."""
    gallery_field_data = []
    gallery_image_ids = []

    candidates = images[1:GALLERY_PHOTO_COUNT + 1]

    for i, photo_url in enumerate(candidates):
        delivery_url, image_id = upload_image(photo_url, f"{slug}-gallery-{i + 1}")
        if delivery_url and image_id:
            # photo_index 1-3 for gallery (0 is reserved for hero)
            alt = make_image_alt(city, state_full, i + 1, slug)
            gallery_field_data.append({"url": delivery_url, "alt": alt})
            gallery_image_ids.append(image_id)
            log.info(f"Gallery photo {i + 1}/{len(candidates)} uploaded: {image_id} | alt: {alt}")
        else:
            log.warning(f"Gallery photo {i + 1}/{len(candidates)} failed — skipping")

    log.info(f"Gallery: {len(gallery_field_data)}/{len(candidates)} photos uploaded")
    return gallery_field_data, gallery_image_ids


# ---------------------------------------------------------------------------
# Webflow CMS
# ---------------------------------------------------------------------------

def write_webflow(
    listing: dict, score_data: dict, content: dict,
    hero_image_url: str, is_hero: bool,
    gallery_field_data: list[dict] | None = None,
    price_per_sqft: float | None = None,
) -> str | None:
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    price      = parse_int(listing.get("listPrice", 0))
    city       = addr.get("city", "")
    state_abbr = addr.get("state", "")
    state_full = addr.get("stateFull", state_abbr)
    address    = addr.get("formattedStreetLine", "")
    zip_code   = addr.get("zip", "")
    slug       = make_slug(address, city, state_abbr)
    beds       = parse_int(details.get("numBedrooms"))
    baths      = parse_int(details.get("numBathrooms"))
    sqft       = parse_int(details.get("sqft"))
    year       = parse_int(details.get("yearBuilt"))

    headline    = content.get("HEADLINE", "")
    name        = headline if headline else f"{city}, {state_full} — ${make_price_display(price)}"

    # Hero image uses photo_index 0 — gets a GSC-aligned alt pattern distinct from gallery images
    hero_alt = make_image_alt(city, state_full, 0, slug)

    field_data = {
        "name":             name,
        "slug":             slug,
        "price":            price,
        "price-display":    make_price_display(price),
        "location-display": f"{city}, {state_full}",
        "address":          address,
        "city":             city,
        "state":            state_abbr,
        "us-state":         STATE_TO_WEBFLOW_ITEM_ID.get(state_abbr),
        "year-built":       year,
        "bedrooms":         beds,
        "bathrooms":        baths,
        "square-feet":      sqft,
        "hero-image":       {"url": hero_image_url, "alt": hero_alt},
        "narrative-body":   format_richtext(content.get("NARRATIVE", "")),
        "short-summary":    content.get("SHORT_SUMMARY", ""),
        "listing-url":      f"https://www.housesunder150k.com/listings/{slug}",
        "state-page-url":   f"https://www.housesunder150k.com/states/{STATE_TO_SLUG.get(state_abbr, '')}" if state_abbr in STATE_TO_SLUG else None,
        "affiliate-url":    listing.get("listingHref") or make_realtor_url(address, city, state_abbr, zip_code),
        "social-caption":   content.get("SOCIAL_CAPTION", ""),
        "tags":             generate_tags(score_data, listing),
        "status":           WF_STATUS_ACTIVE,
        "deal-of-the-day":  is_hero,
        # Score table fields
        "composite-score":        score_data.get("SCORE"),
        "score-property-merit":   score_data.get("SCORE_PROPERTY_MERIT"),
        "score-condition":         score_data.get("SCORE_CONDITION"),
        "score-price-per-sqft":   score_data.get("SCORE_PRICE_PER_SQFT"),
        "score-price-vs-market":  score_data.get("SCORE_PRICE_VS_MARKET"),
        "score-market-conditions": score_data.get("SCORE_MARKET_CONDITIONS"),
        "detail-property-merit":  score_data.get("DETAIL_PROPERTY_MERIT") or "",
        "detail-condition":        score_data.get("DETAIL_CONDITION") or "",
        "detail-price-per-sqft":  score_data.get("DETAIL_PRICE_PER_SQFT") or "",
        "detail-price-vs-market": score_data.get("DETAIL_PRICE_VS_MARKET") or "",
        "detail-market-conditions": score_data.get("DETAIL_MARKET_CONDITIONS") or "",
        "thin-market-flag":       bool(score_data.get("THIN_MARKET", False)),
        "price-per-sqft":         price_per_sqft,
        # has-score intentionally omitted here — written LAST in a separate PATCH below
    }

    if gallery_field_data:
        field_data["gallery-images"] = gallery_field_data

    # Remove None values from score number fields to avoid Webflow type errors
    field_data = {k: v for k, v in field_data.items() if v is not None or k in (
        "thin-market-flag", "deal-of-the-day", "narrative-body", "short-summary",
        "social-caption", "tags",
    )}

    wf_headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    log.info(f"Writing to Webflow: {name} | hero_alt: {hero_alt}")
    try:
        r = requests.post(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items",
            headers=wf_headers,
            json={"fieldData": field_data},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Webflow write failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            log.error(f"Webflow response: {e.response.text[:500]}")
        return None

    item_id = r.json().get("id")
    log.info(f"Webflow item created: {item_id}")

    # Write has-score LAST — only after all other fields confirmed written.
    # If this PATCH fails, has-score stays false and the score table stays hidden.
    try:
        patch_r = requests.patch(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/{item_id}",
            headers=wf_headers,
            json={"fieldData": {"has-score": True}},
            timeout=30,
        )
        patch_r.raise_for_status()
        log.info(f"Webflow has-score set: {item_id}")
    except requests.RequestException as e:
        log.error(f"Webflow has-score PATCH failed ({item_id}): {e} — score table will stay hidden")
        # Do not return None — the item was created successfully; only has-score failed

    return item_id


def publish_webflow(item_id: str) -> bool:
    headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    try:
        r = requests.post(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/publish",
            headers=headers,
            json={"itemIds": [item_id]},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Webflow publish failed: {e}")
        return False
    log.info(f"Published: {item_id}")
    return True


def unset_deal_of_the_day(prior: dict) -> bool:
    """Clear deal-of-the-day from outgoing holder in both Webflow and Supabase."""
    item_id = prior.get("webflow_item_id", "")
    slug    = prior.get("slug", "")

    headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    try:
        r = requests.patch(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/{item_id}",
            headers=headers,
            json={"fieldData": {"deal-of-the-day": False}},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to clear previous deal-of-the-day in Webflow ({item_id}): {e}")
        return False

    log.info(f"Cleared deal-of-the-day in Webflow: {item_id}")
    if slug:
        db_unset_deal_of_day(slug)
    return publish_webflow(item_id)


WEBFLOW_SITE_ID       = "6a650a7eb2639262c4b6adb7"
WEBFLOW_DOMAIN_IDS    = ["6a661987994ab168be06566b", "6a661986994ab168be065664"]


def publish_site() -> bool:
    headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    try:
        r = requests.post(
            f"{WEBFLOW_BASE}/sites/{WEBFLOW_SITE_ID}/publish",
            headers=headers,
            json={"customDomains": WEBFLOW_DOMAIN_IDS},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Webflow site publish failed: {e}")
        return False
    log.info("Site published to housesunder150k.com")
    return True


# ---------------------------------------------------------------------------
# Per-listing pipeline
# ---------------------------------------------------------------------------

def process_listing(
    listing: dict,
    today_ct: date,
    dod_available: bool,
    redfin_market_cache: dict,
    redfin_psf_cache: dict,
    run_stats: dict,
) -> tuple[str, float, bool]:
    addr       = listing.get("address", {})
    price      = parse_int(listing.get("listPrice", 0))
    city       = addr.get("city", "unknown")
    state_full = addr.get("stateFull", addr.get("state", ""))
    zip_code   = addr.get("zip", "")
    address_key = listing.get("mlsNumber", "unknown")
    slug       = make_slug(addr.get("formattedStreetLine", ""), city, addr.get("state", ""))
    list_date  = listing.get("listDate")
    total_cost = 0.0

    # Calculate days since listing
    list_date  = listing.get("listDate")
    days_listed = None
    if list_date:
        try:
            listed_on = date.fromisoformat(list_date)
            days_listed = (get_today_ct() - listed_on).days
        except (ValueError, TypeError):
            pass

    # Hard prefilter: listings on market 365+ days are market rejects, not hidden gems
    if days_listed is not None and days_listed >= 365:
        log.info(f"Skipping {slug} — on market {days_listed} days (listed {list_date}) — market reject")
        db_upsert_seen(address_key, slug, 0, "SKIP")
        return "skipped_score", 0.0, False

    log.info(f"--- Processing: {city} ${make_price_display(price)} ({address_key}) zip={zip_code} ---")

    if db_slug_published(slug):
        log.info(f"Skipping {slug} — already published")
        return "skipped_dedup", 0.0, False

    seen = db_mls_seen_recently(address_key)
    if seen:
        log.info(f"Skipping {address_key} — seen score={seen['score']} within {SEEN_SUPPRESSION_DAYS}d")
        db_upsert_seen(address_key, slug, seen["score"], seen["tier"])
        return "skipped_seen", 0.0, False

    if not prefilter_listing(listing):
        db_upsert_seen(address_key, slug, 2, "SKIP")
        return "skipped_score", 0.0, False

    # --- Redfin market data fetch (cached per zip per run) ---
    if zip_code and zip_code not in redfin_market_cache:
        redfin_market_cache[zip_code] = fetch_redfin_market_data(zip_code)
        redfin_psf_cache[zip_code] = fetch_redfin_psf_data(zip_code)  # (median, count)
        run_stats["redfin_api_credits_used"] += 2
        time.sleep(0.2)

    redfin_market = redfin_market_cache.get(zip_code) if zip_code else None
    psf_result = redfin_psf_cache.get(zip_code) if zip_code else (None, 0)
    zip_median_psf, psf_comp_count = psf_result if psf_result else (None, 0)

    # True null — no Redfin data at all: skip this listing
    if zip_code and redfin_market is None:
        skip_reason = f"redfin_null_zip_{zip_code}"
        log.info(f"Skipping {slug} — {skip_reason}")
        run_stats["redfin_null_skips"] += 1
        db_upsert_seen(address_key, slug, 0, "SKIP")
        return "skipped_redfin_null", 0.0, False

    # Assess thin market and stamp onto redfin_market dict for downstream use
    if redfin_market:
        thin = is_thin_market(
            redfin_market["homes_sold"],
            redfin_market["aggregate_price_data"],
            psf_comp_count,
        )
        redfin_market["thin_market"] = thin
        redfin_market["psf_comp_count"] = psf_comp_count
        if thin:
            run_stats["redfin_thin_market_count"] += 1
            log.info(f"Thin market: zip {zip_code}")
        redfin_data_state = "thin" if thin else "reliable"
    else:
        redfin_data_state = "null"

    # Calculate price_per_sqft
    sqft = parse_int(listing.get("details", {}).get("sqft"))
    price_per_sqft = round(price / sqft, 1) if sqft > 0 else None

    score_data, score_cost = score_listing(listing, redfin_market, zip_median_psf, price_per_sqft, days_listed)
    total_cost += score_cost
    if not score_data:
        return "error", total_cost, False

    score = score_data.get("SCORE", 0)
    tier  = score_data.get("TIER", "SKIP")
    db_upsert_seen(address_key, slug, score, tier)

    if score < 6 or tier in ("BELOW_THRESHOLD", "SKIP"):
        log.info(f"Score {score} tier={tier} — discarding {slug}")
        return "skipped_score", total_cost, False

    content, content_cost = generate_content(listing, score_data)
    total_cost += content_cost
    if not content:
        return "error", total_cost, False
    if not content.get("HEADLINE") or not content.get("NARRATIVE"):
        log.error(f"Content generation returned empty fields for {slug} — skipping Webflow write")
        return "error", total_cost, False

    images = listing.get("images", [])

    hero_image_url, _ = upload_image(images[0], slug) if images else (None, None)
    if not hero_image_url:
        log.warning(f"No hero image for {slug}")
        hero_image_url = ""

    gallery_field_data, gallery_image_ids = (
        upload_gallery_images(images, slug, city, state_full)
        if len(images) > 1 else ([], [])
    )

    claude_wants_hero = score_data.get("DEAL_OF_DAY_CANDIDATE", "NO").upper() == "YES"
    is_hero = claude_wants_hero and dod_available
    if claude_wants_hero and not dod_available:
        log.info(f"{slug} qualifies for deal-of-the-day but slot already taken today")

    if is_hero:
        prior = db_get_active_deal_of_day()
        if prior and prior.get("webflow_item_id"):
            unset_deal_of_the_day(prior)

    item_id = write_webflow(
        listing, score_data, content, hero_image_url, is_hero,
        gallery_field_data, price_per_sqft,
    )
    if not item_id:
        return "error", total_cost, False

    if not publish_webflow(item_id):
        return "error", total_cost, False

    db_insert_published(
        slug=slug, mls_number=address_key, webflow_item_id=item_id,
        score=score, tier=tier, category=score_data.get("CATEGORY", ""),
        headline=content.get("HEADLINE", ""), hero_image_url=hero_image_url,
        today_ct=today_ct, price=price,
        is_deal_of_day=is_hero,
        gallery_image_ids=gallery_image_ids,
        list_date=list_date,
        short_summary=content.get("SHORT_SUMMARY", "") or None,
        social_caption=content.get("SOCIAL_CAPTION", "") or None,
        city=addr.get("city") or None,
        state=addr.get("state") or None,
        # Scoring v2.0
        composite_score=score,
        score_property_merit=score_data.get("SCORE_PROPERTY_MERIT"),
        score_condition=score_data.get("SCORE_CONDITION"),
        score_price_per_sqft=score_data.get("SCORE_PRICE_PER_SQFT"),
        score_price_vs_market=score_data.get("SCORE_PRICE_VS_MARKET"),
        score_market_conditions=score_data.get("SCORE_MARKET_CONDITIONS"),
        detail_property_merit=score_data.get("DETAIL_PROPERTY_MERIT") or None,
        detail_condition=score_data.get("DETAIL_CONDITION") or None,
        detail_price_per_sqft=score_data.get("DETAIL_PRICE_PER_SQFT") or None,
        detail_price_vs_market=score_data.get("DETAIL_PRICE_VS_MARKET") or None,
        detail_market_conditions=score_data.get("DETAIL_MARKET_CONDITIONS") or None,
        price_per_sqft=price_per_sqft,
        thin_market_flag=bool(score_data.get("THIN_MARKET", False)),
        redfin_data_state=redfin_data_state,
        redfin_median_price=redfin_market.get("median_sale_price") if redfin_market else None,
        redfin_homes_sold=redfin_market.get("homes_sold") if redfin_market else None,
        redfin_median_dom=redfin_market.get("median_dom") if redfin_market else None,
        redfin_sale_to_list=redfin_market.get("sale_to_list") if redfin_market else None,
        redfin_price_drops_pct=redfin_market.get("price_drops_pct") if redfin_market else None,
        has_score=True,
    )

    log.info(
        f"Published: {slug} (score={score}, tier={tier}, deal_of_day={is_hero}, "
        f"gallery_photos={len(gallery_image_ids)}, list_date={list_date}, "
        f"redfin_state={redfin_data_state}, psf={price_per_sqft})"
    )
    return "published", total_cost, is_hero


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline():
    log.info("=== HousesUnder150K Ingestion Pipeline Start ===")
    start = time.time()
    today_ct = get_today_ct()

    run_id = db_insert_run({"started_at": datetime.now(timezone.utc).isoformat()})

    count_today = db_count_published_today(today_ct)
    log.info(f"Published today (CT): {count_today}/{DAILY_PUBLISH_LIMIT}")

    if count_today >= DAILY_PUBLISH_LIMIT:
        log.info("Daily limit reached — exiting")
        if run_id:
            db_update_run(run_id, {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "daily_limit_hit": True,
                "notes": f"Daily limit {count_today}/{DAILY_PUBLISH_LIMIT} already reached",
            })
        return

    listings = fetch_listings()
    if not listings:
        log.info("No listings returned — exiting")
        if run_id:
            db_update_run(run_id, {"completed_at": datetime.now(timezone.utc).isoformat(), "listings_fetched": 0})
        return

    stats = {"published": 0, "skipped_score": 0, "skipped_dedup": 0, "skipped_seen": 0,
             "skipped_redfin_null": 0, "error": 0}
    total_cost = 0.0
    published_this_run = 0
    dod_available = not db_deal_of_day_chosen_today(today_ct)
    log.info(f"Deal-of-the-day available today: {dod_available}")

    # Redfin zip caches and run-level counters (shared across all listings in this run)
    redfin_market_cache: dict = {}
    redfin_psf_cache: dict = {}
    run_stats = {"redfin_null_skips": 0, "redfin_thin_market_count": 0, "redfin_api_credits_used": 0}

    for listing in listings:
        if count_today + published_this_run >= DAILY_PUBLISH_LIMIT:
            log.info("Daily limit reached mid-batch — stopping")
            break

        try:
            result, cost, dod_used = process_listing(
                listing, today_ct, dod_available,
                redfin_market_cache, redfin_psf_cache, run_stats,
            )
            stats[result] = stats.get(result, 0) + 1
            total_cost += cost
            if result == "published":
                published_this_run += 1
            if dod_used:
                dod_available = False
        except Exception as e:
            log.error(f"Unhandled error: {e}", exc_info=True)
            stats["error"] += 1

        time.sleep(1)

    elapsed = time.time() - start
    log.info(
        f"=== Pipeline complete in {elapsed:.1f}s | "
        f"published={stats['published']} skipped_score={stats['skipped_score']} "
        f"skipped_seen={stats['skipped_seen']} skipped_dedup={stats['skipped_dedup']} "
        f"skipped_redfin_null={stats['skipped_redfin_null']} "
        f"errors={stats['error']} est_cost=${total_cost:.5f} "
        f"redfin_credits={run_stats['redfin_api_credits_used']} ==="
    )

    if run_id:
        db_update_run(run_id, {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "listings_fetched": len(listings),
            "listings_scored": stats["skipped_score"] + stats["published"],
            "listings_skipped": stats["skipped_seen"] + stats["skipped_dedup"],
            "published": stats["published"],
            "errors": stats["error"],
            "est_cost_usd": round(total_cost, 5),
            "daily_limit_hit": (count_today + published_this_run) >= DAILY_PUBLISH_LIMIT,
            "redfin_null_skips": run_stats["redfin_null_skips"],
            "redfin_thin_market_count": run_stats["redfin_thin_market_count"],
            "redfin_api_credits_used": run_stats["redfin_api_credits_used"],
        })

    if published_this_run > 0:
        publish_site()


if __name__ == "__main__":
    run_pipeline()
