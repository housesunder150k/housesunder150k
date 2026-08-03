---
project: HousesUnder150K
file: adr
type: permanent — append only, decisions never removed
last_updated: 2026-07-29
---

<!-- HousesUnder150K adr -->

# HousesUnder150K ADR

This HousesUnder150K ADR is the append-only record of all architecture, pipeline, and editorial decisions for the HousesUnder150K project. Decisions are never removed — append only.

<!-- HousesUnder150K adr -->

## HousesUnder150K ADR — Stack & Infrastructure — LOCKED

**ADR-001 — Webflow as CMS and site host**
Webflow Premium ($25/mo). No custom backend for the site layer. CMS-driven, auto-published. Site-level API token required — workspace tokens do not have `cms:write` scope.

**ADR-002 — Railway as pipeline host**
Hobby plan ($5/mo flat). Auto-deploys on push to main. Cron-scheduled via Railway cron syntax. Chosen over Cowork — cheaper at scale, no Claude tokens burned on scheduling.

**ADR-003 — Supabase for pipeline state**
Free tier. Three tables: `published_listings`, `seen_listings`, `pipeline_runs`. Separate Supabase account from ShowFlyer for clean separation. Free tier is sufficient — 3 small tables, low write volume, no inactivity risk at 3-6 runs/day.

**ADR-004 — Cloudflare Images for photo hosting**
Starter bundle ($5/mo). Permanent URL independence from Realtor.com CDN. Images fetched at ingest time and re-hosted. Delivery URL: `https://imagedelivery.net/{hash}/{image_id}/public`.

**ADR-005 — Cloudflare DNS**
Free tier. A record + CNAME to Webflow. TXT verification for Webflow domain ownership.

**ADR-006 — Anthropic API separate from Claude.ai Max plan**
Max plan does NOT cover API usage. Separate billing at console.anthropic.com. Pay-per-token.

**ADR-007 — Railway Hobby plan for compute**
~$0.03/mo actual compute cost. Well within $5/mo flat fee. Two services in same project: ingest + maintenance.

---

<!-- HousesUnder150K adr -->

## HousesUnder150K ADR — Data Source — LOCKED

**ADR-008 — RealtyAPI (Realtor.com endpoint) as data source**
PRO plan ($20/mo, 20,000 requests/month). 1,969+ results per state, full nationwide coverage. Repliers API was the original plan — abandoned when MLS license requirement was discovered. Redfin endpoint was tested as fallback — abandoned due to thin rural coverage (0 results in several states). RealtyAPI via Realtor.com is the only practical option at this price point.

**ADR-009 — property_id is not a stable identifier**
Realtor.com can reissue a new `property_id` for the same physical listing on a data refresh. Confirmed live (Session 8): Indianapolis listing had `property_id` drift from `22116371` to `4300388528`. Maintenance job falls back to `/details/byaddress` before concluding Expired, and refreshes `mls_number` in Supabase if the listing resolves under a new ID.

**ADR-010 — 1 listing per state per pipeline run**
`state_published` flag enforces geographic diversity. Shuffled state list ensures no state is always first. Target: 50 listings total per run across 24+ states.

**ADR-011 — Pending listings should be skipped before scoring**
`flags.is_pending == true` in search results means the listing is under contract. These should never consume a scoring token. ⚠ Not yet implemented in `ingest.py` as of Session 8.

---

<!-- HousesUnder150K adr -->

## HousesUnder150K ADR — Pipeline Architecture — LOCKED

**ADR-012 — Two-prompt pipeline**
Call 1 (scoring): lightweight gatekeeper. Input: listing data + agent description. Output: SCORE, TIER, CATEGORY, KEY_HOOKS, REASON, DEAL_OF_DAY_CANDIDATE. Call 2 (content generation): runs only for score ≥ 6. Input: listing data + CATEGORY + KEY_HOOKS from Call 1. Output: HEADLINE, NARRATIVE, SOCIAL_CAPTION, SHORT_SUMMARY.

**ADR-013 — Score threshold is 6+**
Score ≤ 5 = discard. Nothing below 6 is written to Webflow. Previous plan had 4-5 going to archive — eliminated. Thin filler pages provide no editorial value.

**ADR-014 — Scoring prompt trimmed ~65% from original**
All rules intact. Cost ~45% lower. Trimmed prompt at `specs/scoring-prompt-v1.md` (vault) and in codebase at `prompts/scoring-prompt.md`.

**ADR-015 — Empty content guard**
If HEADLINE or NARRATIVE is empty after content generation, skip the Webflow write entirely. A blank draft item is worse than no item. Root cause of blank items: Claude occasionally wraps labels in markdown formatting; fixed by content parser stripping `**bold**`, `#`, and `---` before label matching.

