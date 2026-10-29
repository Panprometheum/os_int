"""geo_engine.py - precise location resolution from multiple sources.

Sources (ordered by precision):
  1. WiFi BSSID scan -> Google Geolocation API / Mozilla
  2. Cell tower (MCC/MNC/LAC/CID) -> OpenCellID / UnwiredLabs
  3. IP -> coordinates (ip-api / ipinfo / ipwhois) - coarsest

All functions return a consistent dict:
  {ok, lat, lon, accuracy, source, raw}
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

TIMEOUT = 12
UA = "Mozilla/5.0 (compatible; osint-geo/1.0)"


def _http(url: str, data: bytes | None = None, headers: dict | None = None, method: str | None = None) -> dict | None:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", "replace")
        return json.loads(raw)
    except Exception:
        return None


def _result(ok, lat=None, lon=None, accuracy=None, source="", raw=None, error=None):
    return {
        "ok": ok, "lat": lat, "lon": lon, "accuracy": accuracy,
        "source": source, "raw": raw, "error": error,
    }


# --------------------------------------------------------------------------
    # 1. IP -> coordinates (multi-provider, pick the most precise)
# --------------------------------------------------------------------------
def ip_geo(ip: str) -> dict:
    out = raise_none = None

    # ip-api.com — free, returns city/lat/lon
    j = _http(f"http://ip-api.com/json/{urllib.parse.quote(ip)}"
              "?fields=status,country,regionName,city,zip,lat,lon,isp,org,as,mobile,proxy,hosting,query")
    if j and j.get("status") == "success":
        return _result(True, j.get("lat"), j.get("lon"), None, "ip-api",
                       j, None)

    # ipwho.is — fallback
    j = _http(f"https://ipwho.is/{urllib.parse.quote(ip)}")
    if j and j.get("success"):
        return _result(True, j.get("latitude"), j.get("longitude"), None, "ipwho.is", j, None)

    # ipinfo.io — fallback without key (rate limited)
    j = _http(f"https://ipinfo.io/{urllib.parse.quote(ip)}/json")
    if j and "loc" in j:
        lat, lon = j["loc"].split(",")
        return _result(True, float(lat), float(lon), None, "ipinfo", j, None)

    return _result(False, source="ip-geo", error="all providers failed")


# --------------------------------------------------------------------------
# 2. WiFi BSSID -> location (Google Geolocation / Mozilla Location Service)
# --------------------------------------------------------------------------
def wifi_geo(bssids: list[dict], api_key: str | None = None) -> dict:
    """bssids = [{'mac': 'aa:bb:cc:dd:ee:ff', 'signal': -50}, ...]

    Without an API key, use the more open Mozilla Location Service (MLS).
    """
    if not bssids:
        return _result(False, source="wifi", error="bssid kosong")

    # --- Mozilla Location Service (MLS) ---
    # Endpoint publik: https://location.services.mozilla.com/v1/geolocate?key=test
    payload = {"wifiAccessPoints": bssids}
    data = json.dumps(payload).encode()
    j = _http("https://location.services.mozilla.com/v1/geolocate?key=" + (api_key or "test"),
              data=data, headers={"Content-Type": "application/json"})
    if j and "location" in j:
        loc = j["location"]
        return _result(True, loc.get("lat"), loc.get("lng"), j.get("accuracy"),
                       "mozilla-mls", j, None)

    # --- Google Geolocation (needs key) ---
    if api_key:
        url = "https://www.googleapis.com/geolocation/v1/geolocate?key=" + api_key
        j = _http(url, data=json.dumps({"wifiAccessPoints": bssids}).encode(),
                  headers={"Content-Type": "application/json"})
        if j and "location" in j:
            loc = j["location"]
            return _result(True, loc.get("lat"), loc.get("lng"), j.get("accuracy"),
                           "google-geoloc", j, None)

    return _result(False, source="wifi", error="wifi geoloc failed (MLS/Google)")


# --------------------------------------------------------------------------
# 3. Cell tower -> location (OpenCellID / UnwiredLabs)
# --------------------------------------------------------------------------
def cell_geo(mcc: int, mnc: int, lac: int, cid: int, api_key: str | None = None) -> dict:
    """Cell tower lookup.

    OpenCellID needs a free key (opencellid.org).
    UnwiredLabs also needs a key.
    """
    if api_key:
        url = "https://us1.unwiredlabs.com/v2/process.php"
        payload = {
            "token": api_key,
            "radio": "gsm",
            "mcc": mcc, "mnc": mnc, "lac": lac, "cid": cid,
            "address": 1,
        }
        j = _http(url, data=json.dumps(payload).encode(),
                  headers={"Content-Type": "application/json"})
        if j and j.get("status") == "ok":
            return _result(True, j.get("lat"), j.get("lon"), j.get("accuracy"),
                           "unwiredlabs", j, None)

    # OpenCellID fallback (needs key)
    if api_key:
        url = (f"https://opencellid.org/cell/get?key={api_key}"
               f"&mcc={mcc}&mnc={mnc}&lac={lac}&cellid={cid}&format=json")
        j = _http(url)
        if j and "lat" in j:
            return _result(True, j.get("lat"), j.get("lon"), j.get("range"),
                           "opencellid", j, None)

    return _result(False, source="cell",
                   error="cell geoloc needs API key (OpenCellID/UnwiredLabs)")


# --------------------------------------------------------------------------
# Combination: try the most precise source first
# --------------------------------------------------------------------------
def resolve_best(ip=None, bssids=None, cell=None, wifi_key=None, cell_key=None) -> dict:
    """Try sources in precision order: cell > wifi > ip."""
    attempts = []
    if cell:
        r = cell_geo(*cell, api_key=cell_key)
        r["method"] = "cell"
        attempts.append(r)
        if r["ok"]:
            return {"best": r, "attempts": attempts}
    if bssids:
        r = wifi_geo(bssids, api_key=wifi_key)
        r["method"] = "wifi"
        attempts.append(r)
        if r["ok"]:
            return {"best": r, "attempts": attempts}
    if ip:
        r = ip_geo(ip)
        r["method"] = "ip"
        attempts.append(r)
        if r["ok"]:
            return {"best": r, "attempts": attempts}
    return {"best": None, "attempts": attempts}
