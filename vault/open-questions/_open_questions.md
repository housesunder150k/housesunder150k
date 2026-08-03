---
project: HousesUnder150K
file: open_questions
type: unresolved decisions — move to _adr.md when resolved
last_updated: 2026-07-29
---

<!-- HousesUnder150K open_questions -->

# HousesUnder150K Open Questions

This HousesUnder150K open questions document tracks all unresolved decisions and research items for the HousesUnder150K project. Resolved items move to the HousesUnder150K ADR.

<!-- HousesUnder150K open_questions -->

## HousesUnder150K Open Questions — Format

Each item: ID, status, question, context, resolution (if closed).

---

## HousesUnder150K Open Questions — Open

**OQ-001 — Sovrn Affiliate Approval**
Status: OPEN
When Sovrn approves the Realtor.com affiliate program, the pipeline's `SOVRN_AFFILIATE_URL` Railway env var needs to be updated to the Sovrn redirect format wrapping the Realtor.com URL. No code change required — the variable is already wired. What is the Sovrn tracking URL format? Does it wrap per-click or per-listing?
Context: Sovrn account is under review (triggered by first live click on site). Commission: $5/lead, 30-day cookie.

**OQ-002 — Beehiiv Configuration**
Status: OPEN
Beehiiv has not been set up. Subscribe button on site has no backend. When this is ready:
- What are the three email tiers and their prices?
- How does Beehiiv connect to the subscribe form on the Webflow site?
- What automation handles sending Deal of the Day to all subscribers vs. featured listings to paid subscribers only?
See `subscription/_subscription.md` for full context.

**OQ-003 — gallery-images Template Wiring**
Status: OPEN
`gallery-images` MultiImage field added to Listings CMS (Session 6). Not yet displayed on the Listing Template page. Requires Designer UI work — cannot be done via API (Collection List configuration is Designer-only). How many images? What layout? When is this a priority relative to other work?

**OQ-004 — Session 7 Report Reconstruction**
Status: OPEN
Session 7 (states pages + SEO work) has no session report in `session_reports/`. A summary was reconstructed in `sessions/_session_log.md` from Session 8's vault gap note and live system evidence. Is a full reconstruction from Railway deployment history / Webflow activity worth the effort, or is the summary sufficient?

**OQ-005 — Supabase RLS Remediation Plan**
Status: OPEN
RLS is disabled on all 3 Supabase tables. Service role key has full read/write access with no policies. When remediating: policies must be added before enabling RLS, or the pipeline loses its own access. What is the risk tolerance here given this is a single-operator pipeline? See `security/_security.md`.

**OQ-006 — Dynamic OG Images**
Status: OPEN — no current API path
Per-listing and per-state Open Graph images (for social sharing previews) cannot be set dynamically via the Webflow API. `openGraph.imageUrl` has strict URL-format validation that rejects the Webflow field-token syntax. Static OG images are set on Homepage and About. All listing and state pages share those static fallbacks. Options: (a) accept static fallback for now, (b) investigate Webflow Designer-only field binding for OG image, (c) generate OG images programmatically and host on Cloudflare.

**OQ-007 — Android / Social Publishing**
Status: OPEN — not yet started
Social captions are generated for every published listing but not posted anywhere. The editorial plan calls for social reels (score 9-10), text posts (score 7-8). What platforms? What tool handles posting? Buffer, Zapier, native API? This is a revenue-driving channel not yet active.

**OQ-008 — Display Ads**
Status: OPEN — not yet started
Display ads are part of the revenue model (AdSense or similar). No ad network has been applied to. At what traffic threshold does display ad revenue become meaningful? What ad placement makes sense given the Webflow site structure?

**OQ-009 — Hero Image Stretching**
Status: OPEN — may be resolved
Hero image stretching on listing detail page at wide/ultrawide viewports was noted in Session 6 pending items. Session 7 appears to have addressed this (max-width: 1200px + aspect-ratio: 16/9 fix documented). Needs visual confirmation at wide viewport widths.

**OQ-010 — REPLIERS_API_KEY Removal**
Status: OPEN
`REPLIERS_API_KEY` is still set in Railway env vars. Unused since the pivot to RealtyAPI. Dead credential. Remove it.

---

<!-- HousesUnder150K open_questions -->

## HousesUnder150K Open Questions — Closed

**OQ-C001 — Which data source for nationwide MLS listings?**
Status: CLOSED — Session 6
Resolution: RealtyAPI (realtyapi.io) Realtor.com endpoint. PRO plan $20/mo, 20,000 requests/month. 1,969+ results per state. Repliers (original choice) required MLS license. Redfin had thin rural coverage.

**OQ-C002 — Filesystem vs. database dedup**
Status: CLOSED — Session 4
Resolution: Supabase `published_listings` table. Filesystem dedup (`posts/[slug].json`) reset on every Railway deploy — not viable for persistent state.

**OQ-C003 — Workspace token vs. site-level token for Webflow**
Status: CLOSED — Session 4
Resolution: Site-level token required. Workspace tokens do NOT have `cms:write` scope regardless of plan. Token from Site Settings → Integrations → API Access.

**OQ-C004 — Sovrn tracking model (per-listing URL vs. single URL)**
Status: CLOSED — Session 3
Resolution: Single Sovrn URL for all listings. Sovrn auto-tracks per click. No per-listing URL generation needed.

**OQ-C005 — Is `detail.status` reliable for pending detection?**
Status: CLOSED — Session 8
Resolution: No. `detail.status` stays `"for_sale"` even for pending listings. `detail.flags.is_pending == true` is the only reliable pending signal. Confirmed against 3 real pending listings in live validation.

**OQ-C006 — Is property_id a stable identifier?**
Status: CLOSED — Session 8
Resolution: No. Realtor.com can reissue a new `property_id` for the same physical listing on a data refresh. Indianapolis listing confirmed this in live validation (22116371 → 4300388528). Maintenance.py now falls back to `/details/byaddress` and refreshes `mls_number` in Supabase when drift is detected.

**OQ-C007 — Can Webflow MCP set conditional visibility binding to an Option field?**
Status: CLOSED — Session 8
Resolution: No. Tested on multiple element types (Section, DivBlock, raw DOM). All rejected with "Setting X is not applicable to this element." Text binding to the same Option field works. Visibility condition must be set manually in the Designer.

**OQ-C008 — Does the Webflow field-token syntax work in JSON-LD schema markup via API?**
Status: CLOSED — Session 7
Resolution: No. The token is accepted by the API but silently resolves to an empty string in JSON-LD context, producing malformed schema. Dangerous — do not use. Workaround: client-side JS reads already-rendered DOM values and injects correct JSON-LD at page load.