**ADR-016 — Supabase dedup replaces filesystem dedup**
Original plan used per-slug JSON files. Reset on every Railway deploy. Replaced with Supabase `published_listings` table for persistent dedup across deploys.

**ADR-017 — 7-day seen suppression**
`seen_listings` table. Listings scored but not published are suppressed for 7 days. Biggest single token cost saver — prevents re-scoring the same discarded listings across runs.

**ADR-018 — Daily limit via CT calendar day**
`DAILY_PUBLISH_LIMIT=10`. Resets at CT midnight (America/Chicago). Controlled drip, not bulk flood. Adjustable via Railway env var without code deploy.

**ADR-019 — 6 cron runs per day**
`0 13,17,21,1,5,9 * * *` (UTC) = 8am/1pm/6pm/8pm/midnight/4am CT. Expanded from 3 runs/day in Session 6.

**ADR-020 — Full site publish via API after each run**
Item-level publish alone only pushes to the Webflow subdomain. Full site publish with both custom domain IDs required to push to housesunder150k.com. `publish_site()` called automatically after each run that produces new listings.

**ADR-021 — Affiliate URL is direct Realtor.com href**
`listing.get("listingHref")` from search result `href` field. Not a constructed URL. Not a zip search URL. The direct property page link from the API response.

**ADR-022 — No CTA line in narrative**
Content generation prompt does not include a CTA line. The site's CTA block on the listing template handles it. Removes duplicate affiliate link in narrative.

**ADR-023 — Relative Realtor.com image paths need prefix**
Realtor.com CDN returns relative paths in some cases. Prepend `https://cdn.repliers.io/` if path does not start with `http`. (Note: this was discovered with test data; behavior may differ on live data — verify if image upload failures occur.)

---

<!-- HousesUnder150K adr -->

## HousesUnder150K ADR — Webflow Build — LOCKED

**ADR-024 — Native Webflow elements only**
No WHTML for anything requiring CMS bindings. WHTML cannot be CMS-bound. All listing template elements are native Webflow elements built via the element builder API.

**ADR-025 — Price Display as PlainText alongside Price as Number**
`price-display` ("105,000") for rendering, `price` (integer) for filtering and sorting. Separating display from data.

**ADR-026 — Location Display as PlainText with full state name**
`location-display` ("Milwaukee, Wisconsin") — always full state name, never abbreviation. `state` field carries the two-letter abbreviation for pipeline logic.

**ADR-027 — Card "Current listing" link must be set in Designer UI**
Cannot be set via MCP. One-time setup in Webflow Designer. Permanent — applies to all future listings automatically once set.

**ADR-028 — `Latest Deals` removed from nav**
Replaced by `Deal of the Day` as the primary CTA. "See Today's Deals" button on homepage links to `/deal-of-the-day`.

**ADR-029 — States pages use CMS-native Reference field architecture**
`States` CMS collection (50 items). `US State` Reference field on `Listings`. States Template page auto-generated by Webflow on collection creation. Backfilled all existing listings on creation.

**ADR-030 — State Page URL as computed Link field**
Webflow does not support binding a link href directly to a Reference field's resolved page. Worked around by adding `state-page-url` Link field to Listings, computed and written by `ingest.py` via `STATE_TO_SLUG` dict.

**ADR-031 — Dynamic SEO via Webflow field-token syntax via API**
`{{wf {"path":"name","type":"PlainText"} }}` works when set via `update_page_settings` API calls for title/description/OG text. Confirmed working on States Template and Listings Template. Does NOT work for `openGraph.imageUrl` or JSON-LD schema markup.

**ADR-032 — Dynamic JSON-LD via client-side JavaScript**
Webflow field tokens fail silently in JSON-LD context (resolve to empty string). Workaround: vanilla JS reads already-rendered CMS values from the page DOM and injects a `<script type="application/ld+json">` tag at page load. Injected via site freeform footer code. Verified working via Google's "View Tested Page" HTML tab. Does not fix OG images for non-JS social crawlers.

**ADR-033 — Sold/pending banner via CSS + CMS text binding + Designer conditional visibility**
Status banner is bottom-positioned on hero images, cyan #00D4FF, text bound to Status CMS field. Conditional visibility (show only for Pending/Sold) must be set manually in Designer — the Webflow MCP API surface does not support binding conditional visibility to an Option field. Text binding works; visibility binding does not.

**ADR-034 — Listings are never unpublished or deleted**
Status changes are communicated via the `status` field and the banner only. SEO and backlink value preserved permanently. A "This property has sold. See more deals in [State] →" experience is delivered via the banner, not a 404.

---

<!-- HousesUnder150K adr -->

## HousesUnder150K ADR — Scoring Model — LOCKED

**ADR-035 — Scoring is a routing system, not a gatekeeper**
Score routes listings to tiers. Target 8-10 published posts per day. Scoring tiers: SKIP (1-3), BELOW_THRESHOLD (4-5), PUBLISH (6), FEATURED (7-8), HERO (9-10).

