---
project: HousesUnder150K
file: primer
type: permanent — load at every session start
last_updated: 2026-07-28
entity: HousesUnder150K.com — housesunder150k@gmail.com
phase: Pipeline live on Realtor.com via RealtyAPI. States pages + SEO live. Sold/pending maintenance job + status banner live. Monetization not yet active.
next_action: Add is_pending check to ingest.py → remove REPLIERS_API_KEY from Railway → configure Beehiiv → wire gallery-images in Webflow Designer
---

<!-- HousesUnder150K primer -->

# HousesUnder150K Primer

This HousesUnder150K primer is the authoritative session-start document for the HousesUnder150K project. Load this HousesUnder150K primer at the beginning of every session before reading any other vault file.

## What HousesUnder150K Is

HousesUnder150K.com is POC Site 1 of a planned 10-site media holding company built on automated content pipelines. HousesUnder150K is a real estate content platform surfacing listings under $150K, scoring them editorially, generating AI narrative in the voice of Michelle Bowers (theoldhouselife.com), publishing to website and social, monetizing via display ads, affiliate links, and email subscriptions.

**The only metric that matters right now for HousesUnder150K: $1,000/month within 90 days of launch.**

<!-- HousesUnder150K primer -->

## HousesUnder150K — Vault File Map

| File | Load When |
|------|-----------|
| `reference/_index.md` | Every HousesUnder150K session — orientation, quick-ref tables |
| `reference/_workflow.md` | Every HousesUnder150K session — session start/end protocol |
| `rules/_rules.md` | Every HousesUnder150K session — non-negotiables |
| `sessions/_session_log.md` | Every HousesUnder150K session — current status and pending items |
| `schema/_schema.md` | Any Webflow CMS, Supabase, or API field session |
| `decisions/_adr.md` | Any HousesUnder150K architecture or pipeline decision session |
| `specs/_spec_pipeline.md` | Any HousesUnder150K ingest pipeline session |
| `specs/_spec_maintenance.md` | Any HousesUnder150K maintenance job session |
| `specs/_spec_scoring.md` | Any HousesUnder150K scoring model session |
| `specs/_spec_content.md` | Any HousesUnder150K content generation or editorial session |
| `maintenance/_runbook.md` | Any HousesUnder150K recovery or incident session |
| `open-questions/_open_questions.md` | Any session touching unresolved HousesUnder150K items |
| `security/_security.md` | Any HousesUnder150K security or credentials session |
| `subscription/_subscription.md` | Any HousesUnder150K email or Beehiiv session |

---

<!-- HousesUnder150K primer -->

## HousesUnder150K — CRITICAL: Data Source

**Repliers API — DEAD END for HousesUnder150K. Do not pursue. MLS license required.**

**RealtyAPI (realtyapi.io) — CURRENT HousesUnder150K DATA SOURCE**
- Endpoint: `https://realtor.realtyapi.io` (Realtor.com)
- PRO plan: $20/mo, 20,000 requests/month
- Railway env var: `REALTYAPI_KEY`
- 1,969+ results per state — full nationwide coverage for HousesUnder150K
- property_id is NOT stable — can drift; see ADR-009 and `maintenance/_runbook.md`

---

<!-- HousesUnder150K primer -->

## HousesUnder150K — Current Build State

**HousesUnder150K IS LIVE AND WORKING**
- housesunder150k.com — SSL active, Webflow Premium
- HousesUnder150K pipeline: RealtyAPI → Claude scoring → content gen → Cloudflare Images → Webflow CMS → auto site publish
- Railway: 6 runs/day, cron `0 13,17,21,1,5,9 * * *`
- HousesUnder150K daily publish limit: 10/day via DAILY_PUBLISH_LIMIT env var
- HousesUnder150K maintenance job: biweekly (Wed/Sat), Railway separate service
- Supabase: 3 tables — live and working
- 7-day seen listing suppression
- ~30 real HousesUnder150K listings live on site
- States pages: all 50 live, CMS-native Reference field architecture
- SEO: dynamic titles/descriptions, structured data (client-side JS), alt text, internal linking

**NOT YET ACTIVE on HousesUnder150K**
- Sovrn affiliate — account under review, pending approval
- Beehiiv / email subscriptions — not configured
- Social publishing — captions generated but not posted
- Display ads — not applied to any network
- gallery-images MultiImage — field in CMS, not wired to template

---

<!-- HousesUnder150K primer -->

## HousesUnder150K — Session Protocol

**Start:** Read `reference/_index.md` → `rules/_rules.md` → `sessions/_session_log.md` → task-specific HousesUnder150K files. Never assume field IDs from memory. Check live systems before touching anything.

**End:** Update `sessions/_session_log.md` → update this HousesUnder150K primer front matter → write session report to `session_reports/` → git commit and push.

---

<!-- HousesUnder150K primer -->

## HousesUnder150K — Stack Summary

| Layer | Service | Cost |
|-------|---------|------|
| Site | Webflow Premium | $25/mo |
| DNS + Images | Cloudflare | $5/mo (Images) |
| HousesUnder150K pipeline host | Railway Hobby | $5/mo |
| Database | Supabase Free | $0 |
| Data | RealtyAPI PRO | $20/mo |
| AI | Anthropic API | ~$25-38/mo |
| **Total** | | **~$56-74/mo** |

HousesUnder150K break-even: ~12-15 Sovrn leads/month at $5/lead commission.

---

<!-- HousesUnder150K primer -->

## HousesUnder150K — Webflow IDs (Quick Reference)

- **Site ID:** `6a650a7eb2639262c4b6adb7`
- **Listings Collection:** `6a650bab14666c3157f27618`
- **States Collection:** `6a67c480dba86ce339bab621`
- Full HousesUnder150K field IDs, option IDs, and page IDs → `schema/_schema.md`

---

<!-- HousesUnder150K primer -->

## HousesUnder150K — Key Architecture Rules

- Site-level Webflow API token only (workspace tokens lack cms:write) for HousesUnder150K
- HousesUnder150K listings are never deleted or unpublished — status field + banner only
- HousesUnder150K Deal of the Day = one slot per CT calendar day, enforced in code
- Cron overlap causes duplicate writes — never use `*/5` in HousesUnder150K production
- property_id is not a stable Realtor.com identifier for HousesUnder150K — address fallback required
