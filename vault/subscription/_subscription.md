---
project: HousesUnder150K
file: subscription
type: living — update as Beehiiv is configured and subscription strategy develops
last_updated: 2026-07-29
status: PLACEHOLDER — Beehiiv not yet configured, subscribe button has no backend
---

<!-- HousesUnder150K subscription -->

# HousesUnder150K Subscription

This HousesUnder150K subscription document defines the email subscription strategy and Beehiiv configuration plan for the HousesUnder150K project. Load for any session touching email, Beehiiv, or subscriber monetization.

<!-- HousesUnder150K subscription -->

## HousesUnder150K Subscription — Current State

A "Subscribe" button exists in the Webflow site navigation and a subscribe section exists on the homepage. Neither is connected to a backend. No email platform has been configured. No subscribers have been collected.

**The subscribe button is a dead end until Beehiiv is set up.**

---

## HousesUnder150K Subscription — Planned Email Platform: Beehiiv

Beehiiv was selected in Session 1 for its native free/paid tier support and recommendation network. No account has been created. No integration work has been done.

**Why Beehiiv:**
- Handles free and paid subscriber tiers natively
- Recommendation network can drive organic subscriber growth
- Built for newsletter monetization at the scale this project targets

---

<!-- HousesUnder150K subscription -->

## HousesUnder150K Subscription — Planned Subscription Tiers

These are the tiers designed in Session 1. They have not been validated, priced, or implemented:

| Tier | Price | What They Get |
|------|-------|---------------|
| Free | $0 | Deal of the Day email daily |
| Investor | $1/month | All listings — early access (24-48 hours before public) |
| Curated | $2/month | Featured listings + Deal of the Day curated digest |

**Notes from Session 1:**
- Investor audience likely to pay — volume buyers want the signal early
- Churn near zero below $5/month price points
- Plan to scale to $5/month once the list proves its value
- Free tier is the acquisition hook — Deal of the Day gives people a reason to subscribe

---

## HousesUnder150K Subscription — What Needs to Be Built

### Beehiiv Account Setup
- Create account at beehiiv.com
- Configure the three tiers (free, $1/month, $2/month)
- Set up payment processing
- Define automation rules: which email goes to which tier

### Webflow → Beehiiv Integration
- Connect the subscribe form on the Webflow homepage to Beehiiv
- Options: Beehiiv native embed, Zapier, or Beehiiv's API
- Webflow forms can POST to a webhook — Beehiiv may have a direct integration

### Email Templates and Automation
- Deal of the Day email — daily, all subscribers including free tier
- All Listings email — daily or 2x/day, paid subscriber tiers only
- Featured Digest — curated, paid tiers only
- Automated triggers: when does each email send? Tied to pipeline publish events?

### Pipeline Integration
- `ingest.py` currently generates `social-caption` and `short-summary` fields — these could feed email content
- Deal of the Day logic in the pipeline already flags the best listing of the day
- Does the email send need to be triggered by the pipeline, or does Beehiiv handle it from CMS?

---

<!-- HousesUnder150K subscription -->

## HousesUnder150K Subscription — Open Questions

See `open-questions/_open_questions.md` — OQ-002 covers Beehiiv configuration.

Key unresolved questions:
- How does Beehiiv connect to Webflow's subscribe form?
- What triggers the Deal of the Day email — pipeline event, Beehiiv automation, or manual?
- How does Beehiiv pull listing content for the email — from CMS, from pipeline webhook, or manually curated?
- At what subscriber count does the paid tier become a meaningful revenue line vs. the Sovrn affiliate?

---

## HousesUnder150K Subscription — Revenue Model Context

Email subscriptions are one of three revenue layers:

1. **Affiliate** (Sovrn/Realtor.com) — $5/lead, passive, scales with traffic
2. **Email subscriptions** (Beehiiv) — recurring, scales with list quality and brand trust
3. **Display ads** — not yet configured, scales with monthly pageviews

The email list is also a retention and re-engagement mechanism — subscribers who miss a day can catch up, which extends the affiliate opportunity beyond a single session.
