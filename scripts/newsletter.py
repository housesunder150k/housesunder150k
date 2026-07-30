"""
HousesUnder150K.com — Weekly Newsletter
Runs on Railway every Saturday at 6am CT.
Queries Supabase for the top 10 listings published Mon–Fri of the current week,
builds an HTML email, creates a MailerLite campaign, and sends it.

Environment variables required:
  SUPABASE_URL
  SUPABASE_KEY
  MAILERLITE_API_KEY
  MAILERLITE_GROUP_ID   (subscriber group/segment to send to)
  SITE_BASE_URL         (https://housesunder150k.com)
"""

import os
import logging
from datetime import datetime, date, timedelta

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

SUPABASE_URL       = os.environ["SUPABASE_URL"]
SUPABASE_KEY       = os.environ["SUPABASE_KEY"]
MAILERLITE_API_KEY = os.environ["MAILERLITE_API_KEY"]
MAILERLITE_GROUP_ID = os.environ["MAILERLITE_GROUP_ID"]
SITE_BASE_URL      = os.environ.get("SITE_BASE_URL", "https://housesunder150k.com")

CT_TZ = pytz.timezone("America/Chicago")

MAILERLITE_BASE = "https://connect.mailerlite.com/api"

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def fetch_weekly_listings() -> list[dict]:
    """Fetch top 10 listings published Mon–Fri of the current CT week, sorted score DESC price ASC."""
    today = datetime.now(CT_TZ).date()
    # Monday of current week
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    url = f"{SUPABASE_URL}/rest/v1/published_listings"
    params = {
        "select": "slug,headline,hero_image_url,score,tier,category,published_date_ct,is_deal_of_day,price",
        "published_date_ct": f"gte.{monday.isoformat()}",
        "and": f"(published_date_ct.lte.{friday.isoformat()})",
        "status": "eq.Active",
        "order": "score.desc,price.asc",
        "limit": "10",
    }
    try:
        r = requests.get(url, headers=_sb_headers(), params=params, timeout=10)
        r.raise_for_status()
        listings = r.json()
        log.info(f"Fetched {len(listings)} listings for {monday} – {friday}")
        return listings
    except Exception as e:
        log.error(f"Supabase fetch error: {e}")
        return []

# ---------------------------------------------------------------------------
# HTML email builder
# ---------------------------------------------------------------------------

def format_price(price: int) -> str:
    return f"${price:,}"


def listing_url(slug: str) -> str:
    return f"{SITE_BASE_URL}/listings/{slug}"


def build_featured_block(listing: dict) -> str:
    """Full-width featured listing — used for the #1 ranked listing."""
    url = listing_url(listing["slug"])
    headline = listing.get("headline", "")
    image = listing.get("hero_image_url", "")
    price = format_price(listing.get("price", 0))
    category = listing.get("category", "").replace("_", " ").title()

    return f"""
    <tr>
      <td style="padding: 0 0 8px 0;">
        <span style="font-family: Arial, sans-serif; font-size: 11px; font-weight: 700;
                     letter-spacing: 2px; color: #00d4d4; text-transform: uppercase;">
          ⭐ Deal of the Week
        </span>
      </td>
    </tr>
    <tr>
      <td style="padding: 0 0 16px 0;">
        <a href="{url}" style="text-decoration: none; display: block;">
          <img src="{image}" alt="{headline}"
               width="560" style="width: 100%; max-width: 560px; height: 320px;
               object-fit: cover; display: block; border-radius: 4px;" />
        </a>
      </td>
    </tr>
    <tr>
      <td style="padding: 0 0 8px 0;">
        <span style="font-family: Arial, sans-serif; font-size: 11px; font-weight: 700;
                     letter-spacing: 2px; color: #00d4d4; text-transform: uppercase;">
          {category}
        </span>
      </td>
    </tr>
    <tr>
      <td style="padding: 0 0 12px 0;">
        <a href="{url}" style="text-decoration: none;">
          <span style="font-family: 'Bebas Neue', Arial, sans-serif; font-size: 36px;
                       font-weight: 400; color: #ffffff; line-height: 1.1; display: block;">
            {headline}
          </span>
        </a>
      </td>
    </tr>
    <tr>
      <td style="padding: 0 0 24px 0;">
        <span style="font-family: Arial, sans-serif; font-size: 22px;
                     font-weight: 700; color: #ffffff;">
          {price}
        </span>
      </td>
    </tr>
    <tr>
      <td style="padding: 0 0 40px 0;">
        <a href="{url}"
           style="display: inline-block; background-color: #00d4d4; color: #0a0a0a;
                  font-family: Arial, sans-serif; font-size: 13px; font-weight: 700;
                  letter-spacing: 1px; text-transform: uppercase; text-decoration: none;
                  padding: 14px 28px; border-radius: 3px;">
          View This Deal →
        </a>
      </td>
    </tr>
    <tr>
      <td style="padding: 0 0 40px 0; border-bottom: 1px solid #222222;">
      </td>
    </tr>
"""


