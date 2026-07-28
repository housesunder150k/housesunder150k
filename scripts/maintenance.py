"""
HousesUnder150K.com — Maintenance Job: Listing Status Sweep
Runs on Railway 1x/week (separate service from ingest.py — see build_status.md).
Rechecks Active listings against RealtyAPI for sold/pending/delisted status,
mirrors the result in Supabase, and pushes only the changed items to Webflow.

Listings are NEVER unpublished or deleted — status transitions only update the
`status` field and (via the Webflow template) show a Sold/Pending banner.

Status mapping — confirmed 2026-07-27 against live RealtyAPI responses:
  - detail.flags.is_pending == true  -> Pending  (detail.status stays "for_sale"
    even when pending — it does NOT flip to "pending". is_pending is the only
    reliable signal.)
  - detail.status == "sold"          -> Sold
  - request error / "Home not found" -> Expired (delisted, no clear signal)
  - otherwise                        -> Active (no change)
"""

import os
import time
import logging
from datetime import datetime, timezone

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

REALTYAPI_KEY                       = os.environ["REALTYAPI_KEY"]
WEBFLOW_API_TOKEN                   = os.environ["WEBFLOW_API_TOKEN"]
WEBFLOW_COLLECTION_ID               = os.environ["WEBFLOW_COLLECTION_ID"]
SUPABASE_URL                        = os.environ["SUPABASE_URL"]
SUPABASE_KEY                        = os.environ["SUPABASE_KEY"]
REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT = int(os.environ.get("REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT", "500"))

REALTYAPI_REALTOR_BASE = "https://realtor.realtyapi.io"
WEBFLOW_BASE            = "https://api.webflow.com/v2"
WEBFLOW_SITE_ID         = "6a650a7eb2639262c4b6adb7"
WEBFLOW_DOMAIN_IDS      = ["6a661987994ab168be06566b", "6a661986994ab168be065664"]

# Webflow Listings collection — Status option field (slug: "status")
# IDs verified live against Webflow on 2026-07-27 — do not assume, re-verify
# if this script ever errors on a PATCH.
WF_STATUS_OPTION_IDS = {
    "Active":  "3b41185e9af84f92d8da092965308a2d",
    "Pending": "001257c77d3ccd4477d620ac135a4afd",
    "Sold":    "541de6b6934cd79d6a76c98d91610063",
    "Expired": "e630110b6993074e3f7299e8dbb7fdc1",
}

REQUEST_SLEEP_SECS = 0.2  # be polite to RealtyAPI between calls


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


