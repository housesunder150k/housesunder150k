"""
HousesUnder150K.com — Ingestion Pipeline
Runs on Railway 3x/day: 8am, 1pm, 6pm CT
Fetches listings from RealtyAPI (Redfin), scores, generates content, publishes to Webflow.
Dedup, daily limit, and seen-listing suppression via Supabase.
Data source: RealtyAPI (realtyapi.io) — Redfin endpoint
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

CLAUDE_MODEL           = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS      = 1000
REALTYAPI_BASE         = "https://redfin.realtyapi.io"
ANTHROPIC_BASE         = "https://api.anthropic.com/v1/messages"
CF_IMAGES_BASE         = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1"
CF_DELIVERY_BASE       = "https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w"
WEBFLOW_BASE           = "https://api.webflow.com/v2"

SEEN_SUPPRESSION_DAYS  = 7
CT_TZ                  = pytz.timezone("America/Chicago")

# States to rotate through — shuffled each run for geographic diversity
US_STATES = [
    "Alabama", "Arkansas", "Georgia", "Illinois", "Indiana", "Iowa", "Kansas",
    "Kentucky", "Louisiana", "Michigan", "Minnesota", "Mississippi", "Missouri",
    "Nebraska", "North Carolina", "Ohio", "Oklahoma", "Pennsylvania",
    "South Carolina", "Tennessee", "Texas", "Virginia", "West Virginia", "Wisconsin",
]

# Webflow CMS
WF_STATUS_ACTIVE = "3b41185e9af84f92d8da092965308a2d"

# Claude pricing (Sonnet 4.6)
COST_PER_1K_INPUT  = 0.003
COST_PER_1K_OUTPUT = 0.015

# State abbreviation -> full name (Redfin returns 2-letter abbreviation)
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
- Price reduction signal in description
- High days on market + low price
- Rich agent description with specifics: +0.5 to +1

NEGATIVE MODIFIERS:
- Manufactured/mobile/modular: -3
- Condo/unit in multi-family complex: -2 (lot size reflects complex parcel, not buyer's land — ignore any acreage signal)
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
    return datetime.now(CT_TZ).date()


def parse_int(raw) -> int:
    try:
        return int(float(str(raw))) if raw is not None else 0
    except (ValueError, TypeError):
        return 0


def make_slug(city: str, price: int) -> str:
    city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
    return f"{city_slug}-{price}"


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


def db_mls_seen_recently(mls_number: str) -> dict | None:
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
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    payload = {
        "slug": slug, "mls_number": mls_number, "webflow_item_id": webflow_item_id,
        "score": score, "tier": tier, "category": category, "headline": headline,
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


REALTYAPI_REALTOR_BASE = "https://realtor.realtyapi.io"


def fetch_search_results(state_name: str, result_count: int = 50) -> list[dict]:
    """Fetch active for-sale listings under $150K in a given state via Realtor.com."""
    params = {
        "location": state_name,
        "priceRange": "max:150000",
        "searchType": "For_Sale",
        "propertyType": "House,Townhome",
        "sortOrder": "Newest",
        "hasPhotos": True,
        "seniorCommunity": False,
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
    """Fetch full listing details including description from Realtor.com."""
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
    """Extract listing description from Realtor.com details/byid response."""
    if not details:
        return ""
    # Response root is 'detail', description is at detail.details.text
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
    """Extract year built from Realtor.com details/byid response."""
    if not details:
        return 0
    detail = details.get("detail") or details
    inner = detail.get("details") or {}
    return parse_int(inner.get("year_built") or 0)


def normalize_listing(result: dict, description: str) -> dict | None:
    """Normalize a Realtor.com search result into the pipeline's listing dict."""
    prop = result.get("property_id", "")
    listing_id = result.get("listing_id", "")
    mls_id = prop  # use property_id as unique identifier

    if not prop:
        return None

    # Address — flat on result
    address = result.get("address", {}) or {}
    street = address.get("line", "") or ""
    city = address.get("city", "") or ""
    state_abbr = address.get("state_code", "") or ""
    zip_code = address.get("postal_code", "") or ""
    state_full = STATE_FULL_NAME.get(state_abbr, state_abbr)

    # Price, specs — top-level fields
    list_price = parse_int(result.get("list_price") or 0)
    beds = parse_int(result.get("beds") or 0)
    baths = parse_int(result.get("baths") or 0)
    sqft = parse_int(result.get("sqft") or 0)
    lot_sqft = parse_int(result.get("lot_sqft") or 0)
    lot_acres = round(lot_sqft / 43560, 2) if lot_sqft else None

    # Year built not in search results — will be null until detail call enriches it
    year_built = 0

    # DOM — derive from list_date if available
    dom = 0

    # Photos — plain URL strings
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

    # Waterfront/pool from description
    desc_lower = description.lower()
    waterfront = any(w in desc_lower for w in [
        "waterfront", "water front", "lakefront", "lake front",
        "riverfront", "river front", "oceanfront", "pond",
    ])
    pool = "pool" in desc_lower

    return {
        "mlsNumber": mls_id,
        "propertyId": prop,
        "listingId": listing_id,
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
    """
    Rotate through US states, collect up to 50 unique active listings under $150K.
    Uses Realtor.com via RealtyAPI for nationwide coverage.
    Fetches full details per listing to get description.
    Returns normalized listing dicts.
    Max 1 publishable candidate per state to ensure geographic diversity.
    """
    target = 50
    collected = []
    seen_ids = set()

    states = US_STATES.copy()
    random.shuffle(states)

    for state in states:
        if len(collected) >= target:
            break

        results = fetch_search_results(state, result_count=50)
        if not results:
            continue

        state_published = False

        for result in results:
            if len(collected) >= target:
                break
            if state_published:
                break

            prop_id = result.get("property_id", "") or result.get("propertyId", "")
            if not prop_id or prop_id in seen_ids:
                continue

            # Fetch full details for description and year built
            details = fetch_listing_details(prop_id)
            time.sleep(0.2)

            description = extract_description(details)
            year_built = extract_year_built(details)

            listing = normalize_listing(result, description)
            if not listing:
                continue

            # Enrich with year_built from detail call
            listing["details"]["yearBuilt"] = year_built
            listing["_state"] = state  # track for diversity flag

            # Skip if price is 0 or missing
            if listing["listPrice"] <= 0:
                continue

            seen_ids.add(prop_id)
            collected.append(listing)
            state_published = True  # move to next state after first candidate

    log.info(f"Fetched {len(collected)} total listings")
    return collected


# ---------------------------------------------------------------------------
# Claude API
# ---------------------------------------------------------------------------

def call_claude(system: str, user: str, call_name: str) -> tuple[str | None, float]:
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
    # Nullify acreage for small multi-unit properties — lot size is the complex parcel, not buyer's land
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
    return result


# ---------------------------------------------------------------------------
# Cloudflare Images
# ---------------------------------------------------------------------------

def upload_image(image_url: str, slug: str) -> str | None:
    if "imagedelivery.net" in image_url:
        return image_url

    log.info(f"Fetching image: {image_url}")
    try:
        img_r = requests.get(image_url, timeout=30)
        img_r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to fetch image: {e}")
        return None

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
        return None

    cf_data = cf_r.json()
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

    return None


# ---------------------------------------------------------------------------
# Webflow CMS
# ---------------------------------------------------------------------------

def write_webflow(listing: dict, score_data: dict, content: dict, hero_image_url: str) -> str | None:
    addr    = listing.get("address", {})
    details = listing.get("details", {})

    price      = parse_int(listing.get("listPrice", 0))
    city       = addr.get("city", "")
    state_abbr = addr.get("state", "")
    state_full = addr.get("stateFull", state_abbr)
    address    = addr.get("formattedStreetLine", "")
    zip_code   = addr.get("zip", "")
    slug       = make_slug(city, price)
    beds       = parse_int(details.get("numBedrooms"))
    baths      = parse_int(details.get("numBathrooms"))
    sqft       = parse_int(details.get("sqft"))
    year       = parse_int(details.get("yearBuilt"))

    headline    = content.get("HEADLINE", "")
    name        = headline if headline else f"{city}, {state_full} — ${make_price_display(price)}"
    is_hero     = score_data.get("DEAL_OF_DAY_CANDIDATE", "NO").upper() == "YES"

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
        "listing-url":      f"https://housesunder150k.com/listings/{slug}",
        "affiliate-url":    make_realtor_url(address, city, state_abbr, zip_code),
        "social-caption":   content.get("SOCIAL_CAPTION", ""),
        "status":           WF_STATUS_ACTIVE,
        "deal-of-the-day":  is_hero,
    }

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


