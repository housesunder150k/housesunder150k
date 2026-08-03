---
project: HousesUnder150K
file: runbook
type: living — append when new failure modes are discovered
last_updated: 2026-07-29
---

<!-- HousesUnder150K runbook -->

# HousesUnder150K Runbook

This HousesUnder150K runbook is the operational reference for pipeline failures, Webflow incidents, and status errors. Load when something is broken, counts are wrong, or a status incident needs investigation.

<!-- HousesUnder150K runbook -->

## HousesUnder150K Runbook — How to Use This File

Load this file when something is broken, counts are wrong, or a status incident needs investigation. Each section describes a failure mode, its root cause, and the exact fix.

---

## HousesUnder150K Runbook — Pipeline Not Running

**Symptoms:** No new listings published for 24+ hours. Railway logs show no recent runs.

**Check first:**
1. Railway dashboard → housesunder150k service → confirm cron is `0 13,17,21,1,5,9 * * *`
2. Check Railway logs for the last run — look for crash on startup vs. crash mid-run
3. Check Supabase `pipeline_runs` table — was a run started but never completed?

**Common causes:**
- Code was pushed that broke `ingest.py` on import (syntax error, missing package)
- Railway service was manually stopped
- `DAILY_PUBLISH_LIMIT` was hit and the pipeline exited early (not a failure — check `daily_limit_hit` in `pipeline_runs`)
- RealtyAPI key expired or rate limit hit

**Resolution:**
- Fix the code issue and push — Railway auto-deploys on push to main
- For immediate test: Railway MCP redeploy (do NOT change cron to `*/5`)
- Wait for `=== Pipeline complete ===` before any second trigger

---

<!-- HousesUnder150K runbook -->

## HousesUnder150K Runbook — Cron Overlap / Duplicate Listings

**Symptoms:** Multiple identical or near-identical listings published in a short window. `pipeline_runs` shows two rows with overlapping `started_at`/`completed_at`. Empty Webflow items with no content.

**Root cause:** Two cron containers ran simultaneously. Railway does not skip overlapping runs. Most common cause: a test cron like `*/5` was left active.

**Resolution:**
1. Check Railway service cron — if it is not `0 13,17,21,1,5,9 * * *`, fix it immediately
2. Delete any duplicate/empty Webflow CMS items via Webflow MCP
3. Delete corresponding rows from `published_listings` in Supabase (slugs of the bad items)
4. Check `seen_listings` — the bad MLS numbers may have been upserted; they will suppress re-ingestion for 7 days. If needed, delete those rows too.

**Prevention:** Never use `*/5` cron. Use Railway MCP redeploy for manual triggers only.

---

## HousesUnder150K Runbook — False Expired Listing

**Symptoms:** A listing that is still active on Realtor.com is showing as Expired or Sold on the site.

**Root cause (confirmed):** Property ID drift. Realtor.com can reissue a new `property_id` for the same physical listing on a data refresh. The `mls_number` stored at ingestion time is stale.

**Resolution:**
1. Find the listing's current Realtor.com URL — search by address manually
2. Extract the new `property_id` from the URL
3. Update `published_listings` in Supabase:
   ```sql
   UPDATE published_listings
   SET mls_number = 'NEW_PROPERTY_ID', status = 'Active', last_status_checked_at = now()
   WHERE slug = 'your-listing-slug';
   ```
4. Update Webflow status field back to Active via MCP:
   - PATCH the CMS item, set `status` to Active option ID `3b41185e9af84f92d8da092965308a2d`
   - Publish the item
   - Run `publish_site()`
5. Verify the next maintenance run does not re-mark it Expired (the refreshed `mls_number` should resolve cleanly now)

**Note:** `maintenance.py` includes the address-based fallback and auto-refreshes `mls_number` in Supabase when drift is detected. This issue should be self-healing for most cases after Session 8.

---

<!-- HousesUnder150K runbook -->

## HousesUnder150K Runbook — Webflow Publish Not Reaching Custom Domain

**Symptoms:** New listings appear on `housesunder150k.webflow.io` but not on `housesunder150k.com`.

**Root cause:** Full site publish was not called with both custom domain IDs, or only item-level publish was triggered.

**Resolution:**
```python
# Trigger manually via Webflow API
POST https://api.webflow.com/v2/sites/6a650a7eb2639262c4b6adb7/publish
Authorization: Bearer {WEBFLOW_API_TOKEN}
body: {
    "customDomains": [
        "6a661987994ab168be06566b",
        "6a661986994ab168be065664"
    ]
}
```
Or trigger via Webflow MCP: `publish_site` with both domain IDs.

