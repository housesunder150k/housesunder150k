---
project: HousesUnder150K
file: workflow
type: permanent — update when protocols change
last_updated: 2026-07-29
---

<!-- HousesUnder150K workflow -->

# HousesUnder150K Workflow

This HousesUnder150K workflow document is the permanent session protocol reference for the HousesUnder150K project. Load at session start to orient to run order, environment setup, and key operational procedures.

<!-- HousesUnder150K workflow -->

## HousesUnder150K Workflow — Session Start Protocol

1. Load `reference/_index.md` — orientation, quick-ref tables, current sprint
2. Load `rules/_rules.md` — non-negotiables always in context
3. Load `sessions/_session_log.md` — what is pending, what last ran, current listing count
4. Load task-specific files based on session focus (see `_index.md` vault file map)
5. **Never assume field IDs, option IDs, or API schemas from memory** — always verify from `schema/_schema.md` or live system
6. Check Supabase `published_listings` count and Railway logs before touching anything in the pipeline

## HousesUnder150K Workflow — Session End Protocol

1. Update `sessions/_session_log.md` — listings published, pipeline run results, what changed, what is pending
2. If any schema changed — update `schema/_schema.md`
3. If any open question was resolved — update `open-questions/_open_questions.md`
4. If any new locked decision was made — append to `decisions/_adr.md`
5. If any non-negotiable rule was established — append to `rules/_rules.md`
6. Write session report to `session_reports/YYYY-MM-DD_[description].md`
7. Update `primer/_primer.md` `updated` and `next_action` frontmatter fields
8. Commit: `git add . && git commit -m "session: [description]" && git push origin main`

<!-- HousesUnder150K workflow -->

## HousesUnder150K Workflow — How to Resume After a Gap

1. Load `sessions/_session_log.md` first — last known state
2. Check Railway logs for runs since last session — confirm pipeline is running, no errors
3. Check Supabase `published_listings` count — verify against session log
4. Check Webflow CMS live listing count — should match Supabase
5. If counts diverge → check `maintenance/_runbook.md` for reconciliation steps
6. Resume from pending items in `_session_log.md`

## HousesUnder150K Workflow — Vault vs Live System Priority

**The vault is orientation, not authoritative state.** Field IDs, option IDs, and row counts drift. Always verify from the live system before acting:

- Webflow field IDs → `get_bindable_sources` or `list_collections` via MCP
- Supabase row counts → `SELECT COUNT(*) FROM published_listings WHERE status = 'Active'`
- Railway env vars → Railway MCP `list-variables`
- RealtyAPI response structure → test call with `REALTYAPI:call_endpoint` before writing code

<!-- HousesUnder150K workflow -->

## HousesUnder150K Workflow — Manual Listing Entry (Deal of the Day)

For manually adding a high-score listing that the pipeline missed:

1. Find Realtor.com property URL → extract `property_id` from URL (`_M{digits}` → strip hyphens)
2. Call RealtyAPI `/details/byid?property_id=X` for full data
3. Upload hero photo to Cloudflare Images → get delivery URL
4. Create Webflow CMS item via MCP with all fields, `deal-of-the-day: true`
5. Publish item, then publish site (both custom domain IDs required)
6. Insert row into Supabase `published_listings` manually
7. Clear any stale `deal-of-the-day` flags from other listings first

## HousesUnder150K Workflow — Pipeline Manual Trigger

Never modify cron to `*/5` — use Railway MCP redeploy instead:
```
Railway:redeploy → service: housesunder150k → environment: production
```
Wait for `=== Pipeline complete ===` in logs before any second trigger.

<!-- HousesUnder150K workflow -->

## HousesUnder150K Workflow — Environment Variables

All credentials in Railway env vars. Never in code, never committed.

| Variable | Service | Notes |
|----------|---------|-------|
| ANTHROPIC_API_KEY | ingest | |
| CLOUDFLARE_ACCOUNT_ID | ingest | af60f586464675e914119c0743898631 |
| CLOUDFLARE_API_TOKEN | ingest | |
| DAILY_PUBLISH_LIMIT | ingest | =10, change without deploy |
| REALTYAPI_KEY | ingest | |
| REPLIERS_API_KEY | ingest | ⚠ unused — remove |
| SOVRN_AFFILIATE_URL | ingest | test link until Sovrn approves |
| SUPABASE_KEY | ingest | service role key |
| SUPABASE_URL | ingest | |
| WEBFLOW_API_TOKEN | ingest | site-level token only |
| WEBFLOW_COLLECTION_ID | ingest | 6a650bab14666c3157f27618 |
| REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT | maintenance | =500/run |
| REALTYAPI_KEY | maintenance | reference to main service var |
| WEBFLOW_API_TOKEN | maintenance | reference to main service var |
| WEBFLOW_COLLECTION_ID | maintenance | reference to main service var |
| SUPABASE_URL | maintenance | reference to main service var |
| SUPABASE_KEY | maintenance | reference to main service var |

Maintenance service credentials are set as **variable references** to the main service (`${{housesunder150k.VAR}}`), not duplicated raw values.
