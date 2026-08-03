# Social Media Pipeline — HousesUnder150K.com
**Status:** In progress — Supabase table created, awaiting Meta and third-party service setup.

---

## Overview

A fully autonomous social media posting pipeline that runs alongside the existing ingestion pipeline. When a listing is published to the website, it is automatically queued for social posting on Facebook and Instagram. A separate posting service runs every 30 minutes and dispatches posts on a fixed daily schedule — 10 standard photo posts per day plus 2 Reels.

No manual intervention required after initial setup.

---

## Architecture

```
Ingestion Pipeline (existing)
        ↓ on successful publish
  social_queue table (Supabase)
        ↓ every 30 minutes
  Social Poster Service (Railway)
        ↓ standard posts              ↓ reels
    Ayrshare API              JSON2Video → Ayrshare API
        ↓                                    ↓
Facebook + Instagram              Facebook + Instagram
```

---

## Posting Schedule (Central Time)

| Time   | Type     | Source                              |
|--------|----------|-------------------------------------|
| 8:00 AM  | Standard | Listing 1                         |
| 10:00 AM | Reel     | Deal of the Day                   |
| 12:00 PM | Standard | Listing 2                         |
| 2:00 PM  | Reel     | Highest-scored listing (non-DoD)  |
| 4:00 PM  | Standard | Listing 3                         |
| 6:00 PM  | Standard | Listing 4                         |
| 8:00 PM  | Standard | Listing 5                         |
| 10:00 PM | Standard | Listing 6                         |
| 12:00 AM | Standard | Listing 7                         |
| 2:00 AM  | Standard | Listing 8                         |

Standard slots after listing 8 continue the pattern if more than 8 listings publish that day (max 10/day). The 10am and 2pm slots are always reserved for Reels and are never used for standard posts.

---

## Products

### 1. Meta Business Suite (Free)
**What it does:** The foundation for both Facebook and Instagram API access. Without a Meta Business Page and Developer App, no automated posting is possible.

**What you need to set up:**
- A Facebook Business Page (not a personal profile — the Graph API does not work with personal profiles)
- An Instagram Professional account (Business or Creator) connected to the Facebook Page
- A Meta Developer App at developers.facebook.com with the `pages_manage_posts`, `instagram_basic`, and `instagram_content_publish` permissions
- A long-lived Page Access Token (valid for 60 days, needs periodic refresh or a system user token for permanent access)
- Your Facebook Page ID
- Your Instagram Business Account ID

**How to get started:**
1. Go to facebook.com/pages/create and create a Business Page
2. Go to instagram.com, convert your account to a Professional account, and link it to your Facebook Page under Settings → Linked Accounts
3. Go to developers.facebook.com → My Apps → Create App → Business type
4. Add the Instagram Graph API and Pages API products to your app
5. Use the Graph API Explorer to generate a Page Access Token with the required permissions
6. Exchange it for a long-lived token (valid 60 days) via the token exchange endpoint
7. Store the token, Page ID, and Instagram Business Account ID as Railway environment variables

**Instagram post behavior:** Instagram does not allow clickable links in post captions. All Instagram posts drive traffic via the bio link. The bio link should point to `housesunder150k.com/states` or a dedicated `/latest` page. Paid promotion ($10/week boosted posts) handles direct listing traffic from Instagram.

---

### 2. Ayrshare (~$29/month)
**What it does:** A social media API aggregator that sits on top of the Meta Graph API and simplifies posting to Facebook and Instagram in a single API call. Handles the complexity of Reels uploads, async processing, and platform-specific formatting differences. Absorbs Meta API changes so the pipeline doesn't break when Meta updates their endpoints.

**Why not use the Meta Graph API directly:** Reels require a multi-step async upload process (upload video → wait for processing → publish) that is fragile and changes frequently. Ayrshare abstracts all of this into one call.

**What you need to set up:**
1. Sign up at ayrshare.com
2. Connect your Facebook Page and Instagram Professional account via their dashboard
3. Get your API key from the dashboard
4. Store as `AYRSHARE_API_KEY` in Railway environment variables

