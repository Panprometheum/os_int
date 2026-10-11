"""breach.py - sumber breach / kebocoran data & email intelligence.

Source:
  - Hudson Rock (info-stealer, gratis)
  - HIBP (butuh key)
  - HIBP paste (butuh key)
  - PGP keyserver (email -> key, nama)
  - Gravatar (email -> profil)
  - EmailRep (butuh key, fallback)
  - Pastebin search (via Google/Jina)
  - deep email checks

Semua balikin {ok, source, data, error}.
"""
from __future__ import annotations

import hashlib
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

TIMEOUT = 15
UA = "Mozilla/5.0 (compatible; osint-breach/1.0)"


def _get(url: str, headers: dict | None = None, timeout: int = TIMEOUT):
    h = {"User-Agent": UA, "Accept": "application/json, text/html"}
    if headers:
        h.update(headers)
    try:
        if _req is not None:
            r = _req.get(url, headers=h, timeout=timeout, verify=False)
            return r.status_code, r.text
        req = urllib.request.Request(url, headers=h)
        import ssl
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------------------------
# Hudson Rock — info-stealer infection check (GRATIS)
# ---------------------------------------------------------------------------
def hudson_rock_email(email: str) -> dict:
    url = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email?email=" + urllib.parse.quote(email)
    s, b = _get(url)
    if s is None:
        return {"ok": False, "source": "hudson-rock", "error": b}
    try:
        j = json.loads(b)
        if j.get("message"):
            return {"ok": True, "source": "hudson-rock", "data": {
                "infected": True, "message": j.get("message"),
                "stealers": [{"computer": r.get("computer_name"), "os": r.get("operating_system"),
                              "ip": r.get("ip"), "date": r.get("date_compromised"),
                              "malware": r.get("malware_path"), "username": r.get("stealer_username")}
                             for r in (j.get("stealers") or [])[:20]],
            }}
        return {"ok": True, "source": "hudson-rock", "data": {"infected": False}}
    except Exception as e:
        return {"ok": False, "source": "hudson-rock", "error": str(e)}


def hudson_rock_username(username: str) -> dict:
    url = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-username?username=" + urllib.parse.quote(username)
    s, b = _get(url)
    if s is None:
        return {"ok": False, "source": "hudson-rock-user", "error": b}
    try:
        j = json.loads(b)
        return {"ok": True, "source": "hudson-rock-user", "data": {
            "infected": bool(j.get("message")),
            "raw": j,
        }}
    except Exception as e:
        return {"ok": False, "source": "hudson-rock-user", "error": str(e)}


def hudson_rock_domain(domain: str) -> dict:
    url = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-domain?domain=" + urllib.parse.quote(domain)
    s, b = _get(url)
    if s is None:
        return {"ok": False, "source": "hudson-rock-domain", "error": b}
    try:
        j = json.loads(b)
        return {"ok": True, "source": "hudson-rock-domain", "data": j}
    except Exception as e:
        return {"ok": False, "source": "hudson-rock-domain", "error": str(e)}


# ---------------------------------------------------------------------------
# HIBP
# ---------------------------------------------------------------------------
def hibp_breaches(account: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "hibp", "error": "butuh API key"}
    s, b = _get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{urllib.parse.quote(account)}?truncateResponse=false",
                headers={"hibp-api-key": api_key})
    if s == 404:
        return {"ok": True, "source": "hibp", "data": {"breaches": []}}
    if s is None or s != 200:
        return {"ok": False, "source": "hibp", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "hibp", "data": {"breaches": json.loads(b)}}
    except Exception as e:
        return {"ok": False, "source": "hibp", "error": str(e)}


