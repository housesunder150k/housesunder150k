"""
HousesUnder150K.com — Ingestion Pipeline
Runs on Railway 3x/day: 8am, 1pm, 6pm CT
Fetches listings from Repliers, scores, generates content, publishes to Webflow.
Dedup, daily limit, and seen-listing suppression via Supabase.
"""

import os
import re
import time
import logging
from datetime import datetime, timezone, date

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

REPLIERS_API_KEY       = os.environ["REPLIERS_API_KEY"]
ANTHROPIC_API_KEY      = os.environ["ANTHROPIC_API_KEY"]
CLOUDFLARE_API_TOKEN   = os.environ["CLOUDFLARE_API_TOKEN"]
CLOUDFLARE_ACCOUNT_ID  = os.environ["CLOUDFLARE_ACCOUNT_ID"]
WEBFLOW_API_TOKEN      = os.environ["WEBFLOW_API_TOKEN"]
WEBFLOW_COLLECTION_ID  = os.environ["WEBFLOW_COLLECTION_ID"]
SOVRN_AFFILIATE_URL    = os.environ["SOVRN_AFFILIATE_URL"]
SUPABASE_URL           = os.environ["SUPABASE_URL"]
SUPABASE_KEY           = os.environ["SUPABASE_KEY"]
DAILY_PUBLISH_LIMIT    = int(os.environ.get("DAILY_PUBLISH_LIMIT", "10"))

CLAUDE_MODEL           = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS      = 1000
REPLIERS_BASE          = "https://api.repliers.io"
REPLIERS_CDN           = "https://cdn.repliers.io"
ANTHROPIC_BASE         = "https://api.anthropic.com/v1/messages"
CF_IMAGES_BASE         = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1"
CF_DELIVERY_BASE       = "https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w"
WEBFLOW_BASE           = "https://api.webflow.com/v2"

SEEN_SUPPRESSION_DAYS  = 7   # Days to suppress re-scoring of discarded listings
CT_TZ                  = pytz.timezone("America/Chicago")

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
    "Ontario": "ON", "Quebec": "QC", "British Columbia": "BC", "Alberta": "AB",
    "Manitoba": "MB", "Saskatchewan": "SK", "Nova Scotia": "NS",
    "New Brunswick": "NB", "Newfoundland and Labrador": "NL",
    "Prince Edward Island": "PE", "Northwest Territories": "NT",
    "Nunavut": "NU", "Yukon": "YT",
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SCORING_PROMPT = """Score this residential listing for HousesUnder150K.com on editorial merit (1-10). Be strict — most listings score 4 or below. Only genuinely interesting listings score 6+. Low price alone is never enough.

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
- Character features: stained glass, exposed beams, hardwood, wraparound porch, clawfoot tub, built-ins, tin ceilings, wainscoting, fireplace
- Finished basement
- Named nearby amenities, trails, parks, charming town
- Price reduction (PRICE_CHANGE=decrease or LAST_STATUS=Pc)
- High days on market + low price
- Rich agent description with specifics: +0.5 to +1

NEGATIVE MODIFIERS:
- Manufactured/mobile/modular: -3
- Needs major work, no renovation history: -1
- No photos: -1
- Under 700 sqft: -1
- HOA with high fees: -0.5
- Sparse description (3 sentences or fewer): -1

SCORING BANDS:
1-3: Skip — no story, bad data, manufactured home
4-5: Below threshold — decent but nothing editorial. Do not publish.
6: Publish — one floor qualifier OR enough positives accumulated
7-8: Featured — strong qualifiers + good description
9-10: Hero / Deal of Day — exceptional on multiple dimensions

OUTPUT (exactly this format, no other text):
SCORE: [1-10]
TIER: [SKIP / BELOW_THRESHOLD / PUBLISH / FEATURED / HERO]
CATEGORY: [NEW_CONSTRUCTION / WATERFRONT / ACREAGE / HISTORIC / RENOVATED / CHARACTER / HIDDEN_GEM / TOO_GOOD_TO_BE_TRUE / WHAT_IF]
KEY_HOOKS: [2-4 specific compelling facts, comma separated]
REASON: [1-2 sentences]
DEAL_OF_DAY_CANDIDATE: [YES / NO]

TIER MAP: 1-3=SKIP | 4-5=BELOW_THRESHOLD | 6=PUBLISH | 7-8=FEATURED | 9-10=HERO
CATEGORIES: NEW_CONSTRUCTION=built within 2yr | WATERFRONT=any water | ACREAGE=land is story | HISTORIC=pre-1950 character | RENOVATED=updated systems | CHARACTER=unique details | HIDDEN_GEM=underrated value | TOO_GOOD_TO_BE_TRUE=price seems wrong | WHAT_IF=lifestyle/land fantasy"""


