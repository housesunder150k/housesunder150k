"""
HousesUnder150K.com — Operator App
Internal tool for FB/IG listing approval and manual listing injection.

Runs as a Railway web service (not a cron).
Serves a login page + single-page HTML app + JSON API.

Auth flow:
  1. Browser hits any route — if no valid session cookie, redirects to /login
  2. /login renders a username/password form
  3. POST /login validates credentials, sets HttpOnly + Secure + SameSite=Strict
     session cookie (HMAC-signed, 12-hour expiry)
  4. All subsequent page loads and fetch() calls send the cookie automatically
  5. No credentials ever appear in HTML source, JS variables, or DevTools

Session cookie is HMAC-SHA256 signed with SESSION_SECRET.
Cannot be forged without the secret. HttpOnly = JS cannot read it.

Environment variables required:
  OPERATOR_USER      — login username
  OPERATOR_PASS      — login password
  SESSION_SECRET     — random hex string for HMAC signing
                       generate: python -c "import secrets; print(secrets.token_hex(32))"
  SUPABASE_URL       — HousesUnder150K Supabase project URL
  SUPABASE_KEY       — Supabase service role key (bypasses RLS)
  PORT               — set automatically by Railway

Start command: uvicorn scripts.operator_app:app --host 0.0.0.0 --port $PORT

Changes:
  2026-09-07: Initial implementation
  2026-09-07: Replaced Basic Auth + embedded credentials with HttpOnly session cookie
"""

import os
import secrets
import hashlib
import hmac
import logging
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OPERATOR_USER  = os.environ["OPERATOR_USER"]
OPERATOR_PASS  = os.environ["OPERATOR_PASS"]
SESSION_SECRET = os.environ["SESSION_SECRET"]
SUPABASE_URL   = os.environ["SUPABASE_URL"]
SUPABASE_KEY   = os.environ["SUPABASE_KEY"]

SESSION_COOKIE  = "hu150k_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours in seconds

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _sign(payload: str) -> str:
    return hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_session_token(username: str) -> str:
    ts = int(datetime.now(timezone.utc).timestamp())
    payload = f"{username}:{ts}"
    return f"{payload}:{_sign(payload)}"


def verify_session_token(token: str) -> str | None:
    """Return username if token is valid and unexpired, else None."""
    try:
        parts = token.rsplit(":", 1)          # split off sig from right
        if len(parts) != 2:
            return None
        payload, sig = parts
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        username, ts_str = payload.rsplit(":", 1)
        age = int(datetime.now(timezone.utc).timestamp()) - int(ts_str)
        if age > SESSION_MAX_AGE:
            return None
        return username
    except Exception:
        return None


def get_session(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return verify_session_token(token)


def require_session(request: Request) -> str:
    """Dependency for API routes — raises 401 if no valid session."""
    username = get_session(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def sb_get(path: str, params: dict) -> list:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers=_sb_headers(), params=params, timeout=10,
    )
    r.raise_for_status()
    return r.json()


def sb_patch(path: str, match: dict, body: dict) -> None:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers=_sb_headers(),
        params={k: f"eq.{v}" for k, v in match.items()},
        json=body, timeout=10,
    )
    r.raise_for_status()


def sb_post(path: str, body: dict) -> list:
    headers = {**_sb_headers(), "Prefer": "return=representation"}
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers=headers, json=body, timeout=10,
    )
    r.raise_for_status()
    return r.json()

