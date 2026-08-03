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
CLAUDE_MAX_TOKENS_SCORING   = 250
CLAUDE_MAX_TOKENS_CONTENT   = 900
REALTYAPI_REALTOR_BASE = "https://realtor.realtyapi.io"
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

SCORING_PROMPT = """Score this residential listing for HousesUnder150K.com on editorial merit (1-10). Be strict — most listings score 4 or below. Only genuinely interesting listings score 6+. Low price alone is never enough.

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
SCORE: [1-10]
TIER: [SKIP / BELOW_THRESHOLD / PUBLISH / FEATURED / HERO]
CATEGORY: [NEW_CONSTRUCTION / WATERFRONT / ACREAGE / HISTORIC / RENOVATED / CHARACTER / HIDDEN_GEM / TOO_GOOD_TO_BE_TRUE / WHAT_IF]
KEY_HOOKS: [2-4 specific compelling facts, comma separated]
REASON: [1-2 sentences]
DEAL_OF_DAY_CANDIDATE: [YES / NO]

TIER MAP: 1-3=SKIP | 4-5=BELOW_THRESHOLD | 6=PUBLISH | 7-8=FEATURED | 9-10=HERO
CATEGORIES: NEW_CONSTRUCTION=built within 2yr | WATERFRONT=any water | ACREAGE=land is story | HISTORIC=pre-1950 character | RENOVATED=updated systems | CHARACTER=unique details | HIDDEN_GEM=underrated value | TOO_GOOD_TO_BE_TRUE=price seems wrong | WHAT_IF=lifestyle/land fantasy"""


CONTENT_PROMPT_TEMPLATE = """You are a writer for HousesUnder150K.com. You find houses under $150,000 that most people miss and you write about them the way you'd describe one to a good friend. Direct, specific, genuinely interested. Not performing enthusiasm and not selling anything.

You are talking to one person, not an audience.

VOICE:
- Use "you" naturally, the way you would in conversation. Not on every sentence, just where it fits.
- Mix short sentences with longer ones. One idea per paragraph. Some paragraphs can be one sentence.
- Write the way you would say it out loud. "The dock goes out 130 feet" not "a 130-foot dock." "A well on the property" not "a 2-inch well."
- Start sentences with And or But when it fits.
- No hyphens used as compound modifiers.
- No em dashes. When you want to add an aside or clarify something mid-sentence, start a new sentence instead. Never use em dashes as connectors or parentheticals.
- No exclamation points. No emojis. No hashtags.
- No clichés. If a word or phrase could appear in any listing for any house anywhere, cut it and say the specific thing you actually mean. Banned words and phrases: nestled, rare find, stunning, breathtaking, turnkey, charming, don't miss, one of a kind, perfect for, ideal for, move-in ready, open concept, motivated seller, won't last long, cozy, boasts, features, sits on, offers, located in, bones, good bones, has potential, priced to sell, versatile, endless possibilities, charm, character-filled, opportunity.
- No promotional adjectives or adverbs. Let the facts do the work.
- Don't repeat the same descriptive word twice in the same piece.
- Don't tell the reader what to feel. Show them what is there.
- Don't pitch. Don't persuade. You are describing something to a friend who asked, not convincing them to buy it.
- Do not editorialize about what the reader should know or consider. State facts and move on.
- If the listing has conditions, limitations, or drawbacks, you can mention them briefly in passing but do not give them their own paragraph or let them become the focus. The house is the story.

STRUCTURE (no headers, no labels, just prose that moves through these beats naturally):

Open with the thing that stops you. The setting, the privacy, the view, the price relative to what you are getting. Whatever is most striking about this specific property. One or two sentences.

Then walk through what is actually there. Lead with what makes this place distinct: the land, the architecture, the location, the original details, anything that sets it apart from every other house at this price. Then move to condition and updates. New roof, updated electrical, fresh HVAC, recent windows, whatever work has been done that means the buyer is not walking into problems. Be specific about what was done and when the listing data provides that. This is where you make the peace of mind case without calling it that.

Close on the price as a plain statement of what you get for it. No summary, no sentiment, no wrap-up. Just land on it and stop.

RULES:
- Every fact must come from the listing data provided. Never invent.
- Name specific things: the town, the lake, the trail, the feature, the year work was done.
- If a word or phrase is vague, replace it with the specific thing you mean. Never let general language stand in for a concrete fact.
- If the agent description is thin, work with what you have. Do not pad.
- Do not write a who this is for paragraph.
- Do not end with a call to action.
- Target 300 to 400 words for the narrative.

You have been given the following listing data:

ADDRESS: {address}
CITY: {city}
STATE: {state_full}
PRICE: ${price_display}
BEDS: {bedrooms} | BATHS: {bathrooms} | SQFT: {sqft} | YEAR BUILT: {year_built}

EDITORIAL CATEGORY: {category}
KEY HOOKS: {key_hooks}

AGENT DESCRIPTION (research only — extract facts, rewrite completely in your own words, never quote or mirror the phrasing):
{description}

Produce exactly these four outputs, clearly labeled:

---

HEADLINE
A search-friendly title under 15 words. Lead with the year built (if pre-1980) or the most distinctive feature, then the city, then the key selling point, then the price with an em dash before it.
Format: "[Year] [City] [Property Type] with [Key Feature] — $[Price]"
Examples: "1931 Detroit Home with Double Lot and French Doors — $150,000" or "Three-Acre Iowa Property with Creek and Barn — $94,000" or "New Construction in Milwaukee with Four Bedrooms — $105,000" or "1908 Ohio Brick Victorian with Original Woodwork — $87,000"
Rules: No periods between phrases. Use " — " (space-dash-space) before the price. Never start with the street address. If no year is available or the home is post-1980, lead with the most distinctive feature or location.

NARRATIVE
300 to 400 words. Follow the structure above.

SOCIAL_CAPTION
Under 60 words. First sentence is the thing that stops the scroll. Include the price and location. Write like a person, not a brand.

SHORT_SUMMARY
One or two sentences, under 30 words. The single most compelling thing about this listing. Makes someone want to read more.

---

Return all four outputs with those exact labels. Nothing else."""


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
    # address keys contain pipe characters — use POST with body to avoid URL encoding issues
    params = {
        "select": "mls_number",
        "last_seen_at": f"gte.{cutoff}",
    }
    headers = _sb_headers()
    headers["Prefer"] = "return=representation"
    # Use individual IN filter — Supabase REST handles comma-separated values
    # Pipe chars in keys need special handling: query one at a time if batch fails
    try:
        # Build filter manually to handle pipe chars safely
        quoted = ",".join(f'"{k}"' for k in address_keys)
        params["mls_number"] = f"in.({quoted})"
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return {row["mls_number"] for row in r.json()}
    except Exception as e:
        log.error(f"Supabase batch_seen error: {e}")
        return set()


