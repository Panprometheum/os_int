# OSINT Console — Phone & Identity Tracking Toolkit

Dashboard **terminal retro amber CRT**: **Phone OSINT** (nomor → akun, auto-resolve)
+ **Tools** (14 tool) + **Grabber** (pelacak lokasi). Semua sumber keluar in-place.

> Nomor doang = nama/akun/operator/region. GPS presisi butuh grabber (target Allow)
> atau data cell/wifi (via API key).

---

## Struktur

```
osint/
├── run.ps1                  # launcher (server + tunnel + browser)
├── osint_phone.py           # toolkit CLI (all-in-one)
├── README.md
├── ANALYSIS_TEMPLATE.md
├── modules/
│   ├── geo_engine.py        # IP / WiFi / cell -> koordinat
│   ├── enrich.py            # phonenumbers, breach, email, github, username
│   ├── forensics.py         # EXIF, whois, DNS, subdomain, harvester
│   ├── socint.py            # nomor -> Telegram/Truecaller/pivot/Jina/messaging/search
│   ├── devprofiles.py       # GitHub/GitLab/PyPI/npm/DockerHub/SO/Keybase/HN/Mastodon/DevTo/Codeberg/Reddit
│   ├── breach.py            # Hudson Rock/PGP/Gravatar/HIBP/EmailRep
│   ├── ipintel.py           # Shodan InternetDB/IPinfo/GreyNoise/AbuseIPDB/Censys
│   ├── leakcheck.py         # LeakCheck public/HIBP/Snusbase/DeHashed/BreachDirectory
│   └── business.py          # GLEIF/SEC EDGAR/OpenCorporates/CompaniesHouse/AHU
└── grabber/
    ├── index_console.php    # DASHBOARD (1 page, 3 tab, amber CRT + boot + phosphor toggle)
    ├── index.php            # landing page (target, amber CRT)
    ├── dashboard.php        # alias -> index_console.php
    ├── api_tools.php        # bridge PHP -> Python
    ├── api_settings.php     # simpan/baca API keys
    ├── config.php           # config + default keys
    ├── config_keys.json     # keys dari Settings panel (auto, gitignored)
    └── logs/hits.jsonl
```

---

## Jalanin

```powershell
cd C:\Users\TUF\Documents\Dfaced\osint
.\run.ps1                 # server + buka dashboard
.\run.ps1 -Tunnel         # + ngrok (URL HTTPS publik)
```

Manual: `php -S localhost:8080 -t osint\grabber` → `http://localhost:8080/dashboard.php`

---

## Dashboard — 3 Tab

### Tab 1: Phone OSINT (auto-resolve)
Kasih nomor → keluar langsung:
- **Identitas**: operator, carrier, tipe, region, E.164
- **Confidence score** 0–100
- **Telegram**: nama/@username/bio/avatar (auto)
- **Truecaller**: nama pemilik (butuh cookie)
- **Nomor sebagai Handle**: pivot 6 platform
- **Messaging Apps**: link Viber/WhatsApp/LINE/Telegram + reachability
- **Social (Jina)**: profil IG/TikTok/X/dll (kalau ada username kandidat)
- **Pencarian** (SerpAPI / link fallback) + **14 Google Dork**

### Tab 2: Tools (14 tool)
| Tool | Sumber |
|------|--------|
| Dev Profiles | GitHub, GitLab, PyPI, npm, DockerHub, StackOverflow, Keybase, HackerNews, Mastodon, DevTo, Codeberg, Reddit |
| Social Profiles | **14 platform** (IG, FB, X, TikTok, LinkedIn, Threads, Snapchat, Pinterest, YouTube, Reddit, Twitch, Medium, GitHub, Telegram) via Jina + **engine scoring** |
| Username Check | 19 platform (marker-based) |
| GitHub Lookup | profil + repos + commit emails |
| Email Intel | Hudson Rock (info-stealer), Gravatar, PGP keyserver, HIBP breach+paste |
| **IP Intel** | Shodan InternetDB (ports/hostnames/vulns), IPinfo, GreyNoise (+AbuseIPDB/Censys opsional) |
| **Breach/Leak** | LeakCheck public (GRATIS), HIBP (+Snusbase/DeHashed/BreachDirectory opsional) |
| **Business Registry** | GLEIF (LEI global), SEC EDGAR (US), AHU Indonesia (+OpenCorporates/CompaniesHouse opsional) |
| Email Lookup | gravatar + klasifikasi domain |
| IP Geolocation | ip-api → ipwho.is → ipinfo |
| WHOIS / DNS / Subdomain | domain intel |
| Reverse Image | Google Lens, Yandex, TinEye, Bing, SauceNAO, trace.moe |

**Handle Pivot** (tab Phone OSINT) cek nomor sebagai username di **17 platform**:
Telegram, Reddit, Pinterest, SoundCloud, Keybase, Steam, GitHub, TikTok, Facebook,
Instagram, Twitter/X, Threads, Snapchat, LinkedIn, YouTube, Medium, Twitch.

