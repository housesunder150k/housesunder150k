---
project: HousesUnder150K
file: spec_scoring
type: living — update when scoring model changes
last_updated: 2026-07-29
prompt_location: scripts/prompts/scoring-prompt.md (codebase)
---

<!-- HousesUnder150K spec_scoring -->

# HousesUnder150K — Scoring Spec

This HousesUnder150K scoring spec defines the scoring model (Claude Call 1) that routes all fetched listings to a publish tier or discard. Load for any session touching scoring calibration, tier thresholds, or the scoring prompt.

<!-- HousesUnder150K spec_scoring -->

## HousesUnder150K Scoring Spec — Overview

The scoring model is Claude Call 1 in the two-prompt pipeline. It evaluates every fetched listing and routes it to a publish tier or discard. The prompt lives in the codebase at `scripts/prompts/scoring-prompt.md`. This document explains the model's intent, calibration, tuning history, and known edge cases.

**Goal:** Route 8-10 listings per day to the site. Most listings should score 4 or below. A score of 6 should feel earned. Quality cannot be recovered — when in doubt, score down.

---

## HousesUnder150K Scoring Spec — Score Bands and Tiers

| Score | Tier | Action |
|-------|------|--------|
| 1-3 | SKIP | Discard. Not written anywhere. |
| 4-5 | BELOW_THRESHOLD | Discard. Not written anywhere. |
| 6 | PUBLISH | Published to site. No social, no email. |
| 7-8 | FEATURED | Published + social text post + email to paid subscribers. |
| 9-10 | HERO | Published + social reel + email ALL subscribers. Deal of the Day candidate. |

**Previous plan (Sessions 1-3):** Scores 4-5 went to an archive — published but not featured. Eliminated in Session 4. Thin filler pages provide no editorial value and dilute the site's signal.

---

<!-- HousesUnder150K spec_scoring -->

## HousesUnder150K Scoring Spec — Automatic 6+ Floor

If ANY of the following are present, the listing automatically scores at least 6 regardless of other factors:

- Waterfront (lake, river, pond, ocean, creek)
- Lake view or mountain view
- Acreage ≥ 0.5 acres (1+ acre is stronger)
- In-ground pool
- Wooded lot / heavily treed
- New construction (current year or last 2 years)
- Historic home (pre-1950 with character details mentioned)

These are non-negotiable floors. A manufactured home with lake frontage still gets the waterfront floor — then the -3 manufactured home penalty applies, netting ~3. The floor and penalties stack independently.

---

## HousesUnder150K Scoring Spec — Additive Qualifiers

Listings without an automatic floor must accumulate qualifiers to reach 6. Qualifiers are additive — more qualifiers = higher score.

**Condition & Updates** (each one present adds to score):
- Recent renovation — kitchen, bathrooms, whole home (within 10 years, year preferred)
- Major system update — roof, HVAC, windows, plumbing, electrical (year preferred)
- Move-in ready with specifics to support the claim

**Size & Space:**
- Sqft 800-1,100: neutral. 1,100-1,400: mild positive. 1,400-1,800: positive. 1,800+: strong positive.
- Bedrooms: 1-2 neutral/slight negative. 3 baseline. 4 positive. 5+ strong positive.
- Large yard, fenced, oversized lot, corner lot with space
- Garage (attached or detached)
- Outbuildings, barn, workshop, shed

**Character & Uniqueness:**
- Historical significance, registry listing, notable age with details
- Stained glass, original millwork, exposed beams, tin ceilings, hardwood throughout, wraparound porch, clawfoot tub, built-ins, wainscoting, fireplace (wood-burning preferred)
- Unusual property type for the price point
- Finished basement

**Location & Community:**
- Great schools or named school district
- Walkable location with named amenities
- Named nearby features (trail, state park, lake, downtown)
- Small charming town with community feel
- Low cost of living area

**Deal Signals:**
- Price reduction (lastPriceChangeType = decrease)
- High days on market with low price (motivated seller)
- Exceptionally low price per square foot for the market
- Bank owned / estate sale / motivated seller stated

**Description Quality:**
- Rich description with specific details, named features, local context: +0.5 to +1
- Sparse description (3 sentences or fewer, no specifics): -1

---

<!-- HousesUnder150K spec_scoring -->

## HousesUnder150K Scoring Spec — Negative Modifiers

| Condition | Modifier |
|-----------|----------|
| Manufactured / mobile / modular home | -3 |
| Condo in multi-family complex (acreage is complex parcel) | -2 |
| Cash-only / as-is AND no automatic floor qualifier | -2 |
| Needs significant work, no renovation history | -1 |
| No photos | -1 |
| Under 700 sqft | -1 |
| Under 800 sqft | -0.5 |
| Sparse description | -1 |
| Condo with high HOA fees mentioned | -0.5 |
| Location with no distinguishing features | -0.5 |

---

## HousesUnder150K Scoring Spec — Special Rules

### Condo Acreage Guard
If ≤2 beds AND <900 sqft: nullify acreage. The listed lot size is the complex parcel, not the property's land. Do not count acreage toward the automatic floor or additive qualifiers for these listings.

