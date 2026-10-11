# OSINT Console — Phone & Identity Tracking Toolkit

Retro **amber CRT terminal** dashboard: **Phone OSINT** (number → accounts, auto-resolve)
+ **Tools** (14 tools) + **Grabber** (location tracker). Every source renders in-place.

> A phone number alone yields name/accounts/operator/region. Precise GPS needs the
> grabber (target taps Allow) or cell/WiFi data (via API key).

---

## Structure

```
osint/
├── run.ps1                  # launcher (server + tunnel + browser)
├── osint_phone.py           # all-in-one CLI toolkit
├── README.md
├── ANALYSIS_TEMPLATE.md
├── modules/
│   ├── geo_engine.py        # IP / WiFi / cell -> coordinates
│   ├── enrich.py            # phonenumbers, breach, email, github, username
│   ├── forensics.py         # EXIF, whois, DNS, subdomain, harvester
│   ├── socint.py            # number -> Telegram/Truecaller/pivot/Jina/messaging/search
│   ├── devprofiles.py       # GitHub/GitLab/PyPI/npm/DockerHub/SO/Keybase/HN/Mastodon/DevTo/Codeberg/Reddit
│   ├── breach.py            # Hudson Rock/PGP/Gravatar/HIBP/EmailRep
│   ├── ipintel.py           # Shodan InternetDB/IPinfo/GreyNoise/AbuseIPDB/Censys
│   ├── leakcheck.py         # LeakCheck public/HIBP/Snusbase/DeHashed/BreachDirectory
│   └── business.py          # GLEIF/SEC EDGAR/OpenCorporates/CompaniesHouse/AHU
└── grabber/
    ├── index_console.php    # DASHBOARD (1 page, 3 tabs, amber CRT + boot + phosphor toggle)
    ├── index.php            # landing page (target-facing, amber CRT)
    ├── dashboard.php        # alias -> index_console.php
    ├── api_tools.php        # PHP -> Python bridge
    ├── api_settings.php     # read/save API keys
    ├── config.php           # config + default keys
    ├── config_keys.json     # keys from Settings panel (auto-created, gitignored)
    └── logs/hits.jsonl
```

---

## Quick Start

```powershell
cd path\to\osint
.\run.ps1                 # server + open dashboard
.\run.ps1 -Tunnel         # + ngrok (public HTTPS URL)
```

Manual: `php -S localhost:8080 -t grabber` → `http://localhost:8080/dashboard.php`

Requirements: PHP 8.x, Python 3.10+ (`pip install phonenumbers python-whois dnspython requests beautifulsoup4 pillow`).

---

## Dashboard — 3 Tabs

### Tab 1: Phone OSINT (auto-resolve)
Enter a number → everything resolves in place:
- **Identity**: operator, carrier, type, region, E.164
- **Confidence score** 0–100
- **Telegram**: name/@username/bio/avatar (auto)
- **Truecaller**: owner name (needs login cookie)
- **Number-as-Handle**: pivot across 6 platforms
- **Messaging Apps**: Viber/WhatsApp/LINE/Telegram links + reachability
- **Social (Jina)**: IG/TikTok/X profiles (when a candidate username exists)
- **Search** (SerpAPI / fallback links) + **14 Google dorks**

### Tab 2: Tools (14 tools)
| Tool | Sources |
|------|--------|
| Dev Profiles | GitHub, GitLab, PyPI, npm, DockerHub, StackOverflow, Keybase, HackerNews, Mastodon, DevTo, Codeberg, Reddit |
| Social Profiles | **14 platforms** (IG, FB, X, TikTok, LinkedIn, Threads, Snapchat, Pinterest, YouTube, Reddit, Twitch, Medium, GitHub, Telegram) via Jina + **scoring engine** |
| Username Check | 19 platforms (marker-based) |
| GitHub Lookup | profile + repos + commit emails |
| Email Intel | Hudson Rock (info-stealer), Gravatar, PGP keyserver, HIBP breach+paste |
| **IP Intel** | Shodan InternetDB (ports/hostnames/vulns), IPinfo, GreyNoise (+AbuseIPDB/Censys optional) |
| **Breach/Leak** | LeakCheck public (FREE), HIBP (+Snusbase/DeHashed/BreachDirectory optional) |
| **Business Registry** | GLEIF (global LEI), SEC EDGAR (US), AHU Indonesia (+OpenCorporates/CompaniesHouse optional) |
| Email Lookup | gravatar + domain classification |
| IP Geolocation | ip-api → ipwho.is → ipinfo |
| WHOIS / DNS / Subdomain | domain intel |
| Reverse Image | Google Lens, Yandex, TinEye, Bing, SauceNAO, trace.moe |

**Handle Pivot** (Phone OSINT tab) checks the number as a username on **17 platforms**:
Telegram, Reddit, Pinterest, SoundCloud, Keybase, Steam, GitHub, TikTok, Facebook,
Instagram, Twitter/X, Threads, Snapchat, LinkedIn, YouTube, Medium, Twitch.

