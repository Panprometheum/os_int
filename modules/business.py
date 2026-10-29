"""business.py - business / company registry lookup.

Sources:
  - OpenCorporates API (needs token; some public endpoints are limited)
  - UK Companies House (needs API key, free)
  - SEC EDGAR (US public companies, FREE, no key)
  - GLEIF LEI (global legal entity, FREE, no key)
  - Indonesia: AHU Online (limited scrape) + OSS

All return {ok, source, data, error}.
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
UA = "Mozilla/5.0 (compatible; osint-business/1.0)"


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
# SEC EDGAR — US public companies (FREE, no key)
# ---------------------------------------------------------------------------
def sec_edgar(company: str) -> dict:
    s, b = _get("https://www.sec.gov/cgi-bin/browse-edgar",
                headers={"User-Agent": "osint-research contact@example.com",
                         "Accept": "application/json"},
                params={"company": company, "type": "10-K", "dateb": "", "owner": "include",
                        "count": "20", "action": "getcompany", "output": "atom"})
    if s is None:
        return {"ok": False, "source": "sec-edgar", "error": b}
    # EDGAR full-text search API (lebih bersih)
    s2, b2 = _get(f"https://efts.sec.gov/LATEST/search-index?q=%22{urllib.parse.quote(company)}%22&forms=10-K")
    # use the EDGAR company search JSON
    s3, b3 = _get("https://www.sec.gov/cgi-bin/browse-edgar",
                  headers={"User-Agent": "osint-research contact@example.com"},
                  params={"company": company, "type": "10-K", "action": "getcompany", "output": "atom",
                          "count": "10"})
    try:
        import re
        if s3 == 200:
            entries = re.findall(r"<title>([^<]+)</title>", b3)
            ciks = re.findall(r"CIK=(\d+)", b3)
            return {"ok": True, "source": "sec-edgar", "data": {
                "company": company, "results": [{"title": t, "cik": c} for t, c in zip(entries[1:11], ciks[:10])],
            }}
    except Exception:
        pass
    return {"ok": True, "source": "sec-edgar", "data": {"company": company, "raw": b3[:500] if b3 else ""}}


def sec_edgar_fulltext(q: str) -> dict:
    s, b = _get("https://efts.sec.gov/LATEST/search-index",
                params={"q": f'"{q}"', "forms": "10-K,10-Q,8-K"})
    if s == 200:
        try:
            return {"ok": True, "source": "sec-edgar-fulltext", "data": json.loads(b)}
        except Exception:
            pass
    # correct endpoint: /LATEST/search-index is invalid; use the EFS UI API
    s, b = _get("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(f'"{q}"'))
    s, b = _get("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(q), params={"forms": "10-K"})
    if s == 200:
        try:
            return {"ok": True, "source": "sec-edgar-fulltext", "data": json.loads(b)}
        except Exception as e:
            return {"ok": False, "source": "sec-edgar-fulltext", "error": str(e)}
    return {"ok": False, "source": "sec-edgar-fulltext", "error": f"http {s}"}


# ---------------------------------------------------------------------------
# GLEIF LEI — global legal entity (FREE, no key)
# ---------------------------------------------------------------------------
def gleif_lei(name: str) -> dict:
    s, b = _get("https://api.gleif.org/api/v1/lei-records",
                params={"filter[entity.legalName]": name, "page[size]": 10})
    if s is None or s != 200:
        return {"ok": False, "source": "gleif", "error": f"http {s}"}
    try:
        j = json.loads(b)
        records = []
        for r in j.get("data", []):
            a = r.get("attributes", {})
            ent = a.get("entity", {})
            legal = ent.get("legalAddress", {})
            records.append({
                "lei": a.get("lei"), "name": ent.get("legalName", {}).get("name"),
                "status": ent.get("status"), "jurisdiction": ent.get("jurisdiction"),
                "legal_form": ent.get("legalForm", {}).get("id") if ent.get("legalForm") else None,
                "address": f"{legal.get('addressLines', [''])[0] if legal.get('addressLines') else ''} {legal.get('city','')} {legal.get('country','')}".strip(),
                "registration_status": a.get("registration", {}).get("status"),
            })
        return {"ok": True, "source": "gleif", "data": {"name": name, "count": len(records), "entities": records}}
    except Exception as e:
        return {"ok": False, "source": "gleif", "error": str(e)}


def gleif_by_lei(lei: str) -> dict:
    s, b = _get(f"https://api.gleif.org/api/v1/lei-records/{urllib.parse.quote(lei)}")
    if s is None or s != 200:
        return {"ok": False, "source": "gleif", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "gleif", "data": json.loads(b).get("data", {})}
    except Exception as e:
        return {"ok": False, "source": "gleif", "error": str(e)}


# ---------------------------------------------------------------------------
# OpenCorporates (needs token)
# ---------------------------------------------------------------------------
def opencorporates(name: str, api_token: str = "") -> dict:
    url = "https://api.opencorporates.com/v0.4/companies/search"
    params = {"q": name}
    if api_token:
        params["api_token"] = api_token
    s, b = _get(url, params=params)
    if s is None or s != 200:
        return {"ok": False, "source": "opencorporates",
                "error": f"http {s} (needs token — register at opencorporates.com)"}
    try:
        j = json.loads(b)
        results = []
        for c in (j.get("results", {}).get("companies") or []):
            comp = c.get("company", {})
            results.append({
                "name": comp.get("name"), "jurisdiction": comp.get("jurisdiction_code"),
                "number": comp.get("company_number"), "status": comp.get("current_status"),
                "incorporation": comp.get("incorporation_date"),
                "type": comp.get("company_type"), "url": comp.get("opencorporates_url"),
            })
        return {"ok": True, "source": "opencorporates", "data": {"name": name, "count": len(results), "companies": results}}
    except Exception as e:
        return {"ok": False, "source": "opencorporates", "error": str(e)}


# ---------------------------------------------------------------------------
# UK Companies House (needs API key, free)
# ---------------------------------------------------------------------------
def uk_companies_house(name: str, api_key: str = "") -> dict:
    if not api_key:
        return {"ok": False, "source": "companies-house", "error": "needs API key (free at company-information.service.gov.uk)"}
    import base64
    token = base64.b64encode(f"{api_key}:".encode()).decode()
    s, b = _get("https://api.company-information.service.gov.uk/search/companies",
                headers={"Authorization": f"Basic {token}"}, params={"q": name})
    if s is None or s != 200:
        return {"ok": False, "source": "companies-house", "error": f"http {s}"}
    try:
        j = json.loads(b)
        results = []
        for it in j.get("items", [])[:15]:
            results.append({
                "title": it.get("title"), "number": it.get("company_number"),
                "status": it.get("company_status"), "type": it.get("company_type"),
                "created": it.get("date_of_creation"),
                "address": it.get("address_snippet"), "url": it.get("links", {}).get("self"),
            })
        return {"ok": True, "source": "companies-house", "data": {"name": name, "count": len(results), "companies": results}}
    except Exception as e:
        return {"ok": False, "source": "companies-house", "error": str(e)}


# ---------------------------------------------------------------------------
# Indonesia — AHU Online (limited scrape; usually needs captcha/session)
# ---------------------------------------------------------------------------
def ahu_indonesia(name: str) -> dict:
    """AHU Online has protection; we provide the endpoint + link + fallback."""
    # endpoint publik yg kadang works
    s, b = _get("https://ahu.go.id/pencarian/profil-badan-hukum",
                params={"nama": name})
    reachable = s == 200
    return {"ok": True, "source": "ahu-indonesia", "data": {
        "name": name,
        "reachable": reachable,
                "note": "AHU Online often needs captcha/session. Open manually:",
        "links": {
            "ahu_profil": "https://ahu.go.id/pencarian/profil-badan-hukum",
            "ahu_persero": "https://ahu.go.id/pencarian/profil-perseroan",
            "oss": "https://oss.go.id/informasi/kbli-berbasis-risiko",
            "direktori": "https://www.google.com/search?q=" + urllib.parse.quote(f'site:ahu.go.id OR site:oss.go.id OR "PT {name}"'),
        },
    }}


# ---------------------------------------------------------------------------
def lookup_all(name: str, opencorporates_token: str = "", companies_house_key: str = "") -> dict:
    jobs = {
        "gleif": lambda: gleif_lei(name),
        "sec_edgar": lambda: sec_edgar(name),
    }
    if opencorporates_token:
        jobs["opencorporates"] = lambda: opencorporates(name, opencorporates_token)
    if companies_house_key:
        jobs["companies_house"] = lambda: companies_house(name, companies_house_key)
    # Indonesia selalu disertakan (link)
    jobs["ahu_indonesia"] = lambda: ahu_indonesia(name)
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
