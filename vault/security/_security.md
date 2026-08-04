---
project: HousesUnder150K
file: security
type: living — update as security posture is defined and implemented
last_updated: 2026-08-04
status: PLACEHOLDER — security plan not yet defined; RLS gap resolved 2026-08-04, other gaps below still open
---

<!-- HousesUnder150K security -->

# HousesUnder150K Security

This HousesUnder150K security document captures known security gaps and serves as the starting point for a formal security plan. Load for any session touching credentials, access controls, or RLS.

<!-- HousesUnder150K security -->

## HousesUnder150K Security — Current Security Posture

HousesUnder150K.com was built in approximately 2 days across Sessions 1-4, moving fast. Security was not formally considered or implemented. This document captures the known gaps and serves as the starting point for a proper security plan.

**The project has no security toolchain, no formal credential management, no RLS policies, and no access audit. This needs to change before meaningful traffic or revenue arrives.**

---

<!-- HousesUnder150K security -->

## HousesUnder150K Security — Known Gaps

### Supabase Row Level Security — RESOLVED (2026-08-04)
RLS is now **enabled** on all 4 Supabase tables (`published_listings`, `seen_listings`, `pipeline_runs`, `social_queue` — the fourth table was added after this gap was first logged). Previously disabled on all tables since creation and tracked as OQ-005; remediation was triggered by a Supabase security advisory email flagging `published_listings` as publicly exposed via the anon key (anyone with the project URL could read/edit/delete every row).

**Verification before the fix:** Confirmed via Railway env vars that `SUPABASE_KEY` (shared by the pipeline, newsletter, and maintenance services) is the `service_role` key, not the anon key. `service_role` bypasses RLS entirely regardless of policy, so enabling RLS with zero policies was sufficient — Postgres's default deny-all for an RLS-enabled table with no policies automatically locks out the `anon`/`authenticated` roles without affecting the pipeline's own access.

**Fix applied:** `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` on all 4 tables, migration `enable_rls_public_tables` (project `krzpkaxvbmpdeluqzkka`).

**Verification after the fix:** Manual pipeline trigger (Railway service `housesunder150k`, 2026-08-04 23:41 UTC) completed with 0 errors, 1 listing published, Webflow write succeeded, site republished to housesunder150k.com. `published_listings` row count confirmed incremented (128 → 129) and `pipeline_runs` logged the run cleanly, confirming service_role writes are unaffected by RLS.

**Remaining:** No RLS policies exist beyond the default deny — none are needed today since the public site reads from Webflow CMS, not Supabase, directly. If a future feature needs the anon key to read Supabase directly, a read-only policy will need to be added then.

**Priority:** Resolved. No user PII was ever at risk; this closed the externally-facing exposure before it was exploited.

---

### Credential Management — UNRESOLVED
**Current state:**
- All credentials in Railway environment variables ✓
- No credentials committed to the repo ✓
- No credential rotation schedule ✗
- No MFA confirmed on key accounts ✗
- No Bitwarden or equivalent credential inventory ✗
- Dead credential: `REPLIERS_API_KEY` still in Railway (unused) ✗

**Accounts requiring MFA audit:**
- housesunder150k@gmail.com (Google account — Webflow, Railway, Supabase, RealtyAPI, Cloudflare all linked)
- Railway
- Supabase
- Cloudflare
- GitHub (housesunder150k org)
- Anthropic API console

**Priority:** High — single Google account compromise cascades to most of the stack.

---

### Webflow Site Security — NOT ASSESSED
No security assessment has been performed on the Webflow site itself. Items not yet reviewed:
- Content Security Policy headers
- Cloudflare security settings (WAF, bot protection, DDoS)
- Webflow form handling (subscribe button) — no backend currently, but when Beehiiv connects, this is an input surface
- Any custom code injected into site head/footer (JSON-LD script, CSS) — reviewed for correctness, not for XSS vectors

---

### GitHub Repository — NOT ASSESSED
- Repo: github.com/housesunder150k/housesunder150k
- No branch protection rules confirmed
- No CI/CD security scanning (no equivalent of ShowFlyer's Gitleaks/Semgrep/njsscan)
- No dependabot configured
- `requirements.txt` pins exact versions — good

---

## HousesUnder150K Security — What a Security Plan Should Cover

When this plan is formally built out, it should address at minimum:

1. **Credential inventory and rotation schedule** — all active API keys, when they were created, rotation cadence
2. **MFA audit** — confirm MFA on every account listed above
3. **Supabase RLS** — ✅ enabled 2026-08-04 (see above); no additional policies currently needed
4. **Cloudflare security configuration** — WAF rules, bot fight mode, security level
5. **GitHub security** — branch protection, secret scanning, dependency review
6. **Webflow CSP** — Content Security Policy headers via Cloudflare (Webflow doesn't support custom headers natively)
7. **Dead credential cleanup** — `REPLIERS_API_KEY` removal from Railway
8. **Incident response** — what to do if a key is exposed, who to notify, how to rotate

---

<!-- HousesUnder150K security -->

## HousesUnder150K Security — Decisions Made (Security-Related)

- All credentials in Railway environment variables, never in code, never committed (from kickoff — followed throughout)
- Maintenance service credentials set as variable references to main service, not duplicated raw values (ADR-043)
- `REPLIERS_API_KEY` flagged for removal — unused since RealtyAPI pivot (OQ-010)
- Supabase RLS enabled on all 4 tables 2026-08-04, closing OQ-005 (service_role key confirmed to bypass RLS, so no policies were required to preserve pipeline access)