## Social Profiles Accuracy (scoring engine)

Social Profiles use a **multi-signal scoring engine**, not binary true/false:
- Parses title/description/content → scores handle match, specific title, bio,
  social metrics (followers/likes/subscribers), substantial content.
- **Honest tri-state status**: `found` / `probable` / `not_found` / `blocked` / `unknown`.
- **Explicit login-wall & anti-bot detection** → `blocked` (never a false positive).
- **Extracts real data**: display name + bio + evidence signals.
- Login-gated platforms (IG/LinkedIn/Reddit) show `blocked` = "unconfirmed",
  never guessed. Tested 10/10 accurate (exists vs not-exists).

### Tab 3: Grabber
Hits + Leaflet map + per-event detail (IP geo, precise GPS, fingerprint).

### CRT Features (header, right side)
- **◧ GREEN/AMBER** — phosphor color toggle (amber ↔ green)
- **♪ SOUND** — beep on/off (Web Audio, square wave)
- **⚙ KEYS** — Settings panel for all API keys (saved to `config_keys.json`)
- **⟳ REFRESH** — reload
- BIOS-style boot sequence on first open
- CRT effects: scanlines, vignette, flicker, text glow

---

## Settings Panel (API keys via UI)

Click **⚙ KEYS** in the header → fill in the keys you have → **SAVE**. Stored in
`grabber/config_keys.json` (mode 0600, gitignored). Empty field = unchanged.

Supported keys: Truecaller cookie, SerpAPI, SearXNG, Shodan, AbuseIPDB, Censys (id+secret),
HIBP, LeakCheck, Snusbase, DeHashed, RapidAPI, EmailRep, OpenCorporates, Companies House,
Telegram bot (token+chat).

Or edit `grabber/config.php` manually. Settings writes are localhost-only by default
(set `allow_remote_settings=true` only behind auth).

---

## Data Sources (all free, no key)

✅ **Telegram** (t.me scrape) · ✅ **Hudson Rock** (info-stealer) · ✅ **GitHub API** ·
✅ **GitLab/PyPI/npm/DockerHub/StackOverflow/Keybase/HackerNews/Mastodon/DevTo/Codeberg** ·
✅ **Gravatar** · ✅ **PGP keyserver** · ✅ **Jina reader** (scrape IG/TikTok/X) ·
✅ **DNS/WHOIS** · ✅ **IP geo**

Optional keys: **Truecaller** (login cookie, number-owner name) ·
**SerpAPI** (search, 100 free/mo) · **HIBP** (breach, paid) · **EmailRep** (free) ·
**OpenCellID/UnwiredLabs** (cell geo)

---

## Key Setup (optional)

Edit `grabber/config.php`:

```php
// Truecaller: log in in browser -> DevTools F12 -> Application -> Cookies -> copy as string
'truecaller_cookie' => 'name=value; name2=value2',

// SerpAPI: free signup at serpapi.com -> copy key
'serpapi_key' => 'KEY',

// HIBP: haveibeenpwned.com/API/Key
'hibp_key' => 'KEY',

// EmailRep: emailrep.io
'emailrep_key' => 'KEY',
```

---

## CLI

```powershell
# Number + resolve
python osint_phone.py 081234567890 --resolve --json

# Dev profiles (username)
python osint_phone.py --dev torvalds --json

# Social profiles (via Jina)
python osint_phone.py --social nasa --json

# Email intel (breach + gravatar + PGP)
python osint_phone.py --email-intel user@gmail.com --json

# IP intel / breach / business
python osint_phone.py --ipintel 1.1.1.1 --json
python osint_phone.py --leakcheck torvalds --json
python osint_phone.py --business tesla --json

# Standalone tools
python osint_phone.py --ip 1.1.1.1 --json
python osint_phone.py --username torvalds --json
python osint_phone.py --github torvalds --json
python osint_phone.py --email user@gmail.com --json
python osint_phone.py --whois example.com --dns --json
python osint_phone.py --subdomain example.com --json
python osint_phone.py --exif photo.jpg --json
python osint_phone.py --reverse-image https://img.jpg --json
```

---

## Location Resolution — Precision Ladder

| Method | Precision | Needs |
|--------|-----------|-------|
| GPS (grabber) | 5–50 m | target taps Allow |
| Cell tower | 50–1500 m | MCC/MNC/LAC/CID + key |
| WiFi BSSID | 20–200 m | BSSID scan |
| IP geolocation | city-level | IP |

---

## Legal & Ethics

- Only track devices/accounts you own or have explicit consent to investigate.
  Unauthorized tracking may violate privacy laws (e.g. Indonesia's PDP Law No.27/2022,
  ITE Law). SS7/tower-level tracking is operator/law-enforcement only.
- This toolkit is for defensive research, asset recovery, and authorized
  investigations. Misuse is on you.
