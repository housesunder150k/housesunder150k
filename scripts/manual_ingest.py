"""
HousesUnder150K.com — Manual Listing Ingestion Service
Runs on Railway cron: */30 * * * * (every 30 minutes)

Purpose:
  Polls the manual_listing_requests Supabase table for pending rows.
  For each pending request, fetches the property from RealtyAPI by address,
  runs it through the full scoring + content generation + Cloudflare + Webflow
  pipeline (same logic as ingest.py), then publishes to the site.

  Key differences from ingest.py:
  - No DAILY_PUBLISH_LIMIT check — manual injections bypass the daily cap
  - No seen_listings suppression — operator has explicitly requested this listing
  - No dedup suppression window — same as above
  - Fetches by address (RealtyAPI /details/byaddress) rather than search
  - Deal of Day assignment follows Jeremy's explicit choice + auto-forward logic
  - FB/IG approval flags set per request row (post_facebook, post_instagram)
  - Uses service_role key — RLS bypassed same as all other pipeline scripts

Deal of Day logic:
  If is_deal_of_day = true on the request:
    1. If deal_of_day_date is set AND no Deal of Day exists for that date: use that date
    2. If deal_of_day_date is NULL:
        - If today has no Deal of Day: set is_deal_of_day = true, published_date_ct = today
        - If today already has a Deal of Day: auto-forward to tomorrow, published_date_ct = tomorrow
           The listing is published to the site immediately but with published_date_ct = tomorrow
           so the pipeline and social scripts pick it up on the right day.
  If is_deal_of_day = false: publish normally, no Deal of Day slot assigned.

FB/IG approval:
  If post_facebook = true on the request: sets fb_ig_approved_facebook = true on the
  published_listings row immediately after insert.
  Same for post_instagram / fb_ig_approved_instagram.
  These listings are then available to facebook.py and instagram.py on their next run.

Dry run:
  python manual_ingest.py --dry-run
  Processes pending requests, fetches + scores + generates content, but does NOT
  write to Webflow or Supabase. Safe to run anytime for testing.

Environment variables required:
  REALTYAPI_KEY          — RealtyAPI key (realtyapi.io)
  ANTHROPIC_API_KEY      — for scoring and content generation
  CLOUDFLARE_API_TOKEN   — for image upload
  CLOUDFLARE_ACCOUNT_ID  — Cloudflare account
  WEBFLOW_API_TOKEN      — for CMS item creation and publish
  WEBFLOW_COLLECTION_ID  — Webflow listings collection ID
  SOVRN_AFFILIATE_URL    — affiliate URL (same as ingest.py)
  SUPABASE_URL           — HousesUnder150K Supabase project URL
  SUPABASE_KEY           — Supabase service role key

Changes:
  2026-09-07: Initial implementation
"""

import os
import re
import time
import logging
import argparse
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
# Config
# ---------------------------------------------------------------------------

REALTYAPI_KEY         = os.environ["REALTYAPI_KEY"]
ANTHROPIC_API_KEY     = os.environ["ANTHROPIC_API_KEY"]
CLOUDFLARE_API_TOKEN  = os.environ["CLOUDFLARE_API_TOKEN"]
CLOUDFLARE_ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
WEBFLOW_API_TOKEN     = os.environ["WEBFLOW_API_TOKEN"]
WEBFLOW_COLLECTION_ID = os.environ["WEBFLOW_COLLECTION_ID"]
SOVRN_AFFILIATE_URL   = os.environ["SOVRN_AFFILIATE_URL"]
SUPABASE_URL          = os.environ["SUPABASE_URL"]
SUPABASE_KEY          = os.environ["SUPABASE_KEY"]

REALTYAPI_BASE = "https://realtor.realtyapi.io"
ANTHROPIC_BASE = "https://api.anthropic.com/v1/messages"
CF_IMAGES_BASE = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1"
CF_DELIVERY_BASE = "https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w"
WEBFLOW_BASE   = "https://api.webflow.com/v2"
WEBFLOW_SITE_ID    = "6a650a7eb2639262c4b6adb7"
WEBFLOW_DOMAIN_IDS = ["6a661987994ab168be06566b", "6a661986994ab168be065664"]

CLAUDE_MODEL              = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS_SCORING = 250
CLAUDE_MAX_TOKENS_CONTENT = 900
CLAUDE_MAX_TOKENS_REVIEW  = 900

