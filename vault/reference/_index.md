---
project: HousesUnder150K
file: vault_index
type: permanent — load at every session start
last_updated: 2026-07-29
---

<!-- HousesUnder150K vault_index -->

# HousesUnder150K Vault Index

This HousesUnder150K vault index is the session-start orientation document for the HousesUnder150K project. Load this HousesUnder150K vault index first at every session to orient to current sprint status and locate task-specific files.

<!-- HousesUnder150K vault_index -->

## HousesUnder150K Vault Index — What HousesUnder150K Is

Automated real estate content platform surfacing residential listings priced under $150K nationwide. Pipeline scores listings editorially, generates AI narrative in the voice of Michelle Bowers (theoldhouselife.com), publishes to Webflow CMS, and monetizes via affiliate links, display ads, and email subscriptions. POC Site 1 of a planned 10-site media holding company.

**Entity:** housesunder150k@gmail.com
**Live site:** https://www.housesunder150k.com
**Webflow Designer:** https://housesunder150k.design.webflow.com
**GitHub:** github.com/housesunder150k/housesunder150k
**The only metric that matters right now:** $1,000/month within 90 days of launch.

---

## HousesUnder150K Vault Index — Vault File Map

| File | Room | Load When |
|------|------|-----------|
| `reference/_index.md` | reference | Every session — this file |
| `reference/_workflow.md` | reference | Every session — session protocol |
| `primer/_primer.md` | primer | Any product, strategy, or architecture session |
| `rules/_rules.md` | rules | Every session — non-negotiables |
| `sessions/_session_log.md` | sessions | Every session — current build status and pending items |
| `schema/_schema.md` | schema | Any Webflow CMS, Supabase, or API field session |
| `decisions/_adr.md` | decisions | Any architecture, pipeline, or stack decision session |
| `specs/_spec_pipeline.md` | specs | Any ingest pipeline session |
| `specs/_spec_maintenance.md` | specs | Any maintenance job or sold/pending detection session |
| `specs/_spec_scoring.md` | specs | Any scoring model, calibration, or tuning session |
| `specs/_spec_content.md` | specs | Any content generation, voice, or editorial session |
| `maintenance/_runbook.md` | maintenance | Any recovery, outage, or false-status incident |
| `open-questions/_open_questions.md` | open-questions | Any session touching unresolved items |
| `security/_security.md` | security | Any security, credentials, or access review session |
| `subscription/_subscription.md` | subscription | Any email, Beehiiv, or subscriber monetization session |

---

<!-- HousesUnder150K vault_index -->

## HousesUnder150K Vault Index — Infrastructure Quick Reference

| Layer | Service | Cost | Notes |
|-------|---------|------|-------|
| Site | Webflow Premium | $25/mo | housesunder150k.com |
| DNS | Cloudflare | Free | SSL active |
| Images | Cloudflare Images | $5/mo | Starter bundle |
| Pipeline host | Railway Hobby | $5/mo | Auto-deploy on push to main |
| Database | Supabase Free | $0 | 3 tables, dedup + tracking |
| Data source | RealtyAPI PRO | $20/mo | Realtor.com, 20K req/mo |
| AI | Anthropic API | ~$25-38/mo | claude-sonnet-4-6, 2 calls/listing |
| Email | Beehiiv | TBD | Not yet configured |
| Affiliate | Sovrn / Realtor.com | $5/lead | Pending Sovrn approval |
| **Total** | | **~$56-74/mo** | Break-even ~12-15 Sovrn leads |

---

<!-- HousesUnder150K vault_index -->

## HousesUnder150K Vault Index — Pipeline Quick Reference

**Cron:** `0 13,17,21,1,5,9 * * *` — 6 runs/day, 4-hour intervals (CT)
**Daily limit:** 10 listings/day via `DAILY_PUBLISH_LIMIT` Railway env var
**Score threshold:** ≤5 discard, 6+ publish
**Seen suppression:** 7 days via `seen_listings` table

```
RealtyAPI (50 listings, 1 per state) → Claude scoring → Claude content gen → Cloudflare Images → Webflow CMS → Supabase dedup
```

**Maintenance:** `0 10 * * 3,6` — Wednesday + Saturday, 10:00 UTC. Status check on all Active listings. 500 RealtyAPI requests/run cap.

---

<!-- HousesUnder150K vault_index -->

## HousesUnder150K Vault Index — Webflow Quick Reference

**Site ID:** `6a650a7eb2639262c4b6adb7`
**Listings Collection ID:** `6a650bab14666c3157f27618`
**API token:** Site-level only — workspace tokens do NOT have cms:write scope

| Page | ID |
|------|----|
| Homepage | 6a650a80b2639262c4b6adba |
| Listing Template | 6a650bab14666c3157f2761e |
| Deal of the Day | 6a6612c009d35063c09f9ac3 |
| About | 6a6612c0d157d1643e103769 |
| States Index | 6a6612c171f470cf8a437d71 |
| States Template | auto-generated on States collection creation |

**Custom Domain IDs (publish_site calls):**
- housesunder150k.com: `6a661987994ab168be06566b`
- www.housesunder150k.com: `6a661986994ab168be065664`

---

<!-- HousesUnder150K vault_index -->

## HousesUnder150K Vault Index — Railway Quick Reference

**Project ID:** `586f6dd5-1930-4301-8262-d5562a3119e7`

| Service | ID | Cron |
|---------|-----|------|
| housesunder150k (ingest) | 15ca3583-43d1-4823-bf3d-5740976e439c | `0 13,17,21,1,5,9 * * *` |
| housesunder150k-maintenance | 2a38bce9-2a88-4711-89b7-3aeb190fe5e3 | `0 10 * * 3,6` |

⚠ **Cron overlap is dangerous.** Railway does not skip overlapping runs. Never use `*/5` in production. Use Railway MCP redeploy for manual triggers only.

---

<!-- HousesUnder150K vault_index -->

## HousesUnder150K Vault Index — Supabase Quick Reference

**Project ID:** `krzpkaxvbmpdeluqzkka`
**URL:** `https://krzpkaxvbmpdeluqzkka.supabase.co`
**Plan:** Free tier

| Table | Purpose |
|-------|---------|
| published_listings | Persistent dedup + daily CT count + status tracking |
| seen_listings | 7-day suppression of scored listings |
| pipeline_runs | Per-run cost and performance tracking |

---

<!-- HousesUnder150K vault_index -->

## HousesUnder150K Vault Index — Current Sprint

**Phase: Pipeline live — content accumulating — monetization not yet active**

Pipeline live on Realtor.com via RealtyAPI. States pages + SEO live (Session 7). Sold/pending maintenance job + status banner live (Session 8). Sovrn affiliate pending approval. Beehiiv not yet configured. No paid traffic. SEO is the only acquisition channel active.

See `sessions/_session_log.md` for full current status and pending items.