def build_grid_item(listing: dict) -> str:
    """Single card for the 2-column grid."""
    url = listing_url(listing["slug"])
    headline = listing.get("headline", "")
    image = listing.get("hero_image_url", "")
    price = format_price(listing.get("price", 0))

    return f"""
      <td width="260" valign="top"
          style="padding: 0 8px 32px 8px; width: 260px;">
        <a href="{url}" style="text-decoration: none; display: block;">
          <img src="{image}" alt="{headline}"
               width="260" style="width: 100%; height: 160px; object-fit: cover;
               display: block; border-radius: 4px; margin-bottom: 12px;" />
        </a>
        <a href="{url}" style="text-decoration: none;">
          <span style="font-family: 'Bebas Neue', Arial, sans-serif; font-size: 20px;
                       font-weight: 400; color: #ffffff; line-height: 1.2;
                       display: block; margin-bottom: 8px;">
            {headline}
          </span>
        </a>
        <span style="font-family: Arial, sans-serif; font-size: 16px;
                     font-weight: 700; color: #00d4d4; display: block; margin-bottom: 12px;">
          {price}
        </span>
        <a href="{url}"
           style="font-family: Arial, sans-serif; font-size: 12px; font-weight: 700;
                  color: #00d4d4; text-decoration: none; letter-spacing: 1px;
                  text-transform: uppercase;">
          View Listing →
        </a>
      </td>
"""


def build_grid_row(left: dict, right: dict | None) -> str:
    """One row of the 2-column grid. right can be None for an odd last item."""
    right_cell = build_grid_item(right) if right else "<td width='260' style='padding: 0 8px;'></td>"
    return f"""
    <tr>
      <td style="padding: 0;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            {build_grid_item(left)}
            {right_cell}
          </tr>
        </table>
      </td>
    </tr>
"""


def build_grid_section(listings: list[dict]) -> str:
    """Build the 2-column grid from listings[1:] (skip the featured #1)."""
    rows = ""
    remaining = listings[1:]
    for i in range(0, len(remaining), 2):
        left = remaining[i]
        right = remaining[i + 1] if i + 1 < len(remaining) else None
        rows += build_grid_row(left, right)
    return rows


def build_email_html(listings: list[dict], week_label: str) -> str:
    """Build the complete HTML email."""
    if not listings:
        return ""

    featured = listings[0]
    grid_rows = build_grid_section(listings)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <title>Houses Under 150K — Weekly Deals</title>
  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap" rel="stylesheet" />
  <!--[if mso]>
  <style>
    .bebas {{ font-family: Arial, sans-serif !important; }}
  </style>
  <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0a;">

  <!-- Preheader -->
  <span style="display: none; max-height: 0; overflow: hidden;">
    This week's best houses under $150K — {week_label}
  </span>

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color: #0a0a0a;">
    <tr>
      <td align="center">

        <!-- Email container -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width: 600px; width: 100%;">

          <!-- Header -->
          <tr>
            <td style="background-color: #0a0a0a; padding: 32px 20px 24px 20px;
                       border-bottom: 1px solid #222222;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td>
                    <span style="font-family: 'Bebas Neue', Arial, sans-serif;
                                 font-size: 28px; color: #ffffff; letter-spacing: 2px;">
                      Houses
                    </span>
                    <span style="font-family: 'Bebas Neue', Arial, sans-serif;
                                 font-size: 28px; color: #00d4d4; letter-spacing: 2px;">
                      Under 150K
                    </span>
                  </td>
                  <td align="right">
                    <span style="font-family: Arial, sans-serif; font-size: 12px;
                                 color: #888888;">
                      Weekly Deals · {week_label}
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Intro -->
          <tr>
            <td style="padding: 32px 20px 8px 20px;">
              <span style="font-family: 'Bebas Neue', Arial, sans-serif; font-size: 48px;
                           color: #ffffff; line-height: 1; letter-spacing: 1px; display: block;">
                This Week's Best Deals.
              </span>
            </td>
          </tr>
          <tr>
            <td style="padding: 8px 20px 32px 20px; border-bottom: 1px solid #222222;">
              <span style="font-family: Arial, sans-serif; font-size: 15px;
                           color: #888888; line-height: 1.6;">
                The 10 highest-rated houses under $150,000 published on
                HousesUnder150K.com this week. One deal of the week leads the list.
              </span>
            </td>
          </tr>

          <!-- Featured listing -->
          <tr>
            <td style="padding: 32px 20px 0 20px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {build_featured_block(featured)}
              </table>
            </td>
          </tr>

          <!-- Grid section header -->
          <tr>
            <td style="padding: 32px 20px 8px 20px;">
              <span style="font-family: Arial, sans-serif; font-size: 11px; font-weight: 700;
                           letter-spacing: 2px; color: #00d4d4; text-transform: uppercase;">
                More Deals This Week
              </span>
            </td>
          </tr>

          <!-- Grid -->
          <tr>
            <td style="padding: 16px 12px 0 12px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {grid_rows}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 32px 20px; border-top: 1px solid #222222;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td>
                    <span style="font-family: 'Bebas Neue', Arial, sans-serif;
                                 font-size: 20px; color: #ffffff; letter-spacing: 2px;">
                      Houses
                    </span>
                    <span style="font-family: 'Bebas Neue', Arial, sans-serif;
                                 font-size: 20px; color: #00d4d4; letter-spacing: 2px;">
                      Under 150K
                    </span>
                    <br />
                    <span style="font-family: Arial, sans-serif; font-size: 12px;
                                 color: #555555;">
                      Finding deals most people miss.
                      <a href="{SITE_BASE_URL}" style="color: #555555;">housesunder150k.com</a>
                    </span>
                  </td>
                  <td align="right" valign="top">
                    <a href="{{{{unsubscribe}}}}"
                       style="font-family: Arial, sans-serif; font-size: 12px;
                              color: #555555; text-decoration: underline;">
                      Unsubscribe
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
        <!-- /Email container -->

      </td>
    </tr>
  </table>
  <!-- /Wrapper -->