CT_TZ = pytz.timezone("America/Chicago")

WF_STATUS_ACTIVE = "3b41185e9af84f92d8da092965308a2d"

COST_PER_1K_INPUT  = 0.003
COST_PER_1K_OUTPUT = 0.015

# ---------------------------------------------------------------------------
# Shared lookup tables (identical to ingest.py)
# ---------------------------------------------------------------------------

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

TAG_MAP = {
    "WATERFRONT": "Waterfront", "ACREAGE": "Acreage", "HISTORIC": "Historic",
    "RENOVATED": "Renovated", "NEW_CONSTRUCTION": "New Construction",
    "CHARACTER": "Character Home", "HIDDEN_GEM": "Hidden Gem",
    "pool": "Pool", "barn": "Barn", "garage": "Garage",
    "basement": "Finished Basement", "fireplace": "Fireplace",
    "acreage": "Acreage", "waterfront": "Waterfront", "lake": "Lake Access",
    "creek": "Creek", "wooded": "Wooded Lot", "farmhouse": "Farmhouse",
    "victorian": "Victorian", "craftsman": "Craftsman", "log cabin": "Log Cabin",
    "stone": "Stone Construction", "new roof": "New Roof", "new hvac": "Updated HVAC",
    "rental": "Income Potential", "airbnb": "Income Potential", "income": "Income Potential",
}

GALLERY_PHOTO_COUNT = 3

# ---------------------------------------------------------------------------
# Prompts (imported from ingest.py — identical, no drift allowed)
# ---------------------------------------------------------------------------

# Load from the shared prompts directory at runtime to avoid duplication
import sys

