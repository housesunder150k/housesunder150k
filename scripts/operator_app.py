"""
HousesUnder150K.com -- Operator App
Internal tool for FB/IG listing approval and manual listing injection.

Auth: login form -> HttpOnly session cookie (HMAC-signed, 12hr expiry).
No credentials in HTML, JS, or DOM at any point.

Env vars required:
  OPERATOR_USER, OPERATOR_PASS, SESSION_SECRET
  SUPABASE_URL, SUPABASE_KEY, PORT

Start: uvicorn scripts.operator_app:app --host 0.0.0.0 --port $PORT

Changes:
  2026-09-07: Initial build
  2026-09-07: HttpOnly session cookie auth
  2026-09-07: DOM-based card rendering (no innerHTML escaping bugs)
  2026-09-07: SameSite=Lax for iOS Safari redirect compat
  2026-09-07: Queue filter: today only, score 7+
"""

import os
import secrets
import hashlib
import hmac
import logging
from datetime import datetime, timezone

import requests
import pytz
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OPERATOR_USER  = os.environ["OPERATOR_USER"]
OPERATOR_PASS  = os.environ["OPERATOR_PASS"]
SESSION_SECRET = os.environ["SESSION_SECRET"]
SUPABASE_URL   = os.environ["SUPABASE_URL"]
SUPABASE_KEY   = os.environ["SUPABASE_KEY"]

SESSION_COOKIE  = "hu150k_session"
SESSION_MAX_AGE = 43200  # 12 hours

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def _sign(payload):
    return hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

def make_token(username):
    ts = int(datetime.now(timezone.utc).timestamp())
    payload = f"{username}:{ts}"
    return f"{payload}:{_sign(payload)}"

def verify_token(token):
    try:
        payload, sig = token.rsplit(":", 1)
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        username, ts_str = payload.rsplit(":", 1)
        if int(datetime.now(timezone.utc).timestamp()) - int(ts_str) > SESSION_MAX_AGE:
            return None
        return username
    except Exception:
        return None

def get_session(request):
    token = request.cookies.get(SESSION_COOKIE)
    return verify_token(token) if token else None