If the issue is persistent, check whether the `publish_site()` function in `ingest.py` still has the correct domain IDs hardcoded.

---

## HousesUnder150K Runbook — Blank / Empty CMS Items in Webflow

**Symptoms:** Listing pages with no headline, no narrative, no price. Cards showing placeholder text.

**Root cause:** Empty content guard did not fire, or a Webflow write was triggered before content generation completed.

**Resolution:**
1. Find the item via Webflow MCP — check which fields are empty
2. If all fields are empty: the item slipped past the empty content guard. Delete it from Webflow MCP and from `published_listings` in Supabase.
3. If partial fields: content was written but partially — delete and re-add manually or wait for pipeline to retry (it won't — slug is now in `published_listings`, so it will be skipped)
4. For manual re-add: follow the manual listing entry process in `reference/_workflow.md`

**Prevention:** The empty content guard (`if not HEADLINE or not NARRATIVE: skip`) prevents writes when content is blank. The markdown strip (`**`, `#`, `---`) prevents parse failures. If blank items reappear, check whether the parser is matching label lines correctly.

---

<!-- HousesUnder150K runbook -->

## HousesUnder150K Runbook — Stale Deal of the Day (Multiple Listings Flagged)

**Symptoms:** More than one listing shows "DEAL OF THE DAY" banner. Homepage Deal of the Day section shows unexpected listing.

**Root cause:** `deal-of-the-day` field was set on multiple listings without clearing previous holders. This was the bug in Session 7 (5 listings simultaneously flagged).

**Resolution:**
1. Query Supabase to find all active Deal of the Day listings:
   ```sql
   SELECT slug, webflow_item_id FROM published_listings WHERE is_deal_of_day = true;
   ```
2. Keep the correct one. For all others:
   - PATCH Webflow: set `deal-of-the-day = false`
   - UPDATE Supabase: `SET is_deal_of_day = false WHERE slug = 'slug'`
3. Publish all changed items + full site publish

**Prevention:** `unset_deal_of_the_day()` in `ingest.py` clears the previous holder before writing a new hero listing. If this re-occurs, check whether that function is being called correctly.

---

## HousesUnder150K Runbook — Supabase Daily Count Not Resetting

**Symptoms:** Pipeline exits immediately at start of a new day claiming `DAILY_PUBLISH_LIMIT` is already hit.

**Root cause:** `published_date_ct` is being set incorrectly — using UTC instead of CT (America/Chicago).

**Resolution:**
1. Check recent rows in `published_listings`:
   ```sql
   SELECT slug, published_at, published_date_ct FROM published_listings ORDER BY published_at DESC LIMIT 10;
   ```
2. Verify `published_date_ct` is the CT date, not UTC date. Evening CT dates should match the previous day in UTC.
3. If dates are wrong: `get_today_ct()` function in `ingest.py` uses `pytz` + `America/Chicago`. Confirm `pytz` is installed and the function is being called at the time of insert, not at script start.

---

<!-- HousesUnder150K runbook -->

## HousesUnder150K Runbook — Maintenance Job False Positives (Listings Incorrectly Marked Sold/Expired)

**Symptoms:** Listings that are still active on Realtor.com are showing as Sold or Expired on the site after a maintenance run.

**Diagnosis:**
1. Check `pipeline_runs` — maintenance uses a separate `pipeline_runs` table? No — maintenance.py does not currently log to `pipeline_runs`. Check Railway logs for the maintenance service instead.
2. For each incorrectly changed listing: follow the "False Expired Listing" runbook above.
3. Check whether `map_status()` in `maintenance.py` is correctly reading `detail.flags.is_pending` and `detail.status`.

**Note:** The only confirmed false-positive root cause is property_id drift (ADR-009). The address-based fallback in `maintenance.py` should catch this automatically post-Session 8.

---

## HousesUnder150K Runbook — RealtyAPI Rate Limit Hit

**Symptoms:** Pipeline logs show 429 errors from RealtyAPI. Listings fetched drops to 0.

**Check:**
- RealtyAPI dashboard → usage this month vs. 20,000/month plan cap
- Worst-case monthly usage: ~8,800 requests (discovery + maintenance)
- If hitting the cap: either a runaway cron was looping, or test runs consumed credits

**Resolution:**
- Wait for monthly reset
- If budget allows: upgrade to the next RealtyAPI tier
- If a runaway cron caused it: fix the cron (see "Cron Overlap" above) and consider `DAILY_PUBLISH_LIMIT` reduction
