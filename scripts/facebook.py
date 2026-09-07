"""
HousesUnder150K.com — Facebook Publisher
Runs 7 days/week on Railway cron:
  Run 1: 0 16 * * *  (11am CT / 4pm UTC)
  Run 2: 0 23 * * *  (6pm CT / 11pm UTC)

Schedule logic:
  Both runs post listing posts only (no article posts on Facebook).
  Pulls from published_listings where fb_ig_approved_facebook = true,
  deduplicates via social_posts table.

Post structure:
  - Image: hero_image_url (Cloudflare-hosted)
  - Caption: 3-line brand voice — hook / color / URL
  - Scheduled via Buffer customScheduled mode

Timing:
  Script randomizes within a 90-minute window around the cron time to
  avoid predictable posting patterns. 11am run: 11:00am-12:30pm CT.
  6pm run: 6:00pm-7:30pm CT.

Buffer API:
  - GraphQL at https://api.buffer.com
  - createPost mutation with customScheduled mode and dueAt (UTC ISO 8601)
  - assets[0].image.url for the hero image

Dry run:
  - python facebook.py --dry-run
  - Fetches and generates post, prints output. Does NOT call Buffer.

Environment variables required:
  BUFFER_API_KEY               — Buffer API key
  BUFFER_FACEBOOK_CHANNEL_ID   — Buffer Facebook Page channel ID (6a974ae7065799be466cdc8e)
  ANTHROPIC_API_KEY            — for caption generation
  SUPABASE_URL                 — HousesUnder150K Supabase project URL
  SUPABASE_KEY                 — Supabase service role key

Approval pool:
  Listings must have fb_ig_approved_facebook = true to enter the pool.
  Set via the approval web app. fb_ig_skipped = true listings are never shown.
  Each listing is posted once per platform — deduplication via social_posts.

Changes:
  2026-09-07: Initial implementation — adapted from pinterest.py
"""

import os
import sys
import logging
import random
import argparse
from datetime import datetime, timedelta

import requests
import pytz

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BUFFER_API_KEY     = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID  = os.environ["BUFFER_FACEBOOK_CHANNEL_ID"]   # 6a9ef63ecd8b9c702c23ead7 (HousesUnder150K Page)
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
SUPABASE_URL       = os.environ["SUPABASE_URL"]
SUPABASE_KEY       = os.environ["SUPABASE_KEY"]

SITE_BASE_URL  = "https://housesunder150k.com"
BUFFER_API_URL = "https://api.buffer.com"

CLAUDE_MODEL      = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 150   # 3-line Facebook caption — tight by design

CT_TZ = pytz.timezone("America/Chicago")

# Posting window: 7am-10pm CT, random time within that window regardless of cron fire time
POST_WINDOW_START_HOUR = 7   # 7am CT
POST_WINDOW_END_HOUR   = 22  # 10pm CT

# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------

def load_prompt(filename: str) -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", filename)
    with open(prompt_path, "r") as f:
        return f.read()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_now_ct() -> datetime:
    return datetime.now(CT_TZ)


