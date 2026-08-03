---
project: HousesUnder150K
file: spec_maintenance
type: living — update when maintenance.py changes
last_updated: 2026-07-29
script: scripts/maintenance.py
---

<!-- HousesUnder150K spec_maintenance -->

# HousesUnder150K — Maintenance Spec

This HousesUnder150K maintenance spec defines the maintenance.py pipeline that checks listing status and updates Webflow + Supabase when listings go Pending, Sold, or Expired. Load for any session touching maintenance.py or sold/pending detection.

<!-- HousesUnder150K spec_maintenance -->

## HousesUnder150K Maintenance Spec — Overview

`maintenance.py` is a separate Railway service that checks the status of all Active published listings against RealtyAPI and updates Webflow + Supabase when a listing has gone Pending, Sold, or Expired. Listings are never deleted or unpublished — only their `status` field changes, and a banner is displayed on the listing image.

**Railway service:** `housesunder150k-maintenance` (ID: `2a38bce9-2a88-4711-89b7-3aeb190fe5e3`)
**Cron:** `0 10 * * 3,6` — Wednesday + Saturday, 10:00 UTC
**Start command:** `python scripts/maintenance.py`
**Restart policy:** NEVER — one-shot scheduled job, does not loop-retry on failure

---

## HousesUnder150K Maintenance Spec — Design Principles

**Bounded request volume.** Cap at 500 RealtyAPI requests per run (`REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT`). Combined with discovery pipeline, worst-case monthly RealtyAPI usage stays ~44% under the 20,000/month plan cap.

**Rotating queue.** Listings are checked oldest-first by `last_status_checked_at` (NULLs first). Every run advances the queue. No listing goes unchecked indefinitely as the pool grows.

**Conservative status transitions.** A network failure or ambiguous response does not mark a listing Expired. The address-based fallback is attempted first. If both fail, the listing is left unchanged and rechecked next rotation.

**Listings never deleted.** Status change → update `status` field and show banner. Listing page stays live. SEO and backlink value preserved permanently.

**Batched Webflow operations.** One PATCH + one item publish per changed listing. Single full site publish at end of run if anything changed.

---

<!-- HousesUnder150K spec_maintenance -->

## HousesUnder150K Maintenance Spec — Pipeline Flow

```
1. Query published_listings WHERE status = 'Active'
   ORDER BY last_status_checked_at ASC NULLS FIRST
   LIMIT REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT

2. For each listing:
   a. check_listing_status(mls_number, address, city, state)
      → new_status = one of: Active, Pending, Sold, Expired
   b. UPDATE published_listings SET last_status_checked_at = now()
   c. If new_status != 'Active':
      → PATCH Webflow item status field
      → Publish item (item-level)
      → UPDATE published_listings SET status = new_status

3. If any status changed:
   → publish_site() — single full site publish
```

---

## HousesUnder150K Maintenance Spec — Status Detection Logic

### check_listing_status(mls_number, address, city, state)

Two-function design: one orchestrating function (linear top-to-bottom) + one small `map_status()` helper.

```
1. Try GET /details/byid?property_id={mls_number}
   → On success: map response to status via map_status()
   → If status != Active: return it

2. If request fails OR response has no `detail` key:
   → Try GET /details/byaddress?address=X&city=Y&state=Z
   → On success:
       - If new property_id found: UPDATE mls_number in Supabase (property_id drift fix)
       - map response to status
   → If address lookup also fails:
       - Log warning, leave status unchanged (return Active)
       - Will recheck next rotation
```

### map_status(detail_response)

```python
if detail is None or "detail" not in response:
    return "Expired"
if response["detail"]["flags"].get("is_pending"):
    return "Pending"
if response["detail"].get("status") == "sold":
    return "Sold"
return "Active"
```

**Confirmed live (Session 8):**
- `flags.is_pending == true` is the reliable pending signal. `detail.status` stays `"for_sale"` even for pending listings — confirmed against 3 real pending listings.
- `detail.status == "sold"` is reliable for sold listings.
- A response with `{"message": "500: Home not found."}` (no `detail` key) maps to Expired.

---

<!-- HousesUnder150K spec_maintenance -->

## HousesUnder150K Maintenance Spec — Property ID Drift

Realtor.com can reissue a new `property_id` for the same physical listing on a data refresh. This was confirmed in a live validation run (Session 8): Indianapolis listing had `property_id` drift from `22116371` to `4300388528`.

