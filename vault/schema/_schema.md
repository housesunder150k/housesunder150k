---
project: HousesUnder150K
file: schema
type: permanent — update when fields change
last_updated: 2026-07-29
---

<!-- HousesUnder150K schema -->

# HousesUnder150K Schema

This HousesUnder150K schema document is the authoritative reference for all field IDs, option IDs, table schemas, and API field maps. Load for any session touching Webflow CMS, Supabase tables, or RealtyAPI field structure.

<!-- HousesUnder150K schema -->

## HousesUnder150K Schema — Webflow CMS — Listings Collection

**Collection ID:** `6a650bab14666c3157f27618`
**fieldData uses field slugs as keys (NOT field IDs) in API writes.**

### Fields

| Field | Type | Slug | Field ID | Notes |
|-------|------|------|----------|-------|
| Name | PlainText | `name` | — | Listing headline |
| Slug | PlainText | `slug` | — | URL slug |
| Price | Number | `price` | — | Raw integer, for filtering/sorting |
| Price Display | PlainText | `price-display` | — | "105,000" — no $ symbol |
| Location Display | PlainText | `location-display` | — | "Milwaukee, Wisconsin" full state name |
| Address | PlainText | `address` | — | Street address only |
| City | PlainText | `city` | — | |
| State | PlainText | `state` | — | Two-letter abbreviation e.g. "WV" |
| Year Built | Number | `year-built` | — | |
| Bedrooms | Number | `bedrooms` | — | |
| Bathrooms | Number | `bathrooms` | — | |
| Square Feet | Number | `square-feet` | — | |
| Hero Image | Image | `hero-image` | — | Cloudflare Images URL. Format: `{"url": "...", "alt": name}` |
| Gallery Images | MultiImage | `gallery-images` | `ffcf9ac5d5ea6fd3cea7765bf596ea1d` | Added Session 6. Not yet wired to listing template. |
| Narrative Body | RichText | `narrative-body` | — | AI-generated 300-400 words. Format: `"<p>para</p><p>para</p>"` |
| Short Summary | PlainText | `short-summary` | — | Under 30 words, card preview text |
| Listing URL | Link | `listing-url` | — | Source listing URL |
| Affiliate URL | Link | `affiliate-url` | — | Direct Realtor.com property href from API |
| Social Caption | PlainText | `social-caption` | — | Under 60 words, no hashtags |
| Status | Option | `status` | `6b58bbdff6c0c0e31e17c04e4188f8be` | Active / Pending / Sold / Expired |
| Deal of the Day | Switch | `deal-of-the-day` | `3e20ffd4c8781f4b215bf2aa02b01542` | Boolean. One true at a time. |
| US State | Reference | `us-state` | `8fd6c51c4052f042dce2026efaf3f380` | Reference to States collection |
| State Page URL | Link | `state-page-url` | — | Computed by ingest.py from STATE_TO_SLUG dict |

### Status Option IDs

| Status | Option ID |
|--------|-----------|
| Active | `3b41185e9af84f92d8da092965308a2d` |
| Pending | `001257c77d3ccd4477d620ac135a4afd` |
| Sold | `541de6b6934cd79d6a76c98d91610063` |
| Expired | `e630110b6993074e3f7299e8dbb7fdc1` |

### Switch Field Filter Operators
- `isOn` / `isOff` — not `equals`, not `isSet`

### CMS Write Format (ingest.py)

```python
fieldData = {
    "name": headline,
    "slug": slug,
    "price": price_int,
    "price-display": "105,000",
    "location-display": "Milwaukee, Wisconsin",
    "address": "3125 N 24th Pl",
    "city": "Milwaukee",
    "state": "WI",
    "year-built": 2024,
    "bedrooms": 3,
    "bathrooms": 2,
    "square-feet": 1200,
    "hero-image": {"url": "https://imagedelivery.net/...", "alt": headline},
    "narrative-body": "<p>paragraph one</p><p>paragraph two</p>",
    "short-summary": "Under 30 words.",
    "listing-url": "https://realtor.com/...",
    "affiliate-url": "https://realtor.com/...",  # direct href from API
    "social-caption": "Under 60 words.",
    "status": "3b41185e9af84f92d8da092965308a2d",  # Active option ID
    "deal-of-the-day": False,
    "us-state": "WEBFLOW_ITEM_ID_FOR_STATE",  # from STATE_TO_WEBFLOW_ITEM_ID dict
    "state-page-url": "https://www.housesunder150k.com/states/west-virginia",
}
```

### Publish Calls

```
# Item-level (staging push)
POST https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}/live

# Full site (custom domain push — required after each run)
POST https://api.webflow.com/v2/sites/6a650a7eb2639262c4b6adb7/publish
body: {"customDomains": ["6a661987994ab168be06566b", "6a661986994ab168be065664"]}
```

---

<!-- HousesUnder150K schema -->

## HousesUnder150K Schema — Webflow CMS — States Collection

**Collection ID:** `6a67c480dba86ce339bab621`
**Item template page ID:** `6a67c480dba86ce339bab6bb`

| Field | Type | Slug | Notes |
|-------|------|------|-------|
| Name | PlainText | `name` | Full state name e.g. "West Virginia" |
| Slug | PlainText | `slug` | e.g. "west-virginia" |
| Abbreviation | PlainText | `abbreviation` | Two-letter e.g. "WV" |

50 items seeded. The `us-state` Reference field on Listings points to this collection.

---

<!-- HousesUnder150K schema -->

## HousesUnder150K Schema — Supabase — Tables

