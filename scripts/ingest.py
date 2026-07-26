"""
HousesUnder150K.com — Ingestion Pipeline
Runs on Railway 3x/day: 8am, 1pm, 6pm CT
Fetches listings from Repliers, scores, generates content, publishes to Webflow.
"""

import os
import sys
import json
import re
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

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

REPLIERS_API_KEY       = os.environ["REPLIERS_API_KEY"]
ANTHROPIC_API_KEY      = os.environ["ANTHROPIC_API_KEY"]
CLOUDFLARE_API_TOKEN   = os.environ["CLOUDFLARE_API_TOKEN"]
CLOUDFLARE_ACCOUNT_ID  = os.environ["CLOUDFLARE_ACCOUNT_ID"]
WEBFLOW_API_TOKEN      = os.environ["WEBFLOW_API_TOKEN"]
WEBFLOW_COLLECTION_ID  = os.environ["WEBFLOW_COLLECTION_ID"]
SOVRN_AFFILIATE_URL    = os.environ["SOVRN_AFFILIATE_URL"]

CLAUDE_MODEL           = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS      = 1000
REPLIERS_BASE          = "https://api.repliers.io"
ANTHROPIC_BASE         = "https://api.anthropic.com/v1/messages"
CF_IMAGES_BASE         = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1"
CF_DELIVERY_BASE       = "https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w"
WEBFLOW_BASE           = "https://api.webflow.com/v2"

# Posts directory — one JSON file per published slug (dedup layer)
POSTS_DIR = Path(__file__).parent.parent / "posts"
POSTS_DIR.mkdir(exist_ok=True)

# Webflow field IDs
WF_FIELDS = {
    "name":            "2d0b39c8706c5aeb8a5d10eb7c7b0ba5",
    "slug":            "3eff577466e8ac4d1f5673c6ba5067f0",
    "price":           "e3e0fbae7e82729a2d40cfd88b8553ad",
    "price-display":   "f1701f816e4213ef8979d44f2a9f4ec4",
    "location-display":"dcbe16cd4151eaab2df0d79d0343ad5e",
    "address":         "2370642ad45dce9c5cbbf8d6122515dc",
    "city":            "ab84ae63bb81f7bfe33ccb50cfe9bc25",
    "state":           "59074a866f1a7d4bffb208b1a63cd827",
    "year-built":      "e16726678f8f43f844c78f4fd226e47c",
    "bedrooms":        "72df5c8c23726e9849fa1520abe59b11",
    "bathrooms":       "ad78567827bc5cc5dbcdbf93379f2c06",
    "square-feet":     "326895e4a7b08fc72b760740045e9e8d",
    "hero-image":      "c2021ed9588e45e46c85ff883a558c02",
    "narrative-body":  "fbfb92acd8aeee91d64209f2e905fc5a",
    "short-summary":   "aec9319d65a89b54b50001e13af0b8c7",
    "listing-url":     "4d428fda04c2feb9db89ef1423343895",
    "affiliate-url":   "2b37c2a126d49592bd34aa91ed798c26",
    "social-caption":  "68cdd4fdfa9a3a1ce86836aaa3617950",
    "status":          "6b58bbdff6c0c0e31e17c04e4188f8be",
    "deal-of-the-day": "3e20ffd4c8781f4b215bf2aa02b01542",
}

WF_STATUS_ACTIVE = "3b41185e9af84f92d8da092965308a2d"

# Claude pricing (Sonnet 4.6) — for cost estimates in logs
COST_PER_1K_INPUT  = 0.003   # $3/M input tokens
COST_PER_1K_OUTPUT = 0.015   # $15/M output tokens

