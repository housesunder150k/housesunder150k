---
project: HousesUnder150K
file: spec_content
type: living — update when content prompt or voice guidelines change
last_updated: 2026-07-29
prompt_location: scripts/prompts/deals-under-150k.md (codebase)
---

<!-- HousesUnder150K spec_content -->

# HousesUnder150K — Content Spec

This HousesUnder150K content spec defines the content generation prompt (Claude Call 2), voice guidelines, and output format rules for all HousesUnder150K listings. Load for any session touching content generation, voice, or editorial quality.

<!-- HousesUnder150K spec_content -->

## HousesUnder150K Content Spec — Overview

The content generation prompt is Claude Call 2 in the two-prompt pipeline. It runs only for listings that scored 6 or above. It receives the listing data plus the CATEGORY and KEY_HOOKS from the scoring call, and produces four outputs: HEADLINE, NARRATIVE, SOCIAL_CAPTION, SHORT_SUMMARY.

The voice benchmark is Michelle Bowers at theoldhouselife.com — 413,900 monthly visits, peaked at 1M. Her format: conversational, enthusiastic, specific, honest. The listing is the content. The writer is the curator.

---

<!-- HousesUnder150K spec_content -->

## HousesUnder150K Content Spec — Outputs

### HEADLINE
The listing page H1 and Webflow `name` field. Also used as the card title on homepage and state pages.

**Rules:**
- Short. Specific. Punchy. No more than 10-12 words ideal.
- Lead with the most interesting fact, not the location.
- Include the price — it's the hook.
- No punctuation at the end.
- No real estate language.

**Examples by category:**
- HISTORIC: "1891 Victorian. Original Tin Ceilings. $87,000."
- NEW_CONSTRUCTION: "Brand New. Milwaukee. $105,000. Yes, Really."
- WATERFRONT: "Lakefront Cottage. Half Acre. $149,000."
- ACREAGE: "1890 Ohio Farmhouse. 12 Acres. Auction Opens at $100K."
- WHAT_IF: "Six Acres and a Barn in Southern Illinois. $94,000."
- TOO_GOOD_TO_BE_TRUE: "Castle House. Road Bricks. Marble Floors. $100,000."
- CHARACTER: "1900 Johnstown Home. Sauna Steam Shower. $82,500."

### NARRATIVE
The listing page body copy. Rich text field — HTML paragraphs. 300-400 words.

**Rules:**
- 3-5 paragraphs
- Opening line leads with the most interesting fact (see category lead rules below)
- Key facts in natural flowing sentences — not a spec list
- Agent description rewritten in the site's voice — facts extracted, never quoted
- Honest hedging when something is uncertain ("the photos suggest..." not "this stunning...")
- No CTA line — the site's CTA block handles it
- No real estate language (see banned words below)
- Specific numbers always ("6.13 acres" not "over six acres")

**Category opening lines:**
- What If → lead with the life detail ("Six acres and a barn in Southern Illinois. $94,000.")
- Time Machine / Historic → lead with what survived ("The original hardwood floors. Still here. 1891.")
- Too Good To Be True → lead with disbelief ("Brand new. $105,000. Milwaukee. Yes, really.")
- Hidden Gem → lead with discovery ("Not sure how this one is still available.")
- New Construction → lead with the impossibility ("Brand new construction. In Milwaukee. For $105,000.")
- Waterfront → lead with the water ("Sitting on the water in [location]. $X.")
- Acreage → lead with the land ("Twelve acres of Ohio farmland. 1890 farmhouse. Auction opens at $100K.")

**Format for Webflow write:**
```
"<p>Opening paragraph.</p><p>Second paragraph.</p><p>Third paragraph.</p>"
```

### SOCIAL_CAPTION
Instagram/Facebook caption. Under 60 words. No hashtags.

**Rules:**
- Same voice as narrative — conversational, enthusiastic, specific
- Lead with the hook (price + most interesting fact)
- No hashtags — they are added separately if at all
- Under 60 words — tight is better

### SHORT_SUMMARY
Homepage card preview text and Deal of the Day section subtext. Under 30 words.

