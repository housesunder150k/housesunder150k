---
project: HousesUnder150K
file: session_log
type: running session index — concise overview entries, newest at top
last_updated: 2026-08-03
---

<!-- HousesUnder150K session_log -->

# HousesUnder150K Session Log

## August 3, 2026 — Slug format fix
- `make_slug()` updated: signature changed from `(city, price)` to `(street, city, state)`. Produces address-based slugs (`409-n-davis-ave-oakland-ne`) instead of `oakland-110000`.
- Both call sites updated in `process_listing()` and `write_webflow()`. Maintenance job unaffected — uses `webflow_item_id`, not slug.
- `_spec_pipeline.md` updated to reflect new slug format.
- Existing ~30 listings keep their old-style slugs; maintenance job sold/pending detection is unaffected.

---

## August 2, 2026 — Session 12: FAQ Schema + Closing Costs Article + Related Articles + Schema Fixes
- Strategic discussion on Google rich results, FAQ schema, and featured snippet eligibility. Decided visible FAQ section required on all articles (Google prohibits schema on hidden content).
- `spec_articles_policy.md` updated: word count to 2,500, FAQ section added as required element, Section 9 added with full FAQ requirements and schema spec, intake template updated, open question on word count retrofit closed.
- FAQ section built into article template (`detail_articles`): `ap-faq-wrap` / `ap-faq-item` / `ap-faq-question` / `ap-faq-answer` / `ap-faq-heading` — 5 new CSS classes, 6 Q&A slots, placed after `lp-cta-block` before `ap-author-box`.
- Site footer script updated: third block for `FAQPage` JSON-LD; fourth block for `Article` JSON-LD (DOM-reading, replaced broken server-side token approach). All four schema blocks now confirmed working.
- New article researched, fact-checked (3 rounds), and published: "What You'll Really Pay at Closing on a $150K Home" (Buying Guide, ~2,500 words, 6 FAQ pairs, CMS ID `6a6f36df582749ce2c6aa30e`).
- FAQ retrofit completed on all 3 articles. Jordan Reyes author photo added.
- Related Articles section: static manual approach replaced with fully automatic CMS Collection List (Articles, sorted by Published Date desc, limit 2, excludes current). Link binding via Designer URL Path. Zero maintenance going forward.
- Rich Results Test confirmed: FAQPage ✅ and Article ✅ schema both working with real data on closing costs article.
- GSC check: 3 impressions, position 24.7 for "homes for 150000" within first 7 days. Healthy signal.
- Outstanding: remove `article-url` Link field from Articles CMS (superseded by URL Path binding).

---

This HousesUnder150K session log is the running index of all development sessions for the HousesUnder150K project. Entries are concise overviews — newest at top. Load this HousesUnder150K session log at every session start to confirm current build status and pending priorities.

<!-- HousesUnder150K session_log -->

## July 29, 2026 — HousesUnder150K vault signal improvement pass
- Applied Practice 2 (keyword seeding) across all non-compliant HousesUnder150K vault documents.
- Fixed front matter: `_open_questions.md` type corrected; `_index.md` file value corrected (index → vault_index); `_session_log.md` type corrected.
- Added title headings, opening sentences, prefixed section headings, and comment anchors to all 16 non-compliant documents.
- No product or codebase changes this session.

---

## July 28, 2026 — Vault front matter audit and remediation
- Audited front matter across all HousesUnder150K vault files as part of cross-project MemPalace recall improvement pass.
- Fixed 4 issues: `_primer.md` missing `file`, `type`, wrong date key; `_session_log.md` prose removed from `last_updated` value; `real-estate-content-platform-concept.md` and `scoring-prompt-v1.md` added YAML front matter (had none).
- No product or codebase changes this session.

---

## Current Build Status

**Phase: Pipeline live — content accumulating — monetization not yet active**

Pipeline running 6x/day on Realtor.com data via RealtyAPI. Maintenance job running biweekly (Wed/Sat) for sold/pending detection. States pages live. SEO layer live. Affiliate (Sovrn) pending approval. Beehiiv not configured. No paid traffic — SEO is the only active acquisition channel.