# US state name → abbreviation lookup (Repliers returns full name)
STATE_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
    # Canadian provinces (test data may include these)
    "Ontario": "ON", "Quebec": "QC", "British Columbia": "BC", "Alberta": "AB",
    "Manitoba": "MB", "Saskatchewan": "SK", "Nova Scotia": "NS",
    "New Brunswick": "NB", "Newfoundland and Labrador": "NL",
    "Prince Edward Island": "PE", "Northwest Territories": "NT",
    "Nunavut": "NU", "Yukon": "YT",
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SCORING_PROMPT = """You are an editorial scoring engine for HousesUnder150K.com, a curated real estate deals site. Your job is to evaluate residential listings priced under $150,000 and score them on a scale of 1-10 based on their editorial merit and reader interest.

You will be given listing data including specs, location, and the agent description. Score the listing based on the criteria below. Be honest and strict — most listings should score 4 or below. Only genuinely interesting listings score 6+.

---

## AUTOMATIC 6+ FLOOR

If ANY of the following are present, the listing automatically scores at least a 6 regardless of other factors:

- Waterfront (lake, river, pond, ocean, creek)
- Lake view or mountain view
- Acreage (0.5+ acres qualifies, 1+ acre is stronger)
- Pool (in-ground)
- Wooded lot / woods / heavily treed
- New construction (built current year or last 2 years)
- Historic home (pre-1950 with character details mentioned)

If none of these are present, the listing must accumulate additive qualifiers to reach a 6.

---

## ADDITIVE QUALIFIERS
## Each qualifier that is clearly present adds to the score. More qualifiers = higher score.

**Condition & Updates (each one counts):**
- Recent renovation — kitchen, bathrooms, or whole home (within last 10 years, year mentioned preferred)
- Major system update — new roof, new HVAC, new windows, new plumbing/electrical (year mentioned preferred)
- Move-in ready, updated, or turnkey language with specifics to back it up

**Size & Space:**
- Square footage tier:
  - Under 800 sqft: negative signal (-1)
  - 800-1,100 sqft: neutral
  - 1,100-1,400 sqft: mild positive (+0.5)
  - 1,400-1,800 sqft: positive (+1)
  - 1,800+ sqft: strong positive (+1.5)
- Bedroom count:
  - 1-2 bed: neutral to slight negative
  - 3 bed: baseline, no adjustment
  - 4 bed: positive (+0.5)
  - 5+ bed: strong positive (+1)
- Large yard beyond automatic floor (fenced, oversized city lot, corner lot with space)
- Garage (attached or detached)
- Outbuildings, barn, workshop, shed

**Character & Uniqueness:**
- Historical significance (listed on registry, named property, notable age with details)
- Unique architectural features: stained glass windows, original millwork, exposed beams, tin ceilings, hardwood floors throughout, wraparound porch, clawfoot tub, built-ins, wainscoting
- Unusual or rare property type for the price point
- Fireplace (wood-burning preferred)
- Finished basement

**Location & Community:**
- Great schools or named school district mentioned
- Walkable location with named amenities (shops, restaurants, trails, parks)
- Named nearby features (trail system, state park, lake, river, downtown)
- Small charming town with community feel
- Low cost of living area

**Deal Signals:**
- Price reduction / price cut (lastPriceChangeType = decrease or lastStatus = Pc)
- High days on market with low price (motivated seller signal)
- Exceptionally low price per square foot for any market
- Bank owned / estate sale / motivated seller explicitly stated

**Description Quality:**
- Rich agent description with specific details, named features, local context: +0.5 to +1
- Sparse description (3 sentences or fewer, no specifics): -1

---

## NEGATIVE MODIFIERS

These push the score down:

- Manufactured home / mobile home / modular: -3 (rarely scores above 4)
- Needs significant work with no renovation history mentioned: -1
- No photos available: -1
- Very small square footage (under 700 sqft): -1
- Condo / HOA with high monthly fees mentioned: -0.5
- Location with no distinguishing features mentioned: -0.5

---

## SCORING BANDS

**1-3: Skip** — Generic listing, no distinguishing features, manufactured home, bad data, or bare specs with nothing interesting. Do not publish.

**4-5: Below threshold** — Decent listing but nothing that makes it editorially interesting. Solid specs but no story. Do not publish.

**6: Minimum publish threshold** — Has at least one automatic qualifier OR has accumulated enough additive qualifiers to be genuinely interesting to a reader. Publish.

**7: Strong listing** — One or more automatic qualifiers plus additional positive signals. Clear reader value. Publish, social post.

**8: Featured listing** — Multiple strong qualifiers, great description, compelling deal. Publish, social post, email to paid subscribers.

**9-10: Deal of the Day candidate** — Exceptional on multiple dimensions. Waterfront + renovation + acreage, or historic home with full character details, or new construction at an unusually low price. Publish, social reel, email ALL subscribers.

---

## INPUT FORMAT

You will receive:

PRICE: [price as integer]
ADDRESS: [street address]
CITY: [city]
STATE: [state abbreviation]
BEDROOMS: [integer]
BATHROOMS: [integer]
SQFT: [integer]
YEAR_BUILT: [integer]
DAYS_ON_MARKET: [integer]
PRICE_CHANGE: [decrease / none]
LAST_STATUS: [New / Pc / etc]
PROPERTY_TYPE: [type]
STYLE: [architectural style]
EXTERIOR: [exterior construction]
POOL: [Y/N]
WATERFRONT: [Y/N]
ACREAGE: [decimal or null]
AMENITIES: [list or null]
DESCRIPTION: [full agent description]

---

## OUTPUT FORMAT

Respond in exactly this format, no other text:

SCORE: [1-10]
TIER: [SKIP / BELOW_THRESHOLD / PUBLISH / FEATURED / HERO]
CATEGORY: [one of: NEW_CONSTRUCTION / WATERFRONT / ACREAGE / HISTORIC / RENOVATED / CHARACTER / HIDDEN_GEM / TOO_GOOD_TO_BE_TRUE / WHAT_IF]
KEY_HOOKS: [2-4 specific compelling facts about this listing, comma separated]
REASON: [1-2 sentences explaining the score]
DEAL_OF_DAY_CANDIDATE: [YES / NO]

---

## TIER MAPPING

- SCORE 1-3 → TIER: SKIP
- SCORE 4-5 → TIER: BELOW_THRESHOLD
- SCORE 6 → TIER: PUBLISH
- SCORE 7-8 → TIER: FEATURED
- SCORE 9-10 → TIER: HERO

---

## CATEGORIES

- NEW_CONSTRUCTION — Built within last 2 years
- WATERFRONT — Any water frontage or water view
- ACREAGE — Primary appeal is land / lot size
- HISTORIC — Pre-1950 with notable character details
- RENOVATED — Recently updated, key systems replaced
- CHARACTER — Unique architectural features, charm, details
- HIDDEN_GEM — Undervalued location, surprisingly good value
- TOO_GOOD_TO_BE_TRUE — Price seems impossibly low for what's offered (use sparingly)
- WHAT_IF — Acreage/land with development or lifestyle potential

---

## NOTES

- Be strict. A score of 6 should feel earned, not given.
- The KEY_HOOKS are passed directly to the content generation prompt — make them specific and usable.
- Do not score up a listing just because the price is low. Low price alone is not editorial.
- Manufactured homes almost never score above 4 regardless of other factors.
- A rich, detailed agent description elevates a borderline listing. A sparse description kills one.
- When in doubt, score down. Volume can be adjusted. Quality cannot be recovered."""


