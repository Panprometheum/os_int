"""forensics.py - EXIF, metadata, domain/whois, DNS.

Semua fungsi balikin {ok, data, source, error}.
"""
from __future__ import annotations

import hashlib
import os
import struct
from datetime import datetime


# --------------------------------------------------------------------------
# 1. EXIF / metadata gambar
# --------------------------------------------------------------------------
def exif_image(path: str) -> dict:
    if not os.path.isfile(path):
        return {"ok": False, "source": "exif", "error": "file tidak ada"}

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
    except ImportError:
        return {"ok": False, "source": "exif", "error": "Pillow tidak terpasang"}

    out = {"file": path, "size": os.path.getsize(path),
           "md5": _hash(path, "md5"), "sha256": _hash(path, "sha256")}

    try:
        img = Image.open(path)
        out["format"] = img.format
        out["mode"] = img.mode
        out["dimensions"] = f"{img.width}x{img.height}"
        out["created"] = None

        exif = img.getexif()
        tags = {}
        gps = {}
        if exif:
            for tid, val in exif.items():
                name = TAGS.get(tid, tid)
                tags[str(name)] = _serialize(val)

            # GPS
            gps_ifd = exif.get_ifd(0x8825)
            if gps_ifd:
                for tid, val in gps_ifd.items():
                    gps[str(GPSTAGS.get(tid, tid))] = _serialize(val)

        out["exif"] = tags
        if gps:
            out["gps_raw"] = gps
            coords = _gps_to_decimal(gps)
            if coords:
                out["gps"] = {"lat": coords[0], "lon": coords[1]}
        return {"ok": True, "source": "exif", "data": out}
    except Exception as e:
        return {"ok": False, "source": "exif", "error": str(e)}


def _hash(path: str, algo: str) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _serialize(v):
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", "replace").strip("\x00")
        except Exception:
            return v.hex()
    if isinstance(v, (list, tuple)):
        return [_serialize(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _serialize(x) for k, x in v.items()}
    return v


def _gps_to_decimal(gps: dict):
    try:
        def dms(val, ref):
            d, m, s = [float(x) for x in val]
            dec = d + m / 60 + s / 3600
            if ref in ("S", "W"):
                dec = -dec
            return dec
        lat = dms(gps["GPSLatitude"], gps.get("GPSLatitudeRef", "N"))
        lon = dms(gps["GPSLongitude"], gps.get("GPSLongitudeRef", "E"))
        return (lat, lon)
    except Exception:
        return None


# --------------------------------------------------------------------------
# 2. Domain / WHOIS
# --------------------------------------------------------------------------
def domain_whois(domain: str) -> dict:
    try:
        import whois
    except ImportError:
        return {"ok": False, "source": "whois", "error": "python-whois tidak terpasang"}
    try:
        w = whois.whois(domain)
        data = {}
        for k, v in dict(w).items():
            if isinstance(v, (list, tuple)):
                data[k] = [_serialize(x) for x in v]
            elif isinstance(v, datetime):
                data[k] = v.isoformat()
            else:
                data[k] = _serialize(v)
        return {"ok": True, "source": "whois", "data": data}
    except Exception as e:
        return {"ok": False, "source": "whois", "error": str(e)}


# --------------------------------------------------------------------------
# 3. DNS records
# --------------------------------------------------------------------------
def dns_records(domain: str) -> dict:
    try:
        import dns.resolver
    except ImportError:
        return {"ok": False, "source": "dns", "error": "dnspython tidak terpasang"}
    out = {}
    for rtype in ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]:
        try:
            answers = dns.resolver.resolve(domain, rtype, lifetime=8)
            out[rtype] = sorted(str(a).strip('"') for a in answers)
        except Exception:
            out[rtype] = []
    return {"ok": True, "source": "dns", "data": out}


# --------------------------------------------------------------------------
# 4. Subdomain enumeration (wordlist minimal)
# --------------------------------------------------------------------------
def subdomains(domain: str, wordlist: list[str] | None = None) -> dict:
    try:
        import dns.resolver
    except ImportError:
        return {"ok": False, "source": "subdomain", "error": "dnspython tidak terpasang"}

    words = wordlist or [
        "www", "mail", "ftp", "webmail", "smtp", "pop", "ns1", "ns2", "dns",
        "dev", "test", "staging", "api", "app", "portal", "admin", "vpn",
        "remote", "blog", "shop", "store", "cdn", "static", "assets", "media",
        "db", "mysql", "sql", "backup", "git", "gitlab", "jenkins", "ci",
        "staging", "beta", "alpha", "demo", "docs", "support", "help",
    ]
    found = {}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3
    resolver.lifetime = 3
    for w in words:
        host = f"{w}.{domain}"
        try:
            ans = resolver.resolve(host, "A", lifetime=3)
            found[host] = sorted(str(a) for a in ans)
        except Exception:
            pass
    return {"ok": True, "source": "subdomain", "data": found}


# --------------------------------------------------------------------------
# 5. Email harvesting dari halaman web (harvester minimal)
# --------------------------------------------------------------------------
def harvest_emails(domain: str) -> dict:
    import re
    import urllib.request
    urls = [f"https://{domain}", f"http://{domain}", f"https://www.{domain}"]
    emails = set()
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                html = r.read().decode("utf-8", "replace")
            found = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html)
            emails.update(found)
        except Exception:
            continue
    return {"ok": True, "source": "harvester", "data": sorted(emails)}