# ---------------------------------------------------------------------------
# Login routes
# ---------------------------------------------------------------------------

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>HousesUnder150K — Operator</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #F9FAFB; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; padding: 24px; }
  .card { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px;
          padding: 32px 28px; width: 100%; max-width: 360px; }
  .eyebrow { font-size: 11px; font-weight: 600; color: #9CA3AF;
             letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 4px; }
  h1 { font-size: 20px; font-weight: 700; color: #111; margin-bottom: 28px; }
  label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 5px; }
  input { width: 100%; padding: 10px 12px; font-size: 15px; font-family: inherit;
          border: 1px solid #D1D5DB; border-radius: 8px; background: #fff;
          color: #111; margin-bottom: 16px; -webkit-appearance: none; }
  input:focus { outline: none; border-color: #111; }
  button { width: 100%; padding: 12px; font-size: 15px; font-weight: 600;
           font-family: inherit; background: #111; color: #fff; border: none;
           border-radius: 8px; cursor: pointer; margin-top: 4px; }
  .error { font-size: 13px; color: #991B1B; margin-top: 14px;
           background: #FEF2F2; border: 1px solid #FECACA;
           border-radius: 8px; padding: 10px 12px; text-align: center; }
</style>
</head>
<body>
<div class="card">
  <div class="eyebrow">HousesUnder150K</div>
  <h1>Operator</h1>
  <form method="POST" action="/login">
    <label for="u">Username</label>
    <input type="text" id="u" name="username"
           autocomplete="username" autocapitalize="none" required />
    <label for="p">Password</label>
    <input type="password" id="p" name="password"
           autocomplete="current-password" required />
    <button type="submit">Sign in</button>
  </form>
  {ERROR}
</div>
</body>
</html>"""


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_session(request):
        return RedirectResponse("/", status_code=302)
    return LOGIN_HTML.replace("{ERROR}", "")


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = (form.get("password") or "").strip()
    ok_user = secrets.compare_digest(username.encode(), OPERATOR_USER.encode())
    ok_pass = secrets.compare_digest(password.encode(), OPERATOR_PASS.encode())
    if not (ok_user and ok_pass):
        error = '<div class="error">Incorrect username or password.</div>'
        return HTMLResponse(LOGIN_HTML.replace("{ERROR}", error), status_code=401)
    token = make_session_token(username)
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,       # JS cannot read this cookie
        secure=True,         # HTTPS only (Railway always serves HTTPS)
        samesite="strict",   # Never sent cross-site
    )
    log.info(f"Login: {username}")
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response

# ---------------------------------------------------------------------------
# API routes — all require valid session cookie
# ---------------------------------------------------------------------------

@app.get("/api/queue")
def get_queue(_: str = Depends(require_session)):
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
async def approve_listing(slug: str, request: Request, _: str = Depends(require_session)):
    body = await request.json()
    fb = bool(body.get("facebook", False))
    ig = bool(body.get("instagram", False))
    if not fb and not ig:
        raise HTTPException(status_code=400, detail="At least one platform required")
    sb_patch("published_listings", {"slug": slug}, {
        "fb_ig_approved_facebook": fb,
        "fb_ig_approved_instagram": ig,
    })
    log.info(f"Approved {slug} fb={fb} ig={ig}")
    return JSONResponse({"ok": True})


@app.post("/api/skip/{slug}")
def skip_listing(slug: str, _: str = Depends(require_session)):
    sb_patch("published_listings", {"slug": slug}, {"fb_ig_skipped": True})
    log.info(f"Skipped {slug}")
    return JSONResponse({"ok": True})


@app.get("/api/requests")
def get_requests(_: str = Depends(require_session)):
    rows = sb_get("manual_listing_requests", {
        "select": "id,address,status,is_deal_of_day,post_facebook,post_instagram,created_at,result_slug,error_message",
        "order": "created_at.desc",
        "limit": "10",
    })
    return JSONResponse({"rows": rows})


@app.post("/api/requests")
async def create_request(request: Request, _: str = Depends(require_session)):
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
    log.info(f"Manual request: {address}")
    return JSONResponse({"ok": True, "id": result[0]["id"] if result else None})

# ---------------------------------------------------------------------------
# Main app — requires session, served at /
# ---------------------------------------------------------------------------

APP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>HousesUnder150K — Operator</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #F9FAFB; color: #111; min-height: 100vh; }

  .header { padding: 16px 20px 0; display: flex; justify-content: space-between; align-items: flex-start; }
  .header-left .eyebrow { font-size: 11px; font-weight: 600; color: #9CA3AF;
                           letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 2px; }
  .header-left .title { font-size: 20px; font-weight: 700; margin-bottom: 16px; }
  .logout-btn { font-size: 12px; color: #9CA3AF; background: none; border: none;
                cursor: pointer; padding: 4px 0; margin-top: 2px; }

  .tabs { display: flex; border-bottom: 1px solid #E5E7EB; padding: 0 20px; }
  .tab { padding: 10px 0; margin-right: 24px; font-size: 14px; font-weight: 400;
         color: #9CA3AF; background: none; border: none;
         border-bottom: 2px solid transparent; margin-bottom: -1px; cursor: pointer; width: auto; }
  .tab.active { font-weight: 600; color: #111; border-bottom-color: #111; }

  .section { padding: 20px; display: none; }
  .section.active { display: block; }

  .card { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px;
          overflow: hidden; margin-bottom: 16px; }
  .card-img { width: 100%; aspect-ratio: 4/3; object-fit: cover; display: block; }
  .no-img { width: 100%; aspect-ratio: 4/3; background: #F3F4F6;
            display: flex; align-items: center; justify-content: center;
            font-size: 13px; color: #9CA3AF; }
  .card-body { padding: 14px 16px; }
  .card-price { font-size: 24px; font-weight: 700; margin-bottom: 2px; }
  .card-loc { font-size: 14px; color: #6B7280; margin-bottom: 10px; }
  .card-meta { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
  .badge { display: inline-block; font-size: 11px; font-weight: 600;
           padding: 2px 8px; border-radius: 20px; }
  .badge-score { background: #EFF6FF; color: #1D4ED8; }
  .badge-cat { background: #F3F4F6; color: #374151; }
  .card-headline { font-size: 12px; color: #9CA3AF; line-height: 1.5; margin-bottom: 8px; }
  .card-link { font-size: 12px; color: #1D4ED8; text-decoration: none; }

  .actions { border-top: 1px solid #F3F4F6; padding: 12px 16px;
             display: flex; flex-direction: column; gap: 8px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

  button { font-family: inherit; font-size: 13px; font-weight: 500; padding: 10px 14px;
           border-radius: 8px; border: 1px solid #D1D5DB; background: #fff;
           color: #111; cursor: pointer; width: 100%; line-height: 1.4; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-approve { background: #F0FDF4; color: #166534; border-color: #86EFAC; }
  .btn-fb { background: #EFF6FF; color: #1D4ED8; border-color: #93C5FD; }
  .btn-ig { background: #FAF5FF; color: #6B21A8; border-color: #C4B5FD; }
  .btn-skip { background: #FEF2F2; color: #991B1B; border-color: #FECACA; }
  .btn-primary { background: #111; color: #fff; border-color: #111; }

  .counter { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .counter span { font-size: 13px; color: #6B7280; }
  .btn-refresh { font-size: 12px; color: #6B7280; background: none; border: none;
                 cursor: pointer; width: auto; padding: 0; }

  .empty { text-align: center; padding: 3rem 1rem; }
  .empty-icon { font-size: 32px; margin-bottom: 12px; }
  .empty-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
  .empty-sub { font-size: 13px; color: #6B7280; margin-bottom: 20px; }

  .spinner { text-align: center; padding: 3rem 1rem; color: #9CA3AF; font-size: 13px; }
  .ring { width: 24px; height: 24px; border: 2px solid #E5E7EB; border-top-color: #111;
          border-radius: 50%; animation: spin 0.7s linear infinite; margin: 0 auto 12px; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .form-group { margin-bottom: 16px; }
  .form-group label { display: block; font-size: 12px; font-weight: 600;
                      color: #374151; margin-bottom: 5px; }
  .form-group input[type="text"] {
    width: 100%; padding: 10px 12px; font-size: 15px; font-family: inherit;
    border: 1px solid #D1D5DB; border-radius: 8px; background: #fff;
    color: #111; -webkit-appearance: none;
  }
  input[type="date"] {
    padding: 8px 10px; font-size: 14px; font-family: inherit;
    border: 1px solid #D1D5DB; border-radius: 8px; background: #fff; color: #111;
  }
  input:focus { outline: none; border-color: #111; }

  .check-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 14px; }
  .check-row input[type="checkbox"] { width: 18px; height: 18px; margin-top: 1px;
                                       accent-color: #111; cursor: pointer; flex-shrink: 0; }
  .check-row label { cursor: pointer; }
  .check-main { font-size: 14px; font-weight: 500; color: #111; }
  .check-sub { font-size: 12px; color: #9CA3AF; margin-top: 2px; }

  .date-indent { padding-left: 28px; margin-bottom: 14px; }
  .date-hint { font-size: 11px; color: #9CA3AF; margin-top: 5px; }

  .divider { height: 1px; background: #E5E7EB; margin: 24px 0; }
  .section-label { font-size: 11px; font-weight: 600; color: #9CA3AF;
                   letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 12px; }

  .req-card { padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; }
  .req-card.pending    { background: #FEF9EC; border: 1px solid #F5D87A; color: #92680A; }
  .req-card.processing { background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8; }
  .req-card.done       { background: #F0FDF4; border: 1px solid #BBF7D0; color: #166534; }
  .req-card.failed     { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; }
  .req-addr { font-size: 13px; font-weight: 500; margin-bottom: 3px; }
  .req-meta { font-size: 11px; opacity: 0.8; }

  .err { font-size: 13px; color: #991B1B; margin-bottom: 16px; line-height: 1.5; }

  .toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
           background: #111; color: #fff; font-size: 13px; font-weight: 500;
           padding: 10px 20px; border-radius: 8px; white-space: nowrap;
           opacity: 0; transition: opacity 0.2s; pointer-events: none; z-index: 999; }
  .toast.show { opacity: 1; }
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="eyebrow">HousesUnder150K</div>
    <div class="title">Operator</div>
  </div>
  <form method="POST" action="/logout" style="margin-top:4px">
    <button class="logout-btn" type="submit">Sign out</button>
  </form>
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab('queue')">Approval queue</button>
  <button class="tab" onclick="switchTab('add')">Add listing</button>
</div>

<div id="tab-queue" class="section active">
  <div class="counter">
    <span id="q-count"></span>
    <button class="btn-refresh" onclick="loadQueue()">Refresh</button>
  </div>
  <div id="q-content"></div>
</div>

<div id="tab-add" class="section">
  <div class="form-group">
    <label for="addr">Property address</label>
    <input type="text" id="addr" placeholder="123 Main St, Springfield, IL 62701"
           autocomplete="off" autocorrect="off" autocapitalize="words" />
  </div>

  <div class="check-row">
    <input type="checkbox" id="chk-dod" onchange="toggleDodDate()" />
    <label for="chk-dod">
      <div class="check-main">Set as Deal of the Day</div>
      <div class="check-sub">Auto-assigns today or tomorrow if today is taken</div>
    </label>
  </div>
  <div id="dod-wrap" class="date-indent" style="display:none">
    <input type="date" id="dod-date" />
    <div class="date-hint">Leave blank to auto-assign. Set a date to target a specific day.</div>
  </div>

  <div class="check-row">
    <input type="checkbox" id="chk-fb" />
    <label for="chk-fb"><div class="check-main">Approve for Facebook</div></label>
  </div>
  <div class="check-row">
    <input type="checkbox" id="chk-ig" />
    <label for="chk-ig"><div class="check-main">Approve for Instagram</div></label>
  </div>

  <button class="btn-primary" id="submit-btn" onclick="submitListing()">Submit listing</button>

  <div class="divider"></div>
  <div class="section-label">Recent requests</div>
  <div id="req-content"><p style="font-size:13px;color:#9CA3AF">Loading...</p></div>
</div>

<div class="toast" id="toast"></div>

<script>
const CATS = {
  HISTORIC:'Historic', ACREAGE:'Acreage', CHARACTER:'Character',
  WATERFRONT:'Waterfront', RENOVATED:'Renovated', HIDDEN_GEM:'Hidden gem',
  WHAT_IF:'What if', NEW_CONSTRUCTION:'New construction',
};

let queue = [], qIdx = 0, working = false, toastTimer;

// Toast
function showToast(msg, ms) {
  const el = document.getElementById('toast');
  el.textContent = msg; el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), ms || 2200);
}

// Tabs
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t, i) => {
    t.classList.toggle('active', ['queue','add'][i] === name);
  });
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (name === 'add') loadRequests();
}

// API — session cookie sent automatically (same-origin, httpOnly)
async function api(method, path, body) {
  const opts = {
    method,
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch('/api' + path, opts);
  if (r.status === 401) { window.location.href = '/login'; return null; }
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// Queue
async function loadQueue() {
  document.getElementById('q-count').textContent = '';
  document.getElementById('q-content').innerHTML = spinner();
  try {
    const data = await api('GET', '/queue');
    if (!data) return;
    queue = data.rows || []; qIdx = 0;
    renderCard();
  } catch(e) {
    document.getElementById('q-content').innerHTML =
      '<div class="err">' + e.message.slice(0,120) + '</div>' +
      '<button onclick="loadQueue()">Retry</button>';
  }
}

function renderCard() {
  const rem = queue.length - qIdx;
  document.getElementById('q-count').textContent =
    rem > 0 ? rem + ' listing' + (rem !== 1 ? 's' : '') + ' remaining' : '';
  const el = document.getElementById('q-content');
  if (rem <= 0) {
    el.innerHTML = '<div class="empty"><div class="empty-icon">\u2713</div>' +
      '<div class="empty-title">Queue is clear</div>' +
      '<div class="empty-sub">All listings reviewed.</div>' +
      '<button onclick="loadQueue()">Refresh</button></div>';
    return;
  }
  const l = queue[qIdx];
  const price = l.price ? '$' + Number(l.price).toLocaleString() : '\u2014';
  const loc = [l.city, l.state].filter(Boolean).join(', ');
  const cat = CATS[l.category] || (l.category || '').toLowerCase().replace(/_/g,' ');
  const img = l.hero_image_url
    ? '<img class="card-img" src="' + l.hero_image_url + '" alt="' + loc + '" ' +
      'onerror="this.outerHTML=\'<div class=\\"no-img\\">No image</div>\'" />'
    : '<div class="no-img">No image</div>';
  const slug = l.slug.replace(/'/g, "\\'");
  el.innerHTML =
    '<div class="card">' + img +
    '<div class="card-body">' +
      '<div class="card-price">' + price + '</div>' +
      '<div class="card-loc">' + loc + '</div>' +
      '<div class="card-meta">' +
        '<span class="badge badge-score">Score ' + (l.score || '?') + '</span>' +
        '<span class="badge badge-cat">' + cat + '</span>' +
      '</div>' +
      (l.headline ? '<div class="card-headline">' + l.headline + '</div>' : '') +
      '<a class="card-link" href="https://housesunder150k.com/listings/' + l.slug + '" ' +
      'target="_blank" rel="noreferrer">View on site \u2192</a>' +
    '</div>' +
    '<div class="actions">' +
      '<button class="btn-approve" onclick="doApprove(\'' + slug + '\',true,true)">Approve \u2014 Facebook + Instagram</button>' +
      '<div class="two-col">' +
        '<button class="btn-fb" onclick="doApprove(\'' + slug + '\',true,false)">Facebook only</button>' +
        '<button class="btn-ig" onclick="doApprove(\'' + slug + '\',false,true)">Instagram only</button>' +
      '</div>' +
      '<button class="btn-skip" onclick="doSkip(\'' + slug + '\')">Not this one</button>' +
    '</div></div>';
}

async function doApprove(slug, fb, ig) {
  if (working) return; working = true; setBtns(true);
  try {
    await api('POST', '/approve/' + slug, { facebook: fb, instagram: ig });
    showToast(fb && ig ? 'Approved \u2014 FB + IG' : fb ? 'Approved \u2014 Facebook' : 'Approved \u2014 Instagram');
    qIdx++; renderCard();
  } catch(e) { showToast('Error: ' + e.message.slice(0,60)); }
  working = false; setBtns(false);
}

async function doSkip(slug) {
  if (working) return; working = true; setBtns(true);
  try {
    await api('POST', '/skip/' + slug);
    showToast('Skipped permanently'); qIdx++; renderCard();
  } catch(e) { showToast('Error: ' + e.message.slice(0,60)); }
  working = false; setBtns(false);
}

function setBtns(d) {
  document.querySelectorAll('.actions button').forEach(b => b.disabled = d);
}

// Add listing
function toggleDodDate() {
  document.getElementById('dod-wrap').style.display =
    document.getElementById('chk-dod').checked ? 'block' : 'none';
}

async function submitListing() {
  const addr = document.getElementById('addr').value.trim();
  if (!addr) { showToast('Enter an address first'); return; }
  const btn = document.getElementById('submit-btn');
  btn.disabled = true; btn.textContent = 'Submitting...';
  try {
    const isDod = document.getElementById('chk-dod').checked;
    const dodDate = document.getElementById('dod-date').value || null;
    const res = await api('POST', '/requests', {
      address: addr,
      is_deal_of_day: isDod,
      deal_of_day_date: isDod && dodDate ? dodDate : null,
      post_facebook: document.getElementById('chk-fb').checked,
      post_instagram: document.getElementById('chk-ig').checked,
    });
    if (!res) return;
    showToast('Submitted \u2014 pipeline picks it up within 30 min', 3000);
    document.getElementById('addr').value = '';
    ['chk-dod','chk-fb','chk-ig'].forEach(id => document.getElementById(id).checked = false);
    document.getElementById('dod-wrap').style.display = 'none';
    loadRequests();
  } catch(e) { showToast('Error: ' + e.message.slice(0,60)); }
  btn.disabled = false; btn.textContent = 'Submit listing';
}

async function loadRequests() {
  document.getElementById('req-content').innerHTML = '<p style="font-size:13px;color:#9CA3AF">Loading...</p>';
  try {
    const data = await api('GET', '/requests');
    if (!data) return;
    const rows = data.rows || [];
    if (!rows.length) {
      document.getElementById('req-content').innerHTML = '<p style="font-size:13px;color:#9CA3AF">No requests yet.</p>';
      return;
    }
    document.getElementById('req-content').innerHTML = rows.map(r => {
      const flags = [r.post_facebook && 'FB', r.post_instagram && 'IG', r.is_deal_of_day && 'DoD'].filter(Boolean).join(' \u00b7 ');
      const detail = r.status === 'done' && r.result_slug ? r.result_slug
        : r.status === 'failed' && r.error_message ? r.error_message.slice(0,60) : '';
      return '<div class="req-card ' + r.status + '">' +
        '<div class="req-addr">' + r.address + '</div>' +
        '<div class="req-meta">' + r.status.toUpperCase() +
        (flags ? ' \u00b7 ' + flags : '') + (detail ? ' \u00b7 ' + detail : '') +
        '</div></div>';
    }).join('');
  } catch(e) {
    document.getElementById('req-content').innerHTML = '<p class="err">Error loading requests.</p>';
  }
}

function spinner() {
  return '<div class="spinner"><div class="ring"></div>Loading...</div>';
}

loadQueue();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def serve_app(request: Request):
    if not get_session(request):
        return RedirectResponse("/login", status_code=302)
    return APP_HTML


@app.get("/health")
def health():
    return {"ok": True}