def _load_ingest_prompts():
    """Import scoring/content/review prompts from ingest.py module."""
    ingest_path = os.path.join(os.path.dirname(__file__), "ingest.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("ingest", ingest_path)
    mod = importlib.util.module_from_spec(spec)
    # Suppress env var errors during import — we only need the constants
    import unittest.mock
    with unittest.mock.patch.dict(os.environ, {
        "REALTYAPI_KEY": "x", "ANTHROPIC_API_KEY": "x",
        "CLOUDFLARE_API_TOKEN": "x", "CLOUDFLARE_ACCOUNT_ID": "x",
        "WEBFLOW_API_TOKEN": "x", "WEBFLOW_COLLECTION_ID": "x",
        "SOVRN_AFFILIATE_URL": "x", "SUPABASE_URL": "x", "SUPABASE_KEY": "x",
    }, clear=False):
        spec.loader.exec_module(mod)
    return mod

_ingest = _load_ingest_prompts()

SCORING_PROMPT         = _ingest.SCORING_PROMPT
CONTENT_PROMPT_TEMPLATE = _ingest.CONTENT_PROMPT_TEMPLATE
REVIEW_PROMPT          = _ingest.REVIEW_PROMPT

# Re-use helper functions from ingest to keep logic in one place
parse_int              = _ingest.parse_int
make_slug              = _ingest.make_slug
make_price_display     = _ingest.make_price_display
format_richtext        = _ingest.format_richtext
make_realtor_url       = _ingest.make_realtor_url
make_address_key       = _ingest.make_address_key
make_image_alt         = _ingest.make_image_alt
generate_tags          = _ingest.generate_tags
parse_scoring_output   = _ingest.parse_scoring_output
parse_content_output   = _ingest.parse_content_output
build_scoring_input    = _ingest.build_scoring_input
log_tokens             = _ingest.log_tokens

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_today_ct() -> date:
    return datetime.now(CT_TZ).date()

def get_tomorrow_ct() -> date:
    return get_today_ct() + timedelta(days=1)

# ---------------------------------------------------------------------------
# Supabase — manual_listing_requests queue
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def fetch_pending_requests() -> list[dict]:
    """Fetch all pending manual listing requests, oldest first."""
    url = f"{SUPABASE_URL}/rest/v1/manual_listing_requests"
    params = {
        "select": "*",
        "status": "eq.pending",
        "order": "created_at.asc",
        "limit": "10",  # process max 10 per poll to avoid long-running jobs
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        rows = r.json()
        log.info(f"Pending requests: {len(rows)}")
        return rows
    except Exception as e:
        log.error(f"Supabase fetch_pending_requests error: {e}")
        return []


def mark_request_processing(request_id: int) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/manual_listing_requests"
    params = {"id": f"eq.{request_id}"}
    try:
        r = requests.patch(url, headers=_sb_headers(), params=params,
                           json={"status": "processing"}, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        log.error(f"Supabase mark_request_processing error: {e}")
        return False


def mark_request_done(request_id: int, result_slug: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/manual_listing_requests"
    params = {"id": f"eq.{request_id}"}
    try:
        r = requests.patch(url, headers=_sb_headers(), params=params, json={
            "status": "done",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "result_slug": result_slug,
        }, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase mark_request_done error: {e}")


def mark_request_failed(request_id: int, error_message: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/manual_listing_requests"
    params = {"id": f"eq.{request_id}"}
    try:
        r = requests.patch(url, headers=_sb_headers(), params=params, json={
            "status": "failed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": error_message[:500],
        }, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase mark_request_failed error: {e}")


def deal_of_day_exists_for_date(target_date: date) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug",
        "published_date_ct": f"eq.{target_date.isoformat()}",
        "is_deal_of_day": "eq.true",
        "limit": 1,
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return len(r.json()) > 0
    except Exception as e:
        log.error(f"Supabase deal_of_day_exists_for_date error: {e}")
        return False


def get_active_deal_of_day() -> dict | None:
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


def insert_published_listing(
    slug: str, address_key: str, webflow_item_id: str,
    score: int, tier: str, category: str, headline: str,
    hero_image_url: str, publish_date_ct: date, price: int,
    is_deal_of_day: bool, gallery_image_ids: list[str],
    short_summary: str | None, social_caption: str | None,
    city: str | None, state: str | None,
    post_facebook: bool, post_instagram: bool,
) -> None:
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    payload = {
        "slug": slug,
        "mls_number": address_key,
        "webflow_item_id": webflow_item_id,
        "score": score,
        "tier": tier,
        "category": category,
        "headline": headline,
        "hero_image_url": hero_image_url,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_date_ct": publish_date_ct.isoformat(),
        "price": price,
        "is_deal_of_day": is_deal_of_day,
        "gallery_image_ids": gallery_image_ids,
        "short_summary": short_summary,
        "social_caption": social_caption,
        "city": city,
        "state": state,
        "fb_ig_approved_facebook": post_facebook,
        "fb_ig_approved_instagram": post_instagram,
    }
    try:
        r = requests.post(url, headers=_sb_headers(), json=payload, timeout=10)
        r.raise_for_status()
        log.info(f"Supabase insert_published: {slug} (fb={post_facebook} ig={post_instagram})")
    except Exception as e:
        log.error(f"Supabase insert_published error: {e}")


# ---------------------------------------------------------------------------
# RealtyAPI — fetch by address
# ---------------------------------------------------------------------------

def fetch_by_address(address: str) -> dict | None:
    """
    Fetch property details from RealtyAPI using a full address string.
    address format: "123 Main St, Springfield, IL 62701"
    Returns the raw API response dict or None on failure.
    """
    try:
        r = requests.get(
            f"{REALTYAPI_BASE}/details/byaddress",
            headers={"x-realtyapi-key": REALTYAPI_KEY},
            params={"address": address},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        log.info(f"RealtyAPI /details/byaddress response keys: {list(data.keys())}")
        return data
    except requests.RequestException as e:
        log.error(f"RealtyAPI /details/byaddress error for '{address}': {e}")
        return None


def normalize_address_response(data: dict, original_address: str) -> dict | None:
    """
    Convert RealtyAPI /details/byaddress response into the normalized listing
    format that the scoring/content/Webflow pipeline expects.
    Same shape as normalize_listing() in ingest.py.
    """
    # The /details/byaddress response may nest data differently than /search/bylocation
    # Try multiple paths for common fields
    detail = data.get("detail") or data.get("property") or data

    # Address
    address_raw = detail.get("address") or data.get("address") or {}
    street  = address_raw.get("line") or address_raw.get("street_line") or ""
    city    = address_raw.get("city") or ""
    state_a = address_raw.get("state_code") or address_raw.get("state") or ""
    zip_c   = address_raw.get("postal_code") or address_raw.get("zip") or ""

    # Fall back to parsing original_address if API doesn't return structured address
    if not street or not city or not state_a:
        parts = [p.strip() for p in original_address.split(",")]
        if len(parts) >= 3:
            street  = street  or parts[0]
            city    = city    or parts[1]
            # "IL 62701" -> state abbr
            state_zip = parts[2].strip().split()
            if not state_a and state_zip:
                state_a = state_zip[0]
            if not zip_c and len(state_zip) > 1:
                zip_c = state_zip[1]

    if not state_a:
        log.error(f"Could not determine state for address: {original_address}")
        return None

    state_full = STATE_FULL_NAME.get(state_a.upper(), state_a)
    address_key = make_address_key(street, city, state_a)

    # Price
    price = parse_int(
        detail.get("list_price")
        or detail.get("listing", {}).get("list_price")
        or data.get("list_price")
        or 0
    )

    # Property details
    inner = detail.get("details") or detail.get("detail") or {}
    beds  = parse_int(inner.get("beds") or detail.get("beds") or 0)
    baths = parse_int(inner.get("baths") or detail.get("baths") or 0)
    sqft  = parse_int(inner.get("sqft") or detail.get("sqft") or 0)
    year  = parse_int(inner.get("year_built") or detail.get("year_built") or 0)

    lot_sqft  = parse_int(inner.get("lot_sqft") or detail.get("lot_sqft") or 0)
    lot_acres = round(lot_sqft / 43560, 2) if lot_sqft else None

    # Description
    desc_candidates = [
        inner.get("text", ""),
        detail.get("description", ""),
        detail.get("remarks", ""),
        detail.get("publicRemarks", ""),
        data.get("description", ""),
    ]
    description = next((c for c in desc_candidates if isinstance(c, str) and len(c) > 10), "")

    desc_lower = description.lower()
    waterfront = any(w in desc_lower for w in [
        "waterfront", "water front", "lakefront", "lake front",
        "riverfront", "river front", "oceanfront", "pond",
    ])
    pool = "pool" in desc_lower

    # Images — try multiple paths
    photos = []
    primary = detail.get("primary_photo") or data.get("primary_photo") or ""
    if isinstance(primary, str) and primary:
        photos.append(primary)
    elif isinstance(primary, dict) and primary.get("href"):
        photos.append(primary["href"])

    for photo in (detail.get("photos") or data.get("photos") or []):
        url = photo if isinstance(photo, str) else (photo.get("href", "") if isinstance(photo, dict) else "")
        if url and url not in photos:
            photos.append(url)

    # Listing href for affiliate URL
    listing_href = (
        detail.get("href")
        or detail.get("listing", {}).get("href")
        or data.get("href")
        or ""
    )

    return {
        "mlsNumber": address_key,
        "propertyId": detail.get("property_id") or data.get("property_id") or "",
        "listingId":  detail.get("listing_id")  or data.get("listing_id")  or "",
        "listingHref": listing_href,
        "listPrice":  price,
        "listDate":   None,  # not available from /details/byaddress
        "address": {
            "formattedStreetLine": street,
            "city":     city,
            "state":    state_a.upper(),
            "stateFull": state_full,
            "zip":      zip_c,
        },
        "details": {
            "numBedrooms":  beds,
            "numBathrooms": baths,
            "sqft":         sqft,
            "yearBuilt":    year,
            "description":  description,
            "lotAcres":     lot_acres,
            "waterfront":   waterfront,
            "pool":         pool,
        },
        "images": photos,
    }

# ---------------------------------------------------------------------------
# Claude API (mirrors ingest.py call_claude)
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
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
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
    blocks = data.get("content", [])
    text = "\n".join(b["text"] for b in blocks if b.get("type") == "text").strip()
    return text if text else None, cost


def score_listing(listing: dict) -> tuple[dict | None, float]:
    raw, cost = call_claude(SCORING_PROMPT, build_scoring_input(listing), "scoring")
    if not raw:
        return None, cost
    parsed = parse_scoring_output(raw)
    parsed["SCORE"] = parse_int(parsed.get("SCORE", "0"))
    log.info(f"Score: {parsed['SCORE']} | Tier: {parsed.get('TIER')} | Category: {parsed.get('CATEGORY')}")
    return parsed, cost


def generate_content(listing: dict, score_data: dict) -> tuple[dict | None, float]:
    addr    = listing.get("address", {})
    details = listing.get("details", {})
    listing_data = (
        f"ADDRESS: {addr.get('formattedStreetLine', '')}\n"
        f"CITY: {addr.get('city', '')}\n"
        f"STATE: {addr.get('stateFull', addr.get('state', ''))}\n"
        f"PRICE: ${make_price_display(parse_int(listing.get('listPrice', 0)))}\n"
        f"BEDS: {parse_int(details.get('numBedrooms'))} | "
        f"BATHS: {parse_int(details.get('numBathrooms'))} | "
        f"SQFT: {parse_int(details.get('sqft'))} | "
        f"YEAR BUILT: {parse_int(details.get('yearBuilt'))}\n"
        f"EDITORIAL CATEGORY: {score_data.get('CATEGORY', '')}\n"
        f"KEY HOOKS: {score_data.get('KEY_HOOKS', '')}\n\n"
        f"AGENT DESCRIPTION — extract facts only, do not replicate tone or style:\n"
        f"{details.get('description', '') or '(no description)'}"
    )
    raw, cost = call_claude(CONTENT_PROMPT_TEMPLATE, listing_data, "content_gen", max_tokens=CLAUDE_MAX_TOKENS_CONTENT)
    if not raw:
        return None, cost
    return parse_content_output(raw), cost

# ---------------------------------------------------------------------------
# Cloudflare Images (mirrors ingest.py)
# ---------------------------------------------------------------------------

def upload_image(image_url: str, slug: str) -> tuple[str | None, str | None]:
    if "imagedelivery.net" in image_url:
        parts = image_url.rstrip("/").split("/")
        image_id = parts[-2] if len(parts) >= 3 else None
        return image_url, image_id
    if not image_url.startswith("http"):
        image_url = f"https://cdn.repliers.io/{image_url}"
    try:
        img_r = requests.get(image_url, timeout=30)
        img_r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Image fetch failed: {e}")
        return None, None
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
    delivery_url = variants[0] if variants else (f"{CF_DELIVERY_BASE}/{image_id}/public" if image_id else None)
    log.info(f"Cloudflare upload OK: {delivery_url}")
    return delivery_url, image_id


def upload_gallery_images(images: list[str], slug: str, city: str, state_full: str) -> tuple[list[dict], list[str]]:
    gallery_field_data = []
    gallery_image_ids = []
    for i, photo_url in enumerate(images[1:GALLERY_PHOTO_COUNT + 1]):
        delivery_url, image_id = upload_image(photo_url, f"{slug}-gallery-{i + 1}")
        if delivery_url and image_id:
            alt = make_image_alt(city, state_full, i + 1, slug)
            gallery_field_data.append({"url": delivery_url, "alt": alt})
            gallery_image_ids.append(image_id)
    log.info(f"Gallery: {len(gallery_field_data)} photos uploaded")
    return gallery_field_data, gallery_image_ids

# ---------------------------------------------------------------------------
# Webflow CMS (mirrors ingest.py)
# ---------------------------------------------------------------------------

def write_webflow(
    listing: dict, score_data: dict, content: dict,
    hero_image_url: str, is_hero: bool,
    gallery_field_data: list[dict] | None = None,
) -> str | None:
    addr       = listing.get("address", {})
    details    = listing.get("details", {})
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
    headline   = content.get("HEADLINE", "")
    name       = headline if headline else f"{city}, {state_full} — ${make_price_display(price)}"
    hero_alt   = make_image_alt(city, state_full, 0, slug)

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
    try:
        r = requests.post(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items",
            headers=headers,
            json={"fieldData": field_data},
            timeout=30,
        )
        r.raise_for_status()
        item_id = r.json().get("id")
        log.info(f"Webflow item created: {item_id}")
        return item_id
    except requests.RequestException as e:
        log.error(f"Webflow write failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            log.error(f"Webflow response: {e.response.text[:500]}")
        return None


def publish_webflow_item(item_id: str) -> bool:
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
        log.info(f"Webflow item published: {item_id}")
        return True
    except requests.RequestException as e:
        log.error(f"Webflow publish failed: {e}")
        return False


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
        log.info("Site published to housesunder150k.com")
        return True
    except requests.RequestException as e:
        log.error(f"Site publish failed: {e}")
        return False


def unset_previous_deal_of_day(prior: dict) -> bool:
    """Clear is_deal_of_day from outgoing holder in Webflow and Supabase."""
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
        log.info(f"Cleared deal-of-the-day in Webflow: {item_id}")
    except requests.RequestException as e:
        log.error(f"Failed to clear previous deal-of-the-day ({item_id}): {e}")
        return False

    # Clear in Supabase
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"slug": f"eq.{slug}"}
    try:
        rr = requests.patch(url, headers=_sb_headers(), params=params,
                            json={"is_deal_of_day": False}, timeout=10)
        rr.raise_for_status()
    except Exception as e:
        log.error(f"Supabase unset_deal_of_day error ({slug}): {e}")

    return publish_webflow_item(item_id)

# ---------------------------------------------------------------------------
# Deal of Day date assignment logic
# ---------------------------------------------------------------------------

def resolve_deal_of_day_date(request: dict) -> tuple[bool, date]:
    """
    Returns (is_deal_of_day, publish_date_ct).

    Rules:
    - If is_deal_of_day = false: no deal slot, publish today.
    - If deal_of_day_date is set: use that date if no DoD exists for it,
      else abort with error (caller should mark_request_failed).
    - If deal_of_day_date is null:
        - Today has no DoD → use today.
        - Today already has DoD → auto-forward to tomorrow.
    """
    is_dod = request.get("is_deal_of_day", False)
    today  = get_today_ct()

    if not is_dod:
        return False, today

    explicit_date_raw = request.get("deal_of_day_date")
    if explicit_date_raw:
        explicit_date = date.fromisoformat(explicit_date_raw)
        if deal_of_day_exists_for_date(explicit_date):
            raise ValueError(
                f"Deal of Day already exists for {explicit_date.isoformat()}. "
                "Choose a different date or leave date blank for auto-assignment."
            )
        log.info(f"Deal of Day: using explicit date {explicit_date.isoformat()}")
        return True, explicit_date

    # Auto-assign
    if not deal_of_day_exists_for_date(today):
        log.info(f"Deal of Day: auto-assigned to today ({today.isoformat()})")
        return True, today
    else:
        tomorrow = get_tomorrow_ct()
        log.info(
            f"Deal of Day: today already taken — auto-forwarding to tomorrow "
            f"({tomorrow.isoformat()})"
        )
        return True, tomorrow

# ---------------------------------------------------------------------------
# Process a single request
# ---------------------------------------------------------------------------

def process_request(request: dict, dry_run: bool = False) -> None:
    request_id   = request["id"]
    address      = request["address"]
    post_fb      = request.get("post_facebook", False)
    post_ig      = request.get("post_instagram", False)

    log.info(f"=== Processing request #{request_id}: '{address}' ===")
    log.info(f"  is_deal_of_day={request.get('is_deal_of_day')} post_facebook={post_fb} post_instagram={post_ig}")

    # Resolve deal of day date before any expensive operations
    try:
        is_dod, publish_date_ct = resolve_deal_of_day_date(request)
    except ValueError as e:
        log.error(f"Request #{request_id} date conflict: {e}")
        if not dry_run:
            mark_request_failed(request_id, str(e))
        return

    # Fetch from RealtyAPI
    raw_data = fetch_by_address(address)
    if not raw_data:
        error = f"RealtyAPI returned no data for address: {address}"
        log.error(error)
        if not dry_run:
            mark_request_failed(request_id, error)
        return

    listing = normalize_address_response(raw_data, address)
    if not listing:
        error = f"Could not normalize RealtyAPI response for: {address}"
        log.error(error)
        if not dry_run:
            mark_request_failed(request_id, error)
        return

    addr       = listing.get("address", {})
    city       = addr.get("city", "")
    state_abbr = addr.get("state", "")
    state_full = addr.get("stateFull", state_abbr)
    price      = parse_int(listing.get("listPrice", 0))
    address_key = listing.get("mlsNumber", "")
    slug       = make_slug(addr.get("formattedStreetLine", ""), city, state_abbr)

    log.info(f"  Resolved: {city}, {state_full} | ${make_price_display(price)} | slug={slug}")

    # Score
    score_data, _ = score_listing(listing)
    if not score_data:
        error = "Scoring failed — no response from Claude"
        log.error(error)
        if not dry_run:
            mark_request_failed(request_id, error)
        return

    score = score_data.get("SCORE", 0)
    tier  = score_data.get("TIER", "SKIP")
    log.info(f"  Score: {score} | Tier: {tier} | Category: {score_data.get('CATEGORY')}")

    # Manual injection bypasses score threshold — operator decision overrides
    # But we warn if the score is very low so operator knows what they're doing
    if score <= 3:
        log.warning(
            f"  Score {score} is very low (SKIP tier). Publishing anyway per manual override. "
            "Review the listing before approving for FB/IG."
        )

    # Generate content
    content, _ = generate_content(listing, score_data)
    if not content or not content.get("HEADLINE") or not content.get("NARRATIVE"):
        error = "Content generation failed or returned empty fields"
        log.error(error)
        if not dry_run:
            mark_request_failed(request_id, error)
        return

    print("\n" + "=" * 60)
    print(f"REQUEST #{request_id}: {address}")
    print(f"SLUG: {slug}")
    print(f"SCORE: {score} | TIER: {tier} | CATEGORY: {score_data.get('CATEGORY')}")
    print(f"DEAL OF DAY: {is_dod} | PUBLISH DATE: {publish_date_ct.isoformat()}")
    print(f"APPROVE FB: {post_fb} | APPROVE IG: {post_ig}")
    print(f"\nHEADLINE: {content.get('HEADLINE', '')}")
    print(f"\nNARRATIVE:\n{content.get('NARRATIVE', '')}")
    print(f"\nSOCIAL CAPTION: {content.get('SOCIAL_CAPTION', '')}")
    print("=" * 60 + "\n")

    if dry_run:
        log.info(f"=== DRY RUN — request #{request_id} not written to Webflow or Supabase ===")
        return

    # Upload images
    images = listing.get("images", [])
    hero_image_url, _ = upload_image(images[0], slug) if images else (None, None)
    if not hero_image_url:
        log.warning(f"  No hero image for {slug}")
        hero_image_url = ""

    gallery_field_data, gallery_image_ids = (
        upload_gallery_images(images, slug, city, state_full) if len(images) > 1 else ([], [])
    )

    # If this is Deal of Day, clear the previous holder for today
    if is_dod and publish_date_ct == get_today_ct():
        prior = get_active_deal_of_day()
        if prior and prior.get("webflow_item_id"):
            unset_previous_deal_of_day(prior)

    # Write to Webflow
    item_id = write_webflow(listing, score_data, content, hero_image_url, is_dod, gallery_field_data)
    if not item_id:
        error = "Webflow write failed"
        log.error(error)
        mark_request_failed(request_id, error)
        return

    if not publish_webflow_item(item_id):
        error = "Webflow publish failed"
        log.error(error)
        mark_request_failed(request_id, error)
        return

    # Insert into Supabase (sets fb/ig approval flags directly)
    insert_published_listing(
        slug=slug,
        address_key=address_key,
        webflow_item_id=item_id,
        score=score,
        tier=tier,
        category=score_data.get("CATEGORY", ""),
        headline=content.get("HEADLINE", ""),
        hero_image_url=hero_image_url,
        publish_date_ct=publish_date_ct,
        price=price,
        is_deal_of_day=is_dod,
        gallery_image_ids=gallery_image_ids,
        short_summary=content.get("SHORT_SUMMARY") or None,
        social_caption=content.get("SOCIAL_CAPTION") or None,
        city=city or None,
        state=state_abbr or None,
        post_facebook=post_fb,
        post_instagram=post_ig,
    )

    # Publish site (triggers CDN rebuild)
    publish_site()

    mark_request_done(request_id, slug)

    log.info(
        f"=== Request #{request_id} complete | slug={slug} | "
        f"score={score} | is_dod={is_dod} | publish_date={publish_date_ct} | "
        f"fb={post_fb} | ig={post_ig} ==="
    )

# ---------------------------------------------------------------------------
# Main poller
# ---------------------------------------------------------------------------

def run(dry_run: bool = False):
    log.info("=== HousesUnder150K Manual Ingest Poller Start ===")
    if dry_run:
        log.info("*** DRY RUN — nothing will be written ***")

    requests_list = fetch_pending_requests()

    if not requests_list:
        log.info("No pending requests — exiting")
        return

    published_count = 0
    for request in requests_list:
        request_id = request["id"]
        try:
            if not dry_run:
                mark_request_processing(request_id)
            process_request(request, dry_run=dry_run)
            published_count += 1
        except Exception as e:
            log.error(f"Unhandled error on request #{request_id}: {e}", exc_info=True)
            if not dry_run:
                mark_request_failed(request_id, str(e)[:500])

        time.sleep(2)  # brief pause between requests

    log.info(f"=== Manual Ingest Poller complete | processed={published_count}/{len(requests_list)} ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HousesUnder150K Manual Listing Ingest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and score listing but do NOT write to Webflow, Supabase, or Cloudflare.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
