#!/usr/bin/env python3
"""
osint_phone.py - Phone OSINT toolkit (precise & complete edition).

Modules:
  - geo_engine : IP / WiFi / cell tower -> approximate coordinates
  - enrich     : phonenumbers, breach, email, github, username, reverse-image
  - forensics  : EXIF, whois, DNS, subdomain, email harvester

Usage:
    python osint_phone.py 081234567890
    python osint_phone.py 081234567890 --json
    python osint_phone.py 081234567890 --ip 8.8.8.8
    python osint_phone.py 081234567890 --whois example.com --dns
    python osint_phone.py --exif foto.jpg
    python osint_phone.py 081234567890 --hibp-key KEY --hlr-key KEY
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime

# local modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "modules"))

try:
    import geo_engine
    import enrich
    import forensics
    import socint
    import devprofiles
    import breach
    import ipintel
    import leakcheck
    import business
    # helper alias for candidate generation
    generate_candidates = socint.generate_candidates
except ImportError as e:
    print(f"[!] Failed to load local modules: {e}", file=sys.stderr)
    print(f"    Make sure the 'modules/' folder exists in {os.path.dirname(__file__)}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Indonesian operator prefixes (static data; blocks may shift over time)
# ---------------------------------------------------------------------------
ID_PREFIXES = {
    "0811": "Telkomsel (Halo)", "0812": "Telkomsel", "0813": "Telkomsel",
    "0821": "Telkomsel", "0822": "Telkomsel", "0823": "Indosat Ooredoo (IM3)",
    "0851": "Telkomsel", "0852": "Telkomsel", "0853": "Telkomsel",
    "0814": "Indosat Ooredoo (M2)", "0815": "Indosat Ooredoo (M2)",
    "0816": "Indosat Ooredoo (M2)", "0855": "Indosat Ooredoo (M2)",
    "0856": "Indosat Ooredoo (IM3)", "0857": "Indosat Ooredoo (IM3)",
    "0858": "Indosat Ooredoo (IM3)", "0817": "XL Axiata",
    "0818": "XL Axiata", "0819": "XL Axiata", "0859": "XL Axiata",
    "0877": "XL Axiata", "0878": "XL Axiata", "0831": "AXIS",
    "0832": "AXIS", "0833": "AXIS", "0838": "AXIS",
    "0834": "AXIS", "0844": "AXIS",
    "0895": "Three (3)", "0896": "Three (3)", "0897": "Three (3)",
    "0898": "Three (3)", "0899": "Three (3)",
    "0881": "Smartfren", "0882": "Smartfren", "0883": "Smartfren",
    "0884": "Smartfren", "0885": "Smartfren", "0886": "Smartfren",
    "0887": "Smartfren", "0888": "Smartfren", "0889": "Smartfren",
}

ID_REGIONS = {
    "082313": "Indosat - blok nasional",
}


# ---------------------------------------------------------------------------
# Number normalization (fallback when phonenumbers lib is missing)
# ---------------------------------------------------------------------------
def normalize(raw: str) -> dict:
    import re
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0"):
        local, intl = digits, "62" + digits[1:]
    elif digits.startswith("62"):
        local, intl = "0" + digits[2:], digits
    elif digits.startswith("8"):
        local, intl = "0" + digits, "62" + digits
    else:
        local = intl = digits

    pretty = re.sub(r"(\d{4})(\d{4})(\d+)$", r"\1-\2-\3", local)
    return {
        "raw": raw, "e164": "+" + intl, "intl": intl, "local": local,
        "pretty": pretty, "prefix": local[:4], "prefix6": local[:6],
        "wa": "https://wa.me/" + intl,
        "tg": "https://t.me/+" + intl,
        "truecaller": "https://www.truecaller.com/search/id/" + intl,
        "getcontact": "https://www.getcontact.com/en/search?q=" + intl,
        "sync": "https://sync.me/search/?number=" + intl,
    }


def operator_lookup(local: str) -> str:
    return ID_PREFIXES.get(local[:4], "Unknown / unlisted prefix")


def region_lookup(local: str) -> str:
    for k, v in ID_REGIONS.items():
        if local.startswith(k):
            return v
    return "—"


def google_dorks(n: dict) -> list[str]:
    intl, local, pretty = n["intl"], n["local"], n["pretty"]
    return [
        f'"{intl}"', f'"+{intl}"', f'"{local}"', f'"{pretty}"',
        f'{intl} filetype:pdf',
        # social platforms
        f'{intl} site:facebook.com OR site:instagram.com OR site:twitter.com OR site:tiktok.com',
        f'{intl} site:reddit.com OR site:github.com OR site:linkedin.com',
        # Indonesian marketplaces
        f'{intl} site:olx.co.id OR site:tokopedia.com OR site:bukalapak.com OR site:shopee.co.id OR site:blibli.com',
        f'{intl} site:pastebin.com OR site:gitlab.com OR site:instagram.com/explore',
        # contact/account hints
        f'"{intl}" (wa OR whatsapp OR telegram OR line)',
        f'"{intl}" (nama OR alamat OR email OR rekening)',
        f'"{intl}" (gmail.com OR yahoo.com OR outlook.com)',
        f'"{intl}" (ktp OR npwp OR sim OR ijazah)',
        f'"{intl}" (jual OR beli OR dp OR cod)',
        f'"{local}" (penipu OR scam OR lapor)',
        # directory / call-logger sites
        f'{intl} site:namaseorang.com OR site:whoscall.com OR site:getcontact.com',
    ]


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------
def confidence_score(profile: dict) -> dict:
    """How verified the target identity is."""
    score = 0
    signals = []
    if profile.get("operator") and profile["operator"] != "—":
        score += 5; signals.append("operator detected")
    if profile.get("phonenumbers"):
        p = profile["phonenumbers"]
        if p.get("carrier"):
            score += 15; signals.append(f"carrier: {p['carrier']}")
        if p.get("region"):
            score += 10; signals.append(f"region: {p['region']}")
        if p.get("number_type"):
            score += 5; signals.append(f"type: {p['number_type']}")
    if profile.get("geo"):
        g = profile["geo"]
        acc = g.get("accuracy")
        if acc is not None:
            if acc <= 50:
                score += 40; signals.append(f"high-accuracy location ({acc}m)")
            elif acc <= 500:
                score += 25; signals.append(f"medium location ({acc}m)")
            else:
                score += 10; signals.append(f"coarse location ({acc}m)")
        else:
            score += 8; signals.append("IP-level location")
    if profile.get("breach", {}).get("count"):
        score += 15; signals.append(f"{profile['breach']['count']} breach")
    if profile.get("github"):
        score += 12; signals.append("github linked")
    if profile.get("email"):
        score += 9; signals.append("email linked")
    # bonus for resolved social accounts across candidates
    resolved = profile.get("resolved") or {}
    for key, val in resolved.items():
        if not isinstance(val, dict):
            continue
        data = val.get("data") or {}
        # handle_pivot hits
        if key == "handle_pivot" and isinstance(data, dict):
            hits = data.get("hits") or {}
            for pl, items in hits.items():
                if items:
                    score += 6; signals.append(f"pivot → {pl}")
                    break  # one hit per platform family is enough
        # social_* resolved profiles
        if key.startswith("social_"):
            uname = key[len("social_"):]
            summary = data.get("_summary") or {}
            if summary.get("found"):
                score += 10; signals.append(f"social found: {uname}")
            elif summary.get("probable"):
                score += 5; signals.append(f"social probable: {uname}")
        # telegram resolve
        if key == "telegram" and isinstance(data, dict):
            bn = data.get("by_number") or {}
            bd = bn.get("data") or {}
            if bd.get("display_name") and not bd.get("generic"):
                score += 12; signals.append("telegram matched")
    score = min(score, 100)
    level = "high" if score >= 65 else ("medium" if score >= 35 else "low")
    return {"score": score, "level": level, "signals": signals}


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------
def build_report(n: dict, profile: dict, opts) -> str:
    L = []
    W = 68
    L.append("=" * W)
    L.append("PHONE OSINT REPORT (advanced)")
    L.append("Generated: " + datetime.now().isoformat(timespec="seconds"))
    L.append("=" * W)
    L.append("")

    L.append("[1] NORMALIZATION")
    L.append(f"  Input    : {n['raw']}")
    L.append(f"  E.164    : {n['e164']}")
    L.append(f"  Local    : {n['local']}  ({n['pretty']})")
    L.append("")

    L.append("[2] OPERATOR & REGION")
    L.append(f"  Operator : {operator_lookup(n['local'])}")
    L.append(f"  Region*  : {region_lookup(n['local'])}")
    pn = profile.get("phonenumbers")
    if pn:
        L.append(f"  Carrier  : {pn.get('carrier') or '—'}")
        L.append(f"  Type     : {pn.get('number_type') or '—'}")
        L.append(f"  Geo desc : {pn.get('geo_description') or '—'}")
        L.append(f"  Timezone : {', '.join(pn.get('timezones') or []) or '—'}")
    L.append("  *region = historic registration area, NOT current location")
    L.append("")

    L.append("[3] GEOLOCATION")
    geo = profile.get("geo")
    if geo:
        L.append(f"  Source   : {geo.get('source')} ({geo.get('method', '')})")
        L.append(f"  Lat, Lon : {geo.get('lat')}, {geo.get('lon')}")
        L.append(f"  Accuracy : {geo.get('accuracy') or '~city'} m")
    else:
        L.append("  (no geo data — needs IP/WiFi/cell)")
    L.append("")

    L.append("[4] LINK PROBE (open manually, check name/avatar/bio)")
    L.append(f"  WhatsApp  : {n['wa']}")
    L.append(f"  Telegram  : {n['tg']}")
    L.append(f"  Truecaller: {n['truecaller']}")
    L.append(f"  GetContact: {n['getcontact']}")
    L.append(f"  Sync.me   : {n['sync']}")
    L.append("")

    L.append("[5] GOOGLE DORKS")
    for d in google_dorks(n):
        L.append(f"  {d}")
    L.append("")

    if profile.get("github"):
        g = profile["github"]
        L.append("[6] GITHUB")
        L.append(f"  User     : {g.get('login')}")
        L.append(f"  Name     : {g.get('name') or '—'}")
        L.append(f"  Location : {g.get('location') or '—'}")
        L.append(f"  Email    : {g.get('email') or '—'}")
        L.append(f"  Blog     : {g.get('blog') or '—'}")
        L.append(f"  Repo     : {g.get('public_repos')} | Followers: {g.get('followers')}")
        if g.get("commit_emails"):
            L.append(f"  Commit emails: {', '.join(g['commit_emails'][:8])}")
        L.append("")

    if profile.get("breach"):
        b = profile["breach"]
        L.append("[7] BREACH")
        L.append(f"  Count    : {b.get('count', 0)}")
        for x in (b.get("names") or [])[:15]:
            L.append(f"    - {x}")
        L.append("")

    if profile.get("email"):
        e = profile["email"]
        L.append("[8] EMAIL ENRICHMENT")
        L.append(f"  Domain   : {e.get('domain') or '—'}")
        L.append(f"  Disposable: {'yes' if e.get('is_disposable') else 'no'}")
        L.append(f"  Free mail : {'yes' if e.get('is_free') else 'no'}")
        if e.get("gravatar"):
            L.append(f"  Gravatar : {e['gravatar'].get('profile_url')}")
        L.append("")

    conf = profile.get("confidence") or confidence_score(profile)
    L.append("[9] CONFIDENCE")
    L.append(f"  Score    : {conf['score']}/100  ({conf['level']})")
    for s in conf["signals"]:
        L.append(f"    + {s}")
    L.append("")

    L.append("=" * W)
    L.append("Legal: only track assets you own or with explicit consent / lawful authorization.")
    L.append("=" * W)
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Phone OSINT toolkit (advanced)")
    ap.add_argument("number", nargs="?", help="Phone number (e.g. 081234567890)")
    ap.add_argument("--out", help="Save report to file")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--links", action="store_true", help="Open probe links in browser")
    ap.add_argument("--dorks", action="store_true", help="Open google dork")
    ap.add_argument("--ip", help="Geo lookup for this IP")
    ap.add_argument("--username", help="Check username across platforms")
    ap.add_argument("--github", help="GitHub user lookup")
    ap.add_argument("--email", help="Email lookup (gravatar, domain)")
    ap.add_argument("--whois", help="WHOIS domain")
    ap.add_argument("--dns", action="store_true", help="DNS records for --whois domain")
    ap.add_argument("--subdomain", help="Subdomain enumeration")
    ap.add_argument("--exif", help="Analyze image EXIF")
    ap.add_argument("--reverse-image", dest="revimg", help="Generate reverse-image links")
    ap.add_argument("--resolve", action="store_true",
                    help="Resolve number -> social accounts (Telegram, Truecaller, pivot, search)")
    ap.add_argument("--dev", help="Developer profile lookup (username) on GitHub/GitLab/PyPI/npm/etc")
    ap.add_argument("--social", help="Resolve social profiles via Jina (username)")
    ap.add_argument("--email-intel", dest="email_intel", help="Intel email (gravatar/PGP/Hudson Rock/HIBP)")
    ap.add_argument("--ipintel", help="IP intelligence (Shodan InternetDB/IPinfo/GreyNoise + AbuseIPDB/Censys opsional)")
    ap.add_argument("--leakcheck", help="Breach/leak lookup (LeakCheck public + HIBP/Snusbase/DeHashed opsional)")
    ap.add_argument("--business", help="Business registry (GLEIF/SEC EDGAR + OpenCorporates/CompaniesHouse opsional)")
    ap.add_argument("--shodan-key", dest="shodan_key", default="", help="Shodan API key")
    ap.add_argument("--abuseipdb-key", dest="abuse_key", default="", help="AbuseIPDB API key")
    ap.add_argument("--censys-id", dest="censys_id", default="", help="Censys API ID")
    ap.add_argument("--censys-secret", dest="censys_secret", default="", help="Censys API secret")
    ap.add_argument("--leakcheck-key", dest="leakcheck_key", default="", help="LeakCheck API key")
    ap.add_argument("--snusbase-key", dest="snusbase_key", default="", help="Snusbase API key")
    ap.add_argument("--dehashed-key", dest="dehashed_key", default="", help="DeHashed API key (email:key)")
    ap.add_argument("--rapidapi-key", dest="rapidapi_key", default="", help="RapidAPI key (BreachDirectory)")
    ap.add_argument("--opencorp-token", dest="opencorp_token", default="", help="OpenCorporates API token")
    ap.add_argument("--ch-key", dest="ch_key", default="", help="UK Companies House API key")
    ap.add_argument("--truecaller-cookie", dest="tc_cookie", default="", help="Cookie login Truecaller")
    ap.add_argument("--serpapi-key", dest="serp_key", default="", help="SerpAPI key")
    ap.add_argument("--searxng", dest="searxng", default="", help="SearXNG instance URL")
    ap.add_argument("--emailrep-key", dest="emailrep_key", default="", help="EmailRep API key")
    ap.add_argument("--hlr-key", help="API key HLR lookup")
    ap.add_argument("--hibp-key", help="API key HIBP")
    ap.add_argument("--wifi-key", help="WiFi geo API key (optional)")
    ap.add_argument("--cell-key", help="Cell geo API key (OpenCellID/UnwiredLabs)")
    ap.add_argument("--mcc", type=int, help="Cell MCC (for --cell)")
    ap.add_argument("--mnc", type=int, help="MNC cell")
    ap.add_argument("--lac", type=int, help="LAC cell")
    ap.add_argument("--cid", type=int, help="CID cell")
    opts = ap.parse_args()

    # ==== Individual tool mode ====
    standalone = {}

    if opts.exif:
        standalone["exif"] = forensics.exif_image(opts.exif)
    if opts.revimg:
        standalone["reverse_image"] = enrich.reverse_image_links(opts.revimg)
    if opts.username:
        standalone["username"] = enrich.username_check(opts.username)
    if opts.github:
        standalone["github"] = enrich.github_lookup(opts.github)
    if opts.whois:
        standalone["whois"] = forensics.domain_whois(opts.whois)
        if opts.dns:
            standalone["dns"] = forensics.dns_records(opts.whois)
    if opts.subdomain:
        standalone["subdomains"] = forensics.subdomains(opts.subdomain)
    if opts.email:
        standalone["email"] = enrich.email_lookup(opts.email).get("data", {})
    if opts.ip:
        standalone["ip_geo"] = geo_engine.ip_geo(opts.ip)
    if opts.dev:
        standalone["dev_profiles"] = devprofiles.lookup_all(opts.dev)
    if opts.social:
        standalone["social_profiles"] = socint.social_resolve_all(opts.social)
    if opts.email_intel:
        standalone["email_intel"] = breach.email_intel(opts.email_intel, opts.hibp_key or "", opts.emailrep_key or "")
    if opts.ipintel:
        standalone["ip_intel"] = ipintel.lookup_all(opts.ipintel, opts.shodan_key or "", opts.abuse_key or "",
                                                     opts.censys_id or "", opts.censys_secret or "")
    if opts.leakcheck:
        standalone["leakcheck"] = leakcheck.lookup_all(opts.leakcheck, opts.leakcheck_key or "",
                                                        opts.hibp_key or "", opts.snusbase_key or "",
                                                        opts.dehashed_key or "", opts.rapidapi_key or "")
    if opts.business:
        standalone["business"] = business.lookup_all(opts.business, opts.opencorp_token or "", opts.ch_key or "")

    # ==== Phone number mode ====
    profile = {}
    if opts.number:
        n = normalize(opts.number)
        profile["operator"] = operator_lookup(n["local"])
        profile["region"] = region_lookup(n["local"])
        profile["dorks"] = google_dorks(n)

        # phonenumbers enrichment
        pe = enrich.enrich_phone(opts.number)
        if pe.get("ok"):
            profile["phonenumbers"] = pe["data"]

        # geo resolve
        cell = None
        if all(v is not None for v in [opts.mcc, opts.mnc, opts.lac, opts.cid]):
            cell = (opts.mcc, opts.mnc, opts.lac, opts.cid)
        if opts.ip or cell:
            g = geo_engine.resolve_best(ip=opts.ip, cell=cell, cell_key=opts.cell_key)
            if g.get("best"):
                profile["geo"] = g["best"]

        # breach
        if opts.hibp_key:
            be = enrich.breach_hibp(n["e164"], opts.hibp_key)
            if be.get("ok"):
                bl = be["data"].get("breaches") or []
                profile["breach"] = {
                    "count": len(bl),
                    "names": [x.get("Name") for x in bl if x.get("Name")],
                }

        # resolve number -> social accounts
        if opts.resolve:
            # generate candidate usernames from the number
            cands = generate_candidates(n["local"], n["intl"])
            resolved = socint.resolve_all(
                n["intl"], n["local"],
                truecaller_cookie=opts.tc_cookie,
                serpapi_key=opts.serp_key,
                searxng_instance=opts.searxng,
                usernames=cands,
            )
            profile["resolved"] = resolved
            # surface the candidate variants used
            profile["candidate_usernames"] = cands[:20]

        profile["confidence"] = confidence_score(profile)

        # report
        if opts.json:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            out = {
                "normalized": n,
                "operator": profile["operator"],
                "region": profile["region"],
                "dorks": profile["dorks"],
                "profile": {k: v for k, v in profile.items() if k != "dorks"},
                "standalone": standalone or None,
            }
            print(json.dumps(out, ensure_ascii=True, default=str))
        else:
            text = build_report(n, profile, opts)
            if opts.resolve and profile.get("resolved"):
                text += "\n\n" + "=" * 68 + "\nRESOLVE: NUMBER -> SOCIAL ACCOUNTS\n" + "=" * 68 + "\n"
                text += json.dumps(profile["resolved"], indent=2, ensure_ascii=False, default=str)
            if standalone:
                text += "\n\n" + "=" * 68 + "\nSTANDALONE TOOL RESULTS\n" + "=" * 68 + "\n"
                text += json.dumps(standalone, indent=2, ensure_ascii=False, default=str)
            print(text)
            if opts.out:
                with open(opts.out, "w", encoding="utf-8") as fh:
                    fh.write(text)
                print(f"\n[+] Report saved: {opts.out}", file=sys.stderr)

        if opts.links:
            import webbrowser
            for url in [n["wa"], n["tg"], n["truecaller"], n["getcontact"]]:
                webbrowser.open_new_tab(url)
        if opts.dorks:
            import webbrowser
            webbrowser.open_new_tab("https://www.google.com/search?q=" +
                                    urllib.parse.quote(f'"{n["intl"]}"'))

    # ==== Tool-only mode (no number) ====
    if standalone and not opts.number:
        if opts.json:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            print(json.dumps(standalone, ensure_ascii=True, default=str))
        else:
            print(json.dumps(standalone, indent=2, ensure_ascii=True, default=str))

    if not opts.number and not standalone:
        ap.print_help()


if __name__ == "__main__":
    main()
