"""leakcheck.py - breach / credential leak sources.

Gratis (public) :
  - LeakCheck public (found count, fields, sources)
  - HIBP breaches list (daftar semua breach publik)
  - HIBP account (butuh key)
  - HIBP paste  (butuh key)

Butuh key (opsional):
  - LeakCheck API (v2, full hasil)
  - Snusbase
  - DeHashed
  - BreachDirectory (RapidAPI)

Semua balikin {ok, source, data, error}.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

try:
    import requests as _req
    try:
        _req.packages.urllib3.disable_warnings()
    except Exception:
        pass
except ImportError:
    _req = None

TIMEOUT = 18
UA = "Mozilla/5.0 (compatible; osint-leakcheck/1.0)"


def _get(url: str, headers: dict | None = None, params: dict | None = None, timeout: int = TIMEOUT):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    try:
        if _req is not None:
            r = _req.get(url, headers=h, params=params, timeout=timeout, verify=False)
            return r.status_code, r.text
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=h)
        import ssl
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------------------------
# LeakCheck
# ---------------------------------------------------------------------------
def leakcheck_public(term: str) -> dict:
    """Gratis, tanpa key. Balikin count + fields + source names."""
    s, b = _get("https://leakcheck.io/api/public", params={"check": term})
    if s is None:
        return {"ok": False, "source": "leakcheck-public", "error": b}
    if s == 429:
        return {"ok": False, "source": "leakcheck-public", "error": "rate limited (coba lagi)"}
    try:
        j = json.loads(b)
        if not j.get("success"):
            return {"ok": True, "source": "leakcheck-public", "data": {
                "term": term, "found": 0, "message": j.get("error") or "tidak ditemukan"}}
        return {"ok": True, "source": "leakcheck-public", "data": {
            "term": term, "found": j.get("found"),
            "fields": j.get("fields", []),
            "sources": [x.get("name") for x in (j.get("sources") or [])],
        }}
    except Exception as e:
        return {"ok": False, "source": "leakcheck-public", "error": str(e)}


def leakcheck_api(term: str, api_key: str) -> dict:
    """Full hasil via API v2 (butuh key)."""
    if not api_key:
        return {"ok": False, "source": "leakcheck-api", "error": "butuh API key"}
    s, b = _get(f"https://leakcheck.io/api/v2/query/{urllib.parse.quote(term)}",
                headers={"X-API-Key": api_key, "accept": "application/json"})
    if s is None or s != 200:
        return {"ok": False, "source": "leakcheck-api", "error": f"http {s}: {b[:120] if b else ''}"}
    try:
        return {"ok": True, "source": "leakcheck-api", "data": json.loads(b)}
    except Exception as e:
        return {"ok": False, "source": "leakcheck-api", "error": str(e)}


# ---------------------------------------------------------------------------
# HIBP
# ---------------------------------------------------------------------------
def hibp_all_breaches() -> dict:
    """Daftar semua breach publik (tanpa key) — buat referensi."""
    s, b = _get("https://haveibeenpwned.com/api/v3/breaches", headers={"User-Agent": "osint"})
    if s is None or s != 200:
        return {"ok": False, "source": "hibp-list", "error": f"http {s}"}
    try:
        j = json.loads(b)
        return {"ok": True, "source": "hibp-list", "data": {
            "count": len(j),
            "breaches": [{"name": x.get("Name"), "domain": x.get("Domain"),
                          "date": x.get("BreachDate"), "pwned": x.get("PwnCount"),
                          "data": x.get("DataClasses")} for x in j],
        }}
    except Exception as e:
        return {"ok": False, "source": "hibp-list", "error": str(e)}


def hibp_account(account: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "hibp", "error": "butuh API key"}
    s, b = _get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{urllib.parse.quote(account)}?truncateResponse=false",
                headers={"hibp-api-key": api_key})
    if s == 404:
        return {"ok": True, "source": "hibp", "data": {"account": account, "breaches": []}}
    if s is None or s != 200:
        return {"ok": False, "source": "hibp", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "hibp", "data": {"account": account, "breaches": json.loads(b)}}
    except Exception as e:
        return {"ok": False, "source": "hibp", "error": str(e)}


def hibp_paste(account: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "hibp-paste", "error": "butuh API key"}
    s, b = _get(f"https://haveibeenpwned.com/api/v3/pasteaccount/{urllib.parse.quote(account)}",
                headers={"hibp-api-key": api_key})
    if s == 404:
        return {"ok": True, "source": "hibp-paste", "data": {"pastes": []}}
    if s is None or s != 200:
        return {"ok": False, "source": "hibp-paste", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "hibp-paste", "data": {"pastes": json.loads(b)}}
    except Exception as e:
        return {"ok": False, "source": "hibp-paste", "error": str(e)}


# ---------------------------------------------------------------------------
# Snusbase / DeHashed / BreachDirectory (butuh key)
# ---------------------------------------------------------------------------
def snusbase(term: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "snusbase", "error": "butuh API key"}
    try:
        r = _req.post("https://api.snusbase.com/data/search",
                      headers={"Auth": api_key, "Content-Type": "application/json"},
                      json={"terms": [term], "types": ["email", "username", "password", "lastip", "_domain"]},
                      timeout=TIMEOUT, verify=False)
        if r.status_code != 200:
            return {"ok": False, "source": "snusbase", "error": f"http {r.status_code}"}
        return {"ok": True, "source": "snusbase", "data": r.json()}
    except Exception as e:
        return {"ok": False, "source": "snusbase", "error": str(e)}


def dehashed(query: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "dehashed", "error": "butuh API key (email:api_key)"}
    import base64
    user, _, key = api_key.partition(":")
    token = base64.b64encode(f"{user}:{key}".encode()).decode()
    s, b = _get(f"https://api.dehashed.com/search?query={urllib.parse.quote(query)}",
                headers={"Authorization": f"Basic {token}", "Accept": "application/json"})
    if s is None or s != 200:
        return {"ok": False, "source": "dehashed", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "dehashed", "data": json.loads(b)}
    except Exception as e:
        return {"ok": False, "source": "dehashed", "error": str(e)}


def breachdirectory(term: str, rapidapi_key: str) -> dict:
    if not rapidapi_key:
        return {"ok": False, "source": "breachdirectory", "error": "butuh RapidAPI key"}
    s, b = _get("https://breachdirectory.p.rapidapi.com/",
                headers={"X-RapidAPI-Key": rapidapi_key, "X-RapidAPI-Host": "breachdirectory.p.rapidapi.com"},
                params={"func": "auto", "term": term})
    if s is None or s != 200:
        return {"ok": False, "source": "breachdirectory", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "breachdirectory", "data": json.loads(b)}
    except Exception as e:
        return {"ok": False, "source": "breachdirectory", "error": str(e)}


# ---------------------------------------------------------------------------
def lookup_all(term: str, leakcheck_key: str = "", hibp_key: str = "",
               snusbase_key: str = "", dehashed_key: str = "", rapidapi_key: str = "") -> dict:
    jobs = {
        "leakcheck_public": lambda: leakcheck_public(term),
        "hibp_account": lambda: hibp_account(term, hibp_key),
    }
    if leakcheck_key:
        jobs["leakcheck_api"] = lambda: leakcheck_api(term, leakcheck_key)
    if snusbase_key:
        jobs["snusbase"] = lambda: snusbase(term, snusbase_key)
    if dehashed_key:
        jobs["dehashed"] = lambda: dehashed(term, dehashed_key)
    if rapidapi_key:
        jobs["breachdirectory"] = lambda: breachdirectory(term, rapidapi_key)
    out = {}
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {k: ex.submit(fn) for k, fn in jobs.items()}
            for k, fut in futs.items():
                try:
                    out[k] = fut.result(timeout=25)
                except Exception as e:
                    out[k] = {"ok": False, "source": k, "error": str(e)}
    except ImportError:
        for k, fn in jobs.items():
            out[k] = fn()
    return out
