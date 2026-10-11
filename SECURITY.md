# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

This is a research toolkit under active development. Security fixes land on `main`.

## Reporting a Vulnerability

Found something? Please **do not** open a public issue for sensitive vulnerabilities.

- Open a [private security advisory](https://github.com/Panprometheum/os_int/security/advisories/new),
  or contact the maintainer via the email on their GitHub profile.
- Include: affected file/endpoint, steps to reproduce, and impact.
- Expect an initial response within 7 days. We'll coordinate disclosure before any public fix.

## Known Security Considerations (by design)

This tool is meant to run **locally/trusted-network only**. If you expose it publicly,
harden it first:

1. **No built-in auth on the dashboard.** `dashboard.php` / `api_tools.php` execute
   OSINT lookups for anyone who can reach the URL. Put it behind HTTP basic auth,
   a VPN, or a reverse proxy with authentication before exposing it.
2. **Settings writes are localhost-only by default** (`api_settings.php` returns 403
   for remote POST unless `allow_remote_settings=true` in `grabber/config.php`).
   Only enable that behind auth.
3. **API keys live in `grabber/config_keys.json`** (mode 0600, gitignored). Never commit
   this file. Rotate any key that was ever pasted into a log, screenshot, or chat.
4. **Grabber logs (`grabber/logs/hits.jsonl`) contain visitor IPs and locations.**
   Treat them as sensitive personal data: restrict access, encrypt backups, delete
   when no longer needed.
5. **Shell execution.** `api_tools.php` shells out to `osint_phone.py` via `proc_open`.
   Arguments are allow-listed and escaped (`escapeshellarg`), but do not add new
   tool endpoints without keeping that allow-list.

## Responsible Use

This toolkit can resolve phone numbers to social accounts and log visitor locations.
Use it only on assets you own, with explicit consent, or under lawful authorization
(e.g. asset recovery, defensive research, formal investigations). The maintainers
are not responsible for misuse.