**Live listings:** ~44 published (as of Session 9 end)
**Pipeline status:** Running — 6 cron runs/day, Railway Hobby
**Maintenance status:** Running — biweekly, Railway Hobby (same project, separate service)
**Affiliate:** Sovrn pending approval — using direct Realtor.com href in the interim
**Email:** Beehiiv not yet configured — subscribe button on site but no backend
**Gallery photos:** Live on template — next pipeline run will populate first listings

---

## Pending Items (ordered by priority)

### P1 — Pipeline
- [ ] Remove `REPLIERS_API_KEY` from Railway ingest service — unused dead credential
- [ ] Delete `specs/scoring-prompt-v1.md` from vault — prompt now lives in codebase

### P2 — Monetization
- [ ] Sovrn approval — swap `SOVRN_AFFILIATE_URL` in Railway when approved. No code change needed.
- [ ] Beehiiv setup — configure free newsletter, connect to subscribe button on site
- [ ] Research highest-paying mortgage affiliate program — add as fixed button on listing pages
- [ ] AdSense implementation — display ads, first monetization layer
- [ ] Build Partners page on Webflow — agent advertising/sponsorship opportunities
- [ ] Newsletter product definition — weekly curated digest of score 8-10 listings

### P3 — Site Completeness
- [ ] Fix potential hero image stretching on listing detail page at wide/ultrawide viewports — noted Session 7, unconfirmed
- [ ] States Template and Listings Template footer/logo audit

### P4 — Documentation
- [ ] Session 7 report — never written. Reconstructable from Railway history and Webflow activity.
- [ ] Update vault docs to reflect Session 9 changes (address key, gallery, pending filter)

### P5 — Security
- [ ] Supabase RLS — disabled on all 3 tables. Enable before scaling.
- [ ] MFA audit — Google, Railway, Supabase, Cloudflare, GitHub, Anthropic
- [ ] Credential audit — full inventory and rotation schedule

### P6 — Minor UX
- [ ] Status banner overlap with price display on listing detail hero — minor visual touch-up
- [ ] States Template and Listings Template footer/logo audit

---

## Session Entries

### 2026-07-28 — Session 9
**Focus:** Competitive analysis, monetization strategy, gallery photos, pending filter, address-based dedup, maintenance Cloudflare cleanup, Webflow gallery template wiring, maintenance job validation.

**Competitive research:**
- Deep analysis of theoldhouselife.com (396K monthly visits, 64% paid social, Google AdSense confirmed, 484 keywords — essentially no SEO, declining from 1M peak in 2023)
- CIRCA Old Houses fetched directly — confirmed WordPress (Redux theme, WP Engine), manual curation, Mailchimp newsletter, paid listing directory model for agents with $500K-$3M+ inventory. The "2 million page views/month" claim in footer inconsistent with Similarweb data (~63K visits). CIRCA has drifted upmarket, abandoned the affordable segment entirely.
- oldhousesunder100k.com — WordPress (Bard/WP Royal free theme), 100% manual, Amazon/Target/Home Depot/eBay affiliate model. ~20K monthly visits. Sister site to oldhousesunder50k.com.
- CIRCA Cheap Old Houses newsletter confirmed: three paid tiers — under $25K, farmhouses 3+ acres under $150K, Canada + Europe under $150K. Validates paid newsletter market in the space.
- Key finding: the entire competitive space is social-traffic dependent with minimal SEO. HousesUnder150K.com's automated pipeline with structured listing pages and dynamic SEO is already ahead of every competitor on that dimension.

**Monetization strategy decisions:**
- Display ads (AdSense → Mediavine → Raptive) — implement first
- Affiliate: Sovrn/Realtor.com ($5/lead) already wired; add mortgage affiliate as fixed button on listing pages
- Newsletter: free subscription, curated weekly digest of score 8-10 listings, segmented by property type. With disclosure, subscriber list segmented by geography is a sellable asset to local agents.
- Personal search alert SaaS product (zip code + radius daily digest) — strong economics but requires auth, portal, Stripe, DB profiles — parked as separate future product, not housesunder150k.com feature
- CIRCA agent listing directory model explicitly rejected — misaligned with editorial model

**RealtyAPI photo data confirmed:**
- Full `photos[]` array (16-20 photos typically) returned in search results — no additional API call needed
- `photo_count` field available
- `street_view_url` available on every listing (unused currently)
- `estimate` field available (Realtor.com AVM — useful deal signal)