When the `/details/byid` call fails but `/details/byaddress` succeeds with a new `property_id`:
1. The new `property_id` is persisted to `published_listings.mls_number` in Supabase
2. Future maintenance runs use the refreshed ID and won't need the fallback again
3. The listing status is mapped from the address-resolved response, not marked Expired

---

## HousesUnder150K Maintenance Spec — Webflow Status Update

```python
# PATCH the status field
PATCH /v2/collections/{collection_id}/items/{item_id}
body: {
    "fieldData": {
        "status": OPTION_ID_FOR_NEW_STATUS
    }
}

# Item-level publish
POST /v2/collections/{collection_id}/items/{item_id}/live
```

Status option IDs:
- Active: `3b41185e9af84f92d8da092965308a2d`
- Pending: `001257c77d3ccd4477d620ac135a4afd`
- Sold: `541de6b6934cd79d6a76c98d91610063`
- Expired: `e630110b6993074e3f7299e8dbb7fdc1`

---

<!-- HousesUnder150K spec_maintenance -->

## HousesUnder150K Maintenance Spec — Sold/Pending Banner

The status banner is rendered on all listing image locations via CSS + CMS text binding. No code in `maintenance.py` controls the banner — it is always shown when `status` is Pending or Sold, via conditional visibility set in the Webflow Designer.

Banner locations (all 4 use the same `status-banner` style class):
- Listing Template hero image (`lp-hero`)
- Homepage Latest Deals card grid (`hu150-card-img-wrap`)
- States Template card grid (same class)
- Deal of the Day page hero image

Banner style: bottom-positioned, full width, cyan `#00D4FF` text, semi-transparent dark background, uppercase via CSS `text-transform`.

**Known minor issue:** On the listing detail hero, the banner (bottom:0, full width) may slightly overlap `lp-hero-price` (bottom:32px, left:40px) when both are visible. Designer touch-up pending.

---

## HousesUnder150K Maintenance Spec — Deal of the Day + Status Interaction

Deal of the Day requires no special handling in `maintenance.py`. The `deal-of-the-day` flag is a one-shot ingestion-time flag with no re-selection mechanism. If a Deal of the Day listing goes Pending or Sold mid-cycle:
- The banner shows on the Deal of the Day section (the banner is bound to wherever the image appears)
- The listing rides out its cycle as Deal of the Day with the banner visible
- No new Deal of the Day is selected by the maintenance job

---

<!-- HousesUnder150K spec_maintenance -->

## HousesUnder150K Maintenance Spec — Environment Variables

All set as **variable references** to the main service in Railway — not duplicated raw values.

| Variable | Source |
|----------|--------|
| `REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT` | `=500` (per-run cap, not true weekly) |
| `REALTYAPI_KEY` | `${{housesunder150k.REALTYAPI_KEY}}` |
| `WEBFLOW_API_TOKEN` | `${{housesunder150k.WEBFLOW_API_TOKEN}}` |
| `WEBFLOW_COLLECTION_ID` | `${{housesunder150k.WEBFLOW_COLLECTION_ID}}` |
| `SUPABASE_URL` | `${{housesunder150k.SUPABASE_URL}}` |
| `SUPABASE_KEY` | `${{housesunder150k.SUPABASE_KEY}}` |

Using variable references means a key rotation on the main service automatically applies to the maintenance service — no drift risk.

---

## HousesUnder150K Maintenance Spec — RealtyAPI Usage (Maintenance)

- 500 requests per run × 2 runs/week × ~4.3 weeks/month = ~4,300 requests/month max
- Combined with discovery pipeline (~4,500/month): ~8,800/month worst case
- Plan cap: 20,000/month — ~56% headroom at worst case

The `REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT` variable name is technically a per-run cap, not a true weekly total. The naming is historical and accepted — the value (500) is correct for the intent.

---

<!-- HousesUnder150K spec_maintenance -->

## HousesUnder150K Maintenance Spec — Validation Run Results (Session 8)

**Run 1 (with property_id drift bug):**
- 30 Active listings checked
- 3 status changes: 2 correctly Pending, 1 incorrectly Expired (Indianapolis — property_id drift)
- 0 errors
- Batched Webflow publish + site publish confirmed working

**Run 2 (after bug fix):**
- 28 Active listings checked (Indianapolis corrected to Active manually)
- 0 status changes
- 0 errors
- No false Expired flags, fallback path not needed (all IDs resolved cleanly)
