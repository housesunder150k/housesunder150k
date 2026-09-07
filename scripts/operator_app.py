"""
HousesUnder150K.com — Operator App
Internal tool for FB/IG listing approval and manual listing injection.

Runs as a Railway web service (not a cron).
Serves a single-page HTML frontend + JSON API backend.
Protected by HTTP Basic Auth — browser prompts for credentials on first visit.

Environment variables required:
  OPERATOR_USER      — Basic Auth username
  OPERATOR_PASS      — Basic Auth password
  SUPABASE_URL       — HousesUnder150K Supabase project URL
  SUPABASE_KEY       — Supabase service role key (bypasses RLS)
  PORT               — set automatically by Railway

Start command: uvicorn scripts.operator_app:app --host 0.0.0.0 --port $PORT

Changes:
  2026-09-07: Initial implementation
"""

import os
import secrets
import logging
from typing import Optional

import requests
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OPERATOR_USER = os.environ["OPERATOR_USER"]
OPERATOR_PASS = os.environ["OPERATOR_PASS"]
SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_KEY"]
SITE_BASE_URL = "https://housesunder150k.com"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username.encode(), OPERATOR_USER.encode())
    correct_pass = secrets.compare_digest(credentials.password.encode(), OPERATOR_PASS.encode())
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm='HousesUnder150K Operator'"},
        )
    return credentials.username


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def sb_get(path: str, params: dict) -> list:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=_sb_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_patch(path: str, match: dict, body: dict) -> None:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers=_sb_headers(),
        params={k: f"eq.{v}" for k, v in match.items()},
        json=body,
        timeout=10,
    )
    r.raise_for_status()


def sb_post(path: str, body: dict) -> list:
    headers = {**_sb_headers(), "Prefer": "return=representation"}
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, json=body, timeout=10)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/queue")
def get_queue(_: str = Depends(require_auth)):
    """Return unapproved, unskipped Active listings ordered by score DESC."""
    rows = sb_get("published_listings", {
        "select": "slug,headline,price,city,state,category,score,hero_image_url",
        "fb_ig_approved_facebook": "eq.false",
        "fb_ig_approved_instagram": "eq.false",
        "fb_ig_skipped": "eq.false",
        "status": "eq.Active",
        "order": "score.desc,published_at.desc",
        "limit": "200",
    })
    return JSONResponse({"rows": rows})


@app.post("/api/approve/{slug}")
async def approve_listing(slug: str, request: Request, _: str = Depends(require_auth)):
    """Set fb_ig_approved_facebook and/or fb_ig_approved_instagram on a listing."""
    body = await request.json()
    fb = bool(body.get("facebook", False))
    ig = bool(body.get("instagram", False))
    if not fb and not ig:
        raise HTTPException(status_code=400, detail="At least one platform required")
    sb_patch("published_listings", {"slug": slug}, {
        "fb_ig_approved_facebook": fb,
        "fb_ig_approved_instagram": ig,
    })
    log.info(f"Approved {slug} — fb={fb} ig={ig}")
    return JSONResponse({"ok": True})


@app.post("/api/skip/{slug}")
def skip_listing(slug: str, _: str = Depends(require_auth)):
    """Permanently skip a listing from the FB/IG queue."""
    sb_patch("published_listings", {"slug": slug}, {"fb_ig_skipped": True})
    log.info(f"Skipped {slug}")
    return JSONResponse({"ok": True})


@app.get("/api/requests")
def get_requests(_: str = Depends(require_auth)):
    """Return the 10 most recent manual listing requests."""
    rows = sb_get("manual_listing_requests", {
        "select": "id,address,status,is_deal_of_day,post_facebook,post_instagram,created_at,result_slug,error_message",
        "order": "created_at.desc",
        "limit": "10",
    })
    return JSONResponse({"rows": rows})


