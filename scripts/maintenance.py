"""
HousesUnder150K.com — Maintenance Job: Listing Status Sweep
Runs on Railway biweekly (Wednesday + Saturday, 10:00 UTC — separate service from ingest.py).
Rechecks Active listings against RealtyAPI for sold/pending/delisted status,
mirrors the result in Supabase, pushes only changed items to Webflow,
and deletes gallery images from Cloudflare on status change.

Listings are NEVER unpublished or deleted — status transitions only update the
`status` field and (via the Webflow template) show a Sold/Pending banner.

Status mapping — confirmed 2026-07-28 against live RealtyAPI responses:
  - detail.flags.is_pending == true  -> Pending  (detail.status stays "for_sale"
    even when pending — it does NOT flip to "pending". is_pending is the only
    reliable signal.)
  - detail.status == "sold"          -> Sold
  - request error / "Home not found" -> Expired, UNLESS an address-based
    lookup resolves the listing under a different property_id (see below)
  - otherwise                        -> Active (no change)

KNOWN FAILURE MODE — property_id drift (confirmed 2026-07-28 on a real listing):
RealtyAPI/Realtor.com can reissue a new property_id for the same physical
listing on a data refresh. The id stored at ingestion time then returns
"Home not found" forever, wrongly marking a live listing Expired. Before
concluding Expired, this script falls back to a /details/byaddress lookup
using the address stored in Webflow. If that resolves, the listing's true
current status is used AND the stored mls_number is refreshed to the new
property_id so this doesn't recur weekly for the same listing. Only if the
address lookup also fails is the listing actually marked Expired.

CLOUDFLARE CLEANUP (added 2026-07-28):
When a listing transitions to Pending/Sold/Expired, gallery images uploaded
to Cloudflare are deleted to avoid storage costs on listings no longer in
active use. The Cloudflare image IDs are stored in published_listings.gallery_image_ids
at ingestion time. After successful deletion, gallery_image_ids is set to NULL.
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
CLOUDFLARE_API_TOKEN                = os.environ["CLOUDFLARE_API_TOKEN"]
CLOUDFLARE_ACCOUNT_ID               = os.environ["CLOUDFLARE_ACCOUNT_ID"]
REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT = int(os.environ.get("REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT", "500"))

REALTYAPI_REALTOR_BASE = "https://realtor.realtyapi.io"
WEBFLOW_BASE            = "https://api.webflow.com/v2"
WEBFLOW_SITE_ID         = "6a650a7eb2639262c4b6adb7"
WEBFLOW_DOMAIN_IDS      = ["6a661987994ab168be06566b", "6a661986994ab168be065664"]
CF_IMAGES_BASE          = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1"

WF_STATUS_OPTION_IDS = {
    "Active":  "3b41185e9af84f92d8da092965308a2d",
    "Pending": "001257c77d3ccd4477d620ac135a4afd",
    "Sold":    "541de6b6934cd79d6a76c98d91610063",
    "Expired": "e630110b6993074e3f7299e8dbb7fdc1",
}

REQUEST_SLEEP_SECS = 0.2


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
    """Active listings, oldest-checked-first (nulls first), up to `limit`."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug,mls_number,webflow_item_id,status,last_status_checked_at,gallery_image_ids",
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
    slug: str, new_status: str, checked_at: str,
    new_mls_number: str | None = None,
    clear_gallery_ids: bool = False,
) -> None:
    """Update status and advance last_status_checked_at. Optionally refresh
    mls_number on property_id drift, and clear gallery_image_ids after deletion."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"slug": f"eq.{slug}"}
    payload = {"status": new_status, "last_status_checked_at": checked_at}
    if new_mls_number:
        payload["mls_number"] = new_mls_number
    if clear_gallery_ids:
        payload["gallery_image_ids"] = None
    try:
        r = requests.patch(url, headers=_sb_headers(), params=params, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase update_listing_status error ({slug}): {e}")


# ---------------------------------------------------------------------------
# Cloudflare Images cleanup
# ---------------------------------------------------------------------------

def delete_cloudflare_images(image_ids: list[str], slug: str) -> bool:
    """Delete gallery images from Cloudflare when a listing goes inactive.
    Non-blocking — logs failures but does not halt the maintenance run.
    Returns True if all deletions succeeded."""
    if not image_ids:
        return True

    all_ok = True
    for image_id in image_ids:
        try:
            r = requests.delete(
                f"{CF_IMAGES_BASE}/{image_id}",
                headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
                timeout=15,
            )
            if r.status_code == 200:
                log.info(f"[{slug}] Cloudflare image deleted: {image_id}")
            elif r.status_code == 404:
                log.warning(f"[{slug}] Cloudflare image not found (already deleted?): {image_id}")
            else:
                log.error(f"[{slug}] Cloudflare delete failed ({r.status_code}): {image_id}")
                all_ok = False
        except requests.RequestException as e:
            log.error(f"[{slug}] Cloudflare delete error ({image_id}): {e}")
            all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# RealtyAPI
# ---------------------------------------------------------------------------

def _ra_headers() -> dict:
    return {"x-realtyapi-key": REALTYAPI_KEY}


def _detail_to_status(detail: dict) -> str:
    if (detail.get("flags") or {}).get("is_pending"):
        return "Pending"
    if detail.get("status") == "sold":
        return "Sold"
    return "Active"


def check_listing_status(property_id: str, webflow_item_id: str) -> tuple[str, str | None]:
    """Returns (status, refreshed_property_id).
    On any request failure, returns ("Active", None) — leave unchanged, retry next rotation."""
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

        # property_id didn't resolve — try address fallback before concluding Expired
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
        log.warning(f"[{property_id}] status check failed ({e}) — leaving unchanged")
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
    log.info(f"Checking {len(queue)} Active listing(s) (cap: {REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT})")

    if not queue:
        log.info("Nothing to check — exiting")
        return

    changed_item_ids = []
    counts = {"unchanged": 0, "changed": 0, "errors": 0, "images_deleted": 0}

    for row in queue:
        slug = row.get("slug")
        property_id = row.get("mls_number")
        webflow_item_id = row.get("webflow_item_id")
        gallery_image_ids = row.get("gallery_image_ids") or []
        checked_at = datetime.now(timezone.utc).isoformat()

        if not property_id or not webflow_item_id:
            log.warning(f"[{slug}] missing property_id or webflow_item_id — skipping")
            counts["errors"] += 1
            continue

        new_status, refreshed_property_id = check_listing_status(property_id, webflow_item_id)
        time.sleep(REQUEST_SLEEP_SECS)

        if new_status == "Active":
            # Advance the queue regardless — no Cloudflare work needed
            db_update_listing_status(slug, "Active", checked_at, refreshed_property_id)
            counts["unchanged"] += 1
            continue

        log.info(f"[{slug}] status change: Active -> {new_status}")

        # Update Webflow status field
        if not patch_webflow_status(webflow_item_id, new_status):
            counts["errors"] += 1
            # Still advance the checked_at so the queue moves forward
            db_update_listing_status(slug, "Active", checked_at, refreshed_property_id)
            continue

        changed_item_ids.append(webflow_item_id)

        # Delete gallery images from Cloudflare — only on status change
        clear_gallery = False
        if gallery_image_ids:
            log.info(f"[{slug}] Deleting {len(gallery_image_ids)} gallery image(s) from Cloudflare")
            deletion_ok = delete_cloudflare_images(gallery_image_ids, slug)
            if deletion_ok:
                clear_gallery = True
                counts["images_deleted"] += len(gallery_image_ids)
            else:
                log.warning(f"[{slug}] Some gallery deletions failed — gallery_image_ids NOT cleared in Supabase")

        # Update Supabase: new status + advance queue + optionally clear gallery ids
        db_update_listing_status(
            slug, new_status, checked_at,
            new_mls_number=refreshed_property_id,
            clear_gallery_ids=clear_gallery,
        )
        counts["changed"] += 1

    if changed_item_ids:
        publish_webflow_items(changed_item_ids)
        publish_site()

    elapsed = time.time() - start
    log.info(
        f"=== Maintenance complete in {elapsed:.1f}s | "
        f"checked={len(queue)} changed={counts['changed']} "
        f"unchanged={counts['unchanged']} errors={counts['errors']} "
        f"images_deleted={counts['images_deleted']} ==="
    )


if __name__ == "__main__":
    run_maintenance()