**How it's used in the pipeline:**
- Standard posts: one API call with `mediaUrls` (hero image), `post` (caption), and `platforms: ["facebook", "instagram"]`
- Reels: one API call with `mediaUrls` (video URL from JSON2Video), `post` (caption), `platforms: ["facebook", "instagram"]`, and `isReel: true`

**Standard post caption format (Facebook):**
```
{headline}

{social_caption}

See full listing → {listing_url}

#HousesUnder150K #AffordableHomes #RealEstate #{State}
```

**Instagram caption format** (no link, drives to bio):
```
{headline}

{social_caption}

Link in bio to see the full listing.

#HousesUnder150K #AffordableHomes #RealEstate #{State}
```

---

### 3. JSON2Video (pricing TBD — evaluate Essential vs Growth plan)
**What it does:** A video generation API that takes a JSON payload of images, text, and audio configuration and renders an MP4 video. Used exclusively for the 2 daily Reels. TTS voiceover (from the listing's `social_caption` field) is included in the rendering credits — no separate ElevenLabs account needed unless a specific voice is required.

**Why JSON2Video over Creatomate:** JSON2Video includes TTS voiceover in the same credit pool as rendering. Creatomate charges extra credits for TTS on top of render credits, which at 60 Reels/month creates meaningful additional cost.

**What you need to set up:**
1. Sign up at json2video.com
2. Get your API key
3. Store as `JSON2VIDEO_API_KEY` in Railway environment variables
4. Design the Reel template once in their visual editor (see template spec below)

**Reel template spec:**
- Resolution: 1080×1920 (9:16 vertical — required for Instagram and Facebook Reels)
- Duration: ~30 seconds
- 4 scenes:
  - Scene 1 (8s): Hero image with Ken Burns zoom, headline text overlay top, HousesUnder150K.com watermark bottom
  - Scene 2 (7s): Gallery photo 1, price overlay bottom right
  - Scene 3 (7s): Gallery photo 2, location overlay bottom left
  - Scene 4 (8s): Gallery photo 3 or hero image repeat, CTA text "See this listing at HousesUnder150K.com"
- TTS voiceover: runs across all scenes, sourced from `social_caption` field (~50 words, ~25 seconds of audio)
- Background music: optional low-volume ambient track (Creatomate and JSON2Video both have royalty-free libraries)
- Variables (populated per listing): `headline`, `social_caption`, `hero_image_url`, `gallery_1`, `gallery_2`, `gallery_3`, `price_display`, `location_display`

**How it's used in the pipeline:**
The social poster service calls JSON2Video with the template ID and listing variables, receives a job ID, polls until the render is complete (typically 60–120 seconds), retrieves the video URL, then passes it to Ayrshare for posting.

---

### 4. Supabase — `social_queue` table (already set up)
**What it does:** Acts as the scheduling layer between the ingestion pipeline and the social poster. The ingestion pipeline writes to this table after each successful Webflow publish. The social poster reads from it every 30 minutes.

**Table:** `social_queue`

| Column | Type | Description |
|--------|------|-------------|
| id | bigserial | Primary key |
| listing_slug | text | e.g. `detroit-150000` |
| listing_url | text | Full URL on housesunder150k.com |
| headline | text | SEO-friendly listing title |
| narrative | text | Full listing description |
| hero_image_url | text | Cloudflare image URL |
| gallery_image_urls | text[] | Up to 3 gallery image URLs |
| social_caption | text | Under 60 words, written by Claude |
| price_display | text | e.g. `150,000` |
| location_display | text | e.g. `Detroit, Michigan` |
| post_type | text | `standard` or `reel` |
| platform | text | `both` (always) |
| scheduled_for | timestamptz | UTC datetime for posting |
| status | text | `pending`, `posted`, `failed`, `skipped` |
| ayrshare_post_id | text | Returned by Ayrshare on success |
| json2video_job_id | text | Returned when reel render is triggered |
| video_url | text | Populated when render completes |
| posted_at | timestamptz | Actual post time |
| error_message | text | Populated on failure |
| score | integer | Editorial score from Claude |
| is_deal_of_day | boolean | Whether this listing is the Deal of the Day |
| created_at | timestamptz | Row creation time |

---

### 5. Railway — `social-poster` service (new)
**What it does:** A new Railway service running `social_poster.py` on a cron schedule every 30 minutes. Separate from the ingestion pipeline service so the two can fail independently.

**Cron:** `*/30 * * * *`

**Logic per run:**
1. Query `social_queue` for rows where `scheduled_for <= now()` and `status = pending`
2. For each row:
   - If `post_type = standard`: post via Ayrshare immediately, mark as `posted`
   - If `post_type = reel` and `json2video_job_id` is null: trigger JSON2Video render, store job ID, mark status as `pending` (will be picked up next run)
   - If `post_type = reel` and `json2video_job_id` is set: poll JSON2Video for completion, if ready post via Ayrshare and mark `posted`, if not ready leave as `pending`
3. Log all results to Railway

**Environment variables needed:**
```
AYRSHARE_API_KEY
JSON2VIDEO_API_KEY
JSON2VIDEO_TEMPLATE_ID_REEL
SUPABASE_URL           (same as ingestion pipeline)
SUPABASE_KEY           (same as ingestion pipeline)
```

---

## Changes to `ingest.py`

After a successful `publish_webflow()` call, two functions are added:

**`schedule_standard_post(listing, content, hero_image_url, gallery_image_urls, score, today_ct)`**
- Claims the next available standard slot from the fixed daily schedule
- Skips 10am and 2pm (reserved for Reels)
- Writes one row to `social_queue` with `post_type = standard`

**`schedule_reel(listing, content, hero_image_url, gallery_image_urls, score, is_deal_of_day, today_ct)`**
- Called for Deal of the Day listings (10am slot) and the highest-scored non-DoD listing (2pm slot)
- Only one reel per slot per day — if slot is already taken, skips
- Writes one row to `social_queue` with `post_type = reel`

---

## Slot assignment logic

Fixed daily slots in CT, stored as hour values:

```python
STANDARD_SLOTS_CT = [8, 12, 16, 18, 20, 22, 0, 2]   # 8am, 12pm, 4pm, 6pm, 8pm, 10pm, 12am, 2am
REEL_SLOTS_CT     = {10: 'deal_of_day', 14: 'top_listing'}  # 10am DoD, 2pm top listing
```

When a listing publishes, the slot assigner:
1. Queries `social_queue` for slots already claimed today
2. Picks the first unclaimed standard slot
3. Converts to UTC and writes to the queue
4. If the listing is Deal of the Day, also claims the 10am Reel slot
5. If the listing has the highest score of the day and isn't DoD, claims the 2pm Reel slot (checked at end of run)

---

## Setup Checklist

- [ ] Create Facebook Business Page
- [ ] Connect Instagram Professional account to Facebook Page
- [ ] Create Meta Developer App at developers.facebook.com
- [ ] Add Instagram Graph API and Pages API products to the app
- [ ] Generate long-lived Page Access Token with required permissions
- [ ] Note down: Facebook Page ID, Instagram Business Account ID
- [ ] Sign up for Ayrshare, connect Facebook and Instagram, get API key
- [ ] Sign up for JSON2Video, get API key
- [ ] Design Reel template in JSON2Video visual editor, note down Template ID
- [ ] Add all new environment variables to Railway
- [ ] Create `social-poster` Railway service pointing at `social_poster.py`
- [ ] Set cron to `*/30 * * * *`
- [ ] Write and deploy `social_poster.py`
- [ ] Write and deploy `schedule_social_posts()` additions to `ingest.py`
- [ ] Test with a single manual queue entry before going live

---

## Cost Summary (at full scale)

| Service | Cost |
|---------|------|
| Ayrshare | ~$29/month |
| JSON2Video | ~$41–54/month (Essential plan, ~60 Reels/month) |
| Meta Business Suite | Free |
| Railway (new service) | Minimal — runs every 30 min, very lightweight |
| **Total addition** | **~$70–83/month** |

Combined with existing pipeline costs (~$65/month), total stack at full scale: **~$135–148/month**.