**ADR-036 — Condo acreage guard**
If ≤2 beds and <900 sqft, nullify acreage score — it is the complex parcel, not the property's land.

**ADR-037 — Audience check caps investor-only properties at 4**
If a regular person with a conventional mortgage cannot buy the property and live in it, max score = 4. Cash-only auction properties, investor dumps with no habitability story — all capped.

**ADR-038 — As-is exception for character properties**
As-is is acceptable if the property has historic significance, acreage, waterfront, or architectural value. As-is + none of these = -2 penalty.

**ADR-039 — Rich agent description elevates score 0.5-1 point**
Sparse description (3 sentences or fewer, no specifics) lowers score -1. The description is the primary source of narrative quality.

---

<!-- HousesUnder150K adr -->

## HousesUnder150K ADR — Maintenance Job — LOCKED

**ADR-040 — Separate Railway service for maintenance**
`housesunder150k-maintenance` service in the same project, same repo, same branch. Own start command (`python scripts/maintenance.py`), own cron. Avoids cron-overlap risk with the discovery service.

**ADR-041 — Maintenance cron: biweekly (Wednesday + Saturday)**
`0 10 * * 3,6` (10:00 UTC). Originally Sunday-only, expanded to two runs per week. Combined RealtyAPI volume (~8,800 requests/month worst case) stays well under 20,000/month plan cap (~55% headroom).

**ADR-042 — 500 request cap per maintenance run**
`REALTYAPI_STATUS_CHECK_WEEKLY_LIMIT=500` in Railway. Rotating oldest-checked-first queue via `last_status_checked_at` (nulls first). Variable name is technically a per-run cap, not a true weekly total.

**ADR-043 — Maintenance service credentials as variable references**
All credentials in the maintenance service are set as references to the main service (`${{housesunder150k.VAR}}`), not duplicated raw values. Prevents rotation drift between the two services.

**ADR-044 — is_pending is the reliable pending signal, not detail.status**
`detail.status` stays `"for_sale"` even for pending listings. `detail.flags.is_pending == true` is the only reliable pending signal. Confirmed against 3 real pending listings.

**ADR-045 — Address fallback before concluding Expired**
A network failure or missing `detail` response does not immediately mark a listing Expired. Fallback: `/details/byaddress` lookup using address stored in Webflow. If the listing resolves under a new `property_id`, refresh `mls_number` in Supabase. If fallback also fails, leave status unchanged and recheck next rotation.

**ADR-046 — Fewer, linear functions over many small helpers**
For sequential API-orchestration logic (like the maintenance status check), prefer one orchestrating function that reads top-to-bottom plus one small reused helper. The first property_id-drift fix used 5 functions and was correctly identified as over-abstracted — collapsed to 2.

---

<!-- HousesUnder150K adr -->

## HousesUnder150K ADR — Editorial & Monetization — LOCKED

**ADR-047 — Michelle Bowers / The Old House Life as voice benchmark**
theoldhouselife.com (413,900 monthly visits). Conversational, discovery register, not journalism. The house does the work. The writer is the curator.

**ADR-048 — Deal of the Day is the anchor feature**
One listing per day — the absolute best score from that day's pipeline. Homepage hero. Social reel + text post. Email to ALL subscribers. The daily hook that drives signups. Single-slot enforced by pipeline logic.

**ADR-049 — Email subscription tiers (Beehiiv — not yet built)**
Free → Deal of the Day daily. $1/month → All listings early access. $2/month → Featured + Deal of the Day curated. Scale to $5 once list proves value.

**ADR-050 — Everything publishes to site regardless of tier**
Even score-6 listings are published to the site. The SEO and passive affiliate layer runs silently. The distinction between tiers is social and email treatment, not site presence.

**ADR-051 — 50-state-domain PBN rejected**
Building state-specific domains (westvirginiahousesunder150k.com etc.) cross-linking to the flagship is structurally equivalent to a private blog network — exactly what Google's spam systems detect. The existing `/states/[state]` pages capture the same search intent without the risk. Decision: do not pursue.

---

<!-- HousesUnder150K adr -->

## HousesUnder150K ADR — Holdco & Portfolio Strategy

**ADR-052 — HousesUnder150K.com is POC Site 1**
12-week target: 5 sites live using the same pipeline with niche configuration changes. $1,000/month from Site 1 is the only metric that matters right now.

**ADR-053 — 12-week portfolio buildout**
Week 1-2: HousesUnder150K.com (building now). Week 3-4: HousesUnder100K.com. Week 5-6: OldHousesUnder150K.com. Week 7-8: FarmhousesUnder150K.com. Week 9-10: NewHomesUnder150K.com. Week 11-12: buffer, all 5 confirmed running. Setup time decreases per site as it becomes configuration not building.