def random_post_time_utc() -> datetime:
    """
    Pick a random time within the 7am-10pm CT window.
    If the current CT time is already past 10pm, schedule for tomorrow's window.
    Always schedules at least 5 minutes in the future.
    """
    now_ct = get_now_ct()
    today = now_ct.date()

    # Build the window for today
    window_start = CT_TZ.localize(datetime(today.year, today.month, today.day, POST_WINDOW_START_HOUR, 0))
    window_end   = CT_TZ.localize(datetime(today.year, today.month, today.day, POST_WINDOW_END_HOUR, 0))

    # If we're past the end of today's window, use tomorrow
    if now_ct >= window_end:
        tomorrow = today + timedelta(days=1)
        window_start = CT_TZ.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, POST_WINDOW_START_HOUR, 0))
        window_end   = CT_TZ.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, POST_WINDOW_END_HOUR, 0))
        log.info(f"Past 10pm CT — scheduling in tomorrow's window")

    # If we're before the window start (e.g. cron fired at 2am), use today's window
    # If we're inside the window, pick randomly from now+5min to window end
    earliest = max(window_start, now_ct + timedelta(minutes=5))

    # Convert to timestamps for randint
    earliest_ts = int(earliest.timestamp())
    latest_ts   = int(window_end.timestamp())

    if earliest_ts >= latest_ts:
        # Window is too tight — schedule at earliest
        scheduled_ct = earliest
    else:
        scheduled_ts = random.randint(earliest_ts, latest_ts)
        scheduled_ct = datetime.fromtimestamp(scheduled_ts, tz=CT_TZ)

    scheduled_utc = scheduled_ct.astimezone(pytz.utc)
    log.info(f"Scheduled post time: {scheduled_ct.strftime('%H:%M CT')} / {scheduled_utc.strftime('%H:%M UTC')}")
    return scheduled_utc

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def get_posted_slugs(platform: str) -> set[str]:
    """Return slugs already posted to this platform."""
    url = f"{SUPABASE_URL}/rest/v1/social_posts"
    params = {
        "select": "source_id",
        "platform": f"eq.{platform}",
        "post_type": "eq.listing",
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return {row["source_id"] for row in r.json()}
    except Exception as e:
        log.error(f"Supabase get_posted_slugs error: {e}")
        return set()


def get_next_approved_listing(posted_slugs: set[str]) -> dict | None:
    """
    Fetch the highest-scored approved Facebook listing not yet posted.
    Orders by score DESC, then published_at DESC as tiebreaker.
    """
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug,headline,short_summary,social_caption,price,city,state,category,hero_image_url",
        "fb_ig_approved_facebook": "eq.true",
        "fb_ig_skipped": "eq.false",
        "status": "eq.Active",
        "order": "score.desc,published_at.desc",
        "limit": "50",  # fetch a batch to filter against posted_slugs locally
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            log.warning("No approved Facebook listings found in pool")
            return None
        for row in rows:
            if row["slug"] not in posted_slugs:
                log.info(f"Selected listing: {row['slug']} (score qualified)")
                return row
        log.error(
            f"All {len(rows)} approved Facebook listings have already been posted. "
            "Approve more listings via the approval app."
        )
        return None
    except Exception as e:
        log.error(f"Supabase get_next_approved_listing error: {e}")
        return None


def log_social_post(
    platform: str,
    source_id: str,
    source_url: str,
    buffer_post_id: str,
    scheduled_at: datetime,
    post_text: str,
) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/social_posts"
    payload = {
        "platform": platform,
        "post_type": "listing",
        "source_id": source_id,
        "source_url": source_url,
        "buffer_post_id": buffer_post_id,
        "buffer_channel_id": BUFFER_CHANNEL_ID,
        "scheduled_at": scheduled_at.isoformat(),
        "status": "scheduled",
        "post_text": post_text,
    }
    try:
        r = requests.post(url, headers=_sb_headers(), json=payload, timeout=10)
        r.raise_for_status()
        log.info(f"social_posts logged: platform={platform} source_id={source_id}")
        return True
    except Exception as e:
        log.error(f"Supabase log_social_post error: {e}")
        return False

# ---------------------------------------------------------------------------
# Claude — generate Facebook caption
# ---------------------------------------------------------------------------

def call_claude(system: str, user: str) -> str | None:
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": CLAUDE_MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        blocks = data.get("content", [])
        text = "\n".join(b["text"] for b in blocks if b.get("type") == "text").strip()
        usage = data.get("usage", {})
        log.info(f"Claude tokens: in={usage.get('input_tokens')} out={usage.get('output_tokens')}")
        return text if text else None
    except Exception as e:
        log.error(f"Claude API error: {e}")
        return None


def generate_facebook_caption(listing: dict) -> str | None:
    system = load_prompt("facebook_listing.md")
    user = (
        f"HEADLINE: {listing.get('headline', '')}\n"
        f"SHORT_SUMMARY: {listing.get('short_summary', '')}\n"
        f"SOCIAL_CAPTION: {listing.get('social_caption', '')}\n"
        f"PRICE: ${listing.get('price', 0):,}\n"
        f"CITY: {listing.get('city', '')}\n"
        f"STATE: {listing.get('state', '')}\n"
        f"CATEGORY: {listing.get('category', '')}\n"
    )
    return call_claude(system, user)

# ---------------------------------------------------------------------------
# Buffer GraphQL API
# ---------------------------------------------------------------------------

def _buffer_headers() -> dict:
    return {
        "Authorization": f"Bearer {BUFFER_API_KEY}",
        "Content-Type": "application/json",
    }


def schedule_post(caption: str, image_url: str, due_at_utc: datetime) -> str | None:
    """
    Schedule a Facebook post via Buffer with image attachment.
    Returns Buffer post ID on success.
    """
    due_at_iso = due_at_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            dueAt
            status
          }
        }
        ... on MutationError {
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "text": caption,
            "channelId": BUFFER_CHANNEL_ID,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": due_at_iso,
            "metadata": {
                "facebook": {
                    "type": "post"
                }
            },
            "assets": [
                {"image": {"url": image_url}}
            ],
        }
    }

    try:
        r = requests.post(
            BUFFER_API_URL,
            headers=_buffer_headers(),
            json={"query": mutation, "variables": variables},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        if "errors" in data:
            log.error(f"Buffer GraphQL errors: {data['errors']}")
            return None

        result = data.get("data", {}).get("createPost", {})

        if "message" in result:
            log.error(f"Buffer MutationError: {result['message']}")
            return None

        post = result.get("post", {})
        post_id = post.get("id")
        due_at = post.get("dueAt")
        log.info(f"Buffer post scheduled: id={post_id} dueAt={due_at}")
        return post_id

    except Exception as e:
        log.error(f"Buffer schedule_post error: {e}")
        if hasattr(e, "response") and e.response is not None:
            log.error(f"Buffer response: {e.response.text[:300]}")
        return None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False):
    log.info("=== HousesUnder150K Facebook Publisher Start ===")
    if dry_run:
        log.info("*** DRY RUN — Buffer API will NOT be called ***")

    now_ct = get_now_ct()
    log.info(f"Current time (CT): {now_ct.strftime('%Y-%m-%d %H:%M %Z')}")

    posted_slugs = get_posted_slugs("facebook")
    log.info(f"Already-posted Facebook listing slugs: {len(posted_slugs)}")

    listing = get_next_approved_listing(posted_slugs)
    if not listing:
        log.error("No approved listing available — aborting")
        return

    if not listing.get("hero_image_url"):
        log.error(f"Listing {listing.get('slug')} has no hero_image_url — aborting")
        return

    caption = generate_facebook_caption(listing)
    if not caption:
        log.error("Claude returned no caption — aborting")
        return

    slug = listing["slug"]
    link_url = f"{SITE_BASE_URL}/listings/{slug}"
    full_caption = f"{caption}\n\n{link_url}"

    due_at_utc = random_post_time_utc()

    print("\n" + "=" * 60)
    print("FACEBOOK CAPTION:")
    print(full_caption)
    print(f"\nIMAGE URL: {listing['hero_image_url']}")
    print(f"SCHEDULED FOR: {due_at_utc.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60 + "\n")

    if dry_run:
        log.info("=== DRY RUN complete — no post sent ===")
        return

    post_id = schedule_post(full_caption, listing["hero_image_url"], due_at_utc)
    if not post_id:
        log.error("Failed to schedule post — aborting")
        return

    log_social_post(
        platform="facebook",
        source_id=slug,
        source_url=link_url,
        buffer_post_id=post_id,
        scheduled_at=due_at_utc,
        post_text=full_caption,
    )

    log.info(
        f"=== Facebook Publisher complete | "
        f"post_id={post_id} | "
        f"slug={slug} | "
        f"scheduled={due_at_utc.strftime('%Y-%m-%d %H:%M UTC')} ==="
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HousesUnder150K Facebook Publisher")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch content and generate post but do NOT send to Buffer.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