### Audience Check
Can a regular person with a conventional mortgage buy this property and actually live in it? If no — auction-only, cash-only investor dump, uninhabitable condition with no character story — maximum score is 4 regardless of other factors.

### As-Is Exception
As-is is acceptable if the property has historic significance, acreage, waterfront, or architectural value. The assumption is that a motivated buyer can take on the work for the right property. As-is + none of these = -2 penalty.

### Rich Description Boost
A rich, detailed agent description with specific named features, local context, and personality elevates a borderline listing 0.5-1 point. This reflects editorial reality: the description is the primary source of narrative quality. A listing that can't generate a compelling post at content generation time is less valuable even if the specs are good.

---

<!-- HousesUnder150K spec_scoring -->

## HousesUnder150K Scoring Spec — Output Format

The scoring prompt returns structured output parsed by `ingest.py`. The content parser strips markdown formatting (`**bold**`, `#`, `---`) before matching.

```
SCORE: [1-10]
TIER: [SKIP / BELOW_THRESHOLD / PUBLISH / FEATURED / HERO]
CATEGORY: [category slug]
KEY_HOOKS: [2-4 specific compelling facts, comma-separated]
REASON: [1-2 sentences]
DEAL_OF_DAY_CANDIDATE: [YES / NO]
```

**KEY_HOOKS are passed directly to the content generation prompt.** They must be specific and usable — not generic ("nice house, good price") but concrete ("1891 Victorian with original tin ceilings and clawfoot tub, 0.8 acres, $87,000 in rural Kentucky"). Quality KEY_HOOKS are the primary driver of narrative quality in Call 2.

---

## HousesUnder150K Scoring Spec — Categories

| Category | When to Use |
|----------|-------------|
| NEW_CONSTRUCTION | Built current year or last 2 years |
| WATERFRONT | Any water frontage or water view |
| ACREAGE | Primary appeal is land / lot size |
| HISTORIC | Pre-1950 with notable character details |
| RENOVATED | Recently updated, key systems replaced |
| CHARACTER | Unique architectural features, charm, specific details |
| HIDDEN_GEM | Undervalued location, surprisingly good value for market |
| TOO_GOOD_TO_BE_TRUE | Price seems impossibly low for what's offered — use sparingly |
| WHAT_IF | Acreage/land with development or lifestyle potential |

---

<!-- HousesUnder150K spec_scoring -->

## HousesUnder150K Scoring Spec — Tuning History

### Session 1 (v1.0 — Original)
Initial scoring model. 10 bands. Scoring tiers included Archive (4-5) as a publish destination.

### Session 2-3 (v1.0)
Archive tier eliminated. Score threshold raised to 6+. Model calibration unchanged.

### Session 4 (v1.1 — Trimmed)
Scoring prompt trimmed ~65% from original. All rules intact, cost ~45% lower (~$0.005/call vs. ~$0.009/call). Confirmed no quality degradation in test runs.

### Session 6 (v1.2 — RealtyAPI Calibration)
Three tuning changes for Realtor.com data patterns:
1. **Condo acreage guard** — added after Brooklyn Park MN condo was incorrectly scored high for lot size (complex parcel)
2. **Cash-only/as-is audience check** — added after Como MS listing (investor dump, no story) was incorrectly scored publishable
3. **Audience check max score = 4** — formalized after multiple investor-only listings scored too high

---

## HousesUnder150K Scoring Spec — Calibration Notes

**Volume check:** If published listings per day is consistently below 5, the scoring may be too strict for the available inventory. Adjust by loosening one or two negative modifier thresholds. Do not lower the score threshold below 6.

**Volume check:** If published listings per day is consistently above 12, the scoring may be too loose. Tighten by raising the bar on what qualifies as "recent renovation" or adding geography-specific adjustments.

**Real descriptions are longer than test data.** Test runs used thin Repliers/test API descriptions. Live Realtor.com descriptions are richer, which elevates more listings via the description quality bonus.

**Geographic mix:** The 1-per-state constraint prevents any single high-inventory state from dominating. If quality is consistently low from certain states, consider whether the state list needs pruning or whether state-specific scoring adjustments are warranted.

---

<!-- HousesUnder150K spec_scoring -->

## HousesUnder150K Scoring Spec — Known Edge Cases

- **New construction in suburban subdivisions:** Technically hits the new construction floor but has no editorial story. The audience check and sparse description penalty should catch these, but monitor for 1980s-2000s cookie-cutter homes slipping through at score 6.
- **Auction properties:** Often have compelling specs but cash-only/unconventional purchase requirements. Audience check should cap these at 4. Verify the check is working if auction properties appear on the site.
- **Property_id drift in scoring data:** `mls_number` stored in `seen_listings` is the `property_id` from the search result. If a property_id drifts between runs, a re-listed property may pass the 7-day suppression check as if it's new. Acceptable behavior — the listing would be re-scored, and the dedup check on slug would catch it if it's already published.