CONTENT_PROMPT_TEMPLATE = """You are a writer for HousesUnder150K.com — a site that finds incredible real estate deals under $150,000 that most people never see. Your voice is enthusiastic but credible, like a knowledgeable friend who spotted an amazing deal and can't wait to tell you about it. Never hype, never fluff — just honest, specific, compelling storytelling about why this property is worth attention.

You write in the voice of Michelle Bowers from The Old House Life. Her format:
1. A short, genuine, enthusiastic reaction (2-4 sentences) — the thing that stops the scroll
2. The key facts woven together in natural flowing sentences — not a spec list
3. The agent description rewritten in enthusiastic conversational voice — extract facts, never quote directly
4. A simple CTA

Short is better. The house is the content. You are the curator.

Voice rules:
- Zero real estate language: no "nestled," "rare find," "move-in ready," "motivated seller," "open concept"
- Specific proper nouns always — name the town, river, trail, feature
- Short sentences. Real numbers. Precision signals you actually looked.
- Second person present tense where it fits — "you wake up to the lake"
- Write like a person who found this, not a brand promoting it
- Never use hashtags

You have been given the following listing data:

ADDRESS: {address}
CITY: {city}
STATE: {state_full}
PRICE DISPLAY: ${price_display}
BEDS: {bedrooms} | BATHS: {bathrooms} | SQFT: {sqft} | YEAR BUILT: {year_built}
LISTING URL: {listing_url}
AFFILIATE LINK: {affiliate_url}

EDITORIAL CATEGORY: {category}
(NEW_CONSTRUCTION = impossible value at new / WATERFRONT = any water / ACREAGE = land is the story /
HISTORIC = pre-1950 character / RENOVATED = updated systems / CHARACTER = unique details /
HIDDEN_GEM = underrated charm / TOO_GOOD_TO_BE_TRUE = price seems wrong / WHAT_IF = lifestyle fantasy)

KEY HOOKS (the most compelling things — lead with these):
{key_hooks}

AGENT DESCRIPTION (research only — extract facts, never quote directly):
{description}

Produce exactly these four outputs, clearly labeled:

---

HEADLINE
One punchy headline under 10 words. Lead with the hook from KEY HOOKS — never the address.
Examples: "A 4BR Farmhouse on 3 Acres. $94,000." or "1891 Brick Victorian. Original Stained Glass. $87K." or "Brand New Construction in Milwaukee: $105,000."

NARRATIVE
Tell the story in 150-250 words. Structure:
- Opening hook (1-2 sentences) — the most surprising or compelling element
- Key facts woven into narrative — never a spec list — make the reader see it
- Location context briefly
- Who this is for and why it matters
End with exactly: See the full listing here → {affiliate_url}

SOCIAL_CAPTION
Under 60 words. First line must stop the scroll. Include price and location. End with a reason to click. No hashtags. Write like a person, not a brand.

SHORT_SUMMARY
1-2 sentences, under 30 words. Used as the listing card preview on the homepage. Lead with the single most compelling thing. Make someone want to read more.

---

Return all four outputs with those exact labels. Nothing else."""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_price(raw) -> int:
    """'5961.00' or 105000 → 105000"""
    try:
        return int(float(str(raw)))
    except (ValueError, TypeError):
        return 0