def require_session(request: Request):
    if not get_session(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return True

# ---------------------------------------------------------------------------
# App + Supabase
# ---------------------------------------------------------------------------

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

def _sb():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

def sb_get(path, params):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=_sb(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def sb_patch(path, match, body):
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers=_sb(),
        params={k: f"eq.{v}" for k, v in match.items()},
        json=body, timeout=10,
    )
    r.raise_for_status()

def sb_post(path, body):
    h = {**_sb(), "Prefer": "return=representation"}
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{path}", headers=h, json=body, timeout=10)
    r.raise_for_status()
    return r.json()

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

LOGIN = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Operator</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#F9FAFB;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}
.card{background:#fff;border:1px solid #E5E7EB;border-radius:12px;padding:32px 28px;width:100%;max-width:360px}
.ey{font-size:11px;font-weight:600;color:#9CA3AF;letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px}
h1{font-size:20px;font-weight:700;color:#111;margin-bottom:28px}
label{display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:5px}
input{width:100%;padding:10px 12px;font-size:15px;font-family:inherit;border:1px solid #D1D5DB;border-radius:8px;background:#fff;color:#111;margin-bottom:16px;-webkit-appearance:none}
input:focus{outline:none;border-color:#111}
button{width:100%;padding:12px;font-size:15px;font-weight:600;font-family:inherit;background:#111;color:#fff;border:none;border-radius:8px;cursor:pointer;margin-top:4px}
.err{font-size:13px;color:#991B1B;margin-top:14px;background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px 12px;text-align:center}
</style>
</head>
<body>
<div class="card">
  <div class="ey">HousesUnder150K</div>
  <h1>Operator</h1>
  <form method="POST" action="/login">
    <label for="u">Username</label>
    <input type="text" id="u" name="username" autocomplete="username" autocapitalize="none" required>
    <label for="p">Password</label>
    <input type="password" id="p" name="password" autocomplete="current-password" required>
    <button type="submit">Sign in</button>
  </form>
  ERROR_SLOT
</div>
</body>
</html>"""


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_session(request):
        return RedirectResponse("/", status_code=302)
    return LOGIN.replace("ERROR_SLOT", "")


@app.post("/login")
async def login_post(request: Request):
    form = await request.form()
    u = (form.get("username") or "").strip()
    p = (form.get("password") or "").strip()
    if not (secrets.compare_digest(u.encode(), OPERATOR_USER.encode()) and
            secrets.compare_digest(p.encode(), OPERATOR_PASS.encode())):
        err = '<div class="err">Incorrect username or password.</div>'
        return HTMLResponse(LOGIN.replace("ERROR_SLOT", err), status_code=401)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(SESSION_COOKIE, make_token(u),
                    max_age=SESSION_MAX_AGE, httponly=True, secure=True, samesite="lax")
    log.info(f"Login: {u}")
    return resp


@app.post("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(SESSION_COOKIE)
    return resp

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/queue")
def api_queue(_=Depends(require_session)):
    today = datetime.now(pytz.timezone("America/Chicago")).date().isoformat()
    rows = sb_get("published_listings", {
        "select": "slug,headline,price,city,state,category,score,hero_image_url",
        "fb_ig_approved_facebook": "eq.false",
        "fb_ig_approved_instagram": "eq.false",
        "fb_ig_skipped": "eq.false",
        "status": "eq.Active",
        "score": "gte.7",
        "published_date_ct": f"eq.{today}",
        "order": "score.desc,published_at.desc",
        "limit": "50",
    })
    return JSONResponse({"rows": rows})


@app.post("/api/approve/{slug}")
async def api_approve(slug: str, request: Request, _=Depends(require_session)):
    body = await request.json()
    fb = bool(body.get("facebook", False))
    ig = bool(body.get("instagram", False))
    if not fb and not ig:
        raise HTTPException(status_code=400, detail="At least one platform required")
    sb_patch("published_listings", {"slug": slug},
             {"fb_ig_approved_facebook": fb, "fb_ig_approved_instagram": ig})
    log.info(f"Approved {slug} fb={fb} ig={ig}")
    return JSONResponse({"ok": True})


@app.post("/api/skip/{slug}")
def api_skip(slug: str, _=Depends(require_session)):
    sb_patch("published_listings", {"slug": slug}, {"fb_ig_skipped": True})
    log.info(f"Skipped {slug}")
    return JSONResponse({"ok": True})


@app.get("/api/requests")
def api_requests(_=Depends(require_session)):
    rows = sb_get("manual_listing_requests", {
        "select": "id,address,status,is_deal_of_day,post_facebook,post_instagram,created_at,result_slug,error_message",
        "order": "created_at.desc",
        "limit": "10",
    })
    return JSONResponse({"rows": rows})


@app.post("/api/requests")
async def api_create_request(request: Request, _=Depends(require_session)):
    body = await request.json()
    address = (body.get("address") or "").strip()
    if not address:
        raise HTTPException(status_code=400, detail="address is required")
    result = sb_post("manual_listing_requests", {
        "address": address,
        "status": "pending",
        "is_deal_of_day": bool(body.get("is_deal_of_day", False)),
        "deal_of_day_date": body.get("deal_of_day_date") or None,
        "post_facebook": bool(body.get("post_facebook", False)),
        "post_instagram": bool(body.get("post_instagram", False)),
    })
    log.info(f"Manual request: {address}")
    return JSONResponse({"ok": True, "id": result[0]["id"] if result else None})

# ---------------------------------------------------------------------------
# Main app HTML -- JS uses DOM APIs only, no innerHTML string escaping
# ---------------------------------------------------------------------------

APP = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Operator</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#F9FAFB;color:#111;min-height:100vh}
.hdr{padding:16px 20px 0;display:flex;justify-content:space-between;align-items:flex-start}
.ey{font-size:11px;font-weight:600;color:#9CA3AF;letter-spacing:.08em;text-transform:uppercase;margin-bottom:2px}
.ti{font-size:20px;font-weight:700;margin-bottom:16px}
.lo{font-size:12px;color:#9CA3AF;background:none;border:none;cursor:pointer;padding:4px 0;margin-top:2px;width:auto}
.tabs{display:flex;border-bottom:1px solid #E5E7EB;padding:0 20px}
.tab{padding:10px 0;margin-right:24px;font-size:14px;font-weight:400;color:#9CA3AF;background:none;border:none;border-bottom:2px solid transparent;margin-bottom:-1px;cursor:pointer;width:auto}
.tab.on{font-weight:600;color:#111;border-bottom-color:#111}
.sec{padding:20px;display:none}
.sec.on{display:block}
.card{background:#fff;border:1px solid #E5E7EB;border-radius:12px;overflow:hidden;margin-bottom:16px}
.ci{width:100%;aspect-ratio:4/3;object-fit:cover;display:block}
.ni{width:100%;aspect-ratio:4/3;background:#F3F4F6;display:flex;align-items:center;justify-content:center;font-size:13px;color:#9CA3AF}
.cb{padding:14px 16px}
.cp{font-size:24px;font-weight:700;margin-bottom:2px}
.cl{font-size:14px;color:#6B7280;margin-bottom:10px}
.cm{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.bd{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:20px}
.bs{background:#EFF6FF;color:#1D4ED8}
.bc{background:#F3F4F6;color:#374151}
.ch{font-size:12px;color:#9CA3AF;line-height:1.5;margin-bottom:8px}
.ck{font-size:12px;color:#1D4ED8;text-decoration:none}
.act{border-top:1px solid #F3F4F6;padding:12px 16px;display:flex;flex-direction:column;gap:8px}
.tc{display:grid;grid-template-columns:1fr 1fr;gap:8px}
button{font-family:inherit;font-size:13px;font-weight:500;padding:10px 14px;border-radius:8px;border:1px solid #D1D5DB;background:#fff;color:#111;cursor:pointer;width:100%;line-height:1.4}
button:disabled{opacity:.5;cursor:not-allowed}
.ba{background:#F0FDF4;color:#166534;border-color:#86EFAC}
.bf{background:#EFF6FF;color:#1D4ED8;border-color:#93C5FD}
.bi{background:#FAF5FF;color:#6B21A8;border-color:#C4B5FD}
.bk{background:#FEF2F2;color:#991B1B;border-color:#FECACA}
.bp{background:#111;color:#fff;border-color:#111}
.ctr{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.ctr span{font-size:13px;color:#6B7280}
.br{font-size:12px;color:#6B7280;background:none;border:none;cursor:pointer;width:auto;padding:0}
.emp{text-align:center;padding:3rem 1rem}
.ei{font-size:32px;margin-bottom:12px}
.et{font-size:15px;font-weight:600;margin-bottom:6px}
.es{font-size:13px;color:#6B7280;margin-bottom:20px}
.spin{text-align:center;padding:3rem 1rem;color:#9CA3AF;font-size:13px}
.ring{width:24px;height:24px;border:2px solid #E5E7EB;border-top-color:#111;border-radius:50%;animation:sp .7s linear infinite;margin:0 auto 12px}
@keyframes sp{to{transform:rotate(360deg)}}
.fg{margin-bottom:16px}
.fg label{display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:5px}
.fg input[type=text]{width:100%;padding:10px 12px;font-size:15px;font-family:inherit;border:1px solid #D1D5DB;border-radius:8px;background:#fff;color:#111;-webkit-appearance:none}
input[type=date]{padding:8px 10px;font-size:14px;font-family:inherit;border:1px solid #D1D5DB;border-radius:8px;background:#fff;color:#111}
input:focus{outline:none;border-color:#111}
.cr{display:flex;align-items:flex-start;gap:10px;margin-bottom:14px}
.cr input[type=checkbox]{width:18px;height:18px;margin-top:1px;accent-color:#111;cursor:pointer;flex-shrink:0}
.cr label{cursor:pointer}
.cm2{font-size:14px;font-weight:500;color:#111}
.cs{font-size:12px;color:#9CA3AF;margin-top:2px}
.di{padding-left:28px;margin-bottom:14px}
.dh{font-size:11px;color:#9CA3AF;margin-top:5px}
.dv{height:1px;background:#E5E7EB;margin:24px 0}
.sl{font-size:11px;font-weight:600;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;margin-bottom:12px}
.rq{padding:10px 12px;border-radius:8px;margin-bottom:8px}
.rq.pending{background:#FEF9EC;border:1px solid #F5D87A;color:#92680A}
.rq.processing{background:#EFF6FF;border:1px solid #BFDBFE;color:#1D4ED8}
.rq.done{background:#F0FDF4;border:1px solid #BBF7D0;color:#166534}
.rq.failed{background:#FEF2F2;border:1px solid #FECACA;color:#991B1B}
.ra{font-size:13px;font-weight:500;margin-bottom:3px}
.rm{font-size:11px;opacity:.8}
.er{font-size:13px;color:#991B1B;margin-bottom:16px}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#111;color:#fff;font-size:13px;font-weight:500;padding:10px 20px;border-radius:8px;white-space:nowrap;opacity:0;transition:opacity .2s;pointer-events:none;z-index:999}
.toast.on{opacity:1}
</style>
</head>
<body>
<div class="hdr">
  <div>
    <div class="ey">HousesUnder150K</div>
    <div class="ti">Operator</div>
  </div>
  <form method="POST" action="/logout" style="margin-top:4px">
    <button class="lo" type="submit">Sign out</button>
  </form>
</div>
<div class="tabs">
  <button class="tab on" id="t-queue">Approval queue</button>
  <button class="tab" id="t-add">Add listing</button>
</div>
<div id="s-queue" class="sec on">
  <div class="ctr"><span id="qcount"></span><button class="br" id="btn-refresh">Refresh</button></div>
  <div id="qcontent"></div>
</div>
<div id="s-add" class="sec">
  <div class="fg">
    <label for="addr">Property address</label>
    <input type="text" id="addr" placeholder="123 Main St, Springfield, IL 62701" autocomplete="off" autocorrect="off" autocapitalize="words">
  </div>
  <div class="cr">
    <input type="checkbox" id="chk-dod">
    <label for="chk-dod">
      <div class="cm2">Set as Deal of the Day</div>
      <div class="cs">Auto-assigns today or tomorrow if today is taken</div>
    </label>
  </div>
  <div id="dod-wrap" class="di" style="display:none">
    <input type="date" id="dod-date">
    <div class="dh">Leave blank to auto-assign. Set a date to target a specific day.</div>
  </div>
  <div class="cr">
    <input type="checkbox" id="chk-fb">
    <label for="chk-fb"><div class="cm2">Approve for Facebook</div></label>
  </div>
  <div class="cr">
    <input type="checkbox" id="chk-ig">
    <label for="chk-ig"><div class="cm2">Approve for Instagram</div></label>
  </div>
  <button class="bp" id="btn-submit">Submit listing</button>
  <div class="dv"></div>
  <div class="sl">Recent requests</div>
  <div id="reqcontent"><p style="font-size:13px;color:#9CA3AF">Loading...</p></div>
</div>
<div class="toast" id="toast"></div>
<script>
var queue = [], qIdx = 0, working = false, toastTimer;
var CATS = {HISTORIC:'Historic',ACREAGE:'Acreage',CHARACTER:'Character',WATERFRONT:'Waterfront',RENOVATED:'Renovated',HIDDEN_GEM:'Hidden gem',WHAT_IF:'What if',NEW_CONSTRUCTION:'New construction'};

function toast(msg, ms) {
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){ el.classList.remove('on'); }, ms || 2200);
}

document.getElementById('t-queue').addEventListener('click', function() { showTab('queue'); });
document.getElementById('t-add').addEventListener('click', function() { showTab('add'); loadRequests(); });
document.getElementById('btn-refresh').addEventListener('click', loadQueue);
document.getElementById('btn-submit').addEventListener('click', submitListing);
document.getElementById('chk-dod').addEventListener('change', function() {
  document.getElementById('dod-wrap').style.display = this.checked ? 'block' : 'none';
});

function showTab(name) {
  document.getElementById('t-queue').className = 'tab' + (name === 'queue' ? ' on' : '');
  document.getElementById('t-add').className = 'tab' + (name === 'add' ? ' on' : '');
  document.getElementById('s-queue').className = 'sec' + (name === 'queue' ? ' on' : '');
  document.getElementById('s-add').className = 'sec' + (name === 'add' ? ' on' : '');
}

function api(method, path, body, cb) {
  var opts = { method: method, credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  fetch('/api' + path, opts).then(function(r) {
    if (r.status === 401) { window.location.href = '/login'; return; }
    if (!r.ok) { r.text().then(function(t){ cb(new Error(t), null); }); return; }
    r.json().then(function(d){ cb(null, d); });
  }).catch(function(e){ cb(e, null); });
}

function loadQueue() {
  document.getElementById('qcount').textContent = '';
  document.getElementById('qcontent').innerHTML = '<div class="spin"><div class="ring"></div>Loading...</div>';
  api('GET', '/queue', null, function(err, data) {
    if (err) {
      document.getElementById('qcontent').innerHTML = '<div class="er">' + err.message.slice(0,120) + '</div>';
      return;
    }
    queue = data.rows || [];
    qIdx = 0;
    renderCard();
  });
}

function renderCard() {
  var rem = queue.length - qIdx;
  document.getElementById('qcount').textContent = rem > 0 ? rem + ' listing' + (rem !== 1 ? 's' : '') + ' remaining' : '';
  var el = document.getElementById('qcontent');
  el.innerHTML = '';

  if (rem <= 0) {
    var d = document.createElement('div'); d.className = 'emp';
    d.innerHTML = '<div class="ei">&#10003;</div><div class="et">Queue is clear</div><div class="es">All listings reviewed.</div>';
    var rb = document.createElement('button'); rb.textContent = 'Refresh'; rb.addEventListener('click', loadQueue);
    d.appendChild(rb); el.appendChild(d);
    return;
  }

  var l = queue[qIdx];
  var card = document.createElement('div'); card.className = 'card';

  // Image
  if (l.hero_image_url) {
    var img = document.createElement('img');
    img.className = 'ci'; img.src = l.hero_image_url;
    img.alt = (l.city || '') + ' ' + (l.state || '');
    img.addEventListener('error', function() {
      var nd = document.createElement('div'); nd.className = 'ni'; nd.textContent = 'No image';
      img.parentNode.replaceChild(nd, img);
    });
    card.appendChild(img);
  } else {
    var ni = document.createElement('div'); ni.className = 'ni'; ni.textContent = 'No image';
    card.appendChild(ni);
  }

  // Body
  var cb = document.createElement('div'); cb.className = 'cb';
  var price = l.price ? '$' + Number(l.price).toLocaleString() : '-';
  var loc = [l.city, l.state].filter(Boolean).join(', ');
  var cat = CATS[l.category] || (l.category || '').toLowerCase().replace(/_/g, ' ');

  var pEl = document.createElement('div'); pEl.className = 'cp'; pEl.textContent = price; cb.appendChild(pEl);
  var lEl = document.createElement('div'); lEl.className = 'cl'; lEl.textContent = loc; cb.appendChild(lEl);

  var meta = document.createElement('div'); meta.className = 'cm';
  var bs = document.createElement('span'); bs.className = 'bd bs'; bs.textContent = 'Score ' + (l.score || '?'); meta.appendChild(bs);
  var bc = document.createElement('span'); bc.className = 'bd bc'; bc.textContent = cat; meta.appendChild(bc);
  cb.appendChild(meta);

  if (l.headline) {
    var hl = document.createElement('div'); hl.className = 'ch'; hl.textContent = l.headline; cb.appendChild(hl);
  }
  var lnk = document.createElement('a'); lnk.className = 'ck';
  lnk.href = 'https://housesunder150k.com/listings/' + l.slug;
  lnk.target = '_blank'; lnk.rel = 'noreferrer'; lnk.textContent = 'View on site';
  cb.appendChild(lnk);
  card.appendChild(cb);

  // Actions
  var act = document.createElement('div'); act.className = 'act';
  var slug = l.slug;

  var bAll = document.createElement('button'); bAll.className = 'ba'; bAll.textContent = 'Approve - Facebook + Instagram';
  bAll.addEventListener('click', function(){ doApprove(slug, true, true); });

  var tc = document.createElement('div'); tc.className = 'tc';
  var bFb = document.createElement('button'); bFb.className = 'bf'; bFb.textContent = 'Facebook only';
  bFb.addEventListener('click', function(){ doApprove(slug, true, false); });
  var bIg = document.createElement('button'); bIg.className = 'bi'; bIg.textContent = 'Instagram only';
  bIg.addEventListener('click', function(){ doApprove(slug, false, true); });
  tc.appendChild(bFb); tc.appendChild(bIg);

  var bSk = document.createElement('button'); bSk.className = 'bk'; bSk.textContent = 'Not this one';
  bSk.addEventListener('click', function(){ doSkip(slug); });

  act.appendChild(bAll); act.appendChild(tc); act.appendChild(bSk);
  card.appendChild(act);
  el.appendChild(card);
}

function doApprove(slug, fb, ig) {
  if (working) return; working = true; setBtns(true);
  api('POST', '/approve/' + slug, { facebook: fb, instagram: ig }, function(err) {
    if (err) { toast('Error: ' + err.message.slice(0,60)); }
    else { toast(fb && ig ? 'Approved - FB + IG' : fb ? 'Approved - Facebook' : 'Approved - Instagram'); qIdx++; renderCard(); }
    working = false; setBtns(false);
  });
}

function doSkip(slug) {
  if (working) return; working = true; setBtns(true);
  api('POST', '/skip/' + slug, null, function(err) {
    if (err) { toast('Error: ' + err.message.slice(0,60)); }
    else { toast('Skipped permanently'); qIdx++; renderCard(); }
    working = false; setBtns(false);
  });
}

function setBtns(d) {
  var btns = document.querySelectorAll('.act button');
  for (var i = 0; i < btns.length; i++) btns[i].disabled = d;
}

function submitListing() {
  var addr = document.getElementById('addr').value.trim();
  if (!addr) { toast('Enter an address first'); return; }
  var btn = document.getElementById('btn-submit');
  btn.disabled = true; btn.textContent = 'Submitting...';
  var isDod = document.getElementById('chk-dod').checked;
  var dodDate = document.getElementById('dod-date').value || null;
  api('POST', '/requests', {
    address: addr,
    is_deal_of_day: isDod,
    deal_of_day_date: isDod && dodDate ? dodDate : null,
    post_facebook: document.getElementById('chk-fb').checked,
    post_instagram: document.getElementById('chk-ig').checked,
  }, function(err) {
    btn.disabled = false; btn.textContent = 'Submit listing';
    if (err) { toast('Error: ' + err.message.slice(0,60)); return; }
    toast('Submitted - pipeline picks it up within 30 min', 3000);
    document.getElementById('addr').value = '';
    document.getElementById('chk-dod').checked = false;
    document.getElementById('chk-fb').checked = false;
    document.getElementById('chk-ig').checked = false;
    document.getElementById('dod-wrap').style.display = 'none';
    loadRequests();
  });
}

function loadRequests() {
  document.getElementById('reqcontent').innerHTML = '<p style="font-size:13px;color:#9CA3AF">Loading...</p>';
  api('GET', '/requests', null, function(err, data) {
    var el = document.getElementById('reqcontent');
    if (err) { el.innerHTML = '<p class="er">Error loading requests.</p>'; return; }
    var rows = data.rows || [];
    if (!rows.length) { el.innerHTML = '<p style="font-size:13px;color:#9CA3AF">No requests yet.</p>'; return; }
    el.innerHTML = '';
    rows.forEach(function(r) {
      var div = document.createElement('div');
      div.className = 'rq ' + r.status;
      var flags = [r.post_facebook && 'FB', r.post_instagram && 'IG', r.is_deal_of_day && 'DoD'].filter(Boolean).join(' / ');
      var detail = r.status === 'done' && r.result_slug ? r.result_slug
        : r.status === 'failed' && r.error_message ? r.error_message.slice(0,60) : '';
      var a = document.createElement('div'); a.className = 'ra'; a.textContent = r.address; div.appendChild(a);
      var m = document.createElement('div'); m.className = 'rm';
      m.textContent = r.status.toUpperCase() + (flags ? ' / ' + flags : '') + (detail ? ' / ' + detail : '');
      div.appendChild(m);
      el.appendChild(div);
    });
  });
}

loadQueue();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def serve_app(request: Request):
    if not get_session(request):
        return RedirectResponse("/login", status_code=302)
    return APP


@app.get("/health")
def health():
    return {"ok": True}
