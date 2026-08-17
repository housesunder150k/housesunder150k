"""
HousesUnder150K.com — Maintenance Job: Listing Status Sweep
Runs on Railway biweekly (Wednesday + Saturday, 10:00 UTC — separate service from ingest.py).
Rechecks Active AND Pending listings against RealtyAPI for sold/pending/delisted status,
mirrors the result in Supabase, pushes only changed items to Webflow,
and deletes gallery images from Cloudflare on status change.

Listings are NEVER unpublished or deleted — status transitions only update the
`status` field and (via the Webflow template) show a Sold/Pending banner.

Status lookup strategy (2026-07-28):
  Address-based lookup is now the primary path. RealtyAPI/Realtor.com can
  reissue new property_ids on data refreshes (confirmed in production), making
  id-based lookups unreliable. The mls_number column in published_listings now
  stores a stable address key ("{street}|{city}|{state}") for new listings.
  Existing listings still have property_ids in mls_number — the maintenance job
  always looks up by address from Webflow field data, so this is handled
  transparently regardless of what's in mls_number.

Status mapping — confirmed 2026-07-28 against live RealtyAPI responses:
  - detail.flags.is_pending == true  -> Pending
  - detail.status == "sold"          -> Sold
  - address lookup fails entirely    -> Expired
  - otherwise                        -> Active (no change)

Sold price tracking (added 2026-08-17):
  When a listing transitions to Sold, last_sold_price and last_sold_date are
  captured from the RealtyAPI detail response and stored in Supabase. These
  fields may be null immediately after sale and populated on a later run.
  status_marked_sold_at records when we first set status=Sold, used as the
  clock for the 45-day give-up threshold.

  Pending listings remain in the check queue — they continue to be rechecked
  each run until they transition to Sold or Expired. Sold is the terminal state.

  A separate pass each run finds Sold listings where sold_price is known but
  has not yet been published to Webflow (sold_price_published = false). It
  appends a bold snippet to the narrative-body rich text field:
    "Originally listed for $X and Sold for $Y on [date]."
  On success, sold_price_published is set to true in Supabase.

  If no sold price is available within SOLD_PRICE_GIVE_UP_DAYS of
  status_marked_sold_at, sold_price_published is set to true to stop retrying.

CLOUDFLARE CLEANUP (added 2026-07-28):
When a listing transitions to Pending/Sold/Expired, gallery images uploaded
to Cloudflare are deleted to avoid storage costs. The Cloudflare image IDs
are stored in published_listings.gallery_image_ids at ingestion time.
After successful deletion, gallery_image_ids is set to NULL in Supabase.
Hero image is never deleted — it must remain for the listing page to render.
"""

import os
import time
import logging
from datetime import datetime, timezone, timedelta

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

# Days after status_marked_sold_at to stop retrying sold price lookup
SOLD_PRICE_GIVE_UP_DAYS = 45

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
    """Active and Pending listings, oldest-checked-first (nulls first), up to `limit`.

    Pending listings remain in the queue so they continue to be rechecked
    until they transition to Sold or Expired. Sold is the terminal state —
    sold listings are never included here.
    """
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug,mls_number,webflow_item_id,status,last_status_checked_at,gallery_image_ids",
        "status": "in.(Active,Pending)",
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


def db_fetch_sold_price_publish_queue() -> list[dict]:
    """Sold listings where sold_price is known but not yet published to Webflow.

    Also returns listings past the give-up threshold so the caller can mark
    them done without publishing (sold_price will be null for those).
    """
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug,webflow_item_id,price,sold_price,sold_date,status_marked_sold_at",
        "status": "eq.Sold",
        "sold_price_published": "eq.false",
        "order": "status_marked_sold_at.asc.nullsfirst",
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Supabase fetch_sold_price_publish_queue error: {e}")
        return []


