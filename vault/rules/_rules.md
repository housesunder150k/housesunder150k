---
project: HousesUnder150K
file: rules
type: permanent — append only, never remove
last_updated: 2026-07-29
---

<!-- HousesUnder150K rules -->

# HousesUnder150K Rules

This HousesUnder150K rules document is the permanent, append-only set of non-negotiable rules governing all HousesUnder150K pipeline, editorial, and operational decisions. Rules are never removed.

<!-- HousesUnder150K rules -->

## HousesUnder150K Rules — Core Product Rule

Every decision is filtered through one question: does this listing give a reader a reason to stop scrolling? If not, it does not belong on the site.

---

<!-- HousesUnder150K rules -->

## HousesUnder150K Rules — Pipeline Rules — LOCKED

**Score threshold is 6+, not 5+.** Score ≤5 = discard. Nothing below 6 touches Webflow. No exceptions for "almost there" listings.

**Empty content guard is non-negotiable.** If HEADLINE or NARRATIVE is empty after content generation, skip the Webflow write. A blank draft item is worse than no item.

**Daily limit is a drip, not a ceiling.** `DAILY_PUBLISH_LIMIT=10` is the current setting. It is a controlled drip for quality signal, not a cap to maximize. Adjust via Railway env var without deploy.

**Cron overlap will cause duplicate writes.** Railway does not skip overlapping cron runs. Never use `*/5` in production. Use Railway MCP redeploy for manual triggers. Always wait for `=== Pipeline complete ===` before redeploying.

**1 listing per state per run.** `state_published` flag enforces geographic diversity. Do not remove this constraint without a deliberate decision.

**7-day seen suppression.** Listings scored but not published are suppressed for 7 days via `seen_listings`. This is the primary token cost saver. Do not reduce below 7 days without measuring impact on API cost.

**Listings are never deleted or unpublished.** Status changes (Pending, Sold, Expired) are communicated via the status banner and the `status` field only. SEO and backlink value is preserved permanently.

**property_id is not a stable long-term identifier.** RealtyAPI/Realtor.com can reissue a new `property_id` for the same physical listing on a data refresh. The maintenance job falls back to `/details/byaddress` before concluding Expired. Any future code keying off `property_id` long-term must account for this.

**Full site publish required after each run.** Item-level publish alone does not push to the custom domain. `publish_site()` must be called with both custom domain IDs after every run that produced new listings.

---

<!-- HousesUnder150K rules -->

## HousesUnder150K Rules — Webflow Rules — LOCKED

**Site-level API token only.** Workspace tokens do NOT have `cms:write` scope regardless of plan. The token in Railway is a site-level token from Site Settings → Integrations → API Access.

**Create elements first, bind in second pass.** Inline creation bindings fail on CMS template pages. Always create the element, then bind in a separate call.

**Switch field filter operator is `isOn` / `isOff`.** Not `equals`, not `isSet`. This is confirmed from a live API error.

**`TextBlock` + `set_text` does not apply text.** Use a `DivBlock` and set its `text` setting via `data_element_settings_tool` instead.

**Webflow's `{{wf}}` field-token syntax works via API for title/description/OG text fields.** It does NOT work for `openGraph.imageUrl` (URL validation rejects it) or JSON-LD schema markup (silently resolves to empty string — dangerous). Dynamic structured data is handled via client-side JS in the site footer code.

**Collection List source and filter can only be configured in the Designer UI.** Not settable via API.

**Conditional visibility binding to an Option field is not achievable via the Webflow MCP API surface.** Text binding to the same field works. Visibility must be set manually in the Designer.

---

<!-- HousesUnder150K rules -->

## HousesUnder150K Rules — Editorial Rules — LOCKED

**The listing is the content. The writer is the curator.** Surface the most interesting fact and get out of the way.

**Voice benchmark: Michelle Bowers, The Old House Life** (theoldhouselife.com). Conversational, not editorial. Discovery register, not journalism.

**Zero real estate language.** No "nestled," "rare find," "open concept," "move-in ready," "charming," "cozy." These are banned from all generated content.

**Zero inflation.** Honest hedging builds more trust than superlatives. If something is uncertain, say so.

**Short sentences. Specific numbers.** "6.13 acres" not "over six acres." Precision is voice.

**The agent description is raw material, never source text.** Facts are extracted and rewritten. Nothing is quoted directly.

**Category leads determine opening line:**
- What If → lead with the life detail ("Six acres and a barn in Southern Illinois. $94,000.")
- Time Machine → lead with what survived ("The original hardwood floors. Still here. 1891.")
- Too Good To Be True → lead with disbelief ("Brand new. $105,000. Milwaukee. Yes, really.")
- Hidden Gem → lead with discovery ("Not sure how this one is still available.")

---

<!-- HousesUnder150K rules -->

## HousesUnder150K Rules — Scoring Rules — LOCKED

**Manufactured/mobile/modular homes: -3.** Rarely scores above 4 regardless of other factors.

**Condo acreage guard.** If ≤2 beds and <900 sqft, nullify acreage — it is the complex parcel, not the property.

**Audience check.** Can a regular person with a conventional mortgage buy this and live in it? If no, max score = 4. Cash-only investor dumps do not belong on the site.

**As-is exception.** As-is is acceptable if the property has historic significance, acreage, waterfront, or architectural value. As-is + none of these = -2.

**is_pending listings are skipped before scoring.** A pending listing should never consume a scoring token. ⚠ This check is not yet implemented in ingest.py as of Session 8.

**Strict calibration.** Most listings should score 4 or below. A score of 6 should feel earned. When in doubt, score down. Volume can be adjusted. Quality cannot be recovered.

---

<!-- HousesUnder150K rules -->

## HousesUnder150K Rules — Monetization Rules

**Affiliate URL is the direct Realtor.com property page href** from the search result. Not a constructed URL. Not a zip search. The direct href.

**Sovrn wrapping replaces the direct Realtor.com URL** once approval comes through. The pipeline variable `SOVRN_AFFILIATE_URL` is set in Railway. Update it there, no code deploy required.

**Deal of the Day is a one-slot-per-CT-calendar-day field.** The pipeline enforces single-slot logic via `db_deal_of_day_chosen_today()` and `unset_deal_of_the_day()`. There must never be more than one listing with `deal-of-the-day = true` active at the same time.

---

<!-- HousesUnder150K rules -->

## HousesUnder150K Rules — Security Rules

Supabase RLS is currently disabled on all 3 tables (`published_listings`, `seen_listings`, `pipeline_runs`). The service role key has full read/write access. This is an open security gap. See `security/_security.md` for full context and remediation plan.

All credentials are in Railway environment variables. Never in code, never committed to the repo.
