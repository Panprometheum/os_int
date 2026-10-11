"""devprofiles.py - lookup profil developer & komunitas (API publik, tanpa key).

Source: GitHub, GitLab, PyPI, npm, DockerHub, StackOverflow, Keybase,
        HackerNews, Mastodon, Reddit, DevTo, Codeberg, Gitea.

Semua balikin {ok, source, data, error} atau dict per-platform.
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

TIMEOUT = 12
UA = "Mozilla/5.0 (compatible; osint-devprofiles/1.0)"


def _json(url: str, headers: dict | None = None, timeout: int = TIMEOUT):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    try:
        if _req is not None:
            r = _req.get(url, headers=h, timeout=timeout, verify=False)
            if r.status_code != 200:
                return None, f"http {r.status_code}"
            return r.json(), None
        req = urllib.request.Request(url, headers=h)
        import ssl
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode("utf-8", "replace")), None
    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------------------------
def github(username: str) -> dict:
    j, err = _json(f"https://api.github.com/users/{urllib.parse.quote(username)}")
    if err or not j or j.get("message") == "Not Found":
        return {"platform": "github", "found": False, "error": err or "not found"}
    repos, _ = _json(f"https://api.github.com/users/{urllib.parse.quote(username)}/repos?per_page=100&sort=updated")
    emails = set()
    for r in (repos or [])[:15]:
        cs, _ = _json(f"https://api.github.com/repos/{urllib.parse.quote(username)}/{urllib.parse.quote(r['name'])}/commits?per_page=15")
        for c in (cs or []):
            e = c.get("commit", {}).get("author", {}).get("email")
            if e:
                emails.add(e)
    return {"platform": "github", "found": True, "data": {
        "name": j.get("name"), "bio": j.get("bio"), "company": j.get("company"),
        "location": j.get("location"), "email": j.get("email"), "blog": j.get("blog"),
        "twitter": j.get("twitter_username"), "public_repos": j.get("public_repos"),
        "followers": j.get("followers"), "created": j.get("created_at"),
        "avatar": j.get("avatar_url"), "url": j.get("html_url"),
        "commit_emails": sorted(emails),
    }}


def gitlab(username: str) -> dict:
    # GitLab public API sering 403 utk search; coba profile langsung
    j, err = _json(f"https://gitlab.com/api/v4/users?username={urllib.parse.quote(username)}")
    if err or not j:
        return {"platform": "gitlab", "found": False, "error": err or "empty"}
    if not isinstance(j, list) or not j:
        return {"platform": "gitlab", "found": False}
    u = j[0]
    return {"platform": "gitlab", "found": True, "data": {
        "name": u.get("name"), "username": u.get("username"), "state": u.get("state"),
        "avatar": u.get("avatar_url"), "url": u.get("web_url"),
        "bio": u.get("bio"), "location": u.get("location"),
    }}


def pypi(username: str) -> dict:
    # PyPI: profile page (HTML) + packages by user
    j, err = _json(f"https://pypi.org/user/{urllib.parse.quote(username)}/")
    # PyPI user page bukan JSON; cek via packages
    pkgs, _ = _json(f"https://pypi.org/pypi/{urllib.parse.quote(username)}/json")
    if pkgs:
        info = pkgs.get("info", {})
        return {"platform": "pypi-package", "found": True, "data": {
            "package": info.get("name"), "version": info.get("version"),
            "author": info.get("author"), "author_email": info.get("author_email"),
            "home_page": info.get("home_page"), "summary": info.get("summary"),
        }}
    return {"platform": "pypi", "found": False}


def npm(username: str) -> dict:
    j, err = _json(f"https://registry.npmjs.org/-/user/org.couchdb.user:{urllib.parse.quote(username)}")
    if err or not j or not j.get("name"):
        # coba search package
        s, _ = _json(f"https://registry.npmjs.org/-/v1/search?text=maintainer:{urllib.parse.quote(username)}&size=10")
        if s and s.get("objects"):
            return {"platform": "npm", "found": True, "data": {
                "packages": [{"name": o.get("package", {}).get("name"),
                              "version": o.get("package", {}).get("version"),
                              "desc": o.get("package", {}).get("description")}
                             for o in s["objects"][:10]]}}
        return {"platform": "npm", "found": False}
    return {"platform": "npm", "found": True, "data": {"name": j.get("name")}}


def dockerhub(username: str) -> dict:
    j, err = _json(f"https://hub.docker.com/v2/users/{urllib.parse.quote(username)}/")
    if err or not j or not j.get("username"):
        return {"platform": "dockerhub", "found": False}
    return {"platform": "dockerhub", "found": True, "data": {
        "username": j.get("username"), "name": j.get("full_name"),
        "location": j.get("location"), "company": j.get("company"),
        "profile_url": j.get("profile_url"), "gravatar": j.get("gravatar_url"),
    }}


def stackoverflow(username: str) -> dict:
    j, err = _json("https://api.stackexchange.com/2.3/users"
                   f"?order=desc&sort=reputation&inname={urllib.parse.quote(username)}&site=stackoverflow")
    if err or not j or not j.get("items"):
        return {"platform": "stackoverflow", "found": False}
    u = j["items"][0]
    return {"platform": "stackoverflow", "found": True, "data": {
        "display_name": u.get("display_name"), "reputation": u.get("reputation"),
        "badges": u.get("badge_counts"), "location": u.get("location"),
        "website": u.get("website_url"), "link": u.get("link"),
        "created": u.get("creation_date"), "user_id": u.get("user_id"),
    }}


def keybase(username: str) -> dict:
    j, err = _json(f"https://keybase.io/_/api/1.0/user/lookup.json?username={urllib.parse.quote(username)}")
    if err or not j or not j.get("them"):
        return {"platform": "keybase", "found": False}
    them = j["them"][0]
    basics = them.get("basics", {})
    prof = them.get("profile", {})
    proofs = them.get("proofs_summary", {}).get("all", [])
    return {"platform": "keybase", "found": True, "data": {
        "username": basics.get("username"), "full_name": prof.get("full_name"),
        "bio": prof.get("bio"), "location": prof.get("location"),
        "proofs": [{"platform": p.get("proof_type"), "handle": p.get("nametag"),
                    "url": p.get("service_url")} for p in proofs],
    }}


def hackernews(username: str) -> dict:
    j, err = _json(f"https://hacker-news.firebaseio.com/v0/user/{urllib.parse.quote(username)}.json")
    if err or not j:
        return {"platform": "hackernews", "found": False}
    return {"platform": "hackernews", "found": True, "data": {
        "id": j.get("id"), "karma": j.get("karma"), "about": j.get("about"),
        "created": j.get("created"), "submitted": j.get("submitted", [])[:5],
    }}


def mastodon(username: str, instance: str = "mastodon.social") -> dict:
    j, err = _json(f"https://{instance}/api/v1/accounts/lookup?acct={urllib.parse.quote(username)}")
    if err or not j or not j.get("id"):
        return {"platform": "mastodon", "found": False}
    return {"platform": "mastodon", "found": True, "data": {
        "display_name": j.get("display_name"), "username": j.get("username"),
        "note": j.get("note"), "avatar": j.get("avatar"),
        "followers": j.get("followers_count"), "following": j.get("following_count"),
        "statuses": j.get("statuses_count"), "created": j.get("created_at"),
        "url": j.get("url"), "bot": j.get("bot"),
    }}


def reddit(username: str) -> dict:
    j, err = _json(f"https://www.reddit.com/user/{urllib.parse.quote(username)}/about.json",
                   headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"})
    if err or not j or not j.get("data"):
        return {"platform": "reddit", "found": False, "error": err or "not found/blocked"}
    d = j["data"]
    return {"platform": "reddit", "found": True, "data": {
        "name": d.get("name"), "comment_karma": d.get("comment_karma"),
        "link_karma": d.get("link_karma"), "created": d.get("created_utc"),
        "icon": d.get("icon_img"), "verified": d.get("verified"),
    }}


def devto(username: str) -> dict:
    j, err = _json(f"https://dev.to/api/users/by_username?url={urllib.parse.quote(username)}")
    if err or not j or not j.get("username"):
        return {"platform": "devto", "found": False}
    return {"platform": "devto", "found": True, "data": {
        "name": j.get("name"), "username": j.get("username"), "summary": j.get("summary"),
        "location": j.get("location"), "website": j.get("website_url"),
        "github": j.get("github_username"), "twitter": j.get("twitter_username"),
        "joined": j.get("joined_at"), "profile": j.get("profile_image"),
    }}


def codeberg(username: str) -> dict:
    j, err = _json(f"https://codeberg.org/api/v1/users/{urllib.parse.quote(username)}")
    if err or not j or not j.get("login"):
        return {"platform": "codeberg", "found": False}
    return {"platform": "codeberg", "found": True, "data": {
        "login": j.get("login"), "full_name": j.get("full_name"),
        "email": j.get("email"), "location": j.get("location"),
        "website": j.get("website"), "bio": j.get("description"),
        "followers": j.get("followers_count"), "avatar": j.get("avatar_url"),
    }}


# ---------------------------------------------------------------------------
def lookup_all(username: str, reddit_ua_ok: bool = True) -> dict:
    """Jalankan semua source paralel."""
    jobs = {
        "github": github, "gitlab": gitlab, "pypi": pypi, "npm": npm,
        "dockerhub": dockerhub, "stackoverflow": stackoverflow, "keybase": keybase,
        "hackernews": hackernews, "mastodon": mastodon, "devto": devto,
        "codeberg": codeberg,
    }
    if reddit_ua_ok:
        jobs["reddit"] = reddit
    out = {}
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {k: ex.submit(fn, username) for k, fn in jobs.items()}
            for k, fut in futs.items():
                try:
                    out[k] = fut.result(timeout=20)
                except Exception as e:
                    out[k] = {"platform": k, "found": False, "error": str(e)}
    except ImportError:
        for k, fn in jobs.items():
            out[k] = fn(username)
    return out