def parse_sqft(raw) -> int:
    """'1000-1100' → 1050, or '1200' → 1200, or 1200 → 1200"""
    if raw is None:
        return 0
    s = str(raw).strip()
    if "-" in s:
        parts = s.split("-")
        try:
            lo = int(parts[0].strip())
            hi = int(parts[1].strip())
            return (lo + hi) // 2
        except (ValueError, IndexError):
            pass
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def parse_int(raw) -> int:
    try:
        return int(float(str(raw))) if raw is not None else 0
    except (ValueError, TypeError):
        return 0


def build_address(addr: dict) -> str:
    parts = [
        str(addr.get("streetNumber", "") or "").strip(),
        str(addr.get("streetName", "") or "").strip(),
        str(addr.get("streetSuffix", "") or "").strip(),
    ]
    return " ".join(p for p in parts if p)


def state_abbrev(full_name: str) -> str:
    return STATE_ABBREV.get(full_name, full_name[:2].upper() if full_name else "")


def make_slug(city: str, price: int) -> str:
    """'Milwaukee', 105000 → 'milwaukee-105000' — matches existing pattern"""
    city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
    return f"{city_slug}-{price}"


def make_price_display(price: int) -> str:
    """105000 → '105,000'"""
    return f"{price:,}"


def format_richtext(text: str) -> str:
    """Wrap narrative paragraphs in Webflow richtext HTML"""
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paragraphs)