def db_update_listing_status(
    slug: str,
    new_status: str,
    checked_at: str,
    clear_gallery_ids: bool = False,
    sold_price: int | None = None,
    sold_date: str | None = None,
    mark_sold_at: str | None = None,
) -> None:
    """Update status and advance last_status_checked_at.

    Optionally:
    - Clear gallery_image_ids after successful Cloudflare deletion.
    - Store sold_price and sold_date when status flips to Sold.
    - Set status_marked_sold_at when first marking Sold (caller passes now()).
    """
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"slug": f"eq.{slug}"}
    payload: dict = {"status": new_status, "last_status_checked_at": checked_at}
    if clear_gallery_ids:
        payload["gallery_image_ids"] = None
    if sold_price is not None:
        payload["sold_price"] = sold_price
    if sold_date is not None:
        payload["sold_date"] = sold_date
    if mark_sold_at is not None:
        payload["status_marked_sold_at"] = mark_sold_at
    try:
        r = requests.patch(url, headers=_sb_headers(), params=params, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase update_listing_status error ({slug}): {e}")


def db_mark_sold_price_published(slug: str) -> None:
    """Set sold_price_published = true — either we wrote the snippet or gave up."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"slug": f"eq.{slug}"}
    try:
        r = requests.patch(
            url, headers=_sb_headers(), params=params,
            json={"sold_price_published": True}, timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase mark_sold_price_published error ({slug}): {e}")


def db_update_sold_price(slug: str, sold_price: int, sold_date: str) -> None:
    """Store sold price/date discovered on a re-check of an already-Sold listing."""
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {"slug": f"eq.{slug}"}
    try:
        r = requests.patch(
            url, headers=_sb_headers(), params=params,
            json={"sold_price": sold_price, "sold_date": sold_date}, timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        log.error(f"Supabase update_sold_price error ({slug}): {e}")


# ---------------------------------------------------------------------------
# Cloudflare Images cleanup
# ---------------------------------------------------------------------------

def delete_cloudflare_images(image_ids: list[str], slug: str) -> bool:
    """Delete gallery images from Cloudflare when a listing goes inactive.
    Hero image is never stored here and is never touched.
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
# RealtyAPI — address-based status lookup
# ---------------------------------------------------------------------------

def _ra_headers() -> dict:
    return {"x-realtyapi-key": REALTYAPI_KEY}


def _extract_sold_price(detail: dict) -> tuple[int | None, str | None]:
    """Extract last_sold_price and last_sold_date from a detail response.
    Returns (price, date_str) where date_str is ISO 'YYYY-MM-DD', or (None, None)."""
    price = detail.get("last_sold_price")
    date = detail.get("last_sold_date")
    if price and isinstance(price, (int, float)) and int(price) > 0:
        return int(price), (str(date) if date else None)
    return None, None


def _detail_to_status(detail: dict) -> str:
    if (detail.get("flags") or {}).get("is_pending"):
        return "Pending"
    if detail.get("status") == "sold":
        return "Sold"
    return "Active"


def check_listing_status(webflow_item_id: str) -> tuple[str, int | None, str | None]:
    """Look up current listing status by address from Webflow field data.

    Returns (status, sold_price, sold_date).
    - status: Active / Pending / Sold / Expired
    - sold_price: integer sale price if available, else None
    - sold_date: ISO date string if available, else None

    On any request failure returns ("Active", None, None) — leave unchanged,
    retry next rotation.
    """
    try:
        wf = requests.get(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/{webflow_item_id}",
            headers=_wf_headers(),
            timeout=30,
        )
        if wf.status_code != 200:
            log.warning(f"[{webflow_item_id}] Webflow fetch failed ({wf.status_code}) — leaving unchanged")
            return "Active", None, None

        field_data = wf.json().get("fieldData", {})
        address = field_data.get("address", "")
        city    = field_data.get("city", "")
        state   = field_data.get("state", "")

        if not address or not city:
            log.warning(f"[{webflow_item_id}] missing address fields in Webflow — leaving unchanged")
            return "Active", None, None

        r = requests.get(
            f"{REALTYAPI_REALTOR_BASE}/details/byaddress",
            headers=_ra_headers(),
            params={"address": f"{address}, {city}, {state}"},
            timeout=30,
        )
        detail = r.json().get("detail") if r.status_code == 200 else None

        if detail:
            status = _detail_to_status(detail)
            sold_price, sold_date = _extract_sold_price(detail)
            log.info(f"[{address}, {city}] -> {status}" +
                     (f" | sold_price={sold_price} sold_date={sold_date}" if status == "Sold" else ""))
            return status, sold_price, sold_date

        log.info(f"[{address}, {city}] not found by address — treating as Expired")
        return "Expired", None, None

    except requests.RequestException as e:
        log.warning(f"[{webflow_item_id}] status check failed ({e}) — leaving unchanged")
        return "Active", None, None


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


def _format_price(price: int) -> str:
    return f"${price:,}"


def _format_sold_date(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' to 'Month D, YYYY'. Falls back to raw string."""
    try:
        from datetime import date as date_cls
        d = date_cls.fromisoformat(date_str)
        return d.strftime("%B %-d, %Y")
    except Exception:
        return date_str


def patch_webflow_sold_snippet(item_id: str, slug: str, list_price: int, sold_price: int, sold_date: str) -> bool:
    """Fetch the current narrative-body, append the sold snippet as a bold paragraph, and PATCH back."""
    # Fetch current field data
    try:
        r = requests.get(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/{item_id}",
            headers=_wf_headers(),
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"[{slug}] Webflow fetch for snippet failed: {e}")
        return False

    field_data = r.json().get("fieldData", {})
    existing_body = field_data.get("narrative-body", "") or ""

    date_display  = _format_sold_date(sold_date)
    price_display = _format_price(list_price)
    sold_display  = _format_price(sold_price)
    snippet = (
        f'<p><strong>Originally listed for {price_display} and '
        f'Sold for {sold_display} on {date_display}.</strong></p>'
    )

    # Guard: don't append twice if somehow called again
    if "Originally listed for" in existing_body:
        log.info(f"[{slug}] sold snippet already present — skipping append")
        return True

    updated_body = existing_body + snippet

    try:
        r = requests.patch(
            f"{WEBFLOW_BASE}/collections/{WEBFLOW_COLLECTION_ID}/items/{item_id}",
            headers=_wf_headers(),
            json={"fieldData": {"narrative-body": updated_body}},
            timeout=30,
        )
        r.raise_for_status()
        log.info(f"[{slug}] sold snippet appended to narrative-body")
        return True
    except requests.RequestException as e:
        log.error(f"[{slug}] Webflow snippet PATCH failed: {e}")
        return False


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
    log.info(f"Published {len(item_ids)} changed item(s)")
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
# Pass 1 — Status sweep (Active + Pending)
# ---------------------------------------------------------------------------

def run_status_sweep() -> tuple[list[str], dict]:
    """Check all Active and Pending listings. Returns (changed_item_ids, counts)."""
    queue = db_fetch_status_check_queue(REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT)
    log.info(f"Status sweep: checking {len(queue)} Active/Pending listing(s) (cap: {REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT})")

    changed_item_ids: list[str] = []
    counts = {"unchanged": 0, "changed": 0, "errors": 0, "images_deleted": 0}

    for row in queue:
        slug            = row.get("slug")
        webflow_item_id = row.get("webflow_item_id")
        current_status  = row.get("status", "Active")
        gallery_ids     = row.get("gallery_image_ids") or []
        checked_at      = datetime.now(timezone.utc).isoformat()

        if not webflow_item_id:
            log.warning(f"[{slug}] missing webflow_item_id — skipping")
            counts["errors"] += 1
            continue

        new_status, sold_price, sold_date = check_listing_status(webflow_item_id)
        time.sleep(REQUEST_SLEEP_SECS)

        # No change — update timestamp and move on
        if new_status == current_status:
            db_update_listing_status(slug, current_status, checked_at)
            counts["unchanged"] += 1
            continue

        # Active -> Active is handled above; anything else is a real transition
        log.info(f"[{slug}] status change: {current_status} -> {new_status}")

        if not patch_webflow_status(webflow_item_id, new_status):
            counts["errors"] += 1
            db_update_listing_status(slug, current_status, checked_at)
            continue

        changed_item_ids.append(webflow_item_id)

        # Cloudflare cleanup on first transition away from Active
        clear_gallery = False
        if gallery_ids and current_status == "Active":
            log.info(f"[{slug}] Deleting {len(gallery_ids)} gallery image(s) from Cloudflare")
            if delete_cloudflare_images(gallery_ids, slug):
                clear_gallery = True
                counts["images_deleted"] += len(gallery_ids)
            else:
                log.warning(f"[{slug}] Some gallery deletions failed — gallery_image_ids NOT cleared")

        # Build kwargs for status update
        update_kwargs: dict = dict(
            new_status=new_status,
            checked_at=checked_at,
            clear_gallery_ids=clear_gallery,
        )

        # Capture sold price if transitioning to Sold
        if new_status == "Sold":
            update_kwargs["mark_sold_at"] = checked_at
            if sold_price:
                update_kwargs["sold_price"] = sold_price
                update_kwargs["sold_date"]  = sold_date
                log.info(f"[{slug}] sold price captured: {sold_price} on {sold_date}")
            else:
                log.info(f"[{slug}] sold price not yet available — will retry in snippet pass")

        db_update_listing_status(slug, **update_kwargs)
        counts["changed"] += 1

    return changed_item_ids, counts


# ---------------------------------------------------------------------------
# Pass 2 — Sold snippet publish
# ---------------------------------------------------------------------------

def run_sold_snippet_pass() -> list[str]:
    """For Sold listings with a known sold_price not yet published, append snippet to Webflow.
    Also handles the give-up case and re-checks for late-arriving prices.
    Returns list of item_ids that were updated (need publishing)."""

    queue = db_fetch_sold_price_publish_queue()
    log.info(f"Sold snippet pass: {len(queue)} listing(s) pending")

    snippet_item_ids: list[str] = []
    now = datetime.now(timezone.utc)
    give_up_cutoff = now - timedelta(days=SOLD_PRICE_GIVE_UP_DAYS)

    for row in queue:
        slug            = row.get("slug")
        webflow_item_id = row.get("webflow_item_id")
        list_price      = row.get("price") or 0
        sold_price      = row.get("sold_price")
        sold_date       = row.get("sold_date")
        marked_sold_raw = row.get("status_marked_sold_at")

        # Parse marked_sold_at for give-up check
        marked_sold_at = None
        if marked_sold_raw:
            try:
                marked_sold_at = datetime.fromisoformat(marked_sold_raw.replace("Z", "+00:00"))
            except Exception:
                pass

        # Case 1: sold price is known — append snippet
        if sold_price and sold_date:
            ok = patch_webflow_sold_snippet(webflow_item_id, slug, list_price, sold_price, sold_date)
            if ok:
                db_mark_sold_price_published(slug)
                snippet_item_ids.append(webflow_item_id)
            else:
                log.warning(f"[{slug}] snippet patch failed — will retry next run")
            continue

        # Case 2: no price yet — try fetching it again from RealtyAPI
        if sold_price is None:
            log.info(f"[{slug}] sold price still null — re-checking RealtyAPI")
            _, fetched_price, fetched_date = check_listing_status(webflow_item_id)
            time.sleep(REQUEST_SLEEP_SECS)

            if fetched_price:
                log.info(f"[{slug}] sold price now available: {fetched_price} on {fetched_date}")
                db_update_sold_price(slug, fetched_price, fetched_date)
                ok = patch_webflow_sold_snippet(webflow_item_id, slug, list_price, fetched_price, fetched_date)
                if ok:
                    db_mark_sold_price_published(slug)
                    snippet_item_ids.append(webflow_item_id)
                else:
                    log.warning(f"[{slug}] snippet patch failed after price fetch — will retry next run")
                continue

            # Case 3: still no price — check give-up threshold
            if marked_sold_at and marked_sold_at < give_up_cutoff:
                log.info(f"[{slug}] {SOLD_PRICE_GIVE_UP_DAYS}d elapsed with no sold price — giving up")
                db_mark_sold_price_published(slug)
            else:
                days_waiting = (now - marked_sold_at).days if marked_sold_at else "?"
                log.info(f"[{slug}] no sold price after {days_waiting}d — will retry next run")

    return snippet_item_ids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_maintenance():
    log.info("=== HousesUnder150K Maintenance — Start ===")
    start = time.time()

    # Pass 1: status sweep (Active + Pending)
    changed_item_ids, sweep_counts = run_status_sweep()

    # Pass 2: sold snippet publish
    snippet_item_ids = run_sold_snippet_pass()

    # Publish anything that changed
    all_changed = list(set(changed_item_ids + snippet_item_ids))
    if all_changed:
        publish_webflow_items(all_changed)
        publish_site()

    elapsed = time.time() - start
    log.info(
        f"=== Maintenance complete in {elapsed:.1f}s | "
        f"status_checked={sweep_counts['unchanged'] + sweep_counts['changed']} "
        f"status_changed={sweep_counts['changed']} "
        f"unchanged={sweep_counts['unchanged']} "
        f"errors={sweep_counts['errors']} "
        f"images_deleted={sweep_counts['images_deleted']} "
        f"snippets_published={len(snippet_item_ids)} ==="
    )


if __name__ == "__main__":
    run_maintenance()
