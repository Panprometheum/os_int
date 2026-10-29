"""ipintel.py - IP intelligence (free + optional key).

Free sources:
  - Shodan InternetDB  (ports, hostnames, cpes, vulns)
  - IPinfo             (hostname, geo, org, ASN)
  - GreyNoise community (noise/riot scanning)
  - ip-api / ipwho.is  (geo fallback)

Sources needing a key (optional):
  - Shodan full  (services, banners, vulns detail)
  - Censys       (hosts, services)
  - AbuseIPDB    (reputation, reports)

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

TIMEOUT = 15
UA = "Mozilla/5.0 (compatible; osint-ipintel/1.0)"


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
def shodan_internetdb(ip: str) -> dict:
    """Free, no key. Ports, hostnames, cpes, tags, vulns."""
    s, b = _get(f"https://internetdb.shodan.io/{urllib.parse.quote(ip)}")
    if s == 404:
        return {"ok": True, "source": "shodan-internetdb", "data": {"ip": ip, "found": False}}
    if s is None or s != 200:
        return {"ok": False, "source": "shodan-internetdb", "error": f"http {s}"}
    try:
        j = json.loads(b)
        return {"ok": True, "source": "shodan-internetdb", "data": {
            "ip": ip, "found": True,
            "ports": j.get("ports", []), "hostnames": j.get("hostnames", []),
            "cpes": j.get("cpes", []), "tags": j.get("tags", []),
            "vulns": j.get("vulns", []),
        }}
    except Exception as e:
        return {"ok": False, "source": "shodan-internetdb", "error": str(e)}


def shodan_host(ip: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "shodan", "error": "needs API key"}
    s, b = _get(f"https://api.shodan.io/shodan/host/{urllib.parse.quote(ip)}?key={api_key}")
    if s is None or s != 200:
        return {"ok": False, "source": "shodan", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "shodan", "data": json.loads(b)}
    except Exception as e:
        return {"ok": False, "source": "shodan", "error": str(e)}


def ipinfo(ip: str) -> dict:
    s, b = _get(f"https://ipinfo.io/{urllib.parse.quote(ip)}/json")
    if s is None or s != 200:
        return {"ok": False, "source": "ipinfo", "error": f"http {s}"}
    try:
        j = json.loads(b)
        loc = j.get("loc", "")
        lat, lon = (loc.split(",") if "," in loc else (None, None))
        return {"ok": True, "source": "ipinfo", "data": {
            "ip": j.get("ip"), "hostname": j.get("hostname"), "city": j.get("city"),
            "region": j.get("region"), "country": j.get("country"),
            "postal": j.get("postal"), "org": j.get("org"), "timezone": j.get("timezone"),
            "lat": float(lat) if lat else None, "lon": float(lon) if lon else None,
        }}
    except Exception as e:
        return {"ok": False, "source": "ipinfo", "error": str(e)}


def greynoise(ip: str) -> dict:
    s, b = _get(f"https://api.greynoise.io/v3/community/{urllib.parse.quote(ip)}")
    if s is None or s not in (200, 404):
        return {"ok": False, "source": "greynoise", "error": f"http {s}"}
    try:
        j = json.loads(b)
        return {"ok": True, "source": "greynoise", "data": {
            "ip": j.get("ip"), "noise": j.get("noise"), "riot": j.get("riot"),
            "classification": j.get("classification"), "name": j.get("name"),
            "last_seen": j.get("last_seen"), "message": j.get("message"),
        }}
    except Exception as e:
        return {"ok": False, "source": "greynoise", "error": str(e)}


def abuseipdb(ip: str, api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "source": "abuseipdb", "error": "needs API key"}
    s, b = _get("https://api.abuseipdb.com/api/v2/check",
                headers={"Key": api_key, "Accept": "application/json"},
                params={"ipAddress": ip, "maxAgeInDays": 90})
    if s is None or s != 200:
        return {"ok": False, "source": "abuseipdb", "error": f"http {s}"}
    try:
        return {"ok": True, "source": "abuseipdb", "data": json.loads(b).get("data", {})}
    except Exception as e:
        return {"ok": False, "source": "abuseipdb", "error": str(e)}


def censys(ip: str, api_id: str, api_secret: str) -> dict:
    if not (api_id and api_secret):
        return {"ok": False, "source": "censys", "error": "needs api_id + api_secret (Censys Platform v2+)"}
    s, b = _get(f"https://search.censys.io/api/v2/hosts/{urllib.parse.quote(ip)}",
                headers={"Accept": "application/json"},
                timeout=TIMEOUT)
    # Censys needs basic auth; requests handles it via the auth param, fallback here
    if _req is not None:
        try:
            r = _req.get(f"https://search.censys.io/api/v2/hosts/{urllib.parse.quote(ip)}",
                         auth=(api_id, api_secret), timeout=TIMEOUT, verify=False)
            if r.status_code == 200:
                return {"ok": True, "source": "censys", "data": r.json().get("result", {})}
            return {"ok": False, "source": "censys", "error": f"http {r.status_code}: {r.text[:120]}"}
        except Exception as e:
            return {"ok": False, "source": "censys", "error": str(e)}
        return {"ok": False, "source": "censys", "error": "needs requests"}


# ---------------------------------------------------------------------------
def lookup_all(ip: str, shodan_key: str = "", abuse_key: str = "",
               censys_id: str = "", censys_secret: str = "") -> dict:
    jobs = {
        "shodan_internetdb": lambda: shodan_internetdb(ip),
        "ipinfo": lambda: ipinfo(ip),
        "greynoise": lambda: greynoise(ip),
    }
    if shodan_key:
        jobs["shodan_full"] = lambda: shodan_host(ip, shodan_key)
    if abuse_key:
        jobs["abuseipdb"] = lambda: abuseipdb(ip, abuse_key)
    if censys_id and censys_secret:
        jobs["censys"] = lambda: censys(ip, censys_id, censys_secret)
    out = {}
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as ex:
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
