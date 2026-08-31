"""
HousesUnder150K.com — LinkedIn Publisher
Runs Mon-Fri on Railway cron: 0 14 * * 1-5 (9am CT / 2pm UTC)

Schedule logic:
  - Monday: article post (most recently published article from Webflow CMS)
  - Tue-Fri: listing post (today's Deal of the Day from Supabase)

Post structure:
  - Post body: original LinkedIn-native commentary (not site copy verbatim)
  - First comment: link to the listing or article, via Buffer LinkedIn metadata

Timing:
  - Script runs at 9am CT. Randomizes a post time within 8:00am-4:30pm CT window.
  - Buffer metadata handles first comment delivery on LinkedIn natively.

Buffer API:
  - GraphQL at https://api.buffer.com
  - createPost mutation with customScheduled mode and dueAt (UTC ISO 8601)
  - LinkedIn first comment via metadata.linkedin.comment

Dry run:
  - python linkedin.py --dry-run
  - Fetches source content, generates post via Claude, prints everything.
  - Does NOT call Buffer API. Safe to run anytime for testing.

Environment variables required:
  BUFFER_API_KEY          — Buffer API key (from publish.buffer.com/settings/api)
  BUFFER_CHANNEL_ID       — Buffer LinkedIn channel ID for Jordan Reyes
  ANTHROPIC_API_KEY       — for LinkedIn post generation
  SUPABASE_URL            — HousesUnder150K Supabase project URL
  SUPABASE_KEY            — Supabase service role key
  WEBFLOW_API_TOKEN       — for fetching latest article from Webflow CMS

Deduplication:
  On Mondays, fetches up to 10 recent articles from Webflow and picks the first
  whose webflow_item_id is not already in social_posts for linkedin/article.
  Aborts with an error if all candidates have been used.

Post log:
  Every successfully scheduled post is recorded in social_posts (Supabase).
  This table is the source of truth for deduplication and analytics joins.

Changes:
  2026-08-30: Initial implementation — GraphQL API, correct Buffer channel/org IDs
  2026-08-30: Added --dry-run flag
  2026-08-31: social_posts log + article deduplication
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

BUFFER_API_KEY       = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_ID    = os.environ["BUFFER_CHANNEL_ID"]   # 6a9471ff065799be4655f279
ANTHROPIC_API_KEY    = os.environ["ANTHROPIC_API_KEY"]
SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_KEY         = os.environ["SUPABASE_KEY"]
WEBFLOW_API_TOKEN    = os.environ["WEBFLOW_API_TOKEN"]

WEBFLOW_ARTICLES_COLLECTION = "6a6de940eb6dc0e3344431d6"
SITE_BASE_URL               = "https://housesunder150k.com"
BUFFER_API_URL              = "https://api.buffer.com"

# Number of recent Webflow articles to fetch as deduplication candidates
ARTICLE_CANDIDATE_LIMIT = 10

CLAUDE_MODEL      = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 400

CT_TZ = pytz.timezone("America/Chicago")

# Posting window: 8:00am - 4:30pm CT = 510 minutes
POST_WINDOW_START_HOUR   = 8
POST_WINDOW_START_MINUTE = 0
POST_WINDOW_MINUTES      = 510

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


def is_monday(force: bool = False) -> bool:
    return force or get_now_ct().weekday() == 0


def random_post_time_utc() -> datetime:
    """Pick a random time between 8:00am and 4:30pm CT, return as UTC datetime."""
    now_ct = get_now_ct()
    window_start = now_ct.replace(
        hour=POST_WINDOW_START_HOUR,
        minute=POST_WINDOW_START_MINUTE,
        second=0,
        microsecond=0,
    )
    offset_minutes = random.randint(0, POST_WINDOW_MINUTES)
    scheduled_ct = window_start + timedelta(minutes=offset_minutes)

    # Safety clamp: never schedule in the past
    if scheduled_ct <= now_ct + timedelta(minutes=5):
        scheduled_ct = now_ct + timedelta(minutes=15)

    scheduled_utc = scheduled_ct.astimezone(pytz.utc)
    log.info(f"Scheduled post time: {scheduled_ct.strftime('%H:%M CT')} / {scheduled_utc.strftime('%H:%M UTC')}")
    return scheduled_utc

# ---------------------------------------------------------------------------
# Supabase — fetch today's Deal of the Day
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def get_deal_of_the_day() -> dict | None:
    today = get_now_ct().date().isoformat()
    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug,headline,short_summary,social_caption,price,city,state,category",
        "is_deal_of_day": "eq.true",
        "published_date_ct": f"eq.{today}",
        "limit": 1,
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            log.warning(f"No Deal of the Day found for {today}")
            return None
        log.info(f"Deal of the Day: {rows[0].get('slug')}")
        return rows[0]
    except Exception as e:
        log.error(f"Supabase get_deal_of_the_day error: {e}")
        return None

# ---------------------------------------------------------------------------
# Supabase — social_posts log
# ---------------------------------------------------------------------------

def get_posted_source_ids(platform: str, post_type: str) -> set[str]:
    """Return the set of source_ids already posted for this platform+post_type."""
    url = f"{SUPABASE_URL}/rest/v1/social_posts"
    params = {
        "select": "source_id",
        "platform": f"eq.{platform}",
        "post_type": f"eq.{post_type}",
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        return {row["source_id"] for row in r.json()}
    except Exception as e:
        log.error(f"Supabase get_posted_source_ids error: {e}")
        return set()


def log_social_post(
    platform: str,
    post_type: str,
    source_id: str,
    source_url: str,
    buffer_post_id: str,
    buffer_channel_id: str,
    scheduled_at: datetime,
    post_text: str,
) -> bool:
    """Insert a row into social_posts. Returns True on success."""
    url = f"{SUPABASE_URL}/rest/v1/social_posts"
    payload = {
        "platform": platform,
        "post_type": post_type,
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
        log.info(f"social_posts logged: platform={platform} post_type={post_type} source_id={source_id}")
        return True
    except Exception as e:
        log.error(f"Supabase log_social_post error: {e}")
        return False


# ---------------------------------------------------------------------------
# Webflow — fetch article candidates (deduplicated)
# ---------------------------------------------------------------------------

def get_latest_article(posted_ids: set[str]) -> dict | None:
    """Fetch recent articles and return the first not already posted to LinkedIn."""
    url = f"https://api.webflow.com/v2/collections/{WEBFLOW_ARTICLES_COLLECTION}/items"
    headers = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "accept": "application/json",
    }
    params = {
        "sortBy": "lastPublished",
        "sortOrder": "desc",
        "limit": ARTICLE_CANDIDATE_LIMIT,
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            log.warning("No articles found in Webflow CMS")
            return None
        for item in items:
            webflow_item_id = item.get("id", "")
            if webflow_item_id in posted_ids:
                log.info(f"Skipping already-posted article: {webflow_item_id}")
                continue
            fd = item.get("fieldData", {})
            slug = item.get("slug") or fd.get("slug", "")
            article_url_path = fd.get("article-url") or (f"/articles/{slug}" if slug else "")
            result = {
                "webflow_item_id": webflow_item_id,
                "name": fd.get("name", ""),
                "excerpt": fd.get("excerpt", ""),
                "url": f"{SITE_BASE_URL}{article_url_path}" if article_url_path else "",
                "read_time": fd.get("read-time", ""),
            }
            log.info(f"Selected article: {result['name']} ({webflow_item_id})")
            return result
        log.error(
            f"All {len(items)} recent Webflow articles have already been posted to LinkedIn. "
            "Publish a new article or the pipeline will skip Mondays until one is available."
        )
        return None
    except Exception as e:
        log.error(f"Webflow get_latest_article error: {e}")
        return None

# ---------------------------------------------------------------------------
# Claude — generate LinkedIn post
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


def generate_listing_post(listing: dict) -> str | None:
    system = load_prompt("linkedin_listing.md")
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


def generate_article_post(article: dict) -> str | None:
    system = load_prompt("linkedin_article.md")
    user = (
        f"TITLE: {article.get('name', '')}\n"
        f"EXCERPT: {article.get('excerpt', '')}\n"
        f"READ_TIME: {article.get('read_time', '')}\n"
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


def schedule_post(post_text: str, due_at_utc: datetime) -> str | None:
    """
    Schedule a LinkedIn post via Buffer. Link is included in post_text body.
    due_at_utc must be a UTC-aware datetime.
    Returns the Buffer post ID on success.
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
            "text": post_text,
            "channelId": BUFFER_CHANNEL_ID,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": due_at_iso,
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