**Project URL:** `https://krzpkaxvbmpdeluqzkka.supabase.co`
**mls_number field stores Realtor.com `property_id`** (not a true MLS number)

### published_listings

Primary dedup table and daily CT publish counter.

```sql
slug                    TEXT PRIMARY KEY
mls_number              TEXT NOT NULL          -- stores Realtor.com property_id
webflow_item_id         TEXT NOT NULL
score                   INTEGER NOT NULL
tier                    TEXT NOT NULL
category                TEXT
headline                TEXT
hero_image_url          TEXT
published_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
published_date_ct       DATE NOT NULL          -- CT calendar day, resets at CT midnight
status                  TEXT NOT NULL DEFAULT 'Active'  -- mirrors Webflow Status field
last_status_checked_at  TIMESTAMPTZ NULL       -- updated every maintenance run
is_deal_of_day          BOOLEAN NOT NULL DEFAULT FALSE
```

Indexes: `published_date_ct`, `mls_number`, `(status, last_status_checked_at)`

### seen_listings

7-day suppression. Prevents re-scoring listings that were already evaluated.

```sql
mls_number      TEXT PRIMARY KEY
slug            TEXT
score           INTEGER NOT NULL
tier            TEXT NOT NULL
first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
times_seen      INTEGER NOT NULL DEFAULT 1
```

Index: `last_seen_at`

### pipeline_runs

Per-run cost and performance tracking.

```sql
id                  SERIAL PRIMARY KEY
started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
completed_at        TIMESTAMPTZ
listings_fetched    INTEGER DEFAULT 0
listings_scored     INTEGER DEFAULT 0
listings_skipped    INTEGER DEFAULT 0
published           INTEGER DEFAULT 0
errors              INTEGER DEFAULT 0
tokens_scoring      INTEGER DEFAULT 0
tokens_content      INTEGER DEFAULT 0
est_cost_usd        NUMERIC(10,5) DEFAULT 0
daily_limit_hit     BOOLEAN DEFAULT FALSE
notes               TEXT
```

---

<!-- HousesUnder150K schema -->

## HousesUnder150K Schema — RealtyAPI — Field Map

**Base URL:** `https://realtor.realtyapi.io`
**Railway env var:** `REALTYAPI_KEY`

### Search Endpoint

```
GET /search/bylocation
params:
  location: "Kentucky"          # state name
  priceRange: "max:150000"
  searchType: "For_Sale"
  propertyType: "House,Townhome"
  sortOrder: "Newest"
  hasPhotos: true
  seniorCommunity: false
  resultCount: 50
```

**Response key:** `searchResults[]`

| Field | Path | Notes |
|-------|------|-------|
| Property ID | `property_id` | Stored as mls_number in Supabase. NOT stable long-term — can be reissued. |
| Listing ID | `listing_id` | |
| Price | `list_price` | |
| Beds | `beds` | |
| Baths | `baths` | |
| Sqft | `sqft` | |
| Lot Sqft | `lot_sqft` | |
| Street | `address.line` | |
| City | `address.city` | |
| State | `address.state_code` | Two-letter |
| Zip | `address.postal_code` | |
| Primary Photo | `primary_photo` | String URL |
| Photos | `photos[]` | Array of string URLs |
| Listing URL | `href` | Direct Realtor.com property page — used as affiliate_url |
| Is Pending | `flags.is_pending` | Boolean — skip in ingest if true ⚠ not yet implemented |

### Detail Endpoint

```
GET /details/byid?property_id=X
```

**Response root:** `detail`

| Field | Path | Notes |
|-------|------|-------|
| Description | `detail.details.text` | Agent description — primary narrative source |
| Year Built | `detail.details.year_built` | |
| Status | `detail.status` | "for_sale" stays even for pending listings |
| Is Pending | `detail.flags.is_pending` | Reliable pending signal |
| Is Sold | `detail.status == "sold"` | Reliable sold signal |

**⚠ Status mapping confirmed live (Session 8):**
- `flags.is_pending == true` → Pending (NOT `detail.status`)
- `detail.status == "sold"` → Sold
- Request error / no `detail` key → Expired
- else → Active (no change)

### Address Fallback Endpoint

```
GET /details/byaddress?address=X&city=Y&state=Z
```

Used by maintenance.py when `property_id` lookup fails (property_id drift). If address resolves, refresh `mls_number` in Supabase with the new `property_id`.

---

<!-- HousesUnder150K schema -->

## HousesUnder150K Schema — Cloudflare Images

**Account ID:** `af60f586464675e914119c0743898631`
**Account Hash:** `VbqNe4WDJ-oPFPFAkDRv_w`
**Delivery URL pattern:** `https://imagedelivery.net/VbqNe4WDJ-oPFPFAkDRv_w/{image_id}/public`

```
POST https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1
Authorization: Bearer {CLOUDFLARE_API_TOKEN}
Content-Type: multipart/form-data
body: file bytes
```

Images are fetched from Realtor.com CDN and re-hosted on Cloudflare for permanent URL independence.

---

## HousesUnder150K Schema — Anthropic API

**Model:** `claude-sonnet-4-6`
**Max tokens:** 1000 per call
**Endpoint:** `https://api.anthropic.com/v1/messages`

| Call | Avg Input Tokens | Avg Output Tokens | Avg Cost |
|------|-----------------|-------------------|----------|
| Scoring (trimmed prompt) | ~990–1,180 | ~100–160 | ~$0.005 |
| Content generation | ~970–1,130 | ~410–480 | ~$0.010 |

**Estimated monthly API cost:** ~$25-38/month (real descriptions are longer than test data)