**ingest.py changes:**
- `pending: False` added to `fetch_search_results()` params — excludes contingent listings at source
- `upload_image()` now returns `(delivery_url, image_id)` tuple instead of single URL
- `upload_gallery_images()` new function — uploads `photos[1:4]` (skipping hero at index 0), returns `(gallery_field_data, gallery_image_ids)`
- `write_webflow()` accepts `gallery_field_data`, writes `gallery-images` MultiImage field only when non-empty
- `db_insert_published()` accepts `gallery_image_ids` list, stores in Supabase `TEXT[]` column
- `process_listing()` orchestrates hero + gallery uploads, passes IDs through to Supabase
- `make_address_key()` added — builds `"{street}|{city}|{state}"` normalized to lowercase
- `normalize_listing()` sets `mlsNumber` to `address_key` instead of `property_id`
- `fetch_listings()` deduplication uses address keys, not property_ids
- `db_batch_seen_recently()` queries by address keys
- All dedup/suppression functions receive `address_key` as the `mls_number` value
- `propertyId` retained on listing dict for detail fetches only

**maintenance.py changes:**
- `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` loaded from env
- `db_fetch_status_check_queue()` now selects `gallery_image_ids` column
- `delete_cloudflare_images()` new function — deletes gallery images per listing on status change, handles 404 gracefully, never touches hero image
- `db_update_listing_status()` accepts `clear_gallery_ids` param — sets `gallery_image_ids = NULL` only after all deletions succeed
- `check_listing_status()` completely rewritten: drops id-first lookup entirely, uses address from Webflow fieldData as primary lookup via `/details/byaddress`. Property_id drift handling removed — no longer needed.
- `db_update_listing_status()` drops `new_mls_number` param
- Run summary log includes `images_deleted` count

**Supabase:**
- Migration `add_gallery_image_ids_to_published_listings` applied — `gallery_image_ids TEXT[] NULL` added to `published_listings`

**Railway:**
- `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` added to `housesunder150k-maintenance` as variable references (16 total vars)

**Webflow template:**
- `lp-gallery` DivBlock created after `lp-narrative` on Listing Template — `margin-top/bottom: 32px`
- `lp-gallery-grid` child DivBlock — `display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px`
- Collection List added inside `lp-gallery-grid`, source bound to `gallery-images` MultiImage field via MCP API + Designer
- Image element added inside Collection List item, bound to `gallery-images` CMS field (`assetId` → field ID `ffcf9ac5d5ea6fd3cea7765bf596ea1d`)
- `lp-gallery-img` style applied — `width: 100%; height: 200px; object-fit: cover; border-radius: 4px`
- Conditional visibility handled natively — Collection List renders nothing when field is empty
- Site published

**Maintenance run validated:**
- Manual trigger: `checked=43 changed=2 unchanged=41 errors=0 images_deleted=0`
- `bradford-149900` and `johnson-city-100000` correctly flagged Pending (both published same day, went under contract within 12 hours — good scoring signal)
- Property_id drift detected on winchester-129900 stained glass listing — address fallback resolved correctly
- `images_deleted=0` correct — all existing listings have null `gallery_image_ids` (pre-feature)

**ADRs added:** (to be added to `decisions/_adr.md`)
- Address key as stable dedup identifier (property_id drift confirmed in production)
- Gallery photos: indices 1-3, agent-ordered, no metadata filtering needed
- Maintenance address-first lookup — id lookup dropped entirely
- Personal search alert product parked as separate future SaaS
- Newsletter model: free, curated weekly digest, geography-segmented list as sellable asset

---

### 2026-07-28 — Session 8 + Documentation Build
**Focus:** Maintenance job + sold/pending banner (Session 8). Full documentation set build (this session).

**Session 8 outcomes:**
- `scripts/maintenance.py` written and deployed to Railway as a separate service (`housesunder150k-maintenance`)
- Cron: `0 10 * * 3,6` (Wednesday + Saturday, 10:00 UTC)
- Status mapping confirmed live: `flags.is_pending` (not `detail.status`) is reliable pending signal; `status=="sold"` reliable for sold; request failure → Expired
- Supabase migration: added `status` and `last_status_checked_at` columns to `published_listings`
- Sold/pending status banner deployed on all 4 image locations (Listing Template, Homepage cards, States Template cards, Deal of the Day hero). CMS text bound to Status field. Conditional visibility set manually in Designer.
- Property_id drift bug found and fixed: Indianapolis listing had stale `property_id`; maintenance.py now falls back to `/details/byaddress` before concluding Expired, and refreshes `mls_number` in Supabase
- Nav fixes: "Search by State" link added to Listing Template, Deal of the Day, and About pages. About page logo rebuilt. About and Deal of the Day footer text filled.
- Vault gap confirmed: `primer/_primer.md` and `build_status.md` were still stamped "Session 6 complete" at session start. Session 7 report was missing entirely.

