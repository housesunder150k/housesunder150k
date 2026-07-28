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
  - request error / "Home not found" -> Expired, UNLESS an address-based
    lookup resolves the listing under a different property_id (see below)
  - otherwise                        -> Active (no change)

KNOWN FAILURE MODE — property_id drift (confirmed 2026-07-28 on a real listing):
RealtyAPI/Realtor.com can reissue a new property_id for the same physical
listing on a data refresh, even though nothing about the listing changed. The
id stored at ingestion time then returns "Home not found" forever, which would
wrongly mark a live listing Expired. Before concluding Expired, this script
falls back to a /details/byaddress lookup using the address stored in Webflow.
If that resolves, the listing's true current status is used AND the stored
mls_number is refreshed to the new property_id so this doesn't recur weekly
for the same listing. Only if the address lookup also fails to find anything
is the listing actually marked Expired.
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


def db_update_listing_status(
    slug: str, new_status: str, checked_at: str, new_mls_number: str | None = None
) -> None:
    """Always called after a check, whether or not status changed —
    advances last_status_checked_at so the rotating queue moves forward.
    If the property_id had drifted (see module docstring), new_mls_number
    refreshes the stored id so this listing doesn't hit the fallback again."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"slug": f"eq.{slug}"}
    payload = {"status": new_status, "last_status_checked_at": checked_at}
    if new_mls_number:
        payload["mls_number"] = new_mls_number
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


def _detail_to_status(detail: dict) -> str:
    """Maps a resolved `detail` dict to Active/Pending/Sold. See module
    docstring for the confirmed field mapping."""
    if (detail.get("flags") or {}).get("is_pending"):
        return "Pending"
    if detail.get("status") == "sold":
        return "Sold"
    return "Active"


def check_listing_status(property_id: str, webflow_item_id: str) -> tuple[str, str | None]:
    """Returns (status, refreshed_property_id) — refreshed_property_id is
    only set when the stored id had drifted (see KNOWN FAILURE MODE above)
    and the address fallback found the listing under a new one; the caller
    persists it to Supabase so this listing doesn't hit the fallback again.
    On any request failure, returns ("Active", None) — i.e. "couldn't verify,
    leave it alone, try again next rotation" rather than risk a false Expired."""
    try:
        r = requests.get(
            f"{REALTYAPI_REALTOR_BASE}/details/byid",
            headers=_ra_headers(),
            params={"property_id": property_id},
            timeout=30,
        )
        detail = r.json().get("detail") if r.status_code == 200 else None

        if detail:
            return _detail_to_status(detail), None

        # property_id didn't resolve — before concluding Expired, look the
        # listing up by address in case RealtyAPI just reissued a new id for it.
        log.info(f"[{property_id}] not found by id — trying address fallback")
        wf = requests.get(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/{webflow_item_id}",
            headers=_wf_headers(),
            timeout=30,
        )
        field_data = wf.json().get("fieldData", {}) if wf.status_code == 200 else {}
        address = field_data.get("address", "")
        city = field_data.get("city", "")
        state = field_data.get("state", "")

        if address and city:
            r = requests.get(
                f"{REALTYAPI_REALTOR_BASE}/details/byaddress",
                headers=_ra_headers(),
                params={"address": f"{address}, {city}, {state}"},
                timeout=30,
            )
            detail = r.json().get("detail") if r.status_code == 200 else None
            if detail:
                new_property_id = detail.get("property_id")
                log.info(f"[{property_id}] resolved via address — id drifted to {new_property_id}")
                return _detail_to_status(detail), new_property_id

        log.info(f"[{property_id}] not found by id or address — treating as Expired")
        return "Expired", None

    except requests.RequestException as e:
        log.warning(f"[{property_id}] status check failed ({e}) — leaving unchanged, will retry next rotation")
        return "Active", None


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

        new_status, refreshed_property_id = check_listing_status(property_id, webflow_item_id)
        time.sleep(REQUEST_SLEEP_SECS)

        # Always advance last_status_checked_at, regardless of outcome —
        # keeps the rotating queue moving forward. Also persist a refreshed
        # property_id if the address fallback found one (see module docstring).
        db_update_listing_status(slug, new_status, checked_at, refreshed_property_id)

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