</body>
</html>"""


# ---------------------------------------------------------------------------
# MailerLite
# ---------------------------------------------------------------------------

def _ml_headers() -> dict:
    return {
        "Authorization": f"Bearer {MAILERLITE_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_and_send_campaign(html: str, week_label: str) -> bool:
    """Create a MailerLite campaign and send it immediately."""

    subject = f"This Week's Best Deals Under $150K — {week_label}"
    from_name = "HousesUnder150K"
    from_email = "newsletter@housesunder150k.com"

    # Step 1 — Create campaign
    log.info("Creating MailerLite campaign...")
    campaign_payload = {
        "name": f"Weekly Newsletter — {week_label}",
        "type": "regular",
        "status": "draft",
        "emails": [
            {
                "subject": subject,
                "from_name": from_name,
                "from": from_email,
                "content": html,
            }
        ],
        "groups": [MAILERLITE_GROUP_ID],
    }

    try:
        r = requests.post(
            f"{MAILERLITE_BASE}/campaigns",
            headers=_ml_headers(),
            json=campaign_payload,
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"MailerLite create campaign failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            log.error(f"Response: {e.response.text[:500]}")
        return False

    campaign_id = r.json().get("data", {}).get("id")
    if not campaign_id:
        log.error("No campaign ID returned from MailerLite")
        return False

    log.info(f"Campaign created: {campaign_id}")

    # Step 2 — Schedule/send immediately
    log.info("Sending campaign...")
    try:
        r = requests.post(
            f"{MAILERLITE_BASE}/campaigns/{campaign_id}/schedule",
            headers=_ml_headers(),
            json={"delivery": "instant"},
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.error(f"MailerLite send failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            log.error(f"Response: {e.response.text[:500]}")
        return False

    log.info(f"Campaign sent successfully: {campaign_id}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_newsletter():
    log.info("=== HousesUnder150K Newsletter Start ===")

    today = datetime.now(CT_TZ).date()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    week_label = f"{monday.strftime('%b %-d')} – {friday.strftime('%b %-d, %Y')}"

    log.info(f"Week: {week_label}")

    listings = fetch_weekly_listings()
    if not listings:
        log.error("No listings found for this week — aborting")
        return

    if len(listings) < 3:
        log.warning(f"Only {len(listings)} listings this week — sending anyway")

    html = build_email_html(listings, week_label)
    if not html:
        log.error("Failed to build email HTML — aborting")
        return

    success = create_and_send_campaign(html, week_label)
    if success:
        log.info("=== Newsletter complete ===")
    else:
        log.error("=== Newsletter failed ===")


if __name__ == "__main__":
    run_newsletter()
