"""enrich.py - enrichment module: phonenumbers, breach, email, social, github, gravatar.

All functions return a consistent dict {ok, data, source, error}.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

TIMEOUT = 12
UA = "Mozilla/5.0 (compatible; osint-enrich/1.0)"


def _http(url: str, headers: dict | None = None, data: bytes | None = None) -> str | None:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def _http_json(url: str, headers: dict | None = None, data: bytes | None = None) -> dict | None:
    raw = _http(url, headers, data)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


# --------------------------------------------------------------------------
# 1. Phone number enrichment via phonenumbers lib
# --------------------------------------------------------------------------
def enrich_phone(raw: str) -> dict:
    try:
        import phonenumbers
        from phonenumbers import carrier, geocoder, timezone, number_type, PhoneNumberType
    except ImportError:
        return {"ok": False, "source": "phonenumbers", "error": "lib not installed"}

    # deteksi region default Indonesia
    try:
        pn = phonenumbers.parse(raw, "ID")
    except Exception as e:
        return {"ok": False, "source": "phonenumbers", "error": str(e)}

    if not phonenumbers.is_valid_number(pn):
        return {"ok": False, "source": "phonenumbers", "error": "invalid number"}

    types = {
        PhoneNumberType.MOBILE: "mobile",
        PhoneNumberType.FIXED_LINE: "fixed",
        PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed/mobile",
        PhoneNumberType.TOLL_FREE: "toll-free",
        PhoneNumberType.PREMIUM_RATE: "premium",
        PhoneNumberType.VOIP: "voip",
        PhoneNumberType.SHARED_COST: "shared-cost",
        PhoneNumberType.PERSONAL_NUMBER: "personal",
        PhoneNumberType.PAGER: "pager",
        PhoneNumberType.UAN: "uan",
        PhoneNumberType.VOICEMAIL: "voicemail",
    }
    nt = number_type(pn)

    data = {
        "e164": phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164),
        "international": phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "national": phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.NATIONAL),
        "rfc3966": phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.RFC3966),
        "country_code": pn.country_code,
        "national_number": pn.national_number,
        "region": phonenumbers.region_code_for_number(pn),
        "carrier": carrier.name_for_number(pn, "en") or None,
        "carrier_id": getattr(carrier, "name_for_number", lambda *a: None)(pn, "id"),
        "geo_description": geocoder.description_for_number(pn, "en") or None,
        "timezones": list(timezone.time_zones_for_number(pn)),
        "number_type": types.get(nt, str(nt)),
        "is_valid": phonenumbers.is_valid_number(pn),
        "is_possible": phonenumbers.is_possible_number(pn),
        "is_geographical": geocoder.description_for_number(pn, "en") != "",
    }
    return {"ok": True, "source": "phonenumbers", "data": data}


# --------------------------------------------------------------------------
# 2. Breach check (HIBP)
# --------------------------------------------------------------------------
def breach_hibp(account: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "hibp", "error": "needs API key"}
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{urllib.parse.quote(account)}?truncateResponse=false"
    raw = _http(url, headers={"hibp-api-key": api_key})
    if raw is None:
        return {"ok": True, "source": "hibp", "data": {"breaches": [], "note": "clean or not detected"}}
    try:
        j = json.loads(raw)
        return {"ok": True, "source": "hibp", "data": {"breaches": j}}
    except Exception:
        return {"ok": False, "source": "hibp", "error": "parse failed"}


def breach_pastes(account: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "hibp-paste", "error": "needs API key"}
    url = f"https://haveibeenpwned.com/api/v3/pasteaccount/{urllib.parse.quote(account)}"
    raw = _http(url, headers={"hibp-api-key": api_key})
    if raw is None:
        return {"ok": True, "source": "hibp-paste", "data": {"pastes": []}}
    try:
        return {"ok": True, "source": "hibp-paste", "data": {"pastes": json.loads(raw)}}
    except Exception:
        return {"ok": False, "source": "hibp-paste", "error": "parse failed"}


# --------------------------------------------------------------------------
# 3. Email -> account (epieos-style, gravatar) + domain info
# --------------------------------------------------------------------------
def email_lookup(email: str) -> dict:
    out = {"ok": True, "source": "email", "data": {}}

    # Gravatar
    import hashlib
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    gj = _http_json(f"https://gravatar.com/{h}.json")
    if gj and gj.get("entry"):
        entry = gj["entry"][0]
        out["data"]["gravatar"] = {
            "profile_url": entry.get("profileUrl"),
            "display_name": entry.get("displayName"),
            "name": entry.get("name"),
            "about": entry.get("aboutMe"),
            "avatar": entry.get("thumbnailUrl"),
            "accounts": [{"shortname": a.get("shortname"), "url": a.get("url"),
                          "username": a.get("username")} for a in entry.get("accounts", [])],
        }
    else:
        out["data"]["gravatar"] = None

    # Domain of email
    if "@" in email:
        domain = email.split("@", 1)[1].lower()
        out["data"]["domain"] = domain
        out["data"]["is_disposable"] = domain in DISPOSABLE_DOMAINS
        out["data"]["is_free"] = domain in FREE_DOMAINS
    return out


DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "throwawaymail.com", "yopmail.com", "trashmail.com", "sharklasers.com",
    "getnada.com", "dispostable.com", "maildrop.cc", "temp-mail.org",
}
FREE_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.co.id", "hotmail.com", "outlook.com",
    "aol.com", "protonmail.com", "proton.me", "icloud.com", "live.com",
    "mail.com", "gmx.com", "zoho.com", "yandex.com", "rocketmail.com",
}


# --------------------------------------------------------------------------
# 4. GitHub user lookup
# --------------------------------------------------------------------------
def github_lookup(username: str) -> dict:
    j = _http_json(f"https://api.github.com/users/{urllib.parse.quote(username)}")
    if not j or j.get("message") == "Not Found":
        return {"ok": False, "source": "github", "error": "not found"}
    # fetch public repos
    repos = _http_json(f"https://api.github.com/users/{urllib.parse.quote(username)}/repos?per_page=100&sort=updated") or []
    rels = []
    for r in repos[:30]:
        rels.append({
            "name": r.get("name"), "url": r.get("html_url"),
            "lang": r.get("language"), "updated": r.get("updated_at"),
            "stars": r.get("stargazers_count"), "desc": r.get("description"),
        })
    emails = set()
    for r in repos[:20]:
        e = _http_json(f"https://api.github.com/repos/{urllib.parse.quote(username)}/{urllib.parse.quote(r['name'])}/commits?per_page=20") or []
        for c in e:
            if c.get("commit", {}).get("author", {}).get("email"):
                emails.add(c["commit"]["author"]["email"])
    return {"ok": True, "source": "github", "data": {
        "login": j.get("login"), "name": j.get("name"), "bio": j.get("bio"),
        "company": j.get("company"), "location": j.get("location"),
        "email": j.get("email"), "blog": j.get("blog"),
        "twitter": j.get("twitter_username"), "public_repos": j.get("public_repos"),
        "followers": j.get("followers"), "following": j.get("following"),
        "created": j.get("created_at"), "avatar": j.get("avatar_url"),
        "repos": rels, "commit_emails": sorted(emails),
    }}


# --------------------------------------------------------------------------
# 5. Username presence check (multi-platform)
# --------------------------------------------------------------------------
def username_check(username: str) -> dict:
    platforms = {
        "github": (f"https://github.com/{username}", ["<span class=\"p-nickname\""], ["Not Found"]),
        "gitlab": (f"https://gitlab.com/{username}", ["data-testid=\"user-avatar-content\""], ["404", "Page Not Found"]),
        "reddit": (f"https://www.reddit.com/user/{username}", ["<shreddit-profile-page", "\"profileId\""], ["Sorry, nobody on Reddit"]),
        "telegram": (f"https://t.me/{username}", ["tgme_page_title", "tgme_page_photo"], ["tgme_page_icon"]),
        "twitch": (f"https://www.twitch.tv/{username}", ["<title>Twitch</title>"], ["Sorry. Unless"]),
        "steam": (f"https://steamcommunity.com/id/{username}", ["actual_persona_name"], ["The specified profile could not be found"]),
        "pinterest": (f"https://www.pinterest.com/{username}/", ["pinterestapp:followers"], ["Not Found"]),
        "soundcloud": (f"https://soundcloud.com/{username}", ["<link rel=\"canonical\" href=\"https://soundcloud.com/"], ["We can't find that page"]),
        "behance": (f"https://www.behance.net/{username}", ["og:type\" content=\"profile"], ["Oops! We can't find this page"]),
        "dribbble": (f"https://dribbble.com/{username}", ["og:url\" content=\"https://dribbble.com/"], ["Whoops, that's a 404"]),
        "medium": (f"https://medium.com/@{username}", ["story"], ["PAGE NOT FOUND", "404"]),
        "roblox": (f"https://www.roblox.com/user.aspx?username={username}", ["profile-container"], ["Page cannot be found"]),
        "youtube": (f"https://www.youtube.com/@{username}", ["og:url\" content=\"https://www.youtube.com/@"], ["404"]),
        "snapchat": (f"https://www.snapchat.com/add/{username}", ["og:title\""], ["404"]),
        "patreon": (f"https://www.patreon.com/{username}", ["og:title\""], ["page not found"]),
        "keybase": (f"https://keybase.io/{username}", ["<div class=\"profile\"", "profile-heading"], ["Not found"]),
        "hackernews": (f"https://news.ycombinator.com/user?id={username}", ["user:"], ["No such user"]),
        "gitea": (f"https://gitea.com/{username}", ["repository"], ["404"]),
        "aboutme": (f"https://about.me/{username}", ["og:title\""], ["404"]),
    }
    found = {}
    for name, (url, pos_markers, neg_markers) in platforms.items():
        found[name] = {"url": url, **_probe(url, pos_markers, neg_markers)}
    return {"ok": True, "source": "username-check", "data": found}


def _probe(url: str, pos_markers: list[str], neg_markers: list[str]) -> dict:
    """GET a page, check for positive/negative markers."""
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    req = urllib.request.Request(url, headers=h, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=9) as r:
            if r.status != 200:
                return {"status": "http " + str(r.status)}
            body = r.read(200000).decode("utf-8", "replace")
        low = body.lower()
        for m in neg_markers:
            if m.lower() in low:
                return {"status": "not found"}
        hits = sum(1 for m in pos_markers if m.lower() in low)
        if hits > 0:
            return {"status": "found", "markers": hits}
        # no negative markers -> likely exists (redirect to a generic profile)
        return {"status": "maybe"}
    except urllib.error.HTTPError as e:
        return {"status": "not found" if e.code == 404 else f"http {e.code}"}
    except Exception as e:
        return {"status": "error"}


# --------------------------------------------------------------------------
# 6. Reverse image (link builder, no API)
# --------------------------------------------------------------------------
def reverse_image_links(image_url: str) -> dict:
    q = urllib.parse.quote(image_url, safe="")
    return {"ok": True, "source": "reverse-image", "data": {
        "image_url": image_url,
        "google_lens": f"https://lens.google.com/uploadbyurl?url={q}",
        "yandex": f"https://yandex.com/images/search?rpt=imageview&url={q}",
        "tineye": f"https://tineye.com/search?url={q}",
        "bing": f"https://www.bing.com/images/search?q=imgurl:{q}&view=detailv2&iss=sbi",
        "saucenao": f"https://saucenao.com/search.php?url={q}",
        "trace": f"https://trace.moe/?url={q}",
    }}