def db_upsert_seen(address_key: str, slug: str, score: int, tier: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/seen_listings"
    headers = _sb_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    payload = {
        "mls_number": address_key,
        "slug": slug,
        "score": score,
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
    score: int, tier: str, category: str, headline: str,
    hero_image_url: str, today_ct: date, price: int = 0,
    is_deal_of_day: bool = False,
    gallery_image_ids: list[str] | None = None,
) -> None:
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    payload = {
        "slug": slug, "mls_number": mls_number, "webflow_item_id": webflow_item_id,
        "score": score, "tier": tier, "category": category, "headline": headline,
        "hero_image_url": hero_image_url,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_date_ct": today_ct.isoformat(),
        "price": price,
        "is_deal_of_day": is_deal_of_day,
        "gallery_image_ids": gallery_image_ids or [],
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
# RealtyAPI — fetch listings + details
# ---------------------------------------------------------------------------

def _ra_headers() -> dict:
    return {"x-realtyapi-key": REALTYAPI_KEY}


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
    dom = 0

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
        "daysOnMarket": dom,
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

def build_scoring_input(listing: dict) -> str:
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    price      = parse_int(listing.get("listPrice", 0))
    address    = addr.get("formattedStreetLine", "")
    city       = addr.get("city", "")
    state      = addr.get("state", "")
    beds       = parse_int(details.get("numBedrooms"))
    baths      = parse_int(details.get("numBathrooms"))
    sqft       = parse_int(details.get("sqft"))
    year       = parse_int(details.get("yearBuilt"))
    dom        = parse_int(listing.get("daysOnMarket"))
    lot_acres  = details.get("lotAcres")
    if lot_acres and beds <= 2 and sqft < 900:
        lot_acres = None
    acreage    = str(lot_acres) if lot_acres else "null"
    waterfront = "Y" if details.get("waterfront") else "N"
    pool       = "Y" if details.get("pool") else "N"
    description = details.get("description", "") or "(no description)"

    return f"""PRICE: {price}
ADDRESS: {address}
CITY: {city}
STATE: {state}
BEDROOMS: {beds}
BATHROOMS: {baths}
SQFT: {sqft}
YEAR_BUILT: {year}
DAYS_ON_MARKET: {dom}
ACREAGE: {acreage}
POOL: {pool}
WATERFRONT: {waterfront}
DESCRIPTION: {description}"""


def parse_scoring_output(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
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

    return True


def score_listing(listing: dict) -> tuple[dict | None, float]:
    raw, cost = call_claude(SCORING_PROMPT, build_scoring_input(listing), "scoring")
    if not raw:
        return None, cost
    parsed = parse_scoring_output(raw)
    score_val = parse_int(parsed.get("SCORE", "0"))
    parsed["SCORE"] = score_val
    log.info(
        f"Score: {score_val} | Tier: {parsed.get('TIER')} | "
        f"Category: {parsed.get('CATEGORY')} | {parsed.get('REASON', '')[:80]}"
    )
    return parsed, cost


# ---------------------------------------------------------------------------
# Call 2 — Content generation
# ---------------------------------------------------------------------------

def generate_content(listing: dict, score_data: dict) -> tuple[dict | None, float]:
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    prompt = CONTENT_PROMPT_TEMPLATE.format(
        address=addr.get("formattedStreetLine", ""),
        city=addr.get("city", ""),
        state_full=addr.get("stateFull", addr.get("state", "")),
        price_display=make_price_display(parse_int(listing.get("listPrice", 0))),
        bedrooms=parse_int(details.get("numBedrooms")),
        bathrooms=parse_int(details.get("numBathrooms")),
        sqft=parse_int(details.get("sqft")),
        year_built=parse_int(details.get("yearBuilt")),
        category=score_data.get("CATEGORY", ""),
        key_hooks=score_data.get("KEY_HOOKS", ""),
        description=details.get("description", "") or "(no description)",
    )
    raw, cost = call_claude("You are a real estate content writer.", prompt, "content_gen", max_tokens=CLAUDE_MAX_TOKENS_CONTENT)
    if not raw:
        return None, cost
    return parse_content_output(raw), cost


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


def upload_gallery_images(images: list[str], slug: str) -> tuple[list[dict], list[str]]:
    """Upload up to GALLERY_PHOTO_COUNT photos (indices 1 onward, skipping hero at index 0)."""
    gallery_field_data = []
    gallery_image_ids = []

    candidates = images[1:GALLERY_PHOTO_COUNT + 1]

    for i, photo_url in enumerate(candidates):
        delivery_url, image_id = upload_image(photo_url, f"{slug}-gallery-{i + 1}")
        if delivery_url and image_id:
            gallery_field_data.append({"url": delivery_url, "alt": f"{slug} photo {i + 2}"})
            gallery_image_ids.append(image_id)
            log.info(f"Gallery photo {i + 1}/{len(candidates)} uploaded: {image_id}")
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
        "hero-image":       {"url": hero_image_url, "alt": name},
        "narrative-body":   format_richtext(content.get("NARRATIVE", "")),
        "short-summary":    content.get("SHORT_SUMMARY", ""),
        "listing-url":      f"https://housesunder150k.com/listings/{slug}",
        "state-page-url":   f"https://housesunder150k.com/states/{STATE_TO_SLUG.get(state_abbr, '')}" if state_abbr in STATE_TO_SLUG else None,
        "affiliate-url":    listing.get("listingHref") or make_realtor_url(address, city, state_abbr, zip_code),
        "social-caption":   content.get("SOCIAL_CAPTION", ""),
        "tags":             generate_tags(score_data, listing),
        "status":           WF_STATUS_ACTIVE,
        "deal-of-the-day":  is_hero,
    }

    if gallery_field_data:
        field_data["gallery-images"] = gallery_field_data

    headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    log.info(f"Writing to Webflow: {name}")
    try:
        r = requests.post(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items",
            headers=headers,
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

def process_listing(listing: dict, today_ct: date, dod_available: bool) -> tuple[str, float, bool]:
    addr       = listing.get("address", {})
    price      = parse_int(listing.get("listPrice", 0))
    city       = addr.get("city", "unknown")
    address_key = listing.get("mlsNumber", "unknown")  # address-based stable key
    slug       = make_slug(addr.get("formattedStreetLine", ""), city, addr.get("state", ""))
    total_cost = 0.0

    log.info(f"--- Processing: {city} ${make_price_display(price)} ({address_key}) ---")

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

    score_data, score_cost = score_listing(listing)
    total_cost += score_cost
    if not score_data:
        return "error", total_cost, False

    score = score_data.get("SCORE", 0)
    tier  = score_data.get("TIER", "SKIP")
    db_upsert_seen(address_key, slug, score, tier)

    if score <= 5:
        log.info(f"Score {score} <= 5 — discarding {slug}")
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

    gallery_field_data, gallery_image_ids = upload_gallery_images(images, slug) if len(images) > 1 else ([], [])

    claude_wants_hero = score_data.get("DEAL_OF_DAY_CANDIDATE", "NO").upper() == "YES"
    is_hero = claude_wants_hero and dod_available
    if claude_wants_hero and not dod_available:
        log.info(f"{slug} qualifies for deal-of-the-day but slot already taken today")

    if is_hero:
        prior = db_get_active_deal_of_day()
        if prior and prior.get("webflow_item_id"):
            unset_deal_of_the_day(prior)

    item_id = write_webflow(listing, score_data, content, hero_image_url, is_hero, gallery_field_data)
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
    )

    log.info(f"Published: {slug} (score={score}, tier={tier}, deal_of_day={is_hero}, gallery_photos={len(gallery_image_ids)})")
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

    stats = {"published": 0, "skipped_score": 0, "skipped_dedup": 0, "skipped_seen": 0, "error": 0}
    total_cost = 0.0
    published_this_run = 0
    dod_available = not db_deal_of_day_chosen_today(today_ct)
    log.info(f"Deal-of-the-day available today: {dod_available}")

    for listing in listings:
        if count_today + published_this_run >= DAILY_PUBLISH_LIMIT:
            log.info("Daily limit reached mid-batch — stopping")
            break

        try:
            result, cost, dod_used = process_listing(listing, today_ct, dod_available)
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
        f"errors={stats['error']} est_cost=${total_cost:.5f} ==="
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
        })

    if published_this_run > 0:
        publish_site()


if __name__ == "__main__":
    run_pipeline()
