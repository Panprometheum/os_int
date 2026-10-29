"""socint.py - resolve number -> social accounts (in-place, no manual link opening).

Active resolvers:
  1. telegram_num()      - scrape t.me preview for a number
  2. telegram_user()     - public Telegram profile via username
  3. truecaller()        - owner-name lookup (via login cookie)
  4. handle_pivot()      - check number as username on many platforms
  5. serpapi_search()    - search engine via SerpAPI (needs key, most reliable)
  6. searxng_search()    - search via SearXNG instance (JSON, configurable)
  7. search_links()      - manual search-link generator (no-key fallback)
  8. extract_phones()    - pull numbers from text (reverse pivot)
  9. generate_candidates() - derive all plausible username variants from a number

All return {ok, source, data, error}.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

try:
    import requests as _requests
    try:
        _requests.packages.urllib3.disable_warnings()
    except Exception:
        pass
except ImportError:
    _requests = None

TIMEOUT = 15
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _get(url: str, headers: dict | None = None, timeout: int = TIMEOUT, params: dict | None = None):
    h = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    if headers:
        h.update(headers)
    if _requests is not None:
        try:
            r = _requests.get(url, headers=h, timeout=timeout, params=params, verify=False)
            return r.status_code, r.text
        except Exception as e:
            return None, str(e)
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=h)
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(500000).decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def _meta(html: str, prop: str) -> str | None:
    for pat in (rf'<meta[^>]+property="{re.escape(prop)}"[^>]+content="([^"]*)"',
                rf'<meta[^>]+content="([^"]*)"[^>]+property="{re.escape(prop)}"'):
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------------------
# 1. Telegram (number + username)
# ---------------------------------------------------------------------------
def telegram_num(number_intl: str) -> dict:
    url = f"https://t.me/+{urllib.parse.quote(number_intl)}"
    s, b = _get(url)
    if s is None:
        return {"ok": False, "source": "telegram", "error": b}
    title = _meta(b, "og:title")
    desc = _meta(b, "og:description")
    image = _meta(b, "og:image")
    generic = title in ("Join group chat on Telegram", "Telegram: Contact", "Telegram", None) and not desc
    data = {"input": "+" + number_intl, "url": url, "title": title,
            "description": desc, "image": image, "generic": generic}
    m = re.search(r'tgme_page_title[^>]*>\s*<span[^>]*>([^<]+)', b)
    if m:
        data["display_name"] = m.group(1).strip()
    m = re.search(r'"username":"([^"]+)"', b)
    if m:
        data["username"] = m.group(1)
    return {"ok": True, "source": "telegram", "data": data}


def telegram_user(username: str) -> dict:
    url = f"https://t.me/{urllib.parse.quote(username)}"
    s, b = _get(url)
    if s is None:
        return {"ok": False, "source": "telegram-user", "error": b}
    title = _meta(b, "og:title")
    if not title or title in ("Telegram: Contact", "Telegram", "Join group chat on Telegram"):
        return {"ok": False, "source": "telegram-user", "error": "profile missing / private"}
    return {"ok": True, "source": "telegram-user", "data": {
        "username": username, "url": url,
        "display_name": title, "bio": _meta(b, "og:description"),
        "avatar": _meta(b, "og:image"),
    }}


def telegram_resolve(number_intl: str) -> dict:
    """Combined: check number + try as username."""
    out = {"by_number": telegram_num(number_intl)}
    # some people set username = number without prefix
    for cand in (number_intl, number_intl[2:], number_intl.lstrip("62")):
        u = telegram_user(cand)
        if u.get("ok"):
            out["by_username"] = u["data"]
            break
    return {"ok": True, "source": "telegram-resolve", "data": out}


# ---------------------------------------------------------------------------
# 2. Truecaller via cookie
# ---------------------------------------------------------------------------
def truecaller(number: str, cookie: str = "") -> dict:
    if not cookie:
        return {"ok": False, "source": "truecaller",
                "error": "needs login cookie (see README for how to get one)"}
    url = f"https://www.truecaller.com/search/id/{urllib.parse.quote(number)}"
    s, b = _get(url, headers={"Cookie": cookie})
    if s is None:
        return {"ok": False, "source": "truecaller", "error": b}
    out = {"url": url}
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', b, re.S)
    if m:
        try:
            j = json.loads(m.group(1))
            data = j.get("props", {}).get("pageProps", {})
            out["raw"] = data.get("data", data)
        except Exception:
            out["raw"] = None
    out["title"] = _meta(b, "og:title")
    out["description"] = _meta(b, "og:description")
    # extract the name if present
    if out.get("raw") and isinstance(out["raw"], dict):
        rec = out["raw"].get("record", {}) if isinstance(out["raw"], dict) else {}
        if rec:
            out["name"] = rec.get("name")
            out["phones"] = rec.get("phones")
            out["addresses"] = rec.get("addresses")
            out["internetAddresses"] = rec.get("internetAddresses")
            out["tags"] = rec.get("tags")
            out["spam"] = rec.get("spamInfo")
    return {"ok": True, "source": "truecaller", "data": out}


# ---------------------------------------------------------------------------
# 3. Handle pivot: number as username
# ---------------------------------------------------------------------------
def handle_pivot(number_local: str, variants: list[str] | None = None) -> dict:
    """Check number as handle on many platforms.
    Accuracy: only platforms verifiable without login. Login-gated ones -> inconclusive.
    Accepts an explicit list of digit-variants to try (generated by generate_candidates).
    """
    if not variants:
        variants = list({number_local, number_local.lstrip("0"), "62" + number_local.lstrip("0")})
    # platform: (template, positive_markers, negative_markers)
    # empty marker [] = check via status code only (for platforms blocking detail)
    platforms = {
        "telegram": ("https://t.me/{v}",
                     ["tgme_page_title", "tgme_page_photo"],
                     ["tgme_page_icon", "tgme_page_additional"]),
        "reddit": ("https://www.reddit.com/user/{v}",
                   ["shreddit-profile", "profileId"],
                   ["Sorry, nobody on Reddit", "page not found"]),
        "pinterest": ("https://www.pinterest.com/{v}/",
                      ["pinterestapp:followers"],
                      ["Not Found", "Page not found"]),
        "soundcloud": ("https://soundcloud.com/{v}",
                       ["soundcloud://users"],
                       ["We can't find that page"]),
        "keybase": ("https://keybase.io/{v}",
                    ["user_info", "profile-heading"],
                    ["Not found"]),
        "steam": ("https://steamcommunity.com/id/{v}",
                  ["actual_persona_name"],
                  ["The specified profile could not be found"]),
        "github": ("https://github.com/{v}",
                   ["<span class=\"p-nickname\"", "og:image\" content=\"https://avatars.githubusercontent.com"],
                   ["Not Found", "Page not found"]),
        "tiktok": ("https://www.tiktok.com/@{v}",
                   ["og:title\" content=\"", "\"uniqueId\""],
                   ["Couldn't find this account", "Couldn’t find"]),
        "facebook": ("https://www.facebook.com/{v}",
                     ["og:title\" content=\"", "profile_id"],
                     ["content is currently unavailable", "Page Not Found", "isn't available"]),
        "instagram": ("https://www.instagram.com/{v}/",
                      ["og:title\" content=\"", "profile_pic_url"],
                      ["Page Not Found", "Sorry, this page"]),
        "twitter": ("https://twitter.com/{v}",
                    ["og:title\" content=\"", "profile_image_url"],
                    ["This account doesn", "page doesn't exist", "account suspended"]),
        "threads": ("https://www.threads.net/@{v}",
                    ["og:title\" content=\"", "profile_pic_url"],
                    ["Page Not Found", "Sorry, this page"]),
        "snapchat": ("https://www.snapchat.com/add/{v}",
                     ["og:title\" content=\"", "profileImageUrl"],
                     ["Page Not Found", "not found", "404"]),
        "linkedin": ("https://www.linkedin.com/in/{v}",
                     ["og:title\" content=\"", "profilePicture"],
                     ["Page not found", "This page doesn't exist"]),
        "youtube": ("https://www.youtube.com/@{v}",
                    ["og:url\" content=\"https://www.youtube.com/@", "channelId"],
                    ["404", "This page isn't available"]),
        "medium": ("https://medium.com/@{v}",
                   ["og:title\" content=\""],
                   ["PAGE NOT FOUND", "404"]),
        "twitch": ("https://www.twitch.tv/{v}",
                   ["channel-link", "\"login\":\""],
                   ["Sorry. Unless", "404"]),
    }
    # build all tasks, run in parallel
    tasks = []
    for v in variants:
        for name, (tmpl, pos, neg) in platforms.items():
            tasks.append((name, v, tmpl.format(v=v), pos, neg))

    hits, inconclusive = {}, []
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=14) as ex:
            futures = {ex.submit(_probe_markers, url, pos, neg): (name, v, url)
                       for (name, v, url, pos, neg) in tasks}
            for fut in futures:
                name, v, url = futures[fut]
                try:
                    res = fut.result(timeout=18)
                except Exception:
                    res = "error"
                if res == "found":
                    hits.setdefault(name, []).append({"handle": v, "url": url})
                elif res == "inconclusive":
                    inconclusive.append({"platform": name, "handle": v, "url": url})
    except ImportError:
        for (name, v, url, pos, neg) in tasks:
            res = _probe_markers(url, pos, neg)
            if res == "found":
                hits.setdefault(name, []).append({"handle": v, "url": url})
            elif res == "inconclusive":
                inconclusive.append({"platform": name, "handle": v, "url": url})

    return {"ok": True, "source": "handle-pivot",
            "data": {"hits": hits, "checked": len(tasks), "inconclusive": inconclusive[:6]}}


def _probe_markers(url: str, pos: list[str], neg: list[str]) -> str:
    s, b = _get(url, timeout=10)
    if s is None:
        return "error"
    if s != 200:
        return "not found" if s == 404 else "error"
    low = b.lower()
    for m in neg:
        if m.lower() in low:
            return "not found"
    hits = sum(1 for m in pos if m.lower() in low)
    if hits > 0:
        return "found"
    return "inconclusive"


# ---------------------------------------------------------------------------
# 3b. Candidate generation: derive username variants from a phone number
# ---------------------------------------------------------------------------
def generate_candidates(number_local: str, number_intl: str = "") -> list[str]:
    """Generate all plausible username variants from a phone number.

    Examples for 082313148259:
      082313148259, 82313148259, 6282313148259,
      0823-1314-8259, 0823_1314_8259, 082313148259,
      082313, 08231314, 082313148, 13148259, ...
    """
    if not number_intl:
        digits = re.sub(r"\D", "", number_local)
        if digits.startswith("0"):
            number_intl = "62" + digits[1:]
        else:
            number_intl = digits
    digits = re.sub(r"\D", "", number_intl)
    variants: set[str] = set()
    # --- raw digits (all lengths >= 6) ---
    for i in range(6, len(digits) + 1):
        variants.add(digits[:i])
        variants.add(digits[len(digits) - i:])
    # --- local & intl raw ---
    variants.add(number_local.lstrip("0"))
    variants.add(number_intl)
    variants.add(number_intl.lstrip("62"))
    # --- with separators ---
    for sep in ["-", "_", "."]:
        if len(digits) >= 10:
            a, b, c = digits[:4], digits[4:8], digits[8:]
            variants.add(f"{a}{sep}{b}{sep}{c}")
            variants.add(f"{digits[:5]}{sep}{digits[5:]}")
            variants.add(f"{digits[:3]}{sep}{digits[3:]}")
        if len(digits) >= 8:
            variants.add(f"{digits[:4]}{sep}{digits[4:]}")
    # --- with '08' prefix stripped ---
    bare = number_local.lstrip("0")
    variants.add(bare)
    variants.add("62" + bare)
    # --- reversed last 6 digits (some people use reverse) ---
    if len(digits) >= 6:
        rev = digits[-6:][::-1]
        variants.add(rev)
        variants.add("08" + rev)
    # --- prefix-only (region code) ---
    if len(digits) >= 4:
        variants.add(digits[:4])
    return sorted({v for v in variants if 4 <= len(v) <= 16 and v.isdigit()})


# ---------------------------------------------------------------------------
# 4. Search via SerpAPI (needs key, reliable)
# ---------------------------------------------------------------------------
def serpapi_search(query: str, api_key: str, engine: str = "google", num: int = 20) -> dict:
    if not api_key:
        return {"ok": False, "source": "serpapi", "error": "needs API key"}
    url = "https://serpapi.com/search.json"
    params = {"q": query, "api_key": api_key, "engine": engine, "num": num, "hl": "id", "gl": "id"}
    s, b = _get(url, params=params)
    if s is None:
        return {"ok": False, "source": "serpapi", "error": b}
    try:
        j = json.loads(b)
        results = []
        for r in j.get("organic_results", [])[:num]:
            results.append({"title": r.get("title"), "url": r.get("link"),
                            "snippet": r.get("snippet")})
        # knowledge graph
        kg = j.get("knowledge_graph")
        return {"ok": True, "source": "serpapi", "data": {
            "query": query, "count": len(results), "results": results,
            "knowledge_graph": kg, "answer_box": j.get("answer_box"),
        }}
    except Exception as e:
        return {"ok": False, "source": "serpapi", "error": f"parse: {e}"}


# ---------------------------------------------------------------------------
# 5. SearXNG (JSON) - needs an instance with format=json enabled
# ---------------------------------------------------------------------------
def searxng_search(query: str, instance: str, num: int = 20) -> dict:
    inst = instance.rstrip("/")
    url = inst + "/search"
    s, b = _get(url, params={"q": query, "format": "json"}, timeout=18)
    if s is None:
        return {"ok": False, "source": "searxng", "error": b}
    try:
        j = json.loads(b)
        results = [{"title": r.get("title"), "url": r.get("url"),
                    "snippet": r.get("content")} for r in j.get("results", [])[:num]]
        return {"ok": True, "source": "searxng", "data": {"instance": inst, "count": len(results), "results": results}}
    except Exception:
        # return raw HTML search (captcha / no-json) as fallback
        return {"ok": False, "source": "searxng",
                "error": "instance has no JSON enabled / hit antibot", "instance": inst}


# ---------------------------------------------------------------------------
# 6. Search links generator (no-key fallback, extended with Indo platforms)
# ---------------------------------------------------------------------------
def search_links(number_local: str, number_intl: str) -> dict:
    q = f'"{number_local}" OR "+{number_intl}"'
    qi = urllib.parse.quote(q)
    qn = urllib.parse.quote(number_local)
    return {"ok": True, "source": "search-links", "data": {
        "query": q,
        "google": f"https://www.google.com/search?q={qi}",
        "google_exact": f"https://www.google.com/search?q=%22{number_intl}%22",
        "bing": f"https://www.bing.com/search?q={qi}",
        "duckduckgo": f"https://duckduckgo.com/?q={qi}",
        "yandex": f"https://yandex.com/search/?text={qi}",
        "facebook": f"https://www.facebook.com/search/top?q={qn}",
        "instagram": f"https://www.instagram.com/explore/tags/{qn}/",
        "tiktok": f"https://www.tiktok.com/search/user?q={qn}",
        "twitter": f"https://twitter.com/search?q={qn}",
        "reddit": f"https://www.reddit.com/search/?q={qn}",
        "truecaller": f"https://www.truecaller.com/search/id/{number_intl}",
        "getcontact": f"https://www.getcontact.com/en/search?q={number_intl}",
        "sync_me": f"https://sync.me/search/?number={number_intl}",
        "callapp": f"https://callapp.com/search?number={number_intl}",
        "numlookup": f"https://www.numlookup.com/lookup/{number_intl}",
        "whatsapp": f"https://wa.me/{number_intl}",
        # Indonesian marketplaces & directories
        "olx": f"https://www.olx.co.id/index.html?q={urllib.parse.quote(number_intl)}",
        "tokopedia": f"https://www.tokopedia.com/search?q={urllib.parse.quote(number_intl)}",
        "bukalapak": f"https://www.bukalapak.com/search/products?q={urllib.parse.quote(number_intl)}",
        "shopee": f"https://shopee.co.id/search?keyword={urllib.parse.quote(number_intl)}",
        "blibli": f"https://www.blibli.com/search?searchvalue={urllib.parse.quote(number_intl)}",
        # Indonesian people/faces search
        "namepeople": f"https://www.namepeople.com/?s={urllib.parse.quote(number_local)}",
        # Reverse phone lookup
        "whitepage_id": f"https://www.whitepages.com.ph/search?query={number_intl}",
        "telkomsel": f"https://www.telkomsel.com/cari?query={urllib.parse.quote(number_local)}",
    }}


# ---------------------------------------------------------------------------
# 7. Extract phones from text
# ---------------------------------------------------------------------------
def extract_phones(text: str) -> dict:
    patterns = [
        r"\+62[\s-]?8\d{1,3}[\s-]?\d{3,4}[\s-]?\d{3,5}",
        r"\b0\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,5}\b",
        r"\b62\d{9,13}\b",
    ]
    found = set()
    for p in patterns:
        for m in re.findall(p, text):
            d = re.sub(r"\D", "", m)
            if 9 <= len(d) <= 15:
                found.add(d)
    return {"ok": True, "source": "phone-extractor", "data": sorted(found)}


# ---------------------------------------------------------------------------
# 8. Jina reader — scrape social pages (JS-heavy) into text/JSON
# ---------------------------------------------------------------------------
def jina_scrape(url: str, timeout: int = 30) -> dict:
    """https://r.jina.ai/<url> -> profile text/JSON. Free, no key.
    Send Accept: application/json so Jina returns structured JSON.
    """
    import time
    last_err = None
    last_code = None
    for attempt in range(3):
        s, b = _get("https://r.jina.ai/" + url, timeout=timeout,
                    headers={"Accept": "application/json",
                             "User-Agent": "Mozilla/5.0 (compatible; osint/1.0)"})
        if s == 200:
            break
        last_code = s
        last_err = f"http {s}" if s else b
        if s in (402, 403, 429, 451):  # rate / abuse / captcha -> backoff
            time.sleep(2 + attempt * 2)
            continue
        return {"ok": False, "source": "jina", "error": last_err, "url": url}
    else:
        # retries exhausted: mark blocked if due to rate/abuse
        return {"ok": False, "source": "jina", "blocked": last_code in (402, 403, 429, 451),
                "error": last_err, "url": url}

    # JSON mode (most reliable)
    try:
        j = json.loads(b)
        # Jina may return structured errors (block, etc.)
        if j.get("code") in (403, 402, 429, 451) or j.get("name") in (
                "AbuseAlleviationError", "AuthenticationRequiredError", "RateLimitError"):
            return {"ok": False, "source": "jina", "blocked": True,
                    "error": j.get("message") or f"jina code {j.get('code')}", "url": url}

        d = j.get("data", j) or {}
        if not d:
            return {"ok": False, "source": "jina", "error": j.get("message") or "empty data", "url": url}
        return {"ok": True, "source": "jina", "data": {
            "url": url, "title": d.get("title"), "description": d.get("description"),
            "content": (d.get("content") or "")[:4000], "warning": d.get("warning"),
        }}
    except Exception:
        pass

    # markdown text mode (fallback)
    title = desc = None
    for line in b.splitlines():
        if line.startswith("Title:") and not title:
            title = line[6:].strip()
        elif line.startswith("Description:") and not desc:
            desc = line[12:].strip()
    content = b.split("Markdown Content:", 1)[1].strip() if "Markdown Content:" in b else ""
    return {"ok": True, "source": "jina", "data": {
        "url": url, "title": title, "description": desc, "content": content[:3000],
    }}


def social_profile(username: str, platform: str) -> dict:
    """Resolve social profiles via Jina reader + multi-signal scoring engine.

    Returns tri-state status: found | not_found | blocked | unknown
    + confidence score 0-100 + extracted data (name, bio, followers).
    """
    urls = {
        "instagram": [f"https://www.instagram.com/{username}/"],
        "tiktok": [f"https://www.tiktok.com/@{username}"],
        "twitter": [f"https://twitter.com/{username}", f"https://nitter.net/{username}"],
        "x": [f"https://x.com/{username}", f"https://nitter.net/{username}"],
        "facebook": [f"https://www.facebook.com/{username}", f"https://m.facebook.com/{username}"],
        "threads": [f"https://www.threads.net/@{username}"],
        "linkedin": [f"https://www.linkedin.com/in/{username}"],
        "snapchat": [f"https://www.snapchat.com/add/{username}"],
        "pinterest": [f"https://www.pinterest.com/{username}/"],
        "youtube": [f"https://www.youtube.com/@{username}"],
        "reddit": [f"https://www.reddit.com/user/{username}"],
        "twitch": [f"https://www.twitch.tv/{username}"],
        "medium": [f"https://medium.com/@{username}"],
        "telegram": [f"https://t.me/{username}"],
        "github": [f"https://github.com/{username}"],
    }
    if platform not in urls:
        return {"ok": False, "source": "social", "error": "platform not supported"}

    last_err = None
    blocked = False
    for url in urls[platform]:
        r = jina_scrape(url)
        if not r.get("ok"):
            last_err = r.get("error")
            if r.get("blocked"):
                blocked = True
            continue
        verdict = analyze_profile(platform, username, r["data"])
        verdict.update({"platform": platform, "username": username, "url": url})
        return {"ok": True, "source": f"social-{platform}", "data": verdict}

    status = "blocked" if blocked else "unknown"
    return {"ok": True, "source": f"social-{platform}", "data": {
        "platform": platform, "username": username, "url": urls[platform][0],
        "status": status, "found": False, "confidence": 0,
        "reason": last_err or ("diblokir Jina (rate/captcha)" if blocked else "tidak ada data"),
    }}


# ---------------------------------------------------------------------------
# Social profile scoring engine
# ---------------------------------------------------------------------------
_NEGATIVES = [
    "couldn't find", "couldn’t find", "couldn't find this account", "not found",
    "page not found", "page isn't available", "this page isn't available",
    "nothing here", "doesn't exist", "no posts", "sorry, this page",
    "don't have permission", "account suspended", "page doesn't exist",
    "the link you followed may be broken", "user not found",
]
_LOGIN_WALL = [
    "log into facebook", "log in to continue", "sign up | linkedin",
    "join linkedin", "see posts, photos and more", "log in • instagram",
    "instagram photos and videos", "sign in to continue", "you must log in",
    "create an account or log in",
]

_PLATFORM_HANDLE_RE = {
    "tiktok": re.compile(r"@([\w.]+)"),
    "twitter": re.compile(r"@([\w]+)"),
    "x": re.compile(r"@([\w]+)"),
    "youtube": re.compile(r"@([\w.-]+)"),
    "instagram": re.compile(r"@([\w.]+)"),
    "threads": re.compile(r"@([\w.]+)"),
}

# generic platform taglines (exact title match = not a profile)
_GENERIC_TITLES = {
    "github": {"build software better, together", "github", "github · build and ship software on a single, collaborative platform"},
    "youtube": {"youtube", "404 not found"},
    "tiktok": {"tiktok - make your day", "tiktok"},
    "twitter": {"twitter", "x. it's what's happening", "nitter.net", "nitter"},
    "x": {"twitter", "x. it's what's happening", "nitter.net"},
    "instagram": {"instagram", "login • instagram", "instagram photos and videos"},
    "facebook": {"facebook", "log in", "log into facebook"},
    "linkedin": {"linkedin", "linkedin: log in or sign up", "sign up | linkedin"},
    "reddit": {"reddit", "reddit - the heart of the internet", "reddit - dive into anything"},
    "twitch": {"twitch"},
    "snapchat": {"snapchat"},
    "threads": {"threads"},
    "medium": {"medium"},
    "telegram": set(),
    "pinterest": {"pinterest"},
}


def analyze_profile(platform: str, username: str, d: dict) -> dict:
    """Score profile existence from Jina title/description/content."""
    title = (d.get("title") or "").strip()
    desc = (d.get("description") or "").strip()
    content = (d.get("content") or "").strip()
    tl, dl, cl = title.lower(), desc.lower(), content.lower()
    blob = f"{tl}\n{dl}\n{cl}"
    uname = username.lower()

    signals = []      # positive signals
    score = 0

    # --- hard negatives ---
    for n in _NEGATIVES:
        if n in blob:
            # "not found" may appear in generic titles; ensure it's not a false trigger
            return {"status": "not_found", "found": False, "confidence": 0,
                    "reason": f"marker: '{n}'", "title": title, "raw": content[:400]}
    if not title and not content:
        return {"status": "not_found", "found": False, "confidence": 0,
                "reason": "empty page", "title": title, "raw": ""}
    if "404" in tl and len(content) < 40:
        return {"status": "not_found", "found": False, "confidence": 0,
                "reason": "404", "title": title, "raw": content[:200]}

    # --- login wall ---
    for lw in _LOGIN_WALL:
        if lw in blob:
            return {"status": "blocked", "found": False, "confidence": 15,
                    "reason": f"login wall ('{lw}') — unconfirmed",
                    "title": title, "raw": content[:300]}

    # --- exact generic title -> not a profile (except telegram) ---
    gset = _GENERIC_TITLES.get(platform, set())
    if tl in gset:
        return {"status": "not_found", "found": False, "confidence": 5,
                "reason": f"generic title ('{title}')", "title": title, "raw": content[:200]}

    # --- Telegram special case: "Telegram: Contact @x" = placeholder (handle unused) ---
    if platform == "telegram":
        is_placeholder = tl.startswith("telegram: contact @") or tl == "telegram"
        has_real = (bool(desc)) or ("subscribers" in cl) or ("members" in cl) or ("tgme_page_photo" in blob)
        if is_placeholder and not has_real:
            return {"status": "not_found", "found": False, "confidence": 5,
                    "reason": "placeholder contact page (handle unused)",
                    "title": title, "raw": content[:200]}
        if has_real:
            score += 45; signals.append("telegram profile confirmed")

    # --- positive signals ---
    hre = _PLATFORM_HANDLE_RE.get(platform)
    if hre and hre.search(title) and uname in tl:
        score += 30; signals.append("handle match in title")
    elif uname in tl:
        score += 22; signals.append("username in title")

    # specific title (not generic, not a system URL)
    clean_title = title.replace("@", "").lower()
    generic_single = {"instagram", "facebook", "tiktok", "twitter", "x", "threads",
                      "snapchat", "linkedin", "twitch", "youtube", "github", "reddit", "medium"}
    if title and len(title) > 3 and clean_title not in generic_single \
            and not tl.startswith("http") and "amazon-adsystem" not in tl:
        score += 20; signals.append("specific title")

    if desc and len(desc) > 5:
        score += 12; signals.append("has description")

    metric = re.search(r"(\d[\d.,]*\s*[kmb]?)\s*(followers?|likes?|views?|subscribers?|pengikut|suka|tayangan|members?)", blob)
    if metric:
        score += 20; signals.append(f"metric: {metric.group(0).strip()}")

    if len(content) > 120:
        score += 10; signals.append("substantial content")
    if any(w in cl for w in ["follow", "followers", "posts", "videos", "subscribe",
                             "joined", "bio", "suka", "mengikuti", "kiriman"]):
        score += 8; signals.append("profile elements")

    score = min(score, 100)
    if score >= 55:
        status = "found"
    elif score >= 30:
        status = "probable"
    else:
        status = "unknown"

    name = title
    for suffix in [" | TikTok", " • Instagram photos and videos", " | Facebook",
                   " | LinkedIn", " - YouTube", " | Pinterest", " | Snapchat",
                   " · GitHub", " | Twitch", " - Overview"]:
        name = name.replace(suffix, "")
    name = re.sub(r"\s*[\(\[].*?[\)\]]\s*$", "", name).strip()

    return {
        "status": status, "found": status in ("found", "probable"),
        "confidence": score, "signals": signals,
        "display_name": name if name and len(name) > 1 else None,
        "bio": desc or None, "title": title, "raw": content[:300],
    }


def _profile_found(title: str, desc: str, content: str, platform: str) -> bool:
    """Legacy compat: call the scoring engine."""
    v = analyze_profile(platform, "", {"title": title, "description": desc, "content": content})
    return v.get("found", False)


def social_resolve_all(username: str, platforms: list[str] | None = None) -> dict:
    platforms = platforms or ["instagram", "facebook", "twitter", "tiktok", "threads",
                              "snapchat", "pinterest", "youtube", "linkedin", "telegram",
                              "github", "reddit", "twitch", "medium"]
    out = {}
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {p: ex.submit(social_profile, username, p) for p in platforms}
            for p, fut in futs.items():
                try:
                    out[p] = fut.result(timeout=40)
                except Exception as e:
                    out[p] = {"ok": False, "source": f"social-{p}", "error": str(e)}
    except ImportError:
        for p in platforms:
            out[p] = social_profile(username, p)

    # ringkasan
    found, probable, blocked, notfound = [], [], [], []
    for p, r in out.items():
        st = (r.get("data") or {}).get("status")
        if st == "found": found.append(p)
        elif st == "probable": probable.append(p)
        elif st == "blocked": blocked.append(p)
        elif st == "not_found": notfound.append(p)
    out["_summary"] = {
        "username": username,
        "found": found, "probable": probable, "blocked": blocked, "not_found": notfound,
        "total_checked": len(platforms),
    }
    return out


# ---------------------------------------------------------------------------
# 9. Messaging app presence (hint, not confirmation)
# ---------------------------------------------------------------------------
def messaging_check(number_intl: str) -> dict:
    out = {}
    # Viber community page
    s, b = _get(f"https://chats.viber.com/{number_intl}")
    out["viber"] = {"url": f"https://chats.viber.com/{number_intl}",
                    "reachable": s == 200}
    # WhatsApp click-to-chat (always 200, but provide the link anyway)
    out["whatsapp"] = {"url": f"https://wa.me/{number_intl}", "check": "manual (needs app)"}
    # LINE
    out["line"] = {"url": f"https://line.me/ti/p/~{number_intl}", "check": "manual"}
    # Telegram
    out["telegram"] = {"url": f"https://t.me/+{number_intl}", "check": "via telegram resolver"}
    return {"ok": True, "source": "messaging", "data": out}


# ---------------------------------------------------------------------------
# Combined resolution
# ---------------------------------------------------------------------------
def resolve_all(number_intl: str, number_local: str,
                truecaller_cookie: str = "", serpapi_key: str = "",
                searxng_instance: str = "", do_search: bool = True,
                do_social: bool = True, usernames: list[str] | None = None) -> dict:
    q = f'"{number_local}" OR "+{number_intl}"'

    def _search():
        if serpapi_key:
            return serpapi_search(q, serpapi_key)
        if searxng_instance:
            return searxng_search(q, searxng_instance)
        return search_links(number_local, number_intl)

    # Auto-generate candidate usernames from the number
    auto_cands = generate_candidates(number_local, number_intl)

    jobs = {
        "telegram": lambda: telegram_resolve(number_intl),
        "truecaller": lambda: truecaller(number_intl, truecaller_cookie),
        "handle_pivot": lambda: handle_pivot(number_local, variants=auto_cands),
        "messaging": lambda: messaging_check(number_intl),
    }
    if do_search:
        jobs["search"] = _search
    # social profile resolve via Jina (when candidate usernames exist)
    if do_social:
        # merge explicit usernames with auto-generated candidates, dedupe preserving order
        merged_cands = list(usernames or [])
        seen: set[str] = set(merged_cands)
        for c in auto_cands:
            if c not in seen and "@" not in c:
                merged_cands.append(c)
                seen.add(c)
        for u in merged_cands[:5]:  # up to 5 candidate social checks
            if u and "@" not in u:
                jobs[f"social_{u}"] = (lambda uu=u: social_resolve_all(uu))

    out = {}
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = {k: ex.submit(fn) for k, fn in jobs.items()}
            for k, fut in futs.items():
                try:
                    out[k] = fut.result(timeout=60)
                except Exception as e:
                    out[k] = {"ok": False, "source": k, "error": str(e)}
    except ImportError:
        for k, fn in jobs.items():
            out[k] = fn()
    return out
