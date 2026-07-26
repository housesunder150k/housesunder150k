# HousesUnder150K — Build Status
Last updated: 2026-07-27 — Session 6 complete

---

## Site Status: LIVE ✅
**URL:** housesunder150k.com
**Listings live:** 7
**Pipeline:** Running 6x/day

---

## What's Working

| Component | Status | Notes |
|---|---|---|
| housesunder150k.com | ✅ LIVE | SSL active |
| Webflow CMS | ✅ LIVE | 7 real listings published |
| Railway pipeline | ✅ LIVE | 6 runs/day, 4-hour intervals |
| Cloudflare Images | ✅ ACTIVE | $5/mo |
| Supabase | ✅ ACTIVE | 3 tables, dedup + suppression working |
| RealtyAPI PRO | ✅ ACTIVE | $20/mo, Realtor.com endpoint |
| Scoring model | ✅ TUNED | Condo/acreage fix, as-is penalty, audience check |
| Content parser | ✅ FIXED | Strips markdown formatting from labels |
| Affiliate URLs | ✅ FIXED | Direct Realtor.com property links |
| Site auto-publish | ✅ WORKING | Runs after each pipeline publish |
| Homepage nav | ✅ UPDATED | Search by State / Deal of the Day / About / Subscribe |
| Deal of the Day section | ✅ LIVE | Static Wheeling WV — needs CMS binding |
| Latest Deals grid | ✅ FILTERED | Excludes deal-of-the-day listings |
| Sovrn | ⏳ PENDING | Approval in progress |

---

## Live Listings

| Slug | Price | Score | Tier | Notes |
|---|---|---|---|---|
| wheeling-100000 | $100,000 | 9 | HERO | Deal of the Day — manually entered |
| andover-100000 | $100,000 | 7 | FEATURED | 1890 farmhouse, 12 acres, auction |
| johnstown-82500 | $82,500 | 6 | PUBLISH | 1900 home, sauna steam shower |
| greenbrier-149900 | $149,900 | 6 | PUBLISH | 2024 new build, furnished |
| woodville-149000 | $149,000 | 6 | PUBLISH | Latest pipeline run |
| russellville-146900 | $146,900 | 6 | PUBLISH | Brick home, new HVAC, 2-car garage |
| indianapolis-145000 | $145,000 | 6 | PUBLISH | Full acre in Indianapolis |

---

## Pending Next Session (Session 7)

- [ ] Build Deal of the Day page (`/deal-of-the-day`)
- [ ] Wire gallery-images MultiImage on listing template (needs Designer)
- [ ] Fix hero image stretching on listing detail page
- [ ] Add `is_pending` check to ingest — skip pending listings
- [ ] Add gallery images to Wheeling WV listing (3 Cloudflare URLs ready)
- [ ] Build maintenance job — daily sold/pending check on published listings
- [ ] Commit all local ingest.py changes
- [ ] Remove REPLIERS_API_KEY from Railway env vars
- [ ] Sovrn approval → swap affiliate URL

---

## Pipeline Configuration

**Cron:** `0 13,17,21,1,5,9 * * *` (8am/12pm/4pm/8pm/12am/4am CT)
**Daily limit:** 10 listings/day
**State rotation:** 24 states, shuffled each run, 1 listing per state
**Score threshold:** ≥ 6 publish
**Data source:** RealtyAPI → Realtor.com (`https://realtor.realtyapi.io`)

---

## Cost Tracking (Session 6)

Estimated Claude API cost per run: ~$0.05-0.23 (varies by hit rate)
Daily estimate: ~$0.30-1.40
Monthly estimate: ~$9-42 (within $25-38 projection)
RealtyAPI credits remaining: ~19,500/20,000

---

## Removed/Cleaned Up

- All 7 Repliers test listings deleted from Webflow + Supabase
- Brooklyn Park condo ($90K, fake acreage) — deleted
- Como Mississippi ($80K, cash-only dump) — deleted
- Battle Creek pending listing — deleted
- Latest Deals nav link — removed
- `#deals` anchor from deals section — removed

---

## Architecture Decisions This Session

49. Realtor.com endpoint confirmed over Redfin (nationwide vs metro-only)
50. `searchResults` is the correct response key
51. Description at `detail.details.text`
52. Direct Realtor.com `href` as affiliate URL (not zip search)
53. 1 listing per state = geographic diversity
54. 6 runs/day at 4-hour intervals
55. Content parser strips markdown bold/hash formatting
56. Empty content guard prevents blank Webflow items
57. Full site publish hardcoded with domain IDs
58. Cron overlap dangerous — use MCP redeploy for testing only
59. gallery-images field added, template wiring deferred to Session 7
60. Latest Deals grid filtered with `deal-of-the-day isOff`
61. Deal of the Day section static until CMS binding wired
62. Manual entry process via Claude MCP connectors established