# ---------------------------------------------------------------------------
# Repliers API
# ---------------------------------------------------------------------------

def fetch_listings(last_run_timestamp: str | None = None) -> list[dict]:
    """
    Fetch active listings under $150K from Repliers.
    last_run_timestamp: ISO8601 string — if provided, only fetch updated since then.
    Returns list of raw listing dicts.
    """
    params = {
        "status": "A",
        "maxPrice": 150000,
        "resultsPerPage": 50,
        "sortBy": "updatedOnDesc",
    }
    if last_run_timestamp:
        params["minUpdatedOn"] = last_run_timestamp

    headers = {"REPLIERS-API-KEY": REPLIERS_API_KEY}

    log.info("Fetching listings from Repliers (maxPrice=150000, status=A)...")
    try:
        r = requests.get(
            f"{REPLIERS_BASE}/listings",
            headers=headers,
            params=params,
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Repliers fetch failed: {e}")
        return []

    data = r.json()
    listings = data.get("listings", [])
    total = data.get("count", len(listings))
    log.info(f"Fetched {len(listings)} listings (total available: {total})")
    return listings


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------

def slug_exists(slug: str) -> bool:
    return (POSTS_DIR / f"{slug}.json").exists()


def write_post_record(slug: str, data: dict) -> None:
    path = POSTS_DIR / f"{slug}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info(f"Wrote post record: posts/{slug}.json")


# ---------------------------------------------------------------------------
# Token logging
# ---------------------------------------------------------------------------

def log_tokens(call_name: str, input_tokens: int, output_tokens: int) -> None:
    cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + \
           (output_tokens / 1000 * COST_PER_1K_OUTPUT)
    log.info(
        f"[TOKENS] {call_name} | in={input_tokens} out={output_tokens} "
        f"| est_cost=${cost:.5f}"
    )


# ---------------------------------------------------------------------------
# Claude API
# ---------------------------------------------------------------------------

def call_claude(system: str, user: str, call_name: str) -> str | None:
    """
    POST to Anthropic /v1/messages. Logs token usage. Returns text content or None.
    """
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": CLAUDE_MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    try:
        r = requests.post(ANTHROPIC_BASE, headers=headers, json=body, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Claude API error ({call_name}): {e}")
        return None

    data = r.json()
    usage = data.get("usage", {})
    log_tokens(call_name, usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    content_blocks = data.get("content", [])
    text_blocks = [b["text"] for b in content_blocks if b.get("type") == "text"]
    return "\n".join(text_blocks).strip() if text_blocks else None


# ---------------------------------------------------------------------------
# Call 1 — Scoring
# ---------------------------------------------------------------------------

def build_scoring_input(listing: dict) -> str:
    addr    = listing.get("address", {})
    details = listing.get("details", {})
    lot     = listing.get("lot", {})
    nearby  = listing.get("nearby", {})

    price   = parse_price(listing.get("listPrice", 0))
    address = build_address(addr)
    city    = addr.get("city", "")
    state_full = addr.get("state", "")
    state   = state_abbrev(state_full)
    beds    = parse_int(details.get("numBedrooms"))
    baths   = parse_int(details.get("numBathrooms"))
    sqft    = parse_sqft(details.get("sqft"))
    year    = parse_int(details.get("yearBuilt"))
    dom     = parse_int(listing.get("daysOnMarket"))

    price_change = listing.get("lastPriceChangeType", "none") or "none"
    last_status  = listing.get("lastStatus", "") or ""
    prop_type    = details.get("propertyType", "") or ""
    style        = details.get("style", "") or ""
    exterior     = details.get("exteriorConstruction1", "") or ""
    pool         = "Y" if str(details.get("swimmingPool", "")).upper() == "Y" else "N"
    waterfront   = "Y" if str(details.get("waterfront", "")).upper() == "Y" else "N"

    acres_raw = lot.get("acres")
    acreage = str(round(float(acres_raw), 2)) if acres_raw else "null"

    amenities = nearby.get("amenities", [])
    amenities_str = ", ".join(amenities) if amenities else "null"

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
PRICE_CHANGE: {price_change}
LAST_STATUS: {last_status}
PROPERTY_TYPE: {prop_type}
STYLE: {style}
EXTERIOR: {exterior}
POOL: {pool}
WATERFRONT: {waterfront}
ACREAGE: {acreage}
AMENITIES: {amenities_str}
DESCRIPTION: {description}"""


def parse_scoring_output(text: str) -> dict:
    """Parse the structured scoring response into a dict."""
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def score_listing(listing: dict) -> dict | None:
    """
    Call Claude with scoring prompt. Returns parsed score dict or None on failure.
    score dict keys: SCORE, TIER, CATEGORY, KEY_HOOKS, REASON, DEAL_OF_DAY_CANDIDATE
    """
    user_input = build_scoring_input(listing)
    raw = call_claude(SCORING_PROMPT, user_input, "scoring")
    if not raw:
        return None
    parsed = parse_scoring_output(raw)
    score_val = parse_int(parsed.get("SCORE", "0"))
    parsed["SCORE"] = score_val
    log.info(
        f"Score: {score_val} | Tier: {parsed.get('TIER')} | "
        f"Category: {parsed.get('CATEGORY')} | {parsed.get('REASON', '')[:80]}"
    )
    return parsed


# ---------------------------------------------------------------------------
# Call 2 — Content generation
# ---------------------------------------------------------------------------

def generate_content(listing: dict, score_data: dict) -> dict | None:
    """
    Call Claude with content prompt. Returns dict with HEADLINE, NARRATIVE,
    SOCIAL_CAPTION, SHORT_SUMMARY, or None on failure.
    """
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    price        = parse_price(listing.get("listPrice", 0))
    address      = build_address(addr)
    city         = addr.get("city", "")
    state_full   = addr.get("state", "")
    beds         = parse_int(details.get("numBedrooms"))
    baths        = parse_int(details.get("numBathrooms"))
    sqft         = parse_sqft(details.get("sqft"))
    year_built   = parse_int(details.get("yearBuilt"))
    description  = details.get("description", "") or "(no description)"
    slug         = make_slug(city, price)
    listing_url  = f"https://housesunder150k.com/listings/{slug}"

    prompt = CONTENT_PROMPT_TEMPLATE.format(
        address=address,
        city=city,
        state_full=state_full,
        price_display=make_price_display(price),
        bedrooms=beds,
        bathrooms=baths,
        sqft=sqft,
        year_built=year_built,
        listing_url=listing_url,
        affiliate_url=SOVRN_AFFILIATE_URL,
        category=score_data.get("CATEGORY", ""),
        key_hooks=score_data.get("KEY_HOOKS", ""),
        description=description,
    )

    raw = call_claude("You are a real estate content writer.", prompt, "content_gen")
    if not raw:
        return None

    return parse_content_output(raw)


def parse_content_output(text: str) -> dict:
    """
    Parse labeled sections from content generation output.
    Handles both 'LABEL\ncontent' and 'LABEL: content' formats.
    """
    result = {"HEADLINE": "", "NARRATIVE": "", "SOCIAL_CAPTION": "", "SHORT_SUMMARY": ""}
    labels = list(result.keys())

    current_label = None
    current_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        matched_label = None
        for label in labels:
            if stripped == label or stripped == f"{label}:":
                matched_label = label
                break

        if matched_label:
            if current_label and current_lines:
                result[current_label] = "\n".join(current_lines).strip()
            current_label = matched_label
            current_lines = []
        else:
            if current_label:
                current_lines.append(line)

    if current_label and current_lines:
        result[current_label] = "\n".join(current_lines).strip()

    return result


# ---------------------------------------------------------------------------
# Cloudflare Images
# ---------------------------------------------------------------------------

def upload_image(image_url: str, slug: str) -> str | None:
    """
    Fetch image from MLS URL, upload to Cloudflare Images.
    Returns permanent delivery URL or None on failure.
    """
    if "imagedelivery.net" in image_url:
        log.info(f"Image already on Cloudflare, skipping upload: {image_url}")
        return image_url

    log.info(f"Fetching image from MLS: {image_url}")
    try:
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to fetch image {image_url}: {e}")
        return None

    content_type = img_response.headers.get("content-type", "image/jpeg")
    filename = f"{slug}.jpg"

    log.info(f"Uploading image to Cloudflare Images ({len(img_response.content)} bytes)...")
    try:
        cf_response = requests.post(
            CF_IMAGES_BASE,
            headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
            files={"file": (filename, img_response.content, content_type)},
            timeout=60,
        )
        cf_response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Cloudflare Images upload failed: {e}")
        return None

    cf_data = cf_response.json()
    if not cf_data.get("success"):
        errors = cf_data.get("errors", [])
        log.error(f"Cloudflare Images error: {errors}")
        return None

    variants = cf_data.get("result", {}).get("variants", [])
    if variants:
        url = variants[0]
        log.info(f"Cloudflare image URL: {url}")
        return url

    image_id = cf_data.get("result", {}).get("id")
    if image_id:
        url = f"{CF_DELIVERY_BASE}/{image_id}/public"
        log.info(f"Cloudflare image URL (constructed): {url}")
        return url

    log.error("Cloudflare upload succeeded but no URL returned")
    return None


# ---------------------------------------------------------------------------
# Webflow CMS
# ---------------------------------------------------------------------------

def write_webflow(listing: dict, score_data: dict, content: dict, hero_image_url: str) -> str | None:
    """
    Write listing to Webflow CMS. Returns the new item ID or None on failure.
    """
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    price      = parse_price(listing.get("listPrice", 0))
    city       = addr.get("city", "")
    state_full = addr.get("state", "")
    state_abbr = state_abbrev(state_full)
    address    = build_address(addr)
    slug       = make_slug(city, price)
    beds       = parse_int(details.get("numBedrooms"))
    baths      = parse_int(details.get("numBathrooms"))
    sqft       = parse_sqft(details.get("sqft"))
    year       = parse_int(details.get("yearBuilt"))
    listing_url = f"https://housesunder150k.com/listings/{slug}"

    headline = content.get("HEADLINE", "")
    name = headline if headline else f"{city}, {state_full} — ${make_price_display(price)}"

    is_hero = score_data.get("DEAL_OF_DAY_CANDIDATE", "NO").upper() == "YES"

    field_data = {
        "name":             name,
        "slug":             slug,
        "price":            price,
        "price-display":    make_price_display(price),
        "location-display": f"{city}, {state_full}",
        "address":          address,
        "city":             city,
        "state":            state_abbr,
        "year-built":       year,
        "bedrooms":         beds,
        "bathrooms":        baths,
        "square-feet":      sqft,
        "hero-image":       {"url": hero_image_url},
        "narrative-body":   format_richtext(content.get("NARRATIVE", "")),
        "short-summary":    content.get("SHORT_SUMMARY", ""),
        "listing-url":      listing_url,
        "affiliate-url":    SOVRN_AFFILIATE_URL,
        "social-caption":   content.get("SOCIAL_CAPTION", ""),
        "status":           WF_STATUS_ACTIVE,
        "deal-of-the-day":  is_hero,
    }

    headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    log.info(f"Writing to Webflow CMS: {name}")
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

    item = r.json()
    item_id = item.get("id")
    log.info(f"Webflow item created: {item_id}")
    return item_id


def publish_webflow(item_id: str) -> bool:
    """Publish a Webflow CMS item by ID. Returns True on success."""
    headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    log.info(f"Publishing Webflow item: {item_id}")
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

    log.info(f"Published item {item_id}")
    return True


# ---------------------------------------------------------------------------
# Per-listing pipeline
# ---------------------------------------------------------------------------

def process_listing(listing: dict) -> str:
    """
    Run the full pipeline for a single listing.
    Returns: 'published' | 'skipped_score' | 'skipped_dedup' | 'error'
    """
    addr    = listing.get("address", {})
    price   = parse_price(listing.get("listPrice", 0))
    city    = addr.get("city", "unknown")
    mls_num = listing.get("mlsNumber", "unknown")
    slug    = make_slug(city, price)

    log.info(f"--- Processing: {city} ${make_price_display(price)} (MLS {mls_num}) ---")

    # Dedup check
    if slug_exists(slug):
        log.info(f"Skipping {slug} — already published")
        return "skipped_dedup"

    # Call 1 — Score
    score_data = score_listing(listing)
    if not score_data:
        log.error(f"Scoring failed for {slug}")
        return "error"

    score = score_data.get("SCORE", 0)

    # Discard 1-5
    if score <= 5:
        log.info(f"Score {score} <= 5 — discarding {slug}")
        return "skipped_score"

    # Call 2 — Content generation
    content = generate_content(listing, score_data)
    if not content:
        log.error(f"Content generation failed for {slug}")
        return "error"

    # Image — fetch images[0], upload to Cloudflare
    images = listing.get("images", [])
    hero_image_url = None
    if images:
        hero_image_url = upload_image(images[0], slug)
    if not hero_image_url:
        log.warning(f"No hero image for {slug} — proceeding without image")
        hero_image_url = ""

    # Write to Webflow
    item_id = write_webflow(listing, score_data, content, hero_image_url)
    if not item_id:
        log.error(f"Webflow write failed for {slug}")
        return "error"

    # Publish
    published = publish_webflow(item_id)
    if not published:
        log.error(f"Webflow publish failed for item {item_id}")
        return "error"

    # Write dedup record
    write_post_record(slug, {
        "slug": slug,
        "mls_number": mls_num,
        "webflow_item_id": item_id,
        "score": score,
        "tier": score_data.get("TIER"),
        "category": score_data.get("CATEGORY"),
        "deal_of_day_candidate": score_data.get("DEAL_OF_DAY_CANDIDATE"),
        "headline": content.get("HEADLINE"),
        "hero_image_url": hero_image_url,
        "published_at": datetime.now(timezone.utc).isoformat(),
    })

    log.info(f"Published: {slug} (score={score}, tier={score_data.get('TIER')})")
    return "published"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline():
    log.info("=== HousesUnder150K Ingestion Pipeline Start ===")
    start = time.time()

    listings = fetch_listings()
    if not listings:
        log.info("No listings returned — exiting")
        return

    stats = {"published": 0, "skipped_score": 0, "skipped_dedup": 0, "error": 0}

    for listing in listings:
        try:
            result = process_listing(listing)
            stats[result] = stats.get(result, 0) + 1
        except Exception as e:
            log.error(f"Unhandled error processing listing: {e}", exc_info=True)
            stats["error"] += 1

        # Brief pause between listings to avoid hammering APIs
        time.sleep(1)

    elapsed = time.time() - start
    log.info(
        f"=== Pipeline complete in {elapsed:.1f}s | "
        f"published={stats['published']} skipped_score={stats['skipped_score']} "
        f"skipped_dedup={stats['skipped_dedup']} errors={stats['error']} ==="
    )


if __name__ == "__main__":
    run_pipeline()