**Documentation build outcomes (this session):**
- Full vault documentation set created following ShowFlyer/TaskView conventions
- Files created: `reference/_index.md`, `reference/_workflow.md`, `rules/_rules.md`, `schema/_schema.md`, `decisions/_adr.md`, `sessions/_session_log.md` (this file), `specs/_spec_pipeline.md`, `specs/_spec_maintenance.md`, `specs/_spec_scoring.md`, `specs/_spec_content.md`, `maintenance/_runbook.md`, `open-questions/_open_questions.md`, `security/_security.md`, `subscription/_subscription.md`
- `primer/_primer.md` updated with vault file map
- `specs/scoring-prompt-v1.md` flagged for deletion — prompt now lives in codebase

---

### 2026-07-27 — Session 7 (NO REPORT — RECONSTRUCTED SUMMARY)
**Focus:** States pages, Deal of the Day dynamic wiring, site cleanup, SEO pass.
**Note:** No session report was written to `session_reports/`. This summary reconstructed from Session 8 vault gap note and live system evidence.

**Outcomes:**
- States CMS collection created (50 items). `US State` Reference field added to Listings. All ~30 existing listings backfilled.
- States Template page built with nav/logo, dynamic H1, filtered Collection List matching homepage card styling.
- States Index page (`/states`) cleaned up — nav/footer/logo defects fixed.
- `ingest.py` updated: `STATE_TO_WEBFLOW_ITEM_ID` and `STATE_TO_SLUG` dicts wired into `write_webflow()`.
- Homepage Deal of the Day section rebuilt as dynamic Collection List (was static Wheeling WV content).
- Single-slot deal-of-the-day bug fixed: 5 listings had `deal-of-the-day = true` simultaneously. Code fix: `db_deal_of_day_chosen_today()`, `db_get_active_deal_of_day()`, `unset_deal_of_the_day()`. Supabase: `is_deal_of_day` column added to `published_listings`.
- Nav/logo/footer fixes across states index, states template, Deal of the Day page, Listings Template.
- Listing detail hero image fix: `max-width: 1200px` + `aspect-ratio: 16/9` (replaces fixed 480px height).
- Mobile nav fix: `tiny` breakpoint overrides on `lp-nav-*` classes.
- Alt text backfilled on all ~30 live listings. Wired into `ingest.py` `write_webflow()`.
- Homepage + About SEO title/description/OG image set.
- Dynamic SEO titles/descriptions via Webflow field-token syntax on States Template + Listings Template.
- Client-side JSON-LD structured data injected via site freeform footer script.
- `state-page-url` Link field added to Listings. "See More Homes in [State]" link on Listing Template.
- 50-state-domain PBN idea raised and rejected (ADR-051).
- Deal of the Day page (`/deal-of-the-day`) — confirmed built in this session (was in Session 6 pending list).

---

### 2026-07-27 — Session 6
**Focus:** Pivot from Redfin to Realtor.com, pipeline rebuild, first real listings.

**Outcomes:**
- Confirmed Redfin endpoint thin rural coverage (0 results Kentucky, 5 Nebraska). Pivoted to RealtyAPI Realtor.com endpoint.
- Rewrote `fetch_listings()`, `fetch_search_results()`, `fetch_listing_details()`, `normalize_listing()`, `extract_description()`, `extract_year_built()` for Realtor.com field structure.
- Content parser fix: strips `**bold**`, `#`, `---` from label lines.
- Empty content guard added.
- Affiliate URL changed from constructed zip search to direct `href` from API response.
- `publish_site()` called automatically after each run.
- Cron expanded to 6 runs/day.
- 1 listing per state per run added.
- Scoring model tuning: condo acreage guard, cash-only/as-is penalty, audience check.
- Removed all test/sample listings from Webflow and Supabase.
- `gallery-images` MultiImage field added to CMS (not yet wired to template).
- Filtered Latest Deals grid: excludes deal-of-the-day listings.
- Built static Deal of the Day section on homepage (Wheeling WV).
- `#deals` anchor cleared from homepage section.
- Updated affiliate URLs on existing listings to direct Realtor.com property pages.
- Manual entry process established.
- First manually entered listing: Wheeling WV castle house ($100K, score 9, Deal of the Day).
- 7 real listings published via pipeline.
- Sovrn account under review.