CONTENT_PROMPT_TEMPLATE = """You are a writer for HousesUnder150K.com — a site that finds incredible real estate deals under $150,000 that most people never see. Your voice is enthusiastic but credible, like a knowledgeable friend who spotted an amazing deal and can't wait to tell you about it. Never hype, never fluff — just honest, specific, compelling storytelling about why this property is worth attention.

You write in the voice of Michelle Bowers from The Old House Life. Her format:
1. A short, genuine, enthusiastic reaction (2-4 sentences) — the thing that stops the scroll
2. The key facts woven together in natural flowing sentences — not a spec list
3. The agent description rewritten in enthusiastic conversational voice — extract facts, never quote directly
4. End cleanly — no CTA line, the site handles that

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
Do NOT include any CTA line or link at the end — end on the story itself.

SOCIAL_CAPTION
Under 60 words. First line must stop the scroll. Include price and location. End with a reason to click. No hashtags. Write like a person, not a brand.

SHORT_SUMMARY
1-2 sentences, under 30 words. Used as the listing card preview on the homepage. Lead with the single most compelling thing. Make someone want to read more.

---

Return all four outputs with those exact labels. Nothing else."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_today_ct() -> date:
    """Return today's date in CT timezone."""
    return datetime.now(CT_TZ).date()


def parse_price(raw) -> int:
    try:
        return int(float(str(raw)))
    except (ValueError, TypeError):
        return 0


def parse_sqft(raw) -> int:
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
    city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
    return f"{city_slug}-{price}"


def make_price_display(price: int) -> str:
    return f"{price:,}"


def format_richtext(text: str) -> str:
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paragraphs)