@app.post("/api/requests")
async def create_request(request: Request, _: str = Depends(require_auth)):
    """Insert a new manual listing request."""
    body = await request.json()
    address = (body.get("address") or "").strip()
    if not address:
        raise HTTPException(status_code=400, detail="address is required")
    row = {
        "address": address,
        "status": "pending",
        "is_deal_of_day": bool(body.get("is_deal_of_day", False)),
        "deal_of_day_date": body.get("deal_of_day_date") or None,
        "post_facebook": bool(body.get("post_facebook", False)),
        "post_instagram": bool(body.get("post_instagram", False)),
    }
    result = sb_post("manual_listing_requests", row)
    log.info(f"Manual request created: {address}")
    return JSONResponse({"ok": True, "id": result[0]["id"] if result else None})


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>HousesUnder150K — Operator</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #F9FAFB; color: #111; min-height: 100vh; }

  .header { padding: 16px 20px 0; }
  .header-eyebrow { font-size: 11px; font-weight: 600; color: #9CA3AF; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 2px; }
  .header-title { font-size: 20px; font-weight: 700; margin-bottom: 16px; }

  .tabs { display: flex; border-bottom: 1px solid #E5E7EB; padding: 0 20px; }
  .tab { padding: 10px 0; margin-right: 24px; font-size: 14px; font-weight: 400; color: #9CA3AF; background: none; border: none; border-bottom: 2px solid transparent; margin-bottom: -1px; cursor: pointer; }
  .tab.active { font-weight: 600; color: #111; border-bottom-color: #111; }

  .section { padding: 20px; display: none; }
  .section.active { display: block; }

  .card { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
  .card-img { width: 100%; aspect-ratio: 4/3; object-fit: cover; display: block; background: #F3F4F6; }
  .card-img-missing { width: 100%; aspect-ratio: 4/3; background: #F3F4F6; display: flex; align-items: center; justify-content: center; font-size: 13px; color: #9CA3AF; }
  .card-body { padding: 14px 16px; }
  .card-price { font-size: 24px; font-weight: 700; margin-bottom: 2px; }
  .card-loc { font-size: 14px; color: #6B7280; margin-bottom: 10px; }
  .card-meta { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
  .badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 20px; }
  .badge-score { background: #EFF6FF; color: #1D4ED8; }
  .badge-cat { background: #F3F4F6; color: #374151; }
  .card-headline { font-size: 12px; color: #9CA3AF; line-height: 1.5; margin-bottom: 8px; }
  .card-link { font-size: 12px; color: #1D4ED8; text-decoration: none; }

  .actions { border-top: 1px solid #F3F4F6; padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; }
  .actions-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

  button { font-family: inherit; font-size: 13px; font-weight: 500; padding: 10px 14px; border-radius: 8px; border: 1px solid #D1D5DB; background: #fff; color: #111; cursor: pointer; width: 100%; line-height: 1.4; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.approve { background: #F0FDF4; color: #166534; border-color: #86EFAC; }
  button.fb { background: #EFF6FF; color: #1D4ED8; border-color: #93C5FD; }
  button.ig { background: #FAF5FF; color: #6B21A8; border-color: #C4B5FD; }
  button.skip { background: #FEF2F2; color: #991B1B; border-color: #FECACA; }
  button.primary { background: #111; color: #fff; border-color: #111; }

  .counter { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .counter-text { font-size: 13px; color: #6B7280; }
  .refresh-btn { font-size: 12px; color: #6B7280; background: none; border: none; cursor: pointer; width: auto; padding: 0; font-weight: 400; }

  .empty { text-align: center; padding: 3rem 1rem; }
  .empty-icon { font-size: 32px; margin-bottom: 12px; }
  .empty-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
  .empty-sub { font-size: 13px; color: #6B7280; margin-bottom: 20px; }

  .spinner { text-align: center; padding: 3rem 1rem; color: #9CA3AF; font-size: 13px; }
  .spinner-ring { width: 24px; height: 24px; border: 2px solid #E5E7EB; border-top-color: #111; border-radius: 50%; animation: spin 0.7s linear infinite; margin: 0 auto 12px; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .form-group { margin-bottom: 16px; }
  .form-group label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 5px; }
  .form-group input[type="text"], .form-group input[type="date"] {
    width: 100%; padding: 9px 12px; font-size: 14px; font-family: inherit;
    border: 1px solid #D1D5DB; border-radius: 8px; background: #fff; color: #111;
  }
  .form-group input:focus { outline: none; border-color: #111; }

  .check-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px; }
  .check-row input[type="checkbox"] { width: 16px; height: 16px; margin-top: 2px; accent-color: #111; cursor: pointer; flex-shrink: 0; }
  .check-label { cursor: pointer; }
  .check-label-main { font-size: 13px; font-weight: 500; color: #111; }
  .check-label-sub { font-size: 12px; color: #9CA3AF; margin-top: 2px; }

  .date-indent { padding-left: 26px; margin-bottom: 12px; }
  .date-hint { font-size: 11px; color: #9CA3AF; margin-top: 4px; }

  .divider { height: 1px; background: #E5E7EB; margin: 24px 0; }
  .section-label { font-size: 11px; font-weight: 600; color: #9CA3AF; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 12px; }

  .req-card { padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; }
  .req-card.pending    { background: #FEF9EC; border: 1px solid #F5D87A; }
  .req-card.processing { background: #EFF6FF; border: 1px solid #BFDBFE; }
  .req-card.done       { background: #F0FDF4; border: 1px solid #BBF7D0; }
  .req-card.failed     { background: #FEF2F2; border: 1px solid #FECACA; }
  .req-address { font-size: 13px; font-weight: 500; margin-bottom: 3px; }
  .req-meta { font-size: 11px; opacity: 0.8; }
  .req-card.pending    .req-address, .req-card.pending    .req-meta { color: #92680A; }
  .req-card.processing .req-address, .req-card.processing .req-meta { color: #1D4ED8; }
  .req-card.done       .req-address, .req-card.done       .req-meta { color: #166534; }
  .req-card.failed     .req-address, .req-card.failed     .req-meta { color: #991B1B; }

  .toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: #111; color: #fff; font-size: 13px; font-weight: 500; padding: 10px 20px; border-radius: 8px; white-space: nowrap; opacity: 0; transition: opacity 0.2s; pointer-events: none; z-index: 999; }
  .toast.show { opacity: 1; }

  .error-msg { font-size: 13px; color: #991B1B; margin-bottom: 16px; line-height: 1.5; }
</style>
</head>
<body>

<div class="header">
  <div class="header-eyebrow">HousesUnder150K</div>
  <div class="header-title">Operator</div>
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab('queue')">Approval queue</button>
  <button class="tab" onclick="switchTab('add')">Add listing</button>
</div>

<!-- Queue tab -->
<div id="tab-queue" class="section active">
  <div class="counter">
    <span class="counter-text" id="queue-counter"></span>
    <button class="refresh-btn" onclick="loadQueue()">Refresh</button>
  </div>
  <div id="queue-content"></div>
</div>

<!-- Add listing tab -->
<div id="tab-add" class="section">
  <div class="form-group">
    <label for="address">Property address</label>
    <input type="text" id="address" placeholder="123 Main St, Springfield, IL 62701" />
  </div>

  <div class="check-row">
    <input type="checkbox" id="chk-dod" onchange="toggleDodDate()" />
    <label for="chk-dod" class="check-label">
      <div class="check-label-main">Set as Deal of the Day</div>
      <div class="check-label-sub">Auto-assigns today or tomorrow if today is taken</div>
    </label>
  </div>
  <div id="dod-date-wrap" class="date-indent" style="display:none">
    <input type="date" id="dod-date" />
    <div class="date-hint">Leave blank to auto-assign. Set a date to target a specific day.</div>
  </div>

  <div class="check-row">
    <input type="checkbox" id="chk-fb" />
    <label for="chk-fb" class="check-label">
      <div class="check-label-main">Approve for Facebook</div>
    </label>
  </div>
  <div class="check-row">
    <input type="checkbox" id="chk-ig" />
    <label for="chk-ig" class="check-label">
      <div class="check-label-main">Approve for Instagram</div>
    </label>
  </div>

  <button class="primary" id="submit-btn" onclick="submitListing()">Submit listing</button>

  <div class="divider"></div>
  <div class="section-label">Recent requests</div>
  <div id="requests-content"><p style="font-size:13px;color:#9CA3AF">Loading...</p></div>
</div>

<div class="toast" id="toast"></div>

<script>
  const CATS = {
    HISTORIC:'Historic', ACREAGE:'Acreage', CHARACTER:'Character',
    WATERFRONT:'Waterfront', RENOVATED:'Renovated', HIDDEN_GEM:'Hidden gem',
    WHAT_IF:'What if', NEW_CONSTRUCTION:'New construction',
  };

  let queue = [];
  let qIdx  = 0;
  let working = false;

  // ── Toast ────────────────────────────────────────────────────────────────
  let toastTimer;
  function showToast(msg, duration) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), duration || 2200);
  }

  // ── Tabs ─────────────────────────────────────────────────────────────────
  function switchTab(name) {
    document.querySelectorAll('.tab').forEach((t, i) => {
      t.classList.toggle('active', ['queue','add'][i] === name);
    });
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    if (name === 'add') loadRequests();
  }

  // ── API calls ────────────────────────────────────────────────────────────
  async function api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch('/api' + path, opts);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  // ── Queue ────────────────────────────────────────────────────────────────
  async function loadQueue() {
    document.getElementById('queue-counter').textContent = '';
    document.getElementById('queue-content').innerHTML = spinner();
    try {
      const data = await api('GET', '/queue');
      queue = data.rows || [];
      qIdx  = 0;
      renderCard();
    } catch(e) {
      document.getElementById('queue-content').innerHTML =
        '<div class="error-msg">' + e.message.slice(0,120) + '</div>' +
        '<button onclick="loadQueue()">Retry</button>';
    }
  }

  function renderCard() {
    const remaining = queue.length - qIdx;
    const counter   = document.getElementById('queue-counter');
    const content   = document.getElementById('queue-content');

    if (remaining <= 0) {
      counter.textContent = '';
      content.innerHTML = '<div class="empty">' +
        '<div class="empty-icon">✓</div>' +
        '<div class="empty-title">Queue is clear</div>' +
        '<div class="empty-sub">All listings reviewed.</div>' +
        '<button onclick="loadQueue()">Refresh</button>' +
        '</div>';
      return;
    }

    counter.textContent = remaining + ' listing' + (remaining !== 1 ? 's' : '') + ' remaining';
    const l = queue[qIdx];
    const price    = l.price ? '$' + Number(l.price).toLocaleString() : '—';
    const loc      = [l.city, l.state].filter(Boolean).join(', ');
    const catLabel = CATS[l.category] || (l.category || '').toLowerCase().replace(/_/g,' ');

    const imgHtml = l.hero_image_url
      ? '<img class="card-img" src="' + l.hero_image_url + '" alt="' + loc + '" onerror="this.outerHTML=\'<div class=\\"card-img-missing\\">No image</div>\'" />'
      : '<div class="card-img-missing">No image</div>';

    content.innerHTML = '<div class="card">' +
      imgHtml +
      '<div class="card-body">' +
        '<div class="card-price">' + price + '</div>' +
        '<div class="card-loc">' + loc + '</div>' +
        '<div class="card-meta">' +
          '<span class="badge badge-score">Score ' + (l.score || '?') + '</span>' +
          '<span class="badge badge-cat">' + catLabel + '</span>' +
        '</div>' +
        (l.headline ? '<div class="card-headline">' + l.headline + '</div>' : '') +
        '<a class="card-link" href="https://housesunder150k.com/listings/' + l.slug + '" target="_blank" rel="noreferrer">View on site →</a>' +
      '</div>' +
      '<div class="actions">' +
        '<button class="approve" onclick="doApprove(\'' + l.slug + '\', true, true)">Approve — Facebook + Instagram</button>' +
        '<div class="actions-row">' +
          '<button class="fb" onclick="doApprove(\'' + l.slug + '\', true, false)">Facebook only</button>' +
          '<button class="ig" onclick="doApprove(\'' + l.slug + '\', false, true)">Instagram only</button>' +
        '</div>' +
        '<button class="skip" onclick="doSkip(\'' + l.slug + '\')">Not this one</button>' +
      '</div>' +
    '</div>';
  }

  async function doApprove(slug, fb, ig) {
    if (working) return;
    working = true;
    setActionBtns(true);
    try {
      await api('POST', '/approve/' + slug, { facebook: fb, instagram: ig });
      const label = fb && ig ? 'Approved — FB + IG' : fb ? 'Approved — Facebook' : 'Approved — Instagram';
      showToast(label);
      qIdx++;
      renderCard();
    } catch(e) { showToast('Error: ' + e.message.slice(0,60)); }
    working = false;
    setActionBtns(false);
  }

  async function doSkip(slug) {
    if (working) return;
    working = true;
    setActionBtns(true);
    try {
      await api('POST', '/skip/' + slug);
      showToast('Skipped permanently');
      qIdx++;
      renderCard();
    } catch(e) { showToast('Error: ' + e.message.slice(0,60)); }
    working = false;
    setActionBtns(false);
  }

  function setActionBtns(disabled) {
    document.querySelectorAll('.actions button').forEach(b => b.disabled = disabled);
  }

  // ── Add listing ───────────────────────────────────────────────────────────
  function toggleDodDate() {
    const checked = document.getElementById('chk-dod').checked;
    document.getElementById('dod-date-wrap').style.display = checked ? 'block' : 'none';
  }

  async function submitListing() {
    const address = document.getElementById('address').value.trim();
    if (!address) { showToast('Enter an address first'); return; }
    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = 'Submitting...';
    try {
      const isDod   = document.getElementById('chk-dod').checked;
      const dodDate = document.getElementById('dod-date').value || null;
      await api('POST', '/requests', {
        address,
        is_deal_of_day:   isDod,
        deal_of_day_date: isDod && dodDate ? dodDate : null,
        post_facebook:    document.getElementById('chk-fb').checked,
        post_instagram:   document.getElementById('chk-ig').checked,
      });
      showToast('Submitted — pipeline picks it up within 30 min', 3000);
      document.getElementById('address').value = '';
      document.getElementById('chk-dod').checked = false;
      document.getElementById('chk-fb').checked  = false;
      document.getElementById('chk-ig').checked  = false;
      document.getElementById('dod-date-wrap').style.display = 'none';
      loadRequests();
    } catch(e) { showToast('Error: ' + e.message.slice(0,60)); }
    btn.disabled = false;
    btn.textContent = 'Submit listing';
  }

  async function loadRequests() {
    document.getElementById('requests-content').innerHTML = '<p style="font-size:13px;color:#9CA3AF">Loading...</p>';
    try {
      const data = await api('GET', '/requests');
      const rows = data.rows || [];
      if (!rows.length) {
        document.getElementById('requests-content').innerHTML = '<p style="font-size:13px;color:#9CA3AF">No requests yet.</p>';
        return;
      }
      document.getElementById('requests-content').innerHTML = rows.map(req => {
        const flags = [req.post_facebook && 'FB', req.post_instagram && 'IG', req.is_deal_of_day && 'DoD'].filter(Boolean).join(' · ');
        const detail = req.status === 'done' && req.result_slug ? req.result_slug
          : req.status === 'failed' && req.error_message ? req.error_message.slice(0,60) : '';
        return '<div class="req-card ' + req.status + '">' +
          '<div class="req-address">' + req.address + '</div>' +
          '<div class="req-meta">' + req.status.toUpperCase() + (flags ? ' · ' + flags : '') + (detail ? ' · ' + detail : '') + '</div>' +
          '</div>';
      }).join('');
    } catch(e) {
      document.getElementById('requests-content').innerHTML = '<p class="error-msg">Error loading requests.</p>';
    }
  }

  function spinner() {
    return '<div class="spinner"><div class="spinner-ring"></div>Loading...</div>';
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  loadQueue();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def serve_app(_: str = Depends(require_auth)):
    return HTML


@app.get("/health")
def health():
    return {"ok": True}