---

### 2026-07-26 — Session 4 — Ingestion Pipeline + Supabase
**Focus:** Write ingest.py, test end-to-end, deploy to Railway, implement Supabase dedup.

**Outcomes:**
- `scripts/ingest.py` written with full Supabase integration.
- `requirements.txt` and `Procfile` created.
- Supabase project created (`krzpkaxvbmpdeluqzkka`). Three tables via migration: `published_listings`, `seen_listings`, `pipeline_runs`.
- Railway cron: `0 13,18,23 * * *` (3 runs/day initially, expanded in Session 6).
- 10 Railway env vars confirmed.
- Scoring prompt trimmed ~65% — all rules intact, cost ~45% lower.
- All integrations confirmed working end-to-end.
- 7 test listings published and seeded into Supabase.
- Identified REPLIERS_API_KEY had leading whitespace → fixed.
- Webflow workspace token missing cms:write → switched to site-level token.
- Dedup moved from filesystem to Supabase.
- Cron overlap warning documented.

---

### 2026-07-26 — Sessions 2 & 3 — Webflow Build + Domain + Infrastructure
**Focus:** Complete Webflow site, connect domain, set up infrastructure.

**Outcomes (Session 2):**
- Homepage card styling fixed (price below image, correct colors).
- `deal-of-the-day` Switch field added to Listings CMS.
- Pages created: Deal of the Day, About, States Index.
- Deal of the Day nav tab added.
- Deal of the Day page built with full CMS bindings.
- About page built.
- States Index built with all 50 state links.
- Published to Webflow subdomain.

**Outcomes (Session 3):**
- All 50 state links styled.
- Listing Template nav updated.
- Cloudflare DNS connected. Site live at housesunder150k.com with HTTPS.
- Milwaukee listing fixed and published.
- Card link set to "Current listing" in Designer (permanent).
- First Cloudflare Images upload (Milwaukee listing hero).
- Sovrn affiliate: account under review.
- Card styling polish: visited-link color fix, font sizes, price display.
- Pre-Session 4 infrastructure: Cloudflare Images subscribed, Railway project created, GitHub connected, 7 Railway env vars set, Webflow API token generated.
- Scoring model finalized.

---

### 2026-07-25 — Session 1 — Kickoff
**Focus:** Site build, pipeline architecture, strategy documentation.

**Outcomes:**
- Webflow site built from scratch. Homepage, Listing Template, CMS schema.
- First real listing: Milwaukee $105K (brand-new construction, ECE Homeownership Initiative).
- Two-prompt pipeline architecture locked.
- Scoring tiers defined.
- Deal of the Day feature designed.
- Sold listing handling designed.
- Email subscription tiers designed (Beehiiv).
- 12-week portfolio buildout plan documented.
- Holdco + SaaS exit vision documented.
- Competitive landscape researched.
- Reference documents produced: `build_status.md`, `real-estate-content-platform-concept.md`.

---

## Pipeline Performance Reference

| Metric | Value | Notes |
|--------|-------|-------|
| Listings fetched per run | 50 | 1 per state, shuffled |
| Typical published per run | ~5 | Varies by state rotation |
| Run time | ~285-319 seconds | ~5 minutes |
| Estimated monthly API cost | ~$25-38 | Real descriptions longer than test |
| RealtyAPI requests — discovery | ~4,500/month | 50 results + 50 detail calls × 6 runs × 30 days |
| RealtyAPI requests — maintenance | ~4,300/month max | 500/run × 2 runs/week × ~4.3 weeks |
| Total RealtyAPI worst case | ~8,800/month | ~44% of 20,000/month PRO plan cap |
| Cloudflare Images per listing | 4 total | 1 hero (permanent) + 3 gallery (deleted on status change) |