def make_realtor_url(addr: dict) -> str:
    street_num  = str(addr.get("streetNumber", "") or "").strip()
    street_name = str(addr.get("streetName", "") or "").strip()
    street_suf  = str(addr.get("streetSuffix", "") or "").strip()
    city        = str(addr.get("city", "") or "").strip()
    state       = str(addr.get("state", "") or "").strip()
    zip_code    = str(addr.get("zip", "") or "").strip()
    state_abbr  = state_abbrev(state)

    def slugify(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")

    if street_num and street_name:
        street = f"{street_num}-{street_name}"
        if street_suf:
            street += f"-{street_suf}"
        parts = [slugify(street), slugify(city), state_abbr]
        if zip_code:
            parts.append(zip_code)
        path = "_".join(parts)
    else:
        path = f"{slugify(city)}_{state_abbr}"

    return f"https://www.realtor.com/realestateandhomes-search/{path}"


# ---------------------------------------------------------------------------
# Supabase — all DB operations
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def db_count_published_today(today_ct: date) -> int:
    """Count listings published today in CT timezone."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug",
        "published_date_ct": f"eq.{today_ct.isoformat()}",
    }
    headers = _sb_headers()
    headers["Prefer"] = "count=exact"
    headers["Range-Unit"] = "items"
    headers["Range"] = "0-0"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        content_range = r.headers.get("Content-Range", "0/0")
        total = content_range.split("/")[-1]
        return int(total) if total != "*" else 0
    except Exception as e:
        log.error(f"Supabase count_published_today error: {e}")
        return 0


def db_slug_published(slug: str) -> bool:
    """Check if slug already exists in published_listings."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"select": "slug", "slug": f"eq.{slug}", "limit": 1}
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return len(r.json()) > 0
    except Exception as e:
        log.error(f"Supabase slug_published error: {e}")
        return False


def db_mls_seen_recently(mls_number: str) -> dict | None:
    """
    Return seen_listings row if this MLS number was seen within suppression window.
    Returns None if not seen or seen too long ago.
    """
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_SUPPRESSION_DAYS)).isoformat()
    url = f"{SUPABASE_URL}/rest/v1/seen_listings"
    params = {
        "select": "*",
        "mls_number": f"eq.{mls_number}",
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


def db_upsert_seen(mls_number: str, slug: str, score: int, tier: str) -> None:
    """Insert or update seen_listings for this MLS number."""
    url = f"{SUPABASE_URL}/rest/v1/seen_listings"
    headers = _sb_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    payload = {
        "mls_number": mls_number,
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
    hero_image_url: str, today_ct: date
) -> None:
    """Insert into published_listings."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    payload = {
        "slug": slug,
        "mls_number": mls_number,
        "webflow_item_id": webflow_item_id,
        "score": score,
        "tier": tier,
        "category": category,
        "headline": headline,
        "hero_image_url": hero_image_url,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_date_ct": today_ct.isoformat(),
    }
    try:
        r = requests.post(url, headers=_sb_headers(), json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase insert_published error: {e}")


def db_insert_run(run_data: dict) -> int | None:
    """Insert a pipeline_runs row, return the new id."""
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
    """Update a pipeline_runs row by id."""
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
    log.info(
        f"[TOKENS] {call_name} | in={input_tokens} out={output_tokens} "
        f"| est_cost=${cost:.5f}"
    )
    return cost


# ---------------------------------------------------------------------------
# Repliers API
# ---------------------------------------------------------------------------

def fetch_listings() -> list[dict]:
    params = {
        "status": "A",
        "maxPrice": 150000,
        "resultsPerPage": 50,
        "sortBy": "updatedOnDesc",
    }
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
# Claude API
# ---------------------------------------------------------------------------

def call_claude(system: str, user: str, call_name: str) -> tuple[str | None, float]:
    """Returns (text, cost)."""
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
        return None, 0.0

    data = r.json()
    usage = data.get("usage", {})
    cost = log_tokens(call_name, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
    content_blocks = data.get("content", [])
    text_blocks = [b["text"] for b in content_blocks if b.get("type") == "text"]
    text = "\n".join(text_blocks).strip() if text_blocks else None
    return text, cost


# ---------------------------------------------------------------------------
# Call 1 — Scoring
# ---------------------------------------------------------------------------

def build_scoring_input(listing: dict) -> str:
    addr    = listing.get("address", {})
    details = listing.get("details", {})
    lot     = listing.get("lot", {})
    nearby  = listing.get("nearby", {})

    price        = parse_price(listing.get("listPrice", 0))
    address      = build_address(addr)
    city         = addr.get("city", "")
    state_full   = addr.get("state", "")
    state        = state_abbrev(state_full)
    beds         = parse_int(details.get("numBedrooms"))
    baths        = parse_int(details.get("numBathrooms"))
    sqft         = parse_sqft(details.get("sqft"))
    year         = parse_int(details.get("yearBuilt"))
    dom          = parse_int(listing.get("daysOnMarket"))
    price_change = listing.get("lastPriceChangeType", "none") or "none"
    last_status  = listing.get("lastStatus", "") or ""
    prop_type    = details.get("propertyType", "") or ""
    style        = details.get("style", "") or ""
    exterior     = details.get("exteriorConstruction1", "") or ""
    pool         = "Y" if str(details.get("swimmingPool", "")).upper() == "Y" else "N"
    waterfront   = "Y" if str(details.get("waterfront", "")).upper() == "Y" else "N"
    acres_raw    = lot.get("acres")
    acreage      = str(round(float(acres_raw), 2)) if acres_raw else "null"
    amenities    = nearby.get("amenities", [])
    amenities_str = ", ".join(amenities) if amenities else "null"
    description  = details.get("description", "") or "(no description)"

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
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def score_listing(listing: dict) -> tuple[dict | None, float]:
    """Returns (score_data, cost)."""
    user_input = build_scoring_input(listing)
    raw, cost = call_claude(SCORING_PROMPT, user_input, "scoring")
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
    """Returns (content, cost)."""
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    price       = parse_price(listing.get("listPrice", 0))
    address     = build_address(addr)
    city        = addr.get("city", "")
    state_full  = addr.get("state", "")
    beds        = parse_int(details.get("numBedrooms"))
    baths       = parse_int(details.get("numBathrooms"))
    sqft        = parse_sqft(details.get("sqft"))
    year_built  = parse_int(details.get("yearBuilt"))
    description = details.get("description", "") or "(no description)"

    prompt = CONTENT_PROMPT_TEMPLATE.format(
        address=address, city=city, state_full=state_full,
        price_display=make_price_display(price),
        bedrooms=beds, bathrooms=baths, sqft=sqft, year_built=year_built,
        category=score_data.get("CATEGORY", ""),
        key_hooks=score_data.get("KEY_HOOKS", ""),
        description=description,
    )
    raw, cost = call_claude("You are a real estate content writer.", prompt, "content_gen")
    if not raw:
        return None, cost
    return parse_content_output(raw), cost


def parse_content_output(text: str) -> dict:
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
    if "imagedelivery.net" in image_url:
        log.info(f"Image already on Cloudflare, skipping: {image_url}")
        return image_url

    if not image_url.startswith("http"):
        image_url = f"{REPLIERS_CDN}/{image_url}"

    log.info(f"Fetching image: {image_url}")
    try:
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to fetch image {image_url}: {e}")
        return None

    content_type = img_response.headers.get("content-type", "image/jpeg")
    log.info(f"Uploading to Cloudflare Images ({len(img_response.content)} bytes)...")
    try:
        cf_response = requests.post(
            CF_IMAGES_BASE,
            headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
            files={"file": (f"{slug}.jpg", img_response.content, content_type)},
            timeout=60,
        )
        cf_response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Cloudflare upload failed: {e}")
        return None

    cf_data = cf_response.json()
    if not cf_data.get("success"):
        log.error(f"Cloudflare error: {cf_data.get('errors')}")
        return None

    variants = cf_data.get("result", {}).get("variants", [])
    if variants:
        log.info(f"Cloudflare URL: {variants[0]}")
        return variants[0]

    image_id = cf_data.get("result", {}).get("id")
    if image_id:
        url = f"{CF_DELIVERY_BASE}/{image_id}/public"
        log.info(f"Cloudflare URL (constructed): {url}")
        return url

    log.error("Cloudflare upload succeeded but no URL returned")
    return None


# ---------------------------------------------------------------------------
# Webflow CMS
# ---------------------------------------------------------------------------

def write_webflow(listing: dict, score_data: dict, content: dict, hero_image_url: str) -> str | None:
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    price      = parse_price(listing.get("listPrice", 0))
    city       = addr.get("city", "")
    state_full = addr.get("state", "")
    address    = build_address(addr)
    slug       = make_slug(city, price)
    beds       = parse_int(details.get("numBedrooms"))
    baths      = parse_int(details.get("numBathrooms"))
    sqft       = parse_sqft(details.get("sqft"))
    year       = parse_int(details.get("yearBuilt"))

    headline      = content.get("HEADLINE", "")
    name          = headline if headline else f"{city}, {state_full} — ${make_price_display(price)}"
    listing_url   = f"https://housesunder150k.com/listings/{slug}"
    affiliate_url = make_realtor_url(addr)
    is_hero       = score_data.get("DEAL_OF_DAY_CANDIDATE", "NO").upper() == "YES"

    field_data = {
        "name":             name,
        "slug":             slug,
        "price":            price,
        "price-display":    make_price_display(price),
        "location-display": f"{city}, {state_full}",
        "address":          address,
        "city":             city,
        "state":            state_abbrev(state_full),
        "year-built":       year,
        "bedrooms":         beds,
        "bathrooms":        baths,
        "square-feet":      sqft,
        "hero-image":       {"url": hero_image_url},
        "narrative-body":   format_richtext(content.get("NARRATIVE", "")),
        "short-summary":    content.get("SHORT_SUMMARY", ""),
        "listing-url":      listing_url,
        "affiliate-url":    affiliate_url,
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

    item_id = r.json().get("id")
    log.info(f"Webflow item created: {item_id}")
    return item_id


def publish_webflow(item_id: str) -> bool:
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

def process_listing(listing: dict, today_ct: date, published_today: int) -> tuple[str, float]:
    """
    Run the full pipeline for a single listing.
    Returns: ('published' | 'skipped_score' | 'skipped_dedup' | 'skipped_seen' | 'error', cost)
    """
    addr    = listing.get("address", {})
    price   = parse_price(listing.get("listPrice", 0))
    city    = addr.get("city", "unknown")
    mls_num = listing.get("mlsNumber", "unknown")
    slug    = make_slug(city, price)
    total_cost = 0.0

    log.info(f"--- Processing: {city} ${make_price_display(price)} (MLS {mls_num}) ---")

    # 1. Dedup — already published
    if db_slug_published(slug):
        log.info(f"Skipping {slug} — already published (Supabase)")
        return "skipped_dedup", 0.0

    # 2. Seen suppression — scored and discarded within suppression window
    seen = db_mls_seen_recently(mls_num)
    if seen:
        log.info(
            f"Skipping MLS {mls_num} — seen {seen['times_seen']}x, "
            f"last score={seen['score']} ({seen['tier']}) within {SEEN_SUPPRESSION_DAYS} days"
        )
        # Update last_seen_at and increment counter
        db_upsert_seen(mls_num, slug, seen["score"], seen["tier"])
        return "skipped_seen", 0.0

    # 3. Score
    score_data, score_cost = score_listing(listing)
    total_cost += score_cost
    if not score_data:
        log.error(f"Scoring failed for {slug}")
        return "error", total_cost

    score = score_data.get("SCORE", 0)
    tier  = score_data.get("TIER", "SKIP")

    # Always upsert to seen_listings after scoring
    db_upsert_seen(mls_num, slug, score, tier)

    if score <= 5:
        log.info(f"Score {score} <= 5 — discarding {slug}")
        return "skipped_score", total_cost

    # 4. Generate content
    content, content_cost = generate_content(listing, score_data)
    total_cost += content_cost
    if not content:
        log.error(f"Content generation failed for {slug}")
        return "error", total_cost

    # 5. Upload image
    images = listing.get("images", [])
    hero_image_url = ""
    if images:
        hero_image_url = upload_image(images[0], slug) or ""
    if not hero_image_url:
        log.warning(f"No hero image for {slug} — proceeding without image")

    # 6. Write to Webflow
    item_id = write_webflow(listing, score_data, content, hero_image_url)
    if not item_id:
        log.error(f"Webflow write failed for {slug}")
        return "error", total_cost

    # 7. Publish
    if not publish_webflow(item_id):
        log.error(f"Webflow publish failed for item {item_id}")
        return "error", total_cost

    # 8. Record in Supabase published_listings
    db_insert_published(
        slug=slug,
        mls_number=mls_num,
        webflow_item_id=item_id,
        score=score,
        tier=tier,
        category=score_data.get("CATEGORY", ""),
        headline=content.get("HEADLINE", ""),
        hero_image_url=hero_image_url,
        today_ct=today_ct,
    )

    log.info(f"Published: {slug} (score={score}, tier={tier})")
    return "published", total_cost


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline():
    log.info("=== HousesUnder150K Ingestion Pipeline Start ===")
    start = time.time()
    today_ct = get_today_ct()

    # Record run start
    run_id = db_insert_run({"started_at": datetime.now(timezone.utc).isoformat()})

    # FIRST: check daily limit before any API calls
    count_today = db_count_published_today(today_ct)
    log.info(f"Published today (CT): {count_today}/{DAILY_PUBLISH_LIMIT}")

    if count_today >= DAILY_PUBLISH_LIMIT:
        log.info(f"Daily limit reached — exiting without processing")
        if run_id:
            db_update_run(run_id, {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "daily_limit_hit": True,
                "notes": f"Exited: daily limit {count_today}/{DAILY_PUBLISH_LIMIT} already reached",
            })
        return

    # Fetch listings
    listings = fetch_listings()
    if not listings:
        log.info("No listings returned — exiting")
        if run_id:
            db_update_run(run_id, {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "listings_fetched": 0,
            })
        return

    stats = {
        "published": 0, "skipped_score": 0, "skipped_dedup": 0,
        "skipped_seen": 0, "error": 0,
    }
    total_tokens_scoring = 0
    total_tokens_content = 0
    total_cost = 0.0
    published_this_run = 0

    for listing in listings:
        # Check if we've hit the daily limit mid-batch
        if count_today + published_this_run >= DAILY_PUBLISH_LIMIT:
            log.info(f"Daily limit reached mid-batch — stopping")
            break

        try:
            result, cost = process_listing(listing, today_ct, count_today + published_this_run)
            stats[result] = stats.get(result, 0) + 1
            total_cost += cost
            if result == "published":
                published_this_run += 1
        except Exception as e:
            log.error(f"Unhandled error processing listing: {e}", exc_info=True)
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


if __name__ == "__main__":
    run_pipeline()