def hibp_pastes(account: str, api_key: str) -> dict:
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
# PGP keyserver — email -> key + nama
# ---------------------------------------------------------------------------
def pgp_keyserver(email: str) -> dict:
    """keys.openpgp.org + keyserver.ubuntu.com."""
    out = {"email": email, "keys": []}
    # keys.openpgp.org (modern, GDPR-compliant)
    s, b = _get("https://keys.openpgp.org/vks/v1/by-email/" + urllib.parse.quote(email))
    if s == 200 and "BEGIN PGP PUBLIC KEY BLOCK" in b:
        out["keys"].append({"server": "keys.openpgp.org", "found": True, "fingerprint": _pgp_fpr(b)})
        out["name"] = _pgp_uid(b)
    # keyserver.ubuntu.com
    s, b = _get("https://keyserver.ubuntu.com/pks/lookup?op=get&search=" + urllib.parse.quote(email))
    if s == 200 and "BEGIN PGP PUBLIC KEY BLOCK" in b:
        out["keys"].append({"server": "keyserver.ubuntu.com", "found": True, "fingerprint": _pgp_fpr(b)})
    return {"ok": True, "source": "pgp", "data": out}


def _pgp_uid(pem: str) -> str | None:
    import re
    m = re.search(r"Comment: ([^\n]+)", pem)
    return m.group(1) if m else None


def _pgp_fpr(pem: str) -> str | None:
    import re
    m = re.search(r"-----BEGIN PGP PUBLIC KEY BLOCK-----", pem)
    return None  # fingerprint butuh parsing binary; skip


# ---------------------------------------------------------------------------
# Gravatar
# ---------------------------------------------------------------------------
def gravatar(email: str) -> dict:
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    s, b = _get(f"https://gravatar.com/{h}.json")
    if s != 200:
        return {"ok": True, "source": "gravatar", "data": {"found": False}}
    try:
        j = json.loads(b)
        e = (j.get("entry") or [{}])[0]
        return {"ok": True, "source": "gravatar", "data": {
            "found": True, "display_name": e.get("displayName"), "name": e.get("name"),
            "about": e.get("aboutMe"), "avatar": e.get("thumbnailUrl"),
            "profile_url": e.get("profileUrl"),
            "accounts": [{"shortname": a.get("shortname"), "username": a.get("username"),
                          "url": a.get("url")} for a in e.get("accounts", [])],
        }}
    except Exception as e:
        return {"ok": False, "source": "gravatar", "error": str(e)}


# ---------------------------------------------------------------------------
# EmailRep (butuh key)
# ---------------------------------------------------------------------------
def emailrep(email: str, api_key: str = "") -> dict:
    if not api_key:
        return {"ok": False, "source": "emailrep", "error": "butuh API key (emailrep.io)"}
    s, b = _get("https://emailrep.io/" + urllib.parse.quote(email),
                headers={"Key": api_key})
    if s is None or s != 200:
        return {"ok": False, "source": "emailrep", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "emailrep", "data": json.loads(b)}
    except Exception as e:
        return {"ok": False, "source": "emailrep", "error": str(e)}


# ---------------------------------------------------------------------------
# Gravatar + PGP + Hudson Rock gabungan untuk 1 email
# ---------------------------------------------------------------------------
def email_intel(email: str, hibp_key: str = "", emailrep_key: str = "") -> dict:
    jobs = {
        "gravatar": lambda: gravatar(email),
        "pgp": lambda: pgp_keyserver(email),
        "hudson_rock": lambda: hudson_rock_email(email),
        "hibp": lambda: hibp_breaches(email, hibp_key),
        "hibp_paste": lambda: hibp_pastes(email, hibp_key),
    }
    if emailrep_key:
        jobs["emailrep"] = lambda: emailrep(email, emailrep_key)
    out = {}
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {k: ex.submit(fn) for k, fn in jobs.items()}
            for k, fut in futs.items():
                try:
                    out[k] = fut.result(timeout=20)
                except Exception as e:
                    out[k] = {"ok": False, "source": k, "error": str(e)}
    except ImportError:
        for k, fn in jobs.items():
            out[k] = fn()
    return out