**Rules:**
- One or two sentences maximum
- The single most compelling thing about the listing
- Reads as a teaser, not a description

---

<!-- HousesUnder150K spec_content -->

## HousesUnder150K Content Spec — Voice Rules (Non-Negotiable)

**Banned words and phrases — never appear in any generated content:**
- nestled, charming, cozy, quaint
- rare find, hidden gem (as a descriptor — the category name is fine)
- open concept, open floor plan
- move-in ready (unless directly supported by specifics)
- stunning, breathtaking, gorgeous, beautiful
- perfect for, ideal for, great for
- turnkey (unless supported by specific renovation details)
- motivated seller (in narrative — this is a scoring signal, not editorial copy)
- priced to sell, won't last, act fast, don't miss

**Voice principles:**
- Short sentences. Active voice. No padding.
- Precision over approximation ("6.13 acres" not "over six acres")
- Real enthusiasm, not manufactured enthusiasm
- Honest hedging when something is uncertain
- The listing does the work. The writer gets out of the way.
- Discovery register — the reader is finding something, not being sold something

---

<!-- HousesUnder150K spec_content -->

## HousesUnder150K Content Spec — Agent Description as Source Material

The agent description is the primary source of specific facts, local context, and named features. It is extracted and rewritten — never quoted directly. Rich descriptions produce better posts. Sparse descriptions produce thinner narratives.

**What to extract:**
- Named features ("original oak floors," "tin ceiling in the dining room," "1.2-acre lot")
- Local context ("two blocks from the town square," "on the edge of the state forest")
- Recent updates with specifics ("new roof 2022," "updated kitchen with quartz counters")
- Unique details that don't appear in the specs (the details that make the listing a story)

**What to ignore:**
- Agent boilerplate ("Don't miss this opportunity")
- Vague superlatives ("beautifully updated")
- Anything that can't be verified or that inflates the listing

---

## HousesUnder150K Content Spec — KEY_HOOKS Bridge

The KEY_HOOKS output from the scoring call (Call 1) are passed directly to the content generation prompt (Call 2). They serve as editorial direction — specific facts the content generator should build around.

Good KEY_HOOKS (specific, usable):
- "1891 Victorian with original tin ceilings and clawfoot tub"
- "0.8 acres on a creek in rural Kentucky"
- "$87,000 — $74/sqft for a fully intact historic home"

Weak KEY_HOOKS (generic, not useful):
- "Nice older home"
- "Good price for the area"
- "Lots of character"

The scoring prompt instructs Claude to make KEY_HOOKS specific and usable. If content quality is poor, check the KEY_HOOKS output from scoring — they are the primary driver of narrative quality.

---

<!-- HousesUnder150K spec_content -->

## HousesUnder150K Content Spec — Content Parser

Before parsing outputs, the pipeline strips markdown formatting that Claude occasionally adds:
- `**bold**` markers removed from around label text
- `#` hash prefixes removed from label lines
- `---` separator lines removed

This runs on both scoring and content generation outputs.

---

## HousesUnder150K Content Spec — Content Generation Input

```
CATEGORY: [from scoring call]
KEY_HOOKS: [from scoring call]
PRICE: [formatted price]
ADDRESS: [street address]
CITY: [city]
STATE: [state abbreviation]
BEDROOMS: [integer]
BATHROOMS: [integer]
SQFT: [integer]
YEAR_BUILT: [integer]
DESCRIPTION: [full agent description]
AFFILIATE_URL: [Realtor.com property page href]
```

---

<!-- HousesUnder150K spec_content -->

## HousesUnder150K Content Spec — Quality Signals to Monitor

If narrative quality is consistently poor, check in this order:
1. Are KEY_HOOKS from scoring specific and usable?
2. Is the agent description rich or sparse? (Sparse description = thinner narrative)
3. Is the category assignment correct? Wrong category produces wrong opening line.
4. Is the narrative hitting 300-400 words or falling short?
5. Is any banned language appearing in generated content?

If headlines are generic (just "3 Bedroom Home in [City] for $X"):
- Check that CATEGORY and KEY_HOOKS are reaching the content prompt correctly
- Check for empty content guard triggering on valid content (check parser strip logic)