## Akurasi Social Profiles (engine scoring)

Social Profiles pakai **engine scoring multi-sinyal**, bukan binary true/false:
- Tarik title/description/content → skor dari: handle cocok, title spesifik, bio,
  metrik sosial (follower/likes/subscribers), konten substansial.
- **Status tri-state jujur**: `found` / `probable` / `not_found` / `blocked` / `unknown`.
- **Deteksi login-wall & anti-bot** eksplisit → `blocked` (bukan false-positive).
- **Ekstrak data nyata**: display name + bio + bukti sinyal.
- Platform butuh login (IG/LinkedIn/Reddit) tampil `blocked` = "tak terkonfirmasi",
  bukan ditebak. Hasil test: 10/10 akurat (exists vs not-exists).

### Tab 3: Grabber
Hits + peta Leaflet + detail event (IP geo, GPS presisi, fingerprint).

### Fitur CRT (header kanan)
- **◧ GREEN/AMBER** — toggle warna fosfor (amber ↔ green)
- **♪ SOUND** — beep on/off (Web Audio, square wave)
- **⚙ KEYS** — Settings panel buat isi semua API key (tersimpan ke `config_keys.json`)
- **⟳ REFRESH** — reload
- Boot sequence ala BIOS waktu pertama buka
- Efek CRT: scanlines, vignette, flicker, glow teks

---

## Settings Panel (isi API key dari UI)

Klik **⚙ KEYS** di header → isi key yang kamu punya → **SIMPAN**. Tersimpan di
`grabber/config_keys.json` (mode 0600, sudah di-gitignore). Kosongkan field = tidak berubah.

Key yang didukung: Truecaller cookie, SerpAPI, SearXNG, Shodan, AbuseIPDB, Censys (id+secret),
HIBP, LeakCheck, Snusbase, DeHashed, RapidAPI, EmailRep, OpenCorporates, Companies House,
Telegram bot (token+chat).

Atau edit manual `grabber/config.php`.

---

## Sumber Data (semua gratis, tanpa key)

✅ **Telegram** (t.me scrape) · ✅ **Hudson Rock** (info-stealer) · ✅ **GitHub API** ·
✅ **GitLab/PyPI/npm/DockerHub/StackOverflow/Keybase/HackerNews/Mastodon/DevTo/Codeberg** ·
✅ **Gravatar** · ✅ **PGP keyserver** · ✅ **Jina reader** (scrape IG/TikTok/X) ·
✅ **DNS/WHOIS** · ✅ **IP geo**

Butuh key (opsional): **Truecaller** (cookie login, nama pemilik nomor) ·
**SerpAPI** (search, gratis 100/bln) · **HIBP** (breach, berbayar) · **EmailRep** (gratis) ·
**OpenCellID/UnwiredLabs** (cell geo)

---

## Setup Key (opsional)

Edit `grabber/config.php`:

```php
// Truecaller: login di browser -> DevTools F12 -> Application -> Cookies -> copy jadi string
'truecaller_cookie' => 'nama=nilai; nama2=nilai2',

// SerpAPI: daftar gratis di serpapi.com -> copy key
'serpapi_key' => 'KEY',

// HIBP: haveibeenpwned.com/API/Key
'hibp_key' => 'KEY',

// EmailRep: emailrep.io
'emailrep_key' => 'KEY',
```

---

## CLI

```powershell
# Nomor + resolve
python osint\osint_phone.py 081234567890 --resolve --json

# Dev profiles (username)
python osint\osint_phone.py --dev torvalds --json

# Social profiles (via Jina)
python osint\osint_phone.py --social nasa --json

# Email intel (breach + gravatar + PGP)
python osint\osint_phone.py --email-intel user@gmail.com --json

# Tool standalone
python osint\osint_phone.py --ip 1.1.1.1 --json
python osint\osint_phone.py --username torvalds --json
python osint\osint_phone.py --github torvalds --json
python osint\osint_phone.py --email user@gmail.com --json
python osint\osint_phone.py --whois example.com --dns --json
python osint\osint_phone.py --subdomain example.com --json
python osint\osint_phone.py --exif foto.jpg --json
python osint\osint_phone.py --reverse-image https://img.jpg --json
```

---

## Resolusi Lokasi — Presisi Bertingkat

| Metode | Presisi | Butuh |
|--------|---------|-------|
| GPS (grabber) | 5–50 m | target Allow |
| Cell tower | 50–1500 m | MCC/MNC/LAC/CID + key |
| WiFi BSSID | 20–200 m | scan BSSID |
| IP geolocation | kota | IP |

---

## Legal

- Tracking orang tanpa izin = **UU PDP No.27/2022 + UU ITE**.
- Legal: aset sendiri, izin target, atau investigasi resmi.
- SS7 / tower triangulation hanya via operator / lawful intercept.