def run(dry_run: bool = False, force_monday: bool = False):
    log.info("=== HousesUnder150K LinkedIn Publisher Start ===")
    if dry_run:
        log.info("*** DRY RUN — Buffer API will NOT be called ***")
    if force_monday:
        log.info("*** --monday flag set — forcing article (Monday) mode ***")

    now_ct = get_now_ct()
    log.info(f"Current time (CT): {now_ct.strftime('%Y-%m-%d %H:%M %Z')}")
    log.info(f"Day: {'Monday (article)' if is_monday(force_monday) else 'Tue-Fri (listing)'}")

    post_text = None
    link_url = None

    if is_monday(force_monday):
        posted_ids = get_posted_source_ids("linkedin", "article")
        log.info(f"Already-posted article IDs on LinkedIn: {len(posted_ids)}")
        article = get_latest_article(posted_ids)
        if not article:
            log.error("No unused article available — aborting")
            return
        post_text = generate_article_post(article)
        link_url = article.get("url", "")
        if not post_text:
            log.error("Claude returned no article post — aborting")
            return
        if not link_url:
            log.error("No article URL — aborting")
            return
        log.info(f"Article post generated ({len(post_text)} chars)")

    else:
        listing = get_deal_of_the_day()
        if not listing:
            log.error("No Deal of the Day found — aborting")
            return
        post_text = generate_listing_post(listing)
        slug = listing.get("slug", "")
        link_url = f"{SITE_BASE_URL}/listings/{slug}"
        if not post_text:
            log.error("Claude returned no listing post — aborting")
            return
        log.info(f"Listing post generated ({len(post_text)} chars)")
        article = None  # not used in listing path; referenced below for source_id

    # Append link to post body — LinkedIn nofollow means first comment
    # provides no SEO benefit over body; presence/entity signals are the goal.
    full_post_text = f"{post_text}\n\n{link_url}"

    due_at_utc = random_post_time_utc()

    print("\n" + "=" * 60)
    print("POST BODY:")
    print(full_post_text)
    print(f"\nSCHEDULED FOR: {due_at_utc.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60 + "\n")

    if dry_run:
        log.info("=== DRY RUN complete — no post sent ===")
        return

    post_id = schedule_post(full_post_text, due_at_utc)
    if not post_id:
        log.error("Failed to schedule post — aborting")
        return

    # Log to social_posts for deduplication and analytics
    source_id = article["webflow_item_id"] if is_monday(force_monday) else listing.get("slug", "")
    post_type = "article" if is_monday(force_monday) else "listing"
    log_social_post(
        platform="linkedin",
        post_type=post_type,
        source_id=source_id,
        source_url=link_url,
        buffer_post_id=post_id,
        buffer_channel_id=BUFFER_CHANNEL_ID,
        scheduled_at=due_at_utc,
        post_text=full_post_text,
    )

    log.info(
        f"=== LinkedIn Publisher complete | "
        f"post_id={post_id} | "
        f"scheduled={due_at_utc.strftime('%Y-%m-%d %H:%M UTC')} ==="
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HousesUnder150K LinkedIn Publisher")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch content and generate post but do NOT send to Buffer.",
    )
    parser.add_argument(
        "--monday",
        action="store_true",
        help="Force Monday (article) mode regardless of actual day. Useful for testing.",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, force_monday=args.monday)