def db_fetch_status_check_queue(limit: int) -> list[dict]:
    """Active listings, oldest-checked-first (nulls first), up to `limit`.
    This is a rotating queue, not a full sweep — every active listing
    eventually gets rechecked, just not all in the same week once the
    active pool exceeds the weekly limit."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug,mls_number,webflow_item_id,status,last_status_checked_at",
        "status": "eq.Active",
        "order": "last_status_checked_at.asc.nullsfirst",
        "limit": limit,
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Supabase fetch_status_check_queue error: {e}")
        return []


def db_update_listing_status(slug: str, new_status: str, checked_at: str) -> None:
    """Always called after a check, whether or not status changed —
    advances last_status_checked_at so the rotating queue moves forward."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"slug": f"eq.{slug}"}
    payload = {"status": new_status, "last_status_checked_at": checked_at}
    try:
        r = requests.patch(url, headers=_sb_headers(), params=params, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase update_listing_status error ({slug}): {e}")


# ---------------------------------------------------------------------------
# RealtyAPI
# ---------------------------------------------------------------------------

def _ra_headers() -> dict:
    return {"x-realtyapi-key": REALTYAPI_KEY}


def check_listing_status(property_id: str) -> str:
    """Returns one of: Active, Pending, Sold, Expired.
    See module docstring for the confirmed field mapping."""
    try:
        r = requests.get(
            f"{REALTYAPI_REALTOR_BASE}/details/byid",
            headers=_ra_headers(),
            params={"property_id": property_id},
            timeout=30,
        )
        if r.status_code != 200:
            log.info(f"[{property_id}] non-200 ({r.status_code}) — treating as Expired")
            return "Expired"
        data = r.json()
    except requests.RequestException as e:
        log.warning(f"[{property_id}] request failed ({e}) — treating as Expired")
        return "Expired"

    detail = data.get("detail")
    if not detail:
        # e.g. {"message": "500: Home not found.", "detail": {}}
        log.info(f"[{property_id}] no detail in response ({data.get('message')}) — treating as Expired")
        return "Expired"

    if (detail.get("flags") or {}).get("is_pending"):
        return "Pending"
    if detail.get("status") == "sold":
        return "Sold"
    return "Active"


# ---------------------------------------------------------------------------
# Webflow
# ---------------------------------------------------------------------------

def _wf_headers() -> dict:
    return {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }


def patch_webflow_status(item_id: str, new_status: str) -> bool:
    """Update the item's status field only. Listing stays live — never
    unpublished or deleted, per the non-negotiable product requirement."""
    option_id = WF_STATUS_OPTION_IDS[new_status]
    try:
        r = requests.patch(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/{item_id}",
            headers=_wf_headers(),
            json={"fieldData": {"status": option_id}},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Webflow status PATCH failed ({item_id}): {e}")
        return False
    return True


def publish_webflow_items(item_ids: list[str]) -> bool:
    if not item_ids:
        return True
    try:
        r = requests.post(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/publish",
            headers=_wf_headers(),
            json={"itemIds": item_ids},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Webflow item publish failed: {e}")
        return False
    log.info(f"Published {len(item_ids)} changed item(s) to staging")
    return True


def publish_site() -> bool:
    """One full site publish at the end of the run if anything changed —
    same pattern ingest.py uses. Never publish per-listing."""
    try:
        r = requests.post(
            f"{WEBFLOW_BASE}/sites/{WEBFLOW_SITE_ID}/publish",
            headers=_wf_headers(),
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
# Main
# ---------------------------------------------------------------------------

def run_maintenance():
    log.info("=== HousesUnder150K Maintenance — Status Sweep Start ===")
    start = time.time()

    queue = db_fetch_status_check_queue(REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT)
    log.info(f"Checking {len(queue)} Active listing(s) (weekly cap: {REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT})")

    if not queue:
        log.info("Nothing to check — exiting")
        return

    changed_item_ids = []
    counts = {"unchanged": 0, "changed": 0, "errors": 0}

    for row in queue:
        slug = row.get("slug")
        property_id = row.get("mls_number")  # mls_number stores Realtor.com property_id
        webflow_item_id = row.get("webflow_item_id")
        checked_at = datetime.now(timezone.utc).isoformat()

        if not property_id or not webflow_item_id:
            log.warning(f"[{slug}] missing property_id or webflow_item_id — skipping")
            counts["errors"] += 1
            continue

        new_status = check_listing_status(property_id)
        time.sleep(REQUEST_SLEEP_SECS)

        # Always advance last_status_checked_at, regardless of outcome —
        # keeps the rotating queue moving forward.
        db_update_listing_status(slug, new_status, checked_at)

        if new_status == "Active":
            counts["unchanged"] += 1
            continue

        log.info(f"[{slug}] status change: Active -> {new_status}")
        if patch_webflow_status(webflow_item_id, new_status):
            changed_item_ids.append(webflow_item_id)
            counts["changed"] += 1
        else:
            counts["errors"] += 1

    if changed_item_ids:
        publish_webflow_items(changed_item_ids)
        publish_site()

    elapsed = time.time() - start
    log.info(
        f"=== Maintenance complete in {elapsed:.1f}s | "
        f"checked={len(queue)} changed={counts['changed']} "
        f"unchanged={counts['unchanged']} errors={counts['errors']} ==="
    )


if __name__ == "__main__":
    run_maintenance()
