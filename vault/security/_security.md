---
project: HousesUnder150K
file: security
type: living — update as security posture is defined and implemented
last_updated: 2026-07-29
status: PLACEHOLDER — security plan not yet defined
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

### Supabase Row Level Security — UNRESOLVED
RLS is **disabled** on all 3 Supabase tables (`published_listings`, `seen_listings`, `pipeline_runs`). The service role key stored in Railway has full read/write access with no policies restricting it.

**Risk:** If the Railway service role key is exposed, an attacker has unrestricted access to all pipeline data. This is not user data (no PII is stored), but it could allow manipulation of listing status, dedup records, or cost tracking.

**Remediation path:** Add appropriate RLS policies before enabling RLS, or the pipeline's own service role access breaks. Since this is a single-operator pipeline (not a multi-tenant app), the policy set is simple — service role bypasses RLS by default in Supabase, so enabling RLS with no policies would only affect non-service-role access. The actual fix may be as simple as: enable RLS (service role still has full access), add a read-only policy for the anon key if any future public queries are needed.

**Priority:** Medium — no user PII at risk, but clean up before scaling.

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
3. **Supabase RLS** — enable and add appropriate policies
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