# ---------------------------------------------------------------------------
# Per-listing pipeline
# ---------------------------------------------------------------------------

def process_listing(listing: dict, today_ct: date) -> tuple[str, float]:
    addr    = listing.get("address", {})
    price   = parse_int(listing.get("listPrice", 0))
    city    = addr.get("city", "unknown")
    mls_num = listing.get("mlsNumber", "unknown")
    slug    = make_slug(city, price)
    total_cost = 0.0

    log.info(f"--- Processing: {city} ${make_price_display(price)} (MLS {mls_num}) ---")

    if db_slug_published(slug):
        log.info(f"Skipping {slug} — already published")
        return "skipped_dedup", 0.0

    seen = db_mls_seen_recently(mls_num)
    if seen:
        log.info(f"Skipping MLS {mls_num} — seen {seen['times_seen']}x, score={seen['score']} within {SEEN_SUPPRESSION_DAYS}d")
        db_upsert_seen(mls_num, slug, seen["score"], seen["tier"])
        return "skipped_seen", 0.0

    score_data, score_cost = score_listing(listing)
    total_cost += score_cost
    if not score_data:
        return "error", total_cost

    score = score_data.get("SCORE", 0)
    tier  = score_data.get("TIER", "SKIP")
    db_upsert_seen(mls_num, slug, score, tier)

    if score <= 5:
        log.info(f"Score {score} <= 5 — discarding {slug}")
        return "skipped_score", total_cost

    content, content_cost = generate_content(listing, score_data)
    total_cost += content_cost
    if not content:
        return "error", total_cost

    images = listing.get("images", [])
    hero_image_url = upload_image(images[0], slug) if images else ""
    if not hero_image_url:
        log.warning(f"No hero image for {slug}")

    item_id = write_webflow(listing, score_data, content, hero_image_url)
    if not item_id:
        return "error", total_cost

    if not publish_webflow(item_id):
        return "error", total_cost

    db_insert_published(
        slug=slug, mls_number=mls_num, webflow_item_id=item_id,
        score=score, tier=tier, category=score_data.get("CATEGORY", ""),
        headline=content.get("HEADLINE", ""), hero_image_url=hero_image_url,
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

    for listing in listings:
        if count_today + published_this_run >= DAILY_PUBLISH_LIMIT:
            log.info("Daily limit reached mid-batch — stopping")
            break

        try:
            result, cost = process_listing(listing, today_ct)
            stats[result] = stats.get(result, 0) + 1
            total_cost += cost
            if result == "published":
                published_this_run += 1
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


if __name__ == "__main__":
    run_pipeline()
